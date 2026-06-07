"""Automatic self-test (no speaking needed): microphone, transcription, clipboard,
toggle chain. Messages follow the system locale (see i18n.py)."""
import time
import numpy as np
import pyperclip

from dictate import Dictator, load_config
import i18n

PANGRAM = "Příliš žluťoučký kůň úpěl ďábelské ódy."  # accents round-trip check

cfg = load_config()
i18n.set_language(cfg.get("ui_language", "auto"))
d = Dictator(cfg)
d.load_model()

print("\n" + i18n.t("sf_a"))
import sounddevice as sd
rec = sd.rec(int(2 * 16000), samplerate=16000, channels=1, dtype="float32")
sd.wait()
audio = rec[:, 0]
rms = float(np.sqrt(np.mean(audio**2)))
verdict = i18n.t("sf_mic_ok") if rms > 1e-5 else i18n.t("sf_mic_silent")
print(i18n.t("sf_a_res", n=len(audio), rms=rms, verdict=verdict))

print("\n" + i18n.t("sf_b"))
t = time.perf_counter()
text = d.transcribe(audio)
print(i18n.t("sf_b_res", ms=(time.perf_counter() - t) * 1000, text=text))

print("\n" + i18n.t("sf_c"))
before = pyperclip.paste()
pyperclip.copy(PANGRAM)
back = pyperclip.paste()
print(i18n.t("sf_c_res", ok=(back == PANGRAM), back=back))
pyperclip.copy(before if before is not None else "")

print("\n" + i18n.t("sf_d"))
captured = []
d.insert_text = lambda s: captured.append(s)  # don't send Ctrl+V into the terminal
d.toggle()              # start
time.sleep(1.5)
d.toggle()              # stop -> runs transcription in a thread
time.sleep(3.0)         # wait for it to finish
print(i18n.t("sf_d_res", busy=d.busy, captured=captured))
print("\n" + i18n.t("sf_done"))
