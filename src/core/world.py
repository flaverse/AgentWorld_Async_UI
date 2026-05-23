import yaml, os

from core.clock import SimClock
from core.spatial_grid import SpatialGrid
from core.lifecycle import EntityLifecycle
from entity.entity import Entity
from layers.base import Layer
from layers.visual import VisualLayer
from layers.auditory import AuditoryLayer
from layers.interaction import InteractionLayer
from layers.agent import AgentLayer
from agent.drives import DriveSystem
from agent.sensory_memory import SensoryMemory
from agent.memory import AgentMemory


class World:
    def __init__(self, world_config: dict, systems: dict):
        self.config = world_config.get("world", {})
        self._world_cfg = world_config
        time_scale = self.config.get("time_scale", 60)
        self.clock = SimClock(
            self.config.get("start_time", "08:00"),
            time_scale,
        )

        self.zones: dict[str, dict] = {}
        self.entities: dict[str, Entity] = {}
        self.grids: dict[str, SpatialGrid] = {}

        self.lifecycle = EntityLifecycle(self)
        self._slot_groups = self._load_slot_groups()
        self._attr_cfg = self.config.get("simulation", {}).get("drive", {}).get("attributes", {})

        for zone_def in world_config.get("zones", []):
            self.zones[zone_def["id"]] = zone_def
            self.grids[zone_def["id"]] = SpatialGrid(
                zone_def["width"], zone_def["height"], cell_size=5
            )

        self._load_entities(world_config.get("entities", []))

    def _load_slot_groups(self) -> dict:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base, "config", "slot_groups.yaml")
        with open(path) as f:
            return yaml.safe_load(f)

    def _resolve_group_mask(self, layer_name: str, group_id: str) -> dict:
        """Resolve a group row from slot_groups.yaml into a {slot: 0/1} mask."""
        groups_cfg = self._slot_groups.get(layer_name, {})
        columns = groups_cfg.get("columns", [])
        groups = groups_cfg.get("groups", {})
        row = groups.get(group_id, groups.get("default", [1] * len(columns)))
        return {col: int(row[i]) for i, col in enumerate(columns)}

    def _load_entities(self, entity_defs: list[dict]) -> None:
        world_group = self._world_cfg.get("world-group", "default")
        contract_group = "default"
        world_mask = self._resolve_group_mask("world", world_group)
        contract_mask = self._resolve_group_mask("contract", contract_group)
        # traits matrix: per-agent override, fallback default
        traits_matrix = self._world_cfg.get("traits", {})
        default_traits = traits_matrix.get("default", [])

        for ent_def in entity_defs:
            eid = ent_def["id"]
            entity = Entity(
                id=ent_def["id"],
                name=ent_def["name"],
                zone=ent_def["zone"],
                pos=list(ent_def.get("pos", [0, 0])),
                describe=ent_def.get("description", ent_def.get("describe", "")),
            )

            if "visual" in ent_def:
                v = ent_def["visual"]
                entity.layers["visual"] = VisualLayer(
                    visible_radius=v.get("visible_radius", 5),
                    sprite=v.get("sprite"),
                    properties=v.get("properties", v.get("info", {})),
                )

            if "interaction" in ent_def:
                inter = ent_def["interaction"]
                entity.layers["interaction"] = InteractionLayer(
                    interaction_radius=inter.get("interaction_radius", 2),
                    private_attrs=inter.get("private_attrs", {}),
                    hidden=inter.get("hidden", {}),
                    gate=inter.get("gate"),
                    properties=inter.get("properties", {}),
                    readonly=inter.get("readonly", False),
                    filepath=inter.get("filepath", ""),
                )

            if "agent" in ent_def:
                ag = ent_def["agent"]
                npc_group = ag.get("npc-group", "default")
                npc_mask = self._resolve_group_mask("npc", npc_group)
                slot_mask = {**contract_mask, **world_mask, **npc_mask}
                # traits: per-agent in matrix overrides default
                agent_traits = ag.get("traits") or traits_matrix.get(eid, default_traits)
                agent_layer = AgentLayer(
                    autonomous=ag.get("autonomous", False),
                    speed=ag.get("speed", 1.0),
                    view_radius=ag.get("view_radius", 20),
                    hearing_radius=ag.get("hearing_radius", 15),
                    interaction_radius=ag.get("interaction_radius", 3),
                    personality=ag.get("personality", ""),
                    template=ag.get("template", ""),
                    llm_provider=ag.get("llm_provider", ""),
                    slot_mask=slot_mask,
                    traits=agent_traits,
                )
                if entity.has("interaction"):
                    agent_layer.drives = DriveSystem(
                        attrs=entity.get("interaction").private_attrs,
                    )
                agent_layer.sensory = SensoryMemory()
                agent_layer.memory = AgentMemory()
                entity.layers["auditory"] = AuditoryLayer(
                    audible_radius=ag.get("hearing_radius", 15),
                    properties={"sound": ""})
                entity.layers["agent"] = agent_layer

            # Generic layers: any unknown layer type → base Layer
            for layer_name, layer_cfg in ent_def.get("layers", {}).items():
                if layer_name in entity.layers:
                    continue
                props = layer_cfg.get("properties", {})
                radius = layer_cfg.get("observable_radius", 5)
                entity.layers[layer_name] = Layer(
                    properties=props, observable_radius=radius)

            self.lifecycle.spawn(entity)

    def get_nearby_ids(self, zone_id: str, pos: list[int], radius: int) -> set[str]:
        grid = self.grids.get(zone_id)
        if grid:
            return grid.query_ids(pos, radius)
        return {eid for eid, e in self.entities.items()
                if e.zone == zone_id}

    def notify_moved(self, entity_id: str, old_pos: list[int], new_pos: list[int],
                     zone_id: str) -> None:
        grid = self.grids.get(zone_id)
        if grid:
            grid.move(entity_id, old_pos, new_pos)

    def update_entity(self, entity_id: str, updates: dict) -> None:
        """Apply dotted-path updates to entity properties. Blind execution — no schema."""
        entity = self.entities.get(entity_id)
        if not entity:
            return
        for path, value in updates.items():
            parts = path.split(".")
            target = entity
            for p in parts[:-1]:
                if hasattr(target, 'get'):
                    target = target.get(p)
                else:
                    target = getattr(target, p, None)
                if target is None:
                    break
            else:
                if hasattr(target, '__setitem__'):
                    target[parts[-1]] = value
                else:
                    setattr(target, parts[-1], value)

    def spawn_entity(self, entity_def: dict) -> Entity:
        """Create and spawn an entity from a dict at runtime. Same format as world.yaml."""
        # Reuse the per-entity logic from _load_entities
        saved = self.entities.copy()
        # Temporarily append the def to load
        self._load_entities([entity_def])
        # Find the newly created entity (it's the one not in saved)
        for eid in self.entities:
            if eid not in saved:
                return self.entities[eid]
        raise RuntimeError(f"Failed to spawn entity: {entity_def.get('id', '?')}")

    def despawn_entity(self, entity_id: str) -> bool:
        """Remove an entity from the world at runtime."""
        return self.lifecycle.despawn(entity_id)
