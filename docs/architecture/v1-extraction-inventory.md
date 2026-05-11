# V1 Extraction Inventory

## Summary

The first extraction should be the already-pure report assembly layer in `backend/app/services/report_engine`. It accepts plain dictionaries, emits typed render models, and has no Streamlit, SQLite, page, or widget dependencies. That gives V2 the right architecture immediately: CRM/job snapshots become normalized report/photosheet documents before any DOCX renderer runs.

Next, extract the domain constants and photo caption/order helpers so every output shares one stormwater vocabulary. Image preparation can follow because DOCX generation depends on it, but upload/project-path behavior should be rewritten around V2 storage instead of copied. The DOCX builders are valuable, but they should move only after their V1 app/session and asset-path assumptions are replaced with explicit inputs.

## Safe to Extract Now

| Source File | Function/Class/Area | Purpose | Dependencies | Why Safe | Target V2 Location |
|---|---|---|---|---|---|
| `backend/app/services/report_engine/schemas.py` | `ReportType`, `ConditionRating`, `ReportStatus`, `NormalizedMeta`, `NormalizedSystem`, `NormalizedWriteUp`, `NormalizedPhoto`, `NormalizedPhotosheetPhoto`, `BmpSummaryLine`, `SystemWriteUpBlock`, `PhotoBatch`, `ReportDocument`, `PhotosheetDocument` | Typed render/snapshot models for reports and photosheets | `enum`, `typing`, `pydantic` | No Streamlit, DB, filesystem, or V1 session imports | `python/stormwater_core/stormwater_core/reports/render_models.py` |
| `backend/app/services/report_engine/normalize.py` | `_str`, `_int`, `_bool`, `_enum`, `normalize_meta`, `normalize_system`, `normalize_write_up`, `normalize_photo`, `normalize_photosheet_photo`, `normalize_session` | Coerce raw dict/session snapshots into typed report models | Local pure schemas only | Designed to accept plain dicts across an API boundary | `python/stormwater_core/stormwater_core/reports/render_models.py` |
| `backend/app/services/report_engine/captions.py` | `build_caption`, `build_full_report_caption`, `build_photosheet_caption`, `build_bmp_summary_lines` | Unified caption strings and BMP summary lines | Local pure schemas, `collections` | No side effects; duplicated logic already isolated from Streamlit | `python/stormwater_core/stormwater_core/photos/captions.py` and `reports/templates.py` |
| `backend/app/services/report_engine/ordering.py` | Flow category constants, `_get_flow_priority`, `sort_photos_for_report`, `renumber_photos`, `sort_photosheet_photos`, `renumber_photosheet_photos`, `batch_photos`, `batch_photos_for_grid` | Stormwater flow ordering, photo renumbering, grid batching | Local pure schemas | Pure and covered by existing ordering tests | `python/stormwater_core/stormwater_core/photos/ordering.py` |
| `backend/app/services/report_engine/writeups.py` | `is_inspection`, `is_maintenance`, `is_combined`, `build_subheading`, `build_findings_opener`, `build_write_up_blocks` | Report-type branching and write-up block assembly | Local pure schemas | No renderer or UI dependencies | `python/stormwater_core/stormwater_core/reports/templates.py` |
| `backend/app/services/report_engine/assemble.py` | `assemble_report`, `assemble_photosheet` | Top-level snapshot-to-render-document orchestration | Local pure report engine modules | This is the cleanest V2 snapshot pipeline already present | `python/stormwater_core/stormwater_core/reports/full_report.py` and `reports/photosheet.py` |
| `stormwater_app/app/constants.py` | `SYSTEM_TYPES`, `SYSTEM_ID_PREFIX`, `COMPONENT_OPTIONS`, `get_components_for_system`, `CONDITION_RATINGS`, `REPORT_TYPES`, write-up template functions, flow/category/photo constants, `get_flow_priority`, `PS_LAYOUTS` | Canonical stormwater vocabulary, captions, ordering, layout config, default wording | None | Pure module; extract domain/report/photo subsets and leave V1 nav constants behind | `python/stormwater_core/stormwater_core/domain/enums.py`, `photos/ordering.py`, `reports/templates.py` |
| `stormwater_app/app/services/captions.py` | `build_caption` plus internal report/photosheet builders | Duck-typed caption builder used by V1 objects | None | No `app.session` import; safe, but backend `report_engine/captions.py` should be canonical to avoid duplication | `python/stormwater_core/stormwater_core/photos/captions.py` |
| `stormwater_app/app/services/smart_captions.py` | `STARTER_SYSTEM_TYPES`, `STARTER_COMPONENTS`, `build_smart_caption`, `is_numbered_caption` | Deterministic caption suggestions and numbered-caption detection | None | Pure helper logic with no UI or storage dependencies | `python/stormwater_core/stormwater_core/photos/captions.py` |
| `stormwater_app/app/services/photo_service.py` | `_sanitize_filename`, `_apply_exif_orientation`, `_copy_without_metadata`, `_resize_if_needed`, `_save_clean_jpeg`, `_save_clean_png`, `_to_jpeg_bytes`, `_unique_dest`, `save_sanitized_image`, `correct_orientation_bytes`, `read_exif_date`, `generate_thumbnail`, `prepare_docx_image`, `compress_for_docx`, `resize_for_report` | Orientation correction, metadata stripping, thumbnailing, DOCX compression | `PIL`, stdlib; module also imports `safe_project_path` | Image functions are pure/file-scoped and reusable; skip `save_uploaded_photo` until V2 storage is designed | `python/stormwater_core/stormwater_core/photos/image_prep.py` and `photos/compression.py` |
| `stormwater_app/app/services/photo_preview_cache.py` | `PreviewResult`, cache-key helpers, preview generation helpers, `get_image_dimensions` | Disk-backed preview JPEG cache | `PIL`, stdlib | No Streamlit or session imports; useful for future photo workflow if cache root is configurable | `python/stormwater_core/stormwater_core/photos/image_prep.py` |
| `stormwater_app/app/services/crm_insights.py` | `parse_crm_date`, `build_crm_command_center`, queue/action helper functions | Rule-based CRM command center, duplicate-ish operational signals, readiness queues | `dateutil`, stdlib | Core builder is pure; exclude `load_crm_command_center` because it imports V1 DB services | `python/stormwater_core/stormwater_core/crm/smart_helpers.py` |
| `stormwater_app/app/services/crm_helpers.py` | `get_linked_crm_status`, picker option builders, CRM-to-report meta mappers | CRM linkage display and report metadata bridging | `typing` only | Pure, but V2 should convert mutating mappers into return-value transforms | `python/stormwater_core/stormwater_core/crm/smart_helpers.py` |
| `stormwater_app/app/services/imports/drive_matching.py` | `normalize_site_name_for_matching`, `score_possible_matches`, `match_drive_file_to_site`, `match_drive_folder_to_site`, `match_report_file_to_report_history` | Drive/report/site fuzzy matching | `re`, `difflib`, stdlib | Pure and already tested as no-API matching logic | `python/stormwater_core/stormwater_core/drive/naming.py` or `crm/smart_helpers.py` |
| `stormwater_app/app/services/imports/normalization.py` | Column/cell/date/currency/status normalizers and alias maps | Spreadsheet/import cleanup helpers | `dateutil`, stdlib | Pure import normalization; useful for V1 data migration and future CSV imports | `python/stormwater_core/stormwater_core/crm/smart_helpers.py` |
| `stormwater_app/app/services/maintenance_flags.py` | `evaluate_flags`, `system_label`, `build_client_summary`, summary constants | Rule-based maintenance triggers and client-facing summary text | None | Pure and report-domain specific | `python/stormwater_core/stormwater_core/reports/templates.py` |
| `stormwater_app/app/services/report_package.py` | `PackageMeta`, `PackageSystem`, `PackageWriteUp`, `PackagePhoto`, options, `ReportPackage`, package builders | Streamlit-free package model bridging project/photosheet state | `pydantic`, stdlib | Does not import Streamlit, files, or exporters; good precursor to immutable snapshot model | `python/stormwater_core/stormwater_core/reports/render_models.py` |
| `stormwater_app/app/services/workflow_status.py` | `WorkflowAction`, `setup_missing`, `photo_status`, `required_writeup_fields`, `writeup_status`, `build_report_workflow_dashboard`, `build_quick_actions` | Report readiness checklist and explicit action model | stdlib only | Pure; valuable as V2 report readiness logic after ps_* names are generalized | `python/stormwater_core/stormwater_core/crm/smart_helpers.py` |
| `stormwater_app/app/services/drive_artifact_service.py` | `parse_drive_folder_id` | Parse raw Drive IDs and folder URLs | `re` | Pure parser with tests; do not move upload function yet | `python/stormwater_core/stormwater_core/drive/naming.py` |
| `stormwater_app/app/utils/file_utils.py` | `sanitize_filename`, `ensure_dir`, `get_output_path` | Safe filename/output path helpers | stdlib | Pure helpers; leave `list_project_files` behind until V2 storage paths exist | `python/stormwater_core/stormwater_core/drive/naming.py` |
| `stormwater_app/app/services/project_paths.py` | `validate_project_id`, `new_project_id`, `recover_project_id` | Safe project/slug validation | stdlib plus `app.paths` for `safe_project_path` | Validation helpers are pure; move `safe_project_path` later with an injected root path | `python/stormwater_core/stormwater_core/domain/models.py` or `drive/naming.py` |
| `stormwater_app/app/services/page_fit.py` | `PageLayout`, `ContentBlock`, `PageFitResult`, estimation helpers, `estimate_cover_blocks`, `apply_page_fit` | Cover-page fit/compression algorithm | stdlib; optional `PIL`; hardcoded V1 logo path | Algorithm is pure and valuable; extract with logo path/config injection | `python/stormwater_core/stormwater_core/reports/full_report.py` or `reports/page_fit.py` |

