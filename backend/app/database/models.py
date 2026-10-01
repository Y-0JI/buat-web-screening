from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class ChatThread(Base):
    """Satu percakapan chat. Di-scope per perangkat (tanpa auth)."""

    __tablename__ = "chat_threads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="Percakapan baru")
    model = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages = relationship(
        "ChatMessage", back_populates="thread", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    """Satu pesan dalam thread chat (user/assistant)."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(
        Integer, ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False, default="")
    reasoning = Column(Text, nullable=True)
    tool_calls = Column(JSON, nullable=True)
    model = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    thread = relationship("ChatThread", back_populates="messages")


class AccumulationScan(Base):
    """Satu siklus scan harian deteksi akumulasi pemain besar.

    Unik per `scan_date` (idempotensi). Scan `complete` tidak ditimpa tanpa
    flag `force`.
    """

    __tablename__ = "accumulation_scans"
    __table_args__ = (
        UniqueConstraint("scan_date", name="uq_accumulation_scans_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_date = Column(Date, nullable=False, index=True)
    status = Column(String(16), nullable=False, default="partial")
    universe_count = Column(Integer, nullable=False, default=0)
    stage_b_count = Column(Integer, nullable=False, default=0)
    stage_c_count = Column(Integer, nullable=False, default=0)
    requests_used = Column(Integer, nullable=False, default=0)
    quota_remaining = Column(Integer, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    signals = relationship(
        "AccumulationSignal", back_populates="scan", cascade="all, delete-orphan"
    )


class AccumulationSignal(Base):
    """Sinyal akumulasi per saham. `components` menyimpan komponen MENTAH agar
    bisa di-re-skor tanpa memanggil API ulang. Tanpa logika skor di sini.
    """

    __tablename__ = "accumulation_signals"
    __table_args__ = (
        Index("ix_accum_signals_scan_score", "scan_id", "score"),
        Index("ix_accum_signals_ticker_scan", "ticker", "scan_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(
        Integer,
        ForeignKey("accumulation_scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ticker = Column(String(16), nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    depth = Column(String(16), nullable=False, default="hv")
    components = Column(JSON, nullable=True)
    reasons = Column(Text, nullable=True)
    close = Column(Float, nullable=True)
    foreign_net = Column(Float, nullable=True)
    broker_net = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    scan = relationship("AccumulationScan", back_populates="signals")


class AccumulationRotation(Base):
    """Kapan tiap ticker terakhir dicek (untuk rotasi irisan universe)."""

    __tablename__ = "accumulation_rotation"
    __table_args__ = (
        UniqueConstraint("ticker", name="uq_accumulation_rotation_ticker"),
    )

    ticker = Column(String(16), primary_key=True)
    stratum = Column(Integer, nullable=False, default=0)
    last_checked_scan_id = Column(Integer, nullable=True)
