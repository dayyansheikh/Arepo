"""Canonical v2 model columns, isolated from v1 migration metadata.

Column declarations follow docs/architecture/FEATURE_STORE_V2_FIELDS.csv; a regression
checks parity. Admission semantics live in repository.py, never in a production hook.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Column,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase

from .types import ExactDecimal, UnsignedIntegerText, UTCDateTime


class FeatureStoreBase(DeclarativeBase):
    pass


class ArchiveManifestRow(FeatureStoreBase):
    __tablename__ = "fs2_archive_manifest"
    artifact_manifest_id = Column(
        String(64),
        ForeignKey(
            "fs2_artifact_manifest.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    byte_count = Column(BigInteger, nullable=False)
    file_hashes = Column(JSON(none_as_null=True), nullable=False)
    format_version = Column(Text, nullable=False)
    id = Column(String(64), primary_key=True)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    partition_bounds = Column(JSON(none_as_null=True), nullable=False)
    preservation_report_id = Column(
        String(64),
        ForeignKey(
            "fs2_artifact_manifest.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
        index=True,
    )
    provenance_class = Column(String, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    restore_report_id = Column(
        String(64),
        ForeignKey(
            "fs2_artifact_manifest.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
        index=True,
    )
    row_count = Column(BigInteger, nullable=False)
    schema_hash = Column(String(64), nullable=False)
    schema_version = Column(Text, nullable=False)
    source_manifest_id = Column(
        String(64),
        ForeignKey(
            "fs2_artifact_manifest.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    supersedes_id = Column(
        String(64),
        ForeignKey(
            "fs2_archive_manifest.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
        index=True,
    )
    verification_state = Column(String, nullable=False)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_archive_manifest_provenance",
        ),
        CheckConstraint(
            "artifact_manifest_id IS NULL OR length(artifact_manifest_id) = 64",
            name="ck_fs2_archive_manifest_artifact_man",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_archive_manifest_id"),
        CheckConstraint(
            "preservation_report_id IS NULL OR length(preservation_report_id) = 64",
            name="ck_fs2_archive_manifest_preservation",
        ),
        CheckConstraint(
            "restore_report_id IS NULL OR length(restore_report_id) = 64",
            name="ck_fs2_archive_manifest_restore_repo",
        ),
        CheckConstraint(
            "schema_hash IS NULL OR length(schema_hash) = 64",
            name="ck_fs2_archive_manifest_schema_hash",
        ),
        CheckConstraint(
            "source_manifest_id IS NULL OR length(source_manifest_id) = 64",
            name="ck_fs2_archive_manifest_source_manif",
        ),
        CheckConstraint(
            "supersedes_id IS NULL OR length(supersedes_id) = 64",
            name="ck_fs2_archive_manifest_supersedes_i",
        ),
    )


class ArtifactManifestRow(FeatureStoreBase):
    __tablename__ = "fs2_artifact_manifest"
    available_at = Column(UTCDateTime(), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False)
    id = Column(String(64), primary_key=True)
    manifest_kind = Column(String, nullable=False)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    object_hash = Column(String(64), nullable=True)
    object_uri = Column(Text, nullable=True)
    payload = Column(JSON(none_as_null=True), nullable=False)
    provenance_class = Column(String, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    schema_version = Column(Text, nullable=False)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_artifact_manifest_provenance",
        ),
        CheckConstraint(
            "content_hash IS NULL OR length(content_hash) = 64",
            name="ck_fs2_artifact_manifest_content_hash",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_artifact_manifest_id"),
        CheckConstraint(
            "object_hash IS NULL OR length(object_hash) = 64",
            name="ck_fs2_artifact_manifest_object_hash",
        ),
    )


class BookLevelRow(FeatureStoreBase):
    __tablename__ = "fs2_book_level"
    id = Column(String(64), primary_key=True)
    level = Column(BigInteger, nullable=False)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    price_decimal = Column(ExactDecimal(), nullable=True)
    price_raw = Column(Text, nullable=False)
    provenance_class = Column(String, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    schema_version = Column(Text, nullable=False)
    side = Column(String, nullable=False)
    size_decimal = Column(ExactDecimal(), nullable=True)
    size_raw = Column(Text, nullable=False)
    snapshot_id = Column(
        Text,
        ForeignKey(
            "fs2_book_snapshot.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    source_observation_id = Column(
        String(64),
        ForeignKey(
            "fs2_source_observation.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    unit = Column(Text, nullable=False)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_book_level_provenance",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_book_level_id"),
        CheckConstraint(
            "source_observation_id IS NULL OR length(source_observation_id) = 64",
            name="ck_fs2_book_level_source_obser",
        ),
    )


class BookSnapshotRow(FeatureStoreBase):
    __tablename__ = "fs2_book_snapshot"
    ask_level_count = Column(BigInteger, nullable=False)
    ask_state = Column(String, nullable=False)
    available_to_model_at = Column(UTCDateTime(), nullable=False, index=True)
    bid_level_count = Column(BigInteger, nullable=False)
    bid_state = Column(String, nullable=False)
    book_hash = Column(Text, nullable=True)
    delta_observation_ids = Column(JSON(none_as_null=True), nullable=False)
    id = Column(String(64), primary_key=True)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    previous_snapshot_id = Column(
        String(64),
        ForeignKey(
            "fs2_book_snapshot.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
        index=True,
    )
    provenance_class = Column(String, nullable=False)
    quote_age_ms = Column(ExactDecimal(), nullable=True)
    quote_age_semantics = Column(String, nullable=False)
    reconstruction_status = Column(String, nullable=False)
    reconstruction_version = Column(Text, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    schema_version = Column(Text, nullable=False)
    sequence_end = Column(Text, nullable=True)
    sequence_start = Column(Text, nullable=True)
    snapshot_kind = Column(String, nullable=False)
    source_observation_id = Column(
        String(64),
        ForeignKey(
            "fs2_source_observation.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    token_outcome_id = Column(
        String(64),
        ForeignKey(
            "fs2_token_outcome_version.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        index=True,
    )
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_book_snapshot_provenance",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_book_snapshot_id"),
        CheckConstraint(
            "previous_snapshot_id IS NULL OR length(previous_snapshot_id) = 64",
            name="ck_fs2_book_snapshot_previous_sna",
        ),
        CheckConstraint(
            "source_observation_id IS NULL OR length(source_observation_id) = 64",
            name="ck_fs2_book_snapshot_source_obser",
        ),
        CheckConstraint(
            "token_outcome_id IS NULL OR length(token_outcome_id) = 64",
            name="ck_fs2_book_snapshot_token_outcom",
        ),
    )


class ConditionIdentityRow(FeatureStoreBase):
    __tablename__ = "fs2_condition_identity"
    chain_id = Column(BigInteger, nullable=True)
    collateral_address = Column(String(42), nullable=True)
    collateral_decimals = Column(BigInteger, nullable=True)
    condition_id = Column(String(66), nullable=True)
    id = Column(String(64), primary_key=True)
    identity_status = Column(String, nullable=False)
    mapping_evidence_ids = Column(JSON(none_as_null=True), nullable=False)
    mapping_version = Column(String(64), nullable=False)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    observed_from_at = Column(UTCDateTime(), nullable=False, index=True)
    provenance_class = Column(String, nullable=False)
    question_id = Column(String(66), nullable=True)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    schema_version = Column(Text, nullable=False)
    supersedes_id = Column(
        String(64),
        ForeignKey(
            "fs2_condition_identity.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
        index=True,
    )
    venue = Column(Text, nullable=False)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_condition_identity_provenance",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_condition_identity_id"),
        CheckConstraint(
            "mapping_version IS NULL OR length(mapping_version) = 64",
            name="ck_fs2_condition_identity_mapping_vers",
        ),
        CheckConstraint(
            "supersedes_id IS NULL OR length(supersedes_id) = 64",
            name="ck_fs2_condition_identity_supersedes_i",
        ),
    )


class EventGroupMembershipRow(FeatureStoreBase):
    __tablename__ = "fs2_event_group_membership"
    event_group_id = Column(Text, nullable=True)
    group_version = Column(String(64), nullable=False)
    id = Column(String(64), primary_key=True)
    mapping_confidence = Column(ExactDecimal(), nullable=True)
    mapping_evidence_ids = Column(JSON(none_as_null=True), nullable=False)
    mapping_method = Column(Text, nullable=False)
    mapping_view = Column(String, nullable=False)
    member_identity_id = Column(
        String(64),
        ForeignKey(
            "fs2_market_identity_version.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        index=True,
    )
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    observed_from_at = Column(UTCDateTime(), nullable=False, index=True)
    provenance_class = Column(String, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    relationship_type = Column(String, nullable=False)
    schema_version = Column(Text, nullable=False)
    supersedes_id = Column(
        String(64),
        ForeignKey(
            "fs2_event_group_membership.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
        index=True,
    )
    valid_from_at = Column(UTCDateTime(), nullable=True, index=True)
    valid_to_at = Column(UTCDateTime(), nullable=True, index=True)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_event_group_membership_provenance",
        ),
        CheckConstraint(
            "group_version IS NULL OR length(group_version) = 64",
            name="ck_fs2_event_group_membership_group_versio",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_event_group_membership_id"),
        CheckConstraint(
            "member_identity_id IS NULL OR length(member_identity_id) = 64",
            name="ck_fs2_event_group_membership_member_ident",
        ),
        CheckConstraint(
            "supersedes_id IS NULL OR length(supersedes_id) = 64",
            name="ck_fs2_event_group_membership_supersedes_i",
        ),
    )


class ExperimentRunRow(FeatureStoreBase):
    __tablename__ = "fs2_experiment_run"
    candidate_manifest_id = Column(
        String(64),
        ForeignKey(
            "fs2_artifact_manifest.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    experiment_id = Column(Text, nullable=False)
    id = Column(String(64), primary_key=True)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    protocol_manifest_id = Column(
        String(64),
        ForeignKey(
            "fs2_artifact_manifest.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    protocol_version = Column(String(64), nullable=False)
    provenance_class = Column(String, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    registered_at = Column(UTCDateTime(), nullable=False, index=True)
    result_manifest_id = Column(
        String(64),
        ForeignKey(
            "fs2_artifact_manifest.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
        index=True,
    )
    schema_version = Column(Text, nullable=False)
    split_manifest_id = Column(
        String(64),
        ForeignKey(
            "fs2_artifact_manifest.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    stage = Column(String, nullable=False)
    supersedes_id = Column(
        String(64),
        ForeignKey(
            "fs2_experiment_run.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
        index=True,
    )
    verdict = Column(String, nullable=False)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_experiment_run_provenance",
        ),
        CheckConstraint(
            "candidate_manifest_id IS NULL OR length(candidate_manifest_id) = 64",
            name="ck_fs2_experiment_run_candidate_ma",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_experiment_run_id"),
        CheckConstraint(
            "protocol_manifest_id IS NULL OR length(protocol_manifest_id) = 64",
            name="ck_fs2_experiment_run_protocol_man",
        ),
        CheckConstraint(
            "protocol_version IS NULL OR length(protocol_version) = 64",
            name="ck_fs2_experiment_run_protocol_ver",
        ),
        CheckConstraint(
            "result_manifest_id IS NULL OR length(result_manifest_id) = 64",
            name="ck_fs2_experiment_run_result_manif",
        ),
        CheckConstraint(
            "split_manifest_id IS NULL OR length(split_manifest_id) = 64",
            name="ck_fs2_experiment_run_split_manife",
        ),
        CheckConstraint(
            "supersedes_id IS NULL OR length(supersedes_id) = 64",
            name="ck_fs2_experiment_run_supersedes_i",
        ),
    )


class FeatureDefinitionRow(FeatureStoreBase):
    __tablename__ = "fs2_feature_definition"
    feature_id = Column(Text, nullable=False)
    feature_version = Column(String(64), nullable=False)
    formula = Column(Text, nullable=False)
    id = Column(String(64), primary_key=True)
    minimum_coverage = Column(ExactDecimal(), nullable=True)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    missingness_policy = Column(JSON(none_as_null=True), nullable=False)
    provenance_class = Column(String, nullable=False)
    raw_dependencies = Column(JSON(none_as_null=True), nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    schema_version = Column(Text, nullable=False)
    status = Column(String, nullable=False)
    transformation_specification = Column(JSON(none_as_null=True), nullable=False)
    units = Column(Text, nullable=False)
    window_specification = Column(JSON(none_as_null=True), nullable=False)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_feature_definition_provenance",
        ),
        CheckConstraint(
            "feature_version IS NULL OR length(feature_version) = 64",
            name="ck_fs2_feature_definition_feature_vers",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_feature_definition_id"),
    )


class FeatureValueRow(FeatureStoreBase):
    __tablename__ = "fs2_feature_value"
    available_to_model_at = Column(UTCDateTime(), nullable=False, index=True)
    computed_at = Column(UTCDateTime(), nullable=False, index=True)
    coverage_definition = Column(Text, nullable=True)
    coverage_fraction = Column(ExactDecimal(), nullable=True)
    denominator = Column(ExactDecimal(), nullable=True)
    feature_definition_id = Column(
        String(64),
        ForeignKey(
            "fs2_feature_definition.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    feature_id = Column(Text, nullable=False)
    feature_version = Column(Text, nullable=False)
    id = Column(String(64), primary_key=True)
    input_observation_ids = Column(JSON(none_as_null=True), nullable=False)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    missingness_reason = Column(String, nullable=False)
    numerator = Column(ExactDecimal(), nullable=True)
    origin_id = Column(
        String(64),
        ForeignKey(
            "fs2_research_origin.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    provenance_class = Column(String, nullable=False)
    quality_flags = Column(JSON(none_as_null=True), nullable=False)
    raw_value_decimal = Column(ExactDecimal(), nullable=True)
    raw_value_text = Column(Text, nullable=True)
    raw_value_vector = Column(JSON(none_as_null=True), nullable=True)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    schema_version = Column(Text, nullable=False)
    transform_manifest_id = Column(
        String(64),
        ForeignKey(
            "fs2_artifact_manifest.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
        index=True,
    )
    transform_version = Column(Text, nullable=False)
    transformed_value = Column(JSON(none_as_null=True), nullable=True)
    units = Column(Text, nullable=False)
    window_end_at = Column(UTCDateTime(), nullable=False, index=True)
    window_start_at = Column(UTCDateTime(), nullable=False, index=True)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_feature_value_provenance",
        ),
        CheckConstraint(
            "feature_definition_id IS NULL OR length(feature_definition_id) = 64",
            name="ck_fs2_feature_value_feature_defi",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_feature_value_id"),
        CheckConstraint(
            "origin_id IS NULL OR length(origin_id) = 64", name="ck_fs2_feature_value_origin_id"
        ),
        CheckConstraint(
            "transform_manifest_id IS NULL OR length(transform_manifest_id) = 64",
            name="ck_fs2_feature_value_transform_ma",
        ),
    )


class InformationEventVersionRow(FeatureStoreBase):
    __tablename__ = "fs2_information_event_version"
    available_to_model_at = Column(UTCDateTime(), nullable=False, index=True)
    claim_id = Column(Text, nullable=False)
    document_id = Column(Text, nullable=False)
    embedding_version = Column(Text, nullable=True)
    entity_ids = Column(JSON(none_as_null=True), nullable=False)
    expectation_available_at = Column(UTCDateTime(), nullable=True, index=True)
    extraction_model_version = Column(Text, nullable=True)
    extraction_output = Column(JSON(none_as_null=True), nullable=False)
    first_available_at = Column(UTCDateTime(), nullable=True, index=True)
    first_received_at = Column(UTCDateTime(), nullable=False, index=True)
    id = Column(String(64), primary_key=True)
    independent_source_count = Column(BigInteger, nullable=True)
    lineage_observation_ids = Column(JSON(none_as_null=True), nullable=False)
    market_match_ids = Column(JSON(none_as_null=True), nullable=False)
    match_confidence = Column(ExactDecimal(), nullable=True)
    matching_version = Column(String(64), nullable=False)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    novelty_value = Column(ExactDecimal(), nullable=True)
    numeric_actual_raw = Column(Text, nullable=True)
    numeric_expectation_raw = Column(Text, nullable=True)
    numeric_unit = Column(Text, nullable=True)
    original_source_id = Column(Text, nullable=True)
    prompt_hash = Column(Text, nullable=True)
    provenance_class = Column(String, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    schema_version = Column(Text, nullable=False)
    source_observation_id = Column(
        String(64),
        ForeignKey(
            "fs2_source_observation.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    source_published_at = Column(UTCDateTime(), nullable=True, index=True)
    stance_probabilities = Column(JSON(none_as_null=True), nullable=True)
    supersedes_id = Column(
        String(64),
        ForeignKey(
            "fs2_information_event_version.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
        index=True,
    )
    text_hash = Column(String(64), nullable=False)
    text_hash_scope = Column(String, nullable=False)
    text_rights_state = Column(String, nullable=False)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_information_event_version_provenance",
        ),
        CheckConstraint(
            "id IS NULL OR length(id) = 64", name="ck_fs2_information_event_version_id"
        ),
        CheckConstraint(
            "matching_version IS NULL OR length(matching_version) = 64",
            name="ck_fs2_information_event_version_matching_ver",
        ),
        CheckConstraint(
            "source_observation_id IS NULL OR length(source_observation_id) = 64",
            name="ck_fs2_information_event_version_source_obser",
        ),
        CheckConstraint(
            "supersedes_id IS NULL OR length(supersedes_id) = 64",
            name="ck_fs2_information_event_version_supersedes_i",
        ),
        CheckConstraint(
            "text_hash IS NULL OR length(text_hash) = 64",
            name="ck_fs2_information_event_version_text_hash",
        ),
    )


class LabelVersionRow(FeatureStoreBase):
    __tablename__ = "fs2_label_version"
    actual_delay_seconds = Column(ExactDecimal(), nullable=True)
    censoring_reason = Column(String, nullable=True)
    fee_config_version = Column(Text, nullable=True)
    id = Column(String(64), primary_key=True)
    label_available_at = Column(UTCDateTime(), nullable=True, index=True)
    label_computation_version = Column(String(64), nullable=False)
    label_id = Column(String(64), nullable=False)
    label_observed_at = Column(UTCDateTime(), nullable=True, index=True)
    label_value = Column(JSON(none_as_null=True), nullable=True)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    origin_id = Column(
        String(64),
        ForeignKey(
            "fs2_research_origin.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    outcome_observation_ids = Column(JSON(none_as_null=True), nullable=False)
    payout_vector = Column(JSON(none_as_null=True), nullable=True)
    prediction_id = Column(
        String(64),
        ForeignKey("fs2_prediction.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"),
        nullable=True,
        index=True,
    )
    provenance_class = Column(String, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    revision_reason = Column(Text, nullable=True)
    schema_version = Column(Text, nullable=False)
    status = Column(String, nullable=False)
    supersedes_label_id = Column(
        Text,
        ForeignKey(
            "fs2_label_version.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
        index=True,
    )
    target_at = Column(UTCDateTime(), nullable=False, index=True)
    target_definition_id = Column(
        String(64),
        ForeignKey(
            "fs2_target_definition.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_label_version_provenance",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_label_version_id"),
        CheckConstraint(
            "label_computation_version IS NULL OR length(label_computation_version) = 64",
            name="ck_fs2_label_version_label_comput",
        ),
        CheckConstraint(
            "label_id IS NULL OR length(label_id) = 64", name="ck_fs2_label_version_label_id"
        ),
        CheckConstraint(
            "origin_id IS NULL OR length(origin_id) = 64", name="ck_fs2_label_version_origin_id"
        ),
        CheckConstraint(
            "prediction_id IS NULL OR length(prediction_id) = 64",
            name="ck_fs2_label_version_prediction_i",
        ),
        CheckConstraint(
            "target_definition_id IS NULL OR length(target_definition_id) = 64",
            name="ck_fs2_label_version_target_defin",
        ),
    )


class MarketIdentityVersionRow(FeatureStoreBase):
    __tablename__ = "fs2_market_identity_version"
    category = Column(Text, nullable=True)
    close_at = Column(UTCDateTime(), nullable=True, index=True)
    condition_identity_id = Column(
        String(64),
        ForeignKey(
            "fs2_condition_identity.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
        index=True,
    )
    event_id = Column(Text, nullable=True)
    fee_configuration = Column(JSON(none_as_null=True), nullable=True)
    id = Column(String(64), primary_key=True)
    information_event_at = Column(UTCDateTime(), nullable=True, index=True)
    lifecycle_state = Column(Text, nullable=False)
    mapping_confidence = Column(ExactDecimal(), nullable=True)
    mapping_evidence_ids = Column(JSON(none_as_null=True), nullable=False)
    mapping_version = Column(String(64), nullable=False)
    market_id = Column(Text, nullable=False)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    observed_from_at = Column(UTCDateTime(), nullable=False, index=True)
    provenance_class = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    resolution_source = Column(Text, nullable=True)
    rules_hash = Column(String(64), nullable=True)
    rules_text = Column(Text, nullable=True)
    schema_version = Column(Text, nullable=False)
    supersedes_id = Column(
        String(64),
        ForeignKey(
            "fs2_market_identity_version.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
        index=True,
    )
    tick_size = Column(ExactDecimal(), nullable=True)
    valid_from_at = Column(UTCDateTime(), nullable=True, index=True)
    valid_to_at = Column(UTCDateTime(), nullable=True, index=True)
    venue = Column(Text, nullable=False)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_market_identity_version_provenance",
        ),
        CheckConstraint(
            "condition_identity_id IS NULL OR length(condition_identity_id) = 64",
            name="ck_fs2_market_identity_version_condition_id",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_market_identity_version_id"),
        CheckConstraint(
            "mapping_version IS NULL OR length(mapping_version) = 64",
            name="ck_fs2_market_identity_version_mapping_vers",
        ),
        CheckConstraint(
            "rules_hash IS NULL OR length(rules_hash) = 64",
            name="ck_fs2_market_identity_version_rules_hash",
        ),
        CheckConstraint(
            "supersedes_id IS NULL OR length(supersedes_id) = 64",
            name="ck_fs2_market_identity_version_supersedes_i",
        ),
    )


class OutcomeObservationRow(FeatureStoreBase):
    __tablename__ = "fs2_outcome_observation"
    ask = Column(ExactDecimal(), nullable=True)
    available_to_model_at = Column(UTCDateTime(), nullable=True, index=True)
    bid = Column(ExactDecimal(), nullable=True)
    close_state = Column(Text, nullable=False)
    executable_size = Column(ExactDecimal(), nullable=True)
    first_received_at = Column(UTCDateTime(), nullable=True, index=True)
    id = Column(String(64), primary_key=True)
    label_observed_at = Column(UTCDateTime(), nullable=True, index=True)
    midpoint = Column(ExactDecimal(), nullable=True)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    missingness_reason = Column(String, nullable=False)
    near_mid_depth = Column(ExactDecimal(), nullable=True)
    observation_status = Column(String, nullable=False)
    origin_id = Column(
        String(64),
        ForeignKey(
            "fs2_research_origin.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    payout_vector = Column(JSON(none_as_null=True), nullable=True)
    provenance_class = Column(String, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    resolution_state = Column(Text, nullable=False)
    schema_version = Column(Text, nullable=False)
    source_observation_id = Column(
        String(64),
        ForeignKey(
            "fs2_source_observation.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    supersedes_id = Column(
        String(64),
        ForeignKey(
            "fs2_outcome_observation.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
        index=True,
    )
    target_at = Column(UTCDateTime(), nullable=False, index=True)
    target_definition_id = Column(
        String(64),
        ForeignKey(
            "fs2_target_definition.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    units = Column(JSON(none_as_null=True), nullable=False)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_outcome_observation_provenance",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_outcome_observation_id"),
        CheckConstraint(
            "origin_id IS NULL OR length(origin_id) = 64",
            name="ck_fs2_outcome_observation_origin_id",
        ),
        CheckConstraint(
            "source_observation_id IS NULL OR length(source_observation_id) = 64",
            name="ck_fs2_outcome_observation_source_obser",
        ),
        CheckConstraint(
            "supersedes_id IS NULL OR length(supersedes_id) = 64",
            name="ck_fs2_outcome_observation_supersedes_i",
        ),
        CheckConstraint(
            "target_definition_id IS NULL OR length(target_definition_id) = 64",
            name="ck_fs2_outcome_observation_target_defin",
        ),
    )


class PredictionRow(FeatureStoreBase):
    __tablename__ = "fs2_prediction"
    abstention_reason = Column(String, nullable=True)
    calibration_version = Column(Text, nullable=False)
    class_probabilities = Column(JSON(none_as_null=True), nullable=True)
    direction = Column(String, nullable=True)
    distribution_parameters = Column(JSON(none_as_null=True), nullable=True)
    experiment_run_id = Column(
        String(64),
        ForeignKey(
            "fs2_experiment_run.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    feature_manifest_id = Column(
        String(64),
        ForeignKey(
            "fs2_artifact_manifest.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    generated_at = Column(UTCDateTime(), nullable=False, index=True)
    horizon_seconds = Column(BigInteger, nullable=False)
    id = Column(String(64), primary_key=True)
    latency_ms = Column(ExactDecimal(), nullable=False)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    model_version = Column(Text, nullable=False)
    origin_id = Column(
        String(64),
        ForeignKey(
            "fs2_research_origin.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    output_kind = Column(String, nullable=False)
    prediction_id = Column(String(64), nullable=False)
    prediction_persisted_at = Column(UTCDateTime(), nullable=False, index=True)
    provenance_class = Column(String, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    schema_version = Column(Text, nullable=False)
    target_definition_id = Column(
        String(64),
        ForeignKey(
            "fs2_target_definition.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    target_version = Column(Text, nullable=False)
    training_manifest_id = Column(
        Text,
        ForeignKey(
            "fs2_artifact_manifest.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    uncalibrated_prediction_id = Column(
        String(64),
        ForeignKey("fs2_prediction.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"),
        nullable=True,
        index=True,
    )
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_prediction_provenance",
        ),
        CheckConstraint(
            "experiment_run_id IS NULL OR length(experiment_run_id) = 64",
            name="ck_fs2_prediction_experiment_r",
        ),
        CheckConstraint(
            "feature_manifest_id IS NULL OR length(feature_manifest_id) = 64",
            name="ck_fs2_prediction_feature_mani",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_prediction_id"),
        CheckConstraint(
            "origin_id IS NULL OR length(origin_id) = 64", name="ck_fs2_prediction_origin_id"
        ),
        CheckConstraint(
            "prediction_id IS NULL OR length(prediction_id) = 64",
            name="ck_fs2_prediction_prediction_i",
        ),
        CheckConstraint(
            "target_definition_id IS NULL OR length(target_definition_id) = 64",
            name="ck_fs2_prediction_target_defin",
        ),
        CheckConstraint(
            "uncalibrated_prediction_id IS NULL OR length(uncalibrated_prediction_id) = 64",
            name="ck_fs2_prediction_uncalibrated",
        ),
    )


class ResearchOriginRow(FeatureStoreBase):
    __tablename__ = "fs2_research_origin"
    eligibility_reason = Column(Text, nullable=False)
    eligibility_snapshot = Column(JSON(none_as_null=True), nullable=False)
    eligibility_version = Column(Text, nullable=False)
    event_group_version = Column(Text, nullable=False)
    feature_cutoff_at = Column(UTCDateTime(), nullable=False, index=True)
    group_manifest_id = Column(
        String(64),
        ForeignKey(
            "fs2_artifact_manifest.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    id = Column(String(64), primary_key=True)
    legacy_entry_reference = Column(JSON(none_as_null=True), nullable=True)
    market_identity_id = Column(
        String(64),
        ForeignKey(
            "fs2_market_identity_version.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        index=True,
    )
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    origin_id = Column(String(64), nullable=False)
    origin_kind = Column(String, nullable=False)
    origin_recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    prediction_origin_at = Column(UTCDateTime(), nullable=False, index=True)
    provenance_class = Column(String, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    sampling_arm = Column(String, nullable=False)
    sampling_manifest_id = Column(
        String(64),
        ForeignKey(
            "fs2_artifact_manifest.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    scheduled_origin_at = Column(UTCDateTime(), nullable=True, index=True)
    schema_version = Column(Text, nullable=False)
    selection_probability = Column(ExactDecimal(), nullable=True)
    token_outcome_id = Column(
        String(64),
        ForeignKey(
            "fs2_token_outcome_version.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        index=True,
    )
    trigger_id = Column(Text, nullable=True)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_research_origin_provenance",
        ),
        CheckConstraint(
            "group_manifest_id IS NULL OR length(group_manifest_id) = 64",
            name="ck_fs2_research_origin_group_manife",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_research_origin_id"),
        CheckConstraint(
            "market_identity_id IS NULL OR length(market_identity_id) = 64",
            name="ck_fs2_research_origin_market_ident",
        ),
        CheckConstraint(
            "origin_id IS NULL OR length(origin_id) = 64", name="ck_fs2_research_origin_origin_id"
        ),
        CheckConstraint(
            "sampling_manifest_id IS NULL OR length(sampling_manifest_id) = 64",
            name="ck_fs2_research_origin_sampling_man",
        ),
        CheckConstraint(
            "token_outcome_id IS NULL OR length(token_outcome_id) = 64",
            name="ck_fs2_research_origin_token_outcom",
        ),
    )


class SourceObservationRow(FeatureStoreBase):
    __tablename__ = "fs2_source_observation"
    availability_evidence_ids = Column(JSON(none_as_null=True), nullable=False)
    available_to_model_at = Column(UTCDateTime(), nullable=False, index=True)
    clock_error_bound_ms = Column(ExactDecimal(), nullable=True)
    clock_session_id = Column(Text, nullable=True)
    coverage_definition = Column(Text, nullable=True)
    coverage_fraction = Column(ExactDecimal(), nullable=True)
    first_available_at = Column(UTCDateTime(), nullable=True, index=True)
    first_received_at = Column(UTCDateTime(), nullable=True, index=True)
    gap_duration_ms = Column(ExactDecimal(), nullable=True)
    id = Column(String(64), primary_key=True)
    ingested_at = Column(UTCDateTime(), nullable=False, index=True)
    legacy_reference = Column(JSON(none_as_null=True), nullable=True)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    missing_reason = Column(String, nullable=False)
    native_clock_details = Column(JSON(none_as_null=True), nullable=False)
    native_record_id = Column(Text, nullable=True)
    observation_id = Column(String(64), nullable=False)
    parsed_at = Column(UTCDateTime(), nullable=True, index=True)
    parser_version = Column(Text, nullable=False)
    payload_encoding = Column(String, nullable=False)
    payload_hash = Column(String(64), nullable=False)
    protocol_version = Column(Text, nullable=True)
    provenance_class = Column(String, nullable=False)
    quality_assessment_state = Column(String, nullable=False)
    quality_flags = Column(JSON(none_as_null=True), nullable=False)
    raw_payload_inline = Column(Text, nullable=True)
    raw_payload_uri = Column(Text, nullable=True)
    raw_timestamp = Column(Text, nullable=True)
    receipt_monotonic_ns = Column(UnsignedIntegerText(), nullable=True)
    receipt_ordinal = Column(BigInteger, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    request_cursor = Column(Text, nullable=True)
    request_id = Column(Text, nullable=False)
    request_metadata = Column(JSON(none_as_null=True), nullable=False)
    revision_of = Column(
        Text,
        ForeignKey(
            "fs2_source_observation.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
        index=True,
    )
    schema_version = Column(Text, nullable=False)
    source_event_at = Column(UTCDateTime(), nullable=True, index=True)
    source_id = Column(Text, nullable=False)
    source_published_at = Column(UTCDateTime(), nullable=True, index=True)
    source_registry_id = Column(
        String(64),
        ForeignKey(
            "fs2_source_registry.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    source_sequence = Column(Text, nullable=True)
    timestamp_unit = Column(Text, nullable=True)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_source_observation_provenance",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_source_observation_id"),
        CheckConstraint(
            "observation_id IS NULL OR length(observation_id) = 64",
            name="ck_fs2_source_observation_observation_",
        ),
        CheckConstraint(
            "payload_hash IS NULL OR length(payload_hash) = 64",
            name="ck_fs2_source_observation_payload_hash",
        ),
        CheckConstraint(
            "source_registry_id IS NULL OR length(source_registry_id) = 64",
            name="ck_fs2_source_observation_source_regis",
        ),
    )


class SourceRegistryRow(FeatureStoreBase):
    __tablename__ = "fs2_source_registry"
    access_state = Column(String, nullable=False)
    clock_semantics = Column(JSON(none_as_null=True), nullable=False)
    endpoint = Column(Text, nullable=False)
    id = Column(String(64), primary_key=True)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    parser_version = Column(Text, nullable=False)
    protocol_version = Column(Text, nullable=True)
    provenance_class = Column(String, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    registry_version = Column(String(64), nullable=False)
    rights_evidence = Column(JSON(none_as_null=True), nullable=False)
    rights_state = Column(String, nullable=False)
    schema_hash = Column(String(64), nullable=False)
    schema_version = Column(Text, nullable=False)
    source_id = Column(Text, nullable=False)
    supersedes_id = Column(
        String(64),
        ForeignKey(
            "fs2_source_registry.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
        index=True,
    )
    unit_conventions = Column(JSON(none_as_null=True), nullable=False)
    verified_observation_id = Column(
        String(64),
        ForeignKey(
            "fs2_source_observation.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
            use_alter=True,
        ),
        nullable=True,
        index=True,
    )
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_source_registry_provenance",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_source_registry_id"),
        CheckConstraint(
            "registry_version IS NULL OR length(registry_version) = 64",
            name="ck_fs2_source_registry_registry_ver",
        ),
        CheckConstraint(
            "schema_hash IS NULL OR length(schema_hash) = 64",
            name="ck_fs2_source_registry_schema_hash",
        ),
        CheckConstraint(
            "supersedes_id IS NULL OR length(supersedes_id) = 64",
            name="ck_fs2_source_registry_supersedes_i",
        ),
        CheckConstraint(
            "verified_observation_id IS NULL OR length(verified_observation_id) = 64",
            name="ck_fs2_source_registry_verified_obs",
        ),
    )


class TargetDefinitionRow(FeatureStoreBase):
    __tablename__ = "fs2_target_definition"
    horizon_seconds = Column(BigInteger, nullable=True)
    id = Column(String(64), primary_key=True)
    label_rule = Column(JSON(none_as_null=True), nullable=False)
    metric_contract = Column(JSON(none_as_null=True), nullable=False)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    provenance_class = Column(String, nullable=False)
    quote_rule = Column(JSON(none_as_null=True), nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    schema_version = Column(Text, nullable=False)
    target_family = Column(String, nullable=False)
    target_version = Column(String(64), nullable=False)
    units = Column(Text, nullable=False)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_target_definition_provenance",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_target_definition_id"),
        CheckConstraint(
            "target_version IS NULL OR length(target_version) = 64",
            name="ck_fs2_target_definition_target_versi",
        ),
    )


class TokenOutcomeVersionRow(FeatureStoreBase):
    __tablename__ = "fs2_token_outcome_version"
    chain_id = Column(BigInteger, nullable=True)
    condition_identity_id = Column(
        String(64),
        ForeignKey(
            "fs2_condition_identity.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
        index=True,
    )
    id = Column(String(64), primary_key=True)
    mapping_evidence_ids = Column(JSON(none_as_null=True), nullable=False)
    mapping_version = Column(String(64), nullable=False)
    market_identity_id = Column(
        String(64),
        ForeignKey(
            "fs2_market_identity_version.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        index=True,
    )
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    observed_from_at = Column(UTCDateTime(), nullable=False, index=True)
    outcome_index = Column(BigInteger, nullable=True)
    outcome_label = Column(Text, nullable=True)
    provenance_class = Column(String, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    schema_version = Column(Text, nullable=False)
    supersedes_id = Column(
        String(64),
        ForeignKey(
            "fs2_token_outcome_version.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
        index=True,
    )
    token_contract = Column(String(42), nullable=True)
    token_id = Column(UnsignedIntegerText(256), nullable=True)
    valid_from_at = Column(UTCDateTime(), nullable=True, index=True)
    valid_to_at = Column(UTCDateTime(), nullable=True, index=True)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_token_outcome_version_provenance",
        ),
        CheckConstraint(
            "condition_identity_id IS NULL OR length(condition_identity_id) = 64",
            name="ck_fs2_token_outcome_version_condition_id",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_token_outcome_version_id"),
        CheckConstraint(
            "mapping_version IS NULL OR length(mapping_version) = 64",
            name="ck_fs2_token_outcome_version_mapping_vers",
        ),
        CheckConstraint(
            "market_identity_id IS NULL OR length(market_identity_id) = 64",
            name="ck_fs2_token_outcome_version_market_ident",
        ),
        CheckConstraint(
            "supersedes_id IS NULL OR length(supersedes_id) = 64",
            name="ck_fs2_token_outcome_version_supersedes_i",
        ),
    )


class TradeObservationRow(FeatureStoreBase):
    __tablename__ = "fs2_trade_observation"
    aggressor_side = Column(String, nullable=True)
    block_hash = Column(String(66), nullable=True)
    block_number = Column(UnsignedIntegerText(), nullable=True)
    chain_id = Column(BigInteger, nullable=True)
    deduplication_status = Column(String, nullable=False)
    deduplication_version = Column(Text, nullable=False)
    economic_fill_key = Column(Text, nullable=True)
    fee_native = Column(ExactDecimal(), nullable=True)
    fee_unit = Column(Text, nullable=True)
    id = Column(String(64), primary_key=True)
    log_index = Column(BigInteger, nullable=True)
    maker_wallet = Column(Text, nullable=True)
    match_status = Column(String, nullable=False)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    notional_currency = Column(Text, nullable=False)
    price_decimal = Column(ExactDecimal(), nullable=True)
    provenance_class = Column(String, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    schema_version = Column(Text, nullable=False)
    settlement_status = Column(String, nullable=False)
    side_semantics_version = Column(Text, nullable=False)
    size_decimal = Column(ExactDecimal(), nullable=True)
    source_observation_id = Column(
        String(64),
        ForeignKey(
            "fs2_source_observation.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    supersedes_id = Column(
        String(64),
        ForeignKey(
            "fs2_trade_observation.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
        index=True,
    )
    taker_wallet = Column(Text, nullable=True)
    token_outcome_id = Column(
        String(64),
        ForeignKey(
            "fs2_token_outcome_version.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
        index=True,
    )
    trade_id = Column(Text, nullable=False)
    trade_notional = Column(ExactDecimal(), nullable=True)
    trade_price_raw = Column(Text, nullable=False)
    trade_size_raw = Column(Text, nullable=False)
    transaction_hash = Column(String(66), nullable=True)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_trade_observation_provenance",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_trade_observation_id"),
        CheckConstraint(
            "source_observation_id IS NULL OR length(source_observation_id) = 64",
            name="ck_fs2_trade_observation_source_obser",
        ),
        CheckConstraint(
            "supersedes_id IS NULL OR length(supersedes_id) = 64",
            name="ck_fs2_trade_observation_supersedes_i",
        ),
        CheckConstraint(
            "token_outcome_id IS NULL OR length(token_outcome_id) = 64",
            name="ck_fs2_trade_observation_token_outcom",
        ),
    )


class WalletStateVersionRow(FeatureStoreBase):
    __tablename__ = "fs2_wallet_state_version"
    as_of_cutoff_at = Column(UTCDateTime(), nullable=False, index=True)
    attribution_confidence = Column(ExactDecimal(), nullable=True)
    available_to_model_at = Column(UTCDateTime(), nullable=False, index=True)
    chain_id = Column(BigInteger, nullable=False)
    coverage_start_at = Column(UTCDateTime(), nullable=True, index=True)
    first_observed_at = Column(UTCDateTime(), nullable=False, index=True)
    history_coverage_fraction = Column(ExactDecimal(), nullable=True)
    history_manifest_id = Column(
        Text,
        ForeignKey(
            "fs2_artifact_manifest.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=False,
        index=True,
    )
    holding_shares = Column(ExactDecimal(), nullable=True)
    id = Column(String(64), primary_key=True)
    missing_fields = Column(JSON(none_as_null=True), nullable=False)
    net_flow = Column(ExactDecimal(), nullable=True)
    prior_mature_event_count = Column(BigInteger, nullable=False)
    provenance_class = Column(String, nullable=False)
    recorded_at = Column(UTCDateTime(), nullable=False, index=True)
    role_flags = Column(JSON(none_as_null=True), nullable=False)
    schema_version = Column(Text, nullable=False)
    skill_posterior_mean = Column(ExactDecimal(), nullable=True)
    skill_posterior_sd = Column(ExactDecimal(), nullable=True)
    state_definition_version = Column(String(64), nullable=False)
    supersedes_id = Column(
        String(64),
        ForeignKey(
            "fs2_wallet_state_version.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
        index=True,
    )
    token_outcome_id = Column(
        String(64),
        ForeignKey(
            "fs2_token_outcome_version.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
        index=True,
    )
    uncertainty = Column(JSON(none_as_null=True), nullable=False)
    wallet_id = Column(Text, nullable=False)
    __table_args__ = (
        CheckConstraint(
            "provenance_class IN ('prospective','reconstructed','synthetic','legacy_unverified')",
            name="ck_fs2_wallet_state_version_provenance",
        ),
        CheckConstraint("id IS NULL OR length(id) = 64", name="ck_fs2_wallet_state_version_id"),
        CheckConstraint(
            "state_definition_version IS NULL OR length(state_definition_version) = 64",
            name="ck_fs2_wallet_state_version_state_defini",
        ),
        CheckConstraint(
            "supersedes_id IS NULL OR length(supersedes_id) = 64",
            name="ck_fs2_wallet_state_version_supersedes_i",
        ),
        CheckConstraint(
            "token_outcome_id IS NULL OR length(token_outcome_id) = 64",
            name="ck_fs2_wallet_state_version_token_outcom",
        ),
    )


MODEL_BY_ENTITY = {
    "archive_manifest": ArchiveManifestRow,
    "artifact_manifest": ArtifactManifestRow,
    "book_level": BookLevelRow,
    "book_snapshot": BookSnapshotRow,
    "condition_identity": ConditionIdentityRow,
    "event_group_membership": EventGroupMembershipRow,
    "experiment_run": ExperimentRunRow,
    "feature_definition": FeatureDefinitionRow,
    "feature_value": FeatureValueRow,
    "information_event_version": InformationEventVersionRow,
    "label_version": LabelVersionRow,
    "market_identity_version": MarketIdentityVersionRow,
    "outcome_observation": OutcomeObservationRow,
    "prediction": PredictionRow,
    "research_origin": ResearchOriginRow,
    "source_observation": SourceObservationRow,
    "source_registry": SourceRegistryRow,
    "target_definition": TargetDefinitionRow,
    "token_outcome_version": TokenOutcomeVersionRow,
    "trade_observation": TradeObservationRow,
    "wallet_state_version": WalletStateVersionRow,
}


def _add_contract_constraints():
    """Share closed vocabularies with admission; JSON-list keys use the validated SHA PK."""
    from .admission import ALIASES, ENUMS, MISSING
    from .schema import FIELD_SPECS, KEY_FIELDS

    for entity, model in MODEL_BY_ENTITY.items():
        table = model.__table__
        keys = KEY_FIELDS[entity]
        if all(not isinstance(table.c[key].type, JSON) for key in keys):
            table.append_constraint(UniqueConstraint(*keys, name=f"uq_fs2_{entity}_natural"))
        if entity in ALIASES:
            table.append_constraint(
                CheckConstraint(f"{ALIASES[entity]} = id", name=f"ck_fs2_{entity}_alias")
            )
        for field, spec in FIELD_SPECS[entity].items():
            if spec["type"] == "ENUM" and field != "provenance_class":
                allowed = (
                    MISSING
                    if field in {"missing_reason", "missingness_reason"}
                    else set(ENUMS[(entity, field)].split())
                )
                values = ",".join("'" + value + "'" for value in sorted(allowed))
                table.append_constraint(
                    CheckConstraint(
                        f"{field} IS NULL OR {field} IN ({values})",
                        name=f"ck_fs2_{entity}_{field}_enum",
                    )
                )
            if spec["type"] == "INT64":
                table.append_constraint(
                    CheckConstraint(
                        f"{field} IS NULL OR {field} >= 0", name=f"ck_fs2_{entity}_{field}_count"
                    )
                )


_add_contract_constraints()
