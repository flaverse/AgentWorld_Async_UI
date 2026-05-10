import time


class WorldClock:
    def __init__(self, start_time_str: str, time_scale: int):
        self.time_scale = time_scale
        self.start_real = time.time()
        self.start_sim_minutes = self._parse_time(start_time_str)

    def now(self) -> float:
        elapsed_real = time.time() - self.start_real
        elapsed_sim_seconds = elapsed_real * self.time_scale
        return self.start_sim_minutes + elapsed_sim_seconds / 60.0

    def time_str(self) -> str:
        total = self.now()
        hours = int(total // 60) % 24
        minutes = int(total % 60)
        return f"{hours:02d}:{minutes:02d}"

    def _parse_time(self, s: str) -> float:
        h, m = map(int, s.split(":"))
        return h * 60 + m
