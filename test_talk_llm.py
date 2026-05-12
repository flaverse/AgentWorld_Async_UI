#!/usr/bin/env python3
"""Quick test: 交谈 now uses LLM resolver."""
import sys,os,yaml,asyncio,uuid,time
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from core.world import World
from agent.brain import Brain
from agent.drives import DriveSystem
from prompt.loader import PromptLoader
from prompt.assembler import PromptAssembler
from llm.client import LLMClient
from systems.sensory import SensorySystem
from systems.interaction import InteractionSystem
from systems.decay import DecaySystem
from interaction.resolver import InteractionResolver

BASE = os.path.dirname(os.path.abspath(__file__))
act_types = Counter()

async def main():
    with open(os.path.join(BASE,"config","world.yaml")) as f: wc=yaml.safe_load(f)
    with open(os.path.join(BASE,"config","llm.yaml")) as f: lc=yaml.safe_load(f)
    loader=PromptLoader(os.path.join(BASE,"config","prompts.yaml"))
    assembler=PromptAssembler(loader)
    llm=LLMClient(lc); brain=Brain(llm,assembler); resolver=InteractionResolver(llm,assembler)
    systems={"sensory":SensorySystem(),"interaction":InteractionSystem(resolver),"decay":DecaySystem()}
    world=World(wc,systems)

    EXTRA=[
        {"id":"vesemir","name":"维瑟米尔","zone":"bar_zone","pos":[20,8],"personality":"老猎魔人","coins":200,"thirst":50,"hunger":40,"social":30,"mood":55},
        {"id":"triss","name":"特莉丝","zone":"square","pos":[35,15],"personality":"女术士","coins":300,"thirst":35,"hunger":45,"social":25,"mood":50},
        {"id":"zoltan","name":"卓尔坦","zone":"bar_zone","pos":[15,10],"personality":"矮人商人","coins":500,"thirst":65,"hunger":50,"social":60,"mood":70},
        {"id":"keira","name":"凯拉","zone":"herb_hut","pos":[8,3],"personality":"年轻女术士","coins":150,"thirst":30,"hunger":55,"social":15,"mood":60},
        {"id":"lambert","name":"兰伯特","zone":"square","pos":[20,10],"personality":"猎魔人","coins":100,"thirst":70,"hunger":60,"social":15,"mood":40},
    ]
    for npc in EXTRA:
        world.register_external_agent(npc["id"],npc["name"],npc["zone"],npc["pos"],personality=npc["personality"])
        e=world.entities[npc["id"]]
        e.get("interaction").private_attrs.update({k:v for k,v in npc.items() if k in ("coins","hunger","thirst","social","energy","fun","mood")})
        e.get("agent").drives=DriveSystem(attrs=e.get("interaction").private_attrs,decay_rates={"thirst":0.022,"hunger":0.018,"social":0.015,"energy":-0.01,"fun":0.015})

    agents=[world.entities[a] for a in ["geralt","yennefer","dandelion","vesemir","triss","zoltan","keira","lambert"]]
    print("="*50)
    print("  Talk=LLM Test — 交谈 now resolve:llm")
    print("="*50)

    per_agent=55
    for agent in agents:
        name=agent.name
        al=agent.get("agent")
        end=time.time()+per_agent
        acts=0
        while time.time()<end:
            elapsed=max(world.clock.now()-agent.last_action_time,0)
            systems["decay"].tick(agent,elapsed)
            systems["sensory"].update(agent,world.entities,world)
            systems["interaction"].update_sensory(agent,world.entities)
            world.prune_events()
            if agent.busy_result is not None:
                r=agent.busy_result; agent.busy_result=None
                systems["interaction"].apply_result(r,agent,world)
            if agent.status=="idle":
                sensory=al.sensory; al.inbox.drain()
                ctx={
                    "round":acts+1,"name":agent.name,"personality":al.personality,
                    "drives_table":al.drives.to_prompt_table(),
                    "zone_name":world.zones.get(agent.zone,{}).get("name",""),
                    "zone_width":40,"zone_height":30,
                    "pos_x":agent.pos[0],"pos_y":agent.pos[1],
                    "interactable_text":sensory.to_prompt_vision(),
                    "visible_text":"","memory_text":al.memory.to_prompt_text(3),
                    "messages_text":"","hearing_text":sensory.to_prompt_hearing(),
                }
                d=await brain.decide(ctx)
                mv=d.get("move_to")
                if mv and isinstance(mv,list) and len(mv)==2:
                    agent.move_to(mv); agent.last_action_time=world.clock.now()
                    systems["sensory"].update(agent,world.entities,world)
                    systems["interaction"].update_sensory(agent,world.entities)
                tid=d.get("target_entity"); an=d.get("action")
                if tid and an and tid in world.entities:
                    tgt=world.entities[tid]; il=tgt.get("interaction")
                    if il and il.get_action(an):
                        ad=il.get_action(an)
                        if ad.target_type.value=="passive":
                            if systems["interaction"].can_interact(agent,tgt):
                                systems["interaction"].submit(uuid.uuid4().hex[:8],agent,tgt,an,world)
                                agent.last_action_time=world.clock.now()
                                acts+=1; act_types[an]+=1
            await asyncio.sleep(2 if agent.status=="busy" else 1.5)
        pa=agent.get("interaction").private_attrs
        print(f"  {name:6s}: {acts} act  thirst={pa.get('thirst',0):.0f} coins={pa['coins']:.0f} mood={pa['mood']:.0f}", flush=True)

    total=sum(1 for _ in act_types.elements())
    print(f"\nTotal: {total} actions")
    for act,cnt in act_types.most_common():
        print(f"  {act:10s}: {cnt:3d} ({cnt/total*100:.0f}%)")
    # Compare: if 交谈 > 0, show ratio
    talk_cnt=act_types.get("交谈",0)
    print(f"\n  Talk ratio: {talk_cnt/total*100:.0f}% (vs 66% before)")

if __name__=="__main__":
    asyncio.run(main())
