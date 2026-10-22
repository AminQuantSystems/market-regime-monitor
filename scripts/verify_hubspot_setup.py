"""Confirm the demonstration properties exist. This script does not create them."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.hubapi.com/crm/properties/2026-09/contacts"
EXPECTED = {
    "meem_demo_status": {
        "type": "enumeration",
        "options": {"REQUESTED", "EMAIL_VERIFICATION_SENT", "EMAIL_FAILED", "ACCESS_GRANTED", "EXPIRED", "REVOKED"},
    },
    "meem_demo_requested_at": {"type": "datetime", "options": None},
    "meem_demo_verified_at": {"type": "datetime", "options": None},
    "meem_demo_access_expires_at": {"type": "datetime", "options": None},
    "meem_demo_request_id": {"type": "string", "options": None},
    "meem_demo_verification_jti": {"type": "string", "options": None},
    "meem_demo_access_jti": {"type": "string", "options": None},
    "meem_demo_interest": {"type": "string", "options": None},
}


def main() -> int:
    key = os.environ.get("HUBSPOT_SERVICE_KEY", "").strip()
    if not key:
        print("HUBSPOT_SERVICE_KEY is not set. No request was made.", file=sys.stderr)
        return 2
    request = urllib.request.Request(API, headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            print(
                "Property definitions could not be read. The running application does not need schema access. "
                "This check needs the read scope crm.schemas.contacts.read. Do not add schema write.",
                file=sys.stderr,
            )
            return 3
        print(f"HubSpot property check failed with status {exc.code}.", file=sys.stderr)
        return 1
    results = payload.get("results") or []
    custom = [item for item in results if item.get("hubspotDefined") is False]
    by_name = {item.get("name"): item for item in results}
    missing: list[str] = []
    for name, expected in EXPECTED.items():
        found = by_name.get(name)
        if found is None or found.get("type") != expected["type"]:
            missing.append(name)
            continue
        if expected["options"] is not None:
            values = {option.get("value") for option in found.get("options") or []}
            if not expected["options"] <= values:
                missing.append(name)
    print(f"Custom contact properties: {len(custom)}")
    print("Free-tier planning figure used by this project: 10 custom properties in total.")
    print(f"Contact properties still unnamed in that figure: {max(0, 10 - len(custom))}")
    if missing:
        print("Missing or incorrect: " + ", ".join(missing), file=sys.stderr)
        return 1
    print("Required demonstration properties are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
