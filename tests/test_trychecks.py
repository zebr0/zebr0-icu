import threading

import pytest
import time

import heal


def print_status(status):
    print("status:", status)


def test_ok(capsys):
    heal.try_checks([
        {"check": "echo one"},
        {"check": "echo two"}
    ], update_status=print_status)
    assert capsys.readouterr().out == "status: ok\n"  # output is not shown for checks that succeed


FIX_WITH_PROGRESSIVE_OUTPUT_1 = """
[10] failed: echo output of the failed test && [ -f {0} ]
[10] output: output of the failed test
status: fixing
[10] fixing: echo one && sleep 1 && echo two && touch {0}
[10] output: one
""".lstrip()

FIX_WITH_PROGRESSIVE_OUTPUT_2 = """
[10] output: two
[10] fix successful
status: ok
""".lstrip()


def test_fix_with_progressive_output(tmp_path, capsys):
    flag = tmp_path.joinpath("flag")

    # here we run try_checks in a thread to be able to test the output
    thread = threading.Thread(target=lambda: heal.try_checks([
        {"check": f"echo output of the failed test && [ -f {flag} ]", "fix": f"echo one && sleep 1 && echo two && touch {flag}", "rank": 10}
    ], update_status=print_status))
    thread.start()

    time.sleep(0.1)
    assert capsys.readouterr().out == FIX_WITH_PROGRESSIVE_OUTPUT_1.format(flag)

    thread.join()
    assert capsys.readouterr().out == FIX_WITH_PROGRESSIVE_OUTPUT_2


KO_OUTPUT = """
[5] failed: echo doomed && false
[5] output: doomed
status: fixing
[5] fixing: false
[5] failed again: echo doomed && false
[5] output: doomed
""".lstrip()


def test_ko(capsys):
    with pytest.raises(ChildProcessError):
        heal.try_checks([
            {"check": "echo doomed && false", "fix": "false", "rank": 5}
        ], update_status=print_status)
    assert capsys.readouterr().out == KO_OUTPUT


RECURSION_OK_OUTPUT = """
[10] failed: [ -f {0} ]
status: fixing
[10] fixing: sleep 1 && touch {0}
[10] fix successful
status: ok
""".lstrip()

RECURSION_OK_LOG = """
ok
ok
ok
""".lstrip()


def test_recursion_ok(tmp_path, capsys):
    log = tmp_path.joinpath("log")
    flag = tmp_path.joinpath("flag")

    # here the first check will be done once, then the second check will fail
    # while the fix for the second check runs (1 second), the previous successful check will run twice since the delay is set to 0.4 second
    heal.try_checks([
        {"check": f"echo ok >> {log}"},
        {"check": f"[ -f {flag} ]", "fix": f"sleep 1 && touch {flag}", "rank": 10}
    ], 0.4, update_status=print_status)

    assert capsys.readouterr().out == RECURSION_OK_OUTPUT.format(flag)
    assert log.read_text() == RECURSION_OK_LOG


DOUBLE_RECURSION_OK_OUTPUT = """
[9] failed: [ -f {1} ]
status: fixing
[9] fixing: sleep 1 && touch {1}
[7] failed: [ ! -f {0} ] && touch {0}
[7] fixing: sleep 1 && rm {0}
[7] fix successful
[9] fix successful
status: ok
""".lstrip()

DOUBLE_RECURSION_OK_LOG = """
ok
ok
ok
ok
""".lstrip()


def test_double_recursion_ok(tmp_path, capsys):
    log = tmp_path.joinpath("log")
    flag1 = tmp_path.joinpath("flag1")
    flag2 = tmp_path.joinpath("flag2")

    # here the first two checks will succeed, but not the third
    # so while the fix for the third check runs (1 second), the first two checks will be executed again 0.4 seconds later
    # but then only the first will succeed, the second will fail
    # so while the fix for the second check runs (1 second), the first one will be executed two more times
    heal.try_checks([
        {"check": f"echo ok >> {log}"},  # succeeds everytime
        {"check": f"[ ! -f {flag1} ] && touch {flag1}", "fix": f"sleep 1 && rm {flag1}", "rank": 7},  # succeeds then fails
        {"check": f"[ -f {flag2} ]", "fix": f"sleep 1 && touch {flag2}", "rank": 9}  # fails every time
    ], 0.4, update_status=print_status)

    assert capsys.readouterr().out == DOUBLE_RECURSION_OK_OUTPUT.format(flag1, flag2)
    assert log.read_text() == DOUBLE_RECURSION_OK_LOG


RECURSION_KO_OUTPUT = """
[11] failed: [ -f {1} ]
status: fixing
[11] fixing: sleep 1 && touch {1}
[6] failed: [ ! -f {0} ] && touch {0}
[6] fixing: true
[6] failed again: [ ! -f {0} ] && touch {0}
""".lstrip()


def test_recursion_ko(tmp_path, capsys):
    flag1 = tmp_path.joinpath("flag1")
    flag2 = tmp_path.joinpath("flag2")

    # here the first check will succeed but the second will fail
    # so while the fix for the second check runs (1 second), the first check will be executed again 0.4 second later
    # but then it will fail, and the fix won't actually fix anything, so everything shuts down with an exception
    with pytest.raises(ChildProcessError):
        heal.try_checks([
            {"check": f"[ ! -f {flag1} ] && touch {flag1}", "fix": "true", "rank": 6},  # succeeds then fails, but won't fix
            {"check": f"[ -f {flag2} ]", "fix": f"sleep 1 && touch {flag2}", "rank": 11}  # fails every time
        ], 0.4, update_status=print_status)

    assert capsys.readouterr().out == RECURSION_KO_OUTPUT.format(flag1, flag2)
