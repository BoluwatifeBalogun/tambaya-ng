"""SQLAlchemy models. Mirrors the seminar report's ERD (§3.14.5) and database design (§3.15, Tables 3.2 to 3.7)
plus the conversation tables (§3.15.7)."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .config import get_settings
from .db import Base

EMBED_DIM = get_settings().embed_dim


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Language(Base):
    """Table 3.6: Language."""

    __tablename__ = "language"
    language_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    language_name: Mapped[str] = mapped_column(String(64), nullable=False)
    native_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    language_code: Mapped[str] = mapped_column(String(8), nullable=False, unique=True)
    native_kb: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Agency(Base):
    """Table 3.3: Agency."""

    __tablename__ = "agency"
    agency_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    agency_name: Mapped[str] = mapped_column(String(160), nullable=False)
    agency_description: Mapped[str] = mapped_column(Text, default="")
    website_url: Mapped[str] = mapped_column(Text, default="")
    contact_info: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    domains: Mapped[list["ServiceDomain"]] = relationship(back_populates="agency")


class ServiceDomain(Base):
    """Table 3.4: Service Domain."""

    __tablename__ = "service_domain"
    domain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agency_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agency.agency_id"), nullable=True)
    slug: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    domain_name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    agency: Mapped[Agency | None] = relationship(back_populates="domains")
    documents: Mapped[list["KnowledgeDocument"]] = relationship(back_populates="domain")


class KnowledgeDocument(Base):
    """Table 3.5: Knowledge Document."""

    __tablename__ = "knowledge_document"
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_domain.domain_id"), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[str] = mapped_column(String(32), default="webpage")
    source_url: Mapped[str] = mapped_column(Text, default="")
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_verified: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    domain: Mapped[ServiceDomain] = relationship(back_populates="documents")
    sources: Mapped[list["Source"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    entries: Mapped[list["KnowledgeEntry"]] = relationship(back_populates="document")


class Source(Base):
    """Table 3.7: Source (traceability between a document and where it was obtained)."""

    __tablename__ = "source"
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_document.document_id"), nullable=False)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, default="")
    source_type: Mapped[str] = mapped_column(String(32), default="official")
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    document: Mapped[KnowledgeDocument] = relationship(back_populates="sources")


class KnowledgeEntry(Base):
    """Table 3.2: Knowledge Entry. The unit retrieved by the RAG component.

    `entry_key` links sibling entries that carry the same fact in different languages (en/ha/yo/ig),
    which lets retrieval work on the English canonical layer and present the user's language."""

    __tablename__ = "knowledge_entry"
    __table_args__ = (UniqueConstraint("entry_key", "language_id", name="uq_entry_key_language"),)

    entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_document.document_id"), nullable=False)
    language_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("language.language_id"), nullable=False)
    entry_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    section_title: Mapped[str] = mapped_column(Text, default="")
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    alt_questions: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_vector = mapped_column(Vector(EMBED_DIM), nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(64), default="")
    page_reference: Mapped[str] = mapped_column(String(128), default="")
    review_status: Mapped[str] = mapped_column(String(16), default="approved")  # approved | pending | rejected
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    document: Mapped[KnowledgeDocument] = relationship(back_populates="entries")
    language: Mapped[Language] = relationship()

    @property
    def embedding_text(self) -> str:
        alts = " ".join(self.alt_questions or [])
        return f"{self.section_title}\n{self.question_text}\n{alts}\n{self.answer_text}"

    @property
    def embedding_text_local(self) -> str:
        """For the hashed local embedder, questions are what users type: weight them and clip the answer."""
        alts = " ".join(self.alt_questions or [])
        return f"{self.question_text} {self.question_text}\n{alts}\n{self.section_title}\n{self.answer_text[:240]}"


class AppUser(Base):
    """§3.15.7 User: anonymous, no personally identifiable information."""

    __tablename__ = "app_user"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Conversation(Base):
    __tablename__ = "conversation"
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.user_id"), nullable=False)
    language_code: Mapped[str] = mapped_column(String(8), default="auto")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "message"
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversation.conversation_id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant
    text: Mapped[str] = mapped_column(Text, nullable=False)
    language_code: Mapped[str] = mapped_column(String(8), default="en")
    domain: Mapped[str] = mapped_column(String(32), default="")
    retrieval_query: Mapped[str] = mapped_column(Text, default="")
    top_entry_key: Mapped[str] = mapped_column(String(64), default="")
    cited_entry_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    was_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    top_similarity: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
