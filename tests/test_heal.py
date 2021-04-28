import threading

import time

import heal


def test_ko_before(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(heal, "is_file_ko", lambda _: True)
    heal.heal(tmp_path, tmp_path, None)

    assert capsys.readouterr().out == "system already in failed status, exiting\n"


EEE = """
directory {0} has changed
reading configuration
done
filtering modes and checks from config
done filtering modes and checks from config
try_checks([], PosixPath('{0}'), [], 0.2, True)
try_checks([], PosixPath('{0}'), [], 0.2, True)
""".lstrip()


def test_ok(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(heal, "try_checks", lambda i, j, k, l, m: print(f"try_checks{i, j, k, l, m}"))

    event = threading.Event()

    threading.Thread(target=heal.heal, args=(tmp_path, tmp_path, event, 0.2)).start()
    time.sleep(0.3)
    event.set()
    time.sleep(0.01)

    assert capsys.readouterr().out == EEE.format(tmp_path)


FFF = """
directory {0} has changed
reading configuration
done
filtering modes and checks from config
done filtering modes and checks from config
write_file(PosixPath('{0}'), 'ko', [])
critical failure, exiting
""".lstrip()


def test_ko_after(monkeypatch, tmp_path, capsys):
    def blibli(i, j, k, l, m):
        raise ChildProcessError()

    monkeypatch.setattr(heal, "try_checks", blibli)
    monkeypatch.setattr(heal, "write_file", lambda i, j, k: print(f"write_file{i, j, k}"))

    event = threading.Event()

    threading.Thread(target=heal.heal, args=(tmp_path, tmp_path, event, 0.2)).start()
    time.sleep(0.01)

    assert capsys.readouterr().out == FFF.format(tmp_path)
