import time

import heal


def test_ok(capsys):
    ft = heal.FixThread("echo ok")
    ft.start()
    ft.join()
    assert capsys.readouterr().out == "fixing: echo ok\nok\n"


def test_ko(capsys):
    ft = heal.FixThread("false")
    ft.start()
    ft.join()
    assert capsys.readouterr().out == "fixing: false\nerror! return code: 1\n"


def test_progressive_output(capsys):
    ft = heal.FixThread("echo one && sleep 1 && echo two")
    ft.start()
    time.sleep(0.1)
    assert capsys.readouterr().out == "fixing: echo one && sleep 1 && echo two\none\n"
    ft.join()
    assert capsys.readouterr().out == "two\n"
