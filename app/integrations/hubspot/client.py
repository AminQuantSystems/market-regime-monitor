"""Bounded HubSpot CRM client. CRM API version 2026-09.

Writes send only known properties. Search and read requests may be retried once.
Creates, updates, and associations are not retried.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import httpx

API_ROOT = "https://api.hubapi.com"
API_VERSION = "2026-09"
CONTACT_PROPERTIES = (
    "email",
    "firstname",
    "lastname",
    "jobtitle",
    "meem_demo_status",
    "meem_demo_requested_at",
    "meem_demo_verified_at",
    "meem_demo_access_expires_at",
    "meem_demo_request_id",
    "meem_demo_verification_jti",
    "meem_demo_access_jti",
    "meem_demo_interest",
)

Transport = Callable[[str, str, dict[str, Any] | None], tuple[int, dict[str, Any] | None]]


class HubSpotError(Exception):
    def __init__(self, operation: str, status: int) -> None:
        self.operation = operation
        self.status = status
        super().__init__(f"HubSpot {operation} failed")


def _httpx_transport(key: str) -> Transport:
    client = httpx.Client(
        timeout=httpx.Timeout(10.0),
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )

    def send(method: str, url: str, payload: dict[str, Any] | None) -> tuple[int, dict[str, Any] | None]:
        response = client.request(method, url, json=payload)
        body: dict[str, Any] | None = None
        if response.content:
            try:
                parsed = response.json()
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                body = parsed
        return response.status_code, body

    return send


class HubSpotClient:
    def __init__(self, key: str, transport: Transport | None = None) -> None:
        self._send = transport or _httpx_transport(key)

    def _call(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
        operation: str,
        *,
        allow_missing: bool = False,
        retry: bool = False,
    ) -> dict[str, Any] | None:
        url = f"{API_ROOT}{path}"
        attempts = 2 if retry else 1
        status = 0
        body: dict[str, Any] | None = None
        for attempt in range(attempts):
            try:
                status, body = self._send(method, url, payload)
            except httpx.HTTPError:
                status, body = 0, None
            if status < 400 and status != 0:
                return body or {}
            if allow_missing and status == 404:
                return None
            if retry and attempt == 0 and status in {0, 429, 503}:
                continue
            raise HubSpotError(operation, status)
        raise HubSpotError(operation, status)

    def find_contact_by_email(self, email: str) -> dict[str, Any] | None:
        properties = "&".join(f"properties={name}" for name in CONTACT_PROPERTIES)
        encoded = quote(email, safe="")
        return self._call(
            "GET",
            f"/crm/objects/{API_VERSION}/contacts/{encoded}?idProperty=email&{properties}",
            None,
            "find_contact",
            allow_missing=True,
            retry=True,
        )

    def find_contact_by_request_id(self, request_id: str) -> dict[str, Any] | None:
        body = self._call(
            "POST",
            f"/crm/objects/{API_VERSION}/contacts/search",
            {
                "filterGroups": [
                    {"filters": [{"propertyName": "meem_demo_request_id", "operator": "EQ", "value": request_id}]}
                ],
                "limit": 1,
                "properties": list(CONTACT_PROPERTIES),
            },
            "find_request",
            retry=True,
        )
        results = (body or {}).get("results") or []
        if not results:
            return None
        return results[0]

    def create_contact(self, properties: dict[str, str]) -> dict[str, Any]:
        created = self._call(
            "POST",
            f"/crm/objects/{API_VERSION}/contacts",
            {"properties": properties},
            "create_contact",
        )
        return created or {}

    def update_contact(self, contact_id: str, properties: dict[str, str]) -> None:
        self._call(
            "PATCH",
            f"/crm/objects/{API_VERSION}/contacts/{quote(contact_id, safe='')}",
            {"properties": properties},
            "update_contact",
        )

    def find_company_by_domain(self, domain: str) -> dict[str, Any] | None:
        return self._first_company("domain", domain, "find_company_domain")

    def find_company_by_name(self, name: str) -> dict[str, Any] | None:
        return self._first_company("name", name, "find_company_name")

    def _first_company(self, property_name: str, value: str, operation: str) -> dict[str, Any] | None:
        body = self._call(
            "POST",
            f"/crm/objects/{API_VERSION}/companies/search",
            {
                "filterGroups": [{"filters": [{"propertyName": property_name, "operator": "EQ", "value": value}]}],
                "limit": 1,
                "properties": ["name", "domain"],
            },
            operation,
            retry=True,
        )
        results = (body or {}).get("results") or []
        if not results:
            return None
        return results[0]

    def create_company(self, properties: dict[str, str]) -> dict[str, Any]:
        created = self._call(
            "POST",
            f"/crm/objects/{API_VERSION}/companies",
            {"properties": properties},
            "create_company",
        )
        return created or {}

    def associate_contact_company(self, contact_id: str, company_id: str) -> None:
        self._call(
            "PUT",
            (
                f"/crm/objects/{API_VERSION}/contact/{quote(contact_id, safe='')}"
                f"/associations/default/company/{quote(company_id, safe='')}"
            ),
            None,
            "associate_contact_company",
        )

    def company_name_for_contact(self, contact_id: str) -> str:
        body = self._call(
            "GET",
            f"/crm/objects/{API_VERSION}/contacts/{quote(contact_id, safe='')}/associations/companies",
            None,
            "list_companies",
            retry=True,
        )
        results = (body or {}).get("results") or []
        if not results:
            return ""
        company_id = str(results[0].get("toObjectId") or results[0].get("id") or "")
        if not company_id:
            return ""
        company = self._call(
            "GET",
            f"/crm/objects/{API_VERSION}/companies/{quote(company_id, safe='')}?properties=name",
            None,
            "read_company",
            retry=True,
        )
        properties = (company or {}).get("properties") or {}
        return str(properties.get("name") or "")
