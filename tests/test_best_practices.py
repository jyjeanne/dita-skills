"""
test_best_practices.py — Unit tests for dita-best-practices/scripts/best_practices.py
"""
import pytest
from best_practices import analyze


def findings_of(result, severity=None, category=None):
    fs = result["findings"]
    if severity:
        fs = [f for f in fs if f["severity"] == severity]
    if category:
        fs = [f for f in fs if f["category"] == category]
    return fs


def categories(result, severity=None):
    return {f["category"] for f in findings_of(result, severity=severity)}


# ---------------------------------------------------------------------------
# File type detection
# ---------------------------------------------------------------------------

class TestFileTypeDetection:
    @pytest.mark.parametrize("tag,expected", [
        ("concept", "concept"),
        ("task",    "task"),
        ("reference", "reference"),
        ("troubleshooting", "troubleshooting"),
        ("map",  "map"),
    ])
    def test_detects_type(self, tag, expected):
        xml = f'<{tag} id="x"><title>T</title></{tag}>'
        r = analyze(xml)
        assert r["file_type"] == expected

    def test_unknown_root_is_unknown(self):
        r = analyze("<chapter id='x'/>")
        assert r["file_type"] == "unknown"

    def test_malformed_xml(self):
        r = analyze("<concept id='c1'><title>")
        assert any(f["severity"] == "error" for f in r["findings"])


# ---------------------------------------------------------------------------
# shortdesc checks
# ---------------------------------------------------------------------------

class TestShortdesc:
    def test_missing_shortdesc_warns(self):
        r = analyze('<concept id="c1"><title>T</title><conbody/></concept>')
        assert "shortdesc" in categories(r, severity="warning")

    def test_empty_shortdesc_warns(self):
        r = analyze('<concept id="c1"><title>T</title><shortdesc/>  <conbody/></concept>')
        assert "shortdesc" in categories(r, severity="warning")

    def test_shortdesc_over_50_words_warns(self):
        long = " ".join(["word"] * 55)
        r = analyze(f'<concept id="c1"><title>T</title>'
                    f'<shortdesc>{long}</shortdesc><conbody/></concept>')
        shortdesc_warns = [f for f in r["findings"]
                           if f["category"] == "shortdesc" and "50" in f["message"]]
        assert shortdesc_warns

    def test_shortdesc_with_block_warns(self):
        r = analyze('<concept id="c1"><title>T</title>'
                    '<shortdesc><p>Block!</p></shortdesc>'
                    '<conbody/></concept>')
        block_warns = [f for f in r["findings"]
                       if f["category"] == "shortdesc" and "block" in f["message"]]
        assert block_warns

    def test_valid_shortdesc_no_warning(self):
        r = analyze('<concept id="c1"><title>T</title>'
                    '<shortdesc>A brief description.</shortdesc>'
                    '<conbody/></concept>')
        assert "shortdesc" not in categories(r, severity="warning")


# ---------------------------------------------------------------------------
# Topic size
# ---------------------------------------------------------------------------

class TestTopicSize:
    def test_small_topic_no_size_warning(self):
        r = analyze('<concept id="c1"><title>T</title>'
                    '<shortdesc>S</shortdesc><conbody><p>Short.</p></conbody></concept>')
        assert "topic-size" not in categories(r, severity="warning")

    def test_large_word_count_warns(self):
        big_p = "<p>" + " ".join(["word"] * 310) + "</p>"
        r = analyze(f'<concept id="c1"><title>T</title>'
                    f'<shortdesc>S</shortdesc><conbody>{big_p}</conbody></concept>')
        assert "topic-size" in categories(r, severity="warning")

    def test_many_blocks_warns(self):
        blocks = "".join(f"<p>Paragraph {i}.</p>" for i in range(55))
        r = analyze(f'<concept id="c1"><title>T</title>'
                    f'<shortdesc>S</shortdesc><conbody>{blocks}</conbody></concept>')
        assert "topic-size" in categories(r, severity="warning")


# ---------------------------------------------------------------------------
# Empty elements
# ---------------------------------------------------------------------------

