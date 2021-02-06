import json
import threading
import time
import urllib.request

import dateutil.parser
import pytest

import heal


@pytest.fixture(autouse=True)
def clean_before_and_after():
    def clean():
        # safety net: stops any remaining StoppableThread at the end of each test, so that nothing gets stuck
        for thread in threading.enumerate():
            if isinstance(thread, heal.StoppableThread):
                thread.stop()
                thread.join()

    clean()
    yield  # see https://stackoverflow.com/questions/22627659/run-code-before-and-after-each-test-in-py-test
    clean()


def test_execute():
    assert heal.execute("/bin/true")
    assert not heal.execute("/bin/false")


MODE_1 = {"if": "true", "then-mode": "mode_1"}
MODE_2 = {"if": "false", "then-mode": "mode_2"}
MODES_YAML = """
---
- if: "true"
  then-mode: "mode_1"
- if: "false"
  then-mode: "mode_2"
""".lstrip()


def test_read_configuration(tmp_path):
    tmp_path.joinpath("modes.yaml").write_text(MODES_YAML)
    # here we only need to test if the file is parsed correctly
    assert heal.read_configuration(tmp_path) == [MODE_1, MODE_2]


STEP_1 = {"if-not": "true", "and-if-mode": "mode_1", "then": "false"}
STEP_2 = {"if-not": "true", "and-if-mode": "mode_2", "then": "false"}
STEP_3 = {"if-not": "true", "then": "false"}
CONFIGURATION = [MODE_1, MODE_2, STEP_1, STEP_2, STEP_3]


def test_get_current_modes():
    assert heal.get_current_modes(CONFIGURATION) == ["mode_1"]
    assert heal.get_current_modes([STEP_1, STEP_2, STEP_3]) == []  # only steps here


def test_get_expected_steps():
    assert heal.get_expected_steps(CONFIGURATION, []) == [STEP_3]
    assert heal.get_expected_steps(CONFIGURATION, ["mode_1"]) == [STEP_1, STEP_3]
    assert heal.get_expected_steps(CONFIGURATION, ["mode_2"]) == [STEP_2, STEP_3]


def _get_current_threads():
    return sorted((thread for thread in threading.enumerate() if isinstance(thread, heal.StepThread)), key=lambda thread: str(thread.step))


def test_converge_threads():
    # ensure there's no thread running
    assert not _get_current_threads()

    # create a first thread
    heal.converge_threads([STEP_1])
    current_threads = _get_current_threads()
    assert len(current_threads) == 1
    thread_1 = current_threads[0]
    assert thread_1.step == STEP_1

    # create a second thread
    heal.converge_threads([STEP_1, STEP_2])
    current_threads = _get_current_threads()
    assert len(current_threads) == 2
    assert id(thread_1) == id(current_threads[0])
    thread_2 = current_threads[1]
    assert thread_2.step == STEP_2

    # remove the first thread
    heal.converge_threads([STEP_2])
    time.sleep(.1)
    current_threads = _get_current_threads()
    assert len(current_threads) == 1
    assert id(thread_2) == id(current_threads[0])

    # remove the second thread
    heal.converge_threads([])
    time.sleep(.1)
    assert not _get_current_threads()


def test_get_status_from_threads():
    # when there's no thread running
    assert heal.get_status_from_threads() == "OK"

    # when there's a successful thread running
    heal.StepThread({"if-not": "true", "then": "false"}).start()
    time.sleep(.1)
    assert heal.get_status_from_threads() == "OK"

    # adding a "fixing" thread to the pool must change the status to "fixing"
    heal.StepThread({"if-not": "false", "then": "sleep 1"}).start()
    time.sleep(.1)
    assert heal.get_status_from_threads() == "FIXING"

    # adding a "ko" thread to the pool must change the status to "ko"
    heal.StepThread({"if-not": "false", "then": "false"}).start()
    time.sleep(.1)
    assert heal.get_status_from_threads() == "KO"


