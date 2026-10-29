import pytest
import os
import json
from config import load_config, save_config, mask_secret, is_masked_value, SENSITIVE_KEYS
from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app, headers={"X-API-Key": "test-suite-token"})

def test_secret_masking():
    # Long key
    key = "AIzaSyD-1234567890abcdef"
    masked = mask_secret(key)
    assert masked.startswith("AIz")
    assert masked.endswith("def")
    assert "****" in masked
    assert is_masked_value(masked)

    # Empty key
    assert mask_secret("") == ""
    assert not is_masked_value("")

    # Short key
    assert mask_secret("12345") == "******"

def test_config_endpoint_masks_secrets():
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    
    # Sensitive keys must be masked or empty, never raw secrets
    for key in SENSITIVE_KEYS:
        if key in data and data[key]:
            assert "****" in data[key] or data[key] == "******"

def test_config_save_does_not_overwrite_with_masks(tmp_path):
    test_cfg_path = str(tmp_path / "test_config.json")
    initial_config = {
        "GEMINI_API_KEY": "real_secret_key_12345",
        "PODCAST_STYLE": "Informative News"
    }
    with open(test_cfg_path, "w") as f:
        json.dump(initial_config, f)

    # Attempt to save with a masked value
    updated_payload = {
        "GEMINI_API_KEY": "rea****2345", # masked
        "PODCAST_STYLE": "Comedy / Entertaining"
    }
    save_config(updated_payload, config_path=test_cfg_path)

    # Verify that the real secret was preserved
    with open(test_cfg_path, "r") as f:
        reloaded = json.load(f)
    assert reloaded["GEMINI_API_KEY"] == "real_secret_key_12345"
    assert reloaded["PODCAST_STYLE"] == "Comedy / Entertaining"

def test_media_endpoint_path_traversal_prevention():
    # Attempt to read an arbitrary file outside workspace
    response = client.get("/api/generate/media?path=../../../../etc/passwd")
    assert response.status_code in (403, 404)

    # Attempt to read config.json directly
    response = client.get("/api/generate/media?path=config.json")
    assert response.status_code in (403, 404)

def test_project_delete_path_traversal_prevention():
    # Attempt directory traversal deletion
    response = client.delete("/api/generate/history/..%2F..%2Fsystem")
    assert response.status_code in (400, 403, 404)
