import json
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
    return modes, checks


def filter_ongoing_modes(modes):
    return sorted(mode.get("mode") for mode in modes if subprocess.run(mode.get("if"), shell=True).returncode == 0)


def main():
    pass
