"""Генератор графических ассетов в минималистичном монохромном стиле (белый, серый, черный).
Создает:
1. Векторные SVG-иконки и растровые PNG с белыми и серыми акцентами
2. Идеально выровненный бренд-хедер сайдбара (205x48) с boat.svg
3. 200px вкладки бокового меню с 16-кадровой интерполяцией (плавная смена состояний)
4. Карточки выбора кораблей с векторной иконкой boat.svg и белой подсветкой выбранного
"""
import re
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from svgpath2mpl import parse_path

ROOT = Path(__file__).resolve().parent / "assets" / "ui"
ROOT.mkdir(parents=True, exist_ok=True)

# Монохромная палитра (черный, графит, серый, белый)
BG_DARK = (10, 10, 11)             # глубокий черный
SIDEBAR_BG = (13, 14, 16)          # графит
TAB_ACTIVE = (26, 29, 36)          # активный таб
STROKE = (34, 37, 44)              # нейтральная рамка
ELEMENT_BG = (17, 18, 20)          # фон карточек
WIDGET_BG = (22, 24, 28)           # фон виджетов
WIDGET_STROKE = (42, 46, 54)       # рамка виджетов
ACCENT = (255, 255, 255)           # чистый белый акцент

TEXT_ACTIVE = (255, 255, 255)
TEXT_HOV = (195, 202, 212)
TEXT_MUTED = (115, 125, 140)
TEXT_SUBTITLE = (135, 145, 160)

BOAT_SVG_PATH = "M4 17.5L3 12L12 9L21 12L20 17.5M5 11.3333V7C5 5.89543 5.89543 5 7 5H17C18.1046 5 19 5.89543 19 7V11.3333M10 5V3C10 2.44772 10.4477 2 11 2H13C13.5523 2 14 2.44772 14 3V5M2 21C3 22 6 22 8 20C10 22 14 22 16 20C18 22 21 22 22 21"

ICONS_SVG = {
    "boat": f'<path d="{BOAT_SVG_PATH}"/>',
    "home": '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    "game": '<circle cx="12" cy="12" r="10"/><line x1="22" y1="12" x2="18" y2="12"/><line x1="6" y1="12" x2="2" y2="12"/><line x1="12" y1="6" x2="12" y2="2"/><line x1="12" y1="22" x2="12" y2="18"/>',
    "multiplayer": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "settings": '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
    "about": '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
    "rotate": '<path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.85.83 6.72 2.24L21 8"/><polyline points="21 3 21 8 16 8"/>',
    "shuffle": '<polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/>',
    "clear": '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    "play": '<polygon points="5 3 19 12 5 21 5 3"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "bot": '<rect x="4" y="4" width="16" height="16" rx="3"/><rect x="9" y="9" width="6" height="6" rx="1"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/>',
    "phone": '<rect x="5" y="2" width="14" height="20" rx="3"/><line x1="12" y1="18" x2="12.01" y2="18"/>',
}

