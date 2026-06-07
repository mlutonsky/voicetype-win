"""Tests for the i18n table: completeness and format-safety. No heavy deps needed."""
import i18n

# Every placeholder used by any template, with a value of a plausible type.
SAMPLE = dict(
    hotkey="ALT+.", language="auto", punctuation=True, device="auto",
    model="some-model", providers=["CPUExecutionProvider"], dev="GPU (CUDA)",
    secs=1.0, ms=42.0, text="hello", err="boom", apps=["Chrome"], status="x",
    st="ready", result="r", n=32000, rms=0.0061, verdict="ok", ok=True,
    back="clip", busy=False, captured=["hi"],
)


def test_every_key_has_en_and_cs():
    for key, entry in i18n._STRINGS.items():
        assert "en" in entry, f"{key} missing 'en'"
        assert "cs" in entry, f"{key} missing 'cs'"


def test_every_template_formats():
    """Each template must format with SAMPLE - catches unknown/typo placeholders."""
    for key, entry in i18n._STRINGS.items():
        for lang in ("en", "cs"):
            entry[lang].format(**SAMPLE)  # raises KeyError on an unknown placeholder


def test_set_language():
    assert i18n.set_language("en") == "en"
    assert i18n.set_language("cs") == "cs"
    assert i18n.set_language("auto") in ("en", "cs")


def test_detect_language_supported():
    assert i18n.detect_language() in ("en", "cs")


def test_t_falls_back_to_en_for_unknown_lang():
    i18n.set_language("en")
    assert i18n.t("warming_up") == i18n._STRINGS["warming_up"]["en"]
    i18n.set_language("auto")
