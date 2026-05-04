"""
test_ditaval_helper.py — Unit tests for ditaval-helper/scripts/ditaval_helper.py
"""
import pytest
from ditaval_helper import validate_ditaval, generate_ditaval, _parse_condition


def errors(r):   return [e["rule"] for e in r["errors"]]
def warnings(r): return [w["rule"] for w in r["warnings"]]
def valid(r):    return r["is_valid"]


# ---------------------------------------------------------------------------
# validate_ditaval — root element
# ---------------------------------------------------------------------------

class TestRoot:
    def test_valid_minimal_val(self):
        r = validate_ditaval('<val><prop action="include" att="audience" val="dev"/></val>')
        assert valid(r)

    def test_malformed_xml(self):
        r = validate_ditaval("<val><prop action='include'")
        assert not valid(r)
        assert "well-formed" in errors(r)

    def test_wrong_root_is_error(self):
        r = validate_ditaval('<filter><prop action="include" att="audience"/></filter>')
        assert not valid(r)
        assert "root-element" in errors(r)


# ---------------------------------------------------------------------------
# <prop> rules
# ---------------------------------------------------------------------------

class TestProp:
    def test_missing_att_is_error(self):
        r = validate_ditaval('<val><prop action="exclude" val="internal"/></val>')
        assert not valid(r)
        assert "att-required" in errors(r)

    def test_missing_action_is_error(self):
        r = validate_ditaval('<val><prop att="audience" val="dev"/></val>')
        assert not valid(r)
        assert "action-required" in errors(r)

    def test_invalid_action_is_error(self):
        r = validate_ditaval('<val><prop att="audience" val="dev" action="hide"/></val>')
        assert not valid(r)
        assert "action-invalid" in errors(r)

    @pytest.mark.parametrize("action", ["include", "exclude", "flag", "passthrough"])
    def test_valid_actions_accepted(self, action):
        xml = f'<val><prop att="audience" val="dev" action="{action}"/></val>'
        r = validate_ditaval(xml)
        assert "action-invalid" not in errors(r)

    def test_duplicate_att_val_is_error(self):
        r = validate_ditaval(
            '<val>'
            '<prop att="audience" val="dev" action="include"/>'
            '<prop att="audience" val="dev" action="exclude"/>'
            '</val>'
        )
        assert not valid(r)
        assert "duplicate-prop" in errors(r)

    def test_no_val_attr_is_default_action(self):
        r = validate_ditaval('<val><prop att="audience" action="exclude"/></val>')
        assert valid(r)

    def test_two_different_vals_same_att_is_valid(self):
        r = validate_ditaval(
            '<val>'
            '<prop att="audience" val="dev" action="include"/>'
            '<prop att="audience" val="qa"  action="exclude"/>'
            '</val>'
        )
        assert valid(r)


# ---------------------------------------------------------------------------
# <prop action="flag"> visual feedback
# ---------------------------------------------------------------------------

class TestFlagFeedback:
    def test_flag_without_visual_warns(self):
        r = validate_ditaval(
            '<val><prop att="product" val="pro" action="flag"/></val>'
        )
        assert "flag-no-feedback" in warnings(r)

    def test_flag_with_color_no_warning(self):
        r = validate_ditaval(
            '<val><prop att="product" val="pro" action="flag" color="#0055CC"/></val>'
        )
        assert "flag-no-feedback" not in warnings(r)

    def test_flag_with_startflag_no_warning(self):
        r = validate_ditaval(
            '<val><prop att="product" val="pro" action="flag">'
            '<startflag><alt-text>PRO</alt-text></startflag>'
            '</prop></val>'
        )
        assert "flag-no-feedback" not in warnings(r)

    def test_invalid_style_is_error(self):
        r = validate_ditaval(
            '<val><prop att="product" val="pro" action="flag" '
            'style="bold" color="#00F"/></val>'
        )
        assert not valid(r)
        assert "style-invalid" in errors(r)

    @pytest.mark.parametrize("style", [
        "underline", "double-underline", "italics", "overline", "line-through"
    ])
    def test_valid_styles(self, style):
        r = validate_ditaval(
            f'<val><prop att="product" val="pro" action="flag" '
            f'style="{style}" color="#00F"/></val>'
        )
        assert "style-invalid" not in errors(r)


# ---------------------------------------------------------------------------
# <revprop>
# ---------------------------------------------------------------------------

