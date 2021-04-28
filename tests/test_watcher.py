import pathlib

import pytest
import time

import heal

READ_CONFIG_FILE_1 = """
---
- lorem
- ipsum
- dolor
- sit
- amet
""".lstrip()

READ_CONFIG_FILE_2 = """
---
- consectetur
- adipiscing
- elit
""".lstrip()

READ_CONFIG_OK_OUTPUT = """
reading configuration
done
""".lstrip()


def test_read_config_ok(tmp_path, capsys):
    tmp_path.joinpath("file1.yml").write_text(READ_CONFIG_FILE_1)
    tmp_path.joinpath("file2.yml").write_text(READ_CONFIG_FILE_2)

    assert sorted(heal.read_config(tmp_path)) == ["adipiscing", "amet", "consectetur", "dolor", "elit", "ipsum", "lorem", "sit"]
    assert capsys.readouterr().out == READ_CONFIG_OK_OUTPUT


READ_CONFIG_KO_OSERROR_OUTPUT = """
reading configuration
'file1.yml' ignored: [Errno 2] No such file or directory: '{0}/file1.yml'
done
""".lstrip()


def test_read_config_ko_oserror(tmp_path, monkeypatch, capsys):
    tmp_path.joinpath("file2.yml").write_text(READ_CONFIG_FILE_2)
    monkeypatch.setattr(pathlib.Path, "iterdir", lambda _: [tmp_path.joinpath("file1.yml"), tmp_path.joinpath("file2.yml")])

    assert heal.read_config(tmp_path) == ["consectetur", "adipiscing", "elit"]
    assert capsys.readouterr().out == READ_CONFIG_KO_OSERROR_OUTPUT.format(tmp_path)


READ_CONFIG_KO_VALUEERROR_OUTPUT = """
reading configuration
'file1.yml' ignored: 'utf-8' codec can't decode byte 0x99 in position 0: invalid start byte
done
""".lstrip()


def test_read_config_ko_valueerror(tmp_path, capsys):
    tmp_path.joinpath("file1.yml").write_bytes(bytes([0x99]))
    tmp_path.joinpath("file2.yml").write_text(READ_CONFIG_FILE_2)

    assert heal.read_config(tmp_path) == ["consectetur", "adipiscing", "elit"]
    assert capsys.readouterr().out == READ_CONFIG_KO_VALUEERROR_OUTPUT


READ_CONFIG_KO_NOT_A_LIST_OUTPUT = """
reading configuration
'file1.yml' ignored: not a proper yaml or json list
done
""".lstrip()


def test_read_config_ko_not_a_list(tmp_path, capsys):
    tmp_path.joinpath("file1.yml").write_text("lorem ipsum dolor sit amet")
    tmp_path.joinpath("file2.yml").write_text(READ_CONFIG_FILE_2)

    assert heal.read_config(tmp_path) == ["consectetur", "adipiscing", "elit"]
    assert capsys.readouterr().out == READ_CONFIG_KO_NOT_A_LIST_OUTPUT


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


FILTER_ONGOING_CHECKS_OK_OUTPUT = """
filtering ongoing checks from ongoing modes
active:  {"check": "a", "fix": "", "rank": 1}
active:  {"check": "b", "fix": "", "rank": 2, "when": "one"}
done filtering ongoing checks from ongoing modes
""".lstrip()


def test_filter_ongoing_checks_ok(capsys):
    ongoing_modes = ["one"]
    checks = [{"check": "a", "fix": "", "rank": 1},
              {"check": "b", "fix": "", "rank": 2, "when": "one"},
              {"check": "c", "fix": "", "rank": 3, "when": "two"}]

    assert heal.filter_ongoing_checks(ongoing_modes, checks) == [{"check": "a", "fix": "", "rank": 1},
                                                                 {"check": "b", "fix": "", "rank": 2, "when": "one"}]
    assert capsys.readouterr().out == FILTER_ONGOING_CHECKS_OK_OUTPUT


def test_directory_has_changed(tmp_path, capsys):
    watcher = heal.Watcher(tmp_path)

    assert watcher._directory_has_changed()
    assert watcher._mtime == tmp_path.stat().st_mtime
    assert capsys.readouterr().out == f"directory {tmp_path} has changed\n"

    time.sleep(0.01)
    assert not watcher._directory_has_changed()
    assert capsys.readouterr().out == ""

    time.sleep(0.01)
    tmp_path.joinpath("dummy").write_text("dummy")

    assert watcher._directory_has_changed()
    assert capsys.readouterr().out == f"directory {tmp_path} has changed\n"


