"""
test_review_dita_guide.py — Tests for review-dita-guide/scripts/review_dita_guide.py

Test categories:
  1. Single-map, single-topic (baseline happy path)
  2. Nested maps (root → child map → topic)
  3. Bookmap traversal (chapter / appendix)
  4. Missing file detection
  5. Circular reference detection
  6. Cross-guide duplicate @id detection
  7. External URL skipping
  8. Topic reuse (same topic referenced from two maps — validated once)
  9. Summary statistics
 10. Best-practices opt-in
 11. Root file not found
 12. Malformed XML handling
"""

import json
from pathlib import Path
import pytest
from review_dita_guide import review_guide, _get_hrefs, _classify, _build_summary


# ---------------------------------------------------------------------------
# Fixtures — minimal valid DITA content strings
# ---------------------------------------------------------------------------

_CONCEPT = (
    '<concept id="c1"><title>Concept</title>'
    '<shortdesc>Short.</shortdesc><conbody/></concept>'
)
_TASK = (
    '<task id="t1"><title>Task</title>'
    '<shortdesc>Short.</shortdesc>'
    '<taskbody><steps><step><cmd>Do it.</cmd></step></steps></taskbody></task>'
)
_REFERENCE = (
    '<reference id="r1"><title>Ref</title>'
    '<shortdesc>Short.</shortdesc><refbody/></reference>'
)
_DITAMAP = '<map id="m1"><title>Map</title>{topicrefs}</map>'
_BOOKMAP = (
    '<bookmap id="bm1">'
    '<booktitle><mainbooktitle>Guide</mainbooktitle></booktitle>'
    '{chapters}'
    '</bookmap>'
)


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Helper accessors
# ---------------------------------------------------------------------------

def valid(r):        return r["summary"].get("invalid_files", 1) == 0
def errors(r):       return [e["rule"] for f in r["files"] for e in f["errors"]]
def cross(r):        return [ci["rule"] for ci in r["cross_guide"]]
def file_types(r):   return {f["type"] for f in r["files"]}
def file_paths(r):   return [f["path"] for f in r["files"]]
def file_depths(r):  return {f["path"]: f["depth"] for f in r["files"]}


# ---------------------------------------------------------------------------
# 1. Single map, single topic
# ---------------------------------------------------------------------------

class TestSingleMapSingleTopic:
    def test_valid_guide_is_valid(self, tmp_path):
        _write(tmp_path / "topic.dita", _CONCEPT)
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="topic.dita"/>'))
        r = review_guide(tmp_path / "root.ditamap")
        assert valid(r)
        assert r["summary"]["topics"] == 1
        assert r["summary"]["maps"]   == 1

    def test_files_list_contains_map_and_topic(self, tmp_path):
        _write(tmp_path / "topic.dita", _CONCEPT)
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="topic.dita"/>'))
        r = review_guide(tmp_path / "root.ditamap")
        assert file_types(r) == {"map", "topic"}

    def test_paths_are_relative_to_root_dir(self, tmp_path):
        _write(tmp_path / "topic.dita", _CONCEPT)
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="topic.dita"/>'))
        r = review_guide(tmp_path / "root.ditamap")
        paths = file_paths(r)
        assert all(not Path(p).is_absolute() for p in paths)


# ---------------------------------------------------------------------------
# 2. Nested maps
# ---------------------------------------------------------------------------

class TestNestedMaps:
    def _build(self, tmp_path):
        _write(tmp_path / "topics" / "t1.dita", _CONCEPT)
        _write(tmp_path / "child.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="topics/t1.dita"/>'))
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(topicrefs='<mapref href="child.ditamap"/>'))
        return tmp_path / "root.ditamap"

    def test_nested_map_traversed(self, tmp_path):
        r = review_guide(self._build(tmp_path))
        assert r["summary"]["maps"]   == 2  # root + child
        assert r["summary"]["topics"] == 1

    def test_root_map_at_depth_0(self, tmp_path):
        r = review_guide(self._build(tmp_path))
        depths = file_depths(r)
        root_entry = next(f for f in r["files"] if f["type"] == "map" and f["depth"] == 0)
        assert root_entry is not None

    def test_child_map_at_depth_1(self, tmp_path):
        r = review_guide(self._build(tmp_path))
        child_entry = next(
            (f for f in r["files"] if f["type"] == "map" and f["depth"] == 1), None
        )
        assert child_entry is not None

    def test_topic_at_depth_2(self, tmp_path):
        r = review_guide(self._build(tmp_path))
        topic_entry = next((f for f in r["files"] if f["type"] == "topic"), None)
        assert topic_entry is not None
        assert topic_entry["depth"] == 2

    def test_three_level_nesting(self, tmp_path):
        _write(tmp_path / "leaf.dita", _CONCEPT)
        _write(tmp_path / "deep.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="leaf.dita"/>'))
        _write(tmp_path / "mid.ditamap",
               _DITAMAP.format(topicrefs='<mapref href="deep.ditamap"/>'))
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(topicrefs='<mapref href="mid.ditamap"/>'))
        r = review_guide(tmp_path / "root.ditamap")
        assert r["summary"]["maps"]   == 3
        assert r["summary"]["topics"] == 1


