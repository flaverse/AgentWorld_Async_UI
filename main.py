import yaml
import asyncio
import uuid
import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_dir, "src"))

from core.world import World
from agent.brain import Brain
from prompt.loader import PromptLoader
from prompt.assembler import PromptAssembler
from llm.client import LLMClient
from interaction.resolver import InteractionResolver
from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem
from systems.decay import DecaySystem
from api.server import start_api_server


async def demo_loop(world, brain, systems, max_actions=5):
    agents = [e for e in world.entities.values()
              if e.get("agent") and e.get("agent").autonomous]
    if not agents:
        print("No autonomous agents found!")
        return

    agent = agents[0]
    agent_layer = agent.get("agent")

    print(f"Found agent: {agent.name}")
    print(f"  Personality: {agent_layer.personality}")
    print()
    print("=" * 60)
    print("  异步 Multi-Agent 自主世界 — Demo")
    print("=" * 60)

    action_count = 0
    while action_count < max_actions:
        agent_layer = agent.get("agent")
        drives = agent_layer.drives

        elapsed = world.clock.now() - agent.last_action_time
        if elapsed < 0:
            elapsed = 0

        # Decay
        systems["decay"].tick(agent, elapsed)

        # Sense
        systems["sensory"].update(agent, world.entities, world)
        systems["interaction"].update_sensory(agent, world.entities)
        world.prune_events()

        # Check busy result
        if agent.busy_result is not None:
            result = agent.busy_result
            agent.busy_result = None
            systems["interaction"].apply_result(result, agent, world)

            # Frontend event
            await world.emit_event({
                "event": "interaction_complete",
                "agent": agent.id, "agent_name": agent.name,
                "observation": result.narrative[:80],
            })
            if result.move_to_zone:
                await world.emit_event({
                    "event": "zone_change", "agent": agent.id,
                    "zone": {"name": world.zones[result.move_to_zone]["name"],
                             "id": result.move_to_zone},
                })

            print(f"\n⏱  {world.clock.time_str()} | {agent.name} ({agent.pos[0]},{agent.pos[1]})")
            print(f"  📖 {result.narrative}")
            if result.caller_deltas:
                print(f"     → 状态变化: {result.caller_deltas}")
            if result.ambient_effects:
                print(f"     → 周边影响: {result.ambient_effects}")

        # Decide if idle
        if agent.status == "idle":
            zone_data = world.get_zone_data(agent.zone)
            sensory = agent_layer.sensory
            memory = agent_layer.memory
            inbox_msgs = agent_layer.inbox.drain()

            # Build visible-only section from sensory
            visible_text = ""
            visible_only = sensory.get_visible_only()
            if visible_only:
                parts = []
                for r in visible_only:
                    parts.append(f"  id={r.entity_id} | {r.name} ({r.pos[0]},{r.pos[1]}) | dist={r.distance}")
                visible_text = "\n".join(parts)

            # Build messages section from inbox
            messages_text = ""
            if inbox_msgs:
                messages_text = "\n".join(
                    f"- {m.from_agent_name}: \"{m.content[:50]}\"" for m in inbox_msgs
                )

            context = {
                "round": action_count + 1,
                "name": agent.name,
                "personality": agent_layer.personality,
                "drives_table": drives.to_prompt_table(),
                "zone_name": zone_data.get("name", ""),
                "zone_width": zone_data.get("width", 0),
                "zone_height": zone_data.get("height", 0),
                "pos_x": agent.pos[0],
                "pos_y": agent.pos[1],
                "interactable_text": sensory.to_prompt_vision(),
                "visible_text": visible_text,
                "memory_text": memory.to_prompt_text(5),
                "messages_text": messages_text,
                "hearing_text": sensory.to_prompt_hearing(),
            }

            # P/Q/KL 三层分布
            from core.kl_divergence import compute_kl
            p = agent.p_distribution if agent.p_distribution else {}
            q_drives = {k: round(float(v), 1) for k, v in drives.attrs.items()}
            # Q distribution (current, temporary)
            q = {
                "pos": list(agent.pos), "zone": agent.zone,
                "drives": q_drives,
                "coins": round(float(agent.get("interaction").private_attrs.get("coins", 0))),
                "interactable": [r.name for r in sensory.get_interactable()],
                "visible": [r.name for r in sensory.get_visible_only()],
            }
            kl_text = compute_kl(p, q) if p else ""

            context["kl_text"] = kl_text

            print(f"\n⏱  {world.clock.time_str()} | {agent.name} ({agent.pos[0]},{agent.pos[1]})")
            inter = agent.get("interaction")
            if inter:
                pa = inter.private_attrs
                print(f"  💭 想下一步... (thirst={pa.get('thirst',0):.0f} coins={pa.get('coins',0)})")
            # Frontend time event
            await world.emit_event({
                "event": "world_time",
                "time": world.clock.time_str(),
            })

            decision = await brain.decide(context)

            action_text = decision.get("action")
            
            if action_text and isinstance(action_text, str) and action_text.strip():
                # Engine auto-parses: find target entity from action text + nearby entities
                systems["sensory"].update(agent, world.entities, world)
                systems["interaction"].update_sensory(agent, world.entities)

                target = systems["interaction"].find_entity_at(
                    agent.zone, agent.pos, action_text, world.entities, exclude_id=agent.id
                )

                if target:
                    # Auto-move to target if not in range
                    if not systems["interaction"].can_interact(agent, target):
                        move_time = agent.move_to(list(target.pos))
                        print(f"  🚶 → ({target.pos[0]},{target.pos[1]})", flush=True)
                        systems["sensory"].update(agent, world.entities, world)
                        systems["interaction"].update_sensory(agent, world.entities)

                    # Re-check after move
                    if systems["interaction"].can_interact(agent, target):
                        # Set target busy (v3)
                        if target.has("agent") and target.get("agent").autonomous:
                            target.status = "busy"

                        story = decision.get("story", "")
                        iid = uuid.uuid4().hex[:8]
                        systems["interaction"].submit(iid, agent, target, action_text, world, story=story)
                        agent.last_action_time = world.clock.now()
                        action_count += 1
                        print(f"  🎯 → {target.name}", flush=True)
                    else:
                        agent.get("agent").memory.record(
                            text=f"想找{target.name}但对方已不在附近"
                        )
                else:
                    # No specific target found — just a movement or rest action
                    print(f"  🚶 {action_text[:40]}...", flush=True)
                    await asyncio.sleep(3)  # Short rest for "look around" actions
            else:
                # action is null or empty — rest
                print(f"  😴 歇会...", flush=True)
                await asyncio.sleep(5)

        # Snapshot P distribution for next cycle
        q_sensory = agent.get("agent").sensory
        agent.p_distribution = {
            "pos": list(agent.pos),
            "zone": agent.zone,
            "drives": {k: round(float(v), 1) for k, v in agent.get("agent").drives.attrs.items()},
            "coins": round(float(agent.get("interaction").private_attrs.get("coins", 0))),
            "interactable": [r.name for r in q_sensory.get_interactable()],
            "visible": [r.name for r in q_sensory.get_visible_only()],
        }

        if agent.status == "busy":
            remaining = agent.busy_until - world.clock.now()
            wait = max(0.5, min(remaining / world.time_scale, 3.0))
        else:
            wait = 1.0
        await asyncio.sleep(wait)

    # Wait for final result
    print("\n等待最后的裁定结果...")
    await systems["interaction"].await_pending(timeout=15)
    if agent.busy_result is not None:
        result = agent.busy_result
        agent.busy_result = None
        systems["interaction"].apply_result(result, agent, world)
        print(f"  📖 {result.narrative}")

    # Final snapshot
    inter = agent.get("interaction")
    print(f"\n{'=' * 60}")
    print(f"  最终状态 | {world.clock.time_str()} | {agent.name}")
    print("=" * 60)
    if inter:
        pa = inter.private_attrs
        print(f"  thirst={pa.get('thirst',0):.0f}  hunger={pa.get('hunger',0):.0f}  coins={pa.get('coins',0)}  energy={pa.get('energy',0):.0f}  fun={pa.get('fun',0):.0f}  mood={pa.get('mood',0):.0f}")
    print()
    print("记忆:")
    for entry in agent_layer.memory.entries:
        print(f"  {entry.get('narrative', '?')}")


