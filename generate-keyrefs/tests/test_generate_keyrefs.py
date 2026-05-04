"""
Tests for generate-keyrefs/scripts/generate_keyrefs.py
"""
import json
import sys
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

# Make script importable from any working directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import generate_keyrefs  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_dita(tmp_path: Path, name: str, body: str) -> Path:
    """Write a minimal DITA concept with the given body content."""
    p = tmp_path / name
    p.write_text(textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE concept PUBLIC "-//OASIS//DTD DITA Concept//EN" "concept.dtd">
        <concept id="{name.replace('.dita','')}">
          <title>Topic</title>
          <conbody>
            {body.strip()}
          </conbody>
        </concept>
    """), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# _slugify
# ---------------------------------------------------------------------------

class TestSlugify:

    def test_plain_text(self):
        assert generate_keyrefs._slugify("ACME Product") == "acme-product"

    def test_url_strips_protocol(self):
        slug = generate_keyrefs._slugify("https://docs.example.com/api")
        assert "https" not in slug
        assert "docs-example-com" in slug

    def test_url_strips_extension(self):
        slug = generate_keyrefs._slugify("images/logo.png")
        assert "png" not in slug
        assert "logo" in slug

    def test_special_chars(self):
        slug = generate_keyrefs._slugify("C++ Guide!")
        assert "+" not in slug
        assert "!" not in slug

    def test_max_length(self):
        long_text = "a" * 100
        assert len(generate_keyrefs._slugify(long_text)) <= 48


# ---------------------------------------------------------------------------
# _unique_key
# ---------------------------------------------------------------------------

class TestUniqueKey:

    def test_no_collision(self):
        used = set()
        key = generate_keyrefs._unique_key("product", used)
        assert key == "product"
        assert "product" in used

    def test_collision_appends_counter(self):
        used = {"product"}
        key = generate_keyrefs._unique_key("product", used)
        assert key == "product-2"

    def test_multiple_collisions(self):
        used = {"product", "product-2"}
        key = generate_keyrefs._unique_key("product", used)
        assert key == "product-3"


# ---------------------------------------------------------------------------
# scan_files — text candidates
# ---------------------------------------------------------------------------

class TestTextScan:

    def test_detects_repeated_ph(self, tmp_path):
        _write_dita(tmp_path, "a.dita", "<p><ph>ACME Pro</ph></p>")
        _write_dita(tmp_path, "b.dita", "<p><ph>ACME Pro</ph></p>")
        text, _ = generate_keyrefs.scan_files(
            list(tmp_path.glob("*.dita")), min_occurrences=2
        )
        assert "ACME Pro" in text

    def test_ignores_below_threshold(self, tmp_path):
        _write_dita(tmp_path, "a.dita", "<p><ph>ACME Pro</ph></p>")
        text, _ = generate_keyrefs.scan_files(
            list(tmp_path.glob("*.dita")), min_occurrences=2
        )
        assert "ACME Pro" not in text

    def test_skips_existing_keyref(self, tmp_path):
        p = tmp_path / "a.dita"
        p.write_text(textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <concept id="a"><title>T</title><conbody>
              <ph keyref="existing-key">ACME Pro</ph>
              <ph keyref="existing-key">ACME Pro</ph>
            </conbody></concept>
        """), encoding="utf-8")
        text, _ = generate_keyrefs.scan_files([p], min_occurrences=2)
        assert "ACME Pro" not in text

    def test_detects_term_and_prodname(self, tmp_path):
        _write_dita(tmp_path, "a.dita", "<p><term>DITA</term></p>")
        _write_dita(tmp_path, "b.dita", "<p><prodname>DITA</prodname></p>")
        text, _ = generate_keyrefs.scan_files(
            list(tmp_path.glob("*.dita")), min_occurrences=2
        )
        assert "DITA" in text


# ---------------------------------------------------------------------------
# scan_files — href candidates
# ---------------------------------------------------------------------------

