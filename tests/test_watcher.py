import pathlib

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

    assert sorted(heal.watch.read_config(tmp_path)) == ["adipiscing", "amet", "consectetur", "dolor", "elit", "ipsum", "lorem", "sit"]
    assert capsys.readouterr().out == READ_CONFIG_OK_OUTPUT


READ_CONFIG_KO_OSERROR_OUTPUT = """
reading configuration
'file1.yml' ignored: [Errno 2] No such file or directory: '{0}/file1.yml'
done
""".lstrip()


def test_read_config_ko_oserror(tmp_path, monkeypatch, capsys):
    tmp_path.joinpath("file2.yml").write_text(READ_CONFIG_FILE_2)
    monkeypatch.setattr(pathlib.Path, "iterdir", lambda _: [tmp_path.joinpath("file1.yml"), tmp_path.joinpath("file2.yml")])

    assert heal.watch.read_config(tmp_path) == ["consectetur", "adipiscing", "elit"]
    assert capsys.readouterr().out == READ_CONFIG_KO_OSERROR_OUTPUT.format(tmp_path)


READ_CONFIG_KO_VALUEERROR_OUTPUT = """
reading configuration
'file1.yml' ignored: 'utf-8' codec can't decode byte 0x99 in position 0: invalid start byte
done
""".lstrip()


def test_read_config_ko_valueerror(tmp_path, capsys):
    tmp_path.joinpath("file1.yml").write_bytes(bytes([0x99]))
    tmp_path.joinpath("file2.yml").write_text(READ_CONFIG_FILE_2)

    assert heal.watch.read_config(tmp_path) == ["consectetur", "adipiscing", "elit"]
    assert capsys.readouterr().out == READ_CONFIG_KO_VALUEERROR_OUTPUT


READ_CONFIG_KO_NOT_A_LIST_OUTPUT = """
reading configuration
'file1.yml' ignored: not a proper yaml or json list
done
""".lstrip()


def test_read_config_ko_not_a_list(tmp_path, capsys):
    tmp_path.joinpath("file1.yml").write_text("lorem ipsum dolor sit amet")
    tmp_path.joinpath("file2.yml").write_text(READ_CONFIG_FILE_2)

    assert heal.watch.read_config(tmp_path) == ["consectetur", "adipiscing", "elit"]
    assert capsys.readouterr().out == READ_CONFIG_KO_NOT_A_LIST_OUTPUT


def test_read_config_ok_empty(tmp_path, capsys):
    assert heal.watch.read_config(tmp_path) == []
    assert capsys.readouterr().out == READ_CONFIG_OK_OUTPUT


FILTER_MODES_AND_CHECKS_OK_OUTPUT = """
filtering modes and checks
done
""".lstrip()


def test_filter_modes_and_checks_ok(capsys):
    modes, checks = heal.watch.filter_modes_and_checks([{"check": "sed do eiusmod tempor", "fix": "incididunt ut labore et dolore magna aliqua", "rank": "2"},
                                                        {"check": "lorem ipsum dolor sit amet", "fix": "consectetur adipiscing elit", "rank": "1", "when": "alpha"},
                                                        {"mode": "beta", "if": "ut enim"},
                                                        {"mode": "alpha", "if": "ad minim veniam"}])

    assert modes == [{"mode": "alpha", "if": "ad minim veniam"},
                     {"mode": "beta", "if": "ut enim"}]
    assert checks == [{"check": "lorem ipsum dolor sit amet", "fix": "consectetur adipiscing elit", "rank": 1, "when": "alpha"},
                      {"check": "sed do eiusmod tempor", "fix": "incididunt ut labore et dolore magna aliqua", "rank": 2}]
    assert capsys.readouterr().out == FILTER_MODES_AND_CHECKS_OK_OUTPUT


