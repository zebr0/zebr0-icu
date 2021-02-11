import threading
import time

import pytest

import heal


@pytest.fixture(autouse=True)
def clean_before_and_after():
    def clean():
        # safety net: stops any remaining StoppableThread at the end of each test, so that nothing gets stuck
        for thread in threading.enumerate():
            if isinstance(thread, heal.util.StoppableThread):
                thread.stop()
                thread.join()

    clean()
    yield  # see https://stackoverflow.com/questions/22627659/run-code-before-and-after-each-test-in-py-test
    clean()


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

# todo: test_masterthread
