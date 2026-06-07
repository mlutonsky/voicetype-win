"""Regression guard: Windows scripts must stay ASCII.

Windows PowerShell 5.1 reads BOM-less .ps1 files as the ANSI code page (e.g.
cp1250). A non-ASCII byte (such as an en-dash) can then be misdecoded into a
quote character and break parsing. Keeping .ps1/.cmd/.vbs ASCII avoids that.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = [
    "install.ps1", "install-autostart.ps1",
    "install.cmd", "install-autostart.cmd",
    "start-dictation.vbs",
]


def test_windows_scripts_are_ascii():
    offenders = {}
    for name in SCRIPTS:
        data = (ROOT / name).read_bytes()
        bad = [(i, b) for i, b in enumerate(data) if b > 0x7F]
        if bad:
            offenders[name] = bad[:5]
    assert not offenders, f"non-ASCII bytes found in: {offenders}"
