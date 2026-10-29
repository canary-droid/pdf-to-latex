# Codex assessment of 31 final Qwen proposals — 24 October 2026

27 suitable for experimental application, four deferred; zero additional investigation-only dispositions. All remain UNACCEPTED. This is Codex assessment, not human verification or whole-page/book accuracy. All 31 complete replacements, corresponding structured OCR and selected source detail images were inspected. Full-page context was additionally inspected for physical pages 166, 170, 205 and 212, solely to interpret these proposals.

v105 would delete most of a paragraph under whole-block replacement and is deferred; its diagnosis is retained. v138 remains explicitly uncertain. v250 and v210 make unnecessary spacing changes and misdescribe the saved OCR. v093 removes an unmatched parenthesis visibly printed in the book: this is an explicitly allowed editorial repair, not an OCR error as Qwen claimed. v224 already has x^a in the OCR; only its spurious t accent is corrected. v001 retains a minor missing source comma. The printed apparent sign/limit issues in v005, v066 and v150 are preserved.

There are no overlapping proposal targets or declared dependency groups among these 31; the builder still enforces conflict and atomic-group safeguards. Historical proposed builds passed for 29; the v034/v036 heading proposals were NOT attempted because their original OCR fragments were unsupported. That is distinct from compiler failure. Compilation does not establish preservation.

