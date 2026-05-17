# The Slot Vector Architecture: Declarative Prompt Composition for Autonomous LLM Agents

**Anonymous authors**

---

## Abstract

Large language model (LLM) agents typically embed their cognitive architecture—memory retrieval, reflection, planning, and importance evaluation—directly in Python code. The dominant paradigm requires hundreds of lines of code solely to manage how and when the LLM thinks, separate from world simulation. We present the **Slot Vector Architecture** (SVA), a declarative alternative that reduces the entire cognitive stack to 45 lines of assembler code and a configurable ordered list of prompt fragments (slots). Formally, a slot $s = (c, t)$ is a condition-template pair: $t$ renders into the LLM's decision prompt iff the runtime context satisfies $c$. A template $T = [s_1, \ldots, s_n]$ is an ordered slot sequence defining both which cognitive capabilities are active and their relative priority. The LLM maintains its own persistent goal via a self-updating `main_thread` field, and self-regulates against repetition without any external deduplication filter. We further introduce a **P/Q/KL attention gate**: the agent acts only when its internal world prediction $P$ diverges from sensory input $Q$, eliminating timer-based reflection cycles. Experiments with 25 agents across 3 zones produce 1,196 actions in 180s (89% social), with 0.7% adjacent repetition—achieved without any external repetition filter. The entire codebase totals ~1,800 lines of Python, of which zero are cognitive code: all agent behavior is configured in ~820 lines of YAML.

---

## 1. Introduction

LLM agents are typically built by embedding cognitive logic—when to reflect, what to remember, how to evaluate importance—directly in the programming language hosting the agent loop. The influential Generative Agents work (Park et al., 2023) uses ~730 lines of Python just to manage the LLM's *thinking process*, separate from world simulation: retrieve (200 lines), importance-score (80), reflect (150), and plan (200). These lines do not simulate the world; they orchestrate the LLM's cognitive workflow.

We argue this conflates two fundamentally distinct responsibilities: **physics simulation** (who is where, what changed) and **cognitive judgment** (what matters, what to do). When code makes cognitive judgments—"this memory is important," "you should reflect now," "don't repeat yourself"—it limits the LLM's autonomy and hardens the system against adaptation.

We propose three design principles:

1. **Engine provides facts; LLM provides judgments.** Code should report *what is*; the LLM should decide *what matters*.
2. **Cognition is prompt composition, not code.** Every cognitive capability can be expressed as a declarative prompt fragment—a *slot*—with a condition for activation and a template for content.
3. **Removal is the direction of progress.** Each deletion of a hardcoded cognitive rule restores decision-making autonomy to the LLM. The v1→v7 evolution of our system empirically validates this.

We instantiate these principles in **AgentWorld Async**, a multi-agent autonomous world engine where up to 25 LLM-driven agents socialize across multiple zones. Our contributions are:

- **Slot Vector Architecture (SVA)** (§3): A formal declarative framework for agent cognition. Adding a new cognitive capability requires zero code changes—only a YAML entry and a template reference.
- **P/Q/KL Attention Gate** (§3.3): An event-driven activation mechanism based on prediction error. Agents act only when $P \neq Q$, not on timers.
- **Empirical validation** (§5): 25-agent deployment producing 1,196 actions with 0.7% repetition, 0 lines of cognitive code, and emergent social structure.
- **Ablation studies** (§5.3-5.5): Isolating the effects of dict-copy correctness, memory format, and idle guidance on agent behavior.

---

## 2. Related Work

**LLM Agent Architectures.** Generative Agents (Park et al., 2023) established the multi-phase agent loop: perceive → retrieve → plan → reflect → act, each as separate code modules. Subsequent frameworks—AutoGen (Wu et al., 2023), CAMEL (Li et al., 2023), CrewAI, LangChain—provide tool-calling pipelines but retain imperative cognitive orchestration. Voyager (Wang et al., 2023) uses an automatic curriculum for exploration but hardcodes the skill library management.

**Declarative Prompt Composition.** Constitutional AI (Bai et al., 2022) uses a static list of principles to guide model behavior, but these are always active and unordered. DSPy (Khattab et al., 2023) composes LLM calls into declarative modules, but modules are Python classes requiring code changes for new capabilities. LangChain's PromptTemplate supports variable substitution but not conditional activation or priority ordering. Our contribution is the *ordered, conditional, pure-declaration* composition—a template's slot list *is* the cognitive architecture.