def render_svg_to_image(svg_markup, size=24, color="#FFFFFF", stroke_width=2.0):
    fig = plt.figure(figsize=(2.4, 2.4), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    ax.set_xlim(0, 24)
    ax.set_ylim(24, 0)
    ax.axis('off')

    # Convert stroke width in SVG units to points for 240x240 canvas
    lw_pts = stroke_width * (240.0 / 24.0) * (72.0 / 100.0)

    # Path
    for m in re.finditer(r'<path\s+[^>]*d="([^"]+)"', svg_markup):
        d_str = m.group(1)
        mpl_path = parse_path(d_str)
        p = patches.PathPatch(mpl_path, facecolor='none', edgecolor=color, lw=lw_pts, capstyle='round', joinstyle='round')
        ax.add_patch(p)

    # Circles
    for m in re.finditer(r'<circle\s+cx="([^"]+)"\s+cy="([^"]+)"\s+r="([^"]+)"', svg_markup):
        cx, cy, r = float(m.group(1)), float(m.group(2)), float(m.group(3))
        c = patches.Circle((cx, cy), r, facecolor='none', edgecolor=color, lw=lw_pts)
        ax.add_patch(c)

    # Lines
    for m in re.finditer(r'<line\s+x1="([^"]+)"\s+y1="([^"]+)"\s+x2="([^"]+)"\s+y2="([^"]+)"', svg_markup):
        x1, y1, x2, y2 = float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))
        l = patches.ConnectionPatch((x1, y1), (x2, y2), "data", "data", edgecolor=color, lw=lw_pts, capstyle='round')
        ax.add_patch(l)

    # Polylines
    for m in re.finditer(r'<polyline\s+points="([^"]+)"', svg_markup):
        pts_str = m.group(1).strip().split()
        poly_pts = []
        for p_pair in pts_str:
            if ',' in p_pair:
                px, py = map(float, p_pair.split(','))
            else:
                poly_pts.append(float(p_pair))
        if poly_pts and not isinstance(poly_pts[0], tuple):
            poly_pts = list(zip(poly_pts[0::2], poly_pts[1::2]))
        p = patches.Polygon(poly_pts, facecolor='none', edgecolor=color, lw=lw_pts, closed=False)
        ax.add_patch(p)

    # Polygons
    for m in re.finditer(r'<polygon\s+points="([^"]+)"', svg_markup):
        pts_str = m.group(1).strip().split()
        poly_pts = []
        for p_pair in pts_str:
            if ',' in p_pair:
                px, py = map(float, p_pair.split(','))
            else:
                poly_pts.append(float(p_pair))
        if poly_pts and not isinstance(poly_pts[0], tuple):
            poly_pts = list(zip(poly_pts[0::2], poly_pts[1::2]))
        p = patches.Polygon(poly_pts, facecolor='none', edgecolor=color, lw=lw_pts, closed=True)
        ax.add_patch(p)

    # Rectangles
    for m in re.finditer(r'<rect\s+([^>]+)/>', svg_markup):
        attrs = dict(re.findall(r'(\w+)="([^"]+)"', m.group(1)))
        x, y, w, h = float(attrs['x']), float(attrs['y']), float(attrs['width']), float(attrs['height'])
        r = patches.Rectangle((x, y), w, h, facecolor='none', edgecolor=color, lw=lw_pts)
        ax.add_patch(r)

    buf = BytesIO()
    plt.savefig(buf, format='png', transparent=True, dpi=100)
    plt.close(fig)
    buf.seek(0)
    im = Image.open(buf).convert("RGBA")
    return im.resize((size, size), Image.Resampling.LANCZOS)