| Unit / block | Physical / printed | Disposition | Specific reason |
|---|---|---|---|
| v001 / klebaner-ch4-7-p0001:b4 | 106 / 91 | suitable | Source supports plain 1, plain c, period after X dot B and comma after c; complete paragraph and interval conditions retained. Minor source comma after the first (0,a] remains absent; no mathematical content loss observed. |
| v036 / klebaner-ch4-7-p0011:b0 | 116 / 101 | suitable | Source heading is 4.2. ITÔ INTEGRAL PROCESS. Corrects lost accent and stray caret; complete heading retained. Proposed compilation was not attempted. |
| v088 / klebaner-ch4-7-p0011:b4 | 116 / 101 | suitable | Source has a period after the integrability condition. All theorem hypotheses, bounds, conclusion and theorem number retained. |
| v219 / klebaner-ch4-7-p0011:b7 | 116 / 101 | suitable | Source domain is blackboard-bold R; replacement preserves the boundedness condition, integral, corollary number and conclusion. |
| v034 / klebaner-ch4-7-p0021:b0 | 126 / 111 | suitable | Source heading has two accented ITÔ occurrences. Complete heading retained; straight apostrophe is a minor typographic normalization. Proposed compilation was not attempted. |
| v177 / klebaner-ch4-7-p0021:b3 | 126 / 111 | suitable | Source has plain Y, integral and H squared, with no tilde/dot. Entire paragraph, both almost-sure integrability conditions and Z definition retained; trailing comma matches source. |
| v191 / klebaner-ch4-7-p0021:b8 | 126 / 111 | suitable | Source ends the second integrability inequality with a comma. Both integrability conditions and following Z definition remain intact. |
| v204 / klebaner-ch4-7-p0021:b14 | 126 / 111 | suitable | Source visibly begins If f(x) and has (C squared function). Conditional clause and entire following stochastic-differential statement retained. |
| v224 / klebaner-ch4-7-p0031:b5 | 136 / 121 | suitable | Removing the spurious hat on t matches the source; entire exercise and parameters retained. Model explanation wrongly claims OCR x squared: saved OCR already has x to a, which the replacement retains. |
| v156 / klebaner-ch4-7-p0031:b12 | 136 / 121 | suitable | Source numerator is plain B(t); full exercise and printed 0 <= t <= T retained. Endpoint T is printed and has not been silently changed despite the apparent denominator issue. |
| v264 / klebaner-ch4-7-p0041:b9 | 146 / 131 | suitable | Source has Y followed by one comma, not a math period. Both full sentences and references (5.23)/(5.2) are preserved. |
| v250 / klebaner-ch4-7-p0041:b20 | 146 / 131 | deferred | Unnecessary cosmetic edit: TeX ignores spaces inside math-mode mathrm{a n d}, which already renders upright and. The claimed spaced-letter defect is incorrect. Formula, signs and tag already match source; retain original. |
| v235 / klebaner-ch4-7-p0051:b3 | 156 / 141 | suitable | Source has no enclosing absolute-value bars. Complete expression, lower s/upper t bounds, integrand and (5.53) tag retained; substantive correction supported. |
| v247 / klebaner-ch4-7-p0051:b10 | 156 / 141 | suitable | Source visibly numbers this condition 1., not capital I. Probability statement, domain and terminal comma retained. |
| v255 / klebaner-ch4-7-p0051:b15 | 156 / 141 | suitable | Source display ends in ds without a period. Removing the OCR period preserves the entire formula and its continuation; model calls it editorial but image supports an OCR punctuation correction. |
| v125 / klebaner-ch4-7-p0061:b2 | 166 / 151 | suitable | Source moment-generating functions use undecorated X(0), X(t). Entire theorem clause, previous-Theorem-6.2 reference, real-u quantifier and t>=0 condition retained. |
| v109 / klebaner-ch4-7-p0061:b3 | 166 / 151 | suitable | Source equation (6.8) has no terminal period; full stochastic expression, bounds, derivative and tag retained. |
| v210 / klebaner-ch4-7-p0061:b4 | 166 / 151 | deferred | Original f(x,t) in C^{2,1} is valid TeX and matches source; spaces in math mode do not make it malformed. Replacement is principally cosmetic; no demonstrated substantive correction. |
| v093 / klebaner-ch4-7-p0061:b9 | 166 / 151 | suitable | The extra closing parenthesis IS visibly printed inside the exponent. Removing it is a clear local editorial repair permitted for this experiment, not the OCR correction claimed by Qwen. Remaining derivative, square, inequality and constants unchanged. |
| v005 / klebaner-ch4-7-p0065:b14 | 170 / 155 | suitable | Source shows the complete nested-exponential/integral equation with positive exponents and inner upper s; replacement restores it without repairing possible author-level sign issues. Proposed build passed; original OCR syntax failed. |
| v251 / klebaner-ch4-7-p0071:b2 | 176 / 161 | suitable | Source real-line symbol is blackboard-bold R. Complete theorem, positivity/continuity, interval and initial-value conditions are preserved; spacing normalization is immaterial. |
| v138 / klebaner-ch4-7-p0081:b14 | 186 / 171 | deferred | Source crop appears consistent with ordinary italic L and sigma, but proposal is explicitly uncertain and changes only weight. Keep original and uncertainty; no automatic application. |
| v194 / klebaner-ch4-7-p0100:b2 | 205 / 190 | suitable | Source has the final period. Complete stopping-result argument, reference (7.7) and expectation equality retained; moving the reference to text is harmless. |
| v220 / klebaner-ch4-7-p0100:b5 | 205 / 190 | suitable | Source stopping-time symbol is tau, not bold italic 1. Whole theorem fragment and integrability hypothesis preserved; theorem-number bold styling is lost but content is retained. |
| v105 / klebaner-ch4-7-p0100:b15 | 205 / 190 | deferred | Incomplete whole-block replacement. Source confirms plain T_b, so diagnosis is useful, but proposed formula alone deletes the Laplace-transform introduction, Brownian starting value 0, hitting-time definition, b>0 and u>0 conditions, first exponential and reference (7.7). Preserve the entire original paragraph and retain diagnosis separately; no substring reinterpretation. |
| v253 / klebaner-ch4-7-p0100:b17 | 205 / 190 | suitable | Entire paragraph, positivity/finiteness assumption, expectation, square-root substitution and limiting statement match source. Math-marking the standalone u is a minor supported notation repair; printed t wedge T_b after the limit is retained. |
| v066 / klebaner-ch4-7-p0101:b4 | 206 / 191 | suitable | Full source paragraph checked: spurious exclamation/dotted delimiter and duplicated comma are removed; both limits, indicators, all expectation statements and references (7.12), (7.11), Theorem 3.18 remain. Printed no-/2 term on the infinite-hitting-time event is deliberately preserved. |
| v178 / klebaner-ch4-7-p0107:b7 | 212 / 197 | suitable | Source has lim inf; complete paragraph and expectation equalities, integrability claim and conditional-Fatou transition retained. |
| v150 / klebaner-ch4-7-p0107:b8 | 212 / 197 | suitable | Source has lim inf in both places. Full equation, conditioning sigma-field, inequality and (7.28) tag retained. Printed final M(s wedge tau_n) is preserved rather than silently repaired. |
| v043 / klebaner-ch4-7-p0120:b2 | 225 / 210 | suitable | Source has prose Davis apostrophe and final period. Entire exercise, starting value zero, exit interval,  / B / =1 and E(sqrt(T))<infinity condition retained. |
| v127 / klebaner-ch4-7-p0120:b7 | 225 / 210 | suitable | Source visibly has periods after [0,T] and a.e. Complete SDE, interval and if-and-only-if condition retained. |


