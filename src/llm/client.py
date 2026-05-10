import os
import json
import time
import asyncio
import concurrent.futures
import requests

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


class LLMClient:
    def __init__(self, config: dict):
        self.model = config.get("model", "gpt-4o")
        self.max_retries = config.get("max_retries", 2)

        api_key = config.get("api_key", "")
        api_key = self._resolve_env_var(api_key)
        base_url = config.get("base_url", "")
        self.provider = config.get("provider", "openai")

        if not api_key:
            base_url, api_key = self._find_credentials(self.provider)
            if base_url and not config.get("base_url"):
                pass

        self.api_key = api_key
        self.base_url = base_url or config.get("base_url", "")

        if not self.api_key:
            raise RuntimeError("No API key found. Set env var or check openclaw config.")

    def _resolve_env_var(self, val: str) -> str:
        if val.startswith("${") and val.endswith("}"):
            return os.environ.get(val[2:-1], "")
        return val

    def _find_credentials(self, preferred: str):
        # Env vars
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

        # Config files
        config_paths = [
            os.path.expanduser("~/.openclaw/agents/coder/agent/models.json"),
            os.path.expanduser("~/.openclaw/agents/life/agent/models.json"),
        ]

        for path in config_paths:
            try:
                with open(path) as f:
                    raw = f.read()
                idx = raw.find('"providers"')
                if idx < 0:
                    continue
                brace_idx = raw.find('{', idx)
                if brace_idx < 0:
                    continue
                partial = raw[brace_idx:]
                depth = 0
                end = 0
                for i, c in enumerate(partial):
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                if end == 0:
                    continue
                providers = json.loads(partial[:end])

                # Check by preferred provider first
                for target in [preferred] + [p for p in providers if p != preferred]:
                    prov = providers.get(target, {})
                    k = prov.get("apiKey", "") or prov.get("api_key", "")
                    u = prov.get("baseUrl", "") or prov.get("base_url", "")
                    if k and u:
                        return u, k
            except Exception:
                continue

        return "", ""

    async def chat(self, system: str, messages: list[dict],
                   temperature: float = 0.7) -> str:
        loop = asyncio.get_running_loop()
        if self.provider == "minimax":
            return await loop.run_in_executor(
                _executor, self._call_anthropic_sync, system, messages, temperature
            )
        else:
            return await loop.run_in_executor(
                _executor, self._call_openai_sync, system, messages, temperature
            )

    def _call_anthropic_sync(self, system: str, messages: list[dict],
                             temperature: float) -> str:
        user_content = messages[0]["content"] if messages else ""

        for attempt in range(self.max_retries + 1):
            if attempt == 0:
                timeout, max_tokens, temp = 180, 8000, temperature
            elif attempt == 1:
                timeout, max_tokens, temp = 120, 3000, min(temperature + 0.2, 1.0)
            else:
                timeout, max_tokens, temp = 120, 2000, 0.8

            try:
                resp = requests.post(
                    f"{self.base_url}/v1/messages",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "anthropic-version": "2023-06-01",
                        "anthropic-dangerous-direct-browser-access": "true",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": max_tokens,
                        "temperature": temp,
                        "system": system,
                        "messages": [{"role": "user", "content": user_content}],
                    },
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    blocks = data.get("content", [])
                    parts = []
                    for b in blocks:
                        t = b.get("text", "") or b.get("thinking", "")
                        if t.strip():
                            parts.append(t)
                    return "\n".join(parts).strip()
                elif resp.status_code == 429 and attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise RuntimeError(f"API {resp.status_code}: {resp.text[:300]}")
            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise
        return ""

    def _call_openai_sync(self, system: str, messages: list[dict],
                          temperature: float) -> str:
        import openai
        client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        full = [{"role": "system", "content": system}] + messages

        for attempt in range(self.max_retries + 1):
            try:
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=full,
                    temperature=temperature,
                    max_tokens=4000,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                else:
                    raise
        return ""
