import pytest
import time

import heal


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
    monkeypatch.setattr(heal, "read_config_from_disk", lambda _: None)

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
reading configuration from directory: {0}
done reading configuration from directory: {0}
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
reading configuration from directory: {0}
done reading configuration from directory: {0}
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
reading configuration from directory: {0}
done reading configuration from directory: {0}
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
reading configuration from directory: {0}
done reading configuration from directory: {0}
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
