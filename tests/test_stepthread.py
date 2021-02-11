import threading
import time

import pytest

import heal
from heal import Status


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


def test_ok(tmp_path, capsys):
    thread = heal.StepThread({"if-not": f"echo ok && touch {tmp_path}/touch"})
    thread.start()
    time.sleep(0.1)

    assert thread.status == Status.OK
    assert tmp_path.joinpath("touch").is_file()
    assert capsys.readouterr().out == ""


def test_ko_stays_ko(tmp_path, capsys):
    thread = heal.StepThread({"if-not": f"touch {tmp_path}/touch"})
    thread.status = Status.KO
    thread.start()
    time.sleep(0.1)
    thread.stop()
    thread.join()

    assert thread.status == Status.KO
    assert not tmp_path.joinpath("touch").exists()
    assert capsys.readouterr().out == ""


def test_loop(tmp_path):
    heal.StepThread({"delay": 0.2, "if-not": f"echo test >> {tmp_path}/loop"}).start()
    time.sleep(0.3)

    assert tmp_path.joinpath("loop").read_text() == "test\ntest\n"


FIXED_WITH_PROGRESS_1 = """
#0733d1bb {{"if-not": "test -f {0}/touch", "then": "echo test && sleep 1 && echo test && touch {0}/touch"}}
#0733d1bb test failed, fixing
#0733d1bb test
""".lstrip()

FIXED_WITH_PROGRESS_2 = """
#0733d1bb test
#0733d1bb fixed
""".lstrip()


def test_fixed_with_progress(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(heal.util, "generate_uid", lambda a: "#0733d1bb")

    thread = heal.StepThread({"if-not": f"test -f {tmp_path}/touch", "then": f"echo test && sleep 1 && echo test && touch {tmp_path}/touch"})
    thread.start()
    time.sleep(0.1)

    assert thread.status == Status.FIXING
    assert capsys.readouterr().out == FIXED_WITH_PROGRESS_1.format(tmp_path)

    time.sleep(1)

    assert thread.status == Status.OK
    assert capsys.readouterr().out == FIXED_WITH_PROGRESS_2


KO_WITH_ERROR = """
#f4104b1a {"if-not": "/bin/false", "then": "echo test && /bin/false"}
#f4104b1a test failed, fixing
#f4104b1a test
#f4104b1a error!
#f4104b1a test still failed: fatal error!
""".lstrip()


def test_ko_with_error(monkeypatch, capsys):
    thread = heal.StepThread({"if-not": "/bin/false", "then": "echo test && /bin/false"})
    thread.start()
    time.sleep(0.1)

    assert thread.status == Status.KO
    assert capsys.readouterr().out == KO_WITH_ERROR
