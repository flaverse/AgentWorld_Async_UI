import json
import re


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
                text = block
                break

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
    def __init__(self, llm_client, assembler):
        self.llm = llm_client
        self.assembler = assembler

    async def decide(self, context: dict) -> dict:
        prompt = self.assembler.assemble("agent_decision", context)
        system = self.assembler.get_system_prompt("agent_decision")
        schema = self.assembler.get_output_schema("agent_decision")

        raw = await self.llm.chat(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            response_format=schema,
        )
        json_str = extract_json(raw)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            from core.error_collector import errors
            errors.log_llm_parse_failure("brain.decide", raw)
            return {"thinking": raw}
