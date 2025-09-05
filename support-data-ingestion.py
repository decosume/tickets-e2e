import os
import re
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Slack config
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

# Zendesk config
ZENDESK_SUBDOMAIN = os.getenv("ZENDESK_SUBDOMAIN")
ZENDESK_EMAIL = os.getenv("ZENDESK_EMAIL")
ZENDESK_API_TOKEN = os.getenv("ZENDESK_API_TOKEN")

# Shortcut config
SHORTCUT_API_TOKEN = os.getenv("SHORTCUT_API_TOKEN")


# ==============================
# DynamoDB (Stub)
# ==============================
def upsert_bug_item(ticket_id, source, attributes):
    """
    Stub for DynamoDB upsert (replace with boto3 put_item).
    """
    print(f"📝 Upserting [{ticket_id}] from [{source}] → {attributes}")


# ==============================
# Slack Functions
# ==============================
def extract_ticket_info_from_slack(text):
    """Extract ticketId and priority if available, fallback if not."""
    ticket_pattern = re.search(r"ticketId[:=]\s*(\S+)", text, re.IGNORECASE)
    priority_pattern = re.search(r"priority[:=]\s*(\S+)", text, re.IGNORECASE)

    ticket_id = ticket_pattern.group(1) if ticket_pattern else f"GENERIC-{hash(text)}"
    priority = priority_pattern.group(1).capitalize() if priority_pattern else "Unknown"

    return ticket_id, priority


def fetch_slack_messages():
    """Fetch Slack messages and normalize into bug records."""
    try:
        url = "https://slack.com/api/conversations.history"
        headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
        params = {"channel": SLACK_CHANNEL_ID, "limit": 50}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        messages = data.get("messages", []) if data.get("ok") else []
        results = []

        for msg in messages:
            text = msg.get("text", "")
            ticket_id, priority = extract_ticket_info_from_slack(text)

            bug_data = {
                "author": msg.get("user", "unknown"),
                "text": text,
                "priority": priority,
                "slack_msg_id": msg.get("ts"),
                "created_at": datetime.fromtimestamp(float(msg["ts"])).isoformat(),
                "source_system": "slack"
            }
            upsert_bug_item(ticket_id, "slack", bug_data)
            results.append((ticket_id, bug_data))

        return results

    except Exception as e:
        print(f"❌ Error fetching Slack messages: {str(e)}")
        return []


# ==============================
# Zendesk Functions
# ==============================
def fetch_zendesk_tickets():
    """Fetch Zendesk tickets and normalize into bug records."""
    try:
        url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/tickets.json"
        auth = (f"{ZENDESK_EMAIL}/token", ZENDESK_API_TOKEN)
        response = requests.get(url, auth=auth, timeout=10)
        response.raise_for_status()

        data = response.json()
        tickets = data.get("tickets", [])
        results = []

        for t in tickets:
            if "bug" not in (t.get("tags") or []):  # filter only bug tickets
                continue

            ticket_id = f"ZD-{t['id']}"
            bug_data = {
                "requester": t.get("requester_id"),
                "assignee": t.get("assignee_id"),
                "priority": t.get("priority"),
                "status": t.get("status"),
                "subject": t.get("subject"),
                "created_at": t.get("created_at"),
                "updated_at": t.get("updated_at"),
                "source_system": "zendesk"
            }
            upsert_bug_item(ticket_id, "zendesk", bug_data)
            results.append((ticket_id, bug_data))

        return results

    except Exception as e:
        print(f"❌ Error fetching Zendesk tickets: {str(e)}")
        return []


# ==============================
# Shortcut Functions
# ==============================
def fetch_shortcut_bugs():
    """Fetch Shortcut open bugs using Search API."""
    try:
        query = (
            "type:bug "
            "(workflow_state_id:500000027 OR workflow_state_id:500000043 "
            "OR workflow_state_id:500000385 OR workflow_state_id:500003719 OR workflow_state_id:500009065) "
            "-state:Complete"
        )

        url = "https://api.app.shortcut.com/api/v3/search/stories"
        headers = {"Shortcut-Token": SHORTCUT_API_TOKEN}
        params = {"query": query, "page_size": 25}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        bugs = data.get("data", [])
        results = []

        for bug in bugs:
            ticket_id = None
            if bug.get("name") and "ZD-" in bug["name"]:  # try to extract Zendesk ID
                match = re.search(r"(ZD-\d+)", bug["name"])
                if match:
                    ticket_id = match.group(1)

            if not ticket_id:
                ticket_id = f"SC-{bug['id']}"

            bug_data = {
                "shortcut_story_id": bug["id"],
                "name": bug.get("name"),
                "state": bug.get("workflow_state_id"),
                "created_at": bug.get("created_at"),
                "updated_at": bug.get("updated_at"),
                "completed": bug.get("completed"),
                "archived": bug.get("archived"),
                "source_system": "shortcut"
            }
            upsert_bug_item(ticket_id, "shortcut", bug_data)
            results.append((ticket_id, bug_data))

        return results

    except Exception as e:
        print(f"❌ Error fetching Shortcut bugs: {str(e)}")
        return []


# ==============================
# Main
# ==============================
def main():
    print("=== Starting Bug Ingestion ===")

    print("\n📥 Fetching Slack data...")
    slack_records = fetch_slack_messages()
    print(f"✅ {len(slack_records)} Slack records processed")

    print("\n📥 Fetching Zendesk tickets...")
    zendesk_records = fetch_zendesk_tickets()
    print(f"✅ {len(zendesk_records)} Zendesk records processed")

    print("\n📥 Fetching Shortcut bugs...")
    shortcut_records = fetch_shortcut_bugs()
    print(f"✅ {len(shortcut_records)} Shortcut records processed")

    print("\n🎯 Ingestion complete.")


if __name__ == "__main__":
    main()
