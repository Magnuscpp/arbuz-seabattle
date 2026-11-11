import random
from game_logic import Board, CELL_SHIP
from bot import BattleshipBot

def test_all_board_sizes_place_complete_fleet():
    for size in (8, 10, 12):
        random.seed(size)
        board = Board(size)
        assert board.auto_place_all()
        assert board.is_fleet_complete()

def test_touching_ships_are_rejected():
    board = Board(10)
    assert board.place_ship(2, 2, 3, "H")
    assert not board.can_place_ship(3, 2, 2, "H")

def test_sink_marks_surrounding_water():
    board = Board(8, {1: 1})
    board.place_ship(3, 3, 1, "H")
    result, ship, misses = board.receive_shot(3, 3)
    assert result == "sunk" and ship.is_sunk and len(misses) == 8

def test_smart_bot_finishes_without_duplicate_shots():
    for seed in range(15):
        random.seed(seed); board = Board(10); assert board.auto_place_all(); bot = BattleshipBot(10, "smart"); used=set()
        for _ in range(100):
            shot=bot.choose_shot(); assert shot not in used; used.add(shot)
            result,ship,misses=board.receive_shot(*shot); bot.register_shot_result(*shot,result,ship.cells if ship else None,misses)
            if board.is_all_sunk: break
        assert board.is_all_sunk
