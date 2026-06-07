"""Expose the CUDA/cuDNN DLLs from the installed nvidia-*-cu12 pip packages.

onnxruntime-gpu bundles neither CUDA nor cuDNN. The nvidia-*-cu12 packages provide
them under site-packages\\nvidia\\<lib>\\bin, but at runtime Windows won't find them
(especially the lazily-loaded cuDNN engine sublibraries) unless they are on the
DLL search path.

Call init_cuda() BEFORE creating an onnxruntime InferenceSession.
"""
import os
import sys
from pathlib import Path


def init_cuda() -> bool:
    """Add the nvidia\\*\\bin directories to the DLL search path. Returns True if any were found."""
    nvidia = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    found = False
    if nvidia.is_dir():
        for bin_dir in sorted(nvidia.glob("*/bin")):
            try:
                os.add_dll_directory(str(bin_dir))
                # also to PATH, for dependencies resolved the classic way
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
