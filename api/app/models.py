from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier: Mapped[str] = mapped_column(String(240), index=True)
    normalized_supplier: Mapped[str] = mapped_column(String(240), index=True)
    description: Mapped[str] = mapped_column(Text)
    amount: Mapped[float] = mapped_column(Float)
    invoice_id: Mapped[str] = mapped_column(String(120), index=True)
    transaction_date: Mapped[str] = mapped_column(String(32), index=True)
    category: Mapped[str] = mapped_column(String(120), index=True)
    category_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    duplicate_reason: Mapped[str] = mapped_column(String(240), default="")
