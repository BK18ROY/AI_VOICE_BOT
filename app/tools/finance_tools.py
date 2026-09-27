"""Simulated customer vehicle finance and loan support tools."""

from typing import Any, Dict


def get_payment_status(transaction_id: str = "TXN-8812") -> Dict[str, Any]:
    """Retrieve simulated payment clearance status."""
    return {
        "transaction_id": transaction_id,
        "status": "success",
        "amount_inr": 24500.0,
        "payment_date": "2026-09-15",
        "payment_mode": "Auto-Debit / NACH",
        "description": "Monthly EMI installment cleared successfully",
    }


def get_loan_status(loan_account_number: str = "LN-4412") -> Dict[str, Any]:
    """Retrieve active auto loan status and remaining balance."""
    return {
        "loan_account_number": loan_account_number,
        "status": "active_in_good_standing",
        "sanctioned_amount_inr": 1200000.0,
        "principal_outstanding_inr": 485000.0,
        "tenure_months": 60,
        "tenure_completed_months": 36,
        "interest_rate_percent": 8.75,
    }


def get_emi_details(account_id: str = "ACC-101") -> Dict[str, Any]:
    """Retrieve upcoming EMI installment schedule and due dates."""
    return {
        "account_id": account_id,
        "monthly_emi_amount_inr": 24500.0,
        "next_due_date": "2026-10-05",
        "autopay_status": "enabled",
        "bank_name": "HDFC Bank Ltd.",
        "overdue_penalty": 0.0,
    }


def get_account_summary(customer_id: str = "CUST-007") -> Dict[str, Any]:
    """Retrieve high-level finance customer summary."""
    return {
        "customer_id": customer_id,
        "customer_name": "Vikram Malhotra",
        "active_loans": 1,
        "total_borrowed_inr": 1200000.0,
        "credit_rating": "Tier 1 Prime",
        "pre_approved_topup_inr": 250000.0,
    }
