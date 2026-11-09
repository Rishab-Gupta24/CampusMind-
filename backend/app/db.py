"""The only place that talks to Supabase. Uses the service-role key (server side only)."""

from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


class NotConfiguredError(RuntimeError):
    """Raised when backend/.env is missing Supabase settings. Its message is safe to show users."""


@lru_cache
def get_client() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise NotConfiguredError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env."
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def count_chunks() -> int:
    result = get_client().table("chunks").select("id", count="exact").limit(1).execute()
    return result.count or 0
