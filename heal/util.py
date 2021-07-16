import datetime
import json
import subprocess
from pathlib import Path
from typing import List

ENCODING = "utf-8"
SP_KWARGS = {"shell": True, "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "encoding": ENCODING}  # common parameters to subprocess commands


def print_output(command: str, result: str, output: List[str], prefix: str) -> None:
    """
    Provides a standard way to print the output of a command's execution.

    :param command: obviously
    :param result: describes the outcome of the command's execution
    :param output: execution's output lines
    :param prefix: prepended to all printed lines
    """

    print(prefix, result + ":", command)
    for line in output:
        print(prefix, "output:", line.rstrip())


def write(status_file: Path, current_modes, status, utc=None):
    if utc is None:  # fix: can't put directly datetime.datetime.utcnow() as a default value (see https://stackoverflow.com/questions/1132941)
        utc = datetime.datetime.utcnow()

    status_file.write_text(json.dumps({"utc": utc.isoformat(), "status": status, "modes": current_modes}, indent=2), encoding=ENCODING)


def ignore(*_, **__):
    pass


def is_ko(status_file: Path):
    try:
        return json.loads(status_file.read_text(encoding=ENCODING)).get("status") == "ko"
    except (OSError, ValueError):
        return False
