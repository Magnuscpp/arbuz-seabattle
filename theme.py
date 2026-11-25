"""Минималистичная монохромная тема (белый, серый, черный).
Палитра: глубокий черный фон, графитовый сайдбар, угольные виджеты,
высококонтрастный белый акцент #FFFFFF без разноцветных градиентов.
"""
from pathlib import Path
import dearpygui.dearpygui as dpg

# Монохромные базовые цвета (белый / серый / черный)
BG = (10, 10, 11, 255)                  # #0A0A0B глубокий черный фон окна
SIDEBAR = (13, 14, 16, 255)             # #0D0E10 графитовый сайдбар
PANEL = (17, 18, 20, 255)               # #111214 темная панель / фон карточек
WIDGET = (24, 26, 30, 255)              # #181A1E базовый фон виджетов и инпутов
WIDGET_HOVER = (34, 38, 44, 255)        # фон при наведении
WIDGET_ACTIVE = (45, 50, 58, 255)       # фон при клике
STROKE = (34, 37, 44, 255)              # #22252C тонкая нейтральная рамка
WIDGET_STROKE = (42, 46, 54, 255)       # #2A2E36 рамка виджетов

# Акцент - чистый минималистичный белый
ACCENT = (255, 255, 255, 255)           # Чистый белый акцент вместо фиолетового
ACCENT_HOVER = (235, 238, 242, 255)
ACCENT_ACTIVE = (210, 215, 222, 255)
ACCENT_MUTED = (160, 168, 182, 255)

TEXT_ACTIVE = (255, 255, 255, 255)      # Белый контрастный текст
TEXT_HOV = (195, 202, 212, 255)         # Светло-серый
TEXT_MUTED = (115, 125, 140, 255)       # Нейтральный серый