# ---------------------------------------------------------------------------
# 3. Bookmap traversal
# ---------------------------------------------------------------------------

class TestBookmapTraversal:
    def test_bookmap_chapter_topic_traversed(self, tmp_path):
        _write(tmp_path / "ch1.dita", _TASK)
        _write(tmp_path / "guide.bookmap",
               _BOOKMAP.format(chapters='<chapter href="ch1.dita"/>'))
        r = review_guide(tmp_path / "guide.bookmap")
        assert r["summary"]["maps"]   == 1
        assert r["summary"]["topics"] == 1

    def test_bookmap_type_is_bookmap(self, tmp_path):
        _write(tmp_path / "ch1.dita", _TASK)
        _write(tmp_path / "guide.bookmap",
               _BOOKMAP.format(chapters='<chapter href="ch1.dita"/>'))
        r = review_guide(tmp_path / "guide.bookmap")
        root_entry = r["files"][0]
        assert root_entry["type"] == "bookmap"

    def test_bookmap_appendix_traversed(self, tmp_path):
        _write(tmp_path / "ch1.dita", _TASK)
        _write(tmp_path / "app1.dita", _REFERENCE)
        content = (
            '<bookmap id="bm1">'
            '<booktitle><mainbooktitle>G</mainbooktitle></booktitle>'
            '<chapter href="ch1.dita"/>'
            '<appendix href="app1.dita"/>'
            '</bookmap>'
        )
        _write(tmp_path / "guide.bookmap", content)
        r = review_guide(tmp_path / "guide.bookmap")
        assert r["summary"]["topics"] == 2

    def test_bookmap_with_child_ditamap(self, tmp_path):
        _write(tmp_path / "topics" / "t1.dita", _CONCEPT)
        _write(tmp_path / "chapter1.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="topics/t1.dita"/>'))
        _write(tmp_path / "guide.bookmap",
               _BOOKMAP.format(chapters='<chapter href="chapter1.ditamap"/>'))
        r = review_guide(tmp_path / "guide.bookmap")
        # bookmap + ditamap = 2 maps
        assert r["summary"]["maps"] == 2
        assert r["summary"]["topics"] == 1


# ---------------------------------------------------------------------------
# 4. Missing file detection
# ---------------------------------------------------------------------------

class TestMissingFiles:
    def test_missing_topic_reported(self, tmp_path):
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="ghost.dita"/>'))
        r = review_guide(tmp_path / "root.ditamap")
        assert r["summary"]["missing"] == 1
        assert "href-target-missing" in errors(r)

    def test_missing_topic_makes_guide_invalid(self, tmp_path):
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="ghost.dita"/>'))
        r = review_guide(tmp_path / "root.ditamap")
        assert not valid(r)

    def test_missing_child_map_reported(self, tmp_path):
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(topicrefs='<mapref href="missing-child.ditamap"/>'))
        r = review_guide(tmp_path / "root.ditamap")
        assert r["summary"]["missing"] >= 1

    def test_present_and_missing_files_mixed(self, tmp_path):
        _write(tmp_path / "present.dita", _CONCEPT)
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(
                   topicrefs='<topicref href="present.dita"/>'
                              '<topicref href="absent.dita"/>'
               ))
        r = review_guide(tmp_path / "root.ditamap")
        assert r["summary"]["topics"]  >= 1
        assert r["summary"]["missing"] == 1


# ---------------------------------------------------------------------------
# 5. Circular reference detection
# ---------------------------------------------------------------------------

