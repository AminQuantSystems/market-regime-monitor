# Gated demonstration

Market Regime Monitor can be published as one container with individually issued, expiring access. This is a controlled demonstration. It is not a client portal.

## Purpose

Give an investment or capital-markets professional a short interactive look at the released application, and give MEEM a simple way to withdraw that access. The finance methodology is unchanged.

## Architecture

The finance package in `src/market_state` does not know about invitations, cookies, or Azure.

The adapter in `app/api/access` does four things:

- checks a signed invitation
- sets an HttpOnly session cookie
- refuses analytical requests that do not have a valid session when access control is enabled
- counts analysis attempts for the current process

In production the same FastAPI process serves the compiled Vite application. Local development still uses Vite on port 5173 and FastAPI on port 8000, with access control off unless the environment says otherwise.

## Invitation lifecycle

1. An operator creates one link with `scripts/create_demo_invite.py`.
2. The prospect opens the link. The token is in the URL fragment, `#token=`, so it is not sent to the server in the request line.
3. The access page posts the token to `POST /api/v1/auth/exchange`.
4. A valid token sets the `meem_demo_session` cookie and the page moves the browser to `/`.
5. The fragment is removed from the address bar. The token is not written to `localStorage` or `sessionStorage`.
6. The cookie expires no later than the invitation.
7. End Demo Session clears the cookie and returns to `/access`.

## Token format

The token is `base64url(canonical JSON)` + `.` + `base64url(HMAC-SHA256)`.

The JSON contains only:

- `v`: token version, currently 1
- `jti`: a random invitation identifier
- `exp`: a Unix expiry time

It does not contain a name, email address, organisation, role, or any client information. The signature is checked with `hmac.compare_digest`.

The default lifetime is 14 days. The server rejects a lifetime above 30 days even if a token was signed for longer.

## Revocation

Set `MEEM_DEMO_REVOKED_JTIS` to a comma-separated list of invitation identifiers and restart or redeploy the container. A matching `jti` is refused. Expiry still applies to every invitation that is not listed.

The creation script prints the invitation identifier. Record it when the link is issued.

To invalidate every outstanding invitation, replace `MEEM_DEMO_SIGNING_KEY` with a new value from `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Do not commit that value, and do not put it in a report or a repository file. Update the Azure Container Apps secret and restart the app. Old tokens stop validating immediately.

## Session cookie

The cookie name is `meem_demo_session`. In production it is `HttpOnly`, `Secure`, `SameSite=Lax`, and `Path=/`. The cookie value is the signed invitation, so validation does not need a database. Logging out deletes it.

## Rate limit

Each invitation may make 30 analysis attempts per rolling hour. Demo and CSV analyses share that limit. The thirty-first attempt returns HTTP 429 and `DEMO_RATE_LIMIT_EXCEEDED`, with a `Retry-After` header.

The counter lives in the container process. It is acceptable for the first demonstration because the container is limited to one replica. The counter can reset when the container scales to zero and starts again. It is abuse protection, not a contractual meter. It is not Redis, and it is not a database.

Uploaded CSV results are not cached. The fixed synthetic demonstration is also calculated on each request by the existing finance path.

## Create an invitation

Set the same signing key that the running demonstration uses, then:

```text
python scripts/create_demo_invite.py --base-url https://<demo-host> --days 14
```

The key is read from `MEEM_DEMO_SIGNING_KEY`. The script does not accept the key as an argument and it does not print the key. It prints the invitation identifier, the UTC expiry, and one fragment link.

## Revoke one invitation

Add its printed identifier to `MEEM_DEMO_REVOKED_JTIS` and redeploy or restart so the process sees the new value.

## Local development

Access control defaults to off. The usual Vite and FastAPI processes are unchanged, so the local board can be used without an invitation.

To exercise the gate locally, set:

```text
MEEM_DEMO_ACCESS_REQUIRED=1
MEEM_DEMO_SIGNING_KEY=<a local key from secrets.token_urlsafe(48)>
MEEM_DEMO_COOKIE_SECURE=0
MEEM_DEMO_CONTACT_EMAIL=<address supplied for the exercise>
```

`MEEM_DEMO_COOKIE_SECURE` stays `0` on plain HTTP. If access control is on and the key is missing or shorter than a 32-byte `token_urlsafe` value, the process refuses to start.

## Production

```text
MEEM_SERVE_FRONTEND=1
MEEM_DEMO_ACCESS_REQUIRED=1
MEEM_DEMO_COOKIE_SECURE=1
MEEM_DEMO_ANALYSE_LIMIT_PER_HOUR=30
MEEM_DEMO_REVOKED_JTIS=
MEEM_DEMO_CONTACT_EMAIL=<owner-supplied public address>
MEEM_DEMO_SIGNING_KEY=<secret reference>
```

`MEEM_SERVE_FRONTEND=1` serves the compiled Vite files from FastAPI. API routes stay ahead of the application shell. `/access`, `/healthz`, the invitation exchange, the public contact endpoint, and the compiled assets remain reachable without a session. `/` and `POST /api/v1/market-regime/analyse` do not.

If `MEEM_DEMO_CONTACT_EMAIL` is empty, the access page says "Contact MEEM Technologies to request demonstration access." and does not show a mailto link.

## Azure shape

One resource group, one Container Apps environment, and one Container App. Consumption workload, UK South, 0.25 vCPU, 0.5 GiB memory, minimum 0 replicas, maximum 1 replica. Ingress is external on port 8000. Logs are not shipped to Log Analytics. There is no separate registry, database, key vault, virtual network, or application gateway in this phase. The image is published to GitHub Container Registry, not Azure Container Registry.

`GET /healthz` only reports that the process is up. It does not run a finance calculation.

## Data warning

The CSV screen says: "Public demonstration — do not upload confidential, personal or client data." The existing 5 MiB server-side limit remains. This deployment does not claim to be an encrypted client portal, a confidential-processing environment, or a regulated retention service.

## What this is not

- client authentication
- user accounts
- passwords
- permanent credentials
- a regulated client portal
- a confidential data environment
- live market data