async def main():
    # Load configs
    with open(os.path.join(base_dir, "config/world.yaml")) as f:
        world_cfg = yaml.safe_load(f)
    with open(os.path.join(base_dir, "config/llm.yaml")) as f:
        llm_cfg = yaml.safe_load(f)

    loader = PromptLoader(os.path.join(base_dir, "config/prompts.yaml"))
    assembler = PromptAssembler(loader)
    llm = LLMClient(llm_cfg)
    brain = Brain(llm, assembler)
    resolver = InteractionResolver(llm, assembler)

    sound_map = {
        "饮用": "杯子碰吧台的清脆声",
        "交谈": "低声的说话声",
        "倚靠": "吧台轻微的吱呀声",
        "捡起": "硬币落地的叮当声",
    }
    systems = {
        "sensory": SensorySystem(),
        "interaction": InteractionSystem(resolver, sound_map),
        "decay": DecaySystem(),
    }

    world = World(world_cfg, systems)

    # Wire EventBus: multi-modal push broadcast
    def on_entity_event(event, entity_id, zone, pos):
        systems["sensory"].broadcast_speech(entity_id, zone, pos, world)
    world.event_bus.on("entity.spoke_or_gestured", on_entity_event)

    # Wire frontend broadcast
    from api.server import broadcast_to_frontend
    world.set_event_callback(broadcast_to_frontend)

    # Start API server in a daemon thread
    start_api_server(world, host="0.0.0.0", port=8000)
    print("🌐 API server: http://0.0.0.0:8000")
    print("   前端: http://0.0.0.0:8000")
    print()

    # Run demo loop as background task (keeps world alive)
    async def safe_demo():
        try:
            await demo_loop(world, brain, systems, max_actions=20)
        except Exception as e:
            import traceback
            print(f"[demo] crashed: {e}")
            traceback.print_exc()
        print("[demo] finished")
    asyncio.create_task(safe_demo())

    # Keep server alive
    print("按 Ctrl+C 停止...")
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    asyncio.run(main())
