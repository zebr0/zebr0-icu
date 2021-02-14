from pathlib import Path

import yaml

ENCODING = "utf-8"


def yield_config_from_disk(directory: Path):
    for path in directory.iterdir():
        yield from yaml.load(path.read_text(encoding=ENCODING), Loader=yaml.BaseLoader)  # uses the yaml baseloader to preserve all strings


def filter_modes_and_checks(config):
    modes, checks = [], []

    for item in config:
        if isinstance(item, dict):
            keys = item.keys()

            if keys == {"mode", "if"}:  # "mode" and "if" are mandatory
                modes.append(item)
            elif keys == {"check", "fix"} or keys == {"check", "fix", "when"}:  # "when" is optional
                checks.append(item)

    return modes, checks


def main():
    pass
