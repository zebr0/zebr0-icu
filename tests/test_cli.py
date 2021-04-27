import os
import signal
import threading

import time

import heal


def test_ok(tmp_path):
    bloblo = tmp_path.joinpath("blibli")
    bloblo.mkdir()

    def blibli():
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGINT)

    threading.Thread(target=blibli).start()
    heal.main(["-d", str(bloblo), "-f", str(tmp_path.joinpath("bliablia")), "-t", "0.2"])
