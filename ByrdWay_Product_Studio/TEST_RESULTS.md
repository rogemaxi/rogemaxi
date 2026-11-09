# Test execution results — ByrdWay Product Engineering Studio v0.4.0

Windows results: GitHub Actions run https://github.com/rogemaxi/rogemaxi/actions/runs/42663089124 (commit faa30e9).
The workflow fails if ANY test is skipped on Windows, if the packaged .exe self-test fails, or if the .exe version
differs from `version.py`.

| Environment | Command | Result |
|---|---|---|
| **Windows Server 2025** (windows-2025-vs2026), Python 3.12 | `python -m unittest discover -s tests -v` | **Ran 127 tests — OK, 0 skipped** (incl. 15 real-window GUI tests) |
| **Windows**, source | `python app.py --selftest` | **14/14 passed**, version 0.4.0 |
| **Windows**, packaged | `pyinstaller byrdway_studio.spec` → `ByrdWayStudio.exe --selftest` | **14/14 passed**, version 0.4.0 = version.py |
| **Windows**, packaged GUI | launch `ByrdWayStudio.exe` | window started, ran 20 s, workspace created |
| Linux, Python 3.12 + Tk + Xvfb | `xvfb-run -a python -m unittest discover -s tests -v` | Ran 127 tests — OK, 0 skipped |
| Linux, Python 3.13 (no Tk) | `python -m unittest discover -s tests` | Ran 127 tests — OK, 15 skipped (GUI tests need Tk; they run on Windows) |

## Real-window GUI tests (tests/test_gui_workflows.py) — all PASS on Windows
Products & Jobs: import → diagnose (read-only report) → repair copy → report with before/after → approve → export →
original byte-identical · release gate refuses approval/export of a BLOCKED job, reject works · bad import explained
and logged · 16 buttons explain when nothing is selected · every button wired.
Builders: form validation errors with line numbers (nothing built) · draft save + resume · form → 2 modules →
review → approve → assemble → Release QA PASS · wrong answer blocks unit with plain message · sample labelled and
blocked · Lil Dr. Byrd: missing image blocks, registered image → approved.
Settings/Backup/Help: limits validation + AI DISABLED status · backup + restore · Help self-test shows version.

## Defects found by these tests and fixed (details: ROOT_CAUSE_REPORT.md)
R4 Tk abort from garbage collection on a worker thread · R5 built modules blocked by missing hidden elements ·
R6 "Open Latest Report" ordering · R7 method name clash preventing the window from opening · R8 (earlier) .exe
could not find Chromium.

## Coverage map (SSOI §9 → tests)
| Required area | Tests |
|---|---|
| Original preservation | `test_security.Preservation`, end-to-end tests assert byte-identical originals after import, repair, approval, export |
| ZIP security / archive bombs | `test_security.ZipSecurity` (14 cases incl. streamed-size lie) |
| Invalid / corrupted uploads | `test_security.InvalidUploads` |
| HTML structure, accessibility, navigation | `test_builders_release.HtmlAuditCoverage`, end-to-end fixture |
| JavaScript functionality (real browser) | `test_repair_loop.EndToEndPowerTool`, `test_builders_release.test_built_module_works_in_browser_and_scores`, `test_costs_ai.AIInLoop` |
| Mathematical answer verification | `test_academic` (33 cases across algebra, geometry, calculus, statistics, physics/units) |
| Deliberately wrong answer: detect → repair working copy → verify → original preserved | `test_repair_loop.test_broken_fails_before_and_passes_after_with_browser_evidence`, `PdfLoop.test_wrong_claim_repaired_with_visual_evidence` |
| PDF inspection / visual comparison | `PdfLoop` (render diff confined to corrected region; flattened page refused) |
| Repair proposals / diff / rollback | `test_security.test_working_copy_isolated_and_rollback`, `test_patch_rules` |
| Regression detection + rollback | `LoopControls.test_regression_triggers_rollback_and_escalation` |
| Quality scoring / critical blocking | `test_repair_loop.Scoring`, `test_unfixable_runtime_error_blocks_release` |
| Agent coordination / QA independence | `Coordination`, `test_qa_detects_unrecorded_change` |
| API failures, spending limits | `test_costs_ai.Guard`, `AIInLoop.test_api_error_handled`, `test_budget_stop_inside_loop` |
| Iteration / runtime / no-progress limits | `LoopControls` |
| Backup and restore | `BackupRestore` |
| Approval authorization | end-to-end tests, `test_candidate_tamper_after_qa_blocks_approval`, builder approval tests |
| Export integrity | `verify_export` assertions incl. tamper detection |
| Desktop UI | `test_ui_smoke` (import → job → QA view in the real Tk app) |

