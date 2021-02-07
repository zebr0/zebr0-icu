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


MODES_YAML = """
---
- if: "true"
  then-mode: "mode_1"
- if: "false"
  then-mode: "mode_2"
""".lstrip()


def test_get_current_modes_from_threads(tmp_path):
    tmp_path.joinpath("modes.yaml").write_text(MODES_YAML)
    # when there's no thread running
    assert heal.get_current_modes_from_threads() == []

    heal.MasterThread(tmp_path).start()
    time.sleep(.1)
    assert heal.get_current_modes_from_threads() == ["mode_1"]


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