class TestCircularReferences:
    def test_direct_self_reference(self, tmp_path):
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(topicrefs='<mapref href="root.ditamap"/>'))
        r = review_guide(tmp_path / "root.ditamap")
        assert "circular-reference" in cross(r)

    def test_indirect_circular_reference(self, tmp_path):
        _write(tmp_path / "a.ditamap",
               _DITAMAP.format(topicrefs='<mapref href="b.ditamap"/>'))
        _write(tmp_path / "b.ditamap",
               _DITAMAP.format(topicrefs='<mapref href="a.ditamap"/>'))
        r = review_guide(tmp_path / "a.ditamap")
        assert "circular-reference" in cross(r)

    def test_non_circular_multi_reference_ok(self, tmp_path):
        """Same topic referenced from two different maps is not circular."""
        _write(tmp_path / "shared.dita", _CONCEPT)
        _write(tmp_path / "child1.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="shared.dita"/>'))
        _write(tmp_path / "child2.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="shared.dita"/>'))
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(
                   topicrefs='<mapref href="child1.ditamap"/>'
                              '<mapref href="child2.ditamap"/>'
               ))
        r = review_guide(tmp_path / "root.ditamap")
        assert "circular-reference" not in cross(r)

    def test_diamond_shared_map_not_circular(self, tmp_path):
        """
        Diamond structure: root→child1→shared, root→child2→shared.
        'shared' is reachable via two paths but contains no cycle — must NOT
        be flagged as a circular reference.
        """
        _write(tmp_path / "shared.dita", _CONCEPT)
        _write(tmp_path / "shared.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="shared.dita"/>'))
        _write(tmp_path / "child1.ditamap",
               _DITAMAP.format(topicrefs='<mapref href="shared.ditamap"/>'))
        _write(tmp_path / "child2.ditamap",
               _DITAMAP.format(topicrefs='<mapref href="shared.ditamap"/>'))
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(
                   topicrefs='<mapref href="child1.ditamap"/>'
                              '<mapref href="child2.ditamap"/>'
               ))
        r = review_guide(tmp_path / "root.ditamap")
        assert "circular-reference" not in cross(r), (
            "Diamond-shaped map inclusion must not be flagged as a circular reference"
        )

    def test_diamond_shared_map_validated_once(self, tmp_path):
        """
        In a diamond structure, the shared child map should appear in file_results
        exactly once (validated once, not twice).
        """
        _write(tmp_path / "shared.dita", _CONCEPT)
        _write(tmp_path / "shared.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="shared.dita"/>'))
        _write(tmp_path / "child1.ditamap",
               _DITAMAP.format(topicrefs='<mapref href="shared.ditamap"/>'))
        _write(tmp_path / "child2.ditamap",
               _DITAMAP.format(topicrefs='<mapref href="shared.ditamap"/>'))
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(
                   topicrefs='<mapref href="child1.ditamap"/>'
                              '<mapref href="child2.ditamap"/>'
               ))
        r = review_guide(tmp_path / "root.ditamap")
        shared_entries = [f for f in r["files"] if "shared.ditamap" in f["path"]]
        assert len(shared_entries) == 1, (
            f"shared.ditamap must appear exactly once in results, got {len(shared_entries)}"
        )


# ---------------------------------------------------------------------------
# 6. Cross-guide duplicate @id detection
# ---------------------------------------------------------------------------

class TestDuplicateGuideId:
    def test_duplicate_id_across_topics_warns(self, tmp_path):
        _write(tmp_path / "t1.dita", '<concept id="shared"><title>T1</title><conbody/></concept>')
        _write(tmp_path / "t2.dita", '<concept id="shared"><title>T2</title><conbody/></concept>')
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(
                   topicrefs='<topicref href="t1.dita"/>'
                              '<topicref href="t2.dita"/>'
               ))
        r = review_guide(tmp_path / "root.ditamap")
        assert "duplicate-guide-id" in cross(r)

    def test_duplicate_id_entry_lists_both_paths(self, tmp_path):
        _write(tmp_path / "t1.dita", '<concept id="dup"><title>T1</title><conbody/></concept>')
        _write(tmp_path / "t2.dita", '<concept id="dup"><title>T2</title><conbody/></concept>')
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(
                   topicrefs='<topicref href="t1.dita"/>'
                              '<topicref href="t2.dita"/>'
               ))
        r = review_guide(tmp_path / "root.ditamap")
        dup = next(ci for ci in r["cross_guide"] if ci["rule"] == "duplicate-guide-id")
        assert len(dup["paths"]) == 2

    def test_unique_ids_no_cross_issue(self, tmp_path):
        _write(tmp_path / "t1.dita", '<concept id="c1"><title>T1</title><conbody/></concept>')
        _write(tmp_path / "t2.dita", '<concept id="c2"><title>T2</title><conbody/></concept>')
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(
                   topicrefs='<topicref href="t1.dita"/>'
                              '<topicref href="t2.dita"/>'
               ))
        r = review_guide(tmp_path / "root.ditamap")
        assert "duplicate-guide-id" not in cross(r)


