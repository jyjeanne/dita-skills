"""
test_validate_dita_topic.py — Unit tests for validate-dita-topic/scripts/validate_dita_topic.py
"""
import pytest
from validate_dita_topic import validate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def errors(result):    return [e["rule"] for e in result["errors"]]
def warnings(result):  return [w["rule"] for w in result["warnings"]]
def valid(result):     return result["is_valid"]


# ---------------------------------------------------------------------------
# Well-formedness
# ---------------------------------------------------------------------------

class TestWellFormedness:
    def test_malformed_xml_returns_error(self):
        r = validate("<concept id='c1'><title>T</title>")
        assert not valid(r)
        assert "well-formed" in errors(r)

    def test_empty_string_returns_error(self):
        r = validate("")
        assert not valid(r)


# ---------------------------------------------------------------------------
# Unknown topic type
# ---------------------------------------------------------------------------

class TestUnknownType:
    def test_unknown_root_element(self):
        r = validate("<chapter id='x'><title>T</title><body/></chapter>")
        assert not valid(r)
        assert "unknown-type" in errors(r)

    def test_type_mismatch_explicit(self):
        r = validate("<concept id='c1'><title>T</title><conbody/></concept>", topic_type="task")
        assert not valid(r)
        assert "root-element" in errors(r)


# ---------------------------------------------------------------------------
# All-type rules: @id, <title>, <shortdesc>
# ---------------------------------------------------------------------------

class TestCommonRules:
    def test_missing_id_is_error(self):
        r = validate("<concept><title>T</title><conbody/></concept>")
        assert not valid(r)
        assert "id-required" in errors(r)

    def test_missing_title_is_error(self):
        r = validate("<concept id='c1'><shortdesc>S</shortdesc><conbody/></concept>")
        assert not valid(r)
        assert "title-required" in errors(r)

    def test_title_must_be_first_child(self):
        r = validate("<concept id='c1'><conbody/><title>T</title></concept>")
        assert not valid(r)
        assert "title-required" in errors(r)

    def test_missing_shortdesc_is_warning(self):
        r = validate("<concept id='c1'><title>T</title><conbody/></concept>")
        assert valid(r)  # missing shortdesc is a warning, not an error
        assert "shortdesc-recommended" in warnings(r)

    def test_shortdesc_with_block_element_warns(self):
        r = validate(
            "<concept id='c1'><title>T</title>"
            "<shortdesc><p>Block inside</p></shortdesc>"
            "<conbody/></concept>"
        )
        assert "shortdesc-no-blocks" in warnings(r)

    def test_shortdesc_over_50_words_warns(self):
        long_desc = " ".join(["word"] * 55)
        r = validate(
            f"<concept id='c1'><title>T</title>"
            f"<shortdesc>{long_desc}</shortdesc>"
            f"<conbody/></concept>"
        )
        assert "shortdesc-length" in warnings(r)

    def test_prolog_after_body_is_error(self):
        r = validate(
            "<concept id='c1'><title>T</title><conbody/>"
            "<prolog/></concept>"
        )
        assert "prolog-order" in errors(r)

    def test_related_links_before_body_is_error(self):
        r = validate(
            "<concept id='c1'><title>T</title>"
            "<related-links/><conbody/></concept>"
        )
        assert "related-links-order" in errors(r)


# ---------------------------------------------------------------------------
# Duplicate IDs
# ---------------------------------------------------------------------------

class TestDuplicateIds:
    def test_duplicate_id_is_error(self):
        r = validate(
            "<concept id='c1'><title>T</title><conbody>"
            "<section id='s1'/><section id='s1'/>"
            "</conbody></concept>"
        )
        assert not valid(r)
        assert "unique-id" in errors(r)

    def test_unique_ids_are_valid(self):
        r = validate(
            "<concept id='c1'><title>T</title><shortdesc>S</shortdesc><conbody>"
            "<section id='s1'/><section id='s2'/>"
            "</conbody></concept>"
        )
        assert "unique-id" not in errors(r)


# ---------------------------------------------------------------------------
# conref format
# ---------------------------------------------------------------------------

