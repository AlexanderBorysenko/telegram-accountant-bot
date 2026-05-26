from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


Status = Literal["pending", "done"]


class TransactionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    money_amount: float
    payment_status: Status = "pending"
    job_status: Status = "pending"


class TransactionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    money_amount: Optional[float] = None
    payment_status: Optional[Status] = None
    job_status: Optional[Status] = None

    def to_update_dict(self) -> dict:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class TransactionDoc(BaseModel):
    id: str
    chat_id: int
    title: str
    description: Optional[str] = None
    money_amount: float
    payment_status: Status = "pending"
    job_status: Status = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_fulfilled(self) -> bool:
        return self.payment_status == "done" and self.job_status == "done"

    def to_display_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "money_amount": self.money_amount,
            "payment_status": self.payment_status,
            "job_status": self.job_status,
            "is_fulfilled": self.is_fulfilled,
            "created_at": self.created_at.isoformat(),
        }
