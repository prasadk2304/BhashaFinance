from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class Transaction(BaseModel):
    transaction_id: str
    customer_id: str
    account_id: str
    amount: float
    type: str  # "emi_debit", "upi_payment", "refund", "wallet_transfer"
    status: str  # "success", "failed", "pending", "reversed"
    description: str
    date: str
    sample_label: str = "Sample"


MOCK_CUSTOMERS: Dict[str, Dict[str, Any]] = {
    "CUST-1001": {
        "customer_id": "CUST-1001",
        "name": "Prasad Sharma",
        "mobile": "+91 98765 43210",
        "cibil_score": 745,
        "active_loan_id": "PAYTM-LN-8812",
        "monthly_income": 85000.0,
    },
    "CUST-1002": {
        "customer_id": "CUST-1002",
        "name": "Ananya Patel",
        "mobile": "+91 91234 56789",
        "cibil_score": 630,
        "active_loan_id": "PAYTM-LN-9920",
        "monthly_income": 42000.0,
    },
}


def get_mock_transactions(customer_id: str) -> List[Transaction]:
    """
    Returns synthetic sample transactions for a given customer.
    Includes recent successful and failed EMI transactions for testing payment help.
    """
    now = datetime.now(timezone.utc)

    # Base synthetic transactions
    txns = [
        Transaction(
            transaction_id="TXN-982101",
            customer_id=customer_id,
            account_id="PAYTM-LN-8812",
            amount=4500.00,
            type="emi_debit",
            status="failed",
            description="Sample auto-debit attempt via NACH (Insufficient funds / Clearing error)",
            date=(now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S UTC"),
        ),
        Transaction(
            transaction_id="TXN-973024",
            customer_id=customer_id,
            account_id="PAYTM-LN-8812",
            amount=4500.00,
            type="emi_debit",
            status="success",
            description="Sample loan EMI monthly installment auto-debit",
            date=(now - timedelta(days=31)).strftime("%Y-%m-%d %H:%M:%S UTC"),
        ),
        Transaction(
            transaction_id="TXN-962190",
            customer_id=customer_id,
            account_id="PAYTM-WLT-001",
            amount=1200.00,
            type="upi_payment",
            status="success",
            description="Sample merchant payment via Paytm UPI",
            date=(now - timedelta(days=35)).strftime("%Y-%m-%d %H:%M:%S UTC"),
        ),
        Transaction(
            transaction_id="TXN-950811",
            customer_id=customer_id,
            account_id="PAYTM-LN-8812",
            amount=4500.00,
            type="emi_debit",
            status="success",
            description="Sample loan EMI monthly installment auto-debit",
            date=(now - timedelta(days=61)).strftime("%Y-%m-%d %H:%M:%S UTC"),
        ),
    ]

    return txns
