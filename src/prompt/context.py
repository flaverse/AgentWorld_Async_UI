"""PromptContext: Agent 决策时的完整上下文。

原则 ④ 配置即行为: 此结构由 PromptAssembler 填充，内容来自 YAML slot。
原则 ② 分层架构: 从 SensoryMemory / DriveSystem / AgentMemory 读取，不接触 Entity。
"""
from dataclasses import dataclass, field


@dataclass
class PromptContext:
    round: int = 0
    name: str = ""
    personality: str = ""
    drives_table: str = ""
    pos_x: int = 0
    pos_y: int = 0
    zone_name: str = ""
    zone_width: int = 0
    zone_height: int = 0
    interactable_text: str = ""
    visible_text: str = ""
    memory_text: str = ""
    messages_text: str = ""
    busy: bool = False
    busy_action: str = ""

    # ── 裁判用 ──
    caller_name: str = ""
    caller_public: str = ""
    caller_private: str = ""
    target_name: str = ""
    target_public: str = ""
    target_private: str = ""
    action: str = ""
    ambient_text: str = ""
