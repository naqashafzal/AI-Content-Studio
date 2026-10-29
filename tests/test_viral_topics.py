import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app, headers={"X-API-Key": "test-suite-token"})

def test_viral_topics_endpoint_standalone():
    # Mock find_viral_topics so test does not require live external API keys
    with patch("agents.TrendAgent.find_viral_topics") as mock_find:
        mock_find.return_value = [
            "AI Superintelligence Breakthrough",
            "Quantum Computing vs Cryptography",
            "Autonomous Agents in 2026"
        ]
        response = client.get("/api/generate/viral-topics")
        assert response.status_code == 200
        data = response.json()
        assert "topics" in data
        assert len(data["topics"]) == 3
        assert data["topics"][0] == "AI Superintelligence Breakthrough"
