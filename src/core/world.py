import asyncio
from core.clock import WorldClock
from entity.entity import Entity
from layers.visual import VisualLayer
from layers.interaction import InteractionLayer, ActionDef, TargetType, ResolveType
from layers.agent import AgentLayer
from agent.drives import DriveSystem
from agent.sensory_memory import SensoryMemory
from agent.memory import AgentMemory
from agent.inbox import Inbox
from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem, ActionResult
from systems.decay import DecaySystem


class World:
    def __init__(self, world_config: dict, systems: dict):
        self.config = world_config.get("world", {})
        time_scale = self.config.get("time_scale", 60)
        self.clock = WorldClock(
            self.config.get("start_time", "08:00"),
            time_scale,
        )
        self.time_scale = time_scale

        self.zones: dict[str, dict] = {}
        self.entities: dict[str, Entity] = {}
        self.active_events: dict = {}

        self._systems = systems

        for zone_def in world_config.get("zones", []):
            self.zones[zone_def["id"]] = zone_def

        self._load_entities(world_config.get("entities", []))

    def _load_entities(self, entity_defs: list[dict]) -> None:
        for ent_def in entity_defs:
            entity = Entity(
                id=ent_def["id"],
                name=ent_def["name"],
                zone=ent_def["zone"],
                pos=list(ent_def.get("pos", [0, 0])),
            )

            if "visual" in ent_def:
                v = ent_def["visual"]
                entity.layers["visual"] = VisualLayer(
                    visible_radius=v.get("visible_radius", 5),
                    sprite=v.get("sprite"),
                    sprite_sheet=v.get("sprite_sheet"),
                    info=v.get("info", {}),
                )

            if "interaction" in ent_def:
                inter = ent_def["interaction"]
                actions = {}
                for name, a in inter.get("actions", {}).items():
                    actions[name] = ActionDef(
                        method=name,
                        target_type=TargetType(a.get("target_type", "passive")),
                        resolve=ResolveType(a.get("resolve", "rule")),
                        params=a.get("params", {}),
                        rule=a.get("rule"),
                        estimated_duration=a.get("estimated_duration", 5),
                    )
                entity.layers["interaction"] = InteractionLayer(
                    interaction_radius=inter.get("interaction_radius", 2),
                    public_attrs=inter.get("public_attrs", {}),
                    private_attrs=inter.get("private_attrs", {}),
                    actions=actions,
                )

            if "agent" in ent_def:
                ag = ent_def["agent"]
                agent_layer = AgentLayer(
                    autonomous=ag.get("autonomous", False),
                    speed=ag.get("speed", 1.0),
                    view_radius=ag.get("view_radius", 20),
                    hearing_radius=ag.get("hearing_radius", 15),
                    interaction_radius=ag.get("interaction_radius", 3),
                    personality=ag.get("personality", ""),
                    drive_rates={k: v.get("decay", 0)
                                 for k, v in ag.get("drives", {}).items()},
                )
                if entity.has("interaction"):
                    init_attrs = entity.get("interaction").private_attrs
                    agent_layer.drives = DriveSystem(
                        values={k: init_attrs.get(k, 50)
                                for k in agent_layer.drive_rates},
                        decay_rates=agent_layer.drive_rates,
                    )
                agent_layer.sensory = SensoryMemory()
                agent_layer.memory = AgentMemory()
                agent_layer.inbox = Inbox()
                entity.layers["agent"] = agent_layer

            if "gate" in ent_def:
                entity.layers["gate"] = ent_def["gate"]

            self.entities[entity.id] = entity

    def get_zone_data(self, zone_id: str) -> dict:
        return self.zones.get(zone_id, {})

    def get_ambient_entities(self, center: Entity, radius: int,
                             exclude: set[str]) -> list[dict]:
        ambient = []
        for entity in self.entities.values():
            if entity.id in exclude:
                continue
            if entity.zone != center.zone:
                continue
            d = center.distance_to(entity)
            if d <= radius and entity.has("visual") and entity.has("interaction"):
                ambient.append({
                    "name": entity.name,
                    "distance": d,
                    "visual": entity.get("visual").see(d),
                    "private_hint": entity.get("interaction").private_attrs,
                })
        return ambient

    def send_message(self, from_id: str, to_id: str, method: str = "",
                     content: str = "") -> None:
        target = self.entities.get(to_id)
        if not target or not target.has("agent"):
            return
        from_entity = self.entities.get(from_id)
        from_name = from_entity.name if from_entity else from_id
        target.get("agent").inbox.send(from_id, from_name, method, content)

    def spawn_event(self, event) -> None:
        self.active_events[event.id] = event
        self.entities[event.id] = event

    def prune_events(self) -> None:
        now = self.clock.now()
        expired = [eid for eid, evt in self.active_events.items()
                   if evt.is_expired(now)]
        for eid in expired:
            del self.active_events[eid]
            self.entities.pop(eid, None)

    def get_systems(self):
        return self._systems
