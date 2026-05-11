#!/usr/bin/env python3
"""Monitor the 1-hour endurance test progress."""
import json, os, time, sys

LOG = "/home/asher/Documents/01_Projects/06_AgentWorld_Async/test_1hour_log.jsonl"
CONSOLE = "/tmp/test_1hour_final.log"

while True:
    os.system("clear")
    print(f"=== AgentWorld 1-Hour Test Monitor ===  {time.strftime('%H:%M:%S')}")
    print()

    # Log stats
    if os.path.exists(LOG):
        entries = []
        with open(LOG) as f:
            for line in f:
                try:
                    entries.append(json.loads(line.strip()))
                except: pass
        
        total = len(entries)
        actions = [e for e in entries if e["event"] == "action"]
        results = [e for e in entries if e["event"] == "result"]
        errors = [e for e in entries if e["event"] == "error"]
        agent_starts = [e for e in entries if e["event"] == "agent_begin"]
        agent_ends = [e for e in entries if e["event"] == "agent_end"]
        
        print(f"  Log entries: {total}  |  Actions: {len(actions)}  |  Errors: {len(errors)}")
        print(f"  Agents started: {len(agent_starts)}  |  Finished: {len(agent_ends)}")
        
        if entries:
            elapsed = entries[-1]["ts"]
            print(f"  Elapsed: {elapsed:.0f}s ({elapsed/60:.1f}min)")
        
        # Per-agent action count
        from collections import Counter
        c = Counter(a["agent"] for a in actions)
        if c:
            print(f"\n  Actions by agent:")
            for name, count in c.most_common():
                print(f"    {name:8s}: {count:3d}")
        
        # Recent errors
        if errors:
            print(f"\n  Recent errors:")
            for e in errors[-3:]:
                print(f"    {e.get('agent','?')}: {e.get('error','')[:80]}")
    else:
        print("  Log file not created yet...")
    
    # Console output (last 5 lines)
    print(f"\n  Console (last 5 lines):")
    if os.path.exists(CONSOLE):
        lines = open(CONSOLE).readlines()
        for l in lines[-5:]:
            print(f"    {l.rstrip()}")
    
    print(f"\n  [Ctrl+C to exit]")
    time.sleep(10)
