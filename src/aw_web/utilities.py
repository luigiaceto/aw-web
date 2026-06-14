import subprocess
from collections import defaultdict
from typing import Any

config_data: defaultdict[str, dict[str, Any]] = defaultdict(dict)

def get_os() -> str:
    """Return the current platform name with Android/WSL detection."""
    result = subprocess.run(["uname", "-a"], capture_output=True, text=True, check=False)
    out = result.stdout.strip().split()
    if not out:
        return "Unknown"
    os_name = out[0]
    if os_name == "Linux":
        if "Android" == out[-1]:
            os_name = "Android"
        elif len(out) > 2 and "WSL" in out[2]:
            os_name = "WSL"
    return os_name

os_name = get_os()

def sanitize_filename(filename: str) -> str:
    """
    Sanitizza il nome del file rimuovendo i caratteri non validi.

    Args:
        filename (str): il nome del file da sanitizzare.

    Returns:
        str: il nome del file sanitizzato.
    """
    if os_name != "Android":
        return filename

    forbidden_char = '"*/:<>?\\|'
    replace_char = '”⁎∕꞉‹›︖＼⏐'
    for a, b in zip(forbidden_char, replace_char):
        filename = filename.replace(a, b)
    return filename