def test_checks_have_changed(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(heal, "read_config", lambda _: None)

    watcher = heal.Watcher(tmp_path)

    monkeypatch.setattr(heal, "filter_modes_and_checks", lambda _: ([], []))
    assert not watcher._checks_have_changed()
    assert capsys.readouterr().out == ""

    monkeypatch.setattr(heal, "filter_modes_and_checks", lambda _: (["mode"], []))
    assert not watcher._checks_have_changed()
    assert watcher._modes == ["mode"]
    assert capsys.readouterr().out == ""

    monkeypatch.setattr(heal, "filter_modes_and_checks", lambda _: (["mode"], ["check1", "check2"]))
    assert watcher._checks_have_changed()
    assert watcher._checks == ["check1", "check2"]
    assert capsys.readouterr().out == "checks have changed\n"

    monkeypatch.setattr(heal, "filter_modes_and_checks", lambda _: (["mode"], ["check1"]))
    assert watcher._checks_have_changed()
    assert watcher._checks == ["check1"]
    assert capsys.readouterr().out == "checks have changed\n"

    assert not watcher._checks_have_changed()
    assert capsys.readouterr().out == ""


def test_ongoing_modes_have_changed(tmp_path, monkeypatch, capsys):
    watcher = heal.Watcher(tmp_path)

    monkeypatch.setattr(heal, "filter_ongoing_modes", lambda _: [])
    assert not watcher._ongoing_modes_have_changed()
    assert capsys.readouterr().out == ""

    monkeypatch.setattr(heal, "filter_ongoing_modes", lambda _: ["mode1", "mode2"])
    assert watcher._ongoing_modes_have_changed()
    assert watcher.ongoing_modes == ["mode1", "mode2"]
    assert capsys.readouterr().out == "ongoing modes have changed: ['mode1', 'mode2']\n"

    monkeypatch.setattr(heal, "filter_ongoing_modes", lambda _: ["mode1"])
    assert watcher._ongoing_modes_have_changed()
    assert capsys.readouterr().out == "ongoing modes have changed: ['mode1']\n"

    assert not watcher._ongoing_modes_have_changed()
    assert capsys.readouterr().out == ""


def test_refresh_ongoing_checks_if_necessary_ko(tmp_path):
    with pytest.raises(ValueError):
        heal.Watcher(tmp_path.joinpath("missing_directory"))


REFRESH_ONGOING_CHECKS_IF_NECESSARY_OUTPUT_1 = """
directory {0} has changed
reading configuration
done
filtering modes and checks from config
done filtering modes and checks from config
""".lstrip()

REFRESH_ONGOING_CHECKS_IF_NECESSARY_CHECKS_CHANGED = """
---
- check: just adding a check without mode
  fix: whatever
  rank: 1
- check: adding a check for later
  fix: whatever
  rank: 10
  when: special
""".lstrip()

REFRESH_ONGOING_CHECKS_IF_NECESSARY_OUTPUT_2 = """
directory {0} has changed
reading configuration
done
filtering modes and checks from config
done filtering modes and checks from config
checks have changed
filtering ongoing checks from ongoing modes
active:  {{"check": "just adding a check without mode", "fix": "whatever", "rank": 1}}
done filtering ongoing checks from ongoing modes
""".lstrip()

REFRESH_ONGOING_CHECKS_IF_NECESSARY_CHECKS_AND_MODES_CHANGED = """
---
- check: adding a check with mode
  fix: whatever
  rank: 2
  when: basic
- mode: basic
  if: true
""".lstrip()

REFRESH_ONGOING_CHECKS_IF_NECESSARY_OUTPUT_3 = """
directory {0} has changed
reading configuration
done
filtering modes and checks from config
done filtering modes and checks from config
checks have changed
ongoing modes have changed: ['basic']
filtering ongoing checks from ongoing modes
active:  {{"check": "just adding a check without mode", "fix": "whatever", "rank": 1}}
active:  {{"check": "adding a check with mode", "fix": "whatever", "rank": 2, "when": "basic"}}
done filtering ongoing checks from ongoing modes
""".lstrip()

REFRESH_ONGOING_CHECKS_IF_NECESSARY_ONLY_MODES_CHANGED = """
---
- mode: special
  if: "[ ! -f {0}/flag ]"
""".lstrip()

REFRESH_ONGOING_CHECKS_IF_NECESSARY_OUTPUT_4 = """
directory {0} has changed
reading configuration
done
filtering modes and checks from config
done filtering modes and checks from config
ongoing modes have changed: ['basic', 'special']
filtering ongoing checks from ongoing modes
active:  {{"check": "just adding a check without mode", "fix": "whatever", "rank": 1}}
active:  {{"check": "adding a check with mode", "fix": "whatever", "rank": 2, "when": "basic"}}
active:  {{"check": "adding a check for later", "fix": "whatever", "rank": 10, "when": "special"}}
done filtering ongoing checks from ongoing modes
""".lstrip()

REFRESH_ONGOING_CHECKS_IF_NECESSARY_OUTPUT_5 = """
ongoing modes have changed: ['basic']
filtering ongoing checks from ongoing modes
active:  {"check": "just adding a check without mode", "fix": "whatever", "rank": 1}
active:  {"check": "adding a check with mode", "fix": "whatever", "rank": 2, "when": "basic"}
done filtering ongoing checks from ongoing modes
""".lstrip()


def test_refresh_ongoing_checks_if_necessary_ok(tmp_path, capsys):
    config_path = tmp_path.joinpath("config")
    config_path.mkdir()

    # init
    watcher = heal.Watcher(config_path)
    assert watcher.refresh_ongoing_checks_if_necessary() == []
    assert capsys.readouterr().out == REFRESH_ONGOING_CHECKS_IF_NECESSARY_OUTPUT_1.format(config_path)

    # case 1: checks changed, not ongoing modes
    time.sleep(0.01)
    config_path.joinpath("checks_changed.yaml").write_text(REFRESH_ONGOING_CHECKS_IF_NECESSARY_CHECKS_CHANGED)
    assert watcher.refresh_ongoing_checks_if_necessary() == [{"check": "just adding a check without mode", "fix": "whatever", "rank": 1}]
    assert capsys.readouterr().out == REFRESH_ONGOING_CHECKS_IF_NECESSARY_OUTPUT_2.format(config_path)

    # case 2: checks and ongoing modes changed
    time.sleep(0.01)
    config_path.joinpath("checks_and_modes_changed.yaml").write_text(REFRESH_ONGOING_CHECKS_IF_NECESSARY_CHECKS_AND_MODES_CHANGED)
    assert watcher.refresh_ongoing_checks_if_necessary() == [{"check": "just adding a check without mode", "fix": "whatever", "rank": 1},
                                                             {"check": "adding a check with mode", "fix": "whatever", "rank": 2, "when": "basic"}]
    assert capsys.readouterr().out == REFRESH_ONGOING_CHECKS_IF_NECESSARY_OUTPUT_3.format(config_path)

    # case 3: new ongoing mode
    time.sleep(0.01)
    config_path.joinpath("only_modes_changed.yaml").write_text(REFRESH_ONGOING_CHECKS_IF_NECESSARY_ONLY_MODES_CHANGED.format(tmp_path))
    assert watcher.refresh_ongoing_checks_if_necessary() == [{"check": "just adding a check without mode", "fix": "whatever", "rank": 1},
                                                             {"check": "adding a check with mode", "fix": "whatever", "rank": 2, "when": "basic"},
                                                             {"check": "adding a check for later", "fix": "whatever", "rank": 10, "when": "special"}]
    assert capsys.readouterr().out == REFRESH_ONGOING_CHECKS_IF_NECESSARY_OUTPUT_4.format(config_path)

    # case 4: nothing changed
    assert watcher.refresh_ongoing_checks_if_necessary() == [{"check": "just adding a check without mode", "fix": "whatever", "rank": 1},
                                                             {"check": "adding a check with mode", "fix": "whatever", "rank": 2, "when": "basic"},
                                                             {"check": "adding a check for later", "fix": "whatever", "rank": 10, "when": "special"}]
    assert capsys.readouterr().out == ""

    # case 5: ongoing modes changed
    tmp_path.joinpath("flag").touch()
    assert watcher.refresh_ongoing_checks_if_necessary() == [{"check": "just adding a check without mode", "fix": "whatever", "rank": 1},
                                                             {"check": "adding a check with mode", "fix": "whatever", "rank": 2, "when": "basic"}]
    assert capsys.readouterr().out == REFRESH_ONGOING_CHECKS_IF_NECESSARY_OUTPUT_5