def render_arbitrary_svg(svg_path, size=24, color="#FFFFFF", filled=None, stroke_width=None):
    with open(svg_path, "r", encoding="utf-8") as f:
        svg_text = f.read()

    vb_m = re.search(r'viewBox="([^"]+)"', svg_text)
    if vb_m:
        parts = [float(x) for x in vb_m.group(1).split()]
        vx, vy, vw, vh = parts[0], parts[1], parts[2], parts[3]
    else:
        vx, vy, vw, vh = 0, 0, 32, 32

    # High-resolution supersampling: 256x256 canvas
    fig = plt.figure(figsize=(2.56, 2.56), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    ax.set_xlim(vx, vx + vw)
    ax.set_ylim(vy + vh, vy)
    ax.axis('off')

    scale_pts = (256.0 / max(vw, vh)) * (72.0 / 100.0)

    for m in re.finditer(r'<path\b([^>]*)\bd="([^"]+)"', svg_text):
        attrs, d_str = m.group(1), m.group(2)
        mpl_path = parse_path(d_str)
        has_fill = ('fill="#' in attrs or 'fill="black"' in attrs or 'fill="none"' not in attrs)
        use_fill = filled if filled is not None else has_fill

        if use_fill:
            p = patches.PathPatch(mpl_path, facecolor=color, edgecolor='none')
        else:
            lw_units = stroke_width if stroke_width else (vw / 16.0)
            lw = lw_units * scale_pts
            p = patches.PathPatch(mpl_path, facecolor='none', edgecolor=color, lw=lw, capstyle='round', joinstyle='round')
        ax.add_patch(p)

    buf = BytesIO()
    plt.savefig(buf, format='png', transparent=True, dpi=100)
    plt.close(fig)
    buf.seek(0)
    im = Image.open(buf).convert('RGBA')
    return im.resize((size, size), Image.Resampling.LANCZOS)

def render_deck_hires(svg_path, sz):
    txt = Path(svg_path).read_text(encoding='utf-8')
    vm = re.search(r'viewBox="([0-9\.\s\-]+)"', txt)
    vx, vy, vw, vh = [float(x) for x in vm.group(1).split()] if vm else (0, 0, 24, 24 * sz)

    lw_scale = 7.2

    fig = plt.figure(figsize=(2.4, 2.4 * (vh / vw)), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    ax.set_xlim(vx, vx + vw)
    ax.set_ylim(vy + vh, vy)
    ax.axis('off')

    for m in re.finditer(r'<path\b([^>]*)\bd="([^"]+)"', txt):
        attrs, d = m.group(1), m.group(2)
        fill = '#FFFFFF' if ('fill="#FFFFFF"' in attrs or 'fill="white"' in attrs) else 'none'
        edge = '#FFFFFF' if ('stroke="#FFFFFF"' in attrs or 'stroke="white"' in attrs or 'stroke=' in attrs) else 'none'
        sw_m = re.search(r'stroke-width="([^"]+)"', attrs)
        sw = float(sw_m.group(1)) if sw_m else 2.0
        ax.add_patch(patches.PathPatch(parse_path(d), facecolor=fill, edgecolor=edge, lw=sw * lw_scale, capstyle='round', joinstyle='round'))

    for m in re.finditer(r'<line\b([^>]+)', txt):
        attrs = m.group(1)
        x1 = float(re.search(r'x1="([^"]+)"', attrs).group(1))
        y1 = float(re.search(r'y1="([^"]+)"', attrs).group(1))
        x2 = float(re.search(r'x2="([^"]+)"', attrs).group(1))
        y2 = float(re.search(r'y2="([^"]+)"', attrs).group(1))
        sw_m = re.search(r'stroke-width="([^"]+)"', attrs)
        sw = float(sw_m.group(1)) if sw_m else 1.5
        ls = '--' if 'stroke-dasharray' in attrs else '-'
        ax.plot([x1, x2], [y1, y2], color='#FFFFFF', lw=sw * lw_scale, linestyle=ls, solid_capstyle='round')

    for m in re.finditer(r'<circle\b([^>]+)', txt):
        attrs = m.group(1)
        cx = float(re.search(r'cx="([^"]+)"', attrs).group(1))
        cy = float(re.search(r'cy="([^"]+)"', attrs).group(1))
        r = float(re.search(r'r="([^"]+)"', attrs).group(1))
        fill = '#FFFFFF' if ('fill="#FFFFFF"' in attrs or 'fill="white"' in attrs) else 'none'
        edge = '#FFFFFF' if ('stroke="#FFFFFF"' in attrs or 'stroke="white"' in attrs or 'stroke=' in attrs) else 'none'
        sw_m = re.search(r'stroke-width="([^"]+)"', attrs)
        sw = float(sw_m.group(1)) if sw_m else 1.8
        ax.add_patch(patches.Circle((cx, cy), r, facecolor=fill, edgecolor=edge, lw=sw * lw_scale))

    for m in re.finditer(r'<rect\b([^>]+)', txt):
        attrs = m.group(1)
        x = float(re.search(r'x="([^"]+)"', attrs).group(1))
        y = float(re.search(r'y="([^"]+)"', attrs).group(1))
        w = float(re.search(r'width="([^"]+)"', attrs).group(1))
        h = float(re.search(r'height="([^"]+)"', attrs).group(1))
        fill = '#FFFFFF' if ('fill="#FFFFFF"' in attrs or 'fill="white"' in attrs) else 'none'
        edge = '#FFFFFF' if ('stroke="#FFFFFF"' in attrs or 'stroke="white"' in attrs or 'stroke=' in attrs) else 'none'
        sw_m = re.search(r'stroke-width="([^"]+)"', attrs)
        sw = float(sw_m.group(1)) if sw_m else 1.6
        ax.add_patch(patches.Rectangle((x, y), w, h, facecolor=fill, edgecolor=edge, lw=sw * lw_scale))

    buf = BytesIO()
    plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0.01, dpi=100)
    plt.close(fig)
    buf.seek(0)
    im = Image.open(buf).convert('RGBA')
    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im

def render_tight_svg(svg_path, target_h=14, color="#FFFFFF", filled=None, stroke_width=None, base_size=64):
    raw = render_arbitrary_svg(svg_path, size=base_size, color=color, filled=filled, stroke_width=stroke_width)
    bbox = raw.getbbox()
    if bbox:
        cropped = raw.crop(bbox)
        aspect = cropped.width / cropped.height
        target_w = max(1, int(round(target_h * aspect)))
        return cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)
    return raw.resize((target_h, target_h), Image.Resampling.LANCZOS)

