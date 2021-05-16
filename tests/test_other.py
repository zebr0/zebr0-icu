import datetime
import json

import heal.util


def test_is_file_ko_directory(tmp_path):
    assert not heal.util.is_file_ko(tmp_path)


def test_is_file_ko_no_file(tmp_path):
    assert not heal.util.is_file_ko(tmp_path.joinpath("blibli"))


def test_is_file_ko_empty_file(tmp_path):
    joinpath = tmp_path.joinpath("blibli")
    joinpath.touch()

    assert not heal.util.is_file_ko(joinpath)


def test_is_file_ko_binary(tmp_path):
    binary_path = tmp_path.joinpath("foo")
    binary_path.write_bytes(bytes([0x99]))

    assert not heal.util.is_file_ko(binary_path)


def test_is_file_ko_normal_text(tmp_path):
    text_path = tmp_path.joinpath("text")
    text_path.write_text("hello")

    assert not heal.util.is_file_ko(text_path)


def test_is_file_ko_wrong_json(tmp_path):
    text_path = tmp_path.joinpath("text")
    text_path.write_text(json.dumps({"foo": "bar"}))

    assert not heal.util.is_file_ko(text_path)


def test_is_file_ko_status_ok(tmp_path):
    text_path = tmp_path.joinpath("text")
    text_path.write_text(json.dumps({"status": "ok"}))

    assert not heal.util.is_file_ko(text_path)


def test_is_file_ko_status_ko(tmp_path):
    text_path = tmp_path.joinpath("text")
    text_path.write_text(json.dumps({"status": "ko"}))

    assert heal.util.is_file_ko(text_path)


def test_write_file(tmp_path):
    file = tmp_path.joinpath("test")
    utc = datetime.datetime.utcnow().isoformat()
    heal.util.write_file(file, ["one", "two"], "ok", utc)

    assert json.loads(file.read_text()) == {"utc": utc, "status": "ok", "modes": ["one", "two"]}