**Prediction Error in Agents.** The free energy principle (Friston, 2010; Parr et al., 2022) posits that biological agents act to minimize prediction error. Our P/Q/KL gate operationalizes this symbolically: $P$ is the agent's internal world model, $Q$ is sensory input, and action occurs when $\|Q - P\| > 0$. This connects to active inference but in a purely discrete, LLM-driven domain.

**Memory in LLM Agents.** MemGPT (Packer et al., 2023) and Reflexion (Shinn et al., 2023) use structured memory with explicit retrieval and scoring. Our approach differs: memory is natural language text written by the LLM itself, with recency-weighted slot injection. No vector database, no separate scoring model, no JSON encoding overhead.

**The critical gap.** No prior work has demonstrated that an agent's *entire cognitive architecture*—all mechanisms managing *how* the LLM thinks—can be reduced to declarative configuration. This is the contribution of SVA.

---

## 3. The Slot Vector Architecture

### 3.0 Formal Definitions

**Definition 1 (Slot).** A slot is a pair $s = (c, t)$ where:
- $c: \mathcal{K} \to \{0, 1\}$ is a condition predicate over the context dictionary $\mathcal{K}$
- $t$ is a template string containing variables from $\mathcal{K}$, rendered via safe string formatting

A slot is *active* for context $K \in \mathcal{K}$ iff $c(K) = 1$.

**Definition 2 (Slot Registry).** A slot registry $\mathcal{S} = \{n_1 \mapsto s_1, \ldots, n_m \mapsto s_m\}$ maps slot names to slots. This is the global set of all defined cognitive capabilities.

**Definition 3 (Template).** A template $T = [n_1, n_2, \ldots, n_k]$ is an ordered list of slot names where $n_i$ are keys in $\mathcal{S}$. The order defines cognitive priority—earlier slots appear earlier in the rendered prompt.

**Definition 4 (Assembler).** The assembler function $A(T, K) = \bigoplus_{n_i \in T} \; t_i \;\text{iff}\; c_i(K)=1$ concatenates the rendered templates of all active slots in template order, where $\bigoplus$ is string concatenation with a fixed separator.

**Proposition 1 (Code Stability).** Adding a new cognitive capability $s_{m+1}$ requires exactly two changes to the system configuration: (1) $\mathcal{S} \leftarrow \mathcal{S} \cup \{n_{m+1} \mapsto s_{m+1}\}$, (2) $T \leftarrow [\ldots, n_{m+1}]$. Zero code changes in the assembler or agent loop.

This follows directly from the assembler's implementation, which iterates $T$ and looks up $\mathcal{S}$ without any awareness of specific slot semantics.

### 3.1 The Assembler (45 Lines)

```python
def assemble(self, template_name, ctx):
    tpl = self.loader.get_template(template_name)
    all_slots = self.loader.data.get("slots", {})
    parts = []
    for name in tpl["slots"]:
        slot = all_slots.get(name, {})
        cond = slot.get("condition", "")
        if cond and not bool(ctx.get(cond)):
            continue
        text = slot.get("template", "")
        if text:
            parts.append(safe_format(text, ctx))
    return "\n\n".join(parts)
```

The assembler is the *only* cognitive code path in the system. It is slot-agnostic: iterating template slots, checking conditions, formatting templates. Any slot semantics are defined entirely in YAML.

### 3.2 The 12-Slot Cognitive Architecture

Our current deployment uses 12 slots forming a priority-ordered attention funnel:

```
Slot Order       | Condition       | Cognitive Directive
─────────────────┼─────────────────┼──────────────────────
main_thread      | main_thread     | Persist a goal; update it
persona          | name            | Remember your identity
world_rules      | (always)        | Obey world constraints
kl_divergence    | kl_text         | Attend to what changed
drive_state      | drives_table    | Satisfy your needs
spatial_context  | zone_name       | Know your location
sensory_section  | sensory_text    | Perceive surroundings
recent_memory    | memory_text     | Recall your history
avoid_repetition | memory_text     | Do not repeat yourself
idle_guidance    | memory_text     | Rest is a valid choice
action_guidance  | (always)        | Act freely; engine finds targets
output_format    | (always)        | Output JSON in this schema
```