# ---------------------------------------------------------------------------
# 7. External URL skipping
# ---------------------------------------------------------------------------

class TestExternalUrls:
    def test_http_href_not_traversed(self, tmp_path):
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(
                   topicrefs='<topicref href="https://example.com/topic.dita"/>'
               ))
        r = review_guide(tmp_path / "root.ditamap")
        # Should not report as missing — external refs are skipped
        assert "href-target-missing" not in errors(r)
        assert r["summary"]["missing"] == 0

    def test_ftp_href_not_traversed(self, tmp_path):
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="ftp://host/file.dita"/>'))
        r = review_guide(tmp_path / "root.ditamap")
        assert r["summary"]["missing"] == 0


# ---------------------------------------------------------------------------
# 8. Topic reuse — validated once
# ---------------------------------------------------------------------------

class TestTopicReuse:
    def test_shared_topic_appears_once_in_results(self, tmp_path):
        _write(tmp_path / "shared.dita", _CONCEPT)
        _write(tmp_path / "child1.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="shared.dita"/>'))
        _write(tmp_path / "child2.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="shared.dita"/>'))
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(
                   topicrefs='<mapref href="child1.ditamap"/>'
                              '<mapref href="child2.ditamap"/>'
               ))
        r = review_guide(tmp_path / "root.ditamap")
        topic_paths = [f["path"] for f in r["files"] if f["type"] == "topic"]
        assert len(topic_paths) == len(set(topic_paths)), \
            "Shared topic validated more than once"


# ---------------------------------------------------------------------------
# 9. Summary statistics
# ---------------------------------------------------------------------------

class TestSummaryStatistics:
    def test_summary_keys_present(self, tmp_path):
        _write(tmp_path / "t.dita", _CONCEPT)
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="t.dita"/>'))
        r = review_guide(tmp_path / "root.ditamap")
        for key in ("total_files", "maps", "topics", "missing", "unknown",
                    "valid_files", "invalid_files", "errors", "warnings",
                    "cross_guide_issues"):
            assert key in r["summary"], f"Missing summary key: {key}"

    def test_total_files_equals_maps_plus_topics_plus_missing_plus_unknown(self, tmp_path):
        _write(tmp_path / "t.dita", _CONCEPT)
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(
                   topicrefs='<topicref href="t.dita"/>'
                              '<topicref href="gone.dita"/>'
               ))
        r = review_guide(tmp_path / "root.ditamap")
        s = r["summary"]
        assert s["total_files"] == s["maps"] + s["topics"] + s["missing"] + s["unknown"]

    def test_valid_plus_invalid_equals_total(self, tmp_path):
        _write(tmp_path / "t.dita", _CONCEPT)
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="t.dita"/>'))
        r = review_guide(tmp_path / "root.ditamap")
        s = r["summary"]
        assert s["valid_files"] + s["invalid_files"] == s["total_files"]


# ---------------------------------------------------------------------------
# 10. Best-practices opt-in
# ---------------------------------------------------------------------------

