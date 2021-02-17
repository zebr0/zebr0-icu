import json
import operator
import subprocess
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


def draft(directory: Path):
    previous_mtime, modes, current_checks, previous_ongoing_modes, previous_checks, ongoing_checks = 0, [], [], [], [], []

    while True:
        current_mtime = directory.stat().st_mtime
        if current_mtime != previous_mtime:
            modes, current_checks = filter_modes_and_checks(read_config_from_disk(directory))

        current_ongoing_modes = filter_ongoing_modes(modes)
        if current_ongoing_modes != previous_ongoing_modes or current_checks != previous_checks:
            ongoing_checks = filter_ongoing_checks(current_ongoing_modes, current_checks)

        for check in ongoing_checks:
            print(json.dumps(check))

        previous_mtime = current_mtime
        previous_checks = current_checks
        previous_ongoing_modes = current_ongoing_modes


def main():
    pass
