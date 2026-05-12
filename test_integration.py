#!/usr/bin/env python3
"""Integration test: verification + component + free-text + LLM decision."""
import sys,os,yaml,asyncio,uuid,json,time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from core.world import World
from core.verification import Verifier, build_feedback
from systems.interaction import InteractionSystem
from systems.sensory import SensorySystem
from agent.brain import Brain
from prompt.loader import PromptLoader
from prompt.assembler import PromptAssembler
from llm.client import LLMClient

BASE = os.path.dirname(os.path.abspath(__file__))
results = {"pass": 0, "fail": 0}

def check(name, cond):
    if cond: results["pass"] += 1; print(f"  ✅ {name}")
    else: results["fail"] += 1; print(f"  ❌ {name}")

async def main():
    # ── 1. Load world ──
    with open(os.path.join(BASE,"config/world.yaml")) as f: wc = yaml.safe_load(f)
    with open(os.path.join(BASE,"config/llm.yaml")) as f: lc = yaml.safe_load(f)
    w = World(wc, {})
    print(f"1. World: {len(w.entities)} entities, {len(w.zones)} zones")
    check("entities loaded", len(w.entities) >= 23)
    check("zones loaded", len(w.zones) == 3)

    # ── 2. Test verification ──
    with open(os.path.join(BASE,"config/prompts.yaml")) as f: pc = yaml.safe_load(f)
    mask = pc["verification"]["projection_mask"]
    v = Verifier(mask=mask)
    
    # Test 2a: attribute_bounds
    effects = [{"entity_id":"geralt","deltas":{"coins":-999,"thirst":-30,"mood":5}}]
    failures = v.verify(effects, w.entities)
    check("attribute_bounds detects coin overflow", len(failures) >= 1)
    fb = build_feedback(failures)
    check("feedback generated", len(fb) > 50)

    # Test 2b: entity_existence
    effects2 = [{"entity_id":"nonexistent","deltas":{"mood":5}}]
    failures2 = v.verify(effects2, w.entities)
    check("entity_existence detects missing entity", len(failures2) >= 1)

    # Test 2c: conservation
    effects3 = [{"entity_id":"geralt","deltas":{"coins":-10}},
                {"entity_id":"dandelion","deltas":{"coins":5}}]
    failures3 = v.verify(effects3, w.entities)
    check("conservation detects imbalance", len(failures3) >= 1)

    # Test 2d: clean pass
    effects4 = [{"entity_id":"geralt","deltas":{"coins":-5,"thirst":-20}},
                {"entity_id":"dandelion","deltas":{"coins":5}}]
    failures4 = v.verify(effects4, w.entities)
    check("clean deltas pass all checks", len(failures4) == 0)

    # ── 3. Test component builder ──
    s = InteractionSystem(None)
    geralt = w.entities["geralt"]
    geralt.zone = "bar_zone"; geralt.pos = [6, 4]
    comp = s.build_component(geralt, w.entities, radius=3)
    check("component has center", any(c["entity_id"] == "geralt" for c in comp))
    check("component has nearby entities", len(comp) >= 3)

    # ── 4. Free-text action ──
    try:
        s.submit("test", geralt, w.entities["bar_counter"], "polish_the_counter", w)
        check("free-text action accepted", True)
    except Exception as e:
        check(f"free-text: {e}", False)

    # ── 5. Describe fields ──
    with_desc = sum(1 for e in w.entities.values() if hasattr(e, "describe"))
    check(f"all entities have describe ({with_desc})", with_desc >= 20)

    # ── 6. Prompt templates ──
    loader = PromptLoader(os.path.join(BASE,"config/prompts.yaml"))
    assembler = PromptAssembler(loader)
    for t in ["agent_decision","interaction_resolve","story_layer","projection_layer","memory_layer"]:
        tmpl = loader.get_template(t)
        check(f"template {t} exists", bool(tmpl))

    # ── 7. LLM decision ──
    llm = LLMClient(lc)
    brain = Brain(llm, assembler)
    SensorySystem().update(geralt, w.entities, w)
    al = geralt.get("agent")
    ctx = {
        "round": 1, "name": geralt.name, "personality": al.personality,
        "drives_table": al.drives.to_prompt_table(),
        "zone_name": "狐狸与鹅酒馆", "zone_width": 24, "zone_height": 16,
        "pos_x": geralt.pos[0], "pos_y": geralt.pos[1],
        "interactable_text": al.sensory.to_prompt_vision(),
        "visible_text": "", "memory_text": "无", "messages_text": "",
        "hearing_text": "",
    }
    t0 = time.time()
    d = await brain.decide(ctx)
    dt = time.time() - t0
    check(f"LLM decision ({dt:.1f}s)", bool(d.get("thinking")))

    # ── 8. Attribute bounds ──
    pa = geralt.get("interaction").private_attrs
    ok, fail = 0, 0
    for attr in ["thirst","hunger","social","energy","fun","mood"]:
        v = pa.get(attr, 0)
        if 0 <= v <= 100: ok += 1
        else: fail += 1
    if pa.get("coins", 0) >= 0: ok += 1
    else: fail += 1
    check(f"attribute bounds {ok}/{ok+fail}", fail == 0)

    # ── Summary ──
    total = results["pass"] + results["fail"]
    print(f"\n{'='*50}")
    print(f"  Results: {results['pass']}/{total} passed")
    if results["fail"]:
        print(f"  ❌ {results['fail']} FAILURES")
    else:
        print(f"  ✅ ALL PASSED")

if __name__ == "__main__":
    asyncio.run(main())
