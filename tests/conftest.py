import threading

import pytest

import heal


@pytest.fixture(autouse=True)
def clean_before_and_after():
    def clean():
        for thread in threading.enumerate():
            if isinstance(thread, heal.util.StoppableThread):
                thread.stop()
                thread.join()

    clean()
    yield  # see https://stackoverflow.com/questions/22627659/run-code-before-and-after-each-test-in-py-test
    clean()
