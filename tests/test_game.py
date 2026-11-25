import random
from game_logic import Board


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


def test_app_initial_state_and_new_game_reset():
    import dearpygui.dearpygui as dpg
    from main import SeaBattleApp
    dpg.create_context()
    try:
        app = SeaBattleApp()
        assert app.mode == "multiplayer"
        assert app.orientation == "H"
        assert app.orient_angle_idx == 1

        app.phase = "battle"
        app.turn = "phone"
        app.enemy_sunk_count = 4
        app.new_game()
        assert app.phase == "placement"
        assert app.turn == "player"
        assert app.enemy_sunk_count == 0
    finally:
        dpg.destroy_context()


def test_board_cell_sizing_never_clips_panels():
    for vw in (940, 1200, 1600):
        for size in (8, 10, 12):
            panel_width = max(330, (vw - 225 - 45) // 2)
            panel_height = max(340, 740 - 205)
            max_cell_w = (panel_width - 56 - 2 * size) // size
            max_cell_h = (panel_height - 76 - 2 * size) // (size + 1)
            cell = max(18, min(50, max_cell_w, max_cell_h))
            grid_w = 24 + size * cell + size * 2
            assert grid_w <= panel_width - 28, f"Clipped at vw={vw}, size={size}: {grid_w} > {panel_width - 28}"
