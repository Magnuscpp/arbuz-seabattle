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
import queue
from pathlib import Path
import sys
import threading
import time
import dearpygui.dearpygui as dpg

from bot import BattleshipBot
from game_logic import Board, CELL_EMPTY, CELL_SHIP, CELL_MISS, CELL_HIT, CELL_SUNK
from network_relay import NetworkRelay
from theme import create_themes, load_fonts


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
        self.phone_ready = False
        self.view_width, self.view_height = 1200, 740
        self.current_page = "home"
        self.sidebar_width = 225

        # Анимации перехода табов и страниц
        self.nav_animation = None
        self.page_transition = None
        self.orient_anim = None

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

        # Загрузка текстур
        with dpg.texture_registry(show=False):
            dpg.add_static_texture(1, 1, [1.0, 1.0, 1.0, 1.0], tag="qr_texture")
            asset_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "assets" / "ui"

            # Бренд-хедер
            brand_path = asset_dir / "brand_header.png"
            if brand_path.exists():
                w, h, _, data = dpg.load_image(str(brand_path))
                dpg.add_static_texture(w, h, data, tag="ui_brand_header")

            # Хедер уведомления (галочка + Уведомление без скобок)
            toast_path = asset_dir / "toast_header.png"
            if toast_path.exists():
                w, h, _, data = dpg.load_image(str(toast_path))
                dpg.add_static_texture(w, h, data, tag="ui_toast_header")

            # 16-кадровые плавные табы
            for page in ("home", "game", "multiplayer", "settings", "about"):
                for frame in range(16):
                    path = asset_dir / f"nav_{page}_{frame}.png"
                    if path.exists():
                        w, h, _, data = dpg.load_image(str(path))
                        dpg.add_static_texture(w, h, data, tag=f"ui_nav_{page}_{frame}")

            # Динамические карточки кораблей (зеленые/красные квадраты и фон)
            for path in asset_dir.glob("ship_card_*.png"):
                tag = f"ui_{path.stem}"
                if not dpg.does_item_exist(tag):
                    w, h, _, data = dpg.load_image(str(path))
                    dpg.add_static_texture(w, h, data, tag=tag)

            # Одиночные иконки
            for icon in ("boat", "home", "game", "multiplayer", "settings", "about", "rotate", "shuffle", "clear", "play", "check", "bot", "phone", "win", "despair"):
                for suffix in ("", "_accent"):
                    path = asset_dir / f"icon_{icon}{suffix}.png"
                    if path.exists():
                        w, h, _, data = dpg.load_image(str(path))
                        dpg.add_static_texture(w, h, data, tag=f"ui_icon_{icon}{suffix}")

            # Текстуры кнопок действий (обычные и с подсветкой при наведении)
            for btn_name in ("btn_rotate", "btn_clear", "btn_random", "btn_start"):
                for suffix in ("", "_hov"):
                    p = asset_dir / f"{btn_name}{suffix}.png"
                    if p.exists():
                        w, h, _, data = dpg.load_image(str(p))
                        dpg.add_static_texture(w, h, data, tag=f"ui_{btn_name}{suffix}")

            # Кадры анимации вращения ориентации корабля (штурвал 0..90 градусов)
            for f in range(7):
                p = asset_dir / f"orient_frame_{f}.png"
                if p.exists():
                    w, h, _, data = dpg.load_image(str(p))
                    dpg.add_static_texture(w, h, data, tag=f"ui_orient_frame_{f}")

        dpg.create_viewport(
            title="Sea Battle - Tactical ImGui Edition",
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
            width=300,
            height=68,
            pos=[16, 16]
        ):
            dpg.bind_item_theme("toast_window", "toast_theme")
            if dpg.does_item_exist("ui_toast_header"):
                dpg.add_image("ui_toast_header", width=180, height=20)
            else:
                dpg.add_text("Уведомление", color=(215, 225, 238))
            dpg.add_spacer(height=3)
            t_msg = dpg.add_text("", tag="toast_text", color=(255, 255, 255), wrap=272)
            if self.fonts and "toast" in self.fonts:
                dpg.bind_item_font(t_msg, self.fonts["toast"])
            elif self.fonts and "semibold" in self.fonts:
                dpg.bind_item_font(t_msg, self.fonts["semibold"])
            dpg.add_spacer(height=4)
            dpg.add_progress_bar(tag="toast_progress", default_value=1.0, width=272, height=2)
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

        self.show_page("home")

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
            dpg.set_item_pos("toast_window", [-310, 16])
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

        # Плавный слайд-ин слева: от -310 до 16
        TARGET_X = 16
        TARGET_Y = 16
        ANIM_IN = 0.16
        ANIM_OUT = 0.16

        if elapsed < ANIM_IN:
            factor = elapsed / ANIM_IN
            factor = 1.0 - (1.0 - factor) ** 2  # ease-out
            curr_x = int(-310 + (TARGET_X - (-310)) * factor)
        elif elapsed > self.toast_duration - ANIM_OUT:
            factor = (self.toast_duration - elapsed) / ANIM_OUT
            factor = max(0.0, factor)
            factor = 1.0 - (1.0 - factor) ** 2
            curr_x = int(-310 + (TARGET_X - (-310)) * factor)
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
        """Плавное вращение корабля-штурвала при смене ориентации."""
        if self.orient_anim is None:
            return
        start_f, end_f, started = self.orient_anim
        progress = min(1.0, (time.monotonic() - started) / 0.16)
        curr_f = int(round(start_f + (end_f - start_f) * progress))
        curr_f = max(0, min(6, curr_f))
        if dpg.does_item_exist("orient_widget_btn"):
            dpg.configure_item("orient_widget_btn", texture_tag=f"ui_orient_frame_{curr_f}")
        if progress >= 1.0:
            self.orient_anim = None

    def show_page(self, page):
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
            dpg.add_spacer(height=24, tag="page_top_spacer")
            builders[page]()

        self.page_transition = (page, time.monotonic())
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
        cell = max(26, min(50, (panel_width - 55) // self.size, (panel_height - 90) // (self.size + 1)))

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
        left_width = max(330, min(int(available * 0.53), available - 330))
        right_width = available - left_width - 10
        panel_height = max(550, self.view_height - 140)
        cell = max(26, min(56, (left_width - 60) // self.size, (panel_height - 90) // (self.size + 1)))

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

                # Правая панель: Выбор кораблей с SVG иконками boat.svg
                with dpg.child_window(width=right_width, height=panel_height, no_scrollbar=True, tag="placement_controls"):
                    dpg.bind_item_theme("placement_controls", "card_theme")
                    t_head = dpg.add_text("ВЫБОР КОРАБЛЯ", indent=10)
                    if self.fonts and "semibold" in self.fonts:
                        dpg.bind_item_font(t_head, self.fonts["semibold"])

                    dpg.add_spacer(height=8)

                    # Карточки выбора кораблей с индикацией (зеленые/красные квадраты и цветовой фон)
                    card_btn_w = min(300, right_width - 24)
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
                            indent=10,
                            callback=self.select_ship,
                            user_data=n,
                            tag=f"ship_btn_{n}",
                            background_color=(0, 0, 0, 0)
                        )
                        dpg.bind_item_theme(f"ship_btn_{n}", "ui_image_button")
                        dpg.add_spacer(height=4)

                    dpg.add_spacer(height=6)
                    dpg.add_separator()
                    dpg.add_spacer(height=8)

                    dpg.add_text("РАСПОЛОЖЕНИЕ", indent=10, color=(120, 130, 145))
                    dpg.add_spacer(height=4)
                    with dpg.group(horizontal=True, indent=10):
                        init_f = 0 if self.orientation == "H" else 6
                        b_orient_ship = dpg.add_image_button(
                            f"ui_orient_frame_{init_f}",
                            width=50,
                            height=50,
                            frame_padding=0,
                            callback=self.rotate,
                            tag="orient_widget_btn",
                            background_color=(0, 0, 0, 0)
                        )
                        dpg.bind_item_theme(b_orient_ship, "ui_image_button")
                        with dpg.group():
                            dpg.add_spacer(height=4)
                            t_orient = dpg.add_text(
                                "Горизонтальное" if self.orientation == "H" else "Вертикальное",
                                tag="orientation_text",
                                color=(255, 255, 255)
                            )
                            if self.fonts and "semibold" in self.fonts:
                                dpg.bind_item_font(t_orient, self.fonts["semibold"])
                            dpg.add_text("Кликните для поворота на 90° (R)", color=(110, 120, 135))

                    dpg.add_spacer(height=8)

                    # Повернуть и Очистить со скругленными углами
                    with dpg.group(horizontal=True, indent=10):
                        if dpg.does_item_exist("ui_btn_rotate"):
                            b_rot = dpg.add_image_button("ui_btn_rotate", width=(card_btn_w - 10) // 2, height=36, frame_padding=0, callback=self.rotate, tag="placement_b_rot")
                        else:
                            b_rot = dpg.add_button(label="Повернуть (R)", width=(card_btn_w - 10) // 2, height=36, callback=self.rotate, tag="placement_b_rot")
                        dpg.bind_item_theme(b_rot, "ui_image_button")

                        if dpg.does_item_exist("ui_btn_clear"):
                            b_clr = dpg.add_image_button("ui_btn_clear", width=(card_btn_w - 10) // 2, height=36, frame_padding=0, callback=self.clear_placement, tag="placement_b_clr")
                        else:
                            b_clr = dpg.add_button(label="Очистить", width=(card_btn_w - 10) // 2, height=36, callback=self.clear_placement, tag="placement_b_clr")
                        dpg.bind_item_theme(b_clr, "ui_image_button")

                    dpg.add_spacer(height=8)

                    # Случайная расстановка
                    if dpg.does_item_exist("ui_btn_random"):
                        b_rnd = dpg.add_image_button("ui_btn_random", width=card_btn_w, height=36, frame_padding=0, indent=10, callback=self.auto_place, tag="placement_b_rnd")
                    else:
                        b_rnd = dpg.add_button(label="Случайная расстановка", width=card_btn_w, height=36, indent=10, callback=self.auto_place, tag="placement_b_rnd")
                    dpg.bind_item_theme(b_rnd, "ui_image_button")

                    dpg.add_spacer(height=12)

                    # Кнопка Начать бой
                    if dpg.does_item_exist("ui_btn_start"):
                        b_start = dpg.add_image_button("ui_btn_start", width=card_btn_w, height=42, frame_padding=0, indent=10, callback=self.start_battle, tag="start_button")
                    else:
                        b_start = dpg.add_button(label="Начать бой", width=card_btn_w, height=42, indent=10, callback=self.start_battle, tag="start_button")
                    dpg.bind_item_theme(b_start, "ui_image_button")

                    dpg.add_spacer(height=6)
                    dpg.add_text("", tag="placement_status_msg", indent=10, wrap=card_btn_w)

    def _page_multiplayer(self):
        panel_w = min(780, self.view_width - self.sidebar_width - 45)
        panel_h = max(520, self.view_height - 150)
        col_left_w = max(340, panel_w - 280)
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
                        st_text = dpg.add_text(
                            "Ожидание подключения..." if self.relay.is_connected else "Комната не запущена",
                            tag="network_status",
                            color=(255, 255, 255) if self.relay.is_connected else (140, 150, 168)
                        )
                        if self.fonts and "semibold" in self.fonts:
                            dpg.bind_item_font(st_text, self.fonts["semibold"])

                        dpg.add_spacer(height=12)
                        dpg.add_separator()
                        dpg.add_spacer(height=10)

                        dpg.add_text("ИНСТРУКЦИЯ ПО ПОДКЛЮЧЕНИЮ:", color=(120, 130, 145))
                        dpg.add_spacer(height=4)
                        dpg.add_text("1. Нажмите «Создать комнату»", color=(200, 210, 225))
                        dpg.add_text("2. Отсканируйте QR-код камерой смартфона", color=(200, 210, 225))
                        dpg.add_text("3. На смартфоне расставьте флот и нажмите «Готов»", color=(200, 210, 225))
                        dpg.add_text("4. На ПК расставьте корабли и начните бой!", color=(200, 210, 225))

                        dpg.add_spacer(height=16)
                        with dpg.group(horizontal=True):
                            b_create = dpg.add_button(label="Создать комнату", width=160, height=36, callback=self.create_room)
                            dpg.bind_item_theme(b_create, "primary_button")
                            b_copy = dpg.add_button(label="Копировать ссылку", width=160, height=36, callback=self.copy_room_link)
                            dpg.bind_item_theme(b_copy, "secondary_button")

                        dpg.add_spacer(height=8)
                        with dpg.group(horizontal=True):
                            b_place = dpg.add_button(label="Расставить флот на ПК", width=200, height=36, callback=self.go_to_placement)
                            dpg.bind_item_theme(b_place, "primary_button")
                            b_stop = dpg.add_button(label="Остановить", width=120, height=36, callback=self.stop_room)
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
        card_w = min(740, self.view_width - self.sidebar_width - 45)
        with dpg.group(tag="page_about", show=True):
            self._title("О проекте", "Школьный индивидуальный проект по информатике")
            with dpg.child_window(width=card_w, height=self.view_height - 150, no_scrollbar=True):
                dpg.bind_item_theme(dpg.last_item(), "card_theme")
                dpg.add_spacer(height=10)
                t = dpg.add_text("ПАСПОРТ ПРОЕКТА: «МОРСКОЙ БОЙ»", color=(255, 255, 255), indent=16)
                if self.fonts and "semibold" in self.fonts:
                    dpg.bind_item_font(t, self.fonts["semibold"])
                dpg.add_spacer(height=4)
                dpg.add_separator()
                dpg.add_spacer(height=8)

                dpg.add_text("Цель работы:", color=(100, 110, 128), indent=16)
                dpg.add_text("Разработка настольного приложения морского боя с искусственным интеллектом и кроссплатформенным мультиплеером ПК ↔ Смартфон без выделенного сервера.", wrap=card_w - 32, indent=16)
                dpg.add_spacer(height=8)

                dpg.add_text("Использованные технологии:", color=(100, 110, 128), indent=16)
                dpg.add_text("• Интерфейс: Python + Dear PyGui (пользовательская темная тема в стиле Dear ImGui Aternos)\n• Искусственный интеллект: алгоритм Hunt & Target (поиск по шахматной четности + добивание)\n• Сетевой протокол: MQTT v5 поверх WebSockets (HiveMQ / EMQX)\n• Мобильный клиент: HTML5 Canvas + Vanilla JS\n• Тестирование: автоматические тесты pytest", indent=16)
                dpg.add_spacer(height=8)

                dpg.add_text("Правила игры:", color=(100, 110, 128), indent=16)
                dpg.add_text("Классические правила: корабли не соприкасаются сторонами и углами (диагоналями). При попадании ход сохраняется. Побеждает игрок, первым потопивший все корабли соперника.", wrap=card_w - 32, indent=16)

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
                self.player.remove_ship_at(r, c)
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

    def rotate(self, *args):
        old_orient = self.orientation
        self.orientation = "V" if self.orientation == "H" else "H"
        orient_name = "Вертикальное" if self.orientation == "V" else "Горизонтальное"
        start_f = 0 if old_orient == "H" else 6
        end_f = 6 if self.orientation == "V" else 0
        self.orient_anim = (start_f, end_f, time.monotonic())
        if dpg.does_item_exist("orientation_text"):
            dpg.set_value("orientation_text", orient_name)
        self.notify(f"Расположение: {orient_name}", duration=1.2)

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
                    dpg.bind_item_theme(tag, "cell_ship_crosshair" if b_th == "cell_ship" else "cell_water_crosshair")
            # Линия столбца от верхнего заголовка до курсора
            for ri in range(r):
                tag = f"{prefix}_{ri}_{c}"
                if dpg.does_item_exist(tag):
                    b_th = self._get_cell_base_theme(prefix, ri, c)
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
            import subprocess
            subprocess.run(["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value '{url}'"], check=True)
            self.notify("Ссылка скопирована в буфер обмена!")
        except Exception:
            self.notify(f"Ссылка: {url}")

    def go_to_placement(self):
        self.mode = "multiplayer"
        self.new_game()
        self.show_page("placement")

    def create_room(self):
        self.mode = "multiplayer"
        self.relay.start()
        dpg.set_value("room_code", self.relay.room_code)
        dpg.set_value("join_url", self.relay.get_join_url())
        dpg.set_value("network_status", "Подключение к брокеру...")
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
        self.notify(f"Комната создана: {self.relay.room_code}")

    def stop_room(self):
        self.relay.stop()
        if dpg.does_item_exist("room_code"):
            dpg.set_value("room_code", "— — — — —")
        if dpg.does_item_exist("network_status"):
            dpg.set_value("network_status", "Комната остановлена")
        if dpg.does_item_exist("join_url"):
            dpg.set_value("join_url", "")
        if dpg.does_item_exist("qr_container"):
            dpg.delete_item("qr_container", children_only=True)
            with dpg.child_window(width=230, height=230, border=True, no_scrollbar=True, parent="qr_container"):
                dpg.add_spacer(height=95)
                dpg.add_text("Нажмите\n«Создать комнату»", color=(120, 130, 145), indent=45)
        self.notify("Комната остановлена")

    def _process_events(self):
        if self.relay.is_connected and dpg.does_item_exist("network_status") and dpg.get_value("network_status") == "Подключение к брокеру...":
            dpg.set_value("network_status", "Комната готова. Ожидание подключения смартфона...")
        try:
            while True:
                action, data = self.events.get_nowait()
                if action == "phone_connected":
                    dpg.set_value("network_status", "Телефон подключен")
                    self.notify("Телефон подключен!")
                elif action == "phone_ready":
                    self.phone_ready = True
                    dpg.set_value("network_status", "Телефон готов. Расставьте флот и нажмите «Начать бой»")
                    self.notify("Телефон готов к бою!")
                elif action == "phone_shot" and self.phase == "battle":
                    if self.turn not in ("phone", "waiting"):
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
            self.show_page(self.current_page)


if __name__ == "__main__":
    SeaBattleApp().build()
