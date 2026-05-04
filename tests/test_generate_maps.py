"""
test_generate_ditamap.py — Unit tests for generate-ditamap/scripts/generate_ditamap.py
test_generate_bookmap.py tests are in the same file for brevity.
"""
import re
import pytest
import xml.etree.ElementTree as ET

from generate_ditamap import generate as gen_map, key_from_href
from generate_bookmap import generate as gen_book


def parse(xml_str):
    xml_str = re.sub(r"<!DOCTYPE[^>]*>", "", xml_str)
    return ET.fromstring(xml_str)


# ===========================================================================
# generate_ditamap
# ===========================================================================

class TestKeyFromHref:
    def test_simple_filename(self):
        assert key_from_href("intro.dita") == "key-intro"

    def test_path_with_dirs(self):
        assert key_from_href("topics/config.dita") == "key-config"

    def test_no_extension(self):
        assert key_from_href("readme") == "key-readme"


class TestGenerateDitamap:
    def test_well_formed_minimal(self):
        xml = gen_map("My Map", "my-map")
        root = parse(xml)
        assert root.tag == "map"

    def test_correct_doctype(self):
        xml = gen_map("T", "m1")
        assert "-//OASIS//DTD DITA 1.3 Map//EN" in xml

    def test_id_assigned(self):
        root = parse(gen_map("T", "my-id"))
        assert root.get("id") == "my-id"

    def test_id_slugified_from_title(self):
        root = parse(gen_map("My Map Title"))
        assert root.get("id") == "my-map-title"

    def test_title_present(self):
        root = parse(gen_map("Test Map", "m1"))
        assert root.findtext("title") == "Test Map"

    def test_topicrefs_generated_for_topics(self):
        root = parse(gen_map("T", "m1", topics=["a.dita", "b.dita"]))
        topicrefs = root.findall("topicref")
        hrefs = [t.get("href") for t in topicrefs]
        assert "a.dita" in hrefs
        assert "b.dita" in hrefs

    def test_keydef_generated_for_each_topic(self):
        root = parse(gen_map("T", "m1", topics=["intro.dita", "config.dita"]))
        keydefs = root.findall("keydef")
        keys = [k.get("keys") for k in keydefs]
        assert "key-intro" in keys
        assert "key-config" in keys

    def test_topicref_keys_match_keydef_keys(self):
        root = parse(gen_map("T", "m1", topics=["intro.dita"]))
        keydef_keys = {k.get("keys") for k in root.findall("keydef")}
        topicref_keys = {t.get("keys") for t in root.findall("topicref")}
        assert keydef_keys == topicref_keys

    def test_reltable_present(self):
        root = parse(gen_map("T", "m1", topics=["a.dita", "b.dita"]))
        assert root.find("reltable") is not None

    def test_reltable_columns_match_cells(self):
        root = parse(gen_map("T", "m1", topics=["a.dita", "b.dita"]))
        reltable = root.find("reltable")
        col_count = len(reltable.findall("relcolspec"))
        for row in reltable.findall("relrow"):
            assert len(row.findall("relcell")) == col_count


# ===========================================================================
# generate_bookmap
# ===========================================================================

class TestGenerateBookmap:
    CHAPTERS = ["ch1.dita", "ch2.dita"]
    APPENDIX = ["appA.dita"]

    def test_well_formed_minimal(self):
        root = parse(gen_book("My Book", "b1"))
        assert root.tag == "bookmap"

    def test_correct_doctype(self):
        xml = gen_book("T", "b1")
        assert "-//OASIS//DTD DITA 1.3 BookMap//EN" in xml

    def test_id_assigned(self):
        root = parse(gen_book("T", "my-book"))
        assert root.get("id") == "my-book"

    def test_id_slugified_from_title(self):
        root = parse(gen_book("My Book Title"))
        assert root.get("id") == "my-book-title"

    def test_mainbooktitle_present(self):
        root = parse(gen_book("Great Book", "b1"))
        assert root.findtext("booktitle/mainbooktitle") == "Great Book"

    def test_chapters_present(self):
        root = parse(gen_book("T", "b1", chapters=self.CHAPTERS))
        chapters = root.findall("chapter")
        hrefs = [c.get("href") for c in chapters]
        assert "ch1.dita" in hrefs
        assert "ch2.dita" in hrefs

    def test_appendix_present(self):
        root = parse(gen_book("T", "b1",
                               chapters=self.CHAPTERS,
                               appendix=self.APPENDIX))
        appendices = root.findall("appendix")
        assert any(a.get("href") == "appA.dita" for a in appendices)

    def test_frontmatter_present(self):
        root = parse(gen_book("T", "b1"))
        assert root.find("frontmatter") is not None
        assert root.find("frontmatter/toc") is not None

    def test_backmatter_present(self):
        root = parse(gen_book("T", "b1"))
        assert root.find("backmatter") is not None

    def test_element_order_valid_for_bookmap_validator(self):
        """Generated bookmap must pass our own validator."""
        from validate_bookmap import validate
        xml = gen_book("T", "b1", chapters=["ch.dita"])
        # Strip DOCTYPE before validating with ElementTree
        xml_no_doctype = re.sub(r"<!DOCTYPE[^>]*>", "", xml)
        r = validate(xml_no_doctype)
        assert r["is_valid"], f"Generated bookmap failed validation: {r['errors']}"
