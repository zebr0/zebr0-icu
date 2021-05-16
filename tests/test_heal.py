import threading

import time

import heal


def test_not_a_directory(tmp_path, capsys):
    heal.heal(tmp_path.joinpath("fake"), tmp_path, None)
    assert capsys.readouterr().out == "directory must exist\n"


def test_ko_before(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(heal, "is_file_ko", lambda _: True)
    heal.heal(tmp_path, tmp_path, None)

    assert capsys.readouterr().out == "system already in failed status, exiting\n"


EEE = """
watching configuration directory: {0}
configuration directory has changed
reading configuration
done
filtering modes and checks
done
try_checks([], 0.2)
try_checks([], 0.2)
""".lstrip()


def test_ok(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(heal, "try_checks", lambda i, j, _: print(f"try_checks{i, j}"))

    event = threading.Event()

    threading.Thread(target=heal.heal, args=(tmp_path, tmp_path, event, 0.2)).start()
    time.sleep(0.3)
    event.set()
    time.sleep(0.01)

    assert capsys.readouterr().out == EEE.format(tmp_path)


FFF = """
watching configuration directory: {0}
configuration directory has changed
reading configuration
done
filtering modes and checks
done
write(PosixPath('{0}'), [], 'ko')
critical failure, exiting
""".lstrip()


def test_ko_after(monkeypatch, tmp_path, capsys):
    def blibli(i, j, k):
        raise ChildProcessError()

    monkeypatch.setattr(heal, "try_checks", blibli)
    monkeypatch.setattr(heal, "write", lambda i, j, k: print(f"write{i, j, k}"))

    event = threading.Event()

    threading.Thread(target=heal.heal, args=(tmp_path, tmp_path, event, 0.2)).start()
    time.sleep(0.01)

    assert capsys.readouterr().out == FFF.format(tmp_path)
