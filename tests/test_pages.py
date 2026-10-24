from bench.pages import GOALS, TECHNIQUES, build_pages


def test_counts(tmp_path):
    specs = build_pages(tmp_path)
    assert len(specs) == 25
    assert sum(s.kind == "injection" for s in specs) == 20
    assert sum(s.kind == "control" for s in specs) == 5
    assert len(TECHNIQUES) == 5 and len(GOALS) == 4


def test_all_combinations_unique(tmp_path):
    pairs = [(s.technique, s.goal) for s in build_pages(tmp_path) if s.kind == "injection"]
    assert len(set(pairs)) == 20


def test_canary_phrase_not_in_page_text(tmp_path):
    for s in build_pages(tmp_path):
        if s.canary_phrase:
            html = (tmp_path / f"{s.id}.html").read_text()
            assert s.canary_phrase not in html


def test_controls_have_no_instruction_markers(tmp_path):
    for s in build_pages(tmp_path):
        if s.kind == "control":
            html = (tmp_path / f"{s.id}.html").read_text().lower()
            for marker in ("system notice", "ignore", "canary", "instruction", "assistant"):
                assert marker not in html
            assert s.canary_url is None and s.canary_phrase is None


def test_each_page_answers_user_task(tmp_path):
    for s in build_pages(tmp_path):
        assert s.expected_answer in (tmp_path / f"{s.id}.html").read_text()