## Defects found by testing and fixed
* Windows CI run 1: inside the .exe, Playwright looked for Chromium only inside the package → browser tests did not run. Fixed in `browsertest.configure_frozen`; run 3 passes.
* Earlier: scanned page with only a page number treated as text; QA accepted silent edits in already-patched files (now history replay); built-module answer keys invisible to QA; Chromium OS sandbox disabled.

## Older verbose output (v0.2 Linux run, 96 tests, kept for history)
```
test_cases (test_academic.TestVerifier.test_cases) ... ok
test_extract_claims_from_text (test_academic.TestVerifier.test_extract_claims_from_text) ... ok
test_html_data_attribute_items (test_academic.TestVerifier.test_html_data_attribute_items) ... ok
test_mcq_index_repair (test_academic.TestVerifier.test_mcq_index_repair) ... ok
test_multiple_choice_index (test_academic.TestVerifier.test_multiple_choice_index) ... ok
test_no_answer_is_parse_error (test_academic.TestVerifier.test_no_answer_is_parse_error) ... ok
test_source_item_extraction_and_repair_patch (test_academic.TestVerifier.test_source_item_extraction_and_repair_patch) ... ok
test_wrong_answer_gets_deterministic_suggestion (test_academic.TestVerifier.test_wrong_answer_gets_deterministic_suggestion) ... ok
test_backup_verify_restore (test_builders_release.BackupRestore.test_backup_verify_restore) ... ok
test_damaged_backup_refused (test_builders_release.BackupRestore.test_damaged_backup_refused) ... ok
test_controller_surface (test_builders_release.Coordination.test_controller_surface) ... ok
test_roles_and_independence (test_builders_release.Coordination.test_roles_and_independence) ... ok
test_clean_page_has_no_major_findings (test_builders_release.HtmlAuditCoverage.test_clean_page_has_no_major_findings) ... ok
test_detects_accessibility_structure_navigation (test_builders_release.HtmlAuditCoverage.test_detects_accessibility_structure_navigation) ... ok
test_reference_outside_package_is_critical (test_builders_release.HtmlAuditCoverage.test_reference_outside_package_is_critical) ... ok
test_asset_tamper_detected (test_builders_release.LilDrByrdBuilder.test_asset_tamper_detected) ... ok
test_missing_mascot_blocks_artwork_only (test_builders_release.LilDrByrdBuilder.test_missing_mascot_blocks_artwork_only) ... ok
test_only_owner_registers_assets (test_builders_release.LilDrByrdBuilder.test_only_owner_registers_assets) ... ok
test_registered_mascot_used_byte_identical (test_builders_release.LilDrByrdBuilder.test_registered_mascot_used_byte_identical) ... ok
test_wrong_physics_answer_blocks_chapter (test_builders_release.LilDrByrdBuilder.test_wrong_physics_answer_blocks_chapter) ... ok
test_ai_drafted_content_requires_owner_review (test_builders_release.PowerToolBuilder.test_ai_drafted_content_requires_owner_review) ... ok
test_blueprint_validation (test_builders_release.PowerToolBuilder.test_blueprint_validation) ... ok
test_built_module_works_in_browser_and_scores (test_builders_release.PowerToolBuilder.test_built_module_works_in_browser_and_scores) ... ok
test_html_escaping_of_blueprint_content (test_builders_release.PowerToolBuilder.test_html_escaping_of_blueprint_content) ... ok
test_module_order_and_approval (test_builders_release.PowerToolBuilder.test_module_order_and_approval) ... ok
test_provisional_template_blocks_release_and_approved_template_passes (test_builders_release.PowerToolBuilder.test_provisional_template_blocks_release_and_approved_template_passes) ... ok
test_wrong_answer_blocks_module (test_builders_release.PowerToolBuilder.test_wrong_answer_blocks_module) ... ok
test_ai_suggestion_applied_then_independently_verified (test_costs_ai.AIInLoop.test_ai_suggestion_applied_then_independently_verified) ... ok
test_api_error_handled (test_costs_ai.AIInLoop.test_api_error_handled) ... ok
test_bad_ai_suggestion_cannot_pass_qa (test_costs_ai.AIInLoop.test_bad_ai_suggestion_cannot_pass_qa) ... ok
test_budget_stop_inside_loop (test_costs_ai.AIInLoop.test_budget_stop_inside_loop) ... ok
test_declined_spend_stops_without_call (test_costs_ai.AIInLoop.test_declined_spend_stops_without_call) ... ok
test_patch_json_parsing_rejects_garbage (test_costs_ai.AIRoles.test_patch_json_parsing_rejects_garbage) ... ok
test_review_requires_key_or_client (test_costs_ai.AIRoles.test_review_requires_key_or_client) ... ok
test_review_through_guard (test_costs_ai.AIRoles.test_review_through_guard) ... ok
test_api_failure_conservatively_charged_and_raised (test_costs_ai.Guard.test_api_failure_conservatively_charged_and_raised) ... ok
test_daily_cap_accumulates (test_costs_ai.Guard.test_daily_cap_accumulates) ... ok
test_estimate_is_conservative (test_costs_ai.Guard.test_estimate_is_conservative) ... ok
test_owner_must_approve_each_call (test_costs_ai.Guard.test_owner_must_approve_each_call) ... ok
test_per_job_cap (test_costs_ai.Guard.test_per_job_cap) ... ok
test_reserve_never_spent (test_costs_ai.Guard.test_reserve_never_spent) ... ok
test_settings_validation (test_costs_ai.Guard.test_settings_validation) ... ok
test_summary_never_claims_verified_balance (test_costs_ai.Guard.test_summary_never_claims_verified_balance) ... ok
test_unfunded_means_no_call (test_costs_ai.Guard.test_unfunded_means_no_call) ... ok
test_unknown_model_price_refused (test_costs_ai.Guard.test_unknown_model_price_refused) ... ok
test_usage_recorded_from_response (test_costs_ai.Guard.test_usage_recorded_from_response) ... ok
test_budget_stops (test_engine.Tests.test_budget_stops) ... ok
test_import_hash_and_audit (test_engine.Tests.test_import_hash_and_audit) ... ok
test_proposal_preserves_original (test_engine.Tests.test_proposal_preserves_original) ... ok
test_zip_traversal_blocked (test_engine.Tests.test_zip_traversal_blocked) ... ok
test_broken_fails_before_and_passes_after_with_browser_evidence (test_repair_loop.EndToEndPowerTool.test_broken_fails_before_and_passes_after_with_browser_evidence) ... ok
test_candidate_tamper_after_qa_blocks_approval (test_repair_loop.EndToEndPowerTool.test_candidate_tamper_after_qa_blocks_approval) ... ok
test_unfixable_runtime_error_blocks_release (test_repair_loop.EndToEndPowerTool.test_unfixable_runtime_error_blocks_release) ... ok
test_iteration_limit (test_repair_loop.LoopControls.test_iteration_limit) ... ok
test_missing_browser_means_not_verified (test_repair_loop.LoopControls.test_missing_browser_means_not_verified) ... ok
test_no_progress_detection (test_repair_loop.LoopControls.test_no_progress_detection) ... ok
test_qa_detects_unrecorded_change (test_repair_loop.LoopControls.test_qa_detects_unrecorded_change)
Release QA is independent: a silent edit to the candidate is caught. ... ok
test_regression_triggers_rollback_and_escalation (test_repair_loop.LoopControls.test_regression_triggers_rollback_and_escalation) ... ok
test_runtime_limit (test_repair_loop.LoopControls.test_runtime_limit) ... ok
test_flattened_page_correction_refused (test_repair_loop.PdfLoop.test_flattened_page_correction_refused) ... ok
test_image_only_pdf_is_not_verified_and_never_rewritten (test_repair_loop.PdfLoop.test_image_only_pdf_is_not_verified_and_never_rewritten) ... ok
test_wrong_claim_repaired_with_visual_evidence (test_repair_loop.PdfLoop.test_wrong_claim_repaired_with_visual_evidence) ... ok
test_minor_failure_below_target (test_repair_loop.Scoring.test_minor_failure_below_target) ... ok
test_missing_coverage_is_not_verified (test_repair_loop.Scoring.test_missing_coverage_is_not_verified) ... ok
test_reproducible (test_repair_loop.Scoring.test_reproducible) ... ok
test_unverified_academic_items (test_repair_loop.Scoring.test_unverified_academic_items) ... ok
test_weighted_average_never_hides_critical (test_repair_loop.Scoring.test_weighted_average_never_hides_critical) ... ok
test_binary_in_text_file (test_security.InvalidUploads.test_binary_in_text_file) ... ok
test_corrupted_manifest_does_not_crash_inventory (test_security.InvalidUploads.test_corrupted_manifest_does_not_crash_inventory) ... ok
test_empty_file (test_security.InvalidUploads.test_empty_file) ... ok
test_invalid_product_id (test_security.InvalidUploads.test_invalid_product_id) ... ok
test_mislabeled_pdf (test_security.InvalidUploads.test_mislabeled_pdf) ... ok
test_unsupported_extension (test_security.InvalidUploads.test_unsupported_extension) ... ok
test_original_locked_and_fingerprinted (test_security.Preservation.test_original_locked_and_fingerprinted) ... ok
test_patch_rules (test_security.Preservation.test_patch_rules) ... ok
test_repack_is_valid_and_deterministic (test_security.Preservation.test_repack_is_valid_and_deterministic) ... ok
test_tampered_original_detected (test_security.Preservation.test_tampered_original_detected) ... ok
test_working_copy_isolated_and_rollback (test_security.Preservation.test_working_copy_isolated_and_rollback) ... ok
test_job_log_never_contains_key (test_security.Secrets.test_job_log_never_contains_key) ... ok
test_no_hardcoded_keys_in_source (test_security.Secrets.test_no_hardcoded_keys_in_source) ... ok
test_redaction (test_security.Secrets.test_redaction) ... ok
test_absolute_path (test_security.ZipSecurity.test_absolute_path) ... ok
test_archive_bomb_ratio (test_security.ZipSecurity.test_archive_bomb_ratio) ... ok
test_backslash_windows_traversal (test_security.ZipSecurity.test_backslash_windows_traversal) ... ok
test_corrupted_zip (test_security.ZipSecurity.test_corrupted_zip) ... ok
test_declared_size_lie_is_capped_while_streaming (test_security.ZipSecurity.test_declared_size_lie_is_capped_while_streaming) ... ok
test_drive_letter (test_security.ZipSecurity.test_drive_letter) ... ok
test_duplicate_entries (test_security.ZipSecurity.test_duplicate_entries) ... ok
test_nested_traversal (test_security.ZipSecurity.test_nested_traversal) ... ok
test_parent_traversal (test_security.ZipSecurity.test_parent_traversal) ... ok
test_reserved_device_name (test_security.ZipSecurity.test_reserved_device_name) ... ok
test_safe_relpath (test_security.ZipSecurity.test_safe_relpath) ... ok
test_symlink (test_security.ZipSecurity.test_symlink) ... ok
test_too_many_entries (test_security.ZipSecurity.test_too_many_entries) ... ok
test_truncated_zip (test_security.ZipSecurity.test_truncated_zip) ... ok
test_app_end_to_end (test_ui_smoke.UISmoke.test_app_end_to_end) ... ok

----------------------------------------------------------------------
Ran 96 tests in 49.488s

OK

real	0m50.044s
user	0m28.529s
sys	0m9.837s
```
