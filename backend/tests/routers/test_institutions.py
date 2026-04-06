"""Tests for GET /api/v1/institutions."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core import cache as cache_module
from tests.conftest import make_institution


class TestListInstitutions:
    async def test_returns_200_with_institution_list(self, client, mock_session):
        inst = make_institution()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [inst]
        mock_session.execute.return_value = mock_result

        response = await client.get("/api/v1/institutions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

    async def test_response_shape(self, client, mock_session):
        inst = make_institution()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [inst]
        mock_session.execute.return_value = mock_result

        body = (await client.get("/api/v1/institutions")).json()
        item = body[0]

        assert item["id"] == "TAU"
        assert item["name_he"] == "אוניברסיטת תל אביב"
        assert item["name_en"] == "Tel Aviv University"
        assert item["type"] == "university"
        assert item["city"] == "Tel Aviv"
        assert "website_url" in item
        assert item["is_active"] is True

    async def test_returns_empty_list_when_no_institutions(self, client, mock_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        response = await client.get("/api/v1/institutions")

        assert response.status_code == 200
        assert response.json() == []

    async def test_multiple_institutions_returned(self, client, mock_session):
        tau = make_institution(id="TAU", name_en="Tel Aviv University")
        huji = make_institution(id="HUJI", name_en="Hebrew University")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [tau, huji]
        mock_session.execute.return_value = mock_result

        body = (await client.get("/api/v1/institutions")).json()

        assert len(body) == 2
        ids = {item["id"] for item in body}
        assert ids == {"TAU", "HUJI"}

    # ── Caching ───────────────────────────────────────────────────────────────

    async def test_cache_miss_populates_cache(self, client, mock_session, monkeypatch):
        """On a cache miss the endpoint should call cache_set."""
        mock_set = AsyncMock()
        monkeypatch.setattr(cache_module, "cache_set", mock_set)

        inst = make_institution()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [inst]
        mock_session.execute.return_value = mock_result

        await client.get("/api/v1/institutions")

        mock_set.assert_awaited_once()
        call_key = mock_set.call_args[0][0]
        assert call_key == "institutions:all"

    async def test_cache_hit_skips_db(self, client, mock_session, monkeypatch):
        """When the cache returns data, the DB must not be queried."""
        cached_data = [
            {
                "id": "TAU",
                "name_he": "אוניברסיטת תל אביב",
                "name_en": "Tel Aviv University",
                "type": "university",
                "location": "תל אביב",
                "city": "Tel Aviv",
                "website_url": "https://www.tau.ac.il",
                "is_active": True,
                "created_at": "2026-04-05T12:00:00+00:00",
            }
        ]
        monkeypatch.setattr(cache_module, "cache_get", AsyncMock(return_value=cached_data))

        response = await client.get("/api/v1/institutions")

        assert response.status_code == 200
        assert response.json()[0]["id"] == "TAU"
        mock_session.execute.assert_not_called()

    async def test_cache_hit_returns_correct_shape(self, client, mock_session, monkeypatch):
        """Cached data is deserialised back into the correct response schema."""
        cached_data = [
            {
                "id": "HUJI",
                "name_he": "האוניברסיטה העברית",
                "name_en": "Hebrew University",
                "type": "university",
                "location": "ירושלים",
                "city": "Jerusalem",
                "website_url": "https://www.huji.ac.il",
                "is_active": True,
                "created_at": "2026-04-05T12:00:00+00:00",
            }
        ]
        monkeypatch.setattr(cache_module, "cache_get", AsyncMock(return_value=cached_data))

        body = (await client.get("/api/v1/institutions")).json()
        assert body[0]["name_en"] == "Hebrew University"
