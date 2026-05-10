"""Pydantic schemas for API requests/responses."""
from pydantic import BaseModel
from typing import Any


class WorldStateResponse(BaseModel):
    time: str
    zones: list[dict]
    entities: list[dict]


class AgentRegisterRequest(BaseModel):
    id: str
    name: str
    zone: str
    pos: list[int]
    sprite: str | None = None
    personality: str = ""


class AgentMoveRequest(BaseModel):
    to: list[int]


class InteractRequest(BaseModel):
    target_entity: str
    action: str


class CommandRequest(BaseModel):
    content: str


class SensoryUpdateMessage(BaseModel):
    type: str = "sensory_update"
    interactable: list[dict]
    visible: list[dict]


class InteractionResultMessage(BaseModel):
    type: str = "interaction_result"
    action: str
    target: str
    narrative: str
    caller_deltas: dict
    public_observation: str
