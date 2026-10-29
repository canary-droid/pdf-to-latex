# Selective sciwrite-lint reuse — 23 October 2026

25 October extension: `critic_anchors.py` reuses `consistency_query` and the same
untrusted-data wrapper for the versioned `critic-anchors-v2` contract. Python binds
whole-block anchors to exact candidate/source hashes and reconstructs quotations
and offsets; the model cites IDs. Old `text_critic.SCHEMA`, prompt and quote
validation remain selected for legacy data. No fragile sentence or TeX splitter
was added. The new production prompt requests material mathematical consequences
and supporting reasoning, not routine editorial findings.

`critic_context.py` reuses `command_spans`, exact source maps and
`bibliography.inventory` for a small local label index. Missing/ambiguous labels,
unresolved OCR and incomplete theorem neighborhoods remain explicit. There are
no embeddings, external lookups, invented citations or new upstream dependencies.
`finding_views` now separates material/context/visual/editorial queues; severity
alone never makes a finding editorial. Display deduplication includes candidate
and draft identities and retains every contributing finding/attempt. Historical
or rejected findings get no final-completion credit. The MIT attribution below
continues to apply; no full upstream application is installed.

The supplied `sciwrite_lint-0.6.1.tar.gz` was read through `tarfile` member streams,
with regular-file, path and size checks. It was not installed, extracted into this
repository, or executed. SHA-256 verified:
`7a76f0e3435e145a220eb5f0adabcad445706131ea9631e27f97394e240202b0`.
Identity came from the supplied `UPSTREAM.json`: sciwrite-lint 0.6.1,
https://github.com/authentic-research-partners/sciwrite-lint,
Copyright (c) 2025 Sergey Samsonau, MIT. The complete licence is retained in
[licenses/sciwrite-lint-MIT.txt](licenses/sciwrite-lint-MIT.txt).

| Upstream component | Local reuse | Changes and limits |
|---|---|---|
| `prompt_safety.py`: `ANTI_INJECTION_INSTRUCTION`, `wrap_untrusted` | `probe/sciwrite_subset.py` | Constant and wrapper behavior retained; no upstream dependencies. These are prompt instructions, not an execution boundary. |
| `checks/full_paper_consistency.py`: `format_system_prompt`, `_make_check_fns` query/state pattern | `sciwrite_subset.consistency_query`, `text_critic.request` | Same system/shared context/question/schema/state separation, adapted to one coherent mathematical window and exact TeX. No body cleaner, figure cache, model probe or automatic context clipping. |
| `checks/cross_section_consistency.py`: `_CONSISTENCY_SYSTEM` | `text_critic.SYSTEM` | Retains the same-object/same-scope contradiction distinction, equivalent notation and missing-context restraint; mathematical questions replace paper-summary comparisons. No four-finding cap. |
| `_process_results` and full-paper `_extract_findings` | `sciwrite_subset.finding_views`, `text_critic.located_findings` | Adapted evidence-key grouping and material queue projection. Every raw finding survives; no `is_genuine` filtering or `truncate_to_model`. Local quoted-span, location, draft-hash and stable-ID checks added. |
| `tex_parser.py`: `find_all_commands`, `find_all_cite_keys` | `sciwrite_subset.command_spans`, `citation_spans` | Balanced-brace scan and citation-key splitting adapted to exact offsets, escaped braces and source maps. Only the listed command family is parsed. Optional arguments, comments/verbatim and natural-language references have explicitly partial coverage. |
| `references/citations.py`: `extract_bibitems` inline discovery | `bibliography.inventory` | Inline bibitem boundaries retained, raw entries preserved. Broad author/title guessing, file following and text cleaning omitted. Structured fields require exact raw-source spans before candidate BibTeX export. |
| `checks/dangling_ref.py`, `dangling_cite.py` | `bibliography.inventory` | Adapted target membership checks. Missing chapter references become unresolved/unknown-outside-window, not nonexistent sources or fabricated citations. |
| `models.py`: `Finding`, `Citation`; `schemas.py`: contradiction/result contracts | `text_critic.SCHEMA`, bibliography JSON contract | Dependency-free explicit contracts, exact quotations, uncertainty, mathematical consequence and separate provenance statuses. No Pydantic coercion, silent truncation, service calls or upstream application migration. |

This is a manuscript consistency check, not a theorem prover. It cannot determine
what a source image prints. Text-dependent concerns go to human mathematical
review; unresolved visual questions go back to a source-image queue.

Explicit exclusions: `strip_latex_for_review`, equation-stripping embedding,
3,000-character slices, four/five-finding caps, upstream service control, default
model fallback, vLLM probing, figure-description loading and arbitrary package
imports. No upstream execution or additional dependency is needed for this path.

The local bibliography inventory preserves the textbook's identity/edition,
original PDF hash and selected source map, raw entries and citation occurrences.
Metadata checked, full text available, actual consultation and claim support are
four separate statuses. Seeing a textbook cite a work establishes none of the
last three. Printed year markers are possible citations, not parsed identities.
No structured entries are invented; candidate `.bib` output requires supported
fields with exact source spans. Existing `.bib` bytes can be retained unparsed;
this implementation is not a universal BibTeX parser and needs no parser install.

Later, separately authorized work may adapt `references/citations.parse_bib_file`
for explicit local `.bib` inputs, `crossref.crossref_lookup` and
`matching.compare_citation_detailed` for metadata comparisons,
`reference_store.parse_and_store` for acquired source provenance, and
`workspace_db/claim_results` contracts for claim-specific supporting spans.
Those paths have not been imported or enabled. Acquisition, external lookups,
claim judgments and optional parser dependency setup are deferred. A new authored
book must select the works it actually cites, retain direct versus second-hand
consultation, and export only those entries; it must not inherit a textbook's
entire bibliography as if every source had been read.


## 25 October 2026 — Task 2 adaptations

The MIT attribution and upstream boundaries remain unchanged. `finding_views`
now projects independent material/context/visual dimensions and separately collapses
positive/editorial observations. Exact candidate/draft provenance, substantive
fields and all contributor IDs are retained when grouping display entries.
`compare_findings` matches overlapping bound spans and broad claim topics as a
review aid, not semantic equivalence or mathematical proof. Non-repetition is not
a refutation. The local context index uses observed statement boundaries and exact
whole blocks; no embedding, punctuation splitter, upstream runtime or reference
fetching was added. Critic v3 uses program-owned bindings and exact-path format
repair while preserving the legacy protocols and original raw responses.
