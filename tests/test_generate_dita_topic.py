"""
test_generate_dita_topic.py — Unit tests for generate-dita-topic/scripts/generate_dita_topic.py
"""
import re
import pytest
import xml.etree.ElementTree as ET

from generate_dita_topic import generate, slugify, _DOCTYPES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse(xml_str):
    """Strip DOCTYPE (not handled by ElementTree) and parse."""
    xml_str = re.sub(r"<!DOCTYPE[^>]*>", "", xml_str)
    return ET.fromstring(xml_str)


def has_doctype(xml_str, topic_type):
    pub_id = _DOCTYPES[topic_type][0]
    return pub_id in xml_str


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_spaces_become_hyphens(self):
        assert slugify("My Cool Topic") == "my-cool-topic"

    def test_digits_at_start_get_prefix(self):
        assert slugify("123 topic").startswith("id-")

    def test_special_chars_stripped(self):
        result = slugify("Hello, World!")
        assert "," not in result
        assert "!" not in result

    def test_empty_string_gives_fallback(self):
        assert slugify("") == "generated-id"

    def test_consecutive_hyphens_collapsed(self):
        result = slugify("a  --  b")
        assert "--" not in result


# ---------------------------------------------------------------------------
# DOCTYPE declarations
# ---------------------------------------------------------------------------

class TestDoctype:
    @pytest.mark.parametrize("topic_type", list(_DOCTYPES.keys()))
    def test_correct_doctype_present(self, topic_type):
        xml = generate(topic_type, "Test Title", "test-id")
        assert has_doctype(xml, topic_type), \
            f"DOCTYPE for {topic_type} not found in output"

    def test_xml_declaration_present(self):
        xml = generate("concept", "T", "c1")
        assert xml.startswith("<?xml version")


# ---------------------------------------------------------------------------
# Well-formedness of all generated types
# ---------------------------------------------------------------------------

class TestWellFormedness:
    @pytest.mark.parametrize("topic_type", list(_DOCTYPES.keys()))
    def test_generated_xml_is_well_formed(self, topic_type):
        xml = generate(topic_type, f"Test {topic_type.capitalize()}", f"id-{topic_type}")
        root = parse(xml)
        assert root is not None

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown topic type"):
            generate("bogus", "T", "id1")


# ---------------------------------------------------------------------------
# Per-type structure checks
# ---------------------------------------------------------------------------

class TestTopicStructure:
    def test_concept_has_conbody(self):
        root = parse(generate("concept", "C", "c1"))
        assert root.tag == "concept"
        assert root.find("conbody") is not None

    def test_task_has_taskbody_with_steps(self):
        root = parse(generate("task", "T", "t1"))
        assert root.tag == "task"
        taskbody = root.find("taskbody")
        assert taskbody is not None
        assert taskbody.find("steps") is not None
        assert taskbody.find("steps/step/cmd") is not None

    def test_reference_has_refbody_with_properties(self):
        root = parse(generate("reference", "R", "r1"))
        assert root.tag == "reference"
        refbody = root.find("refbody")
        assert refbody is not None
        assert refbody.find("properties") is not None

    def test_troubleshooting_has_troublebody(self):
        root = parse(generate("troubleshooting", "TS", "ts1"))
        assert root.tag == "troubleshooting"
        assert root.find("troublebody") is not None
        assert root.find("troublebody/troubleSolution") is not None

    def test_glossentry_has_term_and_def(self):
        root = parse(generate("glossentry", "Term", "g1"))
        assert root.tag == "glossentry"
        assert root.find("glossterm") is not None
        assert root.find("glossdef") is not None

    def test_base_topic_has_body(self):
        root = parse(generate("topic", "Base", "b1"))
        assert root.tag == "topic"
        assert root.find("body") is not None


# ---------------------------------------------------------------------------
# ID assignment
# ---------------------------------------------------------------------------

class TestIdAssignment:
    def test_explicit_id_used(self):
        root = parse(generate("concept", "T", "my-explicit-id"))
        assert root.get("id") == "my-explicit-id"

    def test_id_derived_from_title_when_omitted(self):
        xml = generate("concept", "My New Topic")
        root = parse(xml)
        assert root.get("id") == "my-new-topic"

    def test_title_in_output(self):
        root = parse(generate("concept", "Hello World", "hw"))
        assert root.findtext("title") == "Hello World"
