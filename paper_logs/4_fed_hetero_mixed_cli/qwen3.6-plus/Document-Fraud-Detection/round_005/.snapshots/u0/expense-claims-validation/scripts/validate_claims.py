#!/usr/bin/env python3
"""
Template for validating expense claims against reference data.
Handles fuzzy name matching and multi-field cross-validation.
"""

import json
import re
import sys
from typing import Dict, List, Optional, Tuple

import pdfplumber
import pandas as pd
from Levenshtein import ratio as levenshtein_ratio


VALIDATION_CONFIG = {
    "employees_path": "/path/to/employee_directory.xlsx",
    "trips_path": "/path/to/trip_approvals.csv",
    "claims_pdf_path": "/path/to/claims.pdf",
    "output_path": "/path/to/alerts.json",
    "fuzzy_threshold": 0.90,
    "amount_tolerance": 0.01,
    "name_field": "employee_name",
    "id_field": "employee_id",
    "account_field": "bank_account",
}


def load_reference_data(config: dict) -> Tuple[pd.DataFrame, pd.DataFrame, Dict, Dict]:
    """Load employee and trip data, build lookup indexes."""
    # Detect file type and load
    emp_path = config["employees_path"]
    if emp_path.endswith('.xlsx'):
        employees = pd.read_excel(emp_path)
    else:
        employees = pd.read_csv(emp_path)
    
    trips = pd.read_csv(config["trips_path"])
    
    # Build indexes
    emp_by_name = {}
    for _, row in employees.iterrows():
        key = str(row[config["name_field"]]).strip().lower()
        emp_by_name[key] = row.to_dict()
    
    trips_by_id = {}
    for _, row in trips.iterrows():
        trips_by_id[str(row["trip_id"]).strip()] = row.to_dict()
    
    return employees, trips, emp_by_name, trips_by_id


def find_best_employee_match(
    claim_name: str, 
    emp_by_name: Dict, 
    threshold: float = 0.90
) -> Tuple[Optional[Dict], float]:
    """
    Find best employee match using Levenshtein ratio.
    Returns (employee_record, similarity_score) or (None, 0.0).
    """
    claim_norm = claim_name.strip().lower()
    best_match = None
    best_score = 0.0
    
    for name, record in emp_by_name.items():
        score = levenshtein_ratio(claim_norm, name)
        if score > best_score:
            best_score = score
            best_match = record
    
    if best_score >= threshold:
        return best_match, best_score
    return None, best_score


def parse_claim_page(page_text: str) -> Optional[Dict]:
    """Extract claim fields from page text using regex."""
    patterns = {
        "employee_name": r'Employee:\s*(.+?)(?:\n|$)',
        "department": r'Department:\s*(.+?)(?:\n|$)',
        "bank_account": r'Bank Account:\s*(\S+)',
        "trip_id": r'Trip ID:\s*(\S+)',
        "claim_total": r'Claim Total:\s*\$?([0-9,]+\.?\d*)',
    }
    
    result = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            if field == "claim_total":
                val = float(re.sub(r'[,]', '', val))
            result[field] = val
    
    return result if result else None


def validate_claim(
    claim: Dict, 
    emp_by_name: Dict, 
    trips_by_id: Dict, 
    config: dict
) -> Tuple[bool, str, Optional[Dict]]:
    """
    Validate claim against reference data.
    Returns (is_valid, reason_code, matched_employee_or_none).
    """
    threshold = config["fuzzy_threshold"]
    tolerance = config["amount_tolerance"]
    
    # 1. Employee existence (fuzzy match)
    emp_name = claim.get("employee_name", "")
    matched_emp, score = find_best_employee_match(emp_name, emp_by_name, threshold)
    
    if matched_emp is None:
        return False, "Unknown Employee", None
    
    # 2. Trip existence
    trip_id = claim.get("trip_id", "")
    if trip_id not in trips_by_id:
        return False, "Invalid Trip ID", matched_emp
    
    trip = trips_by_id[trip_id]
    
    # 3. Traveler match (does trip belong to this employee?)
    if trip.get("employee_id") != matched_emp.get(config["id_field"]):
        return False, "Traveler Mismatch", matched_emp
    
    # 4. Bank account match
    claimed_acct = claim.get("bank_account", "")
    expected_acct = matched_emp.get(config["account_field"], "")
    if claimed_acct != expected_acct:
        return False, "Account Mismatch", matched_emp
    
    # 5. Amount tolerance
    claimed_amt = float(claim.get("claim_total", 0))
    approved_amt = float(trip.get("approved_amount", 0))
    if abs(claimed_amt - approved_amt) > tolerance:
        return False, "Amount Mismatch", matched_emp
    
    return True, "OK", matched_emp


def process_claims_pdf(
    pdf_path: str, 
    emp_by_name: Dict, 
    trips_by_id: Dict, 
    config: dict
) -> List[Dict]:
    """Process all pages in claims PDF and return alerts."""
    alerts = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if not text:
                continue
            
            claim = parse_claim_page(text)
            if not claim:
                continue
            
            is_valid, reason, matched_emp = validate_claim(
                claim, emp_by_name, trips_by_id, config
            )
            
            if not is_valid:
                alert = {
                    "claim_page_number": page_num,
                    "employee_name": claim.get("employee_name"),
                    "claimed_amount": claim.get("claim_total"),
                    "bank_account": claim.get("bank_account"),
                    "trip_id": claim.get("trip_id"),
                    "reason": reason
                }
                alerts.append(alert)
                print(f"Page {page_num}: {claim.get('employee_name')} -> {reason}")
            else:
                print(f"Page {page_num}: {claim.get('employee_name')} -> OK")
    
    return alerts


def main():
    config = VALIDATION_CONFIG
    
    print("Loading reference data...")
    _, _, emp_by_name, trips_by_id = load_reference_data(config)
    print(f"Loaded {len(emp_by_name)} employees, {len(trips_by_id)} trips")
    
    print(f"\nProcessing claims PDF: {config['claims_pdf_path']}")
    alerts = process_claims_pdf(
        config["claims_pdf_path"], 
        emp_by_name, 
        trips_by_id, 
        config
    )
    
    # Write output
    with open(config["output_path"], 'w') as f:
        json.dump(alerts, f, indent=2)
    
    print(f"\n=== VALIDATION COMPLETE ===")
    print(f"Total alerts: {len(alerts)}")
    print(f"Output written to: {config['output_path']}")


if __name__ == "__main__":
    main()
