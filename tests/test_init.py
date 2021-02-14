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
