from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import (
    ArchivedMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


IMPORT_ROW_STATUSES = {
    "valid",
    "invalid",
    "duplicate",
    "unmatched",
    "committed",
    "skipped",
}


class ExternalRecordId(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "external_record_ids"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "source_system",
            "source_table",
            "source_id",
            name="uq_external_record_ids_organization_source_record",
        ),
        Index(
            "ix_external_record_ids_organization_id_entity",
            "organization_id",
            "entity_type",
            "entity_id",
        ),
    )

    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    source_table: Mapped[str] = mapped_column(String(128), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    legacy_label: Mapped[str | None] = mapped_column(String(255))

    organization: Mapped["Organization"] = relationship(back_populates="external_record_ids")


class ClientAlias(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "client_aliases"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "alias_value",
            "alias_type",
            name="uq_client_aliases_organization_alias_type",
        ),
        Index("ix_client_aliases_organization_id_client_id", "organization_id", "client_id"),
        Index("ix_client_aliases_organization_id_source_system", "organization_id", "source_system"),
    )

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clients.id"),
    )
    alias_value: Mapped[str] = mapped_column(String(255), nullable=False)
    alias_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_system: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    organization: Mapped["Organization"] = relationship(back_populates="client_aliases")
    client: Mapped["Client | None"] = relationship(back_populates="aliases")


class SiteAlias(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "site_aliases"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "alias_value",
            "alias_type",
            name="uq_site_aliases_organization_alias_type",
        ),
        Index("ix_site_aliases_organization_id_site_id", "organization_id", "site_id"),
        Index("ix_site_aliases_organization_id_client_id", "organization_id", "client_id"),
        Index("ix_site_aliases_organization_id_source_system", "organization_id", "source_system"),
    )

    site_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sites.id"),
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clients.id"),
    )
    alias_value: Mapped[str] = mapped_column(String(255), nullable=False)
    alias_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_system: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    organization: Mapped["Organization"] = relationship(back_populates="site_aliases")
    site: Mapped["Site | None"] = relationship(back_populates="aliases")
    client: Mapped["Client | None"] = relationship(back_populates="site_aliases")


class ServiceCatalog(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "service_catalog"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "service_code",
            name="uq_service_catalog_organization_service_code",
        ),
        Index("ix_service_catalog_organization_id_category", "organization_id", "category"),
        Index("ix_service_catalog_organization_id_is_active", "organization_id", "is_active"),
    )

    service_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    default_frequency: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    organization: Mapped["Organization"] = relationship(back_populates="service_catalog")


class FileCategory(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "file_categories"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "code",
            name="uq_file_categories_organization_code",
        ),
        Index("ix_file_categories_organization_id_is_active", "organization_id", "is_active"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    allowed_parent_types_json: Mapped[list[str] | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    organization: Mapped["Organization"] = relationship(back_populates="file_categories")


class ImportBatch(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "import_batches"
    __table_args__ = (
        Index("ix_import_batches_organization_id_created_at", "organization_id", "created_at"),
        Index("ix_import_batches_organization_id_import_type", "organization_id", "import_type"),
        Index("ix_import_batches_organization_id_status", "organization_id", "status"),
    )

    import_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="dry_run")
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unmatched_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization: Mapped["Organization"] = relationship(back_populates="import_batches")
    import_rows: Mapped[list["ImportRow"]] = relationship(
        back_populates="import_batch",
        cascade="all, delete-orphan",
    )


class ImportRow(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "import_rows"
    __table_args__ = (
        Index("ix_import_rows_organization_id_import_batch_id", "organization_id", "import_batch_id"),
        Index("ix_import_rows_organization_id_status", "organization_id", "status"),
        Index("ix_import_rows_organization_id_duplicate_key", "organization_id", "duplicate_key"),
        Index(
            "ix_import_rows_organization_id_matched_entity",
            "organization_id",
            "matched_entity_type",
            "matched_entity_id",
        ),
    )

    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("import_batches.id"),
        nullable=False,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    import_type: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    normalized_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    validation_errors_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    duplicate_key: Mapped[str | None] = mapped_column(String(255))
    matched_entity_type: Mapped[str | None] = mapped_column(String(64))
    matched_entity_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))

    organization: Mapped["Organization"] = relationship()
    import_batch: Mapped["ImportBatch"] = relationship(back_populates="import_rows")
