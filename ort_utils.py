"""Small ONNX Runtime helpers shared by the app and the diagnostics."""


def session_providers(model) -> list[str]:
    """Best-effort discovery of the execution providers a loaded onnx-asr model uses.

    Walks the model's attributes for onnxruntime InferenceSession objects and
    returns their providers (e.g. ['CUDAExecutionProvider', 'CPUExecutionProvider']).
    """
    import onnxruntime as ort

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

    return walk(model) or ["<unknown>"]
