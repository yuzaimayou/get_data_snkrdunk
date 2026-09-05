from __future__ import annotations

import re
from typing import Any

import requests

from models import SizeListing, parse_size_listings

BASE_URL = "https://snkrdunk.com/v1/apparels"
TIMEOUT_SECONDS = 10


class SnkrdunkApiError(Exception):
    """Base exception for expected SNKRDUNK API failures."""


class InvalidProductIdError(SnkrdunkApiError):
    pass


class ProductNotFoundError(SnkrdunkApiError):
    pass


class RequestTimeoutError(SnkrdunkApiError):
    pass


class ConnectionError_(SnkrdunkApiError):
    pass


class InvalidResponseError(SnkrdunkApiError):
    pass


def validate_product_id(product_id: str) -> str:
    """Validate and normalize a product ID before putting it into the URL."""
    value = product_id.strip()
    if not value or len(value) > 100 or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise InvalidProductIdError("Invalid product ID.")
    return value


def _http_error_message(status_code: int, payload: Any) -> str:
    if status_code == 404:
        return "Product not found."

    detail = None
    if isinstance(payload, dict):
        detail = payload.get("message") or payload.get("error")

    if status_code == 400:
        return f"Bad request to SNKRDUNK API{f': {detail}' if detail else '.'}"
    if status_code == 401:
        return "SNKRDUNK rejected the request (401 Unauthorized)."
    if status_code == 403:
        return "SNKRDUNK rejected the request (403 Forbidden)."
    if status_code == 429:
        return "Too many requests. Please wait and try again."
    if 500 <= status_code <= 599:
        return f"SNKRDUNK server error ({status_code}). Please try again later."
    return f"SNKRDUNK returned HTTP {status_code}."


def fetch_size_listings(product_id: str) -> list[SizeListing]:
    """Fetch and parse size listing data for a SNKRDUNK product."""
    product_id = validate_product_id(product_id)
    url = f"{BASE_URL}/{product_id}/sizes"
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; SNKRDUNK-Price-Viewer/1.0)",
    }

    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
    except requests.Timeout as exc:
        raise RequestTimeoutError("Request timed out. Please try again.") from exc
    except requests.ConnectionError as exc:
        raise ConnectionError_("Unable to connect to SNKRDUNK.") from exc
    except requests.RequestException as exc:
        raise SnkrdunkApiError(f"Request failed: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise InvalidResponseError("Invalid response received from SNKRDUNK.") from exc

    if not response.ok:
        raise SnkrdunkApiError(_http_error_message(response.status_code, payload))

    try:
        listings = parse_size_listings(payload)
    except ValueError as exc:
        raise InvalidResponseError(str(exc)) from exc

    if not listings:
        raise SnkrdunkApiError("No listing data found for this product.")

    return listings
