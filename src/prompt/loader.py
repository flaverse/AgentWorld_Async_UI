import yaml


class PromptLoader:
    def __init__(self, config_path: str):
        with open(config_path, encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

    def get_system_prompt(self, name: str) -> str:
        return self.data.get("system_prompts", {}).get(name, "")

    def get_template(self, name: str) -> dict:
        return self.data.get("templates", {}).get(name, {})

    def get_output_schema(self, name: str) -> dict:
        return self.data.get("output_schemas", {}).get(name, {})
