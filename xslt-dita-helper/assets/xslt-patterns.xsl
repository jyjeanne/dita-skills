<?xml version="1.0" encoding="UTF-8"?>
<!--
  xslt-patterns.xsl — Ready-to-use XSLT 2.0 templates for DITA 1.3
  Copy individual templates into your DITA-OT plugin stylesheet.
  Always match using @class (robust against specializations).
-->
<xsl:stylesheet version="2.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  exclude-result-prefixes="xs">

  <!-- ══════════════════════════════════════════════════════
       BASE TOPIC ELEMENTS
       ══════════════════════════════════════════════════════ -->

  <xsl:template match="*[contains(@class, ' topic/topic ')]" priority="5">
    <article class="topic {@outputclass}">
      <xsl:apply-templates/>
    </article>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' topic/title ')]
                        [parent::*[contains(@class, ' topic/topic ')]]" priority="5">
    <h1><xsl:apply-templates/></h1>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' topic/shortdesc ')]" priority="5">
    <p class="shortdesc"><xsl:apply-templates/></p>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' topic/section ')]" priority="5">
    <section>
      <xsl:if test="@id"><xsl:attribute name="id" select="@id"/></xsl:if>
      <xsl:apply-templates/>
    </section>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' topic/section ')]
                        /*[contains(@class, ' topic/title ')]" priority="6">
    <h2><xsl:apply-templates/></h2>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' topic/p ')]" priority="5">
    <p><xsl:apply-templates/></p>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' topic/note ')]" priority="5">
    <div class="note note--{(@type, 'note')[1]}">
      <xsl:apply-templates/>
    </div>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' topic/ul ')]" priority="5">
    <ul><xsl:apply-templates/></ul>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' topic/ol ')]" priority="5">
    <ol><xsl:apply-templates/></ol>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' topic/li ')]" priority="5">
    <li><xsl:apply-templates/></li>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' topic/xref ')]" priority="5">
    <a href="{@href}"><xsl:apply-templates/></a>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' topic/keyword ')]" priority="5">
    <code class="keyword"><xsl:apply-templates/></code>
  </xsl:template>

  <!-- ══════════════════════════════════════════════════════
       CONCEPT
       ══════════════════════════════════════════════════════ -->

  <xsl:template match="*[contains(@class, ' concept/concept ')]" priority="10">
    <article class="concept {@outputclass}">
      <xsl:apply-templates/>
    </article>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' concept/conbody ')]" priority="10">
    <div class="conbody">
      <xsl:apply-templates/>
    </div>
  </xsl:template>

  <!-- ══════════════════════════════════════════════════════
       TASK
       ══════════════════════════════════════════════════════ -->

  <xsl:template match="*[contains(@class, ' task/task ')]" priority="10">
    <article class="task {@outputclass}">
      <xsl:apply-templates/>
    </article>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' task/taskbody ')]" priority="10">
    <div class="taskbody">
      <xsl:apply-templates/>
    </div>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' task/prereq ')]" priority="10">
    <div class="prereq">
      <h3>Before you begin</h3>
      <xsl:apply-templates/>
    </div>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' task/context ')]" priority="10">
    <div class="context">
      <h3>About this task</h3>
      <xsl:apply-templates/>
    </div>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' task/steps ')]" priority="10">
    <ol class="steps">
      <xsl:apply-templates/>
    </ol>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' task/steps-unordered ')]" priority="10">
    <ul class="steps-unordered">
      <xsl:apply-templates/>
    </ul>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' task/step ')]" priority="10">
    <li class="step">
      <xsl:apply-templates/>
    </li>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' task/cmd ')]" priority="10">
    <span class="cmd"><xsl:apply-templates/></span>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' task/result ')]" priority="10">
    <div class="result">
      <h3>Results</h3>
      <xsl:apply-templates/>
    </div>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' task/postreq ')]" priority="10">
    <div class="postreq">
      <h3>What to do next</h3>
      <xsl:apply-templates/>
    </div>
  </xsl:template>

  <!-- ══════════════════════════════════════════════════════
       REFERENCE
       ══════════════════════════════════════════════════════ -->

  <xsl:template match="*[contains(@class, ' reference/reference ')]" priority="10">
    <article class="reference {@outputclass}">
      <xsl:apply-templates/>
    </article>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' reference/refsyn ')]" priority="10">
    <div class="refsyn">
      <h3>Syntax</h3>
      <xsl:apply-templates/>
    </div>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' reference/properties ')]" priority="10">
    <table class="properties">
      <xsl:apply-templates select="*[contains(@class, ' reference/prophead ')]"/>
      <tbody>
        <xsl:apply-templates select="*[contains(@class, ' reference/property ')]"/>
      </tbody>
    </table>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' reference/prophead ')]" priority="10">
    <thead>
      <tr>
        <xsl:apply-templates/>
      </tr>
    </thead>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' reference/property ')]" priority="10">
    <tr>
      <xsl:apply-templates/>
    </tr>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' reference/proptype ')]
                       |*[contains(@class, ' reference/propvalue ')]
                       |*[contains(@class, ' reference/propdesc ')]
                       |*[contains(@class, ' reference/proptypehd ')]
                       |*[contains(@class, ' reference/propvaluehd ')]
                       |*[contains(@class, ' reference/propdeschd ')]" priority="10">
    <td><xsl:apply-templates/></td>
  </xsl:template>

  <!-- ══════════════════════════════════════════════════════
       TROUBLESHOOTING
       ══════════════════════════════════════════════════════ -->

  <xsl:template match="*[contains(@class, ' troubleshooting/troubleshooting ')]" priority="10">
    <article class="troubleshooting {@outputclass}">
      <xsl:apply-templates/>
    </article>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' troubleshooting/condition ')]" priority="10">
    <div class="condition">
      <h3>Symptom</h3>
      <xsl:apply-templates/>
    </div>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' troubleshooting/troubleSolution ')]" priority="10">
    <div class="troubleSolution">
      <xsl:apply-templates/>
    </div>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' troubleshooting/cause ')]" priority="10">
    <div class="cause">
      <h4>Cause</h4>
      <xsl:apply-templates/>
    </div>
  </xsl:template>

  <xsl:template match="*[contains(@class, ' troubleshooting/remedy ')]" priority="10">
    <div class="remedy">
      <h4>Solution</h4>
      <xsl:apply-templates/>
    </div>
  </xsl:template>

</xsl:stylesheet>
