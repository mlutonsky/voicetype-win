"""Zpřístupní CUDA/cuDNN DLL z nainstalovaných nvidia-*-cu12 pip balíčků.

onnxruntime-gpu nebundluje CUDA ani cuDNN. Balíčky nvidia-*-cu12 je dodají do
site-packages\\nvidia\\<lib>\\bin, ale Windows je při běhu (hlavně lazy-loadované
cuDNN engine sublibrary) nenajde, dokud nejsou na DLL search path.

Zavolej init_cuda() PŘED vytvořením onnxruntime InferenceSession.
"""
import os
import sys
from pathlib import Path


def init_cuda() -> bool:
    """Přidá nvidia\\*\\bin adresáře na DLL search path. Vrací True, pokud nějaké našel."""
    nvidia = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    found = False
    if nvidia.is_dir():
        for bin_dir in sorted(nvidia.glob("*/bin")):
            try:
                os.add_dll_directory(str(bin_dir))
                # i do PATH, kvůli závislostem hledaným klasickým způsobem
                os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
                found = True
            except OSError:
                pass
    try:
        import onnxruntime as ort
        ort.preload_dlls()
    except Exception:
        pass
    return found


if __name__ == "__main__":
    print("init_cuda():", init_cuda())
