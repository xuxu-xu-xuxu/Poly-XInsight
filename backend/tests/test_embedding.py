import pytest
from unittest.mock import patch, AsyncMock, Mock

@pytest.mark.asyncio
async def test_embed_sentences():
    mock_resp = Mock()
    mock_resp.json.return_value = {"dense_embeddings": [[0.1, 0.2, 0.3]]}
    mock_resp.raise_for_status = Mock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("backend.services.embedding.httpx.AsyncClient", return_value=mock_client):
        from backend.services.embedding import embed_sentences
        result = await embed_sentences(["test sentence"])
        assert len(result["dense_embeddings"]) == 1
        assert len(result["dense_embeddings"][0]) == 3

@pytest.mark.asyncio
async def test_embed_single():
    mock_resp = Mock()
    mock_resp.json.return_value = {"dense_embeddings": [[0.5, 0.6]]}
    mock_resp.raise_for_status = Mock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("backend.services.embedding.httpx.AsyncClient", return_value=mock_client):
        from backend.services.embedding import embed_single
        vec = await embed_single("hello")
        assert vec == [0.5, 0.6]