Each slot maps to a GA equivalent: `main_thread` replaces the planning module (~200 lines of Python), `recent_memory` replaces memory retrieval (~200 lines), `avoid_repetition` + `idle_guidance` handle self-regulation (no GA equivalent), `sensory_section` replaces the location tree (~100 lines).

**Configuring cognitive architecture.** Changing slot order changes agent behavior. Moving `recent_memory` before `main_thread` produces memory-driven rather than goal-driven agents—an experiment requiring code restructuring in GA.

### 3.3 The P/Q/KL Attention Gate

**Formal mechanism.** At each poll cycle (0.3s):

$$\text{KL}_{\text{total}} = \bigoplus_{c \in \{\text{visual, auditory, state, temporal}\}} \text{channel\_kl}(P_c, Q_c)$$

where:

$$\text{channel\_kl}(P, Q) = \sum_{e \in P \cup Q} \begin{cases}
\texttt{entered}(e) & \text{if } e \notin P \land e \in Q \\
\texttt{left}(e) & \text{if } e \in P \land e \notin Q \\
\texttt{changed}(e) & \text{if } \text{data}(P[e]) \neq \text{data}(Q[e])
\end{cases}$$

$$\text{state\_kl}(P, Q) = \sum_{a \in \text{attrs}} \sum_{\tau \in \text{thresholds}} \mathbb{1}[(P[a] < \tau \leq Q[a]) \lor (P[a] > \tau \geq Q[a])]$$

$$\text{stale\_kl}(P) = \mathbb{1}[\text{now}() - P.\text{last\_update} > \tau_{\text{stale}}]$$

If $\text{KL}_{\text{total}}$ is empty: sleep, continue observing. Otherwise: trigger LLM decision.

**Dict-Copy Bug.** A critical implementation error was discovered and fixed: assigning `p_channels[ch] = sensory.channels[ch]` created a shared reference between P and Q. Since `sensory.update()` modifies sensory.channels in-place via `channels[ch][eid] = SensorRecord(...)`, the shared reference caused P to be silently mutated alongside Q. After the initial burst of entity entries, all entities appeared unchanged in every subsequent cycle—P always equaled Q. Fixing this to a shallow copy (`dict(ch_data)`) restored proper P/Q separation.

### 3.4 Memory as Natural Language

Agent memory is stored as the LLM's own narrative text:

$$\text{memory}[t] = \text{decision.story} \;\text{or}\; \text{decision.action}$$

Prior versions stored memory as `json.dumps(decision)`—~300-character JSON blobs the LLM could not effectively scan for repetition. Switching to natural language reduced adjacent repetition from 19.9% to 4.4% (§5.4).

### 3.5 The Engine-Language Boundary

We enforce a strict separation formalized as:

$$\text{System} = \underbrace{\text{Sensor} \to \text{Model} \to \text{Comparator}}_{\text{Engine (Python)}} \to \underbrace{\text{Mediator}}_{\text{YAML}} \to \underbrace{\text{Reasoner}}_{\text{LLM}} \to \underbrace{\text{Actor}}_{\text{Engine (Python)}}$$

The engine provides facts ("entity X at distance 3"). The mediator declares priorities ("safety > task completion"). The reasoner decides actions ("greet X"). The engine *never* makes a semantic judgment.

---

## 4. System Design

### 4.1 Agent Loop

```
while running:
    Phase 1 — SENSE:
        decay.tick(elapsed)
        sensory.update(observer, entities)
    
    Phase 2 — KL GATE:
        kl_text = total_kl(P_channels, Q_channels)
        if kl_text == "": sleep; continue
    
    Phase 3 — DECIDE:
        ctx = {main_thread, persona, drives, sensory, memory, kl_text}
        prompt = assembler.assemble("agent_decision", ctx)  # 45 lines
        decision = brain.decide(ctx)                        # LLM #1
    
    Phase 4 — ACT:
        interact(agent, target, decision)
        # NPC→NPC: 0 extra LLM calls
        # NPC→Item: +1 LLM call (narrative generation)
```

### 4.2 Interaction Model