class TestEmptyElements:
    def test_empty_p_warns(self):
        r = analyze('<concept id="c1"><title>T</title><shortdesc>S</shortdesc>'
                    '<conbody><p/></conbody></concept>')
        assert "empty" in categories(r, severity="warning")

    def test_non_empty_p_no_warning(self):
        r = analyze('<concept id="c1"><title>T</title><shortdesc>S</shortdesc>'
                    '<conbody><p>Content.</p></conbody></concept>')
        assert "empty" not in categories(r)


# ---------------------------------------------------------------------------
# Reusable element IDs
# ---------------------------------------------------------------------------

class TestReusableIds:
    def test_section_without_id_gives_info(self):
        r = analyze('<concept id="c1"><title>T</title><shortdesc>S</shortdesc>'
                    '<conbody><section><title>S</title><p>P</p></section></conbody></concept>')
        assert "ids" in categories(r, severity="info")

    def test_section_with_id_no_info(self):
        r = analyze('<concept id="c1"><title>T</title><shortdesc>S</shortdesc>'
                    '<conbody><section id="s1"><title>S</title><p>P</p></section></conbody></concept>')
        assert "ids" not in categories(r, severity="info")


# ---------------------------------------------------------------------------
# Task: step count
# ---------------------------------------------------------------------------

class TestStepCount:
    def test_10_steps_no_warning(self):
        steps = "".join(f"<step><cmd>Step {i}</cmd></step>" for i in range(10))
        r = analyze(f'<task id="t1"><title>T</title><shortdesc>S</shortdesc>'
                    f'<taskbody><steps>{steps}</steps></taskbody></task>')
        assert "steps" not in categories(r, severity="warning")

    def test_11_steps_warns(self):
        steps = "".join(f"<step><cmd>Step {i}</cmd></step>" for i in range(11))
        r = analyze(f'<task id="t1"><title>T</title><shortdesc>S</shortdesc>'
                    f'<taskbody><steps>{steps}</steps></taskbody></task>')
        assert "steps" in categories(r, severity="warning")


# ---------------------------------------------------------------------------
# Nesting depth
# ---------------------------------------------------------------------------

class TestNestingDepth:
    def test_shallow_nesting_ok(self):
        r = analyze('<concept id="c1"><title>T</title><shortdesc>S</shortdesc>'
                    '<conbody><section><section><section/></section></section>'
                    '</conbody></concept>')
        assert "nesting" not in categories(r, severity="warning")

    def test_deep_section_warns(self):
        inner = "<section/>"
        for _ in range(4):
            inner = f"<section>{inner}</section>"
        r = analyze(f'<concept id="c1"><title>T</title><shortdesc>S</shortdesc>'
                    f'<conbody>{inner}</conbody></concept>')
        assert "nesting" in categories(r, severity="warning")


# ---------------------------------------------------------------------------
# Duplicate paragraphs
# ---------------------------------------------------------------------------

class TestDuplicateParagraphs:
    def test_identical_paragraphs_flagged(self):
        text = "This is a reusable paragraph about configuration settings."
        r = analyze(f'<concept id="c1"><title>T</title><shortdesc>S</shortdesc>'
                    f'<conbody><p>{text}</p><p>{text}</p></conbody></concept>')
        assert "reuse" in categories(r, severity="info")

    def test_distinct_paragraphs_not_flagged(self):
        r = analyze('<concept id="c1"><title>T</title><shortdesc>S</shortdesc>'
                    '<conbody><p>Alpha beta gamma delta epsilon.</p>'
                    '<p>One two three four five six.</p></conbody></concept>')
        assert "reuse" not in categories(r, severity="info")


# ---------------------------------------------------------------------------
# Conref chain detection
# ---------------------------------------------------------------------------

class TestConrefChains:
    def test_element_with_id_and_conref_flags_chain_target(self):
        # p1 has @id and @conref; p2's conref points to p1's id → chain
        r = analyze(
            '<concept id="c1"><title>T</title><shortdesc>S</shortdesc>'
            '<conbody>'
            '<p id="p1" conref="lib.dita#lib/src">source</p>'
            '<p conref="topic.dita#c1/p1">ref to chained</p>'
            '</conbody></concept>'
        )
        assert "conref" in categories(r, severity="error")
