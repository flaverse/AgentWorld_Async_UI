"""Spatial Hash Grid for O(k) proximity queries.

Principle 5 (Systems总控): Grid is a World-owned data structure.
Systems read from it but do not modify it.
Entity/Layers have zero awareness of the grid.
"""
from dataclasses import dataclass


@dataclass
class SpatialGrid:
    """Fixed-size cell spatial hash for integer grid coordinates."""
    cell_size: int = 5

    def __init__(self, width: int, height: int, cell_size: int = 5):
        self.cell_size = cell_size
        self.cols = max(1, width // cell_size + 1)
        self.rows = max(1, height // cell_size + 1)
        self.cells = [[set() for _ in range(self.cols)] for _ in range(self.rows)]

    def _cell(self, x: int, y: int) -> tuple[int, int]:
        cx = max(0, min(self.cols - 1, x // self.cell_size))
        cy = max(0, min(self.rows - 1, y // self.cell_size))
        return cx, cy

    def insert(self, entity_id: str, pos: list[int]) -> None:
        cx, cy = self._cell(pos[0], pos[1])
        self.cells[cy][cx].add(entity_id)

    def remove(self, entity_id: str, pos: list[int]) -> None:
        cx, cy = self._cell(pos[0], pos[1])
        self.cells[cy][cx].discard(entity_id)

    def move(self, entity_id: str, old_pos: list[int], new_pos: list[int]) -> None:
        old_cx, old_cy = self._cell(old_pos[0], old_pos[1])
        new_cx, new_cy = self._cell(new_pos[0], new_pos[1])
        if (old_cx, old_cy) != (new_cx, new_cy):
            self.cells[old_cy][old_cx].discard(entity_id)
            self.cells[new_cy][new_cx].add(entity_id)

    def query_ids(self, pos: list[int], radius: int) -> set[str]:
        """Return entity_ids within radius cells of pos."""
        min_cx = max(0, (pos[0] - radius) // self.cell_size)
        max_cx = min(self.cols - 1, (pos[0] + radius) // self.cell_size)
        min_cy = max(0, (pos[1] - radius) // self.cell_size)
        max_cy = min(self.rows - 1, (pos[1] + radius) // self.cell_size)

        result = set()
        for cy in range(min_cy, max_cy + 1):
            row = self.cells[cy]
            for cx in range(min_cx, max_cx + 1):
                result |= row[cx]
        return result
