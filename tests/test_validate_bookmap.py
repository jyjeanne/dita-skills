"""
test_validate_bookmap.py — Unit tests for validate-bookmap/scripts/validate_bookmap.py
"""
import pytest
from validate_bookmap import validate


def errors(r):   return [e["rule"] for e in r["errors"]]
def warnings(r): return [w["rule"] for w in r["warnings"]]
def valid(r):    return r["is_valid"]

VALID_BOOKMAP = (
    '<bookmap id="b1">'
    '<booktitle><mainbooktitle>My Book</mainbooktitle></booktitle>'
    '<chapter href="ch1.dita"/>'
    '</bookmap>'
)


# ---------------------------------------------------------------------------
# Root element
# ---------------------------------------------------------------------------

class TestRoot:
    def test_valid_minimal_bookmap(self):
        r = validate(VALID_BOOKMAP)
        assert valid(r)
        assert errors(r) == []

    def test_malformed_xml(self):
        r = validate("<bookmap id='b1'><chapter href='ch.dita'>")
        assert not valid(r)
        assert "well-formed" in errors(r)

    def test_wrong_root_element(self):
        r = validate('<map id="m1"><topicref href="a.dita"/></map>')
        assert not valid(r)
        assert "root-element" in errors(r)

    def test_missing_id_warns(self):
        r = validate('<bookmap><booktitle><mainbooktitle>B</mainbooktitle></booktitle>'
                     '<chapter href="ch.dita"/></bookmap>')
        assert "id-recommended" in warnings(r)


# ---------------------------------------------------------------------------
# Chapter requirement
# ---------------------------------------------------------------------------

class TestChapterRequired:
    def test_no_chapter_or_part_is_error(self):
        r = validate('<bookmap id="b1">'
                     '<booktitle><mainbooktitle>B</mainbooktitle></booktitle>'
                     '</bookmap>')
        assert not valid(r)
        assert "chapter-required" in errors(r)

    def test_part_satisfies_chapter_requirement(self):
        r = validate('<bookmap id="b1">'
                     '<booktitle><mainbooktitle>B</mainbooktitle></booktitle>'
                     '<part href="part1.dita"/>'
                     '</bookmap>')
        assert "chapter-required" not in errors(r)


# ---------------------------------------------------------------------------
# Element order enforcement
# ---------------------------------------------------------------------------

class TestElementOrder:
    def test_backmatter_before_chapter_is_error(self):
        r = validate('<bookmap id="b1">'
                     '<backmatter/>'
                     '<chapter href="ch1.dita"/>'
                     '</bookmap>')
        assert not valid(r)
        assert "element-order" in errors(r)

    def test_frontmatter_after_chapter_is_error(self):
        r = validate('<bookmap id="b1">'
                     '<chapter href="ch1.dita"/>'
                     '<frontmatter/>'
                     '</bookmap>')
        assert not valid(r)
        assert "element-order" in errors(r)

    def test_appendix_before_chapter_is_error(self):
        r = validate('<bookmap id="b1">'
                     '<appendix href="app.dita"/>'
                     '<chapter href="ch1.dita"/>'
                     '</bookmap>')
        assert not valid(r)
        assert "element-order" in errors(r)

    def test_correct_order_is_valid(self):
        r = validate(
            '<bookmap id="b1">'
            '<booktitle><mainbooktitle>B</mainbooktitle></booktitle>'
            '<bookmeta/>'
            '<frontmatter><toc/></frontmatter>'
            '<chapter href="ch1.dita"/>'
            '<appendix href="app.dita"/>'
            '<backmatter/>'
            '</bookmap>'
        )
        assert valid(r)


# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

class TestSingletons:
    def test_duplicate_booktitle_is_error(self):
        r = validate(
            '<bookmap id="b1">'
            '<booktitle><mainbooktitle>B1</mainbooktitle></booktitle>'
            '<booktitle><mainbooktitle>B2</mainbooktitle></booktitle>'
            '<chapter href="ch.dita"/>'
            '</bookmap>'
        )
        assert not valid(r)
        assert "booktitle-singleton" in errors(r)

    def test_duplicate_backmatter_is_error(self):
        r = validate(
            '<bookmap id="b1">'
            '<chapter href="ch.dita"/>'
            '<backmatter/><backmatter/>'
            '</bookmap>'
        )
        assert not valid(r)
        assert "backmatter-singleton" in errors(r)


# ---------------------------------------------------------------------------
# booktitle: mainbooktitle required
# ---------------------------------------------------------------------------

class TestBooktitle:
    def test_booktitle_without_mainbooktitle_is_error(self):
        r = validate(
            '<bookmap id="b1">'
            '<booktitle><booktitlealt>Alt</booktitlealt></booktitle>'
            '<chapter href="ch.dita"/>'
            '</bookmap>'
        )
        assert not valid(r)
        assert "mainbooktitle-required" in errors(r)

    def test_booktitle_with_mainbooktitle_is_valid(self):
        r = validate(VALID_BOOKMAP)
        assert "mainbooktitle-required" not in errors(r)


# ---------------------------------------------------------------------------
# appendices vs appendix mixing
# ---------------------------------------------------------------------------

class TestAppendices:
    def test_appendices_and_appendix_mixed_is_error(self):
        r = validate(
            '<bookmap id="b1">'
            '<chapter href="ch.dita"/>'
            '<appendices href="apps.dita"/>'
            '<appendix href="appA.dita"/>'
            '</bookmap>'
        )
        assert not valid(r)
        assert "appendices-appendix-mixed" in errors(r)

    def test_only_appendices_is_valid(self):
        r = validate(
            '<bookmap id="b1">'
            '<booktitle><mainbooktitle>B</mainbooktitle></booktitle>'
            '<chapter href="ch.dita"/>'
            '<appendices href="apps.dita"/>'
            '</bookmap>'
        )
        assert "appendices-appendix-mixed" not in errors(r)

    def test_only_bare_appendix_is_valid(self):
        r = validate(VALID_BOOKMAP.replace(
            '</bookmap>', '<appendix href="appA.dita"/></bookmap>'))
        assert "appendices-appendix-mixed" not in errors(r)