class TestConrefFormat:
    def test_conref_without_hash_is_error(self):
        r = validate(
            "<concept id='c1'><title>T</title><shortdesc>S</shortdesc>"
            "<conbody><p conref='library.dita'/></conbody></concept>"
        )
        assert not valid(r)
        assert "conref-format" in errors(r)

    def test_conref_with_hash_is_valid(self):
        r = validate(
            "<concept id='c1'><title>T</title><shortdesc>S</shortdesc>"
            "<conbody><p conref='library.dita#lib/p1'/></conbody></concept>"
        )
        assert "conref-format" not in errors(r)


# ---------------------------------------------------------------------------
# Concept
# ---------------------------------------------------------------------------

class TestConcept:
    VALID = (
        "<concept id='c1'><title>T</title><shortdesc>S</shortdesc>"
        "<conbody><p>Content.</p></conbody></concept>"
    )

    def test_valid_concept(self):
        r = validate(self.VALID)
        assert valid(r)
        assert errors(r) == []

    def test_missing_conbody(self):
        r = validate("<concept id='c1'><title>T</title></concept>")
        assert not valid(r)
        assert "body-required" in errors(r)

    def test_foreign_task_element_in_concept(self):
        r = validate(
            "<concept id='c1'><title>T</title><shortdesc>S</shortdesc>"
            "<conbody><steps><step><cmd>x</cmd></step></steps></conbody></concept>"
        )
        assert not valid(r)
        assert "foreign-element" in errors(r)


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

class TestTask:
    VALID = (
        "<task id='t1'><title>T</title><shortdesc>S</shortdesc>"
        "<taskbody><steps><step><cmd>Do it.</cmd></step></steps></taskbody></task>"
    )

    def test_valid_task(self):
        r = validate(self.VALID)
        assert valid(r)
        assert errors(r) == []

    def test_missing_taskbody(self):
        r = validate("<task id='t1'><title>T</title></task>")
        assert not valid(r)
        assert "body-required" in errors(r)

    def test_empty_steps_is_error(self):
        r = validate(
            "<task id='t1'><title>T</title><shortdesc>S</shortdesc>"
            "<taskbody><steps/></taskbody></task>"
        )
        assert not valid(r)
        assert "step-required" in errors(r)

    def test_step_without_cmd_is_error(self):
        r = validate(
            "<task id='t1'><title>T</title><shortdesc>S</shortdesc>"
            "<taskbody><steps><step><info>No cmd here</info></step></steps></taskbody></task>"
        )
        assert not valid(r)
        assert "cmd-required" in errors(r)

    def test_more_than_10_steps_warns(self):
        steps = "".join(f"<step><cmd>Step {i}</cmd></step>" for i in range(11))
        r = validate(
            f"<task id='t1'><title>T</title><shortdesc>S</shortdesc>"
            f"<taskbody><steps>{steps}</steps></taskbody></task>"
        )
        assert "step-count" in warnings(r)

    def test_duplicate_prereq_is_error(self):
        r = validate(
            "<task id='t1'><title>T</title><shortdesc>S</shortdesc>"
            "<taskbody><prereq/><prereq/>"
            "<steps><step><cmd>x</cmd></step></steps></taskbody></task>"
        )
        assert not valid(r)
        assert "prereq-singleton" in errors(r)

    def test_steps_unordered_valid(self):
        r = validate(
            "<task id='t1'><title>T</title><shortdesc>S</shortdesc>"
            "<taskbody><steps-unordered>"
            "<step><cmd>Do it.</cmd></step>"
            "</steps-unordered></taskbody></task>"
        )
        assert valid(r)

    def test_no_steps_warns_not_errors(self):
        r = validate(
            "<task id='t1'><title>T</title><shortdesc>S</shortdesc>"
            "<taskbody></taskbody></task>"
        )
        assert valid(r)
        assert "steps-recommended" in warnings(r)


# ---------------------------------------------------------------------------
# Reference
# ---------------------------------------------------------------------------

