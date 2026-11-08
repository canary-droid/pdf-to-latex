# Mathpix supplement — 5 November 2026

Selected run: `runs/mathpix-comparison-20261105T064003Z`, linked to the same 32
selected pages in `extraction-comparison-20261104T233805Z`. This is eight PDF
subsets, with render-equality checks, full source/subset hashes and page maps.
No full originals, other corpus pages, or model conclusions were submitted.

The run finished: all eight jobs and all six requested output types downloaded.
Provider pipeline version: `SuperNet-202`. Seven direct TeX builds passed; Breaking
Barriers failed on Unicode black square U+25A0 at document.tex line340. Raw output
is unchanged. `SOURCE-REVIEW.md` records eight direct sampled comparisons, including
preserved CF Case17 equations33–34, the printed Anfuso equation13 numerator, and
Breaking Barriers Figure4. It also records a real O-versus-zero transcription error
in the latter paper. These checks do not certify all 32 pages.

## Controls

```bash
bash scripts/run-mathpix-comparison.sh status
bash scripts/run-mathpix-comparison.sh resume
bash scripts/run-mathpix-comparison.sh pause
bash scripts/run-mathpix-comparison.sh bundle
bash scripts/run-mathpix-comparison.sh usage
```

`usage` refreshes the key's month-to-date `/v3/ocr-usage` snapshot without submitting
a document. Finished `resume` makes zero API calls. The worker uses its own run
lock and persistent tmux session `pdf-mathpix-comparison`; it does not take the
local extraction worker's project lock or change services.

## Accounting and privacy

The operator authorised at most $1.00 before tax for this supplement. Official
published `/v3/pdf` pricing checked on 5 November was $0.005/page, giving a $0.16
estimate for 32 pages. The persistent ledger at
`results/mathpix-accounting/ledger.json` reserves before each POST, retains unknown
charges, immediately stores returned pdf_id values and does not resubmit uncertain
requests. Its budget survives resumes and key changes; no billing settings or
provider quotas are changed. Failed/uncertain submissions remain consumed.

Observed after this run: $0.16 reserved and $0.16 locally estimated; zero uncertain
submissions. Provider usage increased from no reported rows to **32 pdf-page units**
and eight records for each requested conversion format. These are consumption
counters, not an invoice or proof of credits/balance. Actual invoice cost and
credits remain unknown; reports can lag and can include other applications.

Credentials are read only by the authenticated runtime from
`/home/mdi/.config/pdf-to-latex/mathpix.json`. They never enter command arguments,
saved headers, prompts or ZIPs. Response authentication fields are redacted.
`metadata.improve_mathpix=false`, `rm_fonts=false`, equation tags and page breaks
are requested. Account-level privacy settings can override request settings.
The documented PDF policy deletes the source after processing but separately
retains page images up to30 days and text outputs up to90 days. The opt-out is not
presented as zero retention. No account-level settings or deletion API was changed.

Raw MMD, Markdown, `.tex.zip`, `.mmd.zip`, `.lines.json` and `.lines.mmd.json` remain
local. The direct compiler uses the existing isolated image, with identical master
bytes and no model-assisted repair. The supplement has **zero GLM requests**.
After the local comparison finishes, the settled archives are combined into a new
report/ZIP with a four-arm side-by-side HTML. Earlier archives remain intact.

Primary references: https://docs.mathpix.com/reference/post-v3-pdf,
https://docs.mathpix.com/reference/ocr-usage,
https://website.mathpix.com/pricing/api,
https://docs.mathpix.com/concepts/data-retention.
