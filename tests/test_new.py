import threading
import time

import heal

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