Agents communicate via a **write-then-poll** blackboard model. Agent A writes dialogue/expression to its own layers; Agent B polls all entity layers via `sensory.update()`. No event bus, no message passing, no inbox system (deleted in v7.1). This is equivalent to shared-memory multi-agent communication implemented through layer observation.

### 4.3 World Configuration

The world is YAML-defined. Entities declare layers and properties. A complete domain switch—from a Witcher tavern to any other world—requires only a new `world.yaml`. The engine contains zero domain knowledge.

---

## 5. Experiments

### 5.1 Experimental Setup

**Configuration**: 25 LLM-driven agents with distinct personalities, distributed across 3 zones (tavern: 10 agents, village: 9, garrison: 6). **LLM**: DeepSeek-chat via OpenAI-compatible API. **Runtime**: 180 seconds per run. **Parameters**: poll_interval=0.3s, stale_timeout=30s, speech_window=30s. **Hardware**: consumer-grade CPU (all LLM calls are API-based; local computation is negligible).

**[LIMITATION: Single-seed results.]** Results below are from a single 180s run. Multi-seed statistics with variance reporting is planned for the camera-ready version. The qualitative observations (social cluster emergence, topic coherence) are consistent across multiple shorter runs during development.

### 5.2 Metrics

- **Total actions**: count of agent actions with non-null `action_text`
- **NPC↔NPC rate**: fraction of actions where target is another agent
- **Adjacent repetition rate**: $\frac{1}{|A|-N}\sum_{a}\sum_{i=1}^{|A_a|-1} \mathbb{1}[A_a[i] = A_a[i+1]]$, where $A_a$ is agent $a$'s action sequence and $N$ is the number of agents
- **Channel change detections**: count of KL text entries containing "变化" (changed) vs "进入" (entered)
- **Pure-stale triggers**: fraction of actions where KL text equals only the stale message

### 5.3 Main Results

**Table 1: System performance (180s, 25 agents, single run)**

| Metric | Value |
|--------|-------|
| Total actions | 1,196 |
| NPC↔NPC interactions | 1,067 (89.2%) |
| Adjacent repetition rate | 0.7% |
| Channel "change" detections | 743 |
| Channel "enter" detections | 269 |
| Pure-stale triggers | 10 (0.8%) |
| Zone-crossing agents | 18/25 (72%) |
| Main threads set by LLM | 21/25 (84%) |

**Table 2: Output modality distribution**

| Modality | Coverage |
|----------|---------|
| Dialogue (💬) | 53% of actions |
| Story (📖) | 51% |
| Visual expression (👁) | 81% |
| Internal monologue (🧠) | 81% |

### 5.4 Ablation: Dict Copy Fix

**Table 3: Effect of fixing P/Q dict reference sharing (180s, same config)**

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| Total actions | 49 | 1,196 |
| "Change" detections | 0 | 743 |
| "Enter" detections | 49 | 269 |
| KL gate behavior | All entities appear new each cycle | Proper enter/leave/change discrimination |

**Discussion.** Before the fix, the shared dict reference (`p_channels[ch] = ch_data` rather than `dict(ch_data)`) caused P and Q to point to the same mutable dict. `sensory.update()` modifies `Q` in-place via `Q[ch][eid] = SensorRecord(...)`, simultaneously mutating `P`. After the first cycle captured all entities, P always equaled Q, producing zero triggers. The fix restores proper separation: P is now a shallow copy, independent of subsequent Q mutations.

### 5.5 Ablation: Memory Format

**Table 4: Effect of memory format on adjacent repetition (60s, 25 agents)**

| Memory Format | Adjacent Repetition |
|--------------|-------------------|
| Full JSON (`json.dumps(decision)`) | 19.9% |
| Spliced text (`action + " | say: " + dialogue[:80]`) | 4.4% |
| Natural language (`story` field) | 4.4% |

**Discussion.** Full JSON produced ~300-character entries unreadable to the LLM for rapid pattern detection. Both human-readable formats (spliced text and natural story) achieved equivalent repetition reduction. We adopt natural language as the philosophically cleaner approach—the LLM reads its own narrative, not an engine-constructed string.

### 5.6 Ablation: Idle Guidance

**Table 5: Effect of `idle_guidance` slot on stuck-listener behavior (60s, 25 agents)**

