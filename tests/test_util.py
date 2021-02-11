import heal


def test_generate_uid():
    assert heal.util.generate_uid({"yin": "yang"}) == "#0733d1bb"
