# Security review — ByrdWay Product Engineering Studio v0.4.3

Reviewed 2026-11-09 against SSOI §7. Every control below is tested in `tests/` unless marked otherwise.

## Threat model
Uploaded products are **untrusted** (they may come from marketplaces, collaborators or be corrupted). Assets of
value: the owner's original products and approved artwork, the OpenAI key and money, the owner's computer.

## Controls
| Risk | Control | Test |
|---|---|---|
| ZIP path traversal (`../`, absolute, `C:`, backslash, reserved names) | two-pass validation before any write; resolved-path containment | `test_security.ZipSecurity` |
| Symlinks, duplicates, encrypted entries | rejected | same |
| Archive bombs | entry count ≤ 500, total ≤ 150 MB, member ≤ 60 MB, ratio ≤ 200:1, **actual streamed bytes capped** (declared sizes can lie) | `test_archive_bomb_ratio`, `test_declared_size_lie_is_capped_while_streaming` |
| Corrupted / mislabeled files | CRC test, PDF magic bytes, NUL bytes in text → rejected; no partial product left behind | `InvalidUploads` |
| Original modification | copy verified by hash, stored read-only, re-verified before every job, QA, approval and export | `Preservation`, end-to-end tests |
| Untrusted JavaScript | executed **only** inside headless Chromium (renderer sandbox; OS sandbox enabled on Windows); every request intercepted, only `file://` inside the working copy allowed, network blocked; downloads and service workers disabled; time and click limits | `browsertest.py`, end-to-end tests |
| Code injection via math text | no `eval` of raw text: token whitelist, identifier whitelist, length limit, exponent-size guard before SymPy | `test_academic` (`__import__`, `9^9^9`) |
| Patch escaping the product | `safe_relpath` + containment check; binaries cannot be text-patched | `test_patch_rules`, `test_safe_relpath` |
| Silent edits to candidates | QA replays recorded history; candidate hash pinned through approval and export | `test_qa_detects_unrecorded_change`, `test_candidate_tamper_after_qa_blocks_approval` |
| Built-product injection | all blueprint text HTML-escaped; JSON data `</` escaped | `test_html_escaping_of_blueprint_content` |
| API key leakage | key only from env var or OS keyring; never in settings (refused), logs redacted (`sk-…`, `api_key=`, dict keys), no keys in source | `Secrets` tests |
| Unapproved spending | funded amount, reserve, per-job and daily caps, per-call owner dialog, unknown price refused, failed calls charged at estimate | `test_costs_ai` |
| Unapproved release / publication | QA PASS + named explicit owner approval + hash re-check; no upload code exists anywhere (TpT, email, etc.) | end-to-end tests |
| Backup tampering | per-file SHA-256 manifest verified after writing and before restore; restore makes a safety copy outside the workspace | `BackupRestore` |

## Network egress (complete list)
1. `api.openai.com` — only when the owner enables AI and approves the specific call (product text is sent; max 12,000 characters per call by default).
2. Playwright CDN — only when the owner runs `python -m playwright install chromium`.
3. PyPI — only during `install_windows.bat`.
Nothing else. Browser tests run fully offline.

## Residual risks (accepted / owner action)
* **Parser vulnerabilities** in MuPDF (PDF) or Chromium could be exploited by a malicious file. Mitigation: keep
  `pymupdf` and Playwright's Chromium updated (`pip install -U`, `playwright install chromium`); size limits.
* **SymPy simplification time**: a crafted 300-character expression could be slow. There is no hard per-item
  timeout (Python threads cannot be killed); the job runtime limit is checked between iterations only.
* **Workspace data is not encrypted at rest** (Documents folder). Use BitLocker on the PC.
* **Read-only flags** do not stop an administrator; integrity relies on SHA-256 re-verification, which does.
* **Windows sandboxing** of Chromium is enabled by code but was not exercised on a real Windows machine.
* Product text sent to OpenAI is subject to OpenAI's data policies; do not enable AI for confidential drafts.
