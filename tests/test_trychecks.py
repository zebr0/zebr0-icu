import threading
import time

import pytest

import heal


def test_ok(capsys):
    heal.try_checks([
        {"check": "echo one"},
        {"check": "echo two"}
    ])
    assert capsys.readouterr().out == ""


III = """
[10] failed(1): [ -f {0} ]
[10] fixing: echo one && sleep 1 && echo two && touch {0}
[10] output: one
""".lstrip()


def test_progressive_output(tmp_path, capsys):
    flag = tmp_path.joinpath("flag")

    def blibli():
        heal.try_checks([
            {"check": f"[ -f {flag} ]", "fix": f"echo one && sleep 1 && echo two && touch {flag}", "rank": 10}
        ])

    t = threading.Thread(target=blibli)
    t.start()
    time.sleep(0.5)
    assert capsys.readouterr().out == III.format(flag)
    t.join()
    assert capsys.readouterr().out == "[10] output: two\n[10] fix successful\n"


EEE = """
[20] failed(1): echo test && echo test && [ -f {0} ]
[20] output: test
[20] output: test
[20] fixing: echo touch && touch {0}
[20] output: touch
[20] fix successful
""".lstrip()


def test_fix(tmp_path, capsys):
    flag = tmp_path.joinpath("flag")

    heal.try_checks([
        {"check": f"echo test && echo test && [ -f {flag} ]", "fix": f"echo touch && touch {flag}", "rank": 20}
    ])
    assert capsys.readouterr().out == EEE.format(flag)


DDD = """
[5] failed(1): echo doomed && false
[5] output: doomed
[5] fixing: false
[5] warning! fix returned code 1
[5] failed(1): echo doomed && false
[5] output: doomed
""".lstrip()


def test_ko(capsys):
    with pytest.raises(ChildProcessError):
        heal.try_checks([
            {"check": "echo doomed && false", "fix": "false", "rank": 5}
        ])
    assert capsys.readouterr().out == DDD


FFF = """
[10] failed(1): [ -f {0} ]
[10] fixing: sleep 1 && touch {0}
[10] fix successful
""".lstrip()


def test_goodchecks_ok(tmp_path, capsys):
    flag = tmp_path.joinpath("flag")
    goodchecks = tmp_path.joinpath("goodchecks")

    heal.try_checks([
        {"check": f"echo good >> {goodchecks}"},
        {"check": f"[ -f {flag} ]", "fix": f"sleep 1 && touch {flag}", "rank": 10}
    ], 0.4)
    assert capsys.readouterr().out == FFF.format(flag)
    assert goodchecks.read_text() == "good\ngood\ngood\n"


PPP = """
[9] failed(1): [ -f {1} ]
[9] fixing: sleep 1 && touch {1}
[7] failed(1): [ ! -f {0} ] && touch {0}
[7] fixing: rm {0}
[7] fix successful
[9] fix successful
""".lstrip()


def test_goodchecks_ko(tmp_path, capsys):
    flag1 = tmp_path.joinpath("flag1")
    flag2 = tmp_path.joinpath("flag2")

    heal.try_checks([
        {"check": f"[ ! -f {flag1} ] && touch {flag1}", "fix": f"rm {flag1}", "rank": 7},
        {"check": f"[ -f {flag2} ]", "fix": f"sleep 1 && touch {flag2}", "rank": 9}
    ], 0.8)
    assert capsys.readouterr().out == PPP.format(flag1, flag2)


LLL = """
[11] failed(1): [ -f {1} ]
[11] fixing: sleep 1 && touch {1}
[6] failed(1): [ ! -f {0} ] && touch {0}
[6] fixing: true
[6] failed(1): [ ! -f {0} ] && touch {0}
""".lstrip()


def test_goodchecks_exception(tmp_path, capsys):
    flag1 = tmp_path.joinpath("flag1")
    flag2 = tmp_path.joinpath("flag2")

    with pytest.raises(ChildProcessError):
        heal.try_checks([
            {"check": f"[ ! -f {flag1} ] && touch {flag1}", "fix": f"true", "rank": 6},  # c'est dans la récursion que ce test fail et que le test fail > exception
            {"check": f"[ -f {flag2} ]", "fix": f"sleep 1 && touch {flag2}", "rank": 11}
        ], 0.4)
    assert threading.active_count() == 2  # le thread du fix du deuxième test reste actif
    assert capsys.readouterr().out == LLL.format(flag1, flag2)
    time.sleep(0.7)
    assert capsys.readouterr().out == ""
