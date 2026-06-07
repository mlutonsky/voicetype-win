"""voicetype-win – local voice dictation -> text (Whisper Flow style).

Transcription runs offline via onnx-asr; the model is configurable (Parakeet,
Canary, ...) in config.toml. User-facing texts follow the system locale (see i18n.py).

Toggle mode: press the hotkey (default Alt+.) to start recording, press again to
stop. Speech is transcribed and the text is inserted into the focused window.

Run with a console:  .venv\\Scripts\\python.exe dictate.py
Silent background:    run start-dictation.vbs
"""
import gc
import os
import sys
import threading
import time
import tomllib
import winsound
from pathlib import Path

import keyboard
import numpy as np
import pyperclip
import pystray
import sounddevice as sd
from PIL import Image, ImageDraw

import config_utils
import i18n
import media_control
import ort_utils
from cuda_init import init_cuda

# The Windows console is often cp1250 – switch output to UTF-8 so we don't crash on ●/■/→/accents
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE = Path(__file__).resolve().parent
LOGFILE = BASE / "dictate.log"
_MAX_LOG_BYTES = 1_000_000

_log_lock = threading.Lock()
_log_fh = None


def _log_handle():
    """Open the log file once (rotating a large previous log). Returns a handle or None."""
    global _log_fh
    if _log_fh is None:
        try:
            if LOGFILE.exists() and LOGFILE.stat().st_size > _MAX_LOG_BYTES:
                backup = LOGFILE.with_name(LOGFILE.name + ".1")
                try:
                    if backup.exists():
                        backup.unlink()
                    LOGFILE.rename(backup)
                except OSError:
                    pass
            _log_fh = open(LOGFILE, "a", encoding="utf-8")
        except Exception:
            _log_fh = None
    return _log_fh


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    # Console (may be None under pythonw)
    try:
        if sys.stdout is not None:
            print(line, flush=True)
    except Exception:
        pass
    # Also to the log file, kept open across calls (for background runs without a console)
    with _log_lock:
        fh = _log_handle()
        if fh is not None:
            try:
                fh.write(line + "\n")
                fh.flush()
            except Exception:
                pass


def load_config() -> dict:
    cfg = {
        "hotkey": "alt+.",
        "model": "nemo-parakeet-tdt-0.6b-v3",
        "models": ["nemo-parakeet-tdt-0.6b-v3", "nemo-canary-1b-v2"],
        "device": "auto",
        "language": "auto",
        "target_language": "cs",
        "ui_language": "auto",
        "punctuation": True,
        "append_space": True,
        "beep": True,
        "paste_method": "clipboard",
        "restore_clipboard": True,
        "pause_media": True,
    }
    path = BASE / "config.toml"
    if path.is_file():
        with open(path, "rb") as f:
            cfg.update(tomllib.load(f))
    return cfg


def beep(enabled: bool, freq: int, dur: int = 110) -> None:
    if enabled:
        threading.Thread(target=winsound.Beep, args=(freq, dur), daemon=True).start()


def _is_pressed(key: str) -> bool:
    try:
        return keyboard.is_pressed(key)
    except Exception:
        return False


