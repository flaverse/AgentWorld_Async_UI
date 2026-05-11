class PromptAssembler:
    def __init__(self, loader):
        self.loader = loader

    def assemble(self, template_name: str, context: dict) -> str:
        template = self.loader.get_template(template_name)
        parts = []

        for slot_def in template.get("slots", []):
            cond = slot_def.get("condition")
            if cond and not self._check_condition(cond, context):
                continue

            slot = self.loader.get_slot(slot_def["name"])
            provider = slot.get("provider", "content")

            if provider == "content":
                text = slot.get("template", "")
            elif provider == "runtime":
                text = slot.get("template", "").format(**context)
            elif provider == "topology":
                text = slot.get("template", "").format(**context)
            else:
                text = ""

            if text:
                parts.append(text)

        return "\n\n".join(parts)

    def get_system_prompt(self, template_name: str) -> str:
        template = self.loader.get_template(template_name)
        ref = template.get("system_prompt_ref", "")
        if ref:
            return self.loader.get_system_prompt(ref)
        return ""

    def get_output_schema(self, template_name: str) -> dict:
        template = self.loader.get_template(template_name)
        schema_name = template.get("output_schema", "")
        return self.loader.get_output_schema(schema_name)

    def _check_condition(self, cond: str, context: dict) -> bool:
        if cond == "has_memory":
            return bool(context.get("memory_text", "").strip() and
                        context.get("memory_text", "无") != "无")
        if cond == "has_messages":
            return bool(context.get("messages_text", "").strip())
        if cond == "has_visible":
            return bool(context.get("visible_text", "").strip())
        if cond == "has_hearing":
            return bool(context.get("hearing_text", "").strip())
        if cond == "has_ambient":
            return bool(context.get("ambient_text", "").strip())
        if cond == "is_busy":
            return context.get("busy", False)
        return True
