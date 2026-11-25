"""Sea Battle — настольный клиент Dear PyGui в дизайне menu_ready_build (Aternos ImGui Dark).
Включает:
- Минималистичную монохромную палитру (белый, серый, черный) в стиле Apple / Dear ImGui Aternos
- Векторную иконку корабля из boat.svg
- Идеально выровненный бренд-хедер в сайдбаре
- 200px табы с 16-кадровой плавной интерполяцией (ImLerp) без обрезки текста
- Карточки выбора кораблей с реальными SVG-иконками кораблей
- Просторные карточки без скроллбаров («без крутилок»)
- Четкий, плотный русский шрифт Segoe UI Semibold
- Чистый заголовок окна без кракозябр
"""
import json
import queue
from pathlib import Path
import sys
import threading
import time
import dearpygui.dearpygui as dpg
from PIL import Image

from bot import BattleshipBot
from game_logic import Board, Ship, CELL_EMPTY, CELL_SHIP, CELL_MISS, CELL_HIT, CELL_SUNK
from network_relay import NetworkRelay
from theme import create_themes, load_fonts

_INV255 = tuple(i / 255.0 for i in range(256))
SESSION_FILE = Path.home() / ".seabattle_session.json"


def _load_webp_texture(path: Path, tag: str):
    """Быстрая загрузка WebP-изображения в статическую текстуру Dear PyGui через PIL."""
    if not path.exists() or dpg.does_item_exist(tag):
        return
    with Image.open(path) as img:
        rgba = img.convert("RGBA")
        w, h = rgba.size
        data = list(map(_INV255.__getitem__, rgba.tobytes()))
    dpg.add_static_texture(w, h, data, tag=tag)