| Agent | Without idle_guidance | With idle_guidance |
|-------|----------------------|-------------------|
| Lambert (witcher) | 15+ adjacent "sit at table" | 0 |
| Dandelion (bard) | 20+ adjacent "greet Dijkstra" | 0 |
| Quartermaster (supply) | 20+ adjacent "listen to conversation" | 0 |

**Discussion.** These agents were "background listeners"—close enough to active social groups to trigger KL via visual expression changes, but with no new content to contribute. The LLM repeatedly output "join the table" or "stand nearby" because it had no concept of "just listen." The `idle_guidance` slot teaches the LLM that `action: null` is valid. Adding one YAML entry (8 lines) eliminated all stuck-listener behavior with zero code changes.

### 5.7 Qualitative: Emergent Social Structure

**Table 6: Top conversational pairs (25 agents, 180s)**

| Pair | Interactions | Zone | Context |
|------|-------------|------|---------|
| Yennefer ↔ Keira | 28+26 | Garrison | Alchemy collaboration |
| Philippa ↔ Shani | ~90 each | Village | Intelligence exchange |
| Geralt ↔ Triss | multi-turn | Tavern | Social + gryphon quest |

**[LIMITATION: Formal cluster detection is future work.]** The three groups described below were identified through manual inspection of action logs. Automated community detection (e.g., Louvain modularity on the interaction graph) is planned.

**Tavern cluster (10 agents).** Witchers (Geralt, Vesemir, Lambert), sorceresses (Triss), bards (Dandelion, apprentice), merchants (Zoltan, innkeeper), and spies (Dijkstra). Multiple overlapping conversations: hunters discuss contracts, Zoltan buys rounds, Dandelion performs, Dijkstra observes and collects intelligence. A distinct sub-thread involves Vesemir moving between the hunter table and the Triss-Dijkstra political conversation at t=78s—natural cross-group social mobility.

**Village cluster (9 agents).** Shoe-stall spy ring (Thaler, Philippa) exchanging intelligence about swamp footprints and Nilfgaard movements, with the Elder contributing local knowledge (secret passages under ritual stones). A parallel gryphon-hunting party (Ciri, Huntress, Shani) forms independently, later intersecting with the spy ring as Philippa "accidentally" approaches Ciri.

**Garrison cluster (6 agents).** Alchemy collaboration between Yennefer and Keira, joined by Eskel (witcher practical knowledge) and the Quartermaster (supply-line tips). Roche surveils from the war table, and the Nilfgaard Officer circles nervously. The conversation arc progresses from greeting → knowledge sharing → collaboration proposal → experimental attempt—a coherent cooperative trajectory.

### 5.8 Slot Order Sensitivity

**[LIMITATION: Systematic slot-order ablation is future work.]** Preliminary observations indicate that slot order significantly affects behavior. In an informal test, moving `recent_memory` before `main_thread` caused agents to become more memory-reactive and less goal-directed. A systematic study varying slot order across multiple seeds is planned.

---

## 6. Discussion

### 6.1 Why Declarative Beats Imperative for Agent Cognition

The separation of concerns between physics simulation and cognitive judgment has a clear software engineering motivation: cognitive rules change more frequently than physics rules, and different deployment scenarios require different cognitive priorities. A declarative slot list is a *configuration file for cognition*—it can be versioned, A/B tested, and adapted per agent or per scenario without touching the physics engine.

This connects to broader principles:
- **Brooks' subsumption architecture** (1986): behavior emerges from layered, independent modules. Slots are the declarative equivalent of Brooks' layers.
- **Production systems** (Newell & Simon, 1972): IF-THEN rules fire when conditions match. Slots generalize this: IF `ctx[key]` THEN render `template`.
- **Separation of concerns** (Dijkstra, 1974): physics code and cognition code should be different modules. Slots push this to the limit—cognition code is eliminated entirely.

### 6.2 The Removal Principle

The v1→v7 evolution empirically demonstrates a consistent principle: **every deletion of a hardcoded cognitive mechanism is followed by the LLM naturally filling the gap through slot guidance.**

| Deleted Mechanism | How LLM Filled the Gap |
|------------------|----------------------|
| Duplication filter | `avoid_repetition` slot + natural language memory |
| Observing state machine | KL gate: no change → no action (natural waiting) |
| Action registry | Natural language actions + engine fuzzy matching |
| Hardcoded sensory rendering | YAML `sensory_prompts` template-driven channels |
| Inbox messaging system | Layer write-then-poll blackboard communication |

