from string import Formatter


def safe_format(template: str, ctx: dict) -> str:
    """Only replace {key} where key exists in ctx. Leaves other braces alone."""
    result = []
    for literal, field, fmt, _ in Formatter().parse(template):
        result.append(literal)
        if field and field in ctx:
            val = ctx[field]
            result.append(format(val, fmt) if fmt else str(val))
        elif field:
            result.append("{" + field + ("}" if not fmt else f":{fmt}}}"))
    return "".join(result)


class PromptAssembler:
    def __init__(self, loader):
        self.loader = loader

    def assemble(self, template_name: str, ctx: dict, slot_mask: dict = None) -> str:
        tpl = self.loader.get_template(template_name)
        all_slots = self.loader.data.get("slots", {})
        parts = []
        for name in tpl.get("slots", []):
            if slot_mask is not None and not slot_mask.get(name, 1):
                continue
            slot = all_slots.get(name, {})
            cond = slot.get("condition", "")
            if cond and not bool(ctx.get(cond)):
                continue
            text = slot.get("template", "")
            if text:
                parts.append(safe_format(text, ctx))
        return "\n\n".join(parts)

    def get_system_prompt(self, template_name: str) -> str:
        tpl = self.loader.get_template(template_name)
        ref = tpl.get("system_prompt_ref", "")
        if ref:
            return self.loader.get_system_prompt(ref)
        return ""

    def get_output_schema(self, template_name: str) -> dict:
        tpl = self.loader.get_template(template_name)
        schema_name = tpl.get("output_schema", "")
        return self.loader.get_output_schema(schema_name)

    def get_temperature(self, template_name: str) -> float:
        tpl = self.loader.get_template(template_name)
        return tpl.get("temperature", 0.7)