FILTER_MODES_AND_CHECKS_KO_OUTPUT = """
filtering modes and checks
ignored, not a dictionary: "check"
ignored, not a dictionary: []
ignored, values cannot be lists or dictionaries: {"check": "", "fix": "", "rank": {}}
ignored, values cannot be lists or dictionaries: {"check": "", "fix": "", "rank": []}
ignored, keys must match {"mode", "if"} or {"check", "fix", "rank"} or {"check", "fix", "rank", "when"}: {"mode": ""}
ignored, keys must match {"mode", "if"} or {"check", "fix", "rank"} or {"check", "fix", "rank", "when"}: {"mode": "", "if": "", "bonus": ""}
ignored, keys must match {"mode", "if"} or {"check", "fix", "rank"} or {"check", "fix", "rank", "when"}: {"check": "", "fix": ""}
ignored, keys must match {"mode", "if"} or {"check", "fix", "rank"} or {"check", "fix", "rank", "when"}: {"check": "", "fix": "", "rank": "10", "then": ""}
ignored, keys must match {"mode", "if"} or {"check", "fix", "rank"} or {"check", "fix", "rank", "when"}: {"check": "", "fix": "", "rank": "10", "mode": "", "if": ""}
ignored, keys must match {"mode", "if"} or {"check", "fix", "rank"} or {"check", "fix", "rank", "when"}: {}
ignored, keys must match {"mode", "if"} or {"check", "fix", "rank"} or {"check", "fix", "rank", "when"}: {"how": ""}
ignored, rank must be an integer: {"check": "", "fix": "", "rank": "max"}
done
""".lstrip()


def test_filter_modes_and_checks_ko(capsys):
    assert heal.watch.filter_modes_and_checks([
        "check",
        [],
        {"check": "", "fix": "", "rank": {}},
        {"check": "", "fix": "", "rank": []},
        {"mode": ""},
        {"mode": "", "if": "", "bonus": ""},
        {"check": "", "fix": ""},
        {"check": "", "fix": "", "rank": "10", "then": ""},
        {"check": "", "fix": "", "rank": "10", "mode": "", "if": ""},
        {},
        {"how": ""},
        {"check": "", "fix": "", "rank": "max"},
    ]) == ([], [])
    assert capsys.readouterr().out == FILTER_MODES_AND_CHECKS_KO_OUTPUT


def test_filter_modes_and_checks_ok_empty(capsys):
    assert heal.watch.filter_modes_and_checks([]) == ([], [])
    assert capsys.readouterr().out == FILTER_MODES_AND_CHECKS_OK_OUTPUT


def test_filter_current_modes_ok():
    assert heal.watch.filter_current_modes([
        {"mode": "one", "if": "/bin/true"},
        {"mode": "two", "if": "/bin/false"},
        {"mode": "three", "if": "/bin/false"},
        {"mode": "four", "if": "/bin/true"}
    ]) == ["one", "four"]


def test_filter_current_modes_ok_empty():
    assert heal.watch.filter_current_modes([]) == []


FILTER_CURRENT_CHECKS_OK_OUTPUT = """
filtering current checks
active: {"check": "", "fix": "", "rank": 1}
active: {"check": "", "fix": "", "rank": 2, "when": "alpha"}
done
""".lstrip()


def test_filter_current_checks_ok(capsys):
    current_modes = ["alpha"]
    checks = [{"check": "", "fix": "", "rank": 1},
              {"check": "", "fix": "", "rank": 2, "when": "alpha"},
              {"check": "", "fix": "", "rank": 3, "when": "beta"}]

    assert heal.watch.filter_current_checks(current_modes, checks) == [{"check": "", "fix": "", "rank": 1},
                                                                       {"check": "", "fix": "", "rank": 2, "when": "alpha"}]
    assert capsys.readouterr().out == FILTER_CURRENT_CHECKS_OK_OUTPUT


FILTER_CURRENT_CHECKS_OK_EMPTY_OUTPUT = """
filtering current checks
done
""".lstrip()


def test_filter_current_checks_ok_empty(capsys):
    assert heal.watch.filter_current_checks([], []) == []
    assert capsys.readouterr().out == FILTER_CURRENT_CHECKS_OK_EMPTY_OUTPUT