This pattern suggests a design heuristic for LLM agent systems: **when considering whether a cognitive mechanism belongs in code, ask whether a slot could achieve the same effect. If unsure, try the slot first.** This is the inverse of the traditional "start with code, extract to config later" approach.

### 6.3 Limitations

**[All items marked TODO require additional work for a complete submission.]**

1. **Single-seed results.** All quantitative results are from one 180s run. Variance across seeds and runs is unknown. Multi-seed evaluation (5 seeds, mean ± std) is planned.

2. **No head-to-head baseline.** We compare to GA's published architecture description (~730 lines of cognitive code) rather than a reimplementation. Implementing a minimal GA-style baseline (timer-based activation + imperative memory retrieval) would strengthen the comparison.

3. **Single domain.** All experiments use a Witcher-themed tavern world. Cross-domain generalization (e.g., office, classroom, marketplace) is untested.

4. **No formal cluster detection.** Social clusters were identified by manual inspection. Automated community detection (Louvain, Girvan-Newman) on the interaction graph would provide quantitative cluster metrics.

5. **LLM-specific scope.** The SVA pattern is evaluated only with LLMs as the reasoner. Generalization to other reasoner types (symbolic planners, RL policies) is theoretical at this stage.

6. **Slot discovery is manual.** The 12-slot configuration was arrived at through iterative engineering. There is no principled method for determining the optimal number or content of slots for a given domain.

7. **No human evaluation.** Narrative quality, social plausibility, and goal coherence are assessed by the authors. A human study comparing agent behavior to human expectations would strengthen claims of "natural social behavior."

8. **Declarative prior experiments not yet conducted.** The SVA's capability for controlled prior experiments (§6.4, item 6) is theoretically motivated but not yet empirically demonstrated. No cross-world, cross-morality, or cross-prior comparison has been run.

### 6.4 Future Work

1. **Cross-domain SVA deployment.** Test slot vectors in a non-social domain (e.g., a single-agent exploration task) to validate the pattern's generality.

2. **Automated slot optimization.** Develop methods to automatically discover, prune, and reorder slots based on agent performance metrics.

3. **Theoretical analysis of slot expressiveness.** Characterize the class of cognitive architectures representable as slot vectors, and identify any fundamental limitations.

4. **SVA for non-LLM reasoners.** Apply the pattern to classical planners (where slots become planning heuristics) and RL agents (where slots become reward-shaping prompts).

5. **Formal connection to active inference.** The P/Q/KL gate is a discrete symbolic implementation of the free energy principle. A formal mapping between SVA and active inference could ground the architecture in a well-established theoretical framework.

6. **Declarative priors for controlled social simulation.** The SVA's most distinctive capability—and the one we believe will attract the most interest from the social simulation community—is its ability to conduct *controlled experiments on priors at arbitrary granularity*. Because each slot is an independently toggleable, conditionally-rendered prompt fragment, a researcher can vary a single prior (world-level moral rules, group-level information access, individual-level cognitive bias) while holding all other configuration constant. This enables experimental designs that are infeasible in imperative agent architectures.

**World-level priors.** Varying the `world_rules` slot between a "high-morality" and a "low-morality" template, with identical agent populations, measures whether moral priors causally affect emergent social structure.

**Individual-level priors.** Adding a `paranoia` slot to exactly one agent out of 25—while all others share identical configuration—tests whether a single cognitive deviant influences group behavior, information flow, or social network topology.

**Group-level priors.** Varying `sensory_prompts.visual.state` (information transparency) across zones measures how information asymmetry shapes cooperation and exploration.

**Per-attribute priors.** The per-attribute `{min, max, decay, description}` drive system (§3.4) allows experiments on how different physiological models (e.g., short vs. long lifespans via decay rates) shape agent time preferences and risk-taking.

**Controlled comparison protocol.** Each such experiment requires changing only the relevant YAML entries, followed by `python main.py --runtime 600` with identical LLM configuration. No code changes, no recompilation, no risk of accidentally varying an uncontrolled parameter. This is a capability that imperative agent architectures (Generative Agents, CrewAI, AutoGen) lack by design—their cognitive rules are embedded in Python control flow, making isolated prior variation a programming task rather than a configuration switch.