class TestBestPractices:
    def test_best_practices_not_included_by_default(self, tmp_path):
        _write(tmp_path / "t.dita", _CONCEPT)
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="t.dita"/>'))
        r = review_guide(tmp_path / "root.ditamap", include_best_practices=False)
        topic = next(f for f in r["files"] if f["type"] == "topic")
        assert "best_practices" not in topic

    def test_best_practices_included_when_opted_in(self, tmp_path):
        _write(tmp_path / "t.dita", _CONCEPT)
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="t.dita"/>'))
        r = review_guide(tmp_path / "root.ditamap", include_best_practices=True)
        topic = next(f for f in r["files"] if f["type"] == "topic")
        assert "best_practices" in topic
        assert isinstance(topic["best_practices"], list)

    def test_best_practices_not_added_to_maps(self, tmp_path):
        _write(tmp_path / "t.dita", _CONCEPT)
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="t.dita"/>'))
        r = review_guide(tmp_path / "root.ditamap", include_best_practices=True)
        map_entry = next(f for f in r["files"] if f["type"] == "map")
        assert "best_practices" not in map_entry


# ---------------------------------------------------------------------------
# 11. Root file not found
# ---------------------------------------------------------------------------

class TestRootNotFound:
    def test_returns_io_error_cross_issue(self, tmp_path):
        r = review_guide(tmp_path / "nonexistent.ditamap")
        assert r["summary"] == {}
        assert any(ci["rule"] == "io-error" for ci in r["cross_guide"])

    def test_files_list_is_empty_when_root_missing(self, tmp_path):
        r = review_guide(tmp_path / "nonexistent.ditamap")
        assert r["files"] == []


# ---------------------------------------------------------------------------
# 12. Malformed XML
# ---------------------------------------------------------------------------

class TestMalformedXml:
    def test_malformed_map_reported_as_invalid(self, tmp_path):
        _write(tmp_path / "bad.ditamap", "<map id='m1'><unclosed>")
        r = review_guide(tmp_path / "bad.ditamap")
        assert r["files"][0]["is_valid"] is False

    def test_malformed_topic_reported_as_invalid(self, tmp_path):
        _write(tmp_path / "bad.dita", "<concept id='c1'><unclosed>")
        _write(tmp_path / "root.ditamap",
               _DITAMAP.format(topicrefs='<topicref href="bad.dita"/>'))
        r = review_guide(tmp_path / "root.ditamap")
        topic = next(f for f in r["files"] if "bad.dita" in f["path"])
        assert topic["is_valid"] is False


# ---------------------------------------------------------------------------
# Unit tests for internal helpers
# ---------------------------------------------------------------------------

class TestGetHrefs:
    def test_returns_href_and_tag(self, tmp_path):
        map_file = tmp_path / "m.ditamap"
        _write(map_file, '<map><topicref href="t.dita"/></map>')
        refs = _get_hrefs(map_file)
        assert ("t.dita", "topicref") in refs

    def test_strips_fragment(self, tmp_path):
        map_file = tmp_path / "m.ditamap"
        _write(map_file, '<map><topicref href="t.dita#section1"/></map>')
        refs = _get_hrefs(map_file)
        assert refs[0][0] == "t.dita"

    def test_skips_external_urls(self, tmp_path):
        map_file = tmp_path / "m.ditamap"
        _write(map_file, '<map><topicref href="https://example.com/t.dita"/></map>')
        refs = _get_hrefs(map_file)
        assert refs == []

    def test_skips_empty_href(self, tmp_path):
        map_file = tmp_path / "m.ditamap"
        _write(map_file, '<map><topicref href=""/></map>')
        refs = _get_hrefs(map_file)
        assert refs == []

    def test_skips_elements_without_href(self, tmp_path):
        map_file = tmp_path / "m.ditamap"
        _write(map_file, '<map><topicref keyref="mykey"/></map>')
        refs = _get_hrefs(map_file)
        assert refs == []

    def test_malformed_map_returns_empty(self, tmp_path):
        map_file = tmp_path / "bad.ditamap"
        _write(map_file, "<map><unclosed>")
        assert _get_hrefs(map_file) == []


class TestClassify:
    def test_missing_file_is_missing(self, tmp_path):
        assert _classify(tmp_path / "ghost.dita") == "missing"

    def test_ditamap_extension(self, tmp_path):
        f = tmp_path / "m.ditamap"
        _write(f, "<map/>")
        assert _classify(f) == "map"

    def test_bookmap_extension(self, tmp_path):
        f = tmp_path / "g.bookmap"
        _write(f, "<bookmap/>")
        assert _classify(f) == "bookmap"

    def test_dita_extension_is_topic(self, tmp_path):
        f = tmp_path / "t.dita"
        _write(f, '<concept id="c1"><title>T</title><conbody/></concept>')
        assert _classify(f) == "topic"
