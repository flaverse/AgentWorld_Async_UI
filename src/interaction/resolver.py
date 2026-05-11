import json
from systems.interaction import ActionResult
from agent.brain import extract_json


class InteractionResolver:
    def __init__(self, llm_client, assembler):
        self.llm = llm_client
        self.assembler = assembler

    async def resolve(self, caller, target, action: str,
                      ambient_entities: list[dict],
                      world) -> ActionResult:
        interaction = target.get("interaction")
        context = {
            "caller_name": caller.name,
            "caller_public": json.dumps(
                caller.get("interaction").public_attrs
                if caller.has("interaction") else {},
                ensure_ascii=False
            ),
            "caller_private": json.dumps(
                caller.get("interaction").private_attrs
                if caller.has("interaction") else {},
                ensure_ascii=False
            ),
            "target_name": target.name,
            "target_public": json.dumps(
                interaction.public_attrs, ensure_ascii=False
            ),
            "target_private": json.dumps(
                interaction.private_attrs, ensure_ascii=False
            ),
            "action": action,
            "ambient_text": self._format_ambient(ambient_entities),
        }

        prompt = self.assembler.assemble("interaction_resolve", context)
        system = self.assembler.get_system_prompt("interaction_resolve")
        schema = self.assembler.get_output_schema("interaction_resolve")

        raw = await self.llm.chat(
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        json_str = extract_json(raw)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            from core.error_collector import errors
            errors.log_llm_parse_failure("resolver.resolve", raw)
            data = {}

        return ActionResult(
            target_id=target.id,
            caller_deltas=data.get("caller_deltas", {}),
            target_deltas=data.get("target_deltas", {}),
            ambient_effects=data.get("ambient_effects", []),
            narrative=data.get("narrative", ""),
            public_observation=data.get("public_observation", ""),
        )

    def _format_ambient(self, ambient: list[dict]) -> str:
        if not ambient:
            return ""
        lines = []
        for a in ambient:
            name = a.get("name", "?")
            visual = a.get("visual", {})
            look = visual.get("look", "")
            hint = a.get("private_hint", {})
            lines.append(
                f"  - {name}(距离{a.get('distance','?')}): "
                f"视={look}, 状态={json.dumps(hint, ensure_ascii=False)}"
            )
        return "\n".join(lines)
