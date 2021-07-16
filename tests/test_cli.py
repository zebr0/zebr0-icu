import json
import os
import signal
import threading

import time

import heal

OK_OUTPUT = """
watching: {0}
configuration directory has changed
reading configuration
done
filtering modes and checks
done
exiting: loop-ending signal
""".lstrip()


def test_ok(tmp_path, capsys):
    configuration_directory = tmp_path.joinpath("conf")
    configuration_directory.mkdir()

    status_file = tmp_path.joinpath("status.json")

    def delayed_kill():
        time.sleep(0.5)
        os.kill(os.getpid(), signal.SIGINT)

    threading.Thread(target=delayed_kill).start()

    heal.main(["-c", str(configuration_directory), "-s", str(status_file), "-d", "0.2"])

    assert capsys.readouterr().out == OK_OUTPUT.format(configuration_directory)
    assert json.loads(status_file.read_text(encoding="utf-8")).get("status") == "ok"
