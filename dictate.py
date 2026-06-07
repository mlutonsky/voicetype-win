"""voicetype-win – lokální diktování řeči → text (jako Whisper Flow).

Přepis běží offline přes onnx-asr; model je volitelný (Parakeet, Canary, …) v config.toml.

Toggle režim: stiskni zkratku (výchozí Alt+.) pro start nahrávání, stiskni znovu
pro stop. Řeč se přepíše a text se vloží do aktivního okna.

Spuštění (s konzolí):  .venv\\Scripts\\python.exe dictate.py
Tiše na pozadí:        spusť start-dictation.vbs
"""
import sys
import os
import gc
import time
import threading
import tomllib
import winsound
from pathlib import Path

import numpy as np
import sounddevice as sd
import pyperclip
import keyboard
import pystray
from PIL import Image, ImageDraw

from cuda_init import init_cuda
import media_control

# Konzole na Windows bývá cp1250 – přepni výstup na UTF-8, ať nepadáme na ●/■/→/diakritice
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE = Path(__file__).resolve().parent
LOGFILE = BASE / "dictate.log"


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    # Konzole (pokud existuje – pod pythonw je sys.stdout None)
    try:
        if sys.stdout is not None:
            print(line, flush=True)
    except Exception:
        pass
    # Vždy i do logu (kvůli běhu na pozadí bez konzole)
    try:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_config() -> dict:
    cfg = {
        "hotkey": "alt+.",
        "model": "nemo-parakeet-tdt-0.6b-v3",
        "device": "auto",
        "language": "auto",
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
        self.busy = False  # probíhá přepis
        self.model = None
        self.enabled = True          # diktování aktivní (lze pozastavit z traye)
        self.on_state = None         # callback() při změně stavu (pro tray ikonu)
        self.on_gpu = False          # poslední známý stav (GPU/CPU)
        self._paused_media: list[str] = []  # přehrávače pozastavené na dobu nahrávání

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
        if self.loaded:
            return
        import onnx_asr
        if self.cfg["device"] != "cpu":
            init_cuda()
        provs = self.providers()
        log(f"Načítám model {self.cfg['model']} (provideři: {provs}) ...")
        self.model = onnx_asr.load_model(self.cfg["model"], providers=provs)

        # Zjisti reálně použitý provider
        import onnxruntime as ort
        used = self._session_providers(ort)
        self.on_gpu = any("CUDA" in p for p in used)
        log(f"Běží na: {'GPU (CUDA)' if self.on_gpu else 'CPU'}  {used}")

        # Warmup – první inference kompiluje kernely (jinak je první diktování pomalé)
        log("Zahřívám model ...")
        warm = (0.01 * np.random.default_rng(0).standard_normal(self.samplerate)).astype("float32")
        t = time.perf_counter()
        self.transcribe(warm)
        log(f"Model připraven (warmup {time.perf_counter()-t:.1f} s)")
        self.notify()

    def unload_model(self) -> None:
        """Uvolní model z paměti (vrátí ~3,4 GB VRAM). Vhodné před hraním her."""
        with self.lock:
            if self.recording or self.busy:
                log("Nelze uvolnit – probíhá nahrávání/přepis. Zkus to za chvíli.")
                return
            if not self.loaded:
                return
            self.model = None
            gc.collect()
            log("Model uvolněn z paměti (VRAM vrácena). Načte se znovu při dalším diktování.")
        self.notify()

    def _session_providers(self, ort) -> list[str]:
        seen: set[int] = set()

        def walk(obj, depth=0):
            if id(obj) in seen or depth > 5:
                return []
            seen.add(id(obj))
            out: list[str] = []
            for v in getattr(obj, "__dict__", {}).values():
                if isinstance(v, ort.InferenceSession):
                    out += v.get_providers()
                else:
                    out += walk(v, depth + 1)
            return out

        provs = walk(self.model)
        return provs or ["<neznámé>"]

    def transcribe(self, audio: np.ndarray) -> str:
        kwargs: dict = {}
        lang = self.cfg.get("language", "auto")
        if lang and lang != "auto":
            kwargs["language"] = lang
        kwargs["pnc"] = bool(self.cfg.get("punctuation", True))
        result = self.model.recognize(audio, sample_rate=self.samplerate, **kwargs)
        if isinstance(result, list):
            result = result[0] if result else ""
        return (result or "").strip()

    # ---- nahrávání ----
    def _audio_cb(self, indata, frames, time_info, status):
        if status:
            log(f"audio status: {status}")
        self.frames.append(indata[:, 0].copy())

    def start_recording(self) -> None:
        # Pozastav hrající média (YouTube, Spotify, ...) – obnoví se po konci nahrávání
        if self.cfg.get("pause_media", True):
            self._paused_media = media_control.pause_playing()
            if self._paused_media:
                log(f"Pozastaveno přehrávání: {self._paused_media}")
        self.frames = []
        self.stream = sd.InputStream(
            samplerate=self.samplerate, channels=1, dtype="float32",
            callback=self._audio_cb,
        )
        self.stream.start()
        self.recording = True
        beep(self.cfg["beep"], 880)
        log("● Nahrávám ... (stiskni zkratku znovu pro konec)")
        self.notify()

    def stop_recording(self) -> None:
        self.recording = False
        try:
            self.stream.stop()
            self.stream.close()
        finally:
            self.stream = None
        # Obnov dříve pozastavené přehrávače
        if self._paused_media:
            media_control.resume(self._paused_media)
            self._paused_media = []
        beep(self.cfg["beep"], 600)
        audio = np.concatenate(self.frames) if self.frames else np.zeros(0, dtype="float32")
        self.frames = []
        secs = len(audio) / self.samplerate
        log(f"■ Konec ({secs:.1f} s), přepisuji ...")
        self.notify()
        threading.Thread(target=self._process, args=(audio,), daemon=True).start()

    def _process(self, audio: np.ndarray) -> None:
        if len(audio) < self.samplerate * 0.2:
            log("Příliš krátké, ignoruji.")
            self.busy = False
            return
        try:
            if not self.loaded:
                log("Model byl uvolněn – načítám zpět ...")
                self.load_model()
            t = time.perf_counter()
            text = self.transcribe(audio)
            dt = time.perf_counter() - t
            if text:
                log(f"→ ({dt*1000:.0f} ms) {text!r}")
                self.insert_text(text)
            else:
                log(f"→ ({dt*1000:.0f} ms) prázdné (ticho?)")
        except Exception as e:
            log(f"Chyba přepisu: {e}")
        finally:
            self.busy = False
            self.notify()

    # ---- vložení textu ----
    @staticmethod
    def _release_modifiers() -> None:
        """Počká, až uživatel pustí modifikátory ze zkratky, a pro jistotu je uvolní.

        Bez toho je při stisku Alt+. v okamžiku vkládání Alt stále držený a Ctrl+V se
        systému jeví jako Ctrl+Alt+V → nevloží se nic.
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
                log("Přepis ještě běží, počkej chvíli ...")
                return
            if not self.recording:
                self.start_recording()
            else:
                self.busy = True
                self.stop_recording()

    def set_enabled(self, value: bool) -> None:
        with self.lock:
            self.enabled = value
            if not value and self.recording:
                # zruš probíhající nahrávání bez přepisu
                self.recording = False
                try:
                    if self.stream:
                        self.stream.stop()
                        self.stream.close()
                finally:
                    self.stream = None
                self.frames = []
                if self._paused_media:
                    media_control.resume(self._paused_media)
                    self._paused_media = []
        log("Diktování " + ("obnoveno." if value else "pozastaveno."))
        self.notify()


# ---- System tray ikona ----
TRAY_COLORS = {
    "recording": (244, 67, 54),   # červená – nahrává
    "paused": (255, 152, 0),      # oranžová – pozastaveno
    "unloaded": (130, 130, 130),  # šedá – model uvolněn z paměti
    "ready": (76, 175, 80),       # zelená – připraveno
}


def make_icon(color: tuple) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, 60, 60), fill=color)
    white = (255, 255, 255, 255)
    d.rounded_rectangle((26, 16, 38, 38), radius=6, fill=white)   # tělo mikrofonu
    d.arc((20, 18, 44, 46), start=10, end=170, fill=white, width=3)  # držák
    d.line((32, 46, 32, 52), fill=white, width=3)                 # nožka
    d.line((24, 52, 40, 52), fill=white, width=3)                 # podstavec
    return img


def state_key(d: "Dictator") -> str:
    if not d.enabled:
        return "paused"
    if d.recording:
        return "recording"
    if not d.loaded:
        return "unloaded"
    return "ready"


class Tray:
    def __init__(self, d: Dictator, cfg: dict):
        self.d = d
        self.cfg = cfg
        self._icons = {k: make_icon(c) for k, c in TRAY_COLORS.items()}
        self.icon = pystray.Icon(
            "voicetype", self._icons[state_key(d)],
            "voicetype-win", menu=self._menu(),
        )
        d.on_state = self.refresh

    def _menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(self._status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda i: "Pozastavit diktování" if self.d.enabled else "Obnovit diktování",
                self._on_pause,
            ),
            pystray.MenuItem(
                lambda i: "Uvolnit model z paměti (GPU)" if self.d.loaded else "Načíst model do paměti",
                self._on_unload_toggle,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Ukončit", self._on_quit),
        )

    def _status_text(self, item) -> str:
        d = self.d
        if d.recording:
            st = "nahrává"
        elif not d.enabled:
            st = "pozastaveno"
        elif d.busy:
            st = "přepisuje"
        elif d.loaded:
            st = "připraveno"
        else:
            st = "model uvolněn"
        dev = "GPU" if d.on_gpu else "CPU"
        return f"voicetype-win – {st} ({dev}) · {self.cfg['hotkey'].upper()}"

    def refresh(self) -> None:
        self.icon.icon = self._icons[state_key(self.d)]
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
        log("Ukončuji aplikaci ...")
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
    log(f"Konfigurace: zkratka={cfg['hotkey']}, jazyk={cfg['language']}, "
        f"interpunkce={cfg['punctuation']}, device={cfg['device']}")
    d = Dictator(cfg)
    d.load_model()

    keyboard.add_hotkey(cfg["hotkey"], d.toggle, suppress=False)
    log(f"Připraveno. Zkratka: {cfg['hotkey'].upper()}  |  Ovládání přes ikonu v liště.")

    tray = Tray(d, cfg)
    tray.run()  # blokuje hlavní vlákno až do „Ukončit"


if __name__ == "__main__":
    main()
