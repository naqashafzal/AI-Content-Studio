import json
from unittest.mock import MagicMock, patch

import config
from api_clients import GoogleClient, WaveSpeedClient


def _json_response(payload):
    response = MagicMock()
    response.ok = True
    response.json.return_value = payload
    return response


def test_stale_wavespeed_defaults_are_replaced(tmp_path, monkeypatch):
    """Model ids saved by earlier versions are replaced; custom model ids are kept."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({
        "WAVESPEED_IMAGE_MODEL": "black-forest-labs/flux-1.1-pro-ultra",
        "WAVESPEED_VIDEO_MODEL": "wavespeed-ai/ltx-2.3-text-to-video",
        "WAVESPEED_AUDIO_MODEL": "my-org/custom-tts",
    }), encoding="utf-8")
    monkeypatch.setattr(config, "CONFIG_FILE", str(cfg_file))
    monkeypatch.setattr(config, "save_config", lambda data, config_path=None: None)

    loaded = config.load_config()

    assert loaded["WAVESPEED_IMAGE_MODEL"] == "bytedance/seedream-v5.5"
    assert loaded["WAVESPEED_VIDEO_MODEL"] == "alibaba/wan-3.0/text-to-video"
    assert loaded["WAVESPEED_AUDIO_MODEL"] == "my-org/custom-tts"


def test_text_to_speech_sends_voice_id_and_polls_result(tmp_path):
    client = WaveSpeedClient("ws-key")
    out_file = tmp_path / "speech.mp3"
    submit = _json_response({"code": 200, "data": {"id": "pred123", "status": "created"}})
    result = _json_response({"code": 200, "data": {"status": "completed", "outputs": ["https://cdn.example.com/a.mp3"]}})
    audio = MagicMock(content=b"audio-bytes")

    with patch("api_clients.requests.post", return_value=submit) as mock_post, \
            patch("api_clients.requests.get", side_effect=[result, audio]) as mock_get:
        client.generate_speech("Hello there", "Brian", str(out_file))

    assert mock_post.call_args.args[0] == "https://api.wavespeed.ai/api/v3/elevenlabs/multilingual-v2"
    assert mock_post.call_args.kwargs["json"] == {"text": "Hello there", "voice_id": "Brian"}
    assert mock_get.call_args_list[0].args[0] == "https://api.wavespeed.ai/api/v3/predictions/pred123/result"
    assert out_file.read_bytes() == b"audio-bytes"


def test_poll_stops_on_terminal_failure_status(tmp_path):
    client = WaveSpeedClient("ws-key")
    cancelled = _json_response({"code": 200, "data": {"status": "cancelled", "error": ""}})

    with patch("api_clients.requests.get", return_value=cancelled), \
            patch("api_clients.time.sleep") as mock_sleep:
        try:
            client._poll_and_download("pred123", str(tmp_path / "out.png"), timeout=2)
        except RuntimeError as e:
            assert "cancelled" in str(e)
        else:
            raise AssertionError("expected RuntimeError")
    mock_sleep.assert_not_called()


def test_text_to_image_uses_output_format(tmp_path):
    client = WaveSpeedClient("ws-key")
    submit = _json_response({"code": 200, "data": {"id": "pred456", "status": "created"}})
    result = _json_response({"code": 200, "data": {"status": "completed", "outputs": ["https://cdn.example.com/a.png"]}})

    with patch("api_clients.requests.post", return_value=submit) as mock_post, \
            patch("api_clients.requests.get", side_effect=[result, MagicMock(content=b"png")]):
        client.text_to_image("bytedance/seedream-v5.5", "a lighthouse", str(tmp_path / "out.png"))

    assert mock_post.call_args.kwargs["json"] == {"prompt": "a lighthouse", "output_format": "png", "aspect_ratio": "16:9"}


def test_wavespeed_text_engine_uses_llm_endpoint():
    google_client = GoogleClient({"TEXT_ENGINE": "WaveSpeed AI", "WAVESPEED_API_KEY": "ws-key"})
    response = _json_response({"choices": [{"message": {"content": "hi"}}]})
    response.raise_for_status = MagicMock()

    with patch("api_clients.requests.post", return_value=response) as mock_post:
        assert google_client._generate_text("Say hi") == "hi"

    assert mock_post.call_args.args[0] == "https://llm.wavespeed.ai/v1/chat/completions"
    assert mock_post.call_args.kwargs["json"]["model"] == "meta-llama/llama-3.3-70b-instruct"


def test_migration_save_does_not_persist_environment_secrets(tmp_path, monkeypatch):
    """Rewriting stale defaults must not write secrets that only come from the environment."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"WAVESPEED_IMAGE_MODEL": "black-forest-labs/flux-1.1-pro-ultra"}), encoding="utf-8")
    monkeypatch.setattr(config, "CONFIG_FILE", str(cfg_file))
    monkeypatch.setenv("WAVESPEED_API_KEY", "env-only-key")
    monkeypatch.delenv("WAVESPEED_AI_KEY", raising=False)
    saved = []
    monkeypatch.setattr(config, "save_config", lambda data, config_path=None: saved.append(dict(data)))

    loaded = config.load_config()

    assert loaded["WAVESPEED_API_KEY"] == "env-only-key"
    assert saved and saved[0]["WAVESPEED_IMAGE_MODEL"] == "bytedance/seedream-v5.5"
    assert not saved[0].get("WAVESPEED_API_KEY")
    assert not saved[0].get("WAVESPEED_AI_KEY")
