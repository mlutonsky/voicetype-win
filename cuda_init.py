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

_initialized = False  # the DLL directories only need to be registered once per process


def init_cuda() -> bool:
    """Add the nvidia\\*\\bin directories to the DLL search path. Returns True if any were found.

    Idempotent: the expensive/leaky work (add_dll_directory, PATH edits) runs only on
    the first successful call, so repeated model reloads don't grow PATH unbounded.
    """
    global _initialized
    if _initialized:
        return True
    nvidia = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    found = False
    if nvidia.is_dir():
        path_entries = os.environ.get("PATH", "").split(os.pathsep)
        for bin_dir in sorted(nvidia.glob("*/bin")):
            s = str(bin_dir)
            try:
                os.add_dll_directory(s)
                # also to PATH, for dependencies resolved the classic way (dedup)
                if s not in path_entries:
                    os.environ["PATH"] = s + os.pathsep + os.environ.get("PATH", "")
                    path_entries.append(s)
                found = True
            except OSError:
                pass
    try:
        import onnxruntime as ort
        ort.preload_dlls()
    except Exception:
        pass
    if found:
        _initialized = True
    return found


if __name__ == "__main__":
    print("init_cuda():", init_cuda())
