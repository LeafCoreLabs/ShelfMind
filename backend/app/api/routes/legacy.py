"""Legacy unauthenticated routes — redirect clients to /api/dashboard/*."""

from fastapi import APIRouter

router = APIRouter()

# Deprecated: use authenticated /api/dashboard/* endpoints instead.
