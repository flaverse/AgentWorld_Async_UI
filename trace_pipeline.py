#!/usr/bin/env python3
"""Trace one interaction pipeline: LLM #1 -> submit -> LLM #2."""
import sys,os,yaml,asyncio,uuid,json,time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from core.world import World; from agent.brain import Brain
from prompt.loader import PromptLoader; from prompt.assembler import PromptAssembler
from llm.client import LLMClient; from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem; from systems.decay import DecaySystem
from interaction.resolver import InteractionResolver

BASE = os.path.dirname(os.path.abspath(__file__))

async def main():
    with open(os.path.join(BASE,"config/world.yaml")) as f: wc=yaml.safe_load(f)
    with open(os.path.join(BASE,"config/llm.yaml")) as f: lc=yaml.safe_load(f)
    loader=PromptLoader(os.path.join(BASE,"config/prompts.yaml"))
    assembler=PromptAssembler(loader); llm=LLMClient(lc)
    brain=Brain(llm,assembler); resolver=InteractionResolver(llm,assembler)
    systems={"sensory":SensorySystem(),"interaction":InteractionSystem(resolver),"decay":DecaySystem()}
    world=World(wc,systems)

    geralt=world.entities["geralt"]; geralt.zone="bar_zone"; geralt.pos=[6,4]
    dandelion=world.entities["dandelion"]; dandelion.zone="bar_zone"; dandelion.pos=[6,5]
    systems["sensory"].update(geralt,world.entities,world)
    systems["interaction"].update_sensory(geralt,world.entities)

    al=geralt.get("agent")
    ctx={"round":1,"name":geralt.name,"personality":al.personality,
         "drives_table":al.drives.to_prompt_table(),
         "zone_name":"狐狸与鹅酒馆","zone_width":24,"zone_height":16,
         "pos_x":geralt.pos[0],"pos_y":geralt.pos[1],
         "interactable_text":al.sensory.to_prompt_vision(),
         "visible_text":"","memory_text":"无","messages_text":"","hearing_text":""}

    print("="*60)
    print("  Pipeline Trace: LLM #1 -> Submit -> LLM #2")
    print("="*60)

    # ── LLM #1 ──
    prompt1=assembler.assemble("agent_decision",ctx)
    print("\n=== LLM #1 INPUT ===")
    print(prompt1[:800])
    print("...(truncated)")
    
    t1=time.time(); decision=await brain.decide(ctx); dt1=time.time()-t1
    print(f"\n=== LLM #1 OUTPUT ({dt1:.1f}s) ===")
    print(json.dumps(decision,ensure_ascii=False,indent=2))

    # ── Submit ──
    tid=decision.get("target_entity"); an=decision.get("action")
    if not tid or not an or tid not in world.entities:
        print("No valid target/action"); return
    
    target=world.entities[tid]; il=target.get("interaction")
    print(f"\n=== INTERACTION SYSTEM ===")
    print(f"  target: {target.name} | action: \"{an}\" | predefined: {bool(il and il.get_action(an))}")

    ambient=world.get_ambient_entities(target,radius=2,exclude={geralt.id})
    comp=systems["interaction"].build_component(target,world.entities,radius=3)
    print(f"  component: {[c['name'] for c in comp]}")
    print(f"  ambient: {len(ambient)} entities")

    # ── LLM #2 ──
    rctx={"caller_name":geralt.name,
          "caller_public":json.dumps(geralt.get("interaction").public_attrs,ensure_ascii=False) if geralt.has("interaction") else "{}",
          "caller_private":json.dumps(geralt.get("interaction").private_attrs,ensure_ascii=False) if geralt.has("interaction") else "{}",
          "target_name":target.name,
          "target_public":json.dumps(il.public_attrs,ensure_ascii=False) if il else "{}",
          "target_private":json.dumps(il.private_attrs,ensure_ascii=False) if il else "{}",
          "action":an,
          "ambient_text":resolver._format_ambient(ambient)}
    prompt2=assembler.assemble("interaction_resolve",rctx)
    print(f"\n=== LLM #2 INPUT ===")
    print(prompt2)

    t2=time.time()
    result=await resolver.resolve(caller=geralt,target=target,action=an,ambient_entities=ambient,world=world)
    dt2=time.time()-t2

    print(f"\n=== LLM #2 OUTPUT ({dt2:.1f}s) ===")
    print(f"  narrative: {result.narrative}")
    print(f"  caller_deltas: {result.caller_deltas}")
    print(f"  target_deltas: {result.target_deltas}")
    print(f"  ambient_effects: {result.ambient_effects}")
    print(f"  public_observation: {result.public_observation}")

    print(f"\nTotal: {(dt1+dt2):.1f}s (LLM#1={dt1:.1f}s + LLM#2={dt2:.1f}s)")

if __name__=="__main__":
    asyncio.run(main())
