"""
test_validate_ditamap.py — Unit tests for validate-ditamap/scripts/validate_ditamap.py
"""
import pytest
from validate_ditamap import validate


def errors(r):   return [e["rule"] for e in r["errors"]]
def warnings(r): return [w["rule"] for w in r["warnings"]]
def valid(r):    return r["is_valid"]


# ---------------------------------------------------------------------------
# Well-formedness & root element
# ---------------------------------------------------------------------------

class TestRoot:
    def test_valid_minimal_map(self):
        r = validate('<map id="m1"><title>My Map</title>'
                     '<topicref href="a.dita" keys="k-a"/></map>')
        assert valid(r)

    def test_malformed_xml(self):
        r = validate("<map id='m1'><title>T</title>")
        assert not valid(r)
        assert "well-formed" in errors(r)

    def test_wrong_root_element(self):
        r = validate("<bookmap id='b1'><chapter href='ch.dita'/></bookmap>")
        assert not valid(r)
        assert "root-element" in errors(r)

    def test_missing_id_warns(self):
        r = validate('<map><title>T</title><topicref href="a.dita"/></map>')
        assert "id-recommended" in warnings(r)

    def test_missing_title_warns(self):
        r = validate('<map id="m1"><topicref href="a.dita"/></map>')
        assert "title-recommended" in warnings(r)


# ---------------------------------------------------------------------------
# topicref href / keyref rules
# ---------------------------------------------------------------------------

class TestTopicref:
    def test_topicref_with_href_is_valid(self):
        r = validate('<map id="m1"><title>T</title><topicref href="a.dita"/></map>')
        assert valid(r)

    def test_topicref_with_keyref_is_valid(self):
        r = validate('<map id="m1"><title>T</title><topicref keyref="k-a"/></map>')
        assert valid(r)

    def test_topicref_with_keys_only_warns(self):
        r = validate('<map id="m1"><title>T</title><topicref keys="k-a"/></map>')
        assert "href-or-keyref-recommended" in warnings(r)

    def test_topicref_without_href_keyref_keys_is_error(self):
        r = validate('<map id="m1"><title>T</title><topicref/></map>')
        assert not valid(r)
        assert "href-or-keyref-required" in errors(r)

    def test_navref_does_not_need_href(self):
        r = validate('<map id="m1"><title>T</title><navref mapref="other.ditamap"/></map>')
        assert "href-or-keyref-required" not in errors(r)


# ---------------------------------------------------------------------------
# collection-type
# ---------------------------------------------------------------------------

class TestCollectionType:
    @pytest.mark.parametrize("ct", ["unordered", "sequence", "choice", "family"])
    def test_valid_collection_types(self, ct):
        r = validate(f'<map id="m1"><title>T</title>'
                     f'<topicref href="a.dita" collection-type="{ct}"/></map>')
        assert "collection-type-invalid" not in errors(r)

    def test_invalid_collection_type(self):
        r = validate('<map id="m1"><title>T</title>'
                     '<topicref href="a.dita" collection-type="random"/></map>')
        assert not valid(r)
        assert "collection-type-invalid" in errors(r)


# ---------------------------------------------------------------------------
# Key uniqueness
# ---------------------------------------------------------------------------

class TestKeyUniqueness:
    def test_duplicate_keys_in_topicrefs(self):
        r = validate('<map id="m1"><title>T</title>'
                     '<topicref href="a.dita" keys="k1"/>'
                     '<topicref href="b.dita" keys="k1"/></map>')
        assert not valid(r)
        assert "duplicate-key" in errors(r)

    def test_duplicate_keys_in_keydef(self):
        r = validate('<map id="m1"><title>T</title>'
                     '<keydef href="a.dita" keys="k1"/>'
                     '<keydef href="b.dita" keys="k1"/></map>')
        assert not valid(r)
        assert "duplicate-key" in errors(r)

    def test_unique_keys_are_valid(self):
        r = validate('<map id="m1"><title>T</title>'
                     '<topicref href="a.dita" keys="k1"/>'
                     '<topicref href="b.dita" keys="k2"/></map>')
        assert "duplicate-key" not in errors(r)


# ---------------------------------------------------------------------------
# Nesting depth
# ---------------------------------------------------------------------------

class TestNestingDepth:
    def _make_nested(self, depth):
        inner = '<topicref href="leaf.dita"/>'
        for _ in range(depth):
            inner = f'<topicref href="n.dita">{inner}</topicref>'
        return f'<map id="m1"><title>T</title>{inner}</map>'

    def test_depth_5_is_fine(self):
        # _make_nested(4) produces 4 wrapper topicrefs + leaf = leaf at depth 5 ≤ MAX_DEPTH
        r = validate(self._make_nested(4))
        assert "nesting-depth" not in warnings(r)

    def test_depth_6_is_boundary_warn(self):
        # _make_nested(5) produces leaf at depth 6 — first depth that exceeds MAX_DEPTH(5)
        r = validate(self._make_nested(5))
        assert "nesting-depth" in warnings(r)

    def test_depth_6_warns(self):
        r = validate(self._make_nested(6))
        assert "nesting-depth" in warnings(r)


# ---------------------------------------------------------------------------
# Reltable column consistency
# ---------------------------------------------------------------------------

class TestReltable:
    def test_matching_columns_is_valid(self):
        r = validate(
            '<map id="m1"><title>T</title>'
            '<topicref href="a.dita"/>'
            '<reltable>'
            '  <relcolspec/><relcolspec/>'
            '  <relrow><relcell/><relcell/></relrow>'
            '</reltable></map>'
        )
        assert "reltable-column-mismatch" not in errors(r)

    def test_mismatched_columns_is_error(self):
        r = validate(
            '<map id="m1"><title>T</title>'
            '<topicref href="a.dita"/>'
            '<reltable>'
            '  <relcolspec/><relcolspec/>'
            '  <relrow><relcell/></relrow>'
            '</reltable></map>'
        )
        assert not valid(r)
        assert "reltable-column-mismatch" in errors(r)