def create_themes():
    # 1. Глобальная тема приложения
    with dpg.theme(tag="theme_global"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, BG)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, TEXT_MUTED)
            dpg.add_theme_color(dpg.mvThemeCol_Border, STROKE)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, WIDGET)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, WIDGET_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, WIDGET_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_Button, WIDGET)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, WIDGET_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, WIDGET_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_Header, WIDGET)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, WIDGET_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (45, 50, 58, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (18, 20, 26, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (24, 28, 36, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgCollapsed, (18, 20, 26, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ModalWindowDimBg, (0, 0, 0, 160))
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (255, 255, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (220, 224, 230, 255))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (255, 255, 255, 255))
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 10, 10)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 0)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, (0, 0, 0, 0))

    # 2. Боковая панель сайдбара
    with dpg.theme(tag="sidebar_theme"):
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, SIDEBAR)
            dpg.add_theme_color(dpg.mvThemeCol_Border, STROKE)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 8, 10)

    # 3. Кнопка с изображением таба (без рамок и фона)
    with dpg.theme(tag="ui_image_button"):
        with dpg.theme_component(dpg.mvImageButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (0, 0, 0, 0))
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)

    # 4. Основная кнопка действия (Minimalist White Primary Button)
    with dpg.theme(tag="primary_button"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (245, 245, 247, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (220, 222, 228, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (14, 15, 18, 255))  # глубокий черный контрастный текст
            dpg.add_theme_color(dpg.mvThemeCol_Border, (255, 255, 255, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 12, 9)
        with dpg.theme_component(dpg.mvImageButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (245, 245, 247, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (220, 222, 228, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (255, 255, 255, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)

    # 5. Вторичная кнопка (Графитовая с белым текстом)
    with dpg.theme(tag="secondary_button"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, WIDGET)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, WIDGET_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, WIDGET_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_Border, WIDGET_STROKE)
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_ACTIVE)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 8)
        with dpg.theme_component(dpg.mvImageButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, WIDGET)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, WIDGET_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, WIDGET_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_Border, WIDGET_STROKE)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)

    # 6. Кнопка сброса / опасности
    with dpg.theme(tag="danger_button"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (35, 18, 24, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (48, 22, 30, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (60, 26, 36, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (120, 35, 45, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (248, 113, 113, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 8)
        with dpg.theme_component(dpg.mvImageButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (35, 18, 24, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (48, 22, 30, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (60, 26, 36, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (120, 35, 45, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)

    # 7. Выбор корабля (Выбран)
    with dpg.theme(tag="ship_selected_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (34, 38, 46, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (44, 48, 58, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (28, 32, 40, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (255, 255, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 2)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 8)

    # 8. Выбор корабля (Не выбран)
    with dpg.theme(tag="ship_unselected_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, WIDGET)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, WIDGET_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, WIDGET_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_Border, WIDGET_STROKE)
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_HOV)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 8)

    # 9. Сетка игрового поля
    with dpg.theme(tag="board_grid"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 2, 2)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)

    # Координаты (А-К, 1-10) обычное состояние
    with dpg.theme(tag="cell_coord"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (115, 125, 140, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)

    # Координаты (А-К, 1-10) подсвеченные при наведении на клетку
    with dpg.theme(tag="cell_coord_highlight"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (55, 68, 92, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (55, 68, 92, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (55, 68, 92, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (140, 165, 205, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)

    # Клетки игрового поля (монохромная тактическая гамма с яркой подсветкой лучей координат)
    cells = {
        # Вода: глубокий темный графит
        "cell_water":           (WIDGET, (60, 75, 100, 255), (44, 50, 60, 255), (90, 100, 115, 255)),
        # Вода по линии луча при наведении курсора (явно беловатые блоки)
        "cell_water_crosshair": ((46, 56, 74, 255), (65, 80, 108, 255), (75, 90, 120, 255), (255, 255, 255, 255)),
        # Целевая клетка прямо под курсором (акцентная подсветка)
        "cell_target":          ((60, 75, 100, 255), (70, 88, 118, 255), (80, 100, 130, 255), (255, 255, 255, 255)),
        # Корабль: стальной графитовый корпус с четким белым контуром
        "cell_ship":            ((50, 56, 68, 255), (66, 74, 88, 255), (42, 48, 58, 255), (255, 255, 255, 255)),
        # Корабль по перекрестию при наведении
        "cell_ship_crosshair":  ((68, 78, 96, 255), (85, 96, 118, 255), (50, 58, 70, 255), (255, 255, 255, 255)),
        # Промах: темный фон с аккуратной точкой
        "cell_miss":            ((16, 17, 20, 255), (22, 24, 28, 255), (28, 30, 36, 255), (105, 115, 130, 255)),
        # Попадание: яркий контрастный янтарный (боевое состояние попадания)
        "cell_hit":             ((234, 88, 12, 255), (249, 115, 22, 255), (194, 65, 12, 255), (255, 255, 255, 255)),
        # Потоплен: глубокий рубиново-красный
        "cell_sunk":            ((220, 38, 38, 255), (239, 68, 68, 255), (185, 28, 28, 255), (255, 255, 255, 255)),
    }

    for name, (bg_col, hov_col, act_col, txt_col) in cells.items():
        with dpg.theme(tag=name):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, bg_col)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, hov_col)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, act_col)
                border_col = (255, 255, 255, 255) if (name in ("cell_target", "cell_ship", "cell_ship_crosshair")) else ((115, 135, 168, 255) if name == "cell_water_crosshair" else WIDGET_STROKE)
                dpg.add_theme_color(dpg.mvThemeCol_Border, border_col)
                dpg.add_theme_color(dpg.mvThemeCol_Text, txt_col)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 3)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)

    # Карточки и контейнеры
    with dpg.theme(tag="card_theme"):
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_Border, STROKE)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 14, 12)
        with dpg.theme_component(dpg.mvWindowAppItem):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_Border, STROKE)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (18, 20, 26, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (24, 28, 36, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgCollapsed, (18, 20, 26, 255))
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 1)

    # Всплывающее уведомление (Toast / notificationSystem прямоугольник)
    with dpg.theme(tag="toast_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (16, 17, 20, 248))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (55, 60, 72, 255))
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 14, 8)

    # Прогресс-бар уведомления
    with dpg.theme(tag="toast_progress_theme"):
        with dpg.theme_component(dpg.mvProgressBar):
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, (240, 243, 248, 220))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (32, 35, 42, 180))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 1)

    # Тема плотного и равномерного расстояния (4px) для кнопок действий расстановки
    with dpg.theme(tag="placement_actions_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)

    # Карточка со скроллбаром для длинной документации во вкладке «О проекте»
    with dpg.theme(tag="about_card_theme"):
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_Border, STROKE)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, (14, 15, 18, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, (55, 62, 74, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, (85, 95, 112, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, (120, 132, 152, 255))
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 16, 14)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarRounding, 4)


def load_fonts():
    """Загрузка плотных и четких шрифтов Segoe UI Semibold для легко читаемой кириллицы."""
    semibold_path = Path("C:/Windows/Fonts/seguisb.ttf")
    bold_path = Path("C:/Windows/Fonts/segoeuib.ttf")
    regular_path = Path("C:/Windows/Fonts/segoeui.ttf")

    font_base = semibold_path if semibold_path.exists() else regular_path
    font_bold = bold_path if bold_path.exists() else font_base

    if not font_base.exists():
        return {}

    with dpg.font_registry():
        dpg.add_font(str(font_base), 16, tag="font_regular")
        dpg.add_font(str(font_base), 17, tag="font_semibold")
        dpg.add_font(str(font_base), 18, tag="font_control")
        dpg.add_font(str(font_bold), 22, tag="font_title")
        dpg.add_font(str(font_base), 14, tag="font_badge")
        dpg.add_font(str(font_bold), 17, tag="font_toast")

        calibri_reg = Path("C:/Windows/Fonts/calibri.ttf")
        calibri_bold = Path("C:/Windows/Fonts/calibrib.ttf")
        consola_reg = Path("C:/Windows/Fonts/consola.ttf")

        about_reg_path = calibri_reg if calibri_reg.exists() else font_base
        about_bold_path = calibri_bold if calibri_bold.exists() else about_reg_path
        about_mono_path = consola_reg if consola_reg.exists() else about_reg_path

        dpg.add_font(str(about_reg_path), 16, tag="font_about")
        dpg.add_font(str(about_bold_path), 18, tag="font_about_bold")
        dpg.add_font(str(about_mono_path), 14, tag="font_about_mono")

    return {
        "regular": "font_regular",
        "semibold": "font_semibold",
        "control": "font_control",
        "title": "font_title",
        "badge": "font_badge",
        "toast": "font_toast",
        "about": "font_about",
        "about_bold": "font_about_bold",
        "about_mono": "font_about_mono",
    }
