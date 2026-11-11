# -*- coding: utf-8 -*-
"""
bot.py - Искусственный интеллект для игры в морской бой.
Режимы:
- 'easy': случайные выстрелы по непроверенным клеткам.
- 'smart': алгоритм охоты и добивания (Hunt & Target).
  В фазе охоты стреляет по шахматной сетке. При первом попадании
  прощупывает соседние клетки (крестом). При двух попаданиях
  определяет линию корабля и добивает с обоих концов.
"""

import random
from typing import List, Tuple, Set, Optional


class BattleshipBot:
    def __init__(self, board_size: int = 10, difficulty: str = 'smart'):
        self.board_size = board_size
        self.difficulty = difficulty
        self.reset()

    def reset(self):
        self.unvisited: Set[Tuple[int, int]] = {
            (r, c) for r in range(self.board_size) for c in range(self.board_size)
        }
        # Текущий добиваемый корабль: список клеток с попаданиями
        self.current_hits: List[Tuple[int, int]] = []
        # Очередь приоритетных целей для добивания
        self.target_queue: List[Tuple[int, int]] = []

    def register_shot_result(self, r: int, c: int, result: str,
                             sunk_ship_cells: Optional[List[Tuple[int, int]]] = None,
                             surrounding_misses: Optional[List[Tuple[int, int]]] = None):
        """Информирует бота о результате его последнего выстрела."""
        # Удаляем из непроверенных
        self.unvisited.discard((r, c))

        # Если вокруг потопленного корабля образовались промахи, исключаем их из непроверенных
        if surrounding_misses:
            for mr, mc in surrounding_misses:
                self.unvisited.discard((mr, mc))

        if self.difficulty == 'easy':
            return

        # Логика для 'smart':
        if result == 'hit':
            self.current_hits.append((r, c))
            self._update_target_queue_after_hit()
        elif result == 'sunk':
            # Корабль потоплен! Забываем о нем и очищаем очередь целей для этого корабля
            if sunk_ship_cells:
                for sr, sc in sunk_ship_cells:
                    self.unvisited.discard((sr, sc))
            self.current_hits.clear()
            self.target_queue.clear()

    def _update_target_queue_after_hit(self):
        """Обновляет очередь целей на основе уже имеющихся попаданий в текущий корабль."""
        self.target_queue.clear()

        if len(self.current_hits) == 1:
            # Одно попадание - проверяем 4 направления крестом
            r, c = self.current_hits[0]
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            random.shuffle(directions)  # Случайный порядок для разнообразия
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if (nr, nc) in self.unvisited:
                    self.target_queue.append((nr, nc))

        elif len(self.current_hits) >= 2:
            # Два или более попаданий - определяем ориентацию (горизонтальная или вертикальная)
            rows = [r for r, c in self.current_hits]
            cols = [c for r, c in self.current_hits]

            is_horizontal = (len(set(rows)) == 1)
            is_vertical = (len(set(cols)) == 1)

            if is_horizontal:
                fixed_row = rows[0]
                min_c, max_c = min(cols), max(cols)
                # Пробуем стрелять слева и справа
                ends = [(fixed_row, min_c - 1), (fixed_row, max_c + 1)]
                random.shuffle(ends)
                for er, ec in ends:
                    if (er, ec) in self.unvisited:
                        self.target_queue.append((er, ec))

            elif is_vertical:
                fixed_col = cols[0]
                min_r, max_r = min(rows), max(rows)
                # Пробуем стрелять сверху и снизу
                ends = [(min_r - 1, fixed_col), (max_r + 1, fixed_col)]
                random.shuffle(ends)
                for er, ec in ends:
                    if (er, ec) in self.unvisited:
                        self.target_queue.append((er, ec))

    def choose_shot(self) -> Optional[Tuple[int, int]]:
        """Выбирает координату для следующего выстрела."""
        if not self.unvisited:
            return None

        # 1. Если включен режим 'smart' и есть цели в очереди добивания
        if self.difficulty == 'smart' and self.target_queue:
            while self.target_queue:
                target = self.target_queue.pop(0)
                if target in self.unvisited:
                    return target

        # 2. Обычный поиск (фаза охоты)
        if self.difficulty == 'smart':
            # Стрельба по шахматному шаблону (шаг 2)
            parity_candidates = [(r, c) for r, c in self.unvisited if (r + c) % 2 == 0]
            if parity_candidates:
                return random.choice(parity_candidates)

        # 3. Случайный выбор из оставшихся свободных клеток
        return random.choice(list(self.unvisited))
