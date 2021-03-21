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
failed: [ -f {0} ]
return code: 1
stdout: 
fixing: echo one && sleep 1 && echo two && touch {0}
one
""".lstrip()


def test_progressive_output(tmp_path, capsys):
    flag = tmp_path.joinpath("flag")

    def blibli():
        heal.try_checks([
            {"check": f"[ -f {flag} ]", "fix": f"echo one && sleep 1 && echo two && touch {flag}"}
        ])

    t = threading.Thread(target=blibli)
    t.start()
    time.sleep(0.5)
    assert capsys.readouterr().out == III.format(flag)
    t.join()
    assert capsys.readouterr().out == "two\nfix succeeded!\n"


EEE = """
failed: echo test && echo test && [ -f {0} ]
return code: 1
stdout: test
test
fixing: echo touch && touch {0}
touch
fix succeeded!
""".lstrip()


def test_fix(tmp_path, capsys):
    flag = tmp_path.joinpath("flag")

    heal.try_checks([
        {"check": f"echo test && echo test && [ -f {flag} ]", "fix": f"echo touch && touch {flag}"}
    ])
    assert capsys.readouterr().out == EEE.format(flag)


DDD = """
failed: false
return code: 1
stdout: 
fixing: false
error! return code: 1
""".lstrip()


def test_ko(capsys):
    with pytest.raises(Exception):
        heal.try_checks([
            {"check": "false", "fix": "false"}
        ])
    assert capsys.readouterr().out == DDD


FFF = """
failed: [ -f {0} ]
return code: 1
stdout: 
fixing: sleep 1 && touch {0}
fix succeeded!
""".lstrip()


def test_goodchecks_ok(tmp_path, capsys):
    flag = tmp_path.joinpath("flag")
    goodchecks = tmp_path.joinpath("goodchecks")

    heal.try_checks([
        {"check": f"echo good >> {goodchecks}"},
        {"check": f"[ -f {flag} ]", "fix": f"sleep 1 && touch {flag}"}
    ], 0.4)
    assert capsys.readouterr().out == FFF.format(flag)
    assert goodchecks.read_text() == "good\ngood\ngood\n"


PPP = """
failed: [ -f {1} ]
return code: 1
stdout: 
fixing: sleep 1 && touch {1}
failed: [ ! -f {0} ] && touch {0}
return code: 1
stdout: 
fixing: rm {0}
fix succeeded!
fix succeeded!
""".lstrip()  # todo: problem: which thread?


def test_goodchecks_ko(tmp_path, capsys):
    flag1 = tmp_path.joinpath("flag1")
    flag2 = tmp_path.joinpath("flag2")

    heal.try_checks([
        {"check": f"[ ! -f {flag1} ] && touch {flag1}", "fix": f"rm {flag1}"},
        {"check": f"[ -f {flag2} ]", "fix": f"sleep 1 && touch {flag2}"}
    ], 0.8)
    assert capsys.readouterr().out == PPP.format(flag1, flag2)


LLL = """
failed: [ -f {1} ]
return code: 1
stdout: 
fixing: sleep 1 && touch {1}
failed: [ ! -f {0} ] && touch {0}
return code: 1
stdout: 
fixing: true
""".lstrip()


def test_goodchecks_exception(tmp_path, capsys):
    flag1 = tmp_path.joinpath("flag1")
    flag2 = tmp_path.joinpath("flag2")

    with pytest.raises(Exception):
        heal.try_checks([
            {"check": f"[ ! -f {flag1} ] && touch {flag1}", "fix": f"true"},  # c'est dans la récursion que ce test fail et que le test fail > exception
            {"check": f"[ -f {flag2} ]", "fix": f"sleep 1 && touch {flag2}"}
        ], 0.4)
    assert threading.active_count() == 2  # le thread du fix du deuxième test reste actif
    assert capsys.readouterr().out == LLL.format(flag1, flag2)
    time.sleep(0.7)
    assert capsys.readouterr().out == ""
