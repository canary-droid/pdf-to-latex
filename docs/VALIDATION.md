# Validation record — probe 0.1

Prepared on 17 October 2026. This records authoring-workspace checks, not a
successful Spark deployment or a measured PDF reconstruction score.

## Executed locally

- Python 3.12.14, PyMuPDF 1.26.6. The known-source fixture was compiled with
  XeLaTeX from TeX Live 2023 and rasterised into a separate scan PDF.
- The complete offline suite passed: **59 tests** using
  `python3 -m unittest discover -s tests -v`.
- Tests cover actual PDF preparation/page maps; overlapping-window ownership;
  malformed, missing, duplicate and wrongly typed converter page indices;
  blocked network isolation; immutable failed attempts; source/output/evidence
  integrity on resume; HTML escaping; exact local model selection; strict JSON
  validation; local-only endpoint handling; request bounds and credential
  redaction; system inventory and converter SDK contracts.
- Local HTTP tests use mock loopback servers. Converter contract and coordinator
  tests use mocks; they do not demonstrate successful MinerU inference.
- The paper input has 17 pages. The selected book chapter has 30 pages and maps
  to physical pages 89–118 of the 421-page uploaded book. Boundaries were checked
  against the contents and rendered pages. Manifests retain source hashes.
- The two-page native fixture and two-page image-only fixture share a known TeX
  source. These are inputs for future fidelity measurement, not OCR outputs.

## Still to be executed on the Sparks

- Reachability and exact served GLM model identity; text, strict JSON and basic
  image compatibility. A passing digit-image test does not qualify mathematical
  visual fidelity.
- Current head/peer inventory, memory headroom and Linux namespace support.
- ARM64 dependency installation, local model preparation and real Basic OCR.
- Runtime, memory behaviour, actual formula/table/transcription accuracy and
  the ten source-based checks in `FIDELITY_REVIEW.md`.
- Any Standard/vLLM qualification. Its adapter exists, but its runtime is not
  installed or proven by this package.

No real GLM endpoint, OCR service or Spark was contacted from the authoring
workspace. No OpenRouter request was made. No extracted document has yet been
certified faithful, assembled into a final book/article, or compiled by this
probe. Subsequent decisions must use the saved run evidence and human review,
not the offline test count.
