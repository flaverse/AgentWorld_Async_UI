import json


def extract_json(text: str) -> str:
    """从 LLM 响应中提取 JSON 内容。
    处理 markdown 代码块、前导文字等情况。
    """
    text = text.strip()

    # 策略1: ```json ... ``` 或 ``` ... ```
    if "```" in text:
        blocks = text.split("```")
        for i, block in enumerate(blocks):
            block = block.strip()
            if block.startswith("json"):
                block = block[4:].strip()
            if block.startswith("{") or block.startswith("["):
                return block

    # 策略2: 找到第一个 { 到对应的 }
    brace_start = -1
    depth = 0
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                brace_start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and brace_start >= 0:
                return text[brace_start : i + 1]

    # 策略3: 找第一个 [ 到对应的 ]
    bracket_start = -1
    depth = 0
    for i, ch in enumerate(text):
        if ch == "[":
            if depth == 0:
                bracket_start = i
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0 and bracket_start >= 0:
                return text[bracket_start : i + 1]

    return text


class Brain:
    def __init__(self, llm_clients: dict, assembler, default_provider: str = "deepseek"):
        self.llm_clients = llm_clients
        self.default_provider = default_provider
        self.assembler = assembler

    def _get_llm(self, provider: str = ""):
        key = provider or self.default_provider
        return self.llm_clients.get(key, list(self.llm_clients.values())[0])

    async def decide(self, context: dict, template_name: str = "agent_decision",
                     provider: str = "") -> dict:
        llm = self._get_llm(provider)
        prompt = self.assembler.assemble(template_name, context)
        system = self.assembler.get_system_prompt(template_name)
        schema = self.assembler.get_output_schema(template_name)
        temp = self.assembler.get_temperature(template_name)
        raw = await llm.chat(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
            response_format=schema,
        )
        return _parse_llm_json(raw, "brain.decide")


def _parse_llm_json(raw: str, source: str) -> dict:
    json_str = extract_json(raw)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        from core.error_collector import errors
        errors.log_llm_parse_failure(source, raw)
        return {"parse_error": True, "source": source, "raw_preview": raw[:200]}