class Dictator:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.samplerate = 16000
        self.recording = False
        self.frames: list[np.ndarray] = []
        self.stream: sd.InputStream | None = None
        self.lock = threading.Lock()
        self._model_lock = threading.Lock()  # serializes load/unload of the model
        self.busy = False            # transcription in progress
        self.model = None
        self.enabled = True          # dictation active (can be paused from the tray)
        self.on_state = None         # callback() on state change (for the tray icon)
        self.on_gpu = False          # last known device state (GPU/CPU)
        self._paused_media: list[str] = []  # players paused for the duration of recording

    @property
    def loaded(self) -> bool:
        return self.model is not None

    def notify(self) -> None:
        if self.on_state:
            try:
                self.on_state()
            except Exception:
                pass

    # ---- model ----
    def providers(self) -> list[str]:
        dev = self.cfg["device"]
        if dev == "cpu":
            return ["CPUExecutionProvider"]
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]

    def load_model(self) -> None:
        with self._model_lock:
            if self.loaded:
                return
            import onnx_asr
            if self.cfg["device"] != "cpu":
                init_cuda()
            provs = self.providers()
            log(i18n.t("loading_model", model=self.cfg["model"], providers=provs))
            self.model = onnx_asr.load_model(self.cfg["model"], providers=provs)

            # Detect the provider actually used (shared helper)
            used = ort_utils.session_providers(self.model)
            self.on_gpu = any("CUDA" in p for p in used)
            log(i18n.t("running_on", dev="GPU (CUDA)" if self.on_gpu else "CPU", providers=used))

            # Warmup – the first inference compiles kernels (otherwise the first dictation is slow)
            log(i18n.t("warming_up"))
            warm = (0.01 * np.random.default_rng(0).standard_normal(self.samplerate)).astype("float32")
            t = time.perf_counter()
            self.transcribe(warm)
            log(i18n.t("model_ready", secs=time.perf_counter() - t))
        self.notify()

    def unload_model(self) -> None:
        """Free the model from memory (returns ~3.4 GB VRAM). Handy before gaming."""
        # _model_lock first so we can't null the model while a load/warmup is running.
        with self._model_lock:
            with self.lock:
                if self.recording or self.busy:
                    log(i18n.t("cant_unload"))
                    return
            if not self.loaded:
                return
            self.model = None
            gc.collect()
            log(i18n.t("unloaded"))
        self.notify()

    def transcribe(self, audio: np.ndarray) -> str:
        kwargs: dict = {}
        lang = self.cfg.get("language", "auto")
        if lang and lang != "auto":
            kwargs["language"] = lang
        # Output language: required by some models (Canary), ignored by others (Parakeet)
        target = self.cfg.get("target_language")
        if target:
            kwargs["target_language"] = target
        kwargs["pnc"] = bool(self.cfg.get("punctuation", True))
        result = self.model.recognize(audio, sample_rate=self.samplerate, **kwargs)
        if isinstance(result, list):
            result = result[0] if result else ""
        return (result or "").strip()

    # ---- recording ----
    def _audio_cb(self, indata, frames, time_info, status):
        if status:
            log(i18n.t("audio_status", status=status))
        self.frames.append(indata[:, 0].copy())

    def _teardown_stream(self) -> None:
        """Stop and close the input stream. Never raises (errors are logged)."""
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                log(i18n.t("stream_error", err=e))
            finally:
                self.stream = None

    def _resume_media(self) -> None:
        """Resume any media we paused for this recording."""
        if self._paused_media:
            media_control.resume(self._paused_media)
            self._paused_media = []

    def start_recording(self) -> None:
        # Pause playing media (YouTube, Spotify, ...) - resumed after recording ends
        if self.cfg.get("pause_media", True):
            self._paused_media = media_control.pause_playing()
            if self._paused_media:
                log(i18n.t("media_paused", apps=self._paused_media))
        try:
            self.frames = []
            self.stream = sd.InputStream(
                samplerate=self.samplerate, channels=1, dtype="float32",
                callback=self._audio_cb,
            )
            self.stream.start()
        except Exception:
            # Setup failed: don't leave media paused or a half-open stream behind
            self._teardown_stream()
            self._resume_media()
            raise
        self.recording = True
        beep(self.cfg["beep"], 880)
        log(i18n.t("recording"))
        self.notify()

    def stop_recording(self) -> None:
        self.recording = False
        self._teardown_stream()   # never raises
        self._resume_media()
        beep(self.cfg["beep"], 600)
        audio = np.concatenate(self.frames) if self.frames else np.zeros(0, dtype="float32")
        self.frames = []
        secs = len(audio) / self.samplerate
        log(i18n.t("rec_end", secs=secs))
        self.notify()
        threading.Thread(target=self._process, args=(audio,), daemon=True).start()

    def _process(self, audio: np.ndarray) -> None:
        if len(audio) < self.samplerate * 0.2:
            log(i18n.t("too_short"))
            self.busy = False
            self.notify()
            return
        try:
            if not self.loaded:
                log(i18n.t("reloading"))
                self.load_model()
            t = time.perf_counter()
            text = self.transcribe(audio)
            dt = time.perf_counter() - t
            if text:
                log(i18n.t("result", ms=dt * 1000, text=text))
                self.insert_text(text)
            else:
                log(i18n.t("result_empty", ms=dt * 1000))
        except Exception as e:
            log(i18n.t("transcribe_error", err=e))
        finally:
            self.busy = False
            self.notify()

    # ---- text insertion ----
    @staticmethod
    def _release_modifiers() -> None:
        """Wait for the user to release the hotkey modifiers, then release them for safety.

        Without this, when pressing Alt+. the Alt key is still held at paste time and
        Ctrl+V looks like Ctrl+Alt+V to the system → nothing is pasted.
        """
        mods = ("alt", "ctrl", "shift", "windows")
        deadline = time.time() + 0.7
        while time.time() < deadline:
            if not any(_is_pressed(m) for m in mods):
                break
            time.sleep(0.01)
        for m in mods:
            try:
                keyboard.release(m)
            except Exception:
                pass
        time.sleep(0.02)

    def insert_text(self, text: str) -> None:
        if self.cfg.get("append_space", True):
            text = text + " "
        self._release_modifiers()
        if self.cfg.get("paste_method", "clipboard") == "type":
            keyboard.write(text)
            return
        prev = None
        if self.cfg.get("restore_clipboard", True):
            try:
                prev = pyperclip.paste()
            except Exception:
                prev = None
        pyperclip.copy(text)
        time.sleep(0.05)
        keyboard.send("ctrl+v")
        if self.cfg.get("restore_clipboard", True):
            def restore():
                time.sleep(0.25)
                try:
                    pyperclip.copy(prev if prev is not None else "")
                except Exception:
                    pass
            threading.Thread(target=restore, daemon=True).start()

    # ---- toggle ----
    def toggle(self) -> None:
        with self.lock:
            if not self.enabled:
                return
            if self.busy:
                log(i18n.t("busy"))
                return
            try:
                if not self.recording:
                    self.start_recording()
                else:
                    self.busy = True
                    self.stop_recording()
            except Exception as e:
                # A teardown/setup failure must never wedge the toggle permanently
                log(i18n.t("stream_error", err=e))
                self.busy = False
                self.notify()

    def set_enabled(self, value: bool) -> None:
        with self.lock:
            self.enabled = value
            if not value and self.recording:
                # cancel ongoing recording without transcribing
                self.recording = False
                self._teardown_stream()
                self.frames = []
                self._resume_media()
        log(i18n.t("dictation_on") if value else i18n.t("dictation_off"))
        self.notify()

    def _persist_model(self, name: str) -> None:
        path = BASE / "config.toml"
        try:
            path.write_text(
                config_utils.set_model_in_toml(path.read_text(encoding="utf-8"), name),
                encoding="utf-8",
            )
        except Exception as e:
            log(i18n.t("persist_error", err=e))

    def set_model(self, name: str) -> None:
        """Switch the active ASR model (unload old, load new) and remember the choice."""
        if name == self.cfg.get("model"):
            return
        with self.lock:
            if self.recording or self.busy:
                log(i18n.t("cant_switch"))
                return
        log(i18n.t("model_switched", model=name))
        self.unload_model()
        self.cfg["model"] = name
        self._persist_model(name)
        self.notify()
        self.load_model()


