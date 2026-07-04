from tools import (
    run_bash,
    read_file,
    write_file,
    edit,
    search,
    TOOLS,
    TOOL_HANDLERS,
    NEEDS_CONFIRMATION,
)


# --- run_bash ---

def test_run_bash_returns_stdout():
    output = run_bash("echo hello")
    assert output == "hello"


def test_run_bash_times_out():
    output = run_bash("sleep 2", timeout=1)
    assert "超时" in output


# --- read_file ---

def test_read_file_basic(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("line one\nline two\n")

    output = read_file(str(f))

    assert "     1\tline one" in output
    assert "     2\tline two" in output


def test_read_file_missing(tmp_path):
    missing = tmp_path / "nope.txt"

    output = read_file(str(missing))

    assert "不存在" in output


def test_read_file_directory(tmp_path):
    output = read_file(str(tmp_path))

    assert "目录" in output


def test_read_file_offset_and_limit(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("\n".join(f"line {i}" for i in range(1, 11)) + "\n")

    output = read_file(str(f), offset=3, limit=2)

    assert "     3\tline 3" in output
    assert "     4\tline 4" in output
    assert "line 2" not in output
    assert "line 5" not in output


def test_read_file_binary(tmp_path):
    f = tmp_path / "sample.bin"
    f.write_bytes(bytes([0xFF, 0xFE, 0x00, 0x80, 0x81]))

    output = read_file(str(f))

    assert "无法读取" in output


# --- write_file ---

def test_write_file_creates_new_file(tmp_path):
    target = tmp_path / "new.txt"

    output = write_file(str(target), "hello world")

    assert target.read_text() == "hello world"
    assert "已写入" in output


def test_write_file_overwrites_existing(tmp_path):
    target = tmp_path / "existing.txt"
    target.write_text("old content")

    write_file(str(target), "new content")

    assert target.read_text() == "new content"


def test_write_file_creates_parent_dirs(tmp_path):
    target = tmp_path / "nested" / "dir" / "file.txt"

    write_file(str(target), "content")

    assert target.read_text() == "content"


# --- edit ---

def test_edit_replaces_unique_match(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("foo bar baz")

    output = edit(str(f), "bar", "qux")

    assert f.read_text() == "foo qux baz"
    assert "错误" not in output


def test_edit_not_found(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("foo bar baz")

    output = edit(str(f), "nope", "qux")

    assert "未找到" in output
    assert f.read_text() == "foo bar baz"


def test_edit_ambiguous_multiple_matches(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("foo bar foo")

    output = edit(str(f), "foo", "qux")

    assert "2 处匹配" in output
    assert f.read_text() == "foo bar foo"


def test_edit_replace_all(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("foo bar foo")

    edit(str(f), "foo", "qux", replace_all=True)

    assert f.read_text() == "qux bar qux"


# --- search ---

def test_search_finds_match(tmp_path):
    (tmp_path / "a.py").write_text("def hello():\n    pass\n")
    (tmp_path / "b.py").write_text("def other():\n    pass\n")

    output = search("hello", path=str(tmp_path))

    assert "a.py:1:" in output
    assert "b.py" not in output


def test_search_no_match(tmp_path):
    (tmp_path / "a.py").write_text("def hello():\n    pass\n")

    output = search("notfound", path=str(tmp_path))

    assert "未找到" in output


def test_search_file_glob_filter(tmp_path):
    (tmp_path / "a.py").write_text("target\n")
    (tmp_path / "a.txt").write_text("target\n")

    output = search("target", path=str(tmp_path), file_glob="*.py")

    assert "a.py:1:" in output
    assert "a.txt" not in output


def test_search_skips_hidden_and_venv_dirs(tmp_path):
    skip_dir = tmp_path / ".venv"
    skip_dir.mkdir()
    (skip_dir / "lib.py").write_text("target\n")
    (tmp_path / "real.py").write_text("target\n")

    output = search("target", path=str(tmp_path))

    assert "real.py:1:" in output
    assert ".venv" not in output


def test_search_truncates_at_max_results(tmp_path):
    for i in range(5):
        (tmp_path / f"f{i}.py").write_text("target\n")

    output = search("target", path=str(tmp_path), max_results=2)

    assert output.count("target") == 2
    assert "截断" in output


def test_search_skips_binary_files(tmp_path):
    (tmp_path / "bin.dat").write_bytes(bytes([0xFF, 0xFE, 0x00, 0x80]))
    (tmp_path / "real.py").write_text("target\n")

    output = search("target", path=str(tmp_path))

    assert "real.py:1:" in output


# --- tool registry ---

def test_tools_schema_names_match_handlers():
    schema_names = {tool["name"] for tool in TOOLS}
    handler_names = set(TOOL_HANDLERS.keys())

    assert schema_names == handler_names
    assert schema_names == {
        "run_bash",
        "read_file",
        "write_file",
        "edit",
        "search",
        "list_dir",
    }


def test_needs_confirmation_is_subset_of_tool_names():
    schema_names = {tool["name"] for tool in TOOLS}

    assert NEEDS_CONFIRMATION == {"run_bash", "write_file", "edit"}
    assert NEEDS_CONFIRMATION <= schema_names