Experimental candidate and critic preparation
-------------------------------------------
The linked experimental derivative contains all 267 block records, with 27 applied
and four deferred proposals. All deferred/unaffected draft strings are unchanged.
Three nonportable blocks (p0031:b4, p0081:b3, p0081:b19; klebaner-ch4-7 prefix)
retain complete structured OCR and image references, with explicit unresolved TeX
placeholders. The derivative is not a complete editable transcription.

Candidate compilation did not reach TeX: Docker socket permission denied. The
adapter recorded build_failure_unresolved, compilation_claim=false. Heading
proposals v034/v036 were historically not attempted, not failed. The runbook
provides a separate proposed-only heading build and exact candidate build, each
in a new sidecar; no original/candidate/critic evidence is overwritten.

The frozen 20-group critic selection, development/reserved split, 40 baseline
input/request files, prompts and budgets are unchanged in a new linked recipe.
40 text requests are prepared; first four pairs (eight requests) are available.
Reserved g16-Y is unavailable due to p0081:b19. g04-X and g16-X preserve complete
raw-OCR fallbacks from the frozen baseline; neither is silently cleaned. The
windows include 17 of the 27 applied replacements, with 11 changed passage pairs;
this is the existing bounded critic experiment, not coverage of all corrections.
Settings: regular DeepSeek-V4.1-Flash-TF, http://127.0.0.1:8894/v1, medium,
16384 tokens, 600 seconds, sequential, default sampling. No model calls made.

Validation: all 3515 files/membership in the completed continuation, its preview
and original frozen recipe remain unchanged. All 275 call seals and 12899 bound
critic source hashes verify. Full suite: 277 tests, 260 passed, 15 mock-server
socket-setup PermissionErrors, two real compiler opt-in skips; no assertion
failures. Ten focused new regressions pass, including the actual saved v105 case.
Python syntax and git diff --check pass. Offline checks do not establish fidelity.

See paths.json, validation.json, critic-preparation.json and the project runbook
for exact artifact paths, hashes, limitations and normal-terminal commands.

Actual paths:

- audit: `/home/mdi/projects/pdf-to-latex/runs/proposal-audit-20261024T134532Z-6a438a`
- source_run: `/home/mdi/projects/pdf-to-latex/runs/recovery-continuation-trial-20261024T112538Z-8d13d3`
- source_preview: `/home/mdi/projects/pdf-to-latex/runs/recovery-continuation-input-20261024T112538Z-e1a1ef`
- old_recipe: `/home/mdi/projects/pdf-to-latex/runs/text-critic-recipe-20261023T192309Z-6796b6`
- candidate: `/home/mdi/projects/pdf-to-latex/runs/evaluation-candidate-20261024T140145Z-6343d9`
- recipe: `/home/mdi/projects/pdf-to-latex/runs/text-critic-recipe-20261024T140149Z-e7a9d7`
- critic_preview: `/home/mdi/projects/pdf-to-latex/runs/text-critic-input-20261024T140150Z-062adf`
- critic_run: `/home/mdi/projects/pdf-to-latex/runs/text-critic-trial-20261024T140153Z-32efd8`
- critic_zip: `/home/mdi/projects/pdf-to-latex/results/text-critic-trial-20261024T140153Z-32efd8-inspection-20261024T140153Z-be73d2.zip`
- compiler_image: `sha256:cf31ff0238bc6a208228be07acb4a4122a248d0e019ea1ec0cfcd621ff57fd45`
