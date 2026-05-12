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
        
        # Build label mapping table
        label_table = self._build_label_mapping(world.entities)
        
        # Caller recent memory
        caller_memory = ""
        if caller.has("agent"):
            mem = caller.get("agent").memory
            caller_memory = mem.to_prompt_text(3)
        
        context = {
            "caller_name": caller.name,
            "caller_recent_memory": caller_memory or "无",
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
            "label_table": label_table,
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

    def _build_label_mapping(self, entities: dict) -> str:
        """Build ID -> name + describe mapping table for LLM prompt."""
        lines = []
        for eid, e in sorted(entities.items()):
            desc = getattr(e, 'describe', '') or e.name
            lines.append(f"  {eid:16s} -> {e.name} ({desc[:40]})")
        return "\n".join(lines)

    def _format_ambient(self, ambient: list[dict]) -> str:
        if not ambient:
            return ""
        lines = []
        for a in ambient:
            eid = a.get("entity_id", "?")
            name = a.get("name", "?")
            visual = a.get("visual", {})
            look = visual.get("look", "")
            hint = a.get("private_hint", {})
            lines.append(
                f"  - {name} (id={eid}) 距离{a.get('distance','?')}: "
                f"视={look}, 状态={json.dumps(hint, ensure_ascii=False)}"
            )
        return "\n".join(lines)

    async def generate_story(self, caller, component: list[dict],
                              proposed_action: str) -> str:
        """LLM #2: Generate objective narrative from component panorama."""
        caller_desc = getattr(caller, 'describe', '') or caller.name
        comp_text = self._format_component(component)
        context = {
            "caller_name": caller.name, "caller_desc": caller_desc,
            "proposed_action": proposed_action, "component_entities": comp_text,
        }
        prompt = self.assembler.assemble("story_layer", context)
        system = self.assembler.get_system_prompt("story_layer")
        raw = await self.llm.chat(system=system, messages=[{"role":"user","content":prompt}])
        from agent.brain import extract_json
        try:
            data = json.loads(extract_json(raw))
            return data.get("story", raw[:200])
        except Exception:
            return raw[:200]

    async def project_deltas(self, story: str, entities_state: str) -> list:
        """LLM #3: Compute numeric deltas from story."""
        context = {"story_text": story, "entity_states": entities_state}
        prompt = self.assembler.assemble("projection_layer", context)
        system = self.assembler.get_system_prompt("projection_layer")
        raw = await self.llm.chat(system=system, messages=[{"role":"user","content":prompt}])
        from agent.brain import extract_json
        try:
            data = json.loads(extract_json(raw))
            return data.get("effects", [])
        except Exception:
            return []

    def _format_component(self, component: list[dict]) -> str:
        lines = []
        for c in component:
            lines.append(f"  - {c['name']} (id={c['entity_id']}): {c.get('describe','')[:80]}")
            if c.get('private_attrs'):
                lines.append(f"    属性: {json.dumps(c['private_attrs'], ensure_ascii=False)}")
        return "\n".join(lines)
