import pathlib

import heal

READ_CONFIG_FROM_DISK_OK_FILE_1 = """
---
- lorem
- ipsum
- dolor
- sit
- amet
""".lstrip()

READ_CONFIG_FROM_DISK_OK_FILE_2 = """
---
- consectetur
- adipiscing
- elit
""".lstrip()

READ_CONFIG_FROM_DISK_OK_OUTPUT = """
reading configuration from directory: {0}
done reading configuration from directory: {0}
""".lstrip()


def test_read_config_from_disk_ok(tmp_path, capsys):
    tmp_path.joinpath("file1.yml").write_text(READ_CONFIG_FROM_DISK_OK_FILE_1, encoding=heal.ENCODING)
    tmp_path.joinpath("file2.yml").write_text(READ_CONFIG_FROM_DISK_OK_FILE_2, encoding=heal.ENCODING)

    assert sorted(heal.read_config_from_disk(tmp_path)) == ["adipiscing", "amet", "consectetur", "dolor", "elit", "ipsum", "lorem", "sit"]
    assert capsys.readouterr().out == READ_CONFIG_FROM_DISK_OK_OUTPUT.format(tmp_path)


READ_CONFIG_FROM_DISK_KO_OSERROR_OUTPUT = """
reading configuration from directory: {0}
{1} ignored: [Errno 2] No such file or directory: '{1}'
done reading configuration from directory: {0}
""".lstrip()


def test_read_config_from_disk_ko_oserror(monkeypatch, tmp_path, capsys):
    fake_path = tmp_path.joinpath("foo")
    monkeypatch.setattr(pathlib.Path, "iterdir", lambda _: [fake_path])

    assert heal.read_config_from_disk(tmp_path) == []
    assert capsys.readouterr().out == READ_CONFIG_FROM_DISK_KO_OSERROR_OUTPUT.format(tmp_path, fake_path)


READ_CONFIG_FROM_DISK_KO_VALUEERROR_OUTPUT = """
reading configuration from directory: {0}
{1} ignored: 'utf-8' codec can't decode byte 0x99 in position 0: invalid start byte
done reading configuration from directory: {0}
""".lstrip()


def test_read_config_from_disk_ko_valueerror(tmp_path, capsys):
    binary_path = tmp_path.joinpath("foo")
    binary_path.write_bytes(bytes([0x99]))

    assert heal.read_config_from_disk(tmp_path) == []
    assert capsys.readouterr().out == READ_CONFIG_FROM_DISK_KO_VALUEERROR_OUTPUT.format(tmp_path, binary_path)


READ_CONFIG_FROM_DISK_KO_NOT_A_LIST_OUTPUT = """
reading configuration from directory: {0}
{1} ignored: not a proper yaml or json list
done reading configuration from directory: {0}
""".lstrip()


def test_read_config_from_disk_ko_not_a_list(tmp_path, capsys):
    not_a_list_path = tmp_path.joinpath("foo")
    not_a_list_path.write_text("lorem ipsum dolor sit amet")

    assert heal.read_config_from_disk(tmp_path) == []
    assert capsys.readouterr().out == READ_CONFIG_FROM_DISK_KO_NOT_A_LIST_OUTPUT.format(tmp_path, not_a_list_path)


FILTER_MODES_AND_CHECKS_OK_OUTPUT = """
filtering modes and checks from config
done filtering modes and checks from config
""".lstrip()


def test_filter_modes_and_checks_ok(capsys):
    modes, checks = heal.filter_modes_and_checks([{"check": "", "fix": "", "rank": "2"},
                                                  {"check": "b", "fix": "", "rank": "1", "when": ""},
                                                  {"check": "a", "fix": "", "rank": "1", "when": ""},
                                                  {"mode": "", "if": ""}])

    assert modes == [{"mode": "", "if": ""}]
    assert checks == [{"check": "a", "fix": "", "rank": 1, "when": ""},
                      {"check": "b", "fix": "", "rank": 1, "when": ""},
                      {"check": "", "fix": "", "rank": 2}]
    assert capsys.readouterr().out == FILTER_MODES_AND_CHECKS_OK_OUTPUT


FILTER_MODES_AND_CHECKS_KO_OUTPUT = """
filtering modes and checks from config
ignored, keys must match {"mode", "if"} or {"check", "fix", "rank"} or {"check", "fix", "rank", "when"}: {"check": "", "fix": ""}
ignored, keys must match {"mode", "if"} or {"check", "fix", "rank"} or {"check", "fix", "rank", "when"}: {"check": "", "fix": "", "rank": "10", "then": ""}
ignored, rank must be an integer: {"check": "", "fix": "", "rank": "max"}
ignored, all values must be strings: {"check": "", "fix": "", "rank": {}}
ignored, all values must be strings: {"check": "", "fix": "", "rank": []}
ignored, keys must match {"mode", "if"} or {"check", "fix", "rank"} or {"check", "fix", "rank", "when"}: {"mode": ""}
ignored, keys must match {"mode", "if"} or {"check", "fix", "rank"} or {"check", "fix", "rank", "when"}: {"mode": "", "if": "", "bonus": ""}
ignored, keys must match {"mode", "if"} or {"check", "fix", "rank"} or {"check", "fix", "rank", "when"}: {"check": "", "fix": "", "rank": "10", "mode": "", "if": ""}
ignored, keys must match {"mode", "if"} or {"check", "fix", "rank"} or {"check", "fix", "rank", "when"}: {}
ignored, keys must match {"mode", "if"} or {"check", "fix", "rank"} or {"check", "fix", "rank", "when"}: {"how": ""}
ignored, not a dictionary: "check"
done filtering modes and checks from config
""".lstrip()


def test_filter_modes_and_checks_ko(capsys):
    assert heal.filter_modes_and_checks([
        {"check": "", "fix": ""},
        {"check": "", "fix": "", "rank": "10", "then": ""},
        {"check": "", "fix": "", "rank": "max"},
        {"check": "", "fix": "", "rank": {}},
        {"check": "", "fix": "", "rank": []},
        {"mode": ""},
        {"mode": "", "if": "", "bonus": ""},
        {"check": "", "fix": "", "rank": "10", "mode": "", "if": ""},
        {},
        {"how": ""},
        "check"
    ]) == ([], [])
    assert capsys.readouterr().out == FILTER_MODES_AND_CHECKS_KO_OUTPUT


def test_filter_ongoing_modes_ok():
    assert heal.filter_ongoing_modes([
        {"mode": "one", "if": "/bin/true"},
        {"mode": "two", "if": "/bin/false"},
        {"mode": "three", "if": "/bin/false"},
        {"mode": "four", "if": "/bin/true"}
    ]) == ["four", "one"]
