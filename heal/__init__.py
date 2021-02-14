from pathlib import Path

import yaml

ENCODING = "utf-8"


def yield_config_from_disk(directory: Path):
    for path in directory.iterdir():
        yield from yaml.load(path.read_text(encoding=ENCODING), Loader=yaml.BaseLoader)  # uses the yaml baseloader to preserve all strings


def main():
    pass
