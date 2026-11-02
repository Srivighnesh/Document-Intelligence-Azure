from src.processing.text_select import compact, select_relevant


def test_select_relevant_keeps_matches_and_context_without_duplicates() -> None:
    lines = ["header", "address", "context", "next", "footer"]

    assert select_relevant(lines, ("address",), context=2) == [
        "address",
        "context",
        "next",
    ]


def test_select_relevant_deduplicates_overlapping_context() -> None:
    lines = ["first", "match one", "match two", "last"]

    assert select_relevant(lines, ("match",), context=2) == [
        "match one",
        "match two",
        "last",
    ]


def test_select_relevant_falls_back_to_first_three_lines() -> None:
    lines = ["one", "two", "three", "four"]

    assert select_relevant(lines, ("missing",)) == ["one", "two", "three"]


def test_compact_collapses_whitespace_and_cuts_on_word_boundary() -> None:
    assert compact("one\t two\n\n\nthree four", 12) == "one two"