class TestHrefScan:

    def test_detects_repeated_xref_href(self, tmp_path):
        _write_dita(tmp_path, "a.dita",
                    '<xref href="https://example.com/docs">Docs</xref>')
        _write_dita(tmp_path, "b.dita",
                    '<xref href="https://example.com/docs">Docs</xref>')
        _, href = generate_keyrefs.scan_files(
            list(tmp_path.glob("*.dita")), min_occurrences=2
        )
        assert "https://example.com/docs" in href

    def test_detects_image_href(self, tmp_path):
        _write_dita(tmp_path, "a.dita", '<image href="images/logo.png" alt=""/>')
        _write_dita(tmp_path, "b.dita", '<image href="images/logo.png" alt=""/>')
        _, href = generate_keyrefs.scan_files(
            list(tmp_path.glob("*.dita")), min_occurrences=2
        )
        assert "images/logo.png" in href


# ---------------------------------------------------------------------------
# build_keydefs
# ---------------------------------------------------------------------------

class TestBuildKeydefs:

    def test_text_keydef_contains_keyword_element(self):
        keydefs, block = generate_keyrefs.build_keydefs(
            {"ACME Pro": [("ph", Path("a.dita"))]}, {}
        )
        assert any(kd["key"] for kd in keydefs)
        assert "<keyword>ACME Pro</keyword>" in block

    def test_href_keydef_external_has_scope(self):
        _, block = generate_keyrefs.build_keydefs(
            {}, {"https://example.com": [("xref", Path("a.dita"))]}
        )
        assert 'scope="external"' in block
        assert 'format="html"' in block

    def test_image_href_keydef_has_img_prefix(self):
        keydefs, _ = generate_keyrefs.build_keydefs(
            {}, {"images/logo.png": [("image", Path("a.dita")), ("image", Path("b.dita"))]}
        )
        assert any("img-" in kd["key"] for kd in keydefs)

    def test_special_chars_in_value_escaped(self):
        _, block = generate_keyrefs.build_keydefs(
            {"AT&T": [("ph", Path("a.dita")), ("ph", Path("b.dita"))]}, {}
        )
        # The & must be XML-escaped in the keydef block
        assert "&amp;" in block
        # The literal unescaped & must not appear in the raw XML string
        assert "AT&T" not in block


# ---------------------------------------------------------------------------
# full generate() integration
# ---------------------------------------------------------------------------

class TestGenerate:

    def test_returns_expected_structure(self, tmp_path):
        _write_dita(tmp_path, "a.dita", "<ph>MyBrand</ph>")
        _write_dita(tmp_path, "b.dita", "<ph>MyBrand</ph>")
        result = generate_keyrefs.generate([tmp_path], min_occurrences=2)
        assert "keydefs" in result
        assert "changes" in result
        assert "keydef_block" in result
        assert "summary" in result
        assert result["summary"]["files_scanned"] == 2

    def test_empty_dir_returns_zero(self, tmp_path):
        result = generate_keyrefs.generate([tmp_path], min_occurrences=2)
        assert result["summary"]["files_scanned"] == 0
        assert result["keydefs"] == []


# ---------------------------------------------------------------------------
# apply_changes
# ---------------------------------------------------------------------------

class TestApplyChanges:

    def test_rewrites_ph_text(self, tmp_path):
        p = _write_dita(tmp_path, "a.dita", "<ph>MyBrand</ph>")
        keydefs = [{"key": "my-brand", "type": "text", "value": "MyBrand"}]
        applied = generate_keyrefs.apply_changes([p], keydefs)
        assert str(p) in applied
        content = p.read_text(encoding="utf-8")
        assert 'keyref="my-brand"' in content

    def test_rewrites_xref_href(self, tmp_path):
        p = _write_dita(tmp_path, "a.dita",
                        '<xref href="https://example.com">Link</xref>')
        keydefs = [{"key": "ext-example", "type": "href", "href": "https://example.com"}]
        generate_keyrefs.apply_changes([p], keydefs)
        content = p.read_text(encoding="utf-8")
        assert 'keyref="ext-example"' in content
        assert 'href="https://example.com"' not in content

    def test_idempotent_on_already_keyreffed(self, tmp_path):
        p = tmp_path / "a.dita"
        p.write_text(textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <concept id="a"><title>T</title><conbody>
              <ph keyref="my-brand"/>
            </conbody></concept>
        """), encoding="utf-8")
        keydefs = [{"key": "my-brand", "type": "text", "value": "MyBrand"}]
        applied = generate_keyrefs.apply_changes([p], keydefs)
        assert str(p) not in applied  # nothing to change
