import time


class WorldClock:
    def __init__(self, start_time_str: str, time_scale: int):
        self.time_scale = time_scale
        self.start_real = time.time()
        self.start_sim_minutes = self._parse_time(start_time_str)

    def now(self) -> float:
        """返回当前模拟时间 (从 start_sim 起的模拟分钟数)。"""
        elapsed_real = time.time() - self.start_real
        elapsed_sim_seconds = elapsed_real * self.time_scale
        return elapsed_sim_seconds / 60.0

    def _parse_time(self, s: str) -> float:
        h, m = map(int, s.split(":"))
        return h * 60 + m
