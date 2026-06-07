"""Automatický self-test (bez nutnosti mluvit): mikrofon, přepis, schránka, toggle."""
import time
import numpy as np
import pyperclip

from dictate import Dictator, load_config

CZ = "Příliš žluťoučký kůň úpěl ďábelské ódy."

cfg = load_config()
d = Dictator(cfg)
d.load_model()

print("\n=== A) Zachycení zvuku z mikrofonu (2 s) ===")
import sounddevice as sd
rec = sd.rec(int(2 * 16000), samplerate=16000, channels=1, dtype="float32")
sd.wait()
audio = rec[:, 0]
rms = float(np.sqrt(np.mean(audio**2)))
print(f"Vzorků: {len(audio)}, RMS: {rms:.5f}  -> {'mikrofon zachytává' if rms > 1e-5 else 'TICHO / mikrofon?'}")

print("\n=== B) Přepis zachyceného audia (jen test, že nespadne) ===")
t = time.perf_counter()
text = d.transcribe(audio)
print(f"({(time.perf_counter()-t)*1000:.0f} ms) výsledek: {text!r}")

print("\n=== C) Schránka – unicode round-trip (česká diakritika) ===")
before = pyperclip.paste()
pyperclip.copy(CZ)
back = pyperclip.paste()
print(f"OK: {back == CZ}  ({back!r})")
pyperclip.copy(before if before is not None else "")

print("\n=== D) Toggle řetězec (record→stop→přepis→vložení), vložení odchyceno ===")
captured = []
d.insert_text = lambda s: captured.append(s)  # neposíláme Ctrl+V do terminálu
d.toggle()              # start
time.sleep(1.5)
d.toggle()              # stop -> spustí přepis ve vlákně
time.sleep(3.0)         # počkej na dokončení přepisu
print(f"busy={d.busy}, vloženo by se: {captured!r}")
print("\nHotovo. Pro test s řečí spusť dictate.py a mluv.")
