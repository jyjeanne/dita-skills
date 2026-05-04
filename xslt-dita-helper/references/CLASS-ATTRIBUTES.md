# Class Attribute Reference — xslt-dita-helper

Full `@class` attribute values from DITA 1.3 DTD `<!ATTLIST>` declarations.
Use `contains(@class, ' token/token ')` — **note the surrounding spaces**.

## Base topic elements (`dtd/base/dtd/topic.mod`)

| Element | `@class` value |
|---|---|
| `topic` | `- topic/topic ` |
| `title` | `- topic/title ` |
| `titlealts` | `- topic/titlealts ` |
| `navtitle` | `- topic/navtitle ` |
| `searchtitle` | `- topic/searchtitle ` |
| `shortdesc` | `- topic/shortdesc ` |
| `abstract` | `- topic/abstract ` |
| `prolog` | `- topic/prolog ` |
| `metadata` | `- topic/metadata ` |
| `body` | `- topic/body ` |
| `bodydiv` | `- topic/bodydiv ` |
| `section` | `- topic/section ` |
| `sectiondiv` | `- topic/sectiondiv ` |
| `example` | `- topic/example ` |
| `related-links` | `- topic/related-links ` |
| `link` | `- topic/link ` |
| `p` | `- topic/p ` |
| `note` | `- topic/note ` |
| `ul` / `ol` / `li` | `- topic/ul ` / `- topic/ol ` / `- topic/li ` |
| `dl` / `dlentry` / `dt` / `dd` | `- topic/dl ` etc. |
| `fig` | `- topic/fig ` |
| `image` | `- topic/image ` |
| `xref` | `- topic/xref ` |
| `ph` | `- topic/ph ` |
| `keyword` | `- topic/keyword ` |
| `term` | `- topic/term ` |
| `indexterm` | `- topic/indexterm ` |

## Concept (`dtd/technicalContent/dtd/concept.mod`)

| Element | `@class` value |
|---|---|
| `concept` | `- topic/topic concept/concept ` |
| `conbody` | `- topic/body concept/conbody ` |
| `conbodydiv` | `- topic/bodydiv concept/conbodydiv ` |

## Task (`dtd/technicalContent/dtd/task.mod`)

| Element | `@class` value |
|---|---|
| `task` | `- topic/topic task/task ` |
| `taskbody` | `- topic/body task/taskbody ` |
| `prereq` | `- topic/section task/prereq ` |
| `context` | `- topic/section task/context ` |
| `steps` | `- topic/ol task/steps ` |
| `steps-unordered` | `- topic/ul task/steps-unordered ` |
| `steps-informal` | `- topic/section task/steps-informal ` |
| `step` | `- topic/li task/step ` |
| `cmd` | `- topic/ph task/cmd ` |
| `info` | `- topic/itemgroup task/info ` |
| `substeps` | `- topic/ol task/substeps ` |
| `substep` | `- topic/li task/substep ` |
| `tutorialinfo` | `- topic/itemgroup task/tutorialinfo ` |
| `stepxmp` | `- topic/itemgroup task/stepxmp ` |
| `choices` | `- topic/ul task/choices ` |
| `choice` | `- topic/li task/choice ` |
| `choicetable` | `- topic/simpletable task/choicetable ` |
| `stepresult` | `- topic/itemgroup task/stepresult ` |
| `steptroubleshooting` | `- topic/itemgroup task/steptroubleshooting ` |
| `result` | `- topic/section task/result ` |
| `tasktroubleshooting` | `- topic/section task/tasktroubleshooting ` |
| `postreq` | `- topic/section task/postreq ` |

## Reference (`dtd/technicalContent/dtd/reference.mod`)

| Element | `@class` value |
|---|---|
| `reference` | `- topic/topic reference/reference ` |
| `refbody` | `- topic/body reference/refbody ` |
| `refbodydiv` | `- topic/bodydiv reference/refbodydiv ` |
| `refsyn` | `- topic/section reference/refsyn ` |
| `properties` | `- topic/simpletable reference/properties ` |
| `prophead` | `- topic/sthead reference/prophead ` |
| `property` | `- topic/strow reference/property ` |
| `proptypehd` | `- topic/stentry reference/proptypehd ` |
| `propvaluehd` | `- topic/stentry reference/propvaluehd ` |
| `propdeschd` | `- topic/stentry reference/propdeschd ` |
| `proptype` | `- topic/stentry reference/proptype ` |
| `propvalue` | `- topic/stentry reference/propvalue ` |
| `propdesc` | `- topic/stentry reference/propdesc ` |

## Troubleshooting (`dtd/technicalContent/dtd/troubleshooting.mod`)

| Element | `@class` value |
|---|---|
| `troubleshooting` | `- topic/topic troubleshooting/troubleshooting ` |
| `troublebody` | `- topic/body troubleshooting/troublebody ` |
| `troubleSolution` | `- topic/bodydiv troubleshooting/troubleSolution ` |
| `condition` | `- topic/section troubleshooting/condition ` |
| `cause` | `- topic/section troubleshooting/cause ` |
| `remedy` | `- topic/section troubleshooting/remedy ` |
| `responsibleParty` | `- topic/ph troubleshooting/responsibleParty ` |

## Map (`dtd/base/dtd/map.mod`)

| Element | `@class` value |
|---|---|
| `map` | `- map/map ` |
| `topicref` | `- map/topicref ` |
| `topicmeta` | `- map/topicmeta ` |
| `navref` | `- map/navref ` |
| `anchor` | `- map/anchor ` |
| `reltable` | `- map/reltable ` |
| `relcolspec` | `- map/relcolspec ` |
| `relrow` | `- map/relrow ` |
| `relcell` | `- map/relcell ` |
| `keydef` | `- map/topicref bookmap/keydef ` |
