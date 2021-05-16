import datetime
import json
import subprocess
from pathlib import Path

ENCODING = "utf-8"
SP_KWARGS = {"shell": True, "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "encoding": ENCODING}


def print_output(rank, header, command, lines):
    print(rank, header + ":", command)
    for line in lines:
        print(rank, "output:", line.rstrip())


def write(status_file: Path, current_modes, status, utc=datetime.datetime.utcnow()):
    status_file.write_text(json.dumps({"utc": utc.isoformat(), "status": status, "modes": current_modes}, indent=2), encoding=ENCODING)


def ignore(*_, **__):
    pass


def is_ko(status_file: Path):
    try:
        return json.loads(status_file.read_text(encoding=ENCODING)).get("status") == "ko"
    except (OSError, ValueError):
        return False
