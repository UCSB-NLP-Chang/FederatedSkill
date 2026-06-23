#!/usr/bin/env python3
"""Deduplicate alert packs by (type, key_identifiers), keeping first occurrence."""

import json
import sys
from collections import OrderedDict


def get_dedup_key(alert):
    """Generate deduplication key for an alert."""
    alert_type = alert.get("type", "")
    
    if alert_type == "issuer_top_holders":
        return (alert_type, alert.get("issuer_query", ""), alert.get("quarter", ""))
    elif alert_type == "fund_change":
        return (alert_type, alert.get("fund_query", ""), 
                alert.get("quarter_current", ""), alert.get("quarter_baseline", ""))
    elif alert_type == "ignore_me":
        return None  # Will be filtered out
    else:
        return (alert_type, json.dumps(alert, sort_keys=True))


def dedupe_alerts(alerts):
    """Deduplicate alerts, keeping first occurrence of each key."""
    seen = OrderedDict()
    filtered = []
    
    for alert in alerts:
        key = get_dedup_key(alert)
        
        if key is None:
            # Skip ignore_me alerts
            continue
            
        if key not in seen:
            seen[key] = True
            filtered.append(alert)
    
    return filtered


def group_by_type(alerts):
    """Group alerts by their type field."""
    groups = {}
    for alert in alerts:
        alert_type = alert.get("type", "unknown")
        if alert_type not in groups:
            groups[alert_type] = []
        groups[alert_type].append(alert)
    return groups


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: dedupe_alerts.py <alerts.json>", file=sys.stderr)
        sys.exit(1)
    
    with open(sys.argv[1], 'r') as f:
        alerts = json.load(f)
    
    deduped = dedupe_alerts(alerts)
    grouped = group_by_type(deduped)
    
    print(json.dumps({
        "deduped_count": len(deduped),
        "original_count": len(alerts),
        "by_type": {k: len(v) for k, v in grouped.items()},
        "alerts": deduped
    }, indent=2))