def build_assets():
    # Надежные шрифты Windows Segoe UI Semibold для четкой и плотной кириллицы
    font_bold_path = Path("C:/Windows/Fonts/seguisb.ttf")
    font_reg_path = Path("C:/Windows/Fonts/segoeui.ttf")
    font_header_path = Path("C:/Windows/Fonts/segoeuib.ttf")

    font_header = ImageFont.truetype(str(font_header_path), 17) if font_header_path.exists() else ImageFont.load_default()
    font_bold = ImageFont.truetype(str(font_bold_path), 15) if font_bold_path.exists() else ImageFont.load_default()
    font_reg = ImageFont.truetype(str(font_reg_path), 11) if font_reg_path.exists() else ImageFont.load_default()
    font_sub = ImageFont.truetype(str(font_reg_path), 10) if font_reg_path.exists() else ImageFont.load_default()

    # 1. Сохранение векторных SVG и одиночных иконок (белый/серый)
    for name, content in ICONS_SVG.items():
        svg_full = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">\n  {content}\n</svg>'
        (ROOT / f"{name}.svg").write_text(svg_full, encoding="utf-8")
        
        # Акцентная иконка (#FFFFFF чистый белый)
        icon_accent = render_svg_to_image(content, size=24, color="#FFFFFF")
        icon_accent.save(ROOT / f"icon_{name}_accent.png")
        
        # Приглушенная иконка (#6B7280 нейтральный серый)
        icon_muted = render_svg_to_image(content, size=24, color="#6B7280")
        icon_muted.save(ROOT / f"icon_{name}.png")

    # 2. Идеально выровненный бренд-хедер сайдбара (205x48) с белым boat.svg
    boat_glyph = render_svg_to_image(ICONS_SVG["boat"], size=24, color="#FFFFFF", stroke_width=2.2)
    brand_im = Image.new("RGBA", (205, 48), (0, 0, 0, 0))
    # Иконка корабля слева (x=8, y=11)
    brand_im.alpha_composite(boat_glyph, (8, 11))
    d_brand = ImageDraw.Draw(brand_im)
    # Название SEA BATTLE идеально по одной линии с иконкой
    d_brand.text((38, 9), "SEA BATTLE", font=font_header, fill=(255, 255, 255, 255))
    d_brand.text((38, 29), "TACTICAL IMGUI EDITION", font=font_sub, fill=(130, 140, 155, 255))
    brand_im.save(ROOT / "brand_header.png")

    # 2b. Идеально выровненный хедер уведомления (180x20) с белой галочкой и надписью «Уведомление» без скобок
    chk_glyph = render_svg_to_image(ICONS_SVG["check"], size=16, color="#FFFFFF", stroke_width=2.2)
    toast_h_im = Image.new("RGBA", (180, 20), (0, 0, 0, 0))
    toast_h_im.alpha_composite(chk_glyph, (0, 2))
    d_th = ImageDraw.Draw(toast_h_im)
    d_th.text((22, 10), "Уведомление", font=font_bold, fill=(215, 225, 238, 255), anchor="lm")
    toast_h_im.save(ROOT / "toast_header.png")

    # 3. Табы бокового меню шириной 200px (монохромный стиль)
    tabs = [
        ("home", "Главная", "Быстрый старт"),
        ("game", "Морской бой", "Одиночный бой"),
        ("multiplayer", "Мультиплеер", "Онлайн по QR"),
        ("settings", "Настройки", "Параметры игры"),
        ("about", "О проекте", "Паспорт проекта"),
    ]

    NUM_FRAMES = 16
    TAB_WIDTH = 200
    TAB_HEIGHT = 50

    for name, title, desc in tabs:
        svg_content = ICONS_SVG[name]
        
        # Состояние 0: Неактивно (серые тона)
        im_inactive = Image.new("RGBA", (TAB_WIDTH, TAB_HEIGHT), (0, 0, 0, 0))
        d_in = ImageDraw.Draw(im_inactive)
        glyph_in = render_svg_to_image(svg_content, size=22, color="#6B7280")
        im_inactive.alpha_composite(glyph_in, (12, 14))
        d_in.text((44, 11), title, font=font_bold, fill=(160, 170, 185, 255), anchor="lt")
        d_in.text((44, 28), desc, font=font_reg, fill=(95, 105, 120, 255), anchor="lt")

        # Состояние 1: Активно (Фон TAB_ACTIVE (26, 29, 36) на ВСЮ ширину 200px, белый акцент)
        im_active = Image.new("RGBA", (TAB_WIDTH, TAB_HEIGHT), (0, 0, 0, 0))
        d_act = ImageDraw.Draw(im_active)
        # Фон со скруглением 4px на ВСЮ ширину (сплошной и плотный графит)
        d_act.rounded_rectangle((0, 0, TAB_WIDTH - 1, TAB_HEIGHT - 1), radius=4, fill=(26, 29, 36, 255))
        
        # Левая акцентная белая полоска (3px)
        d_act.rounded_rectangle((0, 8, 3, TAB_HEIGHT - 9), radius=2, fill=(255, 255, 255, 255))

        glyph_act = render_svg_to_image(svg_content, size=22, color="#FFFFFF")
        im_active.alpha_composite(glyph_act, (12, 14))
        d_act.text((44, 11), title, font=font_bold, fill=(255, 255, 255, 255), anchor="lt")
        d_act.text((44, 28), desc, font=font_reg, fill=(180, 190, 205, 255), anchor="lt")

        im_inactive.save(ROOT / f"nav_{name}_normal.png")
        im_active.save(ROOT / f"nav_{name}_active.png")

        # 16 промежуточных кадров интерполяции
        for f in range(NUM_FRAMES):
            factor = f / (NUM_FRAMES - 1)
            blended = Image.blend(im_inactive, im_active, factor)
            blended.save(ROOT / f"nav_{name}_{f}.png")

    # 4. Карточки выбора кораблей с индикацией оставшихся/поставленных (зеленые и красные квадраты)
    # Сколько есть — зеленые квадраты, поставленные — красные квадраты.
    # Если все поставлены — блок подсвечивается чуть красным, если еще есть — зеленым.
    names = {5: "Авианосец", 4: "Линкор", 3: "Крейсер", 2: "Эсминец", 1: "Катер"}
    combos = [(5, 1), (4, 1), (3, 2), (3, 1), (2, 3), (2, 2), (1, 4), (1, 3)]
    
    SHIP_BTN_W = 300
    SHIP_BTN_H = 42

    boat_icons = {
        "green_act": render_svg_to_image(ICONS_SVG["boat"], size=22, color="#FFFFFF", stroke_width=2.2),
        "green_norm": render_svg_to_image(ICONS_SVG["boat"], size=22, color="#86EFAC", stroke_width=2.0),
        "red_act": render_svg_to_image(ICONS_SVG["boat"], size=22, color="#FCA5A5", stroke_width=2.2),
        "red_norm": render_svg_to_image(ICONS_SVG["boat"], size=22, color="#EF4444", stroke_width=2.0),
    }

    svg_dir = ROOT / "svg_sources"

    for size, total in combos:
        name = names[size]
        for placed in range(total + 1):
            rem = total - placed
            all_placed = (rem == 0)

            for active in (0, 1):
                im = Image.new("RGBA", (SHIP_BTN_W, SHIP_BTN_H), (0, 0, 0, 0))
                d = ImageDraw.Draw(im)

                if all_placed:
                    bg = (42, 20, 26, 255) if active else (30, 16, 20, 255)
                    border = (239, 68, 68, 255) if active else (75, 30, 38, 255)
                    txt_col = (255, 220, 225, 255) if active else (200, 160, 165, 255)
                    boat_im = boat_icons["red_act"] if active else boat_icons["red_norm"]
                else:
                    bg = (20, 40, 28, 255) if active else (16, 26, 20, 255)
                    border = (74, 222, 128, 255) if active else (36, 75, 48, 255)
                    txt_col = (255, 255, 255, 255) if active else (215, 235, 220, 255)
                    boat_im = boat_icons["green_act"] if active else boat_icons["green_norm"]

                border_w = 2 if active else 1
                d.rounded_rectangle((0, 0, SHIP_BTN_W - 1, SHIP_BTN_H - 1), radius=4, fill=bg, outline=border, width=border_w)
                im.alpha_composite(boat_im, (10, 10))
                d.text((38, 14), f"{name} ({size})", font=font_bold, fill=txt_col, anchor="lt")

                # Квадратики: сколько есть — зеленые, сколько поставлено — красные
                sq_size = 13
                gap = 5
                total_w = total * sq_size + (total - 1) * gap
                start_x = SHIP_BTN_W - 10 - total_w

                for i in range(total):
                    x = start_x + i * (sq_size + gap)
                    y = (SHIP_BTN_H - sq_size) // 2
                    is_available = (i < rem)
                    col = (34, 197, 94, 255) if is_available else (239, 68, 68, 255)
                    border_col = (22, 163, 74, 255) if is_available else (185, 28, 28, 255)
                    d.rounded_rectangle((x, y, x + sq_size - 1, y + sq_size - 1), radius=2, fill=col, outline=border_col, width=1)

                im.save(ROOT / f"ship_card_{size}_{total}_{placed}_{active}.png")

                # Алиасы по умолчанию (для совместимости)
                if placed == 0 and ((size == 3 and total == 2) or (size == 2 and total == 3) or (size == 1 and total == 4) or size in (4, 5)):
                    state_name = "active" if active else "normal"
                    im.save(ROOT / f"ship_card_{size}_{state_name}.png")

    # 4b. Чистые векторные иконки вращающегося корабля для виджета РАСПОЛОЖЕНИЕ (без рамок/квадратов)
    CANVAS_SZ = 64
    max_dims = {5: 56, 4: 56, 3: 50, 2: 42, 1: 30}

    for sz in [1, 2, 3, 4, 5]:
        svg_f = svg_dir / f"ship_{sz}deck.svg"
        if not svg_f.exists():
            continue
        raw_deck = render_deck_hires(svg_f, sz)
        target_d = max_dims.get(sz, 50)
        scale = float(target_d) / max(raw_deck.width, raw_deck.height)

        for f_idx in range(7):
            # ang: f=0 -> -90 (горизонтальное, носом вправо), f=6 -> 0 (вертикальное, носом вверх)
            ang = -90.0 + (90.0 * f_idx / 6.0)
            rot_im = raw_deck.rotate(-ang, expand=True, resample=Image.Resampling.BICUBIC)
            sw = max(1, int(round(rot_im.width * scale)))
            sh = max(1, int(round(rot_im.height * scale)))
            scaled_ship = rot_im.resize((sw, sh), Image.Resampling.LANCZOS)

            tile = Image.new("RGBA", (CANVAS_SZ, CANVAS_SZ), (0, 0, 0, 0))
            rx = (CANVAS_SZ - sw) // 2
            ry = (CANVAS_SZ - sh) // 2
            tile.alpha_composite(scaled_ship, (rx, ry))
            tile.save(ROOT / f"orient_{sz}_frame_{f_idx}.png")
            if sz == 4:
                tile.save(ROOT / f"orient_frame_{f_idx}.png")

    # 5. Новые векторные иконки и текстуры кнопок из svg_sources
    svg_dir = ROOT / "svg_sources"
    if svg_dir.exists():
        # Иконка победы (кубок)
        if (svg_dir / "win.svg").exists():
            im_win = render_arbitrary_svg(svg_dir / "win.svg", size=36, color="#FFFFFF", filled=True)
            im_win.save(ROOT / "icon_win_accent.png")

        # Иконка поражения (отчаяние)
        if (svg_dir / "despair.svg").exists():
            im_despair = render_arbitrary_svg(svg_dir / "despair.svg", size=36, color="#F87171", filled=True)
            im_despair.save(ROOT / "icon_despair_accent.png")

        # Иконки для кнопок управления (с плотным кадрированием без пустот)
        ico_rot = render_tight_svg(svg_dir / "reload.svg", target_h=15, color="#FFFFFF", filled=True) if (svg_dir / "reload.svg").exists() else None
        ico_clr = render_tight_svg(svg_dir / "clear.svg", target_h=15, color="#F87171", filled=False, stroke_width=3.5) if (svg_dir / "clear.svg").exists() else None
        ico_rnd = render_tight_svg(svg_dir / "dice.svg", target_h=16, color="#FFFFFF", filled=True) if (svg_dir / "dice.svg").exists() else None
        ico_play = render_tight_svg(svg_dir / "play.svg", target_h=16, color="#0E0F12", filled=True) if (svg_dir / "play.svg").exists() else None

        # Кнопка Повернуть (R): 146x36 со скруглением radius=6 и hover состоянием
        if ico_rot:
            for state, bg, border, txt_col in [
                ("normal", (22, 24, 28, 255), (46, 52, 64, 255), (240, 243, 248, 255)),
                ("hov", (34, 38, 50, 255), (85, 98, 120, 255), (255, 255, 255, 255)),
            ]:
                im = Image.new("RGBA", (146, 36), (0, 0, 0, 0))
                d = ImageDraw.Draw(im)
                d.rounded_rectangle((0, 0, 145, 35), radius=6, fill=bg, outline=border, width=1)
                bbox = d.textbbox((0, 0), "Повернуть (R)", font=font_bold)
                tw = bbox[2] - bbox[0]
                tot_w = ico_rot.width + 5 + tw
                sx = max(4, (146 - tot_w) // 2)
                im.alpha_composite(ico_rot, (sx, (36 - ico_rot.height) // 2))
                d.text((sx + ico_rot.width + 5, 17), "Повернуть (R)", font=font_bold, fill=txt_col, anchor="lm")
                suffix = "" if state == "normal" else "_hov"
                im.save(ROOT / f"btn_rotate{suffix}.png")

        # Кнопка Очистить: 146x36 со скруглением radius=6 и hover состоянием
        if ico_clr:
            for state, bg, border, txt_col in [
                ("normal", (35, 18, 24, 255), (120, 35, 45, 255), (248, 113, 113, 255)),
                ("hov", (52, 22, 32, 255), (175, 48, 62, 255), (255, 135, 135, 255)),
            ]:
                im = Image.new("RGBA", (146, 36), (0, 0, 0, 0))
                d = ImageDraw.Draw(im)
                d.rounded_rectangle((0, 0, 145, 35), radius=6, fill=bg, outline=border, width=1)
                bbox = d.textbbox((0, 0), "Очистить", font=font_bold)
                tw = bbox[2] - bbox[0]
                tot_w = ico_clr.width + 5 + tw
                sx = max(4, (146 - tot_w) // 2)
                im.alpha_composite(ico_clr, (sx, (36 - ico_clr.height) // 2))
                d.text((sx + ico_clr.width + 5, 17), "Очистить", font=font_bold, fill=txt_col, anchor="lm")
                suffix = "" if state == "normal" else "_hov"
                im.save(ROOT / f"btn_clear{suffix}.png")

        # Кнопка Случайная расстановка: 300x36 со скруглением radius=6 и hover состоянием
        if ico_rnd:
            for state, bg, border, txt_col in [
                ("normal", (22, 24, 28, 255), (46, 52, 64, 255), (240, 243, 248, 255)),
                ("hov", (34, 38, 50, 255), (85, 98, 120, 255), (255, 255, 255, 255)),
            ]:
                im = Image.new("RGBA", (300, 36), (0, 0, 0, 0))
                d = ImageDraw.Draw(im)
                d.rounded_rectangle((0, 0, 299, 35), radius=6, fill=bg, outline=border, width=1)
                bbox = d.textbbox((0, 0), "Случайная расстановка", font=font_bold)
                tw = bbox[2] - bbox[0]
                tot_w = ico_rnd.width + 5 + tw
                sx = max(4, (300 - tot_w) // 2)
                im.alpha_composite(ico_rnd, (sx, (36 - ico_rnd.height) // 2))
                d.text((sx + ico_rnd.width + 5, 17), "Случайная расстановка", font=font_bold, fill=txt_col, anchor="lm")
                suffix = "" if state == "normal" else "_hov"
                im.save(ROOT / f"btn_random{suffix}.png")

        # Кнопка Начать бой: 300x42 со скруглением radius=6 и hover состоянием
        if ico_play:
            for state, bg, border, txt_col in [
                ("normal", (245, 245, 247, 255), (255, 255, 255, 255), (14, 15, 18, 255)),
                ("hov", (255, 255, 255, 255), (255, 255, 255, 255), (14, 15, 18, 255)),
            ]:
                im = Image.new("RGBA", (300, 42), (0, 0, 0, 0))
                d = ImageDraw.Draw(im)
                d.rounded_rectangle((0, 0, 299, 41), radius=6, fill=bg, outline=border, width=1)
                bbox = d.textbbox((0, 0), "Начать бой", font=font_bold)
                tw = bbox[2] - bbox[0]
                tot_w = ico_play.width + 5 + tw
                sx = max(4, (300 - tot_w) // 2)
                im.alpha_composite(ico_play, (sx, (42 - ico_play.height) // 2))
                d.text((sx + ico_play.width + 5, 20), "Начать бой", font=font_bold, fill=txt_col, anchor="lm")
                suffix = "" if state == "normal" else "_hov"
                im.save(ROOT / f"btn_start{suffix}.png")

    print("Все ассеты карточек кораблей и кнопок действий сгенерированы!")

if __name__ == "__main__":
    build_assets()
