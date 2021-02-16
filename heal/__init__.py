import subprocess
from pathlib import Path

import yaml

ENCODING = "utf-8"


def read_config_from_disk(directory: Path):
    print(f"reading configuration from directory: {directory}")
    config = []

    for path in directory.iterdir():
        try:
            text = path.read_text(encoding=ENCODING)
        except (OSError, ValueError) as e:
            print(f"{path} ignored: {e}")
            continue

        data = yaml.load(text, Loader=yaml.BaseLoader)  # uses the yaml baseloader to preserve all strings
        if not isinstance(data, list):
            print(f"{path} ignored: not a proper yaml or json list")
        else:
            config.extend(data)

    print(f"done reading configuration from directory: {directory}")
    return config


def filter_modes_and_checks(config):
    modes, checks = [], []

    for item in config:
        if isinstance(item, dict) and all(isinstance(value, str) for value in item.values()):
            keys = item.keys()

            if keys == {"mode", "if"}:  # "mode" and "if" are mandatory
                modes.append(item)
            elif keys == {"check", "fix", "rank"} or keys == {"check", "fix", "rank", "when"}:  # "when" is optional
                try:
                    item["rank"] = int(item["rank"])
                    checks.append(item)
                except ValueError:
                    pass

    return modes, checks


def filter_current_modes(modes):
    return [mode.get("mode") for mode in modes if subprocess.run(mode.get("if"), shell=True).returncode == 0]


def main():
    pass
