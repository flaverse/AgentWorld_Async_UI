import asyncio
from core.clock import WorldClock
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
        self.grids: dict[str, SpatialGrid] = {}

        self._systems = systems
        self.lifecycle = EntityLifecycle(self)

        for zone_def in world_config.get("zones", []):
            self.zones[zone_def["id"]] = zone_def
            self.grids[zone_def["id"]] = SpatialGrid(
                zone_def["width"], zone_def["height"], cell_size=5
            )

        self._load_entities(world_config.get("entities", []))

    def _load_entities(self, entity_defs: list[dict]) -> None:
        for ent_def in entity_defs:
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
                    sprite_sheet=v.get("sprite_sheet"),
                    properties=v.get("properties", v.get("info", {})),
                )

            if "interaction" in ent_def:
                inter = ent_def["interaction"]
                actions = {}
                for name, a in inter.get("actions", {}).items():
                    # New format: action has description + optional gate
                    # Keep backward compat: old format has resolve/rule/effects
                    adef = dict(a)  # shallow copy to avoid mutating YAML
                    actions[name] = adef
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
                    # DriveSystem 直接引用 private_attrs，非副本
                    # apply_deltas() 更新 interaction.private_attrs 后 drives 自动可见
                    agent_layer.drives = DriveSystem(
                        attrs=entity.get("interaction").private_attrs,
                        decay_rates=agent_layer.drive_rates,
                    )
                agent_layer.sensory = SensoryMemory()
                agent_layer.memory = AgentMemory()
                agent_layer.inbox = Inbox()
                # Auditory layer for speech output (observers poll this)
                from layers.auditory import AuditoryLayer
                entity.layers["auditory"] = AuditoryLayer(
                    audible_radius=ag.get("hearing_radius", 15),
                    properties={"sound": ""})
                entity.layers["agent"] = agent_layer

            if "gate" in ent_def:
                entity.layers["gate"] = ent_def["gate"]

            # Generic layers: any unknown layer type → base Layer
            for layer_name, layer_cfg in ent_def.get("layers", {}).items():
                if layer_name in entity.layers:
                    continue  # already handled above
                props = layer_cfg.get("properties", {})
                radius = layer_cfg.get("observable_radius", 5)
                entity.layers[layer_name] = Layer(
                    properties=props, observable_radius=radius)

            self.lifecycle.spawn(entity)

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
                    "entity_id": entity.id,
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
        self.lifecycle.spawn(event)

    def prune_events(self) -> None:
        now = self.clock.now()
        expired = [eid for eid, evt in self.active_events.items()
                   if evt.is_expired(now)]
        for eid in expired:
            del self.active_events[eid]
            self.lifecycle.despawn(eid)

    def register_external_agent(self, agent_id: str, name: str, zone: str,
                                pos: list[int], sprite: str | None = None,
                                personality: str = "来访者") -> Entity:
        """注册远程 Agent，返回 Entity 对象。
        外部 agent = autonomous=false 的普通 Entity，通过 WS/HTTP 操控。
        它仍能被 SensorySystem 感知，被 InteractionSystem 处理交互。
        """
        from layers.visual import VisualLayer
        from layers.interaction import InteractionLayer
        from layers.agent import AgentLayer
        from agent.sensory_memory import SensoryMemory
        from agent.inbox import Inbox
        from agent.memory import AgentMemory

        entity = Entity(id=agent_id, name=name, zone=zone, pos=pos,
                        describe=f"{name} (外部访客)")
        entity.layers["visual"] = VisualLayer(
            visible_radius=20,
            sprite=sprite,
            properties={"look": f"{name} (外部访客)"},
        )
        entity.layers["interaction"] = InteractionLayer(
            interaction_radius=3,
            public_attrs={"expression": "好奇地四处张望"},
            private_attrs={},
            actions={
                "交谈": {"description": f"和{name}交谈。他/她看起来很好奇。"},
            },
        )
        entity.layers["agent"] = AgentLayer(
            autonomous=False,
            speed=1.0,
            view_radius=20,
            hearing_radius=15,
            interaction_radius=3,
            personality=personality,
        )
        entity.get("agent").sensory = SensoryMemory()
        entity.get("agent").memory = AgentMemory()
        entity.get("agent").inbox = Inbox()
        from layers.auditory import AuditoryLayer
        entity.layers["auditory"] = AuditoryLayer(
            audible_radius=15,
            properties={"sound": ""})
        self.lifecycle.spawn(entity)
        return entity

    def get_nearby_ids(self, zone_id: str, pos: list[int], radius: int) -> set[str]:
        """Return entity_ids within radius. Uses spatial grid if available."""
        grid = self.grids.get(zone_id)
        if grid:
            return grid.query_ids(pos, radius)
        # Fallback: iterate all entities in zone
        return {eid for eid, e in self.entities.items()
                if e.zone == zone_id}

    def notify_moved(self, entity_id: str, old_pos: list[int], new_pos: list[int],
                     zone_id: str) -> None:
        """Called by Entity.move_to to update spatial grid."""
        grid = self.grids.get(zone_id)
        if grid:
            grid.move(entity_id, old_pos, new_pos)

    def get_systems(self):
        return self._systems

    # ── Event broadcast (set by main.py) ──
    _on_event: callable = None

    def set_event_callback(self, cb):
        self._on_event = cb

    async def emit_event(self, data: dict):
        if self._on_event:
            await self._on_event(data)
