import os
import time
import shutil
import socket
import logging
import asyncio
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import httpx

logger = logging.getLogger(__name__)


from dataclasses import dataclass


@dataclass
class ProviderCapabilities:
    """Encapsulates provider and model execution bounds without hardcoded vendor logic."""
    context_window: int = 8192
    max_output_tokens: int = 4096


class LLMResult:
    def __init__(self, text: str, ok: bool, error: Optional[str] = None):
        self.text = text
        self.ok = ok
        self.error = error


class BaseProvider:
    key: str = "base"

    def __init__(self, settings):
        self.settings = settings

    def available(self) -> bool:
        raise NotImplementedError

    async def generate(self, prompt: str) -> LLMResult:
        raise NotImplementedError

    @property
    def model(self) -> str:
        raise NotImplementedError

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Return execution bounds for the active provider/model."""
        return ProviderCapabilities(context_window=8192, max_output_tokens=4096)


class OllamaProvider(BaseProvider):
    key = "ollama"

    def __init__(self, settings):
        super().__init__(settings)
        # Cache detected models so detect_models() is not called on every
        # property access or log statement during a migration run.
        self._cached_models: Optional[List[str]] = None

    @property
    def model(self) -> str:
        if hasattr(self.settings, "ollama_model") and self.settings.ollama_model:
            return self.settings.ollama_model
        models = self._get_models_cached()
        if not models:
            return "qwen2.5-coder:7b"

        priority_str = getattr(
            self.settings,
            "ollama_model_priority",
            "qwen2.5-coder,deepseek-coder,kimi-k2,gemma3,llama3",
        )
        priority = [x.strip().lower() for x in priority_str.split(",") if x.strip()]
        for kw in priority:
            for m in models:
                if kw in m.lower():
                    return m
        return models[0]

    def _get_models_cached(self) -> List[str]:
        """Return cached model list; call detect_models() only on first access."""
        if self._cached_models is None:
            self._cached_models = self.detect_models()
        return self._cached_models

    def _candidate_urls(self) -> List[str]:
        """
        Return a list of base URLs to try.

        On Windows, 'localhost' can resolve to IPv6 (::1) which Ollama does not
        listen on by default.  We always try both 'localhost' and '127.0.0.1' so
        that whichever one works is used automatically.
        """
        base_url = getattr(
            self.settings, "ollama_base_url", "http://localhost:11434"
        ).rstrip("/")
        candidates = [base_url]
        if "localhost" in base_url:
            candidates.append(base_url.replace("localhost", "127.0.0.1"))
        elif "127.0.0.1" in base_url:
            candidates.append(base_url.replace("127.0.0.1", "localhost"))
        return candidates

    def detect_models(self) -> List[str]:
        """
        Query /api/tags to get the list of installed Ollama models.

        • Tries both the configured base URL and a 127.0.0.1/localhost variant.
        • Retries up to 3 times per URL with a 3-second timeout each.
        • Logs the raw JSON response for diagnostics.
        • Extracts the 'name' field from every entry in 'models'.
        """
        for url in self._candidate_urls():
            tags_url = f"{url}/api/tags"
            for attempt in range(1, 4):
                try:
                    logger.debug(
                        "Ollama detect_models attempt %d/3 — GET %s", attempt, tags_url
                    )
                    r = httpx.get(tags_url, timeout=3.0)
                    if r.status_code == 200:
                        raw = r.text
                        logger.info(
                            "Ollama /api/tags response (url=%s): %s",
                            tags_url,
                            raw[:600],
                        )
                        data = r.json()
                        models = [m["name"] for m in data.get("models", [])]
                        logger.info(
                            "Ollama models detected: %s",
                            models if models else "(none)",
                        )
                        return models
                    else:
                        logger.warning(
                            "Ollama /api/tags HTTP %s from %s (attempt %d/3)",
                            r.status_code,
                            tags_url,
                            attempt,
                        )
                except Exception as exc:
                    logger.debug(
                        "Ollama detect_models attempt %d/3 failed (%s): %s",
                        attempt,
                        tags_url,
                        exc,
                    )

        logger.warning(
            "Ollama /api/tags unreachable after 3 attempts on all URLs: %s",
            self._candidate_urls(),
        )
        return []

    def available(self) -> bool:
        """
        Return True only when the Ollama HTTP API is reachable and responds 200.

        We do NOT short-circuit on shutil.which('ollama') because the binary may
        be on PATH while the server daemon is not running — that would cause every
        generate() call to fail immediately with a connection error instead of
        triggering the fallback chain early.
        """
        for url in self._candidate_urls():
            try:
                r = httpx.get(f"{url}/api/tags", timeout=3.0)
                if r.status_code == 200:
                    logger.debug("Ollama available — %s/api/tags responded 200", url)
                    return True
            except Exception:
                pass

        # Last resort: socket-level port check
        base_url = getattr(
            self.settings, "ollama_base_url", "http://localhost:11434"
        )
        try:
            parsed = urlparse(base_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 11434
            with socket.create_connection((host, port), timeout=1.0):
                logger.debug(
                    "Ollama port %s:%s is open (HTTP API check failed)", host, port
                )
                return True
        except Exception:
            pass

        return False

    async def generate(self, prompt: str) -> LLMResult:
        model_name = self.model
        base_url = self._candidate_urls()[0]
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(f"{base_url}/api/generate", json=payload)
                if r.status_code == 200:
                    text = r.json().get("response", "")
                    return LLMResult(text=text, ok=True)
                else:
                    return LLMResult(
                        text="",
                        ok=False,
                        error=f"Ollama returned status {r.status_code}: {r.text}",
                    )
        except Exception as e:
            return LLMResult(text="", ok=False, error=str(e))


class GeminiProvider(BaseProvider):
    key = "gemini"

    @property
    def model(self) -> str:
        return self.settings.gemini_model

    def available(self) -> bool:
        return hasattr(self.settings, "gemini_api_key") and bool(
            self.settings.gemini_api_key.strip()
        )

    async def generate(self, prompt: str) -> LLMResult:
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.settings.gemini_api_key)
            model = genai.GenerativeModel(model_name=self.model)
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(None, model.generate_content, prompt),
                timeout=float(self.settings.gemini_timeout_seconds),
            )
            return LLMResult(text=response.text, ok=True)
        except Exception as e:
            return LLMResult(text="", ok=False, error=str(e))


class OpenAICompatProvider(BaseProvider):
    def __init__(
        self, settings, key: str, api_key: str, base_url: str, default_model: str
    ):
        super().__init__(settings)
        self.key = key
        self._api_key = api_key
        self._base_url = base_url
        self._default_model = default_model

    @property
    def model(self) -> str:
        return self._default_model

    def available(self) -> bool:
        return bool(self._api_key.strip())

    async def generate(self, prompt: str) -> LLMResult:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if "openrouter" in self._base_url.lower():
            headers["HTTP-Referer"] = "http://localhost:8000"
            headers["X-Title"] = "Brownfield IDE"

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if r.status_code == 200:
                    text = r.json()["choices"][0]["message"]["content"]
                    return LLMResult(text=text, ok=True)
                else:
                    return LLMResult(
                        text="",
                        ok=False,
                        error=f"OpenAICompat returned status {r.status_code}: {r.text}",
                    )
        except Exception as e:
            return LLMResult(text="", ok=False, error=str(e))


class FailoverProvider(BaseProvider):
    def __init__(self, settings, primary: BaseProvider):
        super().__init__(settings)
        self.primary = primary
        self._override_key = None

    @property
    def active(self) -> BaseProvider:
        if self._override_key:
            providers = get_providers(self.settings)
            prov = providers.get(self._override_key)
            if prov and prov.available():
                return prov
        return self.primary

    @property
    def key(self) -> str:
        return self.active.key

    @property
    def model(self) -> str:
        return self.active.model

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self.active.capabilities

    def available(self) -> bool:
        return self.active.available()

    async def generate(self, prompt: str) -> LLMResult:
        active = self.active
        logger.info(
            "Using provider: %s / model: %s",
            active.key,
            active.model,
        )
        res = await active.generate(prompt)
        if res.ok:
            return res

        failure_reason = res.error or "Unknown error"
        logger.warning(
            "Fallback triggered\n"
            "  Failed provider : %s\n"
            "  Reason          : %s\n"
            "  Starting failover sequence...",
            active.key,
            failure_reason,
        )

        fallback_order = ["ollama", "gemini", "openrouter", "grok", "openai"]
        tried = {active.key}
        providers = get_providers(self.settings)

        for key in fallback_order:
            if key in tried:
                continue
            prov = providers.get(key)
            if prov and prov.available():
                logger.info(
                    "Fallback provider : %s\n"
                    "  Model           : %s",
                    key,
                    prov.model,
                )
                fallback_res = await prov.generate(prompt)
                if fallback_res.ok:
                    self._override_key = key
                    logger.info(
                        "Fallback successful\n"
                        "  Active provider now: %s / %s",
                        key,
                        prov.model,
                    )
                    return fallback_res
                tried.add(key)

        return res


def get_providers(settings) -> Dict[str, BaseProvider]:
    openrouter_key = getattr(settings, "openrouter_api_key", "")
    grok_key = getattr(settings, "grok_api_key", "")
    openai_key = getattr(settings, "openai_api_key", "")

    return {
        "ollama": OllamaProvider(settings),
        "gemini": GeminiProvider(settings),
        "openrouter": OpenAICompatProvider(
            settings,
            "openrouter",
            openrouter_key,
            "https://openrouter.ai/api/v1",
            getattr(settings, "openrouter_model", "openai/gpt-4o-mini"),
        ),
        "grok": OpenAICompatProvider(
            settings,
            "grok",
            grok_key,
            "https://api.x.ai/v1",
            getattr(settings, "grok_model", "grok-2-1212"),
        ),
        "openai": OpenAICompatProvider(
            settings,
            "openai",
            openai_key,
            "https://api.openai.com/v1",
            getattr(settings, "openai_model", "gpt-4o-mini"),
        ),
    }


def _check_ollama_with_retry(
    ollama: "OllamaProvider",
    *,
    max_attempts: int = 4,
    wait_seconds: float = 3.0,
) -> bool:
    """
    Check Ollama availability with retry for startup timing.

    Ollama can take 10-20 seconds to finish GPU detection and start serving
    requests.  A single check at startup timing is not reliable.  This helper
    retries up to max_attempts times (default: 4 × 3 s = 12 s total wait)
    so the backend does not fall back to Gemini simply because Ollama has not
    finished booting.

    This function is ONLY called from get_active_provider_instance() at startup.
    The fast available() path is preserved for all other callers.
    """
    for attempt in range(1, max_attempts + 1):
        logger.info(
            "  [Ollama] Detection attempt %d/%d — checking %s",
            attempt,
            max_attempts,
            ollama._candidate_urls(),
        )
        if ollama.available():
            models = ollama._get_models_cached()
            logger.info(
                "  [Ollama] ✔ Detected on attempt %d\n"
                "           URLs tried   : %s\n"
                "           Models found : %s\n"
                "           Selected     : %s",
                attempt,
                ollama._candidate_urls(),
                models if models else "(none)",
                ollama.model if models else "(no model — will retry)",
            )
            if models:
                return True
            # Server is up but has no models yet — keep waiting
        if attempt < max_attempts:
            logger.info(
                "  [Ollama] Not ready yet — waiting %.0fs before retry %d/%d …",
                wait_seconds,
                attempt + 1,
                max_attempts,
            )
            time.sleep(wait_seconds)

    logger.info(
        "  [Ollama] Unavailable after %d attempt(s) — falling back to next provider.",
        max_attempts,
    )
    return False


def get_active_provider_instance(settings) -> Optional[BaseProvider]:
    forced = os.environ.get("AI_PROVIDER", "").strip().lower()
    if not forced:
        forced = os.environ.get("BROWNFIELD_LLM_PROVIDER", "").strip().lower()
    if forced == "gemini":
        forced = "auto"
    if not forced:
        forced = getattr(settings, "ai_provider", "auto").strip().lower()
    if forced == "gemini":
        forced = "auto"

    providers = get_providers(settings)

    logger.info(
        "\n"
        "  ╔═ Provider Registry — Auto Selection ═══════════════════╗\n"
        "  ║  Mode : %s\n"
        "  ║  Priority : Ollama → Gemini → OpenRouter → Grok → OpenAI\n"
        "  ╚════════════════════════════════════════════════════════",
        forced,
    )

    selected = None
    if forced == "auto":
        # ── Ollama first — retry at startup to handle boot timing ──────
        ollama = providers["ollama"]
        if _check_ollama_with_retry(ollama):
            selected = ollama
        else:
            logger.info("  [Ollama] Skipped — checking cloud providers …")
            for k in ["gemini", "openrouter", "grok", "openai"]:
                prov = providers[k]
                if prov.available():
                    logger.info("  [%s] ✔ Available — selected.", k)
                    selected = prov
                    break
                else:
                    logger.info("  [%s] Not available.", k)
    else:
        prov = providers.get(forced)
        if prov and prov.available():
            selected = prov
        else:
            logger.warning(
                "  Configured provider '%s' unavailable — running auto-fallback …", forced
            )
            ollama = providers["ollama"]
            if _check_ollama_with_retry(ollama):
                selected = ollama
            else:
                for k in ["gemini", "openrouter", "grok", "openai"]:
                    prov = providers[k]
                    if prov.available():
                        selected = prov
                        break

    if selected:
        inner = selected if not isinstance(selected, FailoverProvider) else selected.primary
        is_ollama = inner.key == "ollama"
        reason = (
            "Local coding model detected via Ollama (highest priority)."
            if is_ollama
            else f"Ollama unavailable — API key configured for '{inner.key}'."
        )
        logger.info(
            "\n"
            "  ╔═ Provider Selected ════════════════════════════════════╗\n"
            "  ║  Provider : %s\n"
            "  ║  Model    : %s\n"
            "  ║  Reason   : %s\n"
            "  ╚════════════════════════════════════════════════════════",
            inner.key,
            inner.model,
            reason,
        )
        return FailoverProvider(settings, selected)

    logger.warning(
        "No LLM provider available — Ollama not running and no API keys configured."
    )
    return None
