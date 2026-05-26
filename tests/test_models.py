import pytest
from datetime import datetime, timezone


def test_create_transaction_required_fields():
    from src.models import TransactionCreate
    tx = TransactionCreate(title="Test task", money_amount=100.0)
    assert tx.title == "Test task"
    assert tx.money_amount == 100.0
    assert tx.description is None
    assert tx.payment_status == "pending"
    assert tx.job_status == "pending"


def test_create_transaction_all_fields():
    from src.models import TransactionCreate
    tx = TransactionCreate(
        title="Full task",
        description="With description",
        money_amount=250.0,
        payment_status="done",
        job_status="pending",
    )
    assert tx.description == "With description"
    assert tx.payment_status == "done"


def test_create_transaction_invalid_status():
    from src.models import TransactionCreate
    with pytest.raises(ValueError):
        TransactionCreate(title="Bad", money_amount=100.0, payment_status="invalid")


def test_update_transaction_partial():
    from src.models import TransactionUpdate
    update = TransactionUpdate(title="New title")
    assert update.title == "New title"
    assert update.money_amount is None
    assert update.payment_status is None


def test_update_transaction_to_dict_excludes_none():
    from src.models import TransactionUpdate
    update = TransactionUpdate(payment_status="done")
    d = update.to_update_dict()
    assert d == {"payment_status": "done"}
    assert "title" not in d


def test_transaction_doc_is_fulfilled():
    from src.models import TransactionDoc
    doc = TransactionDoc(
        id="abc123",
        chat_id=1,
        title="Test",
        money_amount=100.0,
        payment_status="done",
        job_status="done",
        created_at=datetime.now(timezone.utc),
    )
    assert doc.is_fulfilled is True


def test_transaction_doc_not_fulfilled():
    from src.models import TransactionDoc
    doc = TransactionDoc(
        id="abc123",
        chat_id=1,
        title="Test",
        money_amount=100.0,
        payment_status="done",
        job_status="pending",
        created_at=datetime.now(timezone.utc),
    )
    assert doc.is_fulfilled is False