# ---- system tray icon ----
# Single source of truth for tray state -> (icon color, i18n status-label key).
TRAY_STATES = {
    "recording":    ((244, 67, 54),   "st_recording"),    # red
    "paused":       ((255, 152, 0),   "st_paused"),       # orange
    "transcribing": ((76, 175, 80),   "st_transcribing"),  # green (busy, working)
    "ready":        ((76, 175, 80),   "st_ready"),         # green
    "unloaded":     ((130, 130, 130), "st_unloaded"),      # grey
}


def make_icon(color: tuple) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, 60, 60), fill=color)
    white = (255, 255, 255, 255)
    d.rounded_rectangle((26, 16, 38, 38), radius=6, fill=white)       # mic body
    d.arc((20, 18, 44, 46), start=10, end=170, fill=white, width=3)   # mic holder
    d.line((32, 46, 32, 52), fill=white, width=3)                     # stem
    d.line((24, 52, 40, 52), fill=white, width=3)                     # base
    return img


def current_state(d: "Dictator") -> str:
    if not d.enabled:
        return "paused"
    if d.recording:
        return "recording"
    if d.busy:
        return "transcribing"
    if not d.loaded:
        return "unloaded"
    return "ready"


class Tray:
    def __init__(self, d: Dictator, cfg: dict):
        self.d = d
        self.cfg = cfg
        self._icons = {k: make_icon(color) for k, (color, _) in TRAY_STATES.items()}
        self.icon = pystray.Icon(
            "voicetype", self._icons[current_state(d)],
            "voicetype-win", menu=self._menu(),
        )
        d.on_state = self.refresh

    def _menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(self._status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda i: i18n.t("menu_pause") if self.d.enabled else i18n.t("menu_resume"),
                self._on_pause,
            ),
            pystray.MenuItem(
                lambda i: i18n.t("menu_unload") if self.d.loaded else i18n.t("menu_load"),
                self._on_unload_toggle,
            ),
            pystray.MenuItem(lambda i: i18n.t("menu_model"), self._model_menu()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda i: i18n.t("menu_quit"), self._on_quit),
        )

    def _model_menu(self) -> pystray.Menu:
        items = []
        for name in self.cfg.get("models", []):
            items.append(pystray.MenuItem(
                name.replace("nemo-", ""),
                self._make_model_setter(name),
                checked=self._make_model_checker(name),
                radio=True,
            ))
        return pystray.Menu(*items)

    def _make_model_setter(self, name: str):
        # Switch on a worker thread so the click returns immediately (load can take seconds)
        def cb(icon, item):
            threading.Thread(target=lambda: self.d.set_model(name), daemon=True).start()
        return cb

    def _make_model_checker(self, name: str):
        return lambda item: self.d.cfg.get("model") == name

    def _status_text(self, item) -> str:
        d = self.d
        label = TRAY_STATES[current_state(d)][1]
        dev = "GPU" if d.on_gpu else "CPU"
        return i18n.t("tray_status", st=i18n.t(label), dev=dev, hotkey=self.cfg["hotkey"].upper())

    def refresh(self) -> None:
        self.icon.icon = self._icons[current_state(self.d)]
        try:
            self.icon.update_menu()
        except Exception:
            pass

    def _on_pause(self, icon, item) -> None:
        self.d.set_enabled(not self.d.enabled)

    def _on_unload_toggle(self, icon, item) -> None:
        target = self.d.unload_model if self.d.loaded else self.d.load_model
        threading.Thread(target=target, daemon=True).start()

    def _on_quit(self, icon, item) -> None:
        log(i18n.t("quitting"))
        try:
            keyboard.clear_all_hotkeys()
        except Exception:
            pass
        icon.stop()
        os._exit(0)

    def run(self) -> None:
        self.icon.run()


def main() -> None:
    cfg = load_config()
    i18n.set_language(cfg.get("ui_language", "auto"))
    log(i18n.t("config", hotkey=cfg["hotkey"], language=cfg["language"],
               punctuation=cfg["punctuation"], device=cfg["device"]))
    d = Dictator(cfg)
    d.load_model()

    keyboard.add_hotkey(cfg["hotkey"], d.toggle, suppress=False)
    log(i18n.t("ready", hotkey=cfg["hotkey"].upper()))

    tray = Tray(d, cfg)
    tray.run()  # blocks the main thread until "Quit"


if __name__ == "__main__":
    main()
