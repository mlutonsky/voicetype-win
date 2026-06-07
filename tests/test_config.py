"""config.toml must be valid TOML and contain the documented keys."""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = {
    "hotkey", "model", "models", "device", "language", "target_language",
    "ui_language", "punctuation", "append_space", "beep", "paste_method",
    "restore_clipboard", "pause_media",
}


def test_active_model_is_in_models_list():
    import tomllib
    with open(ROOT / "config.toml", "rb") as f:
        cfg = tomllib.load(f)
    assert cfg["model"] in cfg["models"], "active model must be one of the offered models"


def test_config_parses_and_has_required_keys():
    with open(ROOT / "config.toml", "rb") as f:
        cfg = tomllib.load(f)
    missing = REQUIRED - set(cfg)
    assert not missing, f"config.toml missing keys: {missing}"
