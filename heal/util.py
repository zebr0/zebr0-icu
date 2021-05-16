import datetime
import json
from pathlib import Path

ENCODING = "utf-8"


def write(status_file: Path, current_modes, status, utc=datetime.datetime.utcnow()):
    status_file.write_text(json.dumps({"utc": utc.isoformat(), "status": status, "modes": current_modes}, indent=2), encoding=ENCODING)


def ignore(*_, **__):
    pass


def is_ko(status_file: Path):
    try:
        return json.loads(status_file.read_text(encoding=ENCODING)).get("status") == "ko"
    except (OSError, ValueError):
        return False
