import os
import json
import time
import asyncio
import concurrent.futures

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=64)


def _retry(fn, max_retries: int, name: str) -> str:
    """Shared retry wrapper — exponential backoff, error logging, final failure."""
    for attempt in range(max_retries + 1):
        try:
            return fn(attempt)
        except Exception as e:
            if attempt < max_retries:
                from core.error_collector import errors
                errors.log_error(f"llm.{name}", f"retry {attempt+1}/{max_retries}: {e}")
                time.sleep(2 ** attempt)
                continue
            from core.error_collector import errors
            errors.log_exception(f"llm.{name}", e, "final failure")
            raise
    return ""


class LLMClient:
    def __init__(self, config: dict, concurrency_gate=None, telemetry=None):
        self.model = config.get("model", "gpt-4o")
        self.max_retries = config.get("max_retries", 2)

        api_key = config.get("api_key", "")
        api_key = self._resolve_env_var(api_key)
        base_url = config.get("base_url", "")
        self.provider = config.get("provider", "openai")

        if not api_key:
            base_url, api_key = self._find_credentials(self.provider)

        self.api_key = api_key
        self.base_url = base_url or config.get("base_url", "")

        if not self.api_key:
            raise RuntimeError("No API key found. Set env var or check openclaw config.")

        self._gate = concurrency_gate
        self._hit_429 = False
        self._telemetry = telemetry

    def _resolve_env_var(self, val: str) -> str:
        if val.startswith("${") and val.endswith("}"):
            return os.environ.get(val[2:-1], "")
        return val

    def _find_credentials(self, preferred: str):
        if preferred == "minimax":
            api_key = os.environ.get("MINIMAX_API_KEY", "").strip()
            if api_key:
                url = os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic")
                return url, api_key

        if preferred in ("deepseek", "openai"):
            api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip() or \
                      os.environ.get("OPENAI_API_KEY", "").strip()
            if api_key:
                url = os.environ.get("DEEPSEEK_BASE_URL", "") or \
                      os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
                return url, api_key

        config_paths = [
            os.path.expanduser("~/.openclaw/agents/coder/agent/models.json"),
            os.path.expanduser("~/.openclaw/agents/life/agent/models.json"),
        ]
        for path in config_paths:
            try:
                with open(path) as f:
                    raw = f.read()
                idx = raw.find('"providers"')
                if idx < 0: continue
                brace_idx = raw.find('{', idx)
                if brace_idx < 0: continue
                partial = raw[brace_idx:]
                depth = 0
                end = 0
                for i, c in enumerate(partial):
                    if c == '{': depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0: end = i + 1; break
                if end == 0: continue
                providers = json.loads(partial[:end])
                for target in [preferred] + [p for p in providers if p != preferred]:
                    prov = providers.get(target, {})
                    k = prov.get("apiKey", "") or prov.get("api_key", "")
                    u = prov.get("baseUrl", "") or prov.get("base_url", "")
                    if k and u: return u, k
            except Exception as e:
                from core.error_collector import errors
                errors.log_exception("llm._find_credentials", e, f"parsing {path}")
                continue
        return "", ""

    async def chat(self, system: str, messages: list[dict],
                   temperature: float = 0.7,
                   response_format: dict = None) -> str:
        loop = asyncio.get_running_loop()
        if self._gate:
            await loop.run_in_executor(_executor, self._gate.acquire)
        self._hit_429 = False
        try:
            _t0 = time.time()
            if self.provider == "minimax":
                result = await loop.run_in_executor(
                    _executor, self._call_anthropic, system, messages,
                    temperature, response_format)
            else:
                result = await loop.run_in_executor(
                    _executor, self._call_openai, system, messages,
                    temperature, response_format)
            _dt_ms = (time.time() - _t0) * 1000
            if self._telemetry and not self._hit_429:
                self._telemetry.record(self.provider, "chat", _dt_ms)
            if self._gate:
                if self._hit_429:
                    self._gate.report_429()
                else:
                    self._gate.report_ok()
            return result
        finally:
            if self._gate:
                self._gate.release()

    def _call_anthropic(self, system: str, messages: list[dict],
                        temperature: float, response_format: dict = None) -> str:
        import requests

        user_content = messages[0]["content"] if messages else ""

        def call(attempt: int) -> str:
            if attempt == 0:
                to, mt, t = 180, 8000, temperature
            elif attempt == 1:
                to, mt, t = 120, 3000, min(temperature + 0.2, 1.0)
            else:
                to, mt, t = 120, 2000, 0.8

            resp = requests.post(
                f"{self.base_url}/v1/messages",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "anthropic-version": "2023-06-01",
                    "anthropic-dangerous-direct-browser-access": "true",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model, "max_tokens": mt,
                    "temperature": t, "system": system,
                    "messages": [{"role": "user", "content": user_content}],
                },
                timeout=to,
            )
            if resp.status_code == 200:
                data = resp.json()
                blocks = data.get("content", [])
                parts = [b.get("text", "") or b.get("thinking", "")
                         for b in blocks if (b.get("text") or b.get("thinking", "")).strip()]
                return "\n".join(parts).strip()
            if resp.status_code != 429:
                raise RuntimeError(f"API {resp.status_code}: {resp.text[:300]}")
            self._hit_429 = True
            raise RuntimeError("rate limit")

        return _retry(call, self.max_retries, "anthropic")

    def _call_openai(self, system: str, messages: list[dict],
                     temperature: float, response_format: dict = None) -> str:
        import openai
        client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        full = [{"role": "system", "content": system}] + messages

        def call(attempt: int) -> str:
            kwargs = {
                "model": self.model, "messages": full,
                "temperature": temperature, "max_tokens": 4000, "timeout": 120,
            }
            if response_format:
                kwargs["response_format"] = response_format
            try:
                resp = client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content or ""
            except openai.RateLimitError:
                self._hit_429 = True
                raise
            except openai.APIStatusError as e:
                if e.status_code == 429:
                    self._hit_429 = True
                raise

        return _retry(call, self.max_retries, "openai")
