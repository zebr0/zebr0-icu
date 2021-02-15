import heal

FILE_1 = """
---
- lorem
- ipsum
- dolor
- sit
- amet
""".lstrip()

FILE_2 = """
---
- consectetur
- adipiscing
- elit
""".lstrip()


def test_yield_config_from_disk_ok(tmp_path):
    tmp_path.joinpath("file1.yml").write_text(FILE_1, encoding=heal.ENCODING)
    tmp_path.joinpath("file2.yml").write_text(FILE_2, encoding=heal.ENCODING)

    assert sorted(heal.yield_config_from_disk(tmp_path)) == ["adipiscing", "amet", "consectetur", "dolor", "elit", "ipsum", "lorem", "sit"]


def test_filter_modes_and_checks_ok():
    modes, checks = heal.filter_modes_and_checks([{"check": "", "fix": "", "rank": "10"},
                                                  {"check": "", "fix": "", "rank": "10", "when": ""},
                                                  {"mode": "", "if": ""}])

    assert modes == [{"mode": "", "if": ""}]
    assert checks == [{"check": "", "fix": "", "rank": 10},
                      {"check": "", "fix": "", "rank": 10, "when": ""}]


def test_filter_modes_and_checks_ko():
    assert heal.filter_modes_and_checks([
        {"check": "", "fix": ""},
        {"check": "", "fix": "", "rank": "10", "then": ""},
        {"check": "", "fix": "", "rank": "max"},
        {"check": "", "fix": "", "rank": {}},
        {"check": "", "fix": "", "rank": []},
        {"mode": ""},
        {"mode": "", "if": "", "bonus": ""},
        {"check": "", "fix": "", "rank": "10", "mode": "", "if": ""},
        {},
        {"how": ""},
        "check"
    ]) == ([], [])


def test_filter_current_modes_ok():
    assert heal.filter_current_modes([
        {"mode": "one", "if": "/bin/true"},
        {"mode": "two", "if": "/bin/false"}
    ]) == ["one"]
