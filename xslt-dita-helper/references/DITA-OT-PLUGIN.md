---
# DITA-OT Plugin Development — xslt-dita-helper
# See: https://www.dita-ot.org/dev/topics/plugin-creating.html
---

# DITA-OT Plugin Reference — xslt-dita-helper

## Minimum plugin structure

```
com.example.myplugin/
├── plugin.xml         # Required: declares extension points
└── xsl/
    └── override.xsl   # XSLT stylesheet with template overrides
```

## plugin.xml skeleton

```xml
<?xml version="1.0" encoding="UTF-8"?>
<plugin id="com.example.myplugin">
  <require plugin="org.dita.html5"/>
  <feature extension="dita.xsl.xhtml" value="xsl/override.xsl" type="file"/>
</plugin>
```

Common extension points:

| Extension point | Targets |
|---|---|
| `dita.xsl.xhtml` | HTML5 output (XHTML) |
| `dita.xsl.xslfo` | PDF via XSL-FO |
| `dita.xsl.docbook` | DocBook output |
| `ant.import` | Ant build customization |

## override.xsl skeleton

```xslt
<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <!-- Import the default DITA-OT HTML5 stylesheet -->
  <xsl:import href="plugin:org.dita.html5:xsl/dita2html5Impl.xsl"/>

  <!-- Override: render <note> with a custom wrapper -->
  <xsl:template match="*[contains(@class, ' topic/note ')]" priority="10">
    <div class="note note--{@type}">
      <xsl:apply-templates/>
    </div>
  </xsl:template>

  <!-- Override: pass @outputclass as HTML class -->
  <xsl:template match="*[contains(@class, ' topic/ph ')]" priority="10">
    <span>
      <xsl:if test="@outputclass">
        <xsl:attribute name="class" select="@outputclass"/>
      </xsl:if>
      <xsl:apply-templates/>
    </span>
  </xsl:template>

</xsl:stylesheet>
```

## Priority rules

- Built-in DITA-OT templates typically have priority `0` or `1`
- Use `priority="10"` in your override to reliably take precedence
- Do **not** use `priority="-1"` — that makes your template a fallback

## Key XPath patterns for DITA

```xslt
<!-- Match any topic type -->
*[contains(@class, ' topic/topic ')]

<!-- Match concept body -->
*[contains(@class, ' concept/conbody ')]

<!-- Match task steps (ordered or unordered) -->
*[contains(@class, ' task/steps ') or contains(@class, ' task/steps-unordered ')]

<!-- Match a step's command -->
*[contains(@class, ' task/cmd ')]

<!-- Match a reference properties table -->
*[contains(@class, ' reference/properties ')]

<!-- Match conditional content for post-processing -->
*[@audience or @platform or @product]

<!-- Get the topic type from class attribute -->
substring-before(substring-after(@class, '- '), '/')
```

## Processing instructions

```xslt
<!-- Handle DITA-OT processing instructions -->
<xsl:template match="processing-instruction('dita-ot')">
  <!-- Custom PI handling -->
</xsl:template>
```
