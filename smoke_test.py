"""Diagnostika: ověří GPU (CUDA), stáhne model (dle config.toml) a změří latenci přepisu.

Spuštění:
    .venv\\Scripts\\python.exe smoke_test.py
"""
import time
import tomllib
from pathlib import Path
import numpy as np
from cuda_init import init_cuda

_cfg_path = Path(__file__).resolve().parent / "config.toml"
MODEL = "nemo-parakeet-tdt-0.6b-v3"
if _cfg_path.is_file():
    with open(_cfg_path, "rb") as _f:
        MODEL = tomllib.load(_f).get("model", MODEL)

# Zpřístupni CUDA/cuDNN DLL (musí proběhnout před importem session)
print("init_cuda():", init_cuda())

import onnxruntime as ort

print(f"onnxruntime {ort.__version__}")
print("Dostupní provideři:", ort.get_available_providers())

import onnx_asr

PROVIDERS = ["CUDAExecutionProvider", "CPUExecutionProvider"]

print(f"\nNačítám model {MODEL} (poprvé se stáhne, ~1 GB)...")
t0 = time.perf_counter()
model = onnx_asr.load_model(MODEL, providers=PROVIDERS)
print(f"Model načten za {time.perf_counter() - t0:.1f} s")

# Zjisti, na čem reálně běží encoder
used = None
for attr in vars(model).values():
    sess = getattr(attr, "_session", None) or getattr(attr, "session", None)
    if isinstance(sess, ort.InferenceSession):
        used = sess.get_providers()
        break
# Hlubší hledání, pokud nahoře nenajdeme session
if used is None:
    def find_sessions(obj, depth=0, seen=None):
        if seen is None:
            seen = set()
        if id(obj) in seen or depth > 4:
            return []
        seen.add(id(obj))
        found = []
        for v in getattr(obj, "__dict__", {}).values():
            if isinstance(v, ort.InferenceSession):
                found.append(v.get_providers())
            else:
                found += find_sessions(v, depth + 1, seen)
        return found
    provs = find_sessions(model)
    used = provs[0] if provs else ["<neznámé>"]
print("Session provideři:", used)
on_gpu = any("CUDA" in p for p in used)
print(f"==> Běží na: {'GPU (CUDA)' if on_gpu else 'CPU'}")

# Pipeline test: 2 s ticha při 16 kHz (ověří, že přepis nespadne + latence)
print("\nTest přepisu (2 s ticha)...")
audio = np.zeros(16000 * 2, dtype=np.float32)
t0 = time.perf_counter()
result = model.recognize(audio, sample_rate=16000)
dt = time.perf_counter() - t0
print(f"Výsledek: {result!r}")
print(f"Latence přepisu 2 s audia: {dt*1000:.0f} ms")
print("\nHotovo. Pokud je výše GPU (CUDA), je vše připraveno.")
