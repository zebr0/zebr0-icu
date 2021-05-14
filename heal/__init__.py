import argparse
import datetime
import json
import pathlib
import signal
import subprocess
import threading
from operator import itemgetter
from pathlib import Path
from typing import List, Any, Tuple

import yaml

ENCODING = "utf-8"


def read_config(directory: Path) -> List[Any]:
    print("reading configuration")
    config = []

    for path in directory.iterdir():
        try:
            text = path.read_text(encoding=ENCODING)
        except (OSError, ValueError) as error:
            print(f"'{path.relative_to(directory)}' ignored: {error}")
            continue

        data = yaml.load(text, Loader=yaml.BaseLoader)
        if not isinstance(data, list):
            print(f"'{path.relative_to(directory)}' ignored: not a proper yaml or json list")
        else:
            config.extend(data)

    print("done")
    return config


def filter_modes_and_checks(config: List[Any]) -> Tuple[List[dict], List[dict]]:
    print("filtering modes and checks")
    modes, checks = [], []

    for item in config:
        if not isinstance(item, dict):
            print("ignored, not a dictionary:", json.dumps(item))
            continue

        if not all(isinstance(value, str) for value in item.values()):
            print("ignored, values cannot be lists or dictionaries:", json.dumps(item))
            continue

        keys = item.keys()
        if keys == {"mode", "if"}:  # "mode" and "if" are mandatory
            modes.append(item)
        elif keys == {"check", "fix", "rank"} or keys == {"check", "fix", "rank", "when"}:  # "when" is optional
            try:
                item["rank"] = int(item["rank"])  # converts the rank to an integer so that checks can be sorted
                checks.append(item)
            except ValueError:
                print("ignored, rank must be an integer:", json.dumps(item))
        else:
            print('ignored, keys must match {"mode", "if"} or {"check", "fix", "rank"} or {"check", "fix", "rank", "when"}:', json.dumps(item))

    print("done")
    return sorted(modes, key=itemgetter("mode")), sorted(checks, key=itemgetter("rank"))


def filter_current_modes(modes):
    return [mode.get("mode") for mode in modes if subprocess.run(mode.get("if"), shell=True).returncode == 0]


def filter_current_checks(current_modes, checks):
    print("filtering current checks")
    current_checks = []

    for check in checks:
        if not check.get("when") or check.get("when") in current_modes:
            print("active:", json.dumps(check))
            current_checks.append(check)

    print("done")
    return current_checks


class Watcher:
    def __init__(self, directory):
        self.directory = directory
        self.mtime = 0
        self.modes = []
        self.checks = []
        self.current_modes = []
        self.current_checks = []

    def directory_has_changed(self):
        new_mtime = self.directory.stat().st_mtime
        if new_mtime == self.mtime:
            return False
        print("configuration directory has changed")
        self.mtime = new_mtime
        return True

    def checks_have_changed(self):
        self.modes, new_checks = filter_modes_and_checks(read_config(self.directory))
        if new_checks == self.checks:
            return False
        print("checks have changed")
        self.checks = new_checks
        return True

    def current_modes_have_changed(self):
        new_current_modes = filter_current_modes(self.modes)
        if new_current_modes == self.current_modes:
            return False
        print("current modes have changed:", new_current_modes)
        self.current_modes = new_current_modes
        return True

    def refresh_current_checks_if_necessary(self):
        if (self.directory_has_changed() and self.checks_have_changed()) | self.current_modes_have_changed():
            self.current_checks = filter_current_checks(self.current_modes, self.checks)
        return self.current_checks


def write_file(file: Path, status, modes, utc=datetime.datetime.utcnow().isoformat()):
    file.write_text(json.dumps({
        "utc": utc,
        "status": status,
        "modes": modes
    }, indent=2), encoding=ENCODING)


def try_checks(checks, file, modes, delay=10, first_recursion=False):
    for i, check in enumerate(checks):
        test = check.get("check")
        cp = subprocess.run(test, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding=ENCODING)
        if cp.returncode == 0:
            continue

        fix, rank = check.get("fix"), check.get("rank")
        print(f"[{rank}] failed({cp.returncode}): {test}")
        for line in cp.stdout.splitlines():
            print(f"[{rank}] output: {line}")

        print(f"[{rank}] fixing: {fix}")
        if first_recursion:
            write_file(file, "fixing", modes)

        sp = subprocess.Popen(fix, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding=ENCODING)
        threading.Thread(target=lambda: [print(f"[{rank}] output: {line}", end="") for line in sp.stdout]).start()

        while True:
            try:
                if sp.wait(delay) != 0:
                    print(f"[{rank}] warning! fix returned code {sp.returncode}")
                break
            except subprocess.TimeoutExpired:
                try_checks(checks[:i], file, modes, delay)

        cp = subprocess.run(test, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding=ENCODING)
        if cp.returncode != 0:
            print(f"[{rank}] failed({cp.returncode}): {test}")
            for line in cp.stdout.splitlines():
                print(f"[{rank}] output: {line}")
            raise ChildProcessError()

        print(f"[{rank}] fix successful")

    if first_recursion:
        write_file(file, "ok", modes)


def is_file_ko(file: Path):
    try:
        if json.loads(file.read_text(encoding=ENCODING)).get("status") == "ko":
            return True
    except (OSError, ValueError):
        pass


def heal(directory: Path, file, event, delay=10):
    if is_file_ko(file):
        print("system already in failed status, exiting")
        return

    if not directory.is_dir():
        print("directory must exist")
        return

    print("watching configuration directory:", directory)
    watcher = Watcher(directory)

    try:
        while True:
            try_checks(watcher.refresh_current_checks_if_necessary(), file, watcher.current_modes, delay, True)
            if event.wait(delay):
                break
    except ChildProcessError:
        write_file(file, "ko", watcher.current_modes)
        print("critical failure, exiting")


def main(args=None):
    argparser = argparse.ArgumentParser(description="")
    argparser.add_argument("-d", "--directory", type=pathlib.Path, default=pathlib.Path("/etc/heald"), help="")
    argparser.add_argument("-f", "--file", type=pathlib.Path, default=pathlib.Path("/var/heald/status.json"), help="")
    argparser.add_argument("-t", "--time", type=float, default=10, help="")
    args = argparser.parse_args(args)

    event = threading.Event()

    # handles signals properly
    for sig in [signal.SIGINT, signal.SIGTERM]:
        signal.signal(sig, lambda signum, frame: event.set())

    heal(args.directory, args.file, event, args.time)
