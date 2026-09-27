"""Dealer and workshop service operations tools."""

import random
from typing import Any, Dict


def get_dealer_details(dealer_code: str = "DLR-901") -> Dict[str, Any]:
    """Look up dealership franchise details, workshop manager, and contact numbers."""
    dealers = {
        "DLR-901": {
            "name": "Apex Motors Dealership & Service Center",
            "city": "Gurugram",
            "service_manager": "Anil Sharma",
            "phone": "+91-124-5550199",
            "rating": 4.8,
            "address": "Plot 12, Sector 29",
        },
        "DLR-502": {
            "name": "Grand Star Auto Services",
            "city": "Mumbai",
            "service_manager": "Pooja Mehta",
            "phone": "+91-22-4440288",
            "rating": 4.7,
            "address": "Andheri East Link Road",
        },
    }
    return dealers.get(
        dealer_code.upper(),
        {
            "dealer_code": dealer_code,
            "name": "Authorized Regional Dealership",
            "city": "Regional Hub",
            "phone": "1800-DEALER-CARE",
        },
    )


def get_customer_details(customer_id: str = "CUST-007") -> Dict[str, Any]:
    """Retrieve customer vehicle profile and service record."""
    return {
        "customer_id": customer_id,
        "name": "Vikram Malhotra",
        "vehicle_model": "Sedan Prime SX 2024",
        "vin": "MB12X9827364",
        "last_service_date": "2026-03-10",
        "odometer_km": 18450,
        "preferred_dealer": "Apex Motors Dealership & Service Center (DLR-901)",
    }


def get_service_status(job_card_id: str = "JC-7711") -> Dict[str, Any]:
    """Retrieve live status of vehicle in workshop."""
    return {
        "job_card_id": job_card_id,
        "vehicle": "Sedan Prime SX (HR26-DF-4402)",
        "service_stage": "Quality Inspection & Washing",
        "technician": "Suresh Verma",
        "estimated_completion_time": "Today, 5:30 PM",
        "bill_estimate_inr": 8200.0,
        "parts_replaced": ["Engine Oil", "Oil Filter", "Cabin Air Filter"],
    }


def create_dealer_request(dealer_code: str, issue_description: str, priority: str = "normal") -> Dict[str, Any]:
    """Create dealer escalation or parts replenishment ticket."""
    ticket_id = f"DTK-{random.randint(10000, 99999)}"
    return {
        "ticket_id": ticket_id,
        "dealer_code": dealer_code,
        "issue_description": issue_description,
        "priority": priority,
        "status": "ticket_logged_for_zonal_lead",
    }


def record_customer_feedback(session_id: str, rating: int, comments: str = "") -> Dict[str, Any]:
    """Store customer satisfaction feedback."""
    return {
        "session_id": session_id,
        "rating": rating,
        "comments": comments,
        "status": "feedback_recorded_successfully",
    }
