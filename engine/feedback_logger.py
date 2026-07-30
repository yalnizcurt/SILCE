import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("SILCE.FeedbackLogger")

# In-memory analytics store for real-time dashboard simulation
analytics_store = {
    "impressions": 1240,
    "accepts": 384,
    "dismissals": 92,
    "checkouts_with_silce": 1180,
    "total_mac_users": 5000,
    "users_with_new_category": 1620,
    "baseline_mac_new_cat_percent": 18.5, # Historical baseline %
    "checkout_abandonments_control": 4.2, # Control group %
    "checkout_abandonments_silce": 4.1,   # SILCE group % (Guardrail maintained)
    "avg_checkout_time_sec": 42.0,
    "events_log": []
}

def log_event(event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Logs an impression, accept, dismiss, or checkout event.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    event_entry = {
        "timestamp": timestamp,
        "event_type": event_type,
        "data": data
    }
    analytics_store["events_log"].insert(0, event_entry)
    # Keep only last 50 events in log memory
    if len(analytics_store["events_log"]) > 50:
        analytics_store["events_log"].pop()

    if event_type == "impression":
        analytics_store["impressions"] += 1
    elif event_type == "accept":
        analytics_store["accepts"] += 1
        analytics_store["users_with_new_category"] += 1
    elif event_type == "dismiss":
        analytics_store["dismissals"] += 1
    elif event_type == "checkout":
        analytics_store["checkouts_with_silce"] += 1

    return get_analytics_summary()

def get_analytics_summary() -> Dict[str, Any]:
    """
    Computes current metrics and guardrail performance statistics.
    """
    impressions = analytics_store["impressions"]
    accepts = analytics_store["accepts"]
    dismissals = analytics_store["dismissals"]
    total_mac = analytics_store["total_mac_users"]
    new_cat_users = analytics_store["users_with_new_category"]

    acceptance_rate = round((accepts / impressions * 100), 1) if impressions > 0 else 0.0
    dismissal_rate = round((dismissals / impressions * 100), 1) if impressions > 0 else 0.0
    category_expansion_mac_percent = round((new_cat_users / total_mac * 100), 1)

    return {
        "primary_metric": {
            "name": "Monthly Active Customers Purchasing New Categories",
            "current_value": f"{category_expansion_mac_percent}%",
            "baseline_value": f"{analytics_store['baseline_mac_new_cat_percent']}%",
            "relative_lift": f"+{round(category_expansion_mac_percent - analytics_store['baseline_mac_new_cat_percent'], 1)}%",
            "target": "28.0%"
        },
        "secondary_metrics": {
            "acceptance_rate": f"{acceptance_rate}%",
            "impressions_total": impressions,
            "accepts_total": accepts,
            "dismissals_total": dismissals
        },
        "guardrail_metrics": {
            "checkout_completion_rate": "95.9%",
            "checkout_abandonment": f"{analytics_store['checkout_abandonments_silce']}% (Control: {analytics_store['checkout_abandonments_control']}%)",
            "avg_checkout_time": f"{analytics_store['avg_checkout_time_sec']}s (No delay introduced)",
            "dismissal_rate": f"{dismissal_rate}%"
        },
        "recent_events": analytics_store["events_log"][:10]
    }
