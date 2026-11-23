"""
server/core/model_gateway.py

Multi-Model AI Gateway supporting Gemini, OpenAI-compatible APIs, 
WaveSpeed LLM, and local Ollama inference with task-based routing and automated failover.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from config import load_config

class BaseModelProvider:
    def __init__(self, name: str):
        self.name = name

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        raise NotImplementedError

    def is_available(self) -> bool:
        return True

class GeminiProvider(BaseModelProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        super().__init__("Gemini")
        self.api_key = api_key
        self.model_name = model_name

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        # Use direct REST endpoint to ensure compatibility across google-genai versions
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"System Directive: {system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will follow your directive."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "maxOutputTokens": kwargs.get("max_tokens", 4096),
            }
        }
        res = requests.post(url, json=body, timeout=45)
        if res.status_code != 200:
            raise Exception(f"Gemini API returned {res.status_code}: {res.text[:300]}")
        data = res.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise Exception("Gemini returned empty candidates.")
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise Exception("Gemini candidate content empty.")
        return parts[0].get("text", "")

class OpenAICompatibleProvider(BaseModelProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model_name: str = "gpt-4o-mini", provider_label: str = "OpenAI-Compatible"):
        super().__init__(provider_label)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096)
        }
        res = requests.post(url, json=payload, headers=headers, timeout=45)
        if res.status_code != 200:
            raise Exception(f"{self.name} API returned {res.status_code}: {res.text[:300]}")
        data = res.json()
        choices = data.get("choices", [])
        if not choices:
            raise Exception(f"{self.name} returned no choices.")
        return choices[0].get("message", {}).get("content", "")

class OllamaProvider(BaseModelProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama3"):
        super().__init__("Ollama (Local)")
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    def is_available(self) -> bool:
        try:
            res = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return res.status_code == 200
        except Exception:
            return False

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False
        }
        res = requests.post(url, json=payload, timeout=60)
        if res.status_code != 200:
            raise Exception(f"Ollama returned {res.status_code}: {res.text[:300]}")
        return res.json().get("response", "")

class ModelGateway:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._has_explicit_config = config is not None
        self.config = config or load_config()
        self._init_providers()

    def refresh_config(self):
        """Reloads config.json dynamically unless a custom config/mock provider was injected."""
        if self._has_explicit_config:
            return
        if "mock" in getattr(self, "providers", {}):
            return
        self.config = load_config()
        self._init_providers()

    def _init_providers(self):
        gemini_key = self.config.get("GEMINI_API_KEY", "")
        openai_key = self.config.get("OPENAI_API_KEY", "")
        wavespeed_key = self.config.get("WAVESPEED_API_KEY") or self.config.get("WAVESPEED_AI_KEY") or ""
        ollama_url = self.config.get("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = self.config.get("OLLAMA_MODEL", "llama3")

        self.providers: Dict[str, BaseModelProvider] = {
            "gemini": GeminiProvider(gemini_key, model_name=self.config.get("GEMINI_MODEL", "gemini-2.5-flash")),
            "wavespeed": OpenAICompatibleProvider(
                api_key=wavespeed_key,
                base_url="https://llm.wavespeed.ai/v1",
                model_name=self.config.get("WAVESPEED_TEXT_MODEL", "meta-llama/llama-3.3-70b-instruct"),
                provider_label="WaveSpeed LLM"
            ),
            "openai": OpenAICompatibleProvider(
                api_key=openai_key,
                base_url=self.config.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                model_name=self.config.get("OPENAI_MODEL", "gpt-4o-mini")
            ),
            "ollama": OllamaProvider(base_url=ollama_url, model_name=ollama_model)
        }

    def get_preferred_order(self, task: str = "general") -> List[str]:
        engine_pref = self.config.get("TEXT_ENGINE", "Gemini API").lower()
        if "gemini" in engine_pref:
            order = ["gemini", "wavespeed", "openai", "ollama"]
        elif "wavespeed" in engine_pref:
            order = ["wavespeed", "gemini", "openai", "ollama"]
        elif "ollama" in engine_pref or "local" in engine_pref:
            order = ["ollama", "gemini", "wavespeed", "openai"]
        else:
            order = ["openai", "gemini", "wavespeed", "ollama"]
        return order

    def generate(self, prompt: str, system_prompt: Optional[str] = None, task: str = "general", **kwargs) -> str:
        self.refresh_config()
        order = self.get_preferred_order(task)
        last_error = None

        for provider_key in order:
            provider = self.providers.get(provider_key)
            if not provider or not provider.is_available():
                continue

            try:
                logging.info(f"[ModelGateway] Routing task '{task}' to provider '{provider.name}'")
                text = provider.generate_text(prompt, system_prompt=system_prompt, **kwargs)
                if text and text.strip():
                    return text.strip()
            except Exception as e:
                logging.warning(f"[ModelGateway] Provider '{provider.name}' failed for task '{task}': {e}. Attempting failover...")
                last_error = e

        if last_error:
            raise Exception(f"All configured AI model providers failed. Last error: {last_error}")
        raise Exception("No AI model provider is currently configured or available. Please provide an API key in Settings.")

    def generate_json(self, prompt: str, system_prompt: Optional[str] = None, task: str = "general") -> Any:
        full_system = (system_prompt or "") + "\nYou MUST return valid JSON ONLY with NO surrounding markdown or backticks."
        raw = self.generate(prompt, system_prompt=full_system, task=task)
        clean = raw.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        return json.loads(clean.strip())

# Global gateway singleton
gateway = ModelGateway()