def test_directory_has_changed(tmp_path, capsys):
    watcher = heal.Watcher(tmp_path)

    assert watcher.directory_has_changed()
    assert watcher.mtime == tmp_path.stat().st_mtime
    assert capsys.readouterr().out == "configuration directory has changed\n"

    time.sleep(0.01)
    assert not watcher.directory_has_changed()
    assert capsys.readouterr().out == ""

    time.sleep(0.01)
    tmp_path.joinpath("dummy").write_text("dummy")

    assert watcher.directory_has_changed()
    assert capsys.readouterr().out == "configuration directory has changed\n"


def test_checks_have_changed(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(heal.watch, "read_config", lambda _: None)

    watcher = heal.Watcher(tmp_path)

    monkeypatch.setattr(heal.watch, "filter_modes_and_checks", lambda _: ([], []))
    assert not watcher.checks_have_changed()
    assert capsys.readouterr().out == ""

    monkeypatch.setattr(heal.watch, "filter_modes_and_checks", lambda _: (["mode"], []))
    assert not watcher.checks_have_changed()
    assert watcher.modes == ["mode"]
    assert capsys.readouterr().out == ""

    monkeypatch.setattr(heal.watch, "filter_modes_and_checks", lambda _: (["mode"], ["check1", "check2"]))
    assert watcher.checks_have_changed()
    assert watcher.checks == ["check1", "check2"]
    assert capsys.readouterr().out == "checks have changed\n"

    monkeypatch.setattr(heal.watch, "filter_modes_and_checks", lambda _: (["mode"], ["check1"]))
    assert watcher.checks_have_changed()
    assert watcher.checks == ["check1"]
    assert capsys.readouterr().out == "checks have changed\n"

    assert not watcher.checks_have_changed()
    assert capsys.readouterr().out == ""


def test_current_modes_have_changed(tmp_path, monkeypatch, capsys):
    watcher = heal.Watcher(tmp_path)

    monkeypatch.setattr(heal.watch, "filter_current_modes", lambda _: [])
    assert not watcher.current_modes_have_changed()
    assert capsys.readouterr().out == ""

    monkeypatch.setattr(heal.watch, "filter_current_modes", lambda _: ["mode1", "mode2"])
    assert watcher.current_modes_have_changed()
    assert watcher.current_modes == ["mode1", "mode2"]
    assert capsys.readouterr().out == "current modes have changed: ['mode1', 'mode2']\n"

    monkeypatch.setattr(heal.watch, "filter_current_modes", lambda _: ["mode1"])
    assert watcher.current_modes_have_changed()
    assert capsys.readouterr().out == "current modes have changed: ['mode1']\n"

    assert not watcher.current_modes_have_changed()
    assert capsys.readouterr().out == ""


REFRESH_CURRENT_CHECKS_IF_NECESSARY_OUTPUT_1 = """
configuration directory has changed
reading configuration
done
filtering modes and checks
done
""".lstrip()

REFRESH_CURRENT_CHECKS_IF_NECESSARY_CHECKS_CHANGED = """
---
- check: just adding a check without mode
  fix: whatever
  rank: 1
- check: adding a check for later
  fix: whatever
  rank: 10
  when: special
""".lstrip()

REFRESH_CURRENT_CHECKS_IF_NECESSARY_OUTPUT_2 = """
configuration directory has changed
reading configuration
done
filtering modes and checks
done
checks have changed
filtering current checks
active: {"check": "just adding a check without mode", "fix": "whatever", "rank": 1}
done
""".lstrip()

REFRESH_CURRENT_CHECKS_IF_NECESSARY_CHECKS_AND_MODES_CHANGED = """
---
- check: adding a check with mode
  fix: whatever
  rank: 2
  when: basic
- mode: basic
  if: true
""".lstrip()

REFRESH_CURRENT_CHECKS_IF_NECESSARY_OUTPUT_3 = """
configuration directory has changed
reading configuration
done
filtering modes and checks
done
checks have changed
current modes have changed: ['basic']
filtering current checks
active: {"check": "just adding a check without mode", "fix": "whatever", "rank": 1}
active: {"check": "adding a check with mode", "fix": "whatever", "rank": 2, "when": "basic"}
done
""".lstrip()

REFRESH_CURRENT_CHECKS_IF_NECESSARY_ONLY_MODES_CHANGED = """
---
- mode: special
  if: "[ ! -f {0}/flag ]"
""".lstrip()

REFRESH_CURRENT_CHECKS_IF_NECESSARY_OUTPUT_4 = """
configuration directory has changed
reading configuration
done
filtering modes and checks
done
current modes have changed: ['basic', 'special']
filtering current checks
active: {"check": "just adding a check without mode", "fix": "whatever", "rank": 1}
active: {"check": "adding a check with mode", "fix": "whatever", "rank": 2, "when": "basic"}
active: {"check": "adding a check for later", "fix": "whatever", "rank": 10, "when": "special"}
done
""".lstrip()

REFRESH_CURRENT_CHECKS_IF_NECESSARY_OUTPUT_5 = """
current modes have changed: ['basic']
filtering current checks
active: {"check": "just adding a check without mode", "fix": "whatever", "rank": 1}
active: {"check": "adding a check with mode", "fix": "whatever", "rank": 2, "when": "basic"}
done
""".lstrip()


def test_refresh_current_checks_if_necessary_ok(tmp_path, capsys):
    config_path = tmp_path.joinpath("config")
    config_path.mkdir()

    # init
    watcher = heal.Watcher(config_path)
    assert watcher.refresh_current_checks_if_necessary() == []
    assert capsys.readouterr().out == REFRESH_CURRENT_CHECKS_IF_NECESSARY_OUTPUT_1

    # case 1: checks changed, not current modes
    time.sleep(0.01)
    config_path.joinpath("checks_changed.yaml").write_text(REFRESH_CURRENT_CHECKS_IF_NECESSARY_CHECKS_CHANGED)
    assert watcher.refresh_current_checks_if_necessary() == [{"check": "just adding a check without mode", "fix": "whatever", "rank": 1}]
    assert capsys.readouterr().out == REFRESH_CURRENT_CHECKS_IF_NECESSARY_OUTPUT_2

    # case 2: checks and current modes changed
    time.sleep(0.01)
    config_path.joinpath("checks_and_modes_changed.yaml").write_text(REFRESH_CURRENT_CHECKS_IF_NECESSARY_CHECKS_AND_MODES_CHANGED)
    assert watcher.refresh_current_checks_if_necessary() == [{"check": "just adding a check without mode", "fix": "whatever", "rank": 1},
                                                             {"check": "adding a check with mode", "fix": "whatever", "rank": 2, "when": "basic"}]
    assert capsys.readouterr().out == REFRESH_CURRENT_CHECKS_IF_NECESSARY_OUTPUT_3

    # case 3: new current mode
    time.sleep(0.01)
    config_path.joinpath("only_modes_changed.yaml").write_text(REFRESH_CURRENT_CHECKS_IF_NECESSARY_ONLY_MODES_CHANGED.format(tmp_path))
    assert watcher.refresh_current_checks_if_necessary() == [{"check": "just adding a check without mode", "fix": "whatever", "rank": 1},
                                                             {"check": "adding a check with mode", "fix": "whatever", "rank": 2, "when": "basic"},
                                                             {"check": "adding a check for later", "fix": "whatever", "rank": 10, "when": "special"}]
    assert capsys.readouterr().out == REFRESH_CURRENT_CHECKS_IF_NECESSARY_OUTPUT_4

    # case 4: nothing changed
    assert watcher.refresh_current_checks_if_necessary() == [{"check": "just adding a check without mode", "fix": "whatever", "rank": 1},
                                                             {"check": "adding a check with mode", "fix": "whatever", "rank": 2, "when": "basic"},
                                                             {"check": "adding a check for later", "fix": "whatever", "rank": 10, "when": "special"}]
    assert capsys.readouterr().out == ""

    # case 5: current modes changed
    tmp_path.joinpath("flag").touch()
    assert watcher.refresh_current_checks_if_necessary() == [{"check": "just adding a check without mode", "fix": "whatever", "rank": 1},
                                                             {"check": "adding a check with mode", "fix": "whatever", "rank": 2, "when": "basic"}]
    assert capsys.readouterr().out == REFRESH_CURRENT_CHECKS_IF_NECESSARY_OUTPUT_5
