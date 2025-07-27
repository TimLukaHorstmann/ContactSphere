# Script to fetch LinkedIn connections using the LinkedIn API
# https://learn.microsoft.com/en-us/linkedin/dma/member-data-portability/member-data-portability-member/?view=li-dma-data-portability-2025-05

# --> only possible for LinkedIn members in the EEA and Switzerland!

import requests
from dotenv import load_dotenv
import os

# ─────────── Load env ───────────
load_dotenv()  # will read .env in the current working directory
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
if not LINKEDIN_ACCESS_TOKEN:
    raise RuntimeError("⚠️ LINKEDIN_ACCESS_TOKEN not found in .env")


# ─── your config ───
API_VERSION  = "202312"
BASE_URL     = "https://api.linkedin.com/rest"
HEADERS = {
    "Authorization":    f"Bearer {LINKEDIN_ACCESS_TOKEN}",
    "LinkedIn-Version": API_VERSION,
    "Content-Type":     "application/json",
}
# ────────────────────

def fetch_connections_page(start=0, count=50):
    """
    Returns the CONNECTIONS snapshot block,
    whose 'elements' key is a list of your connection-dicts.
    """
    resp = requests.get(
        f"{BASE_URL}/memberSnapshotData",
        headers=HEADERS,
        params={
            "q":      "criteria",      # literal
            "domain": "CONNECTIONS",   # 1st-degree connections
            "start":  start,
            "count":  count,
        }
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    data = fetch_connections_page()

    # this is your list of connection-dicts:
    snapshot_data = data.get("elements", [])

    print(snapshot_data)  # debug: print raw data

    # save connections to a file (optional)
    with open("connections.json", "w") as f:
        import json
        json.dump(snapshot_data, f, indent=2)

    connections = snapshot_data[0].get("snapshotData", [])

    print(f"✅ Retrieved {len(connections)} connections:\n")
    for c in connections:
        print(
            f"{c['First Name']} {c['Last Name']} | "
            f"{c.get('Company','–')} | {c.get('Position','–')} | "
            f"Connected: {c.get('Connected On','–')} | "
            f"Email: {c.get('Email Address','–') or '–'} | "
            f"{c['URL']}"
        )

        for key, value in c.items():
            print(f"{key}: {value}")

        print("-" * 80)