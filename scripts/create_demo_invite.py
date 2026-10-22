"""Operator tool for a single expiring demonstration invitation.

The signing key is read from MEEM_DEMO_SIGNING_KEY. It is never accepted as an
argument and it is never printed.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.access.settings import key_is_strong
from app.api.access.tokens import MAX_INVITATION_DAYS, InvitationError, issue_invitation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create one Market Regime Monitor demonstration invitation.")
    parser.add_argument("--base-url", required=True, help="Public demonstration origin, without a path.")
    parser.add_argument("--days", type=int, default=14, help="Lifetime in days, from 1 to 30. The default is 14.")
    args = parser.parse_args(argv)
    key = os.environ.get("MEEM_DEMO_SIGNING_KEY", "")
    if not key_is_strong(key):
        print("MEEM_DEMO_SIGNING_KEY is missing or too weak. No invitation was created.", file=sys.stderr)
        return 2
    if args.days < 1 or args.days > MAX_INVITATION_DAYS:
        print(f"Invitation duration must be from 1 to {MAX_INVITATION_DAYS} days.", file=sys.stderr)
        return 2
    try:
        token, invitation_id, expires_at = issue_invitation(key, days=args.days)
    except (InvitationError, ValueError):
        print("The invitation could not be created.", file=sys.stderr)
        return 2
    expires = datetime.fromtimestamp(expires_at, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    link = args.base_url.rstrip("/") + "/access#token=" + token
    print(f"Invite ID: {invitation_id}")
    print(f"Expires: {expires}")
    print(f"Link: {link}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
