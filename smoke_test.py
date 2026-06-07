"""Diagnostics: verify the GPU (CUDA), download the model (from config.toml) and
measure transcription latency. Messages follow the system locale (see i18n.py).

Run:
    .venv\\Scripts\\python.exe smoke_test.py
"""
import sys
import time
import tomllib
from pathlib import Path

import numpy as np

import i18n
from cuda_init import init_cuda
from ort_utils import session_providers

# The Windows console is often cp1250 – switch output to UTF-8 to be safe
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_cfg_path = Path(__file__).resolve().parent / "config.toml"
MODEL = "nemo-parakeet-tdt-0.6b-v3"
_ui = "auto"
if _cfg_path.is_file():
    with open(_cfg_path, "rb") as _f:
        _cfg = tomllib.load(_f)
        MODEL = _cfg.get("model", MODEL)
        _ui = _cfg.get("ui_language", "auto")
i18n.set_language(_ui)

# Expose CUDA/cuDNN DLLs (must happen before creating a session)
print("init_cuda():", init_cuda())

import onnxruntime as ort

print(f"onnxruntime {ort.__version__}")
print(i18n.t("sm_providers", providers=ort.get_available_providers()))

import onnx_asr

PROVIDERS = ["CUDAExecutionProvider", "CPUExecutionProvider"]

print("\n" + i18n.t("sm_loading", model=MODEL))
t0 = time.perf_counter()
model = onnx_asr.load_model(MODEL, providers=PROVIDERS)
print(i18n.t("sm_loaded_in", secs=time.perf_counter() - t0))

# Detect which provider the encoder actually runs on (shared helper)
used = session_providers(model)
print(i18n.t("sm_session", providers=used))
on_gpu = any("CUDA" in p for p in used)
print(i18n.t("sm_running_on", dev="GPU (CUDA)" if on_gpu else "CPU"))

# Pipeline test: 2 s of silence at 16 kHz (checks the pipeline doesn't crash + latency)
print("\n" + i18n.t("sm_test"))
audio = np.zeros(16000 * 2, dtype=np.float32)
t0 = time.perf_counter()
result = model.recognize(audio, sample_rate=16000)
dt = time.perf_counter() - t0
print(i18n.t("sm_result", result=result))
print(i18n.t("sm_latency", ms=dt * 1000))
print("\n" + i18n.t("sm_done"))
