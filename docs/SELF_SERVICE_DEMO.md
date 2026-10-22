# Self-service demonstration

A visitor can request access, verify an email address, and open Market Regime Monitor without an operator creating the invitation. The signed invitation mechanism remains the operator fallback.

This is not a user-account system. There is no password, no database, and no marketing list.

## Flow

1. `POST /api/v1/demo-access/request` validates the form.
2. A hidden honeypot field that contains text returns the same success response and does nothing else.
3. The contact and company are written to HubSpot.
4. A verification link is emailed. The token is in the URL fragment `#verify=`, not the query string.
5. `POST /api/v1/demo-access/verify` checks the signature, purpose, expiry, request id, and the single-use verification id stored in HubSpot.
6. A normal 14-day demonstration session cookie is set. The long-lived token is not emailed.
7. When `MEEM_DEMO_OWNER_EMAIL` is set, a short lead summary is sent. If that send fails, the visitor still has access.

Manual invitations from `scripts/create_demo_invite.py` continue to work through `#token=`.

## Tokens

The verification payload is `v`, `purpose` (`email_verify`), `request_id`, `jti`, and `exp`. It does not contain a name, email address, organisation, role, or interest. The lifetime is 30 minutes. A token whose expiry is more than 60 minutes ahead is rejected. A consumed verification id cannot grant another session.

The session cookie remains `meem_demo_session`: HttpOnly, Secure in production, SameSite=Lax. Logout is unchanged.

## Limits

These process-local limits reset when the single replica restarts, including scale-to-zero:

- 5 demonstration requests an hour for one client address
- 50 verification emails in a rolling day

The per-address cooldown is 10 minutes. It uses the process memory and the `meem_demo_requested_at` value in HubSpot, so a restart does not immediately allow another message to the same address. The daily email ceiling is process-local and is not durable. Azure’s own sending limits are a further ceiling. None of this is contractual metering. There is no Redis and no database.

Analysis remains limited to 30 attempts an hour for each granted invitation.

## Configuration

Local development can leave the new integrations unset. The public form then returns a controlled unavailable response and does not grant access.

Production adds:

```text
HUBSPOT_SERVICE_KEY
AZURE_COMMUNICATION_CONNECTION_STRING
AZURE_EMAIL_SENDER
MEEM_DEMO_PUBLIC_BASE_URL
MEEM_DEMO_REQUEST_LIMIT_PER_HOUR=5
MEEM_DEMO_VERIFICATION_COOLDOWN_MINUTES=10
MEEM_DEMO_EMAIL_DAILY_LIMIT=50
MEEM_DEMO_OWNER_EMAIL
```

`MEEM_DEMO_OWNER_EMAIL` is optional. The public base URL is the external `https` origin used inside verification links.

## What is still not provided

No client authentication, user accounts, permanent credentials, regulated client portal, confidential data environment, or live market data. The finance methodology is unchanged.
