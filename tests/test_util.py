import heal.util

PRINT_OUTPUT_OK_OUTPUT = """
[x] result: command
[x] output: line 1
[x] output: line 2
""".lstrip()


def test_print_output_ok(capsys):
    heal.util.print_output("command", "result", ["line 1", "line 2"], "[x]")
    assert capsys.readouterr().out == PRINT_OUTPUT_OK_OUTPUT


WRITE_OK_TEXT = """
{
  "timestamp": "1970-01-01T00:00:00+00:00",
  "status": "ok",
  "modes": [
    "alpha",
    "beta"
  ]
}""".lstrip()


def test_write_ok(tmp_path):
    status_file = tmp_path.joinpath("dummy")
    heal.util.write(status_file, ["alpha", "beta"], "ok", 0)
    assert status_file.read_text() == WRITE_OK_TEXT


def test_is_ko_directory(tmp_path):
    assert not heal.util.is_ko(tmp_path)


def test_is_ko_no_file(tmp_path):
    assert not heal.util.is_ko(tmp_path.joinpath("file-does-not-exist-yet"))


def test_is_ko_empty(tmp_path):
    empty_file = tmp_path.joinpath("empty-file")
    empty_file.touch()

    assert not heal.util.is_ko(empty_file)


def test_is_ko_binary(tmp_path):
    binary_file = tmp_path.joinpath("binary-file")
    binary_file.write_bytes(bytes([0x99]))

    assert not heal.util.is_ko(binary_file)


def test_is_ko_plain_text(tmp_path):
    plain_text_file = tmp_path.joinpath("plain-text")
    plain_text_file.write_text("lorem ipsum")

    assert not heal.util.is_ko(plain_text_file)


def test_is_ko_wrong_json(tmp_path):
    wrong_json_file = tmp_path.joinpath("wrong-json")
    wrong_json_file.write_text('{"foo": "bar"}')

    assert not heal.util.is_ko(wrong_json_file)


def test_is_ko_status_ok(tmp_path):
    status_ok_file = tmp_path.joinpath("status-ok")
    status_ok_file.write_text('{"status": "ok"}')

    assert not heal.util.is_ko(status_ok_file)


def test_is_ko_status_ko(tmp_path):
    status_ko_file = tmp_path.joinpath("status-ko")
    status_ko_file.write_text('{"status": "ko"}')

    assert heal.util.is_ko(status_ko_file)
