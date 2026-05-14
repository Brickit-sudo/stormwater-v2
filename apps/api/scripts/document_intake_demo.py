from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Sequence
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.db import get_session_factory  # noqa: E402
from app.models import DocumentRecord, DocumentTextChunk, Organization  # noqa: E402


DEMO_TEXT = (
    "Demo document intake only. This fake stormwater snippet represents a report summary "
    "that has been staged for human review before any fields become CRM truth."
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safe demo skeleton for document intake records and text chunks.",
    )
    parser.add_argument(
        "--organization-id",
        type=uuid.UUID,
        help="Organization to receive demo records. Required with --create-demo-record.",
    )
    parser.add_argument(
        "--create-demo-record",
        action="store_true",
        help="Create one fake document record and one fake text chunk. No files are read.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        help="Explicit file path to test extractor availability. No recursive folder scans.",
    )
    return parser.parse_args(argv)


def _create_demo_record(organization_id: uuid.UUID) -> None:
    session_factory = get_session_factory()
    with session_factory() as session:
        organization = session.get(Organization, organization_id)
        if organization is None:
            raise SystemExit(f"Organization not found: {organization_id}")
        document = DocumentRecord(
            organization_id=organization_id,
            source="demo_cli",
            file_name="CLI Demo Inspection Summary.md",
            document_type="report",
            status="queued",
            extraction_status="complete",
        )
        session.add(document)
        session.flush()
        session.add(
            DocumentTextChunk(
                organization_id=organization_id,
                document_id=document.id,
                chunk_index=0,
                heading="Demo Summary",
                text=DEMO_TEXT,
                token_count=len(DEMO_TEXT.split()),
            ),
        )
        session.commit()
        print(f"Created demo document_id={document.id}")


def _check_explicit_path(path: Path) -> None:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise SystemExit(f"Path does not exist: {resolved}")
    if resolved.is_dir():
        raise SystemExit("Directory scans are intentionally not supported by this skeleton.")

    try:
        import markitdown  # noqa: F401
    except ImportError:
        print(
            "MarkItDown is not installed. Install it in the API environment only when you are "
            "ready to run an explicit extractor pilot, for example: python -m pip install markitdown"
        )
        return

    print(
        "MarkItDown is installed, but this skeleton does not parse files yet. "
        f"Ready for a later explicit pilot against: {resolved}"
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.create_demo_record:
        if args.organization_id is None:
            raise SystemExit("--organization-id is required with --create-demo-record.")
        _create_demo_record(args.organization_id)
    elif args.path is not None:
        _check_explicit_path(args.path)
    else:
        print(
            "No action taken. Use --create-demo-record with --organization-id for fake data, "
            "or --path for an explicit extractor availability check."
        )


if __name__ == "__main__":
    main()