## Extract Later

| Source File | Area | Why Later | What Must Change First |
|---|---|---|---|
| `stormwater_app/app/services/photosheet_builder.py` | `render_photosheet`, `build_photosheet`, Word header/footer/table helpers | Valuable DOCX renderer, but imports V1 `prepare_docx_image` and hardcodes V1 logo/assets/cache assumptions | Extract image prep first; pass asset paths, cache dir, and output path explicitly |
| `stormwater_app/app/services/report_builder.py` | `render_report`, DOCX cover/photo/footer helpers, `STYLE_CONFIG`, report boilerplate | Contains the real Sterling DOCX layout, but imports Streamlit, V1 `ProjectSession`, V1 photo service, V1 page-fit, and dynamic backend module bridge | Remove `st.cache_resource`, use `stormwater_core` render models directly, inject asset/output/cache paths |
| `stormwater_app/app/services/template_report_builder.py` | Template/report context, python-docx body renderer, helper XML functions | Cleaner context shape but still imports V1 caption/photo/report-package services | Move report package, captions, and image prep first; then choose whether this renderer replaces or supplements `report_builder.py` |
| `stormwater_app/app/services/export_context.py` | Adapters from `ReportPackage` to V1 dataclasses/builders | Pure behavior, but imports `app.session` dataclasses from a Streamlit module | Move models to `stormwater_core` first, then rewrite adapters around V2 snapshots |
| `stormwater_app/app/services/photo_adapters.py` | Photosheet/full-report photo conversion | Pure intent, but imports `Photo` and `PhotosheetPhoto` from Streamlit-bound `app.session` | Move/redefine domain photo models first |
| `stormwater_app/app/services/caption_workflow_state.py` | Caption studio draft/index state helpers | Pure but strongly tied to V1 `ps_*` session keys and Streamlit screen behavior | Decide whether V2 keeps caption draft logic in frontend TypeScript or backend snapshot validation |
| `stormwater_app/app/services/export_orchestrator.py` | Export requests/results and artifact orchestration | Good boundary, but imports V1 renderers/PDF renderer/export context | Extract renderers and package models first; replace filesystem output assumptions with V2 artifact service |
| `stormwater_app/app/services/post_export_hooks.py` | Artifact validation, CRM sync, follow-up creation | Some models are pure, but CRM sync imports V1 CRM services and writes SQLite | Split side-effect-free diagnostics from DB-writing hooks; implement V2 service layer first |
| `stormwater_app/app/services/google_service.py` | Drive upload/list behavior | Uses Streamlit cache/session user, SQLite config, service-account assumptions | Rebuild as FastAPI Drive service with explicit auth/config, pagination, and record-scoped folder queries |
| `stormwater_app/app/services/drive_artifact_service.py` | `upload_report_artifact_to_drive` | Tightly coupled to V1 SQLite artifact rows and V1 Google service | Keep parser now; rebuild upload around V2 `evidence_files`/`report_artifacts` |
| `stormwater_app/app/services/crm_db.py` | SQLite CRM persistence and report artifact history | Important migration reference but not final source of truth | Use only for migration mapping; implement V2 SQLAlchemy/Postgres instead |
| `stormwater_app/app/services/crm_service.py` | Service wrappers over V1 CRM DB/API | Mixed local/backend compatibility layer | Replace with V2 FastAPI service layer and Postgres models |
| `backend/app/models/*`, `backend/app/schemas/*`, `backend/app/api/*` | Existing backend CRUD POC | Useful field/reference material, but V2 schema should be redesigned around organizations/clients/sites/jobs | Start fresh V2 SQLAlchemy/Alembic models after this inventory |
| `backend/app/services/importer.py`, `backend/app/services/analyzer.py` | Historical report import/extraction | Potentially useful later, not MVP extraction | Stabilize core CRM/report/photo pipeline first |

