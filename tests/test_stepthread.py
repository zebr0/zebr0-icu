import threading
import time

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
