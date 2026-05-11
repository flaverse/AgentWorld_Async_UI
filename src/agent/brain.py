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
        )
        json_str = extract_json(raw)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            from core.error_collector import errors
            errors.log_llm_parse_failure("brain.decide", raw)
            return {"thinking": raw}

    async def decide_batch(self, agent_contexts: dict[str, dict]) -> dict[str, dict]:
        """一次 LLM 调用处理多个 agent 的决策。n 个 agent → 1 次 LLM。

        Args:
            agent_contexts: {agent_id: context_dict}

        Returns:
            {agent_id: decision_dict}
        """
        if len(agent_contexts) == 1:
            # 单个 agent 走原路径
            aid, ctx = next(iter(agent_contexts.items()))
            return {aid: await self.decide(ctx)}

        # 构建合并 prompt
        parts = [
            f"你是一个世界模拟引擎的决策模块。以下是 {len(agent_contexts)} 个 NPC 的独立决策请求。",
            "每个 NPC 互相独立，不要跨 NPC 推理。请为每个 NPC 输出一条决策。",
            "",
        ]
        for aid, ctx in agent_contexts.items():
            parts.append(f"==== NPC: {ctx.get('name', aid)} (id: {aid}) ====")
            parts.append(ctx.get("prompt_text", ""))
            parts.append("")

        parts.append("==== 输出格式 ====")
        parts.append(
            f'返回一个 JSON 对象，key 为 NPC 的 id，value 为决策 JSON。'
            f'例如: {{"{list(agent_contexts.keys())[0]}": {{"thinking": "...", "move_to": null, "target_entity": "drink_ale", "action": "饮用"}}}}'
        )
        parts.append("只输出 JSON，不要 markdown 包裹，不要额外文字。")

        combined = "\n".join(parts)
        system = self.assembler.get_system_prompt("agent_decision")

        raw = await self.llm.chat(
            system=system,
            messages=[{"role": "user", "content": combined}],
        )

        # 解析: 期望返回 {agent_id: decision, ...}
        json_str = extract_json(raw)
        try:
            result = json.loads(json_str)
            if isinstance(result, dict):
                # 验证并补全
                out = {}
                for aid in agent_contexts:
                    if aid in result and isinstance(result[aid], dict):
                        out[aid] = result[aid]
                    else:
                        out[aid] = {"thinking": f"(batch parse failed for {aid})"}
                return out
        except json.JSONDecodeError:
            from core.error_collector import errors
            errors.log_llm_parse_failure("brain.decide_batch", raw)

        # fallback: 每个 agent 返回空决策
        return {aid: {"thinking": "(batch parse failed)"} for aid in agent_contexts}