**[TODO: Implement and report results for at least one declarative prior experiment (e.g., world moral-rules gradient) in the camera-ready version.]**

---

## 7. Conclusion

We presented the **Slot Vector Architecture**, a declarative framework for LLM agent cognition. The key insight is that agent cognitive capabilities—memory retrieval, planning, self-regulation, sensory interpretation—are not separate code modules but composable prompt fragments. A 45-line slot-agnostic assembler, 12 YAML slot definitions, and a prediction-error-driven attention gate replace ~730 lines of cognitive code while achieving richer emergent behavior (1,196 actions, 0.7% repetition, 89% social, 0 lines of cognitive code). The slot vector pattern generalizes beyond LLM agents: any autonomous system with a perception-action loop can instantiate its mediator as a declarative priority stack, separating physics from cognition and enabling configuration-driven behavioral adaptation.

---

## References

[1] Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. (2023). Generative agents: Interactive simulacra of human behavior. *UIST 2023*.

[2] Bai, Y., Kadavath, S., Kundu, S., et al. (2022). Constitutional AI: Harmlessness from AI feedback. *NeurIPS 2022*.

[3] Khattab, O., Singhvi, A., Maheshwari, P., et al. (2023). DSPy: Compiling declarative language model calls into self-improving pipelines. *arXiv:2310.03714*.

[4] Friston, K. (2010). The free-energy principle: a unified brain theory? *Nature Reviews Neuroscience*, 11(2), 127–138.

[5] Parr, T., Pezzulo, G., & Friston, K. J. (2022). *Active inference: the free energy principle in mind, brain, and behavior*. MIT Press.

[6] Packer, C., Fang, V., Patil, S. G., et al. (2023). MemGPT: Towards LLMs as operating systems. *arXiv:2310.08560*.

[7] Shinn, N., Cassano, F., Gopinath, A., et al. (2023). Reflexion: Language agents with verbal reinforcement learning. *NeurIPS 2023*.

[8] Wu, Q., Bansal, G., Zhang, J., et al. (2023). AutoGen: Enabling next-gen LLM applications via multi-agent conversation. *arXiv:2308.08155*.

[9] Li, G., Hammoud, H. A. A. K., Itani, H., et al. (2023). CAMEL: Communicative agents for "mind" exploration of large language model society. *NeurIPS 2023*.

[10] Wang, G., Xie, Y., Jiang, Y., et al. (2023). Voyager: An open-ended embodied agent with large language models. *arXiv:2305.16291*.

[11] Brooks, R. A. (1986). A robust layered control system for a mobile robot. *IEEE Journal of Robotics and Automation*, 2(1), 14–23.

[12] Newell, A., & Simon, H. A. (1972). *Human problem solving*. Prentice-Hall.

---

## Appendix A: Full Slot Registry

| Slot | Condition | Template (abbreviated) |
|------|-----------|----------------------|
| `main_thread` | `main_thread` | "Your current goal: {main_thread}. Serve it." |
| `persona` | `name` | "You are {name}. {personality}" |
| `world_rules` | (always) | "Rules: conservation, diminishing returns..." |
| `kl_divergence` | `kl_text` | "Changes: {kl_text}" |
| `drive_state` | `drives_table` | "State: {drives_table}" |
| `spatial_context` | `zone_name` | "Location: {zone_name} ({pos_x}, {pos_y})" |
| `sensory_section` | `sensory_text` | "{sensory_text}" (three-channel template) |
| `recent_memory` | `memory_text` | "Recent history: {memory_text}" |
| `avoid_repetition` | `memory_text` | "Check history. Don't repeat." |
| `idle_guidance` | `memory_text` | "null action is valid. Wait if listening." |
| `action_guidance` | (always) | "Act freely. Engine finds targets." |
| `output_format` | (always) | "Output JSON: {thinking, action, story, ...}" |

## Appendix B: Sensory Prompts Configuration

```yaml
sensory_prompts:
  visual:
    header: "## Visual"
    state: "{name} ({distance})"
    content: "{look}"
    detail: "  {detail}"
  auditory:
    header: "## Auditory"
    state: "{name}"
    content: '"{current_speech}"'
  interaction:
    header: "## Interactable"
    state: "{name} — {description}"
```