def test_get_current_modes_from_threads(tmp_path):
    tmp_path.joinpath("modes.yaml").write_text(MODES_YAML)
    # when there's no thread running
    assert heal.get_current_modes_from_threads() == []

    heal.MasterThread(tmp_path).start()
    time.sleep(.1)
    assert heal.get_current_modes_from_threads() == ["mode_1"]


STEPS_YAML = """
---
- if-not: "true"
  then: "true"
- if-not: "true"
  then: "false"
""".lstrip()


def test_shutdown(tmp_path):
    tmp_path.joinpath("steps.yaml").write_text(STEPS_YAML)
    # create a master and some step threads
    heal.MasterThread(tmp_path).start()
    time.sleep(.1)
    assert len(threading.enumerate()) == 4  # 3 + main thread

    heal.shutdown(None, None)  # parameters are irrelevant
    time.sleep(.1)
    assert len(threading.enumerate()) == 1  # only the main thread now


def test_httpserverthread():
    for _ in range(2):  # twice to check that the socket closes alright
        thread = heal.HTTPServerThread()
        thread.start()
        time.sleep(.1)
        assert thread.is_alive()
        thread.stop()
        thread.join()
        assert not thread.is_alive()


def test_httpserverthread_get():
    heal.HTTPServerThread().start()

    # here we only need to test if the response if valid and the json is good
    with urllib.request.urlopen("http://127.0.0.1:8000") as response:
        assert response.status == 200
        assert response.info().get_content_type() == "application/json"

        response_json = json.load(response)
        dateutil.parser.parse(response_json.get("utc"))
        assert response_json.get("status") == "OK"
        assert response_json.get("modes") == []


def test_stepthread_execute(tmp_path):
    for step in [{"if-not": f"touch {tmp_path}/if-not", "then": "false"},
                 {"if-not": "false", "then": f"touch {tmp_path}/then"}]:
        thread = heal.StepThread(step)
        thread.start()
        time.sleep(.1)
        thread.stop()
        thread.join()

    assert tmp_path.joinpath("if-not").is_file()
    assert tmp_path.joinpath("then").is_file()


def test_stepthread_loop_delay(tmp_path):
    thread = heal.StepThread({"delay": .2, "if-not": f"echo 'test' >> {tmp_path}/loop", "then": "false"})
    thread.start()
    time.sleep(.3)
    thread.stop()
    thread.join()

    assert tmp_path.joinpath("loop").read_text() == "test\ntest\n"


def test_stepthread_status_default_then_ok():
    thread = heal.StepThread({"if-not": "sleep 1", "then": "false"})
    thread.start()
    time.sleep(.5)
    assert thread.status == heal.Status.OK

    thread.stop()
    thread.join()
    assert thread.status == heal.Status.OK


def test_stepthread_status_fixing_then_ok(tmp_path):
    thread = heal.StepThread({"if-not": f"test -f {tmp_path}/fixing_ok", "then": f"sleep 1 && touch {tmp_path}/fixing_ok"})
    thread.start()
    time.sleep(.5)
    assert thread.status == heal.Status.FIXING

    thread.stop()
    thread.join()
    assert thread.status == heal.Status.OK


def test_stepthread_status_fixing_then_ko(tmp_path):
    thread = heal.StepThread({"if-not": f"test -f {tmp_path}/fixing_ko", "then": f"sleep 1 && touch {tmp_path}/fixing_ko && false"})
    thread.start()
    time.sleep(.5)
    assert thread.status == heal.Status.FIXING

    thread.stop()
    thread.join()
    assert thread.status == heal.Status.KO


def test_stepthread_status_still_ko():
    thread = heal.StepThread({"if-not": "false", "then": "sleep 1"})
    thread.start()
    time.sleep(.5)
    assert thread.status == heal.Status.FIXING

    thread.stop()
    thread.join()
    assert thread.status == heal.Status.KO

# todo: test_masterthread
# todo: full tests