class TestReference:
    VALID = (
        "<reference id='r1'><title>T</title><shortdesc>S</shortdesc>"
        "<refbody><section><p>Content.</p></section></refbody></reference>"
    )

    def test_valid_reference(self):
        r = validate(self.VALID)
        assert valid(r)

    def test_missing_refbody(self):
        r = validate("<reference id='r1'><title>T</title></reference>")
        assert not valid(r)
        assert "body-required" in errors(r)

    def test_empty_property_row_warns(self):
        r = validate(
            "<reference id='r1'><title>T</title><shortdesc>S</shortdesc>"
            "<refbody><properties><property/></properties></refbody></reference>"
        )
        assert "property-empty" in warnings(r)

    def test_properties_with_cells_is_valid(self):
        r = validate(
            "<reference id='r1'><title>T</title><shortdesc>S</shortdesc>"
            "<refbody><properties>"
            "<property><proptype>Name</proptype><propvalue>Val</propvalue></property>"
            "</properties></refbody></reference>"
        )
        assert "property-empty" not in warnings(r)


# ---------------------------------------------------------------------------
# Troubleshooting
# ---------------------------------------------------------------------------

class TestTroubleshooting:
    VALID = (
        "<troubleshooting id='ts1'><title>T</title><shortdesc>S</shortdesc>"
        "<troublebody>"
        "<condition><p>Problem.</p></condition>"
        "<troubleSolution>"
        "<cause><p>Root cause.</p></cause>"
        "<remedy><steps><step><cmd>Fix it.</cmd></step></steps></remedy>"
        "</troubleSolution>"
        "</troublebody></troubleshooting>"
    )

    def test_valid_troubleshooting(self):
        r = validate(self.VALID)
        assert valid(r)

    def test_missing_troublebody(self):
        r = validate("<troubleshooting id='ts1'><title>T</title></troubleshooting>")
        assert not valid(r)
        assert "body-required" in errors(r)

    def test_missing_troublesolution_is_error(self):
        r = validate(
            "<troubleshooting id='ts1'><title>T</title><shortdesc>S</shortdesc>"
            "<troublebody><condition><p>P</p></condition></troublebody></troubleshooting>"
        )
        assert not valid(r)
        assert "troubleSolution-required" in errors(r)

    def test_duplicate_condition_is_error(self):
        r = validate(
            "<troubleshooting id='ts1'><title>T</title><shortdesc>S</shortdesc>"
            "<troublebody>"
            "<condition/><condition/>"
            "<troubleSolution><cause/></troubleSolution>"
            "</troublebody></troubleshooting>"
        )
        assert not valid(r)
        assert "condition-singleton" in errors(r)

    def test_troublesolution_with_no_cause_or_remedy_warns(self):
        r = validate(
            "<troubleshooting id='ts1'><title>T</title><shortdesc>S</shortdesc>"
            "<troublebody><troubleSolution/></troublebody></troubleshooting>"
        )
        assert "troubleSolution-empty" in warnings(r)


# ---------------------------------------------------------------------------
# Glossentry
# ---------------------------------------------------------------------------

class TestGlossentry:
    def test_valid_glossentry(self):
        r = validate("<glossentry id='g1'><glossterm>Term</glossterm><glossdef>Def.</glossdef></glossentry>")
        assert valid(r)

    def test_missing_glossterm_is_error(self):
        r = validate("<glossentry id='g1'><glossdef>Def.</glossdef></glossentry>")
        assert not valid(r)
        assert "glossterm-required" in errors(r)

    def test_missing_glossdef_is_error(self):
        r = validate("<glossentry id='g1'><glossterm>Term</glossterm></glossentry>")
        assert not valid(r)
        assert "glossdef-required" in errors(r)

    def test_reversed_glossterm_glossdef_is_error(self):
        r = validate("<glossentry id='g1'><glossdef>Def.</glossdef><glossterm>Term</glossterm></glossentry>")
        assert not valid(r)
        assert "glossterm-order" in errors(r)

    def test_foreign_task_element_in_glossentry_is_error(self):
        r = validate("<glossentry id='g1'><glossterm>T</glossterm><glossdef>D</glossdef>"
                     "<steps><step><cmd>x</cmd></step></steps></glossentry>")
        assert not valid(r)
        assert "foreign-element" in errors(r)
