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

def test_app_initial_orientation_and_size_change_reset():
    import dearpygui.dearpygui as dpg
    from main import SeaBattleApp
    dpg.create_context()
    try:
        app = SeaBattleApp()
        # Default orientation 'H' must match angle_idx 1 (90 deg)
        assert app.orientation == "H"
        assert app.orient_angle_idx == 1

        # Simulate battle in progress, then change size -> must reset to placement
        app.phase = "battle"
        app.turn = "bot"
        app.change_size(None, "8 × 8")
        assert app.size == 8
        assert app.phase == "placement"
        assert app.turn == "player"
        assert app.selected_size == 3
    finally:
        dpg.destroy_context()

def test_board_cell_sizing_never_clips_panels():
    for vw in (940, 1200, 1600):
        for size in (8, 10, 12):
            panel_width = max(330, (vw - 225 - 45) // 2)
            panel_height = max(380, 740 - 180)
            max_cell_w = (panel_width - 56 - 2 * size) // size
            max_cell_h = (panel_height - 76 - 2 * size) // (size + 1)
            cell = max(18, min(50, max_cell_w, max_cell_h))
            grid_w = 24 + size * cell + size * 2
            assert grid_w <= panel_width - 28, f"Clipped at vw={vw}, size={size}: {grid_w} > {panel_width - 28}"
