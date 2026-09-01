"""Shared helpers for the MongoDB repository implementations."""

from __future__ import annotations

from typing import Any

from bson import ObjectId
from bson.errors import InvalidId


def to_object_id(value: str) -> ObjectId | None:
    """Convert a string id to an ``ObjectId``, or None when malformed.

    Returning None instead of raising lets callers translate an unusable id into
    a plain 404 rather than a 500.
    """
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def with_string_id(document: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the document with ``_id`` renamed to ``id`` as a string."""
    data = dict(document)
    raw_id = data.pop("_id", None)
    if raw_id is not None:
        data["id"] = str(raw_id)
    return data
