"""Localize the app's texts according to the system locale.

The default language is English; if Windows is in Czech (or the config forces
`ui_language = "cs"`) the Czech texts are used. Easy to extend with more languages.
"""
import ctypes

_LANG = "en"

# Key -> {lang: template}; templates support str.format(**kwargs)
_STRINGS = {
    # --- log / console ---
    "config": {
        "en": "Config: hotkey={hotkey}, language={language}, punctuation={punctuation}, device={device}",
        "cs": "Konfigurace: zkratka={hotkey}, jazyk={language}, interpunkce={punctuation}, device={device}",
    },
    "ready": {
        "en": "Ready. Hotkey: {hotkey}  |  Control it from the tray icon.",
        "cs": "Připraveno. Zkratka: {hotkey}  |  Ovládání přes ikonu v liště.",
    },
    "loading_model": {
        "en": "Loading model {model} (providers: {providers}) ...",
        "cs": "Načítám model {model} (provideři: {providers}) ...",
    },
    "running_on": {
        "en": "Running on: {dev}  {providers}",
        "cs": "Běží na: {dev}  {providers}",
    },
    "warming_up": {"en": "Warming up the model ...", "cs": "Zahřívám model ..."},
    "model_ready": {
        "en": "Model ready (warmup {secs:.1f} s)",
        "cs": "Model připraven (warmup {secs:.1f} s)",
    },
    "cant_unload": {
        "en": "Can't unload – recording/transcription in progress. Try again shortly.",
        "cs": "Nelze uvolnit – probíhá nahrávání/přepis. Zkus to za chvíli.",
    },
    "unloaded": {
        "en": "Model unloaded from memory (VRAM freed). It will reload on the next dictation.",
        "cs": "Model uvolněn z paměti (VRAM vrácena). Načte se znovu při dalším diktování.",
    },
    "too_short": {"en": "Too short, ignoring.", "cs": "Příliš krátké, ignoruji."},
    "reloading": {
        "en": "Model was unloaded – reloading ...",
        "cs": "Model byl uvolněn – načítám zpět ...",
    },
    "result": {"en": "→ ({ms:.0f} ms) {text!r}", "cs": "→ ({ms:.0f} ms) {text!r}"},
    "result_empty": {
        "en": "→ ({ms:.0f} ms) empty (silence?)",
        "cs": "→ ({ms:.0f} ms) prázdné (ticho?)",
    },
    "transcribe_error": {"en": "Transcription error: {err}", "cs": "Chyba přepisu: {err}"},
    "media_paused": {"en": "Paused media: {apps}", "cs": "Pozastaveno přehrávání: {apps}"},
    "recording": {
        "en": "● Recording ... (press the hotkey again to stop)",
        "cs": "● Nahrávám ... (stiskni zkratku znovu pro konec)",
    },
    "rec_end": {
        "en": "■ Stop ({secs:.1f} s), transcribing ...",
        "cs": "■ Konec ({secs:.1f} s), přepisuji ...",
    },
    "busy": {
        "en": "Transcription still running, wait a moment ...",
        "cs": "Přepis ještě běží, počkej chvíli ...",
    },
    "dictation_on": {"en": "Dictation resumed.", "cs": "Diktování obnoveno."},
    "dictation_off": {"en": "Dictation paused.", "cs": "Diktování pozastaveno."},
    "audio_status": {"en": "audio status: {status}", "cs": "audio status: {status}"},
    "stream_error": {"en": "Audio stream error: {err}", "cs": "Chyba audio streamu: {err}"},
    "quitting": {"en": "Quitting ...", "cs": "Ukončuji aplikaci ..."},
    "model_switched": {"en": "Switching model to {model} ...", "cs": "Přepínám model na {model} ..."},
    "cant_switch": {
        "en": "Can't switch the model while recording/transcribing.",
        "cs": "Nelze přepnout model během nahrávání/přepisu.",
    },
    "persist_error": {"en": "Could not save config: {err}", "cs": "Nepodařilo se uložit config: {err}"},
    # --- tray menu ---
    "menu_pause": {"en": "Pause dictation", "cs": "Pozastavit diktování"},
    "menu_resume": {"en": "Resume dictation", "cs": "Obnovit diktování"},
    "menu_unload": {"en": "Unload model from memory (GPU)", "cs": "Uvolnit model z paměti (GPU)"},
    "menu_load": {"en": "Load model into memory", "cs": "Načíst model do paměti"},
    "menu_quit": {"en": "Quit", "cs": "Ukončit"},
    "menu_model": {"en": "Model", "cs": "Model"},
    # --- tray status ---
    "st_recording": {"en": "recording", "cs": "nahrává"},
    "st_paused": {"en": "paused", "cs": "pozastaveno"},
    "st_transcribing": {"en": "transcribing", "cs": "přepisuje"},
    "st_ready": {"en": "ready", "cs": "připraveno"},
    "st_unloaded": {"en": "model unloaded", "cs": "model uvolněn"},
    "tray_status": {
        "en": "voicetype-win – {st} ({dev}) · {hotkey}",
        "cs": "voicetype-win – {st} ({dev}) · {hotkey}",
    },
    # --- smoke_test.py ---
    "sm_providers": {"en": "Available providers: {providers}", "cs": "Dostupní provideři: {providers}"},
    "sm_loading": {
        "en": "Loading model {model} (downloads ~1 GB on first run) ...",
        "cs": "Načítám model {model} (poprvé se stáhne ~1 GB) ...",
    },
    "sm_loaded_in": {"en": "Model loaded in {secs:.1f} s", "cs": "Model načten za {secs:.1f} s"},
    "sm_session": {"en": "Session providers: {providers}", "cs": "Session provideři: {providers}"},
    "sm_running_on": {"en": "==> Running on: {dev}", "cs": "==> Běží na: {dev}"},
    "sm_test": {
        "en": "Transcription test (2 s of silence) ...",
        "cs": "Test přepisu (2 s ticha) ...",
    },
    "sm_result": {"en": "Result: {result!r}", "cs": "Výsledek: {result!r}"},
    "sm_latency": {"en": "Latency for 2 s of audio: {ms:.0f} ms", "cs": "Latence přepisu 2 s audia: {ms:.0f} ms"},
    "sm_done": {
        "en": "Done. If it says GPU (CUDA) above, everything is ready.",
        "cs": "Hotovo. Pokud je výše GPU (CUDA), je vše připraveno.",
    },
    # --- selftest.py ---
    "sf_a": {"en": "=== A) Microphone capture (2 s) ===", "cs": "=== A) Zachycení zvuku z mikrofonu (2 s) ==="},
    "sf_a_res": {"en": "Samples: {n}, RMS: {rms:.5f}  -> {verdict}", "cs": "Vzorků: {n}, RMS: {rms:.5f}  -> {verdict}"},
    "sf_mic_ok": {"en": "microphone is capturing", "cs": "mikrofon zachytává"},
    "sf_mic_silent": {"en": "SILENCE / mic?", "cs": "TICHO / mikrofon?"},
    "sf_b": {
        "en": "=== B) Transcribe captured audio (no-crash test) ===",
        "cs": "=== B) Přepis zachyceného audia (jen test, že nespadne) ===",
    },
    "sf_b_res": {"en": "({ms:.0f} ms) result: {text!r}", "cs": "({ms:.0f} ms) výsledek: {text!r}"},
    "sf_c": {
        "en": "=== C) Clipboard – Unicode round-trip (accents) ===",
        "cs": "=== C) Schránka – unicode round-trip (česká diakritika) ===",
    },
    "sf_c_res": {"en": "OK: {ok}  ({back!r})", "cs": "OK: {ok}  ({back!r})"},
    "sf_d": {
        "en": "=== D) Toggle chain (record->stop->transcribe->insert), insertion captured ===",
        "cs": "=== D) Toggle řetězec (record→stop→přepis→vložení), vložení odchyceno ===",
    },
    "sf_d_res": {"en": "busy={busy}, would insert: {captured!r}", "cs": "busy={busy}, vloženo by se: {captured!r}"},
    "sf_done": {
        "en": "Done. For a speech test, run dictate.py and talk.",
        "cs": "Hotovo. Pro test s řečí spusť dictate.py a mluv.",
    },
}


def detect_language() -> str:
    """Return 'cs' for a Czech Windows locale, otherwise 'en'."""
    try:
        buf = ctypes.create_unicode_buffer(85)
        if ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, 85) and buf.value:
            if buf.value.lower().startswith("cs"):
                return "cs"
            return "en"
    except Exception:
        pass
    try:
        # Fallback: LANGID, primary language 0x05 = Czech
        if (ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF) == 0x05:
            return "cs"
    except Exception:
        pass
    return "en"


def set_language(ui_language: str = "auto") -> str:
    """Set the language: 'en'/'cs' to force it, anything else = auto-detect."""
    global _LANG
    _LANG = ui_language if ui_language in ("en", "cs") else detect_language()
    return _LANG


def current() -> str:
    return _LANG


def t(key: str, **kwargs) -> str:
    entry = _STRINGS.get(key, {})
    template = entry.get(_LANG) or entry.get("en") or key
    try:
        return template.format(**kwargs)
    except Exception:
        return template


# Default: detect from the system already at import time (config can override via set_language).
set_language("auto")
