import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Any

import time

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


def write(file: Path, modes: List[str], status: str, timestamp: float = None) -> None:
    """
    Writes the given timestamp, status and modes into a JSON file.

    :param file: Path to the target file
    :param modes: list of modes
    :param status: status
    :param timestamp: timestamp, defaults to the current timestamp
    """

    if timestamp is None:  # fix: can't put directly time.time() as a default value (see https://stackoverflow.com/questions/1132941)
        timestamp = time.time()

    file.write_text(
        json.dumps(
            {
                "timestamp": datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
                "status": status,
                "modes": modes
            }, indent=2
        ), encoding=ENCODING  # todo: can't seem to be able to properly test the encoding
    )


def ignore(*_: Any, **__: Any) -> None:
    """
    Dummy function that does absolutely nothing.
    """

    pass


def is_ko(status_file: Path):
    try:
        return json.loads(status_file.read_text(encoding=ENCODING)).get("status") == "ko"
    except (OSError, ValueError):
        return False