## Do Not Extract

| Source File | Area | Reason |
|---|---|---|
| `stormwater_app/app.py` | Streamlit router and mode/page dispatch | V2 should use Next/FastAPI routing, not Streamlit rerun routing |
| `stormwater_app/app/pages/*` | Streamlit pages | UI/widget code, session mutation, page navigation, and report-first workflow should stay in V1 |
| `stormwater_app/app/components/sidebar.py` | Sidebar/navigation | Streamlit-specific and explicitly not part of the V2 product direction |
| `stormwater_app/app/components/topbar.py` | Streamlit topbar/workflow chrome | UI chrome and V1 navigation model |
| `stormwater_app/app/components/styles.py` | CSS injection | Streamlit styling, not V2 Tailwind/shadcn design system |
| `stormwater_app/app/components/ui_helpers.py` | Streamlit UI helpers | Imports Streamlit and mutates V1 page state |
| `stormwater_app/app/session.py` | `init_session`, `get_project`, draft save/load, `ps_sync_widget_states` | Central `st.session_state` workflow; only the data model shapes should inform V2 models |
| `stormwater_app/app/services/api_client.py` | V1 frontend HTTP client | Streamlit-facing compatibility client; V2 web app needs generated/fetch/React Query clients |
| `stormwater_app/app/services/auth.py`, `stormwater_app/app/services/auth_mode.py` | V1 local auth/session role helpers | Streamlit/session and SQLite-bound auth path |
| `stormwater_app/app/services/db.py` | Local SQLite connection/config | V2 persistence should be Postgres through FastAPI |
| `stormwater_app/app/services/role_kpis.py`, `dispatch_service.py`, `followup_service.py`, `job_completion_service.py` | SQLite-driven operational queries | Keep business ideas, but not V1 query implementation |
| `stormwater_app/app/services/sheets_sync.py` | Background Google Sheets sync | V1-specific sync path; not part of CRM-first MVP |
| `stormwater_app/frontend/*` | Old embedded frontend assets | Superseded by `stormwater-v2/apps/web` |

