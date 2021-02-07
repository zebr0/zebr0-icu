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


def test_execute():
    assert heal.execute("/bin/true")
    assert not heal.execute("/bin/false")


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

# todo: full tests
