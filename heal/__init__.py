import json
import operator
import subprocess
import threading
from pathlib import Path

import yaml

ENCODING = "utf-8"


def read_config_from_disk(directory: Path):
    print("reading configuration from directory:", directory)
    config = []

    for path in directory.iterdir():
        try:
            text = path.read_text(encoding=ENCODING)
        except (OSError, ValueError) as e:
            print(path, "ignored:", e)
            continue

        data = yaml.load(text, Loader=yaml.BaseLoader)  # uses the yaml baseloader to preserve all strings
        if not isinstance(data, list):
            print(path, "ignored: not a proper yaml or json list")
        else:
            config.extend(data)

    print("done reading configuration from directory:", directory)
    return config


def filter_modes_and_checks(config):
    print("filtering modes and checks from config")
    modes, checks = [], []

    for item in config:
        j = json.dumps(item)

        if not isinstance(item, dict):
            print("ignored, not a dictionary:", j)
            continue

        if not all(isinstance(value, str) for value in item.values()):
            print("ignored, all values must be strings:", j)
            continue

        keys = item.keys()

        if keys == {"mode", "if"}:  # "mode" and "if" are mandatory
            modes.append(item)
        elif keys == {"check", "fix", "rank"} or keys == {"check", "fix", "rank", "when"}:  # "when" is optional
            try:
                item["rank"] = int(item["rank"])
                checks.append(item)
            except ValueError:
                print("ignored, rank must be an integer:", j)
        else:
            print('ignored, keys must match {"mode", "if"} or {"check", "fix", "rank"} or {"check", "fix", "rank", "when"}:', j)

    print("done filtering modes and checks from config")
    return modes, sorted(checks, key=operator.itemgetter("rank", "check"))


def filter_ongoing_modes(modes):
    return sorted(mode.get("mode") for mode in modes if subprocess.run(mode.get("if"), shell=True).returncode == 0)


def filter_ongoing_checks(ongoing_modes, checks):
    print("filtering ongoing checks from ongoing modes")
    ongoing_checks = []

    for check in checks:
        if not check.get("when") or check.get("when") in ongoing_modes:
            print("active: ", json.dumps(check))
            ongoing_checks.append(check)

    print("done filtering ongoing checks from ongoing modes")
    return ongoing_checks


class Watcher:
    def __init__(self, directory, mtime=0, modes=None, checks=None, ongoing_modes=None, ongoing_checks=None):
        if not directory.is_dir():
            raise ValueError("directory must exist")

        self._directory = directory
        self._mtime = mtime
        self._modes = modes or []
        self._checks = checks or []
        self._ongoing_modes = ongoing_modes or []
        self._ongoing_checks = ongoing_checks or []

    def _directory_has_changed(self):
        new_mtime = self._directory.stat().st_mtime
        if new_mtime != self._mtime:
            print(f"directory {self._directory} has changed")
            self._mtime = new_mtime
            return True
        return False

    def _checks_have_changed(self):
        self._modes, new_checks = filter_modes_and_checks(read_config_from_disk(self._directory))
        if new_checks != self._checks:
            print("checks have changed")
            self._checks = new_checks
            return True
        return False

    def _ongoing_modes_have_changed(self):
        new_ongoing_modes = filter_ongoing_modes(self._modes)
        if new_ongoing_modes != self._ongoing_modes:
            print(f"ongoing modes have changed: {new_ongoing_modes}")
            self._ongoing_modes = new_ongoing_modes
            return True
        return False

    def _refresh_ongoing_checks(self):
        self._ongoing_checks = filter_ongoing_checks(self._ongoing_modes, self._checks)

    def refresh_ongoing_checks_if_necessary(self):
        if self._directory_has_changed():
            if self._checks_have_changed() | self._ongoing_modes_have_changed():
                self._refresh_ongoing_checks()
        elif self._ongoing_modes_have_changed():
            self._refresh_ongoing_checks()

        return self._ongoing_checks


def try_checks(checks, delay=10):
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
        sp = subprocess.Popen(fix, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding=ENCODING)
        threading.Thread(target=lambda: [print(f"[{rank}] output: {line}", end="") for line in sp.stdout]).start()

        while True:
            try:
                if sp.wait(delay) != 0:
                    print(f"[{rank}] warning! fix returned code {sp.returncode}")
                break
            except subprocess.TimeoutExpired:
                try_checks(checks[:i], delay)

        cp = subprocess.run(test, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding=ENCODING)
        if cp.returncode != 0:
            print(f"[{rank}] failed({cp.returncode}): {test}")
            for line in cp.stdout.splitlines():
                print(f"[{rank}] output: {line}")
            raise ChildProcessError()

        print(f"[{rank}] fix successful")


def draft(directory: Path, delay=10):
    watcher = Watcher(directory)

    while True:
        try_checks(watcher.refresh_ongoing_checks_if_necessary(), delay)


def main():
    pass
