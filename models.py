from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SizeListing:
    """Normalized size listing information returned by the SNKRDUNK API."""

    size: str
    min_listing_price: int | float | None
    listing_item_count: int


class SizeParseError(ValueError):
    """Raised when an API response does not contain recognizable size data."""


def _as_number(value: Any) -> int | float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
        return int(number) if number.is_integer() else number
    return None


def _as_count(value: Any) -> int:
    number = _as_number(value)
    if number is None:
        return 0
    try:
        return max(0, int(number))
    except (TypeError, ValueError, OverflowError):
        return 0


def _looks_like_size_record(value: Any) -> bool:
    """Return True for a size-price record from the SNKRDUNK response."""
    if not isinstance(value, dict):
        return False

    # Current SNKRDUNK response uses:
    # {
    #   "size": {"localizedName": "S", ...},
    #   "minListingPrice": 11000,
    #   "listingItemCount": 32,
    #   ...
    # }
    has_size = "size" in value and (
        isinstance(value.get("size"), (str, int, float))
        or isinstance(value.get("size"), dict)
    )
    has_listing_fields = bool(
        {"minListingPrice", "listingItemCount", "min_listing_price", "listing_item_count"}
        & set(value)
    )
    return has_size and has_listing_fields


def _extract_size_name(value: Any) -> str | None:
    """Extract the display size from either a scalar or nested size object."""
    if value is None:
        return None
    if isinstance(value, dict):
        # localizedName is the human-readable size, e.g. S, M, L, 26.0.
        for key in ("localizedName", "name", "label", "value"):
            candidate = value.get(key)
            if candidate is not None and str(candidate).strip():
                return str(candidate).strip()
        return None
    text = str(value).strip()
    return text or None


def _find_size_records(value: Any) -> list[dict[str, Any]]:
    """Recursively find the most relevant list of size records in arbitrary JSON."""
    best: list[dict[str, Any]] = []

    if isinstance(value, list):
        records = [item for item in value if _looks_like_size_record(item)]
        if len(records) > len(best):
            best = records
        for item in value:
            nested = _find_size_records(item)
            if len(nested) > len(best):
                best = nested
    elif isinstance(value, dict):
        for child in value.values():
            nested = _find_size_records(child)
            if len(nested) > len(best):
                best = nested

    return best


def parse_size_listings(data: Any) -> list[SizeListing]:
    """Extract size listings without assuming a single fixed JSON nesting level."""
    records = data.get("sizePrices")
    if not records:
        raise SizeParseError("Không thể phân tích dữ liệu size từ API.")

    listings: list[SizeListing] = []
    for record in records:
        raw_size = record.get("size")
        size=raw_size.get("localizedName")
        if raw_size is None:
            continue

        price = record.get("minListingPrice", record.get("min_listing_price"))
        count = record.get("listingItemCount", record.get("listing_item_count", 0))
        listings.append(
            SizeListing(
                size=size,
                min_listing_price=_as_number(price),
                listing_item_count=_as_count(count),
            )
        )

    if not listings:
        raise SizeParseError("Không thể phân tích dữ liệu size từ API.")

    return listings
