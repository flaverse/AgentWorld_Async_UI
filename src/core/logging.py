"""Unified logger for AgentWorld Async.

原则 ⑨ 前端零知识: 日志仅在后端，前端通过 WS 获取事件。
"""
import logging
import sys

_logger = logging.getLogger("agentworld")
_logger.setLevel(logging.DEBUG)

_handler = logging.StreamHandler(sys.stdout)
_handler.setLevel(logging.DEBUG)
_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname).1s] %(name)s | %(message)s",
    datefmt="%H:%M:%S",
))
_logger.addHandler(_handler)


def get_logger(name: str = "agentworld") -> logging.Logger:
    return logging.getLogger(name)
