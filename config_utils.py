"""Lightweight config helpers (no heavy deps, so tests/CI can import them freely)."""


def set_model_in_toml(text: str, name: str) -> str:
    """Return config text with the active `model = "..."` line set to name.

    Replaces only the `model` key (never the `models` list), preserving comments
    and indentation. Appends the line if no `model` key is present.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key == "model":
            indent = line[: len(line) - len(line.lstrip())]
            lines[i] = f'{indent}model = "{name}"'
            break
    else:
        lines.append(f'model = "{name}"')
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