class SeaBattleApp:
    def __init__(self):
        self.size = 10
        self.difficulty = "smart"
        self.mode = "bot"
        self.player = Board(self.size)
        self.enemy = Board(self.size)
        self.bot = BattleshipBot(self.size, self.difficulty)
        self.phase = "placement"
        self.turn = "player"
        self.orientation = "H"
        self.selected_size = 4
        self.log = []
        self.events = queue.Queue()
        self.relay = NetworkRelay()
        self.relay.on_phone_connected = lambda: self.events.put(("phone_connected", None))
        self.relay.on_phone_ready = lambda data: self.events.put(("phone_ready", data))
        self.relay.on_phone_shot = lambda r, c: self.events.put(("phone_shot", (r, c)))
        self.relay.on_defense_result = lambda data: self.events.put(("defense_result", data))
        self.relay.on_phone_restart = lambda: self.events.put(("phone_restart", None))
        self.relay.on_phone_left = lambda: self.events.put(("phone_left", None))
        self.relay.on_error = lambda err: self.events.put(("relay_error", err))
        self.phone_ready = False
        self.room_locked = False
        self._last_heartbeat_sent = 0.0
        self.view_width, self.view_height = 1200, 740
        self.current_page = "home"
        self.sidebar_width = 225

        # Анимации перехода табов и страниц
        self.nav_animation = None
        self.page_transition = None
        self.orient_anim = None
        self.orient_angle_idx = 1  # 0: 0° (Вверх), 1: 90° (Вправо / H), 2: 180° (Вниз), 3: 270° (Влево)

        # Система всплывающих уведомлений (Toast Notifications)
        self.toast_msg = None
        self.toast_start = 0
        self.toast_duration = 2.5

        # Интерактивная подсветка координат и перекрестия при наведении
        self._hovered_cell = None

    def build(self):
        dpg.create_context()
        create_themes()
        self.fonts = load_fonts()

        # Загрузка текстур (оптимизированные WebP-ассеты)
        with dpg.texture_registry(show=False):
            dpg.add_static_texture(1, 1, [1.0, 1.0, 1.0, 1.0], tag="qr_texture")
            asset_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "assets" / "ui"

            _load_webp_texture(asset_dir / "brand_header.webp", "ui_brand_header")
            _load_webp_texture(asset_dir / "toast_header.webp", "ui_toast_header")

            # 16-кадровые плавные табы
            for page in ("home", "game", "multiplayer", "settings", "about"):
                for frame in range(16):
                    _load_webp_texture(asset_dir / f"nav_{page}_{frame}.webp", f"ui_nav_{page}_{frame}")

            # Динамические карточки кораблей (зеленые/красные квадраты и фон)
            for path in asset_dir.glob("ship_card_*.webp"):
                _load_webp_texture(path, f"ui_{path.stem}")

            # Используемые иконки
            for icon in ("bot_accent", "multiplayer_accent", "win_accent", "despair_accent"):
                _load_webp_texture(asset_dir / f"icon_{icon}.webp", f"ui_icon_{icon}")

            # Текстуры кнопок действий (обычные и с подсветкой при наведении)
            for btn_name in ("btn_rotate", "btn_clear", "btn_random", "btn_start"):
                for suffix in ("", "_hov"):
                    _load_webp_texture(asset_dir / f"{btn_name}{suffix}.webp", f"ui_{btn_name}{suffix}")

            # Кадры анимации вращения ориентации корабля (24 кадра для каждого типа)
            for sz in (1, 2, 3, 4, 5):
                for f in range(24):
                    _load_webp_texture(asset_dir / f"orient_{sz}_frame_{f}.webp", f"ui_orient_{sz}_frame_{f}")

        dpg.create_viewport(
            title="Sea Battle",
            width=self.view_width,
            height=self.view_height,
            min_width=940,
            min_height=660,
            resizable=True
        )

        with dpg.window(tag="root", no_title_bar=True, no_move=True, no_resize=True, no_collapse=True):
            with dpg.group(horizontal=True):
                self._sidebar()
                with dpg.child_window(tag="content", border=False, no_scrollbar=True):
                    pass

        # Окно всплывающего уведомления (слева сверху прямоугольником в стиле menu_ready_build notificationSystem)
        with dpg.window(
            tag="toast_window",
            no_title_bar=True,
            no_resize=True,
            no_move=True,
            no_scrollbar=True,
            no_collapse=True,
            show=False,
            width=320,
            height=84,
            pos=[16, 16]
        ):
            dpg.bind_item_theme("toast_window", "toast_theme")
            if dpg.does_item_exist("ui_toast_header"):
                dpg.add_image("ui_toast_header", width=180, height=20)
            else:
                dpg.add_text("Уведомление", color=(215, 225, 238))
            dpg.add_spacer(height=3)
            t_msg = dpg.add_text("", tag="toast_text", color=(255, 255, 255), wrap=292)
            if self.fonts and "toast" in self.fonts:
                dpg.bind_item_font(t_msg, self.fonts["toast"])
            elif self.fonts and "semibold" in self.fonts:
                dpg.bind_item_font(t_msg, self.fonts["semibold"])
            dpg.add_spacer(height=4)
            dpg.add_progress_bar(tag="toast_progress", default_value=1.0, width=292, height=2)
            dpg.bind_item_theme("toast_progress", "toast_progress_theme")

        with dpg.handler_registry():
            dpg.add_key_press_handler(key=dpg.mvKey_R, callback=self._rotate_hotkey)

        dpg.bind_theme("theme_global")
        if self.fonts and "regular" in self.fonts:
            dpg.bind_font(self.fonts["regular"])

        dpg.set_primary_window("root", True)
        dpg.set_viewport_resize_callback(self._resize)
        dpg.setup_dearpygui()
        dpg.show_viewport()

        start_page = self._restore_session()
        self.show_page(start_page)

        # Главный цикл приложения с 60 FPS
        while dpg.is_dearpygui_running():
            self._process_events()
            self._animate_navigation()
            self._animate_page_transition()
            self._animate_orient()
            self._update_board_hover()
            self._update_button_hovers()
            self._update_toast()

            # Мгновенная адаптация при любом изменении размера окна (растягивание, максимизация)
            vw, vh = dpg.get_viewport_client_width(), dpg.get_viewport_client_height()
            if vw > 0 and vh > 0 and (vw, vh) != (self.view_width, self.view_height):
                self._resize()

            dpg.render_dearpygui_frame()
            time.sleep(0.012)

        if self.room_locked or self.phase == "battle":
            self._save_session()
        self.relay.stop()
        dpg.destroy_context()

    def _sidebar(self):
        with dpg.child_window(width=self.sidebar_width, border=True, tag="sidebar", no_scrollbar=True):
            dpg.bind_item_theme("sidebar", "sidebar_theme")
            dpg.add_spacer(height=6)

            # Идеально выровненный бренд-хедер
            if dpg.does_item_exist("ui_brand_header"):
                dpg.add_image("ui_brand_header", width=205, height=48, indent=2)
            else:
                dpg.add_text("SEA BATTLE", color=(255, 255, 255), indent=10)

            dpg.add_spacer(height=16)

            # Табы меню с полной 200px шириной (без обрезки текста)
            for page in ("home", "game", "multiplayer", "settings", "about"):
                initial_frame = 15 if page == self.current_page else 0
                dpg.add_image_button(
                    f"ui_nav_{page}_{initial_frame}",
                    width=200,
                    height=50,
                    indent=2,
                    callback=self._nav_callback(page),
                    tag=f"nav_{page}",
                    background_color=(0, 0, 0, 0)
                )
                dpg.bind_item_theme(f"nav_{page}", "ui_image_button")
                dpg.add_spacer(height=3)

    def _tab_for_page(self, page):
        """Определяет ID вкладки в сайдбаре для указанной страницы."""
        if page in ("game", "placement"):
            return "game"
        return page

    def _nav_callback(self, page):
        def navigate(sender, app_data, user_data):
            if self.room_locked and page not in ("game", "multiplayer"):
                self.notify("Вы в комнате! Нажмите «Выйти из комнаты»", duration=2.5)
                return
            if page == "game":
                if self.phase == "battle":
                    self.show_page("game")
                elif self.current_page == "placement":
                    pass
                else:
                    self.new_game()
            else:
                self.show_page(page)
        return navigate

    def notify(self, message: str, duration: float = 2.4):
        """Всплывающее уведомление слева сверху прямоугольником (Aternos notificationSystem)."""
        self.toast_msg = message
        self.toast_start = time.monotonic()
        self.toast_duration = duration
        if dpg.does_item_exist("toast_text"):
            dpg.set_value("toast_text", message)
        if dpg.does_item_exist("toast_window"):
            dpg.set_item_pos("toast_window", [-330, 16])
            dpg.show_item("toast_window")
            dpg.focus_item("toast_window")

    def _update_toast(self):
        if not self.toast_msg:
            return
        now = time.monotonic()
        elapsed = now - self.toast_start
        if elapsed >= self.toast_duration:
            self.toast_msg = None
            if dpg.does_item_exist("toast_window"):
                dpg.hide_item("toast_window")
            return

        # Плавный слайд-ин слева: от -330 до 16
        TARGET_X = 16
        TARGET_Y = 16
        ANIM_IN = 0.16
        ANIM_OUT = 0.16

        if elapsed < ANIM_IN:
            factor = elapsed / ANIM_IN
            factor = 1.0 - (1.0 - factor) ** 2  # ease-out
            curr_x = int(-330 + (TARGET_X - (-330)) * factor)
        elif elapsed > self.toast_duration - ANIM_OUT:
            factor = (self.toast_duration - elapsed) / ANIM_OUT
            factor = max(0.0, factor)
            factor = 1.0 - (1.0 - factor) ** 2
            curr_x = int(-330 + (TARGET_X - (-330)) * factor)
        else:
            curr_x = TARGET_X

        if dpg.does_item_exist("toast_window"):
            dpg.set_item_pos("toast_window", [curr_x, TARGET_Y])
            rem_ratio = max(0.0, min(1.0, (self.toast_duration - elapsed) / self.toast_duration))
            if dpg.does_item_exist("toast_progress"):
                dpg.set_value("toast_progress", rem_ratio)

    def _animate_navigation(self):
        """16-кадровая плавная интерполяция активного таба."""
        if self.nav_animation is None:
            return
        previous, current, started = self.nav_animation
        progress = min(1.0, (time.monotonic() - started) / 0.18)
        eased = progress * progress * (3 - 2 * progress)
        frame = round(eased * 15)

        if dpg.does_item_exist(f"nav_{previous}"):
            dpg.configure_item(f"nav_{previous}", texture_tag=f"ui_nav_{previous}_{15 - frame}")
        if dpg.does_item_exist(f"nav_{current}"):
            dpg.configure_item(f"nav_{current}", texture_tag=f"ui_nav_{current}_{frame}")

        if progress >= 1.0:
            self.nav_animation = None
            if dpg.does_item_exist(f"nav_{previous}"):
                dpg.configure_item(f"nav_{previous}", texture_tag=f"ui_nav_{previous}_0")
            if dpg.does_item_exist(f"nav_{current}"):
                dpg.configure_item(f"nav_{current}", texture_tag=f"ui_nav_{current}_15")

    def _animate_page_transition(self):
        """Плавный подъем контента страницы."""
        if self.page_transition is None:
            return
        page, started = self.page_transition
        progress = min(1.0, (time.monotonic() - started) / 0.18)
        eased = progress * progress * (3 - 2 * progress)
        offset = int(24 * (1.0 - eased))

        if dpg.does_item_exist("page_top_spacer"):
            dpg.set_item_height("page_top_spacer", max(1, offset))

        if progress >= 1.0:
            self.page_transition = None

    def _animate_orient(self):
        """Плавное вращение корабля по часовой стрелке на 90 градусов."""
        if self.orient_anim is None:
            return
        start_f, end_f, started = self.orient_anim
        progress = min(1.0, (time.monotonic() - started) / 0.18)
        t = progress
        eased = 1.0 - (1.0 - t) * (1.0 - t)  # quadratic ease-out
        curr_f = int(round(start_f + (end_f - start_f) * eased)) % 24
        tex = f"ui_orient_{self.selected_size}_frame_{curr_f}"
        if not dpg.does_item_exist(tex):
            tex = f"ui_orient_frame_{curr_f}"
        if dpg.does_item_exist("orient_widget_btn"):
            dpg.configure_item("orient_widget_btn", texture_tag=tex)
        if progress >= 1.0:
            self.orient_anim = None

    def show_page(self, page, animate=True):
        self._hovered_cell = None
        previous_page = self.current_page
        self.current_page = page

        previous_tab = self._tab_for_page(previous_page)
        current_tab = self._tab_for_page(page)

        if current_tab != previous_tab:
            self.nav_animation = (previous_tab, current_tab, time.monotonic())
        else:
            self.nav_animation = None
            if dpg.does_item_exist(f"nav_{current_tab}"):
                dpg.configure_item(f"nav_{current_tab}", texture_tag=f"ui_nav_{current_tab}_15")

        dpg.delete_item("content", children_only=True)
        builders = {
            "home": self._page_home,
            "game": self._page_game,
            "placement": self._page_placement,
            "multiplayer": self._page_multiplayer,
            "settings": self._page_settings,
            "about": self._page_about
        }

        with dpg.group(parent="content"):
            dpg.add_spacer(height=24 if animate else 1, tag="page_top_spacer")
            builders[page]()

        self.page_transition = (page, time.monotonic()) if animate else None
        dpg.set_y_scroll("content", 0)
        self.refresh_all()

    def _page_home(self):
        content_width = self.view_width - self.sidebar_width - 35
        content_height = self.view_height
        card_w = min(600, max(460, content_width - 50))
        indent_x = max(16, (content_width - card_w) // 2)

        # Центрирование блока по вертикали:
        # заголовок (~32) + подзаголовок (~22) + отступ (16) + карточка 1 (152) + отступ (14) + карточка 2 (152) = ~388px
        total_block_h = 388
        top_spacer_h = max(20, (content_height - total_block_h) // 2 - 30)

        with dpg.group(tag="page_home", show=True):
            dpg.add_spacer(height=top_spacer_h)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=indent_x)
                with dpg.group():
                    title = dpg.add_text("ТАКТИЧЕСКИЙ МОРСКОЙ БОЙ", color=(255, 255, 255))
                    if self.fonts and "title" in self.fonts:
                        dpg.bind_item_font(title, self.fonts["title"])

                    sub = dpg.add_text("Настольная стратегия в темном стиле ImGui с искусственным интеллектом", color=(100, 110, 128))
                    if self.fonts and "regular" in self.fonts:
                        dpg.bind_item_font(sub, self.fonts["regular"])

                    dpg.add_spacer(height=16)

                    # Карточка 1: Против бота
                    with dpg.child_window(width=card_w, height=152, border=True, no_scrollbar=True):
                        dpg.bind_item_theme(dpg.last_item(), "card_theme")
                        with dpg.group(horizontal=True):
                            if dpg.does_item_exist("ui_icon_bot_accent"):
                                dpg.add_image("ui_icon_bot_accent", width=28, height=28)
                            with dpg.group():
                                t1 = dpg.add_text("Одиночный бой против ИИ", color=(255, 255, 255))
                                if self.fonts and "semibold" in self.fonts:
                                    dpg.bind_item_font(t1, self.fonts["semibold"])
                                dpg.add_text("Интеллектуальный поиск целей Hunt & Target с шахматной чётностью.", color=(140, 150, 168), wrap=card_w - 65)
                        dpg.add_spacer(height=6)
                        with dpg.group(horizontal=True):
                            b1 = dpg.add_button(label="Расставить флот", width=170, height=36, callback=self.choose_bot)
                            dpg.bind_item_theme(b1, "primary_button")
                            b_quick = dpg.add_button(label="Быстрый старт (Авто)", width=190, height=36, callback=self.quick_game)
                            dpg.bind_item_theme(b_quick, "secondary_button")

                    dpg.add_spacer(height=14)

                    # Карточка 2: Мультиплеер
                    with dpg.child_window(width=card_w, height=152, border=True, no_scrollbar=True):
                        dpg.bind_item_theme(dpg.last_item(), "card_theme")
                        with dpg.group(horizontal=True):
                            if dpg.does_item_exist("ui_icon_multiplayer_accent"):
                                dpg.add_image("ui_icon_multiplayer_accent", width=28, height=28)
                            with dpg.group():
                                t2 = dpg.add_text("Кроссплатформенный мультиплеер", color=(255, 255, 255))
                                if self.fonts and "semibold" in self.fonts:
                                    dpg.bind_item_font(t2, self.fonts["semibold"])
                                dpg.add_text("Подключение смартфона через сканирование QR-кода по протоколу MQTT.", color=(140, 150, 168), wrap=card_w - 65)
                        dpg.add_spacer(height=6)
                        b2 = dpg.add_button(label="Создать онлайн комнату", width=240, height=36, callback=self.choose_multiplayer)
                        dpg.bind_item_theme(b2, "secondary_button")

    def choose_bot(self):
        self.mode = "bot"
        self.new_game()
        self.notify("Режим: Одиночная игра")

    def choose_multiplayer(self):
        self.mode = "multiplayer"
        self.show_page("multiplayer")
        self.notify("Режим: Мультиплеер")

    def quick_game(self):
        self.mode = "bot"
        self.new_game()
        self.player.auto_place_all()
        self.start_battle()
        self.notify("Быстрый бой запущен!")

    def _page_game(self):
        panel_width = max(330, (self.view_width - self.sidebar_width - 45) // 2)
        panel_height = max(380, self.view_height - 180)
        max_cell_w = (panel_width - 56 - 2 * self.size) // self.size
        max_cell_h = (panel_height - 76 - 2 * self.size) // (self.size + 1)
        cell = max(18, min(50, max_cell_w, max_cell_h))

        with dpg.group(tag="page_game", show=True):
            self._title("Морской бой", "Уничтожьте все корабли флота противника раньше, чем он уничтожит ваш")
            with dpg.group(horizontal=True):
                # Поле игрока
                with dpg.child_window(width=panel_width, height=panel_height, no_scrollbar=True):
                    dpg.bind_item_theme(dpg.last_item(), "card_theme")
                    with dpg.group(horizontal=True):
                        dpg.add_text("ВАШ ФЛОТ", indent=8)
                        dpg.add_spacer(width=16)
                        dpg.add_text("Кораблей: —", tag="player_alive", color=(240, 243, 248))
                        dpg.add_spacer(width=16)
                        t_pl_hint = dpg.add_text("", tag="player_coord_hint", color=(200, 220, 245))
                        if self.fonts and "semibold" in self.fonts:
                            dpg.bind_item_font(t_pl_hint, self.fonts["semibold"])
                    dpg.add_spacer(height=6)
                    self._board_widget("player", clickable=False, cell=cell)

                # Поле противника
                with dpg.child_window(width=panel_width, height=panel_height, no_scrollbar=True):
                    dpg.bind_item_theme(dpg.last_item(), "card_theme")
                    with dpg.group(horizontal=True):
                        dpg.add_text("ПОЛЕ ПРОТИВНИКА", indent=8)
                        dpg.add_spacer(width=16)
                        dpg.add_text("Кораблей: —", tag="enemy_alive", color=(248, 113, 113))
                        dpg.add_spacer(width=16)
                        t_en_hint = dpg.add_text("", tag="enemy_coord_hint", color=(200, 220, 245))
                        if self.fonts and "semibold" in self.fonts:
                            dpg.bind_item_font(t_en_hint, self.fonts["semibold"])
                    dpg.add_spacer(height=6)
                    self._board_widget("enemy", clickable=True, cell=cell)

            dpg.add_spacer(height=10)
            status_banner = dpg.add_text("Матч еще не начат", tag="battle_status_line", color=(240, 243, 248), indent=16)
            if self.fonts and "semibold" in self.fonts:
                dpg.bind_item_font(status_banner, self.fonts["semibold"])

    def _page_placement(self):
        available = self.view_width - self.sidebar_width - 45
        left_width = max(310, min(int(available * 0.45), available - 495))
        right_width = available - left_width - 10
        panel_height = max(550, self.view_height - 140)
        max_cell_w = (left_width - 56 - 2 * self.size) // self.size
        max_cell_h = (panel_height - 76 - 2 * self.size) // (self.size + 1)
        cell = max(18, min(56, max_cell_w, max_cell_h))

        available_sizes = sorted(self.player.fleet_config.keys(), reverse=True)
        if self.selected_size not in available_sizes:
            self.selected_size = available_sizes[0]

        with dpg.group(tag="page_placement", show=True):
            self._title("Расстановка флота", "Выберите корабль, ориентацию и кликните по клетке. Нажатие R меняет ориентацию.")
            with dpg.group(horizontal=True):
                # Левая панель: Сетка расстановки
                with dpg.child_window(width=left_width, height=panel_height, no_scrollbar=True):
                    dpg.bind_item_theme(dpg.last_item(), "card_theme")
                    with dpg.group(horizontal=True):
                        dpg.add_text("ВАШЕ ПОЛЕ", indent=10)
                        dpg.add_spacer(width=16)
                        t_place_hint = dpg.add_text("", tag="placement_coord_hint", color=(200, 220, 245))
                        if self.fonts and "semibold" in self.fonts:
                            dpg.bind_item_font(t_place_hint, self.fonts["semibold"])
                    dpg.add_spacer(height=6)
                    self._board_widget("placement", clickable=True, cell=cell)

                # Правая панель: Выбор кораблей и Расположение
                with dpg.child_window(width=right_width, height=panel_height, no_scrollbar=True, tag="placement_controls"):
                    dpg.bind_item_theme("placement_controls", "card_theme")
                    dpg.add_spacer(height=6)

                    # Верхний блок: Выбор кораблей (слева) + Расположение (справа или ниже при узком окне)
                    is_wide_right = right_width >= 480
                    with dpg.group(horizontal=is_wide_right, indent=8):
                        # Левая колонка: ВЫБОР КОРАБЛЯ и карточки
                        with dpg.group():
                            t_head = dpg.add_text("ВЫБОР КОРАБЛЯ")
                            if self.fonts and "semibold" in self.fonts:
                                dpg.bind_item_font(t_head, self.fonts["semibold"])
                            dpg.add_spacer(height=4)

                            card_btn_w = 300
                            rem_dict = self.player.get_remaining_to_place()
                            for n in available_sizes:
                                total = self.player.fleet_config.get(n, 1)
                                rem = rem_dict.get(n, total)
                                placed = max(0, min(total, total - rem))
                                is_active = 1 if n == self.selected_size else 0
                                tex_tag = f"ui_ship_card_{n}_{total}_{placed}_{is_active}"
                                if not dpg.does_item_exist(tex_tag):
                                    tex_tag = f"ui_ship_card_{n}_{'active' if is_active else 'normal'}"

                                dpg.add_image_button(
                                    tex_tag,
                                    width=card_btn_w,
                                    height=42,
                                    frame_padding=0,
                                    callback=self.select_ship,
                                    user_data=n,
                                    tag=f"ship_btn_{n}",
                                    background_color=(0, 0, 0, 0)
                                )
                                dpg.bind_item_theme(f"ship_btn_{n}", "ui_image_button")
                                dpg.add_spacer(height=3)

                        if is_wide_right:
                            dpg.add_spacer(width=12)
                        else:
                            dpg.add_spacer(height=6)

                        # Правая колонка: РАСПОЛОЖЕНИЕ (справа от кораблей)
                        orient_img_size = 132 if is_wide_right else 84
                        with dpg.group(horizontal=not is_wide_right):
                            if is_wide_right:
                                t_orient_title = dpg.add_text("РАСПОЛОЖЕНИЕ", color=(140, 150, 168))
                                if self.fonts and "semibold" in self.fonts:
                                    dpg.bind_item_font(t_orient_title, self.fonts["semibold"])
                                dpg.add_spacer(height=6)

                            # Иконка активного корабля, плавно вращающаяся по часовой стрелке как штурвал на 90°
                            curr_f = (getattr(self, "orient_angle_idx", 1) * 6) % 24
                            ship_tex = f"ui_orient_{self.selected_size}_frame_{curr_f}"
                            if not dpg.does_item_exist(ship_tex):
                                ship_tex = f"ui_orient_frame_{curr_f}"

                            b_orient_ship = dpg.add_image_button(
                                ship_tex,
                                width=orient_img_size,
                                height=orient_img_size,
                                frame_padding=0,
                                callback=self.rotate,
                                tag="orient_widget_btn",
                                background_color=(0, 0, 0, 0)
                            )
                            dpg.bind_item_theme(b_orient_ship, "ui_image_button")

                            if is_wide_right:
                                dpg.add_spacer(height=4)
                                t_orient_val = dpg.add_text(
                                    "Горизонтальное" if self.orientation == "H" else "Вертикальное",
                                    tag="orientation_text",
                                    color=(255, 255, 255)
                                )
                                if self.fonts and "semibold" in self.fonts:
                                    dpg.bind_item_font(t_orient_val, self.fonts["semibold"])
                                dpg.add_text("Поворот (R)", color=(110, 120, 135))
                            else:
                                with dpg.group():
                                    t_orient_title = dpg.add_text("РАСПОЛОЖЕНИЕ", color=(140, 150, 168))
                                    if self.fonts and "semibold" in self.fonts:
                                        dpg.bind_item_font(t_orient_title, self.fonts["semibold"])
                                    t_orient_val = dpg.add_text(
                                        "Горизонтальное" if self.orientation == "H" else "Вертикальное",
                                        tag="orientation_text",
                                        color=(255, 255, 255)
                                    )
                                    if self.fonts and "semibold" in self.fonts:
                                        dpg.bind_item_font(t_orient_val, self.fonts["semibold"])
                                    dpg.add_text("Поворот (R)", color=(110, 120, 135))

                    dpg.add_spacer(height=6)
                    dpg.add_separator()
                    dpg.add_spacer(height=6)

                    # Кнопки действий: Повернуть и Очистить, Случайная, Начать бой
                    # Ровный шаг ровно 4px между всеми тремя рядами кнопок, ширина строго 300px 1:1
                    ctrl_btn_w = 300
                    with dpg.group(tag="placement_actions_group", indent=10):
                        dpg.bind_item_theme("placement_actions_group", "placement_actions_theme")
                        with dpg.group(horizontal=True):
                            if dpg.does_item_exist("ui_btn_rotate"):
                                b_rot = dpg.add_image_button("ui_btn_rotate", width=146, height=36, frame_padding=0, callback=self.rotate, tag="placement_b_rot")
                            else:
                                b_rot = dpg.add_button(label="Повернуть (R)", width=146, height=36, callback=self.rotate, tag="placement_b_rot")
                            dpg.bind_item_theme(b_rot, "ui_image_button")

                            dpg.add_spacer(width=8)

                            if dpg.does_item_exist("ui_btn_clear"):
                                b_clr = dpg.add_image_button("ui_btn_clear", width=146, height=36, frame_padding=0, callback=self.clear_placement, tag="placement_b_clr")
                            else:
                                b_clr = dpg.add_button(label="Очистить", width=146, height=36, callback=self.clear_placement, tag="placement_b_clr")
                            dpg.bind_item_theme(b_clr, "ui_image_button")

                        # Случайная расстановка (строго через 4px от первого ряда)
                        if dpg.does_item_exist("ui_btn_random"):
                            b_rnd = dpg.add_image_button("ui_btn_random", width=ctrl_btn_w, height=36, frame_padding=0, callback=self.auto_place, tag="placement_b_rnd")
                        else:
                            b_rnd = dpg.add_button(label="Случайная расстановка", width=ctrl_btn_w, height=36, callback=self.auto_place, tag="placement_b_rnd")
                        dpg.bind_item_theme(b_rnd, "ui_image_button")

                        # Кнопка Начать бой (строго через 4px от случайной расстановки)
                        if dpg.does_item_exist("ui_btn_start"):
                            b_start = dpg.add_image_button("ui_btn_start", width=ctrl_btn_w, height=42, frame_padding=0, callback=self.start_battle, tag="start_button")
                        else:
                            b_start = dpg.add_button(label="Начать бой", width=ctrl_btn_w, height=42, callback=self.start_battle, tag="start_button")
                        dpg.bind_item_theme(b_start, "ui_image_button")

                    dpg.add_spacer(height=4)
                    dpg.add_text("", tag="placement_status_msg", indent=10, wrap=ctrl_btn_w)

    def _page_multiplayer(self):
        panel_w = min(780, self.view_width - self.sidebar_width - 45)
        panel_h = max(520, self.view_height - 150)
        col_left_w = max(300, panel_w - 295)
        with dpg.group(tag="page_multiplayer", show=True):
            self._title("Онлайн мультиплеер", "Кроссплатформенный бой ПК ↔ Смартфон по протоколу MQTT")
            with dpg.child_window(width=panel_w, height=panel_h, no_scrollbar=True):
                dpg.bind_item_theme(dpg.last_item(), "card_theme")
                dpg.add_spacer(height=10)
                with dpg.group(horizontal=True, indent=14):
                    # Левая колонка: Код комнаты, статус, шаги, кнопки
                    with dpg.child_window(width=col_left_w, height=panel_h - 32, border=False, no_scrollbar=True):
                        dpg.add_text("КОД ВАШЕЙ КОМНАТЫ", color=(120, 130, 145))
                        code_str = self.relay.room_code if self.relay.is_connected else "— — — — —"
                        code_text = dpg.add_text(code_str, tag="room_code", color=(255, 255, 255))
                        if self.fonts and "title" in self.fonts:
                            dpg.bind_item_font(code_text, self.fonts["title"])

                        dpg.add_spacer(height=6)
                        if self.phone_ready:
                            net_msg = "Телефон готов. Расставьте флот и нажмите «Начать бой»"
                            net_col = (255, 255, 255)
                        elif self.relay.is_phone_connected:
                            net_msg = "Телефон подключен"
                            net_col = (255, 255, 255)
                        elif self.relay.is_connected:
                            net_msg = "Комната готова. Ожидание подключения смартфона..."
                            net_col = (255, 255, 255)
                        else:
                            net_msg = "Комната не запущена"
                            net_col = (140, 150, 168)
                        st_text = dpg.add_text(
                            net_msg,
                            tag="network_status",
                            color=net_col,
                            wrap=col_left_w - 16
                        )
                        if self.fonts and "semibold" in self.fonts:
                            dpg.bind_item_font(st_text, self.fonts["semibold"])

                        dpg.add_spacer(height=12)
                        dpg.add_separator()
                        dpg.add_spacer(height=10)

                        dpg.add_text("ИНСТРУКЦИЯ ПО ПОДКЛЮЧЕНИЮ:", color=(120, 130, 145))
                        dpg.add_spacer(height=4)
                        dpg.add_text("1. Нажмите «Создать комнату»", color=(200, 210, 225), wrap=col_left_w - 16)
                        dpg.add_text("2. Отсканируйте QR-код камерой смартфона", color=(200, 210, 225), wrap=col_left_w - 16)
                        dpg.add_text("3. На смартфоне расставьте флот и нажмите «Готов»", color=(200, 210, 225), wrap=col_left_w - 16)
                        dpg.add_text("4. На ПК расставьте корабли и начните бой!", color=(200, 210, 225), wrap=col_left_w - 16)

                        dpg.add_spacer(height=16)
                        with dpg.group(horizontal=True):
                            b_create = dpg.add_button(label="Создать комнату", width=160, height=36, callback=self.create_room)
                            dpg.bind_item_theme(b_create, "primary_button")
                            b_copy = dpg.add_button(label="Копировать ссылку", width=160, height=36, callback=self.copy_room_link)
                            dpg.bind_item_theme(b_copy, "secondary_button")

                        dpg.add_spacer(height=8)
                        with dpg.group(horizontal=True):
                            b_place = dpg.add_button(label="Расставить флот на ПК", width=185, height=36, callback=self.go_to_placement)
                            dpg.bind_item_theme(b_place, "primary_button")
                            b_stop = dpg.add_button(label="Выйти из комнаты", width=155, height=36, callback=self.stop_room)
                            dpg.bind_item_theme(b_stop, "danger_button")

                    # Правая колонка: QR-код
                    with dpg.child_window(width=250, height=panel_h - 32, border=False, no_scrollbar=True):
                        dpg.add_text("QR-КОД ДЛЯ СМАРТФОНА", color=(120, 130, 145))
                        dpg.add_spacer(height=6)
                        with dpg.group(tag="qr_container"):
                            if self.relay.is_connected and dpg.does_item_exist("qr_texture"):
                                dpg.add_image("qr_texture", width=230, height=230, tag="qr_image")
                            else:
                                with dpg.child_window(width=230, height=230, border=True, no_scrollbar=True):
                                    dpg.add_spacer(height=95)
                                    dpg.add_text("Нажмите\n«Создать комнату»", color=(120, 130, 145), indent=45)
                        dpg.add_spacer(height=8)
                        dpg.add_text(self.relay.get_join_url() if self.relay.is_connected else "", tag="join_url", wrap=230, color=(140, 160, 190))

    def _page_settings(self):
        card_w = min(680, self.view_width - self.sidebar_width - 45)
        with dpg.group(tag="page_settings", show=True):
            self._title("Настройки", "Параметры применяются при создании следующего матча")
            with dpg.child_window(width=card_w, height=self.view_height - 150, no_scrollbar=True):
                dpg.bind_item_theme(dpg.last_item(), "card_theme")
                dpg.add_spacer(height=12)
                dpg.add_text("Размер игрового поля", indent=16)
                dpg.add_combo(items=["8 × 8", "10 × 10", "12 × 12"], default_value=f"{self.size} × {self.size}", width=240, indent=16, callback=self.change_size)

                dpg.add_spacer(height=16)
                dpg.add_text("Интеллект бота", indent=16)
                cur_diff = "Умный" if self.difficulty == "smart" else "Легкий"
                dpg.add_combo(items=["Легкий", "Умный"], default_value=cur_diff, width=240, indent=16, callback=self.change_difficulty)

                dpg.add_spacer(height=16)
                dpg.add_text("Адрес веб-клиента (GitHub Pages)", indent=16)
                dpg.add_input_text(default_value=self.relay.github_pages_url, width=card_w - 40, indent=16, tag="github_url", callback=lambda s, a: self.relay.set_github_pages_url(a))

    def _page_about(self):
        card_w = min(840, self.view_width - self.sidebar_width - 45)
        wrap_w = card_w - 48
        f_body = self.fonts.get("about") if self.fonts else None
        f_head = self.fonts.get("about_bold") if self.fonts else None
        f_mono = self.fonts.get("about_mono") if self.fonts else None

        def add_section(title_txt):
            dpg.add_spacer(height=10)
            t = dpg.add_text(title_txt, color=(255, 255, 255), indent=12, wrap=wrap_w)
            if f_head:
                dpg.bind_item_font(t, f_head)
            dpg.add_separator()
            dpg.add_spacer(height=4)

        def add_code_line(text, color=(180, 210, 255)):
            t = dpg.add_text(text, color=color, indent=16, wrap=wrap_w)
            if f_mono:
                dpg.bind_item_font(t, f_mono)

        def add_plain(text, color=(205, 212, 222)):
            t = dpg.add_text(text, color=color, indent=16, wrap=wrap_w)
            if f_body:
                dpg.bind_item_font(t, f_body)

        with dpg.group(tag="page_about", show=True):
            self._title("О проекте", "Простой разбор: где что лежит, какие картинки, импорты и функции работают")
            with dpg.child_window(width=card_w, height=self.view_height - 150, no_scrollbar=False):
                dpg.bind_item_theme(dpg.last_item(), "about_card_theme")

                add_section("1. Где что лежит в папке проекта")
                add_code_line("main.py          — главный файл запуска, все окна, меню, клики и анимации")
                add_code_line("game_logic.py    — правила морского боя, поле, корабли, выстрелы")
                add_code_line("bot.py           — умный бот (поиск по клеткам + добивание)")
                add_code_line("network_relay.py — связь с телефоном через облачный MQTT-брокер и QR")
                add_code_line("theme.py         — цвета, стили кнопок/клеток и загрузка шрифтов")
                add_code_line("make_ui_assets.py— скрипт, который заранее рисует все WebP-иконки и кнопки")
                add_code_line("assets/ui/       — папка со всеми готовыми картинками (WebP) и исходниками SVG")
                add_code_line("web/index.html   — мобильная версия сайта для игры с телефона")
                add_code_line("build.py         — сборка программы в один SeaBattle.exe через PyInstaller")
                add_code_line("tests/test_game.py — автотесты проверки правил, бота и размеров сетки")

                add_section("2. Где лежат картинки (фотки) и как они используются")
                add_plain("В папке assets/ui/ лежат только нужные сжатые WebP-картинки (исходные векторы лежат в assets/ui/svg_sources/). В начале запуска main.py загружает их в видеопамять через PIL + _load_webp_texture:")
                add_code_line("brand_header.webp        — логотип SEA BATTLE вверху левого меню")
                add_code_line("toast_header.webp        — шапка всплывающего уведомления слева сверху")
                add_code_line("nav_<tab>_0..15.webp     — 16 кадров плавной анимации вкладок меню")
                add_code_line("ship_card_<n>_*.webp     — карточки кораблей (зеленые/красные квадратики)")
                add_code_line("orient_<1..5>_frame_0..23.webp — 24 кадра вращения корабля при нажатии R")
                add_code_line("btn_rotate/clear/random/start(_hov).webp — кнопки расстановки и их hover-вид")
                add_code_line("icon_<name>_accent.webp  — иконки бота, мультиплеера, победы и поражения")
                add_plain("QR-код для телефона не хранится файлом: network_relay.py (строки 61–80) рисует его на лету через библиотеку qrcode и кладет в текстуру qr_texture.")

                add_section("3. main.py — главный файл (окно, меню, анимации и клики)")
                add_plain("Импорты: queue (очередь событий из фонового потока сети), pathlib.Path (пути к файлам), sys (путь _MEIPASS внутри exe), threading (сеть без зависания окна), time (таймеры анимаций), dearpygui (весь GUI), PIL.Image (открытие WebP), а также локальные Board, BattleshipBot, NetworkRelay, create_themes, load_fonts.")
                add_code_line("_load_webp_texture(path, tag) | открывает WebP через PIL, переводит пиксели в 0..1 через _INV255 и кладёт в GPU. Нужна при старте в build().")
                add_code_line("SeaBattleApp.__init__ | создаёт доски player/enemy, бота, сетевой клиент и начальные флаги фазы, хода и анимаций.")
                add_code_line("build() | грузит все WebP-картинки, создаёт окно, сайдбар, toast-окно, горячую клавишу R и крутит главный цикл 60 FPS.")
                add_code_line("_sidebar(), _tab_for_page(), _nav_callback() | рисуют левое меню и переключают вкладки (игровое поле и расстановка ведут на вкладку Бой).")
                add_code_line("notify(), _update_toast() | показывают уведомление слева сверху: плавно выезжает с -330px до 16px, уменьшает полоску и прячется.")
                add_code_line("_animate_navigation() | плавно меняет 16 кадров картинки вкладки (nav_<tab>_0..15) за 0.18с, чтобы подсветка таба перетекала.")
                add_code_line("_animate_page_transition() | при открытии вкладки сжимает верхний отступ с 24px до 1px — получается мягкий подъём контента.")
                add_code_line("_animate_orient() | при повороте корабля крутит его иконку на +90° (6 кадров из 24) с замедлением в конце.")
                add_code_line("show_page(page) | очищает правую часть окна, рисует выбранное меню и запускает refresh_all().")
                add_code_line("_page_home(), choose_bot(), choose_multiplayer(), quick_game() | главный экран с карточками режимов и быстрым авто-стартом.")
                add_code_line("_page_placement() | экран расстановки: слева сетка, справа карточки кораблей, виджет поворота и 4 кнопки.")
                add_code_line("_page_game() | экран боя: два поля рядом (ваше и врага) со счётчиками живых кораблей и строкой хода.")
                add_code_line("_page_multiplayer() | код комнаты, статус сети, кнопки запуска/остановки и QR-код для телефона.")
                add_code_line("_page_settings(), _page_about() | настройки (размер поля, сложность бота, ссылка сайта) и эта справка.")
                add_code_line("_board_widget(prefix, clickable, cell) | строит сетку из кнопок: верхние буквы А–К, левые цифры 1–10 и клетки.")
                add_code_line("cell_click(), player_shot(), bot_turn() | обработка клика: ставит/убирает корабль или стреляет по врагу и передаёт ход боту.")
                add_code_line("_update_ship_cards(), select_ship(), rotate(), auto_place(), clear_placement() | управление флотом при расстановке.")
                add_code_line("start_battle(), new_game(), finish(), show_game_over_dialog() | старт матча, сброс, завершение и модальное окно победы/поражения.")
                add_code_line("refresh_all(), _refresh_board(), _get_cell_base_theme() | обновляют цвета, символы (■, •, ×) и счётчики на обоих полях.")
                add_code_line("_update_button_hovers() | как работает подсветка кнопок: каждый кадр проверяет is_item_hovered(tag) и меняет текстуру на *_hov (и обратно).")
                add_code_line("_update_board_hover() | как работает прицел: находит клетку под курсором, красит букву/цифру, лучи перекрестия и пишет [ Г-5 ].")
                add_code_line("change_size(), change_difficulty(), copy_room_link(), create_room(), stop_room() | настройки матча и управление комнатой.")
                add_code_line("_process_events(), _resize() | разбирает события от телефона из очереди queue и подстраивает размер интерфейса при растягивании окна.")

                add_section("4. game_logic.py — правила, поле и корабли")
                add_plain("Импорты: random (случайная расстановка), typing (типы). Этот файл ничего не знает про графику — только чистые правила игры.")
                add_code_line("Ship (hit, is_sunk, get_surrounding_cells) | хранит координаты палуб, попадания и вычисляет клетки вокруг потопленного корабля.")
                add_code_line("Board (can_place_ship, place_ship, remove_ship_at) | проверяет, чтобы корабли не касались даже углами, ставит и убирает их.")
                add_code_line("Board.auto_place_all() | случайно расставляет весь флот от крупных кораблей к мелким (до 500 попыток).")
                add_code_line("Board.receive_shot() | принимает выстрел, возвращает miss/hit/sunk и при потоплении автоматически ставит промахи вокруг.")
                add_code_line("Board.get_view(hide=True) | прячет живые корабли противника (туман войны), оставляя только выстрелы.")

                add_section("5. bot.py — искусственный интеллект")
                add_plain("Импорты: random, typing. Нужен для одиночной игры против ПК в режимах easy и smart.")
                add_code_line("register_shot_result() | запоминает попадание, при потоплении очищает очередь и вычеркивает клетки вокруг корабля.")
                add_code_line("_update_target_queue_after_hit() | после 1 попадания проверяет 4 стороны крестом, после 2+ бьёт строго вдоль линии корабля.")
                add_code_line("choose_shot() | выбирает клетку: сначала очередь добивания, затем шахматная сетка (r+c)%2==0, иначе случайно.")

                add_section("6. network_relay.py — связь ПК с телефоном")
                add_plain("Импорты: json, random, string, threading, time, PIL.Image, paho.mqtt.client, qrcode.")
                add_code_line("generate_room_code() | делает 5-значный код комнаты без путающихся символов (0/O, 1/I).")
                add_code_line("generate_qr_texture_data() | генерирует QR-картинку со ссылкой ?room=КОД прямо в памяти для Dear PyGui.")
                add_code_line("start(), _on_connect(), _on_message(), send_to_phone() | подключается к HiveMQ/EMQX и пересылает выстрелы между ПК и телефоном.")

                add_section("7. theme.py, make_ui_assets.py, web/index.html, build.py")
                add_code_line("theme.py: create_themes(), load_fonts() | задаёт всю чёрно-белую палитру, скругления, цвета клеток и грузит шрифты Segoe UI / Calibri / Consolas.")
                add_code_line("make_ui_assets.py: build_assets() | рендерит SVG через matplotlib/PIL в 264 сжатых WebP-файла в папке assets/ui/.")
                add_code_line("web/index.html | мобильная копия игры для браузера телефона: MQTT по WSS, вращение корабля по тапу и перекрестие под пальцем.")
                add_code_line("build.py | собирает весь проект и папку assets/ui/ в один файл dist/SeaBattle.exe через PyInstaller.")
                dpg.add_spacer(height=10)

    def _title(self, title, subtitle):
        dpg.add_spacer(height=4)
        item = dpg.add_text(title, color=(255, 255, 255), indent=12)
        if self.fonts and "title" in self.fonts:
            dpg.bind_item_font(item, self.fonts["title"])
        detail = dpg.add_text(subtitle, color=(100, 110, 128), indent=12)
        if self.fonts and "regular" in self.fonts:
            dpg.bind_item_font(detail, self.fonts["regular"])
        dpg.add_spacer(height=6)

    def _board_widget(self, prefix, clickable, cell=34):
        with dpg.group(tag=f"grid_{prefix}"):
            with dpg.group(horizontal=True, horizontal_spacing=2):
                dpg.add_button(label="", width=24, height=cell, enabled=False)
                dpg.bind_item_theme(dpg.last_item(), "cell_coord")
                for c in range(self.size):
                    btn = dpg.add_button(
                        label=Board.coord_to_str(0, c).split('-')[0],
                        width=cell,
                        height=cell,
                        enabled=False,
                        tag=f"{prefix}_col_{c}"
                    )
                    dpg.bind_item_theme(btn, "cell_coord")

            for r in range(self.size):
                with dpg.group(horizontal=True, horizontal_spacing=2):
                    btn_num = dpg.add_button(
                        label=str(r + 1),
                        width=24,
                        height=cell,
                        enabled=False,
                        tag=f"{prefix}_row_{r}"
                    )
                    dpg.bind_item_theme(btn_num, "cell_coord")
                    for c in range(self.size):
                        cb = (lambda s, a, u: self.cell_click(*u)) if clickable else None
                        cell_btn = dpg.add_button(
                            label="",
                            width=cell,
                            height=cell,
                            callback=cb,
                            user_data=(prefix, r, c),
                            tag=f"{prefix}_{r}_{c}"
                        )
                        dpg.bind_item_theme(cell_btn, "cell_water")
        dpg.bind_item_theme(f"grid_{prefix}", "board_grid")

    def cell_click(self, prefix, r, c):
        if prefix == "placement":
            if self.phase != "placement":
                return
            if self.player.get_cell(r, c) == CELL_SHIP:
                removed = self.player.remove_ship_at(r, c)
                if removed:
                    self.selected_size = removed.size
                    curr_f = (getattr(self, "orient_angle_idx", 1) * 6) % 24
                    tex = f"ui_orient_{self.selected_size}_frame_{curr_f}"
                    if not dpg.does_item_exist(tex):
                        tex = f"ui_orient_frame_{curr_f}"
                    if dpg.does_item_exist("orient_widget_btn"):
                        dpg.configure_item("orient_widget_btn", texture_tag=tex)
                self.notify("Корабль убран с поля")
                if dpg.does_item_exist("placement_status_msg"):
                    dpg.set_value("placement_status_msg", "")
            elif self.player.get_remaining_to_place().get(self.selected_size, 0) > 0:
                placed = self.player.place_ship(r, c, self.selected_size, self.orientation)
                if not placed and dpg.does_item_exist("placement_status_msg"):
                    dpg.set_value("placement_status_msg", "Нельзя поставить: касание или выход за край!")
                    dpg.configure_item("placement_status_msg", color=(248, 113, 113))
                elif placed:
                    self.notify(f"Корабль ({self.selected_size} палуб) установлен")
                    if dpg.does_item_exist("placement_status_msg"):
                        dpg.set_value("placement_status_msg", "")
                    # Автовыбор следующего доступного типа корабля, если текущий исчерпан
                    rem_after = self.player.get_remaining_to_place()
                    if rem_after.get(self.selected_size, 0) <= 0:
                        for next_sz in sorted(rem_after.keys(), reverse=True):
                            if rem_after[next_sz] > 0:
                                self.selected_size = next_sz
                                curr_f = (getattr(self, "orient_angle_idx", 1) * 6) % 24
                                tex = f"ui_orient_{self.selected_size}_frame_{curr_f}"
                                if not dpg.does_item_exist(tex):
                                    tex = f"ui_orient_frame_{curr_f}"
                                if dpg.does_item_exist("orient_widget_btn"):
                                    dpg.configure_item("orient_widget_btn", texture_tag=tex)
                                break
            else:
                msg = f"Все корабли ({self.selected_size} палуб) уже расставлены! Выберите другой тип."
                if dpg.does_item_exist("placement_status_msg"):
                    dpg.set_value("placement_status_msg", msg)
                    dpg.configure_item("placement_status_msg", color=(248, 113, 113))
                self.notify(msg, duration=2.0)
            self.refresh_all()
        elif prefix == "enemy" and self.phase == "battle" and self.turn == "player":
            self.player_shot(r, c)

    def player_shot(self, r, c):
        if self.mode == "multiplayer":
            if self.enemy.get_cell(r, c) != CELL_EMPTY:
                return
            self.turn = "waiting"
            self.relay.send_to_phone({"action": "incoming_shot", "r": r, "c": c})
            self._log(f"Выстрел {Board.coord_to_str(r, c)}: ожидание...")
            self.refresh_all()
            return

        result, ship, misses = self.enemy.receive_shot(r, c)
        if result in ("invalid", "already_shot"):
            return
        res_name = self._result_name(result)
        self._log(f"Выстрел {Board.coord_to_str(r, c)}: {res_name}")
        self.notify(f"Выстрел {Board.coord_to_str(r, c)}: {res_name}")

        if self.enemy.is_all_sunk:
            self.finish("Победа! Флот противника полностью уничтожен.", is_victory=True)
            return

        if result == "miss":
            self.turn = "bot"
            self.refresh_all()
            dpg.set_frame_callback(dpg.get_frame_count() + 25, self.bot_turn)
        else:
            self.refresh_all()

    def bot_turn(self):
        if self.phase != "battle":
            return
        shot = self.bot.choose_shot()
        if not shot:
            return
        r, c = shot
        result, ship, misses = self.player.receive_shot(r, c)
        self.bot.register_shot_result(r, c, result, ship.cells if ship else None, misses)
        res_name = self._result_name(result)
        self._log(f"Бот стреляет {Board.coord_to_str(r, c)}: {res_name}")

        if self.player.is_all_sunk:
            self.finish("Поражение. Ваш флот уничтожен.", is_victory=False)
            return
        if result == "miss":
            self.turn = "player"
        else:
            dpg.set_frame_callback(dpg.get_frame_count() + 25, self.bot_turn)
        self.refresh_all()

    def _update_ship_cards(self):
        """Обновляет карточки кораблей (зеленые/красные квадраты и цвет фона блоков)."""
        rem_dict = self.player.get_remaining_to_place()
        for n in self.player.fleet_config.keys():
            btn_tag = f"ship_btn_{n}"
            if dpg.does_item_exist(btn_tag):
                total = self.player.fleet_config.get(n, 1)
                rem = rem_dict.get(n, 0)
                placed = max(0, min(total, total - rem))
                is_active = 1 if n == self.selected_size else 0
                tex_tag = f"ui_ship_card_{n}_{total}_{placed}_{is_active}"
                if not dpg.does_item_exist(tex_tag):
                    tex_tag = f"ui_ship_card_{n}_{'active' if is_active else 'normal'}"
                if dpg.does_item_exist(tex_tag):
                    dpg.configure_item(btn_tag, texture_tag=tex_tag)

    def select_ship(self, sender, value, user_data):
        self.selected_size = int(user_data)
        self._update_ship_cards()
        curr_f = (getattr(self, "orient_angle_idx", 0) * 6) % 24
        tex = f"ui_orient_{self.selected_size}_frame_{curr_f}"
        if not dpg.does_item_exist(tex):
            tex = f"ui_orient_frame_{curr_f}"
        if dpg.does_item_exist("orient_widget_btn"):
            dpg.configure_item("orient_widget_btn", texture_tag=tex)

    def rotate(self, *args):
        old_idx = getattr(self, "orient_angle_idx", 0)
        new_idx = (old_idx + 1) % 4
        self.orient_angle_idx = new_idx
        self.orientation = "V" if new_idx in (0, 2) else "H"
        orient_name = "Вертикальное" if self.orientation == "V" else "Горизонтальное"
        
        # Поворот по часовой стрелке на +90° (6 кадров)
        start_f = old_idx * 6
        end_f = old_idx * 6 + 6
        self.orient_anim = (start_f, end_f, time.monotonic())
        
        if dpg.does_item_exist("orientation_text"):
            dpg.set_value("orientation_text", orient_name)
        self.notify(f"Расположение: {orient_name}", duration=1.0)

    def _rotate_hotkey(self, *args):
        if self.current_page == "placement":
            self.rotate()

    def auto_place(self):
        self.player.auto_place_all()
        if dpg.does_item_exist("placement_status_msg"):
            dpg.set_value("placement_status_msg", "Весь флот расставлен! Нажмите «Начать бой»")
            dpg.configure_item("placement_status_msg", color=(240, 243, 248))
        self.notify("Флот расставлен автоматически!")
        self.refresh_all()

    def clear_placement(self):
        self.player.reset()
        if dpg.does_item_exist("placement_status_msg"):
            dpg.set_value("placement_status_msg", "")
            dpg.configure_item("placement_status_msg", color=(248, 113, 113))
        self.notify("Поле очищено")
        self.refresh_all()

    def start_battle(self):
        if not self.player.is_fleet_complete():
            rem = self.player.get_remaining_to_place()
            rem_str = ", ".join(f"{s}пал: {n}" for s, n in sorted(rem.items(), reverse=True) if n > 0)
            msg = f"Расставьте весь флот! Осталось: {rem_str}"
            self._set_status(msg)
            if dpg.does_item_exist("placement_status_msg"):
                dpg.set_value("placement_status_msg", msg)
                dpg.configure_item("placement_status_msg", color=(248, 113, 113))
            self.notify(msg, duration=3.0)
            return

        if dpg.does_item_exist("placement_status_msg"):
            dpg.set_value("placement_status_msg", "")

        if self.mode == "multiplayer":
            if not self.phone_ready:
                self._set_status("Телефон еще не готов")
                self.show_page("multiplayer")
                self.notify("Ожидание готовности телефона...")
                return
            self.enemy = Board(self.size, {})
            self.phase, self.turn, self.log = "battle", "player", ["Сетевой бой начался. Ваш ход!"]
            self.relay.send_to_phone({"action": "game_start", "phone_turn": False, "size": self.size})
            self.show_page("game")
            self.notify("Сетевой бой начался! Ваш ход")
            self.refresh_all()
            return

        self.enemy = Board(self.size)
        self.enemy.auto_place_all()
        self.bot = BattleshipBot(self.size, self.difficulty)
        self.phase, self.turn, self.log = "battle", "player", ["Бой начался. Ваш ход!"]
        self.show_page("game")
        self.notify("Бой начался! Ваш ход")
        self.refresh_all()

    def new_game(self, *args):
        self.player = Board(self.size)
        self.enemy = Board(self.size)
        self.bot = BattleshipBot(self.size, self.difficulty)
        self.phase, self.turn, self.log = "placement", "player", []
        if self.mode != "multiplayer":
            self.phone_ready = False
        self.show_page("placement")
        self.refresh_all()

    def finish(self, text, is_victory=True):
        self.phase = "finished"
        self._log(text)
        self._set_status(text)
        self.refresh_all()
        title = "ПОБЕДА!" if is_victory else "ПОРАЖЕНИЕ!"
        self.notify(text, duration=4.0)
        self.show_game_over_dialog(title, text, is_victory)

    def show_game_over_dialog(self, title, message, is_victory):
        if dpg.does_item_exist("modal_game_over"):
            dpg.delete_item("modal_game_over")
        modal_w, modal_h = 460, 275
        with dpg.window(
            label="Итоги матча",
            modal=True,
            show=True,
            tag="modal_game_over",
            no_resize=True,
            width=modal_w,
            height=modal_h,
            pos=((self.view_width - modal_w) // 2, (self.view_height - modal_h) // 2)
        ):
            dpg.bind_item_theme("modal_game_over", "card_theme")
            dpg.add_spacer(height=10)
            with dpg.group(horizontal=True, indent=16):
                icon_tag = "ui_icon_win_accent" if is_victory else "ui_icon_despair_accent"
                if dpg.does_item_exist(icon_tag):
                    dpg.add_image(icon_tag, width=32, height=32)
                t = dpg.add_text(title, color=(255, 255, 255) if is_victory else (248, 113, 113))
                if self.fonts and "title" in self.fonts:
                    dpg.bind_item_font(t, self.fonts["title"])

            dpg.add_spacer(height=8)
            t_msg = dpg.add_text(message, indent=16, wrap=modal_w - 40)
            if self.fonts and "regular" in self.fonts:
                dpg.bind_item_font(t_msg, self.fonts["regular"])

            dpg.add_spacer(height=14)
            dpg.add_separator()
            dpg.add_spacer(height=14)

            with dpg.group(horizontal=True, indent=16):
                b1 = dpg.add_button(label="Сыграть снова", width=195, height=38, callback=self._restart_from_modal)
                dpg.bind_item_theme(b1, "primary_button")
                b2 = dpg.add_button(label="В главное меню", width=195, height=38, callback=self._menu_from_modal)
                dpg.bind_item_theme(b2, "secondary_button")

    def _restart_from_modal(self):
        if dpg.does_item_exist("modal_game_over"):
            dpg.delete_item("modal_game_over")
        self.new_game()

    def _menu_from_modal(self):
        if dpg.does_item_exist("modal_game_over"):
            dpg.delete_item("modal_game_over")
        if self.room_locked:
            self.stop_room()
        else:
            self._clear_session()
        self.show_page("home")

    def _log(self, text):
        self.log.insert(0, text)
        self.log = self.log[:18]

    def _set_status(self, text):
        self.status = text

    def _result_name(self, r):
        return {"miss": "промах", "hit": "попадание", "sunk": "корабль потоплен"}.get(r, r)

    def refresh_all(self):
        self._refresh_board("placement", self.player, False)
        self._refresh_board("player", self.player, False)
        self._refresh_board("enemy", self.enemy, True)

        self._update_ship_cards()

        if dpg.does_item_exist("player_alive"):
            dpg.set_value("player_alive", f"Кораблей: {self.player.count_alive_ships()}")

        if dpg.does_item_exist("enemy_alive"):
            enemy_count = self.enemy.count_alive_ships() if self.mode == "bot" else "—"
            dpg.set_value("enemy_alive", f"Кораблей: {enemy_count}")

        opponent = "телефона" if self.mode == "multiplayer" else "бота"
        if dpg.does_item_exist("battle_status_line"):
            if self.phase == "battle":
                st = "Ваш ход — выберите клетку на поле противника" if self.turn == "player" else f"Ход {opponent} (ожидание выстрела...)"
                dpg.set_value("battle_status_line", st)
                dpg.configure_item("battle_status_line", color=(255, 255, 255) if self.turn == "player" else (249, 115, 22))
            elif self.phase == "finished":
                dpg.set_value("battle_status_line", "Матч завершен")
                dpg.configure_item("battle_status_line", color=(255, 255, 255))
            else:
                dpg.set_value("battle_status_line", "Матч еще не начат")

        if self.player.is_fleet_complete() and dpg.does_item_exist("placement_status_msg"):
            curr = dpg.get_value("placement_status_msg")
            if not curr or "Осталось" in curr:
                dpg.set_value("placement_status_msg", "Весь флот расставлен! Нажмите «Начать бой»")
                dpg.configure_item("placement_status_msg", color=(240, 243, 248))

    def _refresh_board(self, prefix, board, hide):
        if not dpg.does_item_exist(f"{prefix}_0_0"):
            return
        if self._hovered_cell and self._hovered_cell[0] == prefix:
            self._hovered_cell = None
        view = board.get_view(hide)
        themes = {
            CELL_EMPTY: "cell_water",
            CELL_SHIP: "cell_ship",
            CELL_MISS: "cell_miss",
            CELL_HIT: "cell_hit",
            CELL_SUNK: "cell_sunk"
        }
        labels = {
            CELL_EMPTY: "",
            CELL_SHIP: "■",
            CELL_MISS: "•",
            CELL_HIT: "×",
            CELL_SUNK: "×"
        }
        for r in range(self.size):
            for c in range(self.size):
                val = view[r][c]
                dpg.configure_item(f"{prefix}_{r}_{c}", label=labels[val])
                dpg.bind_item_theme(f"{prefix}_{r}_{c}", themes[val])

    def _get_cell_base_theme(self, prefix, r, c):
        themes = {
            CELL_EMPTY: "cell_water",
            CELL_SHIP: "cell_ship",
            CELL_MISS: "cell_miss",
            CELL_HIT: "cell_hit",
            CELL_SUNK: "cell_sunk"
        }
        try:
            if prefix in ("placement", "player"):
                val = self.player.get_cell(r, c)
                return themes.get(val, "cell_water")
            elif prefix == "enemy":
                val = self.enemy.get_view(hide=True)[r][c]
                return themes.get(val, "cell_water")
        except Exception:
            pass
        return "cell_water"

    def _update_button_hovers(self):
        btns = (
            ("btn_rotate", "placement_b_rot"),
            ("btn_clear", "placement_b_clr"),
            ("btn_random", "placement_b_rnd"),
            ("btn_start", "start_button")
        )
        for name, tag in btns:
            if dpg.does_item_exist(tag):
                is_hov = dpg.is_item_hovered(tag)
                tex = f"ui_{name}_hov" if is_hov else f"ui_{name}"
                if dpg.does_item_exist(tex):
                    curr = dpg.get_item_configuration(tag).get("texture_tag")
                    if curr != tex:
                        dpg.configure_item(tag, texture_tag=tex)

    def _update_board_hover(self):
        active_prefixes = []
        for pfx in ("placement", "enemy", "player"):
            if dpg.does_item_exist(f"{pfx}_0_0"):
                active_prefixes.append(pfx)

        found = None
        for prefix in active_prefixes:
            for r in range(self.size):
                for c in range(self.size):
                    tag = f"{prefix}_{r}_{c}"
                    if dpg.does_item_exist(tag) and dpg.is_item_hovered(tag):
                        found = (prefix, r, c)
                        break
                if found:
                    break
            if found:
                break

        if found == self._hovered_cell:
            return

        # 1. Сброс предыдущей подсветки перекрестия
        if self._hovered_cell is not None:
            p_pfx, p_r, p_c = self._hovered_cell
            if dpg.does_item_exist(f"{p_pfx}_col_{p_c}"):
                dpg.bind_item_theme(f"{p_pfx}_col_{p_c}", "cell_coord")
            if dpg.does_item_exist(f"{p_pfx}_row_{p_r}"):
                dpg.bind_item_theme(f"{p_pfx}_row_{p_r}", "cell_coord")
            for ci in range(self.size):
                tag = f"{p_pfx}_{p_r}_{ci}"
                if dpg.does_item_exist(tag):
                    dpg.bind_item_theme(tag, self._get_cell_base_theme(p_pfx, p_r, ci))
            for ri in range(self.size):
                tag = f"{p_pfx}_{ri}_{p_c}"
                if dpg.does_item_exist(tag):
                    dpg.bind_item_theme(tag, self._get_cell_base_theme(p_pfx, ri, p_c))
            hint_tag = f"{p_pfx}_coord_hint"
            if dpg.does_item_exist(hint_tag):
                dpg.set_value(hint_tag, "")

        self._hovered_cell = found

        # 2. Активация новой подсветки
        if found is not None:
            prefix, r, c = found
            if dpg.does_item_exist(f"{prefix}_col_{c}"):
                dpg.bind_item_theme(f"{prefix}_col_{c}", "cell_coord_highlight")
            if dpg.does_item_exist(f"{prefix}_row_{r}"):
                dpg.bind_item_theme(f"{prefix}_row_{r}", "cell_coord_highlight")
            # Линия строки от левого заголовка до курсора
            for ci in range(c):
                tag = f"{prefix}_{r}_{ci}"
                if dpg.does_item_exist(tag):
                    b_th = self._get_cell_base_theme(prefix, r, ci)
                    if b_th in ("cell_water", "cell_ship"):
                        dpg.bind_item_theme(tag, "cell_ship_crosshair" if b_th == "cell_ship" else "cell_water_crosshair")
            # Линия столбца от верхнего заголовка до курсора
            for ri in range(r):
                tag = f"{prefix}_{ri}_{c}"
                if dpg.does_item_exist(tag):
                    b_th = self._get_cell_base_theme(prefix, ri, c)
                    if b_th in ("cell_water", "cell_ship"):
                        dpg.bind_item_theme(tag, "cell_ship_crosshair" if b_th == "cell_ship" else "cell_water_crosshair")
            # Целевая клетка под курсором
            target_tag = f"{prefix}_{r}_{c}"
            if dpg.does_item_exist(target_tag):
                b_th = self._get_cell_base_theme(prefix, r, c)
                if b_th == "cell_water":
                    dpg.bind_item_theme(target_tag, "cell_target")
            # Индикатор точной координаты
            hint_tag = f"{prefix}_coord_hint"
            if dpg.does_item_exist(hint_tag):
                coord_str = Board.coord_to_str(r, c)
                dpg.set_value(hint_tag, f"[ {coord_str} ]")

    def change_size(self, sender, value):
        new_size = int(value.split()[0])
        if new_size == self.size:
            return
        self.size = new_size
        self.player = Board(self.size)
        self.enemy = Board(self.size)
        self.bot = BattleshipBot(self.size, self.difficulty)
        self.phase = "placement"
        self.turn = "player"
        self.log = []
        available_sizes = sorted(self.player.fleet_config.keys(), reverse=True)
        self.selected_size = available_sizes[0]
        self.notify(f"Размер поля: {self.size}×{self.size}")
        self._set_status(f"Размер поля изменен на {self.size}×{self.size}.")

    def change_difficulty(self, sender, value):
        self.difficulty = "easy" if value == "Легкий" else "smart"
        self.notify(f"Сложность: {value}")

    def copy_room_link(self):
        url = self.relay.get_join_url()
        try:
            dpg.set_clipboard_text(url)
            self.notify("Ссылка скопирована в буфер обмена!")
        except Exception:
            self.notify(f"Ссылка: {url}")

    def go_to_placement(self):
        self.mode = "multiplayer"
        if self.size != 10:
            self.size = 10
            self.selected_size = 4
            self.notify("Для мультиплеера установлен размер поля 10×10")
        self.new_game()

    def create_room(self):
        self.mode = "multiplayer"
        self.room_locked = True
        if self.size != 10:
            self.size = 10
            self.selected_size = 4
        self.phone_ready = False
        if dpg.does_item_exist("room_code"):
            dpg.set_value("room_code", self.relay.room_code)
        if dpg.does_item_exist("join_url"):
            dpg.set_value("join_url", self.relay.get_join_url())
        if dpg.does_item_exist("network_status"):
            dpg.set_value("network_status", "Подключение к брокеру...")

        def _connect_bg():
            self.relay.start()
            self.events.put(("room_updated", None))

        threading.Thread(target=_connect_bg, daemon=True).start()
        w, h, data = self.relay.generate_qr_texture_data()
        if dpg.does_item_exist("qr_image"):
            dpg.delete_item("qr_image")
        if dpg.does_item_exist("qr_texture"):
            dpg.delete_item("qr_texture")
        with dpg.texture_registry(show=False):
            dpg.add_static_texture(w, h, data, tag="qr_texture")
        if dpg.does_item_exist("qr_container"):
            dpg.delete_item("qr_container", children_only=True)
            dpg.add_image("qr_texture", width=230, height=230, tag="qr_image", parent="qr_container")
        self._save_session()
        self.notify(f"Комната создана: {self.relay.room_code}")

    def stop_room(self):
        if self.relay.is_connected:
            self.relay.send_to_phone({"action": "room_closed"})
        self.relay.stop()
        self.phone_ready = False
        self.room_locked = False
        self.phase = "placement"
        self.turn = "player"
        self._clear_session()
        if dpg.does_item_exist("room_code"):
            dpg.set_value("room_code", "— — — — —")
        if dpg.does_item_exist("network_status"):
            dpg.set_value("network_status", "Вы вышли из комнаты")
        if dpg.does_item_exist("join_url"):
            dpg.set_value("join_url", "")
        if dpg.does_item_exist("qr_container"):
            dpg.delete_item("qr_container", children_only=True)
            with dpg.child_window(width=230, height=230, border=True, no_scrollbar=True, parent="qr_container"):
                dpg.add_spacer(height=95)
                dpg.add_text("Нажмите\n«Создать комнату»", color=(120, 130, 145), indent=45)
        self.notify("Вы вышли из комнаты")

    def _save_session(self):
        try:
            payload = {
                "mode": self.mode,
                "room_code": self.relay.room_code,
                "room_locked": self.room_locked,
                "phase": self.phase,
                "turn": self.turn,
                "size": self.size,
                "difficulty": self.difficulty,
                "current_page": self.current_page,
                "phone_ready": self.phone_ready,
                "player_grid": self.player.grid,
                "player_ships": [
                    {"size": s.size, "cells": s.cells, "hits": list(s.hits), "orientation": s.orientation}
                    for s in self.player.ships
                ],
                "enemy_grid": self.enemy.grid,
                "enemy_ships": [
                    {"size": s.size, "cells": s.cells, "hits": list(s.hits), "orientation": s.orientation}
                    for s in self.enemy.ships
                ],
            }
            SESSION_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _clear_session(self):
        try:
            if SESSION_FILE.exists():
                SESSION_FILE.unlink()
        except Exception:
            pass

    def _restore_session(self) -> str:
        if not SESSION_FILE.exists():
            return "home"
        try:
            data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            if not (data.get("room_locked") or data.get("phase") == "battle"):
                return "home"
            self.mode = data.get("mode", "bot")
            self.size = int(data.get("size", 10))
            self.difficulty = data.get("difficulty", "smart")
            self.phase = data.get("phase", "placement")
            self.turn = data.get("turn", "player")
            self.room_locked = bool(data.get("room_locked", False))
            self.phone_ready = bool(data.get("phone_ready", False))

            self.player = Board(self.size)
            self.player.grid = data.get("player_grid", self.player.grid)
            self.player.ships = []
            for sd in data.get("player_ships", []):
                sh = Ship(sd["size"], [tuple(c) for c in sd["cells"]], sd.get("orientation", "H"))
                sh.hits = {tuple(h) for h in sd.get("hits", [])}
                self.player.ships.append(sh)

            self.enemy = Board(self.size, {} if self.mode == "multiplayer" else None)
            self.enemy.grid = data.get("enemy_grid", self.enemy.grid)
            self.enemy.ships = []
            for sd in data.get("enemy_ships", []):
                sh = Ship(sd["size"], [tuple(c) for c in sd["cells"]], sd.get("orientation", "H"))
                sh.hits = {tuple(h) for h in sd.get("hits", [])}
                self.enemy.ships.append(sh)

            self.bot = BattleshipBot(self.size, self.difficulty)
            if self.room_locked and data.get("room_code"):
                self.relay.room_code = data["room_code"]
                w, h, qdata = self.relay.generate_qr_texture_data()
                if dpg.does_item_exist("qr_texture"):
                    dpg.delete_item("qr_texture")
                with dpg.texture_registry(show=False):
                    dpg.add_static_texture(w, h, qdata, tag="qr_texture")
                threading.Thread(target=lambda: self.relay.start(self.relay.room_code), daemon=True).start()

            page = data.get("current_page", "home")
            if page in ("game", "placement", "multiplayer"):
                self.notify("Сессия восстановлена!")
                return page
        except Exception:
            self._clear_session()
        return "home"

    def _process_events(self):
        now = time.monotonic()
        if self.relay.is_connected and (now - self._last_heartbeat_sent) >= 3.0:
            self._last_heartbeat_sent = now
            self.relay.send_to_phone({"action": "heartbeat"})

        if (
            self.relay.is_phone_connected
            and self.relay.last_phone_seen > 0
            and (now - self.relay.last_phone_seen) > 12.0
        ):
            self.relay.is_phone_connected = False
            self.relay.last_phone_seen = 0.0
            self.phone_ready = False
            self.events.put(("phone_afk", None))

        if self.relay.is_connected and dpg.does_item_exist("network_status") and dpg.get_value("network_status") == "Подключение к брокеру...":
            dpg.set_value("network_status", "Комната готова. Ожидание подключения смартфона...")
        try:
            while True:
                action, data = self.events.get_nowait()
                if action == "room_updated":
                    if dpg.does_item_exist("room_code"):
                        dpg.set_value("room_code", self.relay.room_code)
                    if dpg.does_item_exist("join_url"):
                        dpg.set_value("join_url", self.relay.get_join_url())
                elif action == "relay_error":
                    if dpg.does_item_exist("network_status"):
                        dpg.set_value("network_status", "Ошибка подключения к брокеру")
                    self.notify("Не удалось подключиться к MQTT брокеру", duration=3.5)
                elif action == "phone_connected":
                    if dpg.does_item_exist("network_status"):
                        dpg.set_value("network_status", "Телефон подключен")
                    self.notify("Телефон подключен!")
                elif action in ("phone_left", "phone_afk"):
                    self.phone_ready = False
                    msg = "Смартфон вышел из комнаты" if action == "phone_left" else "Смартфон отключился (AFK)"
                    if dpg.does_item_exist("network_status"):
                        dpg.set_value("network_status", msg)
                    self.notify(msg, duration=3.0)
                    if self.phase == "battle" and self.mode == "multiplayer":
                        self.phase = "placement"
                        self.show_page("multiplayer")
                elif action == "phone_ready":
                    self.phone_ready = True
                    if dpg.does_item_exist("network_status"):
                        dpg.set_value("network_status", "Телефон готов. Расставьте флот и нажмите «Начать бой»")
                    self.notify("Телефон готов к бою!")
                elif action == "phone_restart":
                    self.phone_ready = False
                    if dpg.does_item_exist("network_status"):
                        dpg.set_value("network_status", "Телефон подключен (новая расстановка)")
                    self.notify("Игрок на телефоне готовится к новой игре")
                elif action == "phone_shot" and self.phase == "battle":
                    if self.turn != "phone":
                        continue
                    r, c = data
                    result, ship, misses = self.player.receive_shot(r, c)
                    all_sunk = self.player.is_all_sunk
                    self.relay.send_to_phone({
                        "action": "shot_result",
                        "r": r,
                        "c": c,
                        "res": result,
                        "surrounding": misses,
                        "all_sunk": all_sunk
                    })
                    res_name = self._result_name(result)
                    self._log(f"Телефон стреляет {Board.coord_to_str(r, c)}: {res_name}")
                    self.notify(f"Телефон: {Board.coord_to_str(r, c)} ({res_name})")
                    if all_sunk:
                        self.relay.send_to_phone({"action": "game_over", "winner": "phone"})
                        self.finish("Поражение. Ваш флот уничтожен.", is_victory=False)
                    else:
                        self.turn = "phone" if result in ("hit", "sunk") else "player"
                    self.refresh_all()
                elif action == "defense_result" and self.phase == "battle":
                    r, c = int(data["r"]), int(data["c"])
                    result = data.get("res", "miss")
                    self.enemy.grid[r][c] = CELL_MISS if result == "miss" else CELL_HIT if result == "hit" else CELL_SUNK
                    for mr, mc in data.get("surrounding", []):
                        self.enemy.grid[mr][mc] = CELL_MISS
                    res_name = self._result_name(result)
                    self._log(f"Выстрел {Board.coord_to_str(r, c)}: {res_name}")
                    self.notify(f"Выстрел: {res_name}")
                    total_fleet_cells = sum(s * count for s, count in self.player.fleet_config.items())
                    sunk_or_hit_cells = sum(1 for row in self.enemy.grid for cell in row if cell in (CELL_HIT, CELL_SUNK))
                    if data.get("all_sunk", False) or sunk_or_hit_cells >= total_fleet_cells:
                        self.relay.send_to_phone({"action": "game_over", "winner": "pc"})
                        self.finish("Победа! Флот противника уничтожен.", is_victory=True)
                        return
                    self.turn = "player" if result in ("hit", "sunk") else "phone"
                    self.refresh_all()
        except queue.Empty:
            pass

    def _resize(self, *args):
        width, height = dpg.get_viewport_client_width(), dpg.get_viewport_client_height()
        if width <= 0 or height <= 0 or (width, height) == (self.view_width, self.view_height):
            return
        self.view_width, self.view_height = width, height
        if dpg.does_item_exist("content"):
            self.show_page(self.current_page, animate=False)


if __name__ == "__main__":
    SeaBattleApp().build()
