from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    """Public liveness probe for deployment infrastructure."""
    return {"status": "ok"}
