import datetime
import json
from pathlib import Path

ENCODING = "utf-8"


def write_file(file: Path, modes, status, utc=datetime.datetime.utcnow().isoformat()):
    file.write_text(json.dumps({
        "utc": utc,
        "status": status,
        "modes": modes
    }, indent=2), encoding=ENCODING)


def do_nothing(status):
    pass


def is_file_ko(file: Path):
    try:
        if json.loads(file.read_text(encoding=ENCODING)).get("status") == "ko":
            return True
    except (OSError, ValueError):
        pass
