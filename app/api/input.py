"""Transport parsing for the analyse request. Finance validation stays in market_state."""

from __future__ import annotations

import csv
import json
import re
from io import StringIO
from pathlib import Path

import pandas as pd
from fastapi import UploadFile

from app.api.errors import APIError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
_DATE_TEXT = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NUMBER_TEXT = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")
_ALLOWED_MEDIA = {
    "",
    "text/csv",
    "application/csv",
    "text/plain",
    "application/vnd.ms-excel",
    "application/octet-stream",
}
_DEMO_DIR = Path(__file__).resolve().parents[1] / "demo"
DEMO_CSV = _DEMO_DIR / "v1_market_data.csv"
DEMO_METADATA = _DEMO_DIR / "metadata.json"


def require_iso_date(value: str, field_name: str) -> str:
    if not isinstance(value, str) or _DATE_TEXT.fullmatch(value) is None:
        raise APIError(400, "API_INVALID_DATE_FORMAT", f"{field_name} must be YYYY-MM-DD")
    return value


def load_demo_metadata() -> dict:
    return json.loads(DEMO_METADATA.read_text(encoding="utf-8"))


def load_demo_csv() -> pd.DataFrame:
    return parse_csv_text(DEMO_CSV.read_text(encoding="utf-8"))


async def read_upload(upload: UploadFile | None) -> pd.DataFrame:
    if upload is None:
        raise APIError(400, "API_FILE_REQUIRED", "An upload requires a prices CSV")
    media = (upload.content_type or "").split(";", 1)[0].strip().lower()
    if media not in _ALLOWED_MEDIA:
        raise APIError(415, "API_UNSUPPORTED_MEDIA_TYPE", f"Unsupported content type: {media}")
    raw = await _read_limited(upload)
    if b"\x00" in raw:
        raise APIError(400, "API_INVALID_CSV", "Uploaded content is not a CSV text file")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise APIError(400, "API_INVALID_UTF8", "Uploaded CSV must be UTF-8") from None
    return parse_csv_text(text)


async def _read_limited(upload: UploadFile) -> bytes:
    remaining = MAX_UPLOAD_BYTES + 1
    chunks: list[bytes] = []
    while remaining:
        block = await upload.read(remaining)
        if not block:
            break
        chunks.append(block)
        remaining -= len(block)
    payload = b"".join(chunks)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise APIError(413, "API_FILE_TOO_LARGE", "Uploaded CSV exceeds 5 MiB")
    return payload


def parse_csv_text(text: str) -> pd.DataFrame:
    """Turn CSV text into a frame without trimming, filling, or dropping rows."""
    if text == "":
        raise APIError(400, "API_INVALID_CSV", "Uploaded CSV is empty")
    try:
        rows = list(csv.reader(StringIO(text, newline="")))
    except csv.Error as exc:
        raise APIError(400, "API_INVALID_CSV", "Uploaded CSV could not be parsed") from exc
    if not rows:
        raise APIError(400, "API_INVALID_CSV", "Uploaded CSV has no header")
    header = rows[0]
    records = []
    for row in rows[1:]:
        if len(row) != len(header):
            raise APIError(400, "API_INVALID_CSV", "Uploaded CSV has a row that does not match the header")
        records.append({column: _price_cell(column, value) for column, value in zip(header, row, strict=True)})
    return pd.DataFrame(records, columns=header)


def _price_cell(column: str, value: str) -> object:
    if column != "adjusted_close":
        return value
    if value == "":
        return ""
    if _NUMBER_TEXT.fullmatch(value) is None:
        return value
    return float(value)
