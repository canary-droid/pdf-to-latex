# Concurrency-only handover audit — 29 October 2026

Codex read-only assessment; not mathematical/source verification.

The actual operator pointer selected `editorial-chapters-trial-20261029T103643Z-713678`.
At15:02 UTC both writer locks were held, call100 was in flight and the stage had16
complete conversion/critic pairs. The existing safe-pause control was requested.
After its608.054-second request and normal compilation finished, the state became
paused and both locks released. The authoritative handover includes that additional
complete conversion, not the earlier snapshot. It awaits its own critic.

No model/API requests, services, installations, source PDFs or completed OCR were
changed during this task. Docker inspection is denied by this session. The normal
operator launcher must capture the current actual build and capacity; saved tags or
recipe revisions do not establish the full running build.

|Handover stage outcome|Count|
|---|---:|
|Completed conversion|17|
|Completed revised critic|16|
|Complete final response without a complete document|2|
|Dependent critic unavailable, no request|2|
|Pending conversion|113|
|Pending critic|114|

100 calls plus24 earlier calls remain in accounting. Full Bergomi Chapter1 was
already retained outside this remaining-work stage. Selected Bergomi18 parts have
14 passing compilation records,3 syntax failures and1 missing-context/macro failure.
Gatheral34 selected parts have passing compilation records. Compilation is not
mathematical correctness or full-book fidelity. Existing unresolved issues and
source supplements remain unchanged.

## Recorded requests, not inferred effort

|Actual stage requests|Count|Effort sent|Summed request seconds|
|---|---:|---|---:|
|Conversion|19|high|7067.706|
|Critic|16|max|7693.997|

All35 actual request bodies have `stream=true`, `max_tokens=131072`, exact model
`glm53-regular` and no sampling overrides. Both source extractions/section instructions
remain unchanged. Effective effort relies on the previously inspected installed
mapping; responses do not attest a level. Request sums above are a serial historical
measurement, never concurrent wall time or a future completion estimate.

Detailed per-call data are retained as `handover-audit.json` in the new linked run:
actual request hashes, effort, usage/reasoning/other completion counts, finish reasons,
latency, server prefill/decode and selected compilation status. Compiler duration was
not recorded and stays unknown. Missing counters are not filled with zeros.

Bergomi2-s10 / call083: finish `stop`,261.771s;158623 prompt,12355 completion,1 reasoning,
12354 other completion tokens; prefill84.4087s,decode177.0397s. Final channel is37323
characters of analysis/fragment material. It contains no complete document wrapper;
existing extraction records an ambiguous surrounded fence. Conversion diagnostic:
`Final answer retained but no unambiguous complete LaTeX document`.
The critic's `unavailable: No complete conversion to review` has no reserved call.
An announcement of that phase was not evidence of either a sent or completed critic.
This concurrency task does not modify the saved answer or the document contract.

Saved idle health just before call100 advertised4 streams, context1048576 and a
shared pool2015232 tokens, with126976 free and1867968 kept-prefix rows. Source inspection
of the local GLM multi-stream/cache patches shows unowned kept prefixes can be evicted;
free rows alone do not describe admissible pool capacity. Conversely, four slots do
not imply four independent1M contexts. The new coordinator reserves conservative full
request+output bounds against90% of the pool and checks actual two-node memory.
Actual immutable images/installed code/serving configuration are unverified here;
launch captures them read-only before concurrent dispatch. No runtime is changed.

## Later grouping opportunity, not an implementation

At this frozen handover the repeated-subsection-heading heuristic finds46 untouched
pending apparent recap units in8 chapters,74602 native characters. There are113
pending conversions with1267535 native characters in total. Chapter2's eight former
recap candidates have already completed and are excluded. This is5.9% of remaining
native text and40.7% of remaining conversion units. Source-page classification and
contiguity still require verification before a separate grouping experiment. No
repeated heading/content is deleted, and no units or request inputs were regrouped.
The complete six-item roadmap and acceptance conditions are in EDITORIAL-CHAPTERS.md.

## Validation

Independent development imports were verified from
`/tmp/pdf-to-latex-concurrency-development-20261029`. Original code remained unchanged
while its writer drained. Focused scheduler/legacy transport regressions pass,
including exact outgoing effort/token/stream serialization and legacy idle admission.
Full suite once:576 tests,549 passed,15 socket `PermissionError` errors,12 skips
(4 opt-in compiler and8 optional local-evidence checks absent from the compact copy).
No observed assertion failure. The old operator run had separately passed562 tests
with4 optional skips in216.559 seconds; that does not validate this new scheduler.
The next operator launch runs the changed normal-terminal suite once.

Live model concurrency, actual build capture, real cache/memory behavior and new
compiler execution remain untested here. Runtime qualification uses production
requests and preserves all results. It does not certify fidelity or compare identical
task sets. No duration promise or overall deadline is introduced.
