"""GuiEmitter — spatial + stats event broadcast to WebSocket clients.

Independent of DashboardEmitter. Uses fire-and-forget pattern with
per-client asyncio.Queue (maxsize=200). Late joiners receive a full
world_init snapshot for catch-up.
"""
import json
import time
import asyncio


class GuiEmitter:
    def __init__(self, world, history_size: int = 50):
        self._clients: list[asyncio.Queue] = []
        self._world = world
        self._start_ts = time.time()
        self._interaction_counts: dict[tuple, int] = {}
        self._history: list[dict] = []
        self._history_size = history_size
        self._snapshot_interval: float = 5.0
        self._drive_task: asyncio.Task | None = None

    # ── client lifecycle ──

    async def register(self) -> asyncio.Queue:
        q = asyncio.Queue(maxsize=200)
        init = self._build_world_init()
        payload = json.dumps(init, ensure_ascii=False)
        await q.put(payload)
        # replay recent history for late-join catch-up
        for evt in self._history:
            await q.put(json.dumps(evt, ensure_ascii=False))
        self._clients.append(q)
        return q

    def unregister(self, q: asyncio.Queue):
        if q in self._clients:
            self._clients.remove(q)

    # ── emit ──

    def emit(self, event: dict):
        event["ts"] = round(time.time() - self._start_ts, 1)
        if event.get("type") == "interaction":
            key = (event["agent_id"], event["target_id"])
            self._interaction_counts[key] = self._interaction_counts.get(key, 0) + 1
        payload = json.dumps(event, ensure_ascii=False)
        # keep history for catch-up
        self._history.append(event)
        if len(self._history) > self._history_size:
            self._history.pop(0)
        for q in self._clients:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    # ── world init snapshot ──

    def _build_world_init(self) -> dict:
        zones = []
        for zid, z in self._world.zones.items():
            zones.append({
                "id": zid, "name": z.get("name", zid),
                "width": z.get("width", 60), "height": z.get("height", 40),
            })
        entities = []
        for eid, e in self._world.entities.items():
            etype = "agent" if e.has("agent") else "object"
            sprite = None
            if e.has("visual"):
                sprite = e.get("visual").sprite
            entities.append({
                "id": eid, "name": e.name, "zone": e.zone,
                "pos": list(e.pos), "type": etype, "sprite": sprite,
            })
        return {"type": "world_init", "ts": 0.0, "zones": zones, "entities": entities}

    # ── periodic snapshots ──

    async def _drive_snapshot_loop(self):
        while True:
            await asyncio.sleep(self._snapshot_interval)
            try:
                ts = round(time.time() - self._start_ts, 1)

                # pos_snapshot: all entity positions for smooth map updates
                pos_list = []
                for eid, e in self._world.entities.items():
                    pos_list.append({
                        "id": eid, "zone": e.zone, "pos": list(e.pos),
                    })
                self.emit({"type": "pos_snapshot", "entities": pos_list})

                # drive_snapshot: per-agent drive values
                snapshots = {}
                for eid, e in self._world.entities.items():
                    if e.has("agent"):
                        al = e.get("agent")
                        if al is not None and al.drives is not None:
                            snapshots[eid] = {
                                k: round(float(v), 1)
                                for k, v in al.drives.attrs.items()
                            }
                if snapshots:
                    self.emit({"type": "drive_snapshot", "snapshots": snapshots})

                # interaction_heatmap
                pairs = [
                    {"agent": k[0], "target": k[1], "count": v}
                    for k, v in self._interaction_counts.items()
                ]
                self.emit({"type": "interaction_heatmap", "pairs": pairs})
            except Exception:
                pass  # never kill the loop on transient world-read errors

    def start_snapshots(self, interval: float = 5.0):
        self._snapshot_interval = interval
        self._drive_task = asyncio.ensure_future(self._drive_snapshot_loop())

    async def stop_snapshots(self):
        if self._drive_task:
            self._drive_task.cancel()
            try:
                await self._drive_task
            except asyncio.CancelledError:
                pass
