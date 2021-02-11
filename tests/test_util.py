import time

import heal


class TestThread(heal.util.LoopThread):
    def loop(self):
        print("ha", end="")


def test_loopthread(capsys):
    thread = TestThread(0.2)
    thread.start()
    time.sleep(0.3)
    thread.stop()
    thread.join()

    assert capsys.readouterr().out == "haha"


def test_generate_uid():
    assert heal.util.generate_uid({"yin": "yang"}) == "#0733d1bb"