class TestRevprop:
    def test_valid_revprop(self):
        r = validate_ditaval(
            '<val><revprop action="flag" val="2.1" color="#00F"/></val>'
        )
        assert valid(r)

    def test_missing_action_is_error(self):
        r = validate_ditaval('<val><revprop val="2.1"/></val>')
        assert not valid(r)
        assert "action-required" in errors(r)

    def test_revprop_flag_without_visual_warns(self):
        r = validate_ditaval('<val><revprop action="flag" val="2.1"/></val>')
        assert "flag-no-feedback" in warnings(r)

    def test_revprop_no_val_is_valid(self):
        r = validate_ditaval('<val><revprop action="exclude"/></val>')
        assert valid(r)


# ---------------------------------------------------------------------------
# <style-conflict>
# ---------------------------------------------------------------------------

class TestStyleConflict:
    def test_single_style_conflict_valid(self):
        r = validate_ditaval(
            '<val>'
            '<prop att="audience" val="dev" action="flag" color="#00F"/>'
            '<style-conflict foreground-conflict-color="#CC0000"/>'
            '</val>'
        )
        assert valid(r)

    def test_duplicate_style_conflict_is_error(self):
        r = validate_ditaval(
            '<val>'
            '<prop att="audience" val="dev" action="flag" color="#00F"/>'
            '<style-conflict foreground-conflict-color="#CC0000"/>'
            '<style-conflict foreground-conflict-color="#FF0000"/>'
            '</val>'
        )
        assert not valid(r)
        assert "style-conflict-singleton" in errors(r)


# ---------------------------------------------------------------------------
# generate_ditaval
# ---------------------------------------------------------------------------

class TestGenerateDitaval:
    def test_generates_valid_xml(self):
        import xml.etree.ElementTree as ET
        xml = generate_ditaval([
            {"attribute": "audience", "value": "internal", "action": "exclude"},
            {"attribute": "platform", "value": "linux",    "action": "include"},
        ])
        root = ET.fromstring(xml)
        assert root.tag == "val"

    def test_exclude_prop_present(self):
        xml = generate_ditaval([
            {"attribute": "audience", "value": "internal", "action": "exclude"},
        ])
        assert 'action="exclude"' in xml
        assert 'att="audience"' in xml
        assert 'val="internal"' in xml

    def test_flag_has_startflag(self):
        xml = generate_ditaval([
            {"attribute": "product", "value": "pro", "action": "flag",
             "color": "#0055CC"},
        ])
        assert "<startflag>" in xml

    def test_style_conflict_added_when_flags_present(self):
        xml = generate_ditaval([
            {"attribute": "product", "value": "pro", "action": "flag",
             "color": "#0055CC"},
        ])
        assert "style-conflict" in xml

    def test_no_style_conflict_without_flags(self):
        xml = generate_ditaval([
            {"attribute": "audience", "value": "internal", "action": "exclude"},
        ])
        assert "style-conflict" not in xml

    def test_revflag_generates_revprop(self):
        xml = generate_ditaval([
            {"attribute": "rev", "value": "2.1", "action": "revflag",
             "style": "underline"},
        ])
        assert "<revprop" in xml

    def test_generated_output_passes_validation(self):
        """Output of generate must pass our own validator."""
        xml = generate_ditaval([
            {"attribute": "audience", "value": "internal", "action": "exclude"},
            {"attribute": "platform", "value": "linux",    "action": "include"},
            {"attribute": "product",  "value": "pro",      "action": "flag",
             "color": "#0055CC", "style": "underline"},
        ])
        r = validate_ditaval(xml)
        assert r["is_valid"], f"Generated DITAVAL failed validation: {r['errors']}"


# ---------------------------------------------------------------------------
# _parse_condition helper
# ---------------------------------------------------------------------------

class TestParseCondition:
    def test_simple_att_val(self):
        c = _parse_condition("audience=internal", "exclude")
        assert c["attribute"] == "audience"
        assert c["value"] == "internal"
        assert c["action"] == "exclude"

    def test_with_visual_extras(self):
        c = _parse_condition("product=pro:color=#00F:style=underline", "flag")
        assert c["attribute"] == "product"
        assert c["color"] == "#00F"
        assert c["style"] == "underline"

    def test_att_only_no_val(self):
        c = _parse_condition("audience", "exclude")
        assert c["attribute"] == "audience"
        assert c["value"] == ""
