"""Global metric registry. Decouple eval from engine: zero src/ imports.

To add a new metric, write a function and decorate it:

    from .registry import register_metric

    @register_metric(name="my_metric", category="social", description="...", source="Paper Name")
    def my_metric(traces: list[dict]) -> dict:
        return {"value": 42}

Then import the module in metrics/__init__.py.
"""

REGISTRY: dict[str, dict] = {}


def register_metric(name: str, category: str = "general",
                    description: str = "", source: str = ""):
    def decorator(fn):
        REGISTRY[name] = {
            "fn": fn,
            "category": category,
            "description": description,
            "source": source,
        }
        return fn
    return decorator
