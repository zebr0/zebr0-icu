import datetime
import json
import threading

import time

import heal


def test_configuration_directory_not_exists(tmp_path, capsys):
    configuration_directory = tmp_path.joinpath("not-exists")
    status_file = tmp_path.joinpath("status-file")

    heal.heal(configuration_directory, status_file, threading.Event())

    assert capsys.readouterr().out == f"exiting: {configuration_directory} must exist and be a directory\n"
    assert not status_file.exists()


def test_configuration_directory_not_a_directory(tmp_path, capsys):
    configuration_directory = tmp_path.joinpath("file")
    configuration_directory.touch()
    status_file = tmp_path.joinpath("status-file")

    heal.heal(configuration_directory, status_file, threading.Event())

    assert capsys.readouterr().out == f"exiting: {configuration_directory} must exist and be a directory\n"
    assert not status_file.exists()


PROGRESSIVE_AND_KO_INPUT = """
---
- check: false
  fix: true
  rank: 1
""".lstrip()

PROGRESSIVE_AND_KO_OUTPUT_1 = """
watching: {0}
configuration directory has changed
reading configuration
done
filtering modes and checks
done
""".lstrip()

PROGRESSIVE_AND_KO_OUTPUT_2 = """
configuration directory has changed
reading configuration
done
filtering modes and checks
done
checks have changed
filtering current checks
active: {"check": "false", "fix": "true", "rank": 1}
done
[1] failed: false
[1] fixing: true
[1] failed again: false
exiting: fatal error
""".lstrip()


def test_progressive_and_ko(tmp_path, capsys):
    # empty configuration
    configuration_directory = tmp_path.joinpath("config")
    configuration_directory.mkdir()
    status_file = tmp_path.joinpath("status-file")

    thread = threading.Thread(target=heal.heal, args=(configuration_directory, status_file, threading.Event(), 0.1))
    thread.start()

    time.sleep(0.15)  # 2 cycles
    assert json.loads(status_file.read_text()).get("status") == "ok"
    assert capsys.readouterr().out == PROGRESSIVE_AND_KO_OUTPUT_1.format(configuration_directory)

    # adding failing configuration
    configuration_directory.joinpath("failing-configuration").write_text(PROGRESSIVE_AND_KO_INPUT)

    thread.join()
    assert json.loads(status_file.read_text()).get("status") == "ko"
    assert capsys.readouterr().out == PROGRESSIVE_AND_KO_OUTPUT_2

    # previous run failed, so if we start it again, it should immediately fail
    heal.heal(configuration_directory, status_file, threading.Event())
    assert capsys.readouterr().out == f"exiting: ko status found in {status_file}\n"


OK_INPUT = """
---
- check: "[ ! -f {0} ]"
  fix: rm {0}
  rank: 1
""".lstrip()

OK_OUTPUT = """
watching: {0}
configuration directory has changed
reading configuration
done
filtering modes and checks
done
checks have changed
filtering current checks
active: {{"check": "[ ! -f {1} ]", "fix": "rm {1}", "rank": 1}}
done
[1] failed: [ ! -f {1} ]
[1] fixing: rm {1}
[1] fix successful
[1] failed: [ ! -f {1} ]
[1] fixing: rm {1}
[1] fix successful
""".lstrip()


def test_ok(tmp_path, capsys):
    # regular configuration
    flag = tmp_path.joinpath("flag")
    configuration_directory = tmp_path.joinpath("config")
    configuration_directory.mkdir()
    configuration_directory.joinpath("config-file").write_text(OK_INPUT.format(flag))
    status_file = tmp_path.joinpath("status-file")
    event = threading.Event()

    thread = threading.Thread(target=heal.heal, args=(configuration_directory, status_file, event, 0.01))
    thread.start()

    # lots of cycles
    time.sleep(0.2)
    status_1 = json.loads(status_file.read_text())
    assert status_1.get("status") == "ok"

    # first problem
    flag.touch()
    time.sleep(0.1)
    status_2 = json.loads(status_file.read_text())
    assert status_2.get("status") == "ok"
    assert datetime.datetime.fromisoformat(status_2.get("utc")) > datetime.datetime.fromisoformat(status_1.get("utc"))

    # second problem
    flag.touch()
    time.sleep(0.2)
    status_3 = json.loads(status_file.read_text())
    assert status_3.get("status") == "ok"
    assert datetime.datetime.fromisoformat(status_3.get("utc")) > datetime.datetime.fromisoformat(status_2.get("utc"))

    # normal interruption
    event.set()
    thread.join()

    assert capsys.readouterr().out == OK_OUTPUT.format(configuration_directory, flag)
