import json
import subprocess
from operator import itemgetter
from pathlib import Path
from typing import List, Any, Tuple

import yaml

from heal.util import ENCODING


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
