"""Lokalizace textů aplikace podle locale systému.

Výchozí jazyk je angličtina; pokud je Windows v češtině (nebo to vynutí config
`ui_language = "cs"`), použijí se české texty. Snadno rozšiřitelné o další jazyky.
"""
import ctypes

_LANG = "en"

# Klíč -> {jazyk: šablona}; šablony podporují str.format(**kwargs)
_STRINGS = {
    # --- log / konzole ---
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
    "quitting": {"en": "Quitting ...", "cs": "Ukončuji aplikaci ..."},
    # --- tray menu ---
    "menu_pause": {"en": "Pause dictation", "cs": "Pozastavit diktování"},
    "menu_resume": {"en": "Resume dictation", "cs": "Obnovit diktování"},
    "menu_unload": {"en": "Unload model from memory (GPU)", "cs": "Uvolnit model z paměti (GPU)"},
    "menu_load": {"en": "Load model into memory", "cs": "Načíst model do paměti"},
    "menu_quit": {"en": "Quit", "cs": "Ukončit"},
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
}


def detect_language() -> str:
    """Vrátí 'cs' pro českou Windows lokalizaci, jinak 'en'."""
    try:
        buf = ctypes.create_unicode_buffer(85)
        if ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, 85) and buf.value:
            if buf.value.lower().startswith("cs"):
                return "cs"
            return "en"
    except Exception:
        pass
    try:
        # Fallback: LANGID, primární jazyk 0x05 = čeština
        if (ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF) == 0x05:
            return "cs"
    except Exception:
        pass
    return "en"


def set_language(ui_language: str = "auto") -> str:
    """Nastaví jazyk: 'en'/'cs' napevno, cokoli jiného = auto-detekce."""
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


# Výchozí: detekuj podle systému už při importu (config to může přepsat přes set_language).
set_language("auto")