## V1 Logic Worth Keeping

- Report generation: Sterling DOCX layout, cover-page XML rearrangement approach, page-fit algorithm, photo grid sizing, footer/header styling, certification language, and report-type branching.
- Photosheet generation: native Word header/footer architecture, continuous body table, layout presets, caption fitting/truncation, notes page handling, and no-manual-page-break pagination.
- Image compression/prep: EXIF orientation correction, metadata stripping, HEIC handling, thumbnail generation, DOCX JPEG cache keys, max-dimension resizing, and progressive JPEG output.
- Caption/order logic: unified caption builder, photosheet component captions, flow-of-water ordering, view priority, renumbering, grid batching, smart caption suggestions, and BMP summary lines.
- CRM smart helpers: command-center queues, date parsing, missing-field/readiness checks, duplicate/matching helpers, and explicit CRM linkage status.
- Drive naming/folder conventions: Drive folder ID parsing, record folder fields, private-by-default artifact upload behavior, targeted folder listing rule, and Drive/site/report fuzzy matching.
- Stormwater report wording/templates: system/component vocabulary, default findings/recommendations/maintenance/post-service language, maintenance trigger flags, client-summary language, introduction/certification/report-title boilerplate.

## V1 Logic to Leave Behind

- Streamlit UI pages.
- `session_state` workflows and `ps_*` state as a long-term data model.
- SQLite-only final CRM path.
- Fake/old page navigation and compatibility routing.
- Report-first page structure.
- UI code mixed with database code.
- Drive scans during page render.
- Mutable live UI state as the report generation source.

## Recommended Extraction Order

1. `crm_smart_helpers`
2. `photo caption/order helpers`
3. `image prep/compression helpers`
4. `photosheet render model`
5. `report render model`
6. `DOCX generation helpers`
7. `Drive naming helpers`

