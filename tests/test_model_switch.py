"""Tests for the config model-persistence helper (no heavy deps)."""
from config_utils import set_model_in_toml


def test_replaces_only_active_model_key():
    text = 'model = "old"\nmodels = ["a", "b"]\n# keep me\n'
    out = set_model_in_toml(text, "new")
    assert 'model = "new"' in out
    assert 'models = ["a", "b"]' in out   # the list must stay untouched
    assert "# keep me" in out             # comments preserved
    assert out.count('model = "new"') == 1


def test_appends_when_no_model_key():
    out = set_model_in_toml('language = "auto"\n', "x")
    assert 'model = "x"' in out
    assert 'language = "auto"' in out


def test_preserves_trailing_newline():
    assert set_model_in_toml('model = "a"\n', "b").endswith("\n")
    assert not set_model_in_toml('model = "a"', "b").endswith("\n")
