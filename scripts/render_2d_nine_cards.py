from __future__ import annotations

import argparse
import io
import json
import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


W, H = 900, 1500
OUTPUT_DIR: Path | None = None
DEFAULT_LOGO = Path(__file__).resolve().parents[1] / "assets" / "shanjia-pangolin-logo.png"
PERIOD_LABEL = "本期"
DATA_CUTOFF = "待填写"

FONT_REGULAR: str | None = None
FONT_BOLD: str | None = None

BG = "#F4F7FB"
PANEL = "#FFFFFF"
INK = "#132238"
MUTED = "#64748B"
GRID = "#DCE4EE"
PURPLE = "#7657D7"
PURPLE_LIGHT = "#E9E3FA"
CYAN = "#1FA7C1"
CYAN_LIGHT = "#DDF4F8"
GREEN = "#2FA873"
GREEN_LIGHT = "#DFF5EA"
RED = "#DD5B63"
RED_LIGHT = "#FCE5E7"
AMBER = "#E99A2D"
AMBER_LIGHT = "#FFF1D9"
NAVY = "#152441"

MODEL_COLORS = [
    "#7657D7", "#1FA7C1", "#E58B3A", "#2FA873", "#D95E89", "#5470C6",
]


def F(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    font = FONT_BOLD if bold else FONT_REGULAR
    if not font:
        raise RuntimeError("字体尚未配置，请通过命令行参数或环境变量指定中文字体。")
    return ImageFont.truetype(font, size)


def resolve_font(explicit: str | None, env_name: str, candidates: tuple[str, ...]) -> str:
    """Resolve a font without embedding a machine-specific absolute path."""
    requested = explicit or os.environ.get(env_name)
    if requested:
        path = Path(requested).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"字体文件不存在：{path}")
        return str(path.resolve())

    for candidate in candidates:
        try:
            font = ImageFont.truetype(candidate, 24)
        except OSError:
            continue
        return getattr(font, "path", candidate)

    raise FileNotFoundError(
        f"未找到可用中文字体。请使用命令行参数指定，或设置环境变量 {env_name}。"
    )


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def mix(c1: str, c2: str, t: float) -> tuple[int, int, int]:
    a, b = rgb(c1), rgb(c2)
    return tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))


def month_label(value: str) -> str:
    """Turn an ISO-like month key into a compact label without fixing a release year."""
    parts = value.split("-")
    if len(parts) >= 2 and parts[-1].isdigit():
        return f"{int(parts[-1])}月"
    return value


def specialty_rows(data: dict, field: str) -> list[tuple[str, float]]:
    """Pair specialty values with the authoritative department labels in the input."""
    labels = list(data["gates"]["by_department"])
    values = list(data[field].values())
    if len(labels) != len(values):
        raise ValueError(f"{field} 与 gates.by_department 的专科数量不一致")
    return list(zip(labels, values))


def gradient_image(top: str, bottom: str) -> Image.Image:
    img = Image.new("RGB", (W, H), top)
    px = img.load()
    a, b = rgb(top), rgb(bottom)
    for y in range(H):
        t = y / max(H - 1, 1)
        color = tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))
        for x in range(W):
            px[x, y] = color
    return img


def rounded(draw: ImageDraw.ImageDraw, box, fill=PANEL, radius=24, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def measure(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> float:
    if not text:
        return 0
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if paragraph == "":
            lines.append("")
            continue
        current = ""
        for char in paragraph:
            candidate = current + char
            if current and measure(draw, candidate, font) > max_width:
                lines.append(current.rstrip())
                current = char.lstrip()
            else:
                current = candidate
        if current:
            lines.append(current.rstrip())
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill=INK,
    max_width=760,
    line_gap=8,
    anchor="la",
    max_lines: int | None = None,
) -> int:
    x, y = xy
    lines = wrap_lines(draw, text, font, max_width)
    if max_lines is not None:
        lines = lines[:max_lines]
    line_h = font.size + line_gap
    for i, line in enumerate(lines):
        draw.text((x, y + i * line_h), line, font=font, fill=fill, anchor=anchor)
    return y + len(lines) * line_h


def draw_logo(draw: ImageDraw.ImageDraw, img: Image.Image, logo: Image.Image | None, x: int, y: int, size: int, dark=False):
    if logo is not None:
        fitted = logo.copy()
        max_width = round(size * 1.62)
        fitted.thumbnail((max_width, size), Image.Resampling.LANCZOS)
        if dark:
            rounded(draw, (x - 6, y - 6, x + max_width + 6, y + size + 6), fill="#FFFFFF", radius=15)
        px = x + (max_width - fitted.width) // 2
        py = y + (size - fitted.height) // 2
        if fitted.mode in ("RGBA", "LA"):
            img.paste(fitted, (px, py), fitted)
        else:
            img.paste(fitted.convert("RGB"), (px, py))
        return
    outline = "#A8B7CB" if not dark else "#8FA4C8"
    fill = "#FFFFFF" if not dark else "#24385D"
    rounded(draw, (x, y, x + size, y + size), fill=fill, radius=16, outline=outline, width=2)
    draw.text((x + size / 2, y + size / 2 - 7), "LOGO", font=F(16, True), fill=outline, anchor="mm")
    draw.text((x + size / 2, y + size / 2 + 13), "待替换", font=F(12), fill=outline, anchor="mm")


def base_card(title: str, subtitle: str, number: int, logo: Image.Image | None):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_logo(draw, img, logo, 56, 42, 58)
    draw.text((174, 49), "山甲AI医疗测评", font=F(22, True), fill=INK)
    draw.text((174, 80), "来自穿三甲研究院", font=F(15), fill=MUTED)
    draw.text((842, 62), f"{number:02d}/09", font=F(18, True), fill=MUTED, anchor="ra")
    draw.text((54, 142), title, font=F(46, True), fill=INK)
    draw_wrapped(draw, (56, 207), subtitle, F(22), MUTED, 790, 7)
    draw.line((54, 258, 846, 258), fill=GRID, width=2)
    return img, draw


def footer(draw: ImageDraw.ImageDraw, text=None):
    if text is None:
        text = f"仅代表本批次、题目与评分口径｜数据截至 {DATA_CUTOFF}"
    draw.line((54, 1400, 846, 1400), fill=GRID, width=2)
    draw.text((54, 1435), "山甲AI医疗测评｜来自穿三甲研究院", font=F(17, True), fill=INK)
    draw.text((846, 1435), text, font=F(14), fill=MUTED, anchor="ra")


def load_logo(path: str | None) -> Image.Image | None:
    if not path:
        return None
    logo_path = Path(path)
    if not logo_path.exists():
        raise FileNotFoundError(f"Logo 文件不存在：{logo_path}")
    if logo_path.suffix.lower() == ".svg":
        try:
            import cairosvg
        except ImportError as exc:
            raise RuntimeError("SVG Logo 需要 cairosvg；也可直接提供透明 PNG。") from exc
        data = cairosvg.svg2png(url=str(logo_path))
        return Image.open(io.BytesIO(data)).convert("RGBA")
    return Image.open(logo_path).convert("RGBA")


def save(img: Image.Image, filename: str):
    if OUTPUT_DIR is None:
        raise RuntimeError("OUTPUT_DIR is not configured")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(OUTPUT_DIR / filename, format="PNG", optimize=True)


def card1(data, logo):
    img = gradient_image("#12213E", "#29486D")
    draw = ImageDraw.Draw(img, "RGB")
    draw.ellipse((570, -80, 1050, 400), fill="#1F7894")
    draw.ellipse((-220, 1080, 300, 1600), fill="#4F3E91")
    draw_logo(draw, img, logo, 56, 48, 70, dark=True)
    draw.text((188, 60), "山甲AI医疗测评", font=F(24, True), fill="#FFFFFF")
    draw.text((188, 94), "来自穿三甲研究院", font=F(16), fill="#B9C8DA")
    draw.text((56, 220), PERIOD_LABEL, font=F(30, True), fill="#69D6E6")
    draw.text((52, 285), "2D医生端", font=F(76, True), fill="#FFFFFF")
    draw.text((52, 385), "AI医疗测评", font=F(76, True), fill="#FFFFFF")
    draw_wrapped(
        draw,
        (58, 500),
        f"{data['population']['products']}款产品、{data['population']['departments']}个专科的临床定性与技术定量汇总",
        F(27),
        "#C9D7E7",
        760,
        10,
    )

    stats = [
        (str(data["population"]["products"]), "款产品"),
        (str(data["population"]["departments"]), "个专科"),
        (str(data["population"]["runs_per_product_per_department"]), "次重复测试"),
        (f"{data['population']['clinical_outputs']} + {data['population']['technical_outputs']}", "临床输出 + 技术输出"),
    ]
    for idx, (big, small) in enumerate(stats):
        col, row = idx % 2, idx // 2
        x = 54 + col * 402
        y = 650 + row * 208
        rounded(draw, (x, y, x + 364, y + 170), fill="#FFFFFF", radius=28)
        draw.text((x + 28, y + 28), big, font=F(46 if idx < 3 else 36, True), fill=NAVY)
        draw.text((x + 28, y + 102), small, font=F(21), fill=MUTED)

    rounded(draw, (54, 1090, 846, 1265), fill="#172A4B", radius=28, outline="#587093", width=2)
    draw.text((84, 1123), "评分结构", font=F(22, True), fill="#8FE1EC")
    draw.text((84, 1171), "临床定性 60 分", font=F(30, True), fill="#C6B7FF")
    draw.text((446, 1171), "+  技术定量 40 分", font=F(30, True), fill="#8FE1EC")
    draw.text((54, 1372), "排名用于理解本批次表现，不构成临床诊疗、采购或投资建议。", font=F(18), fill="#D7E2EE")
    draw.text((846, 1434), "01/09", font=F(18, True), fill="#B9C8DA", anchor="ra")
    save(img, "01_封面.png")


def card2(data, logo):
    img, draw = base_card("这份榜单怎么得出", "同一套任务，分别观察临床决策质量与技术结构化能力。", 2, logo)
    rounded(draw, (54, 290, 846, 430), fill=PANEL, radius=24)
    draw.text((82, 318), "样本结构", font=F(22, True), fill=INK)
    population = data["population"]
    draw.text((82, 365), f"{population['products']}款产品  ×  {population['departments']}个专科  ×  {population['runs_per_product_per_department']}次重复  =  {population['clinical_outputs']}次输出", font=F(28, True), fill=NAVY)

    boxes = [
        ("01", "临床定性", "医生核对分\n满分60", PURPLE_LIGHT, PURPLE),
        ("02", "安全闸门", "Step 1A / 1B\n按输出样本统计", GREEN_LIGHT, GREEN),
        ("03", "技术定量", "D1—D5结构化评估\n折算满分40", CYAN_LIGHT, CYAN),
        ("04", "综合得分", "临床均分 + 技术分\n满分100", "#E7EDF6", NAVY),
    ]
    for i, (num, name, desc, fill, accent) in enumerate(boxes):
        x = 54 + (i % 2) * 405
        y = 470 + (i // 2) * 250
        rounded(draw, (x, y, x + 378, y + 214), fill=fill, radius=26)
        draw.text((x + 28, y + 28), num, font=F(19, True), fill=accent)
        draw.text((x + 28, y + 67), name, font=F(30, True), fill=INK)
        draw_wrapped(draw, (x + 28, y + 119), desc, F(19), MUTED, 320, 7)

    draw.text((54, 1015), "60 / 40 评分结构", font=F(24, True), fill=INK)
    rounded(draw, (54, 1065, 846, 1125), fill="#E8EDF4", radius=18)
    draw.rounded_rectangle((54, 1065, 529, 1125), radius=18, fill=PURPLE)
    draw.rounded_rectangle((529, 1065, 846, 1125), radius=18, fill=CYAN)
    draw.text((292, 1095), "临床 60", font=F(22, True), fill="white", anchor="mm")
    draw.text((688, 1095), "技术 40", font=F(22, True), fill="white", anchor="mm")

    rounded(draw, (54, 1170, 846, 1350), fill=AMBER_LIGHT, radius=24)
    draw.text((82, 1200), "跨月阅读提示", font=F(22, True), fill="#9A5E11")
    draw_wrapped(draw, (82, 1242), "若不同批次的专科范围或合成口径发生变化，历史部分只比较名次演化，不比较绝对分数。", F(20), "#78501C", 730, 8)
    footer(draw)
    save(img, "02_测评方法.png")


def card3(data, logo):
    img, draw = base_card(f"{data['population']['products']}款产品完整榜单", "综合分 = 临床定性（60）+ 技术定量（40）；按综合分降序。", 3, logo)
    draw.rectangle((54, 278, 68, 294), fill=PURPLE)
    draw.text((78, 273), "临床定性", font=F(17), fill=MUTED)
    draw.rectangle((182, 278, 196, 294), fill=CYAN)
    draw.text((206, 273), "技术定量", font=F(17), fill=MUTED)
    draw.text((810, 273), "总分", font=F(17), fill=MUTED, anchor="ra")

    products = sorted(data["products"], key=lambda x: x["overall_rank"])
    y0, row_h = 322, 67
    bar_x, bar_w, bar_h = 322, 470, 22
    for i, p in enumerate(products):
        y = y0 + i * row_h
        if i < 3:
            rounded(draw, (50, y - 10, 850, y + 51), fill="#F0ECFB", radius=15)
        draw.text((58, y + 15), f"{p['overall_rank']:02d}", font=F(18, True), fill=PURPLE if i < 3 else MUTED, anchor="lm")
        label = p["label"]
        label_font = F(20, True if i < 3 else False)
        lines = wrap_lines(draw, label, label_font, 220)[:2]
        ty = y + 4 if len(lines) == 1 else y - 8
        for j, line in enumerate(lines):
            draw.text((102, ty + j * 24), line, font=label_font, fill=INK)
        draw.rounded_rectangle((bar_x, y + 4, bar_x + bar_w, y + 4 + bar_h), radius=10, fill="#E4EAF1")
        c_w = round(bar_w * p["clinical"] / 100)
        t_w = round(bar_w * p["technical"] / 100)
        draw.rounded_rectangle((bar_x, y + 4, bar_x + c_w, y + 4 + bar_h), radius=10, fill=PURPLE)
        draw.rectangle((bar_x + max(c_w - 10, 0), y + 4, bar_x + c_w, y + 4 + bar_h), fill=PURPLE)
        draw.rectangle((bar_x + c_w, y + 4, bar_x + c_w + t_w, y + 4 + bar_h), fill=CYAN)
        draw.text((842, y + 15), f"{p['total']:.1f}", font=F(21, True), fill=INK, anchor="rm")

    draw_wrapped(draw, (54, 1344), f"注：模型名应以{PERIOD_LABEL}经确认的权威记录为准；疑似错误版本不用于对外命名。", F(16), MUTED, 790, 5)
    footer(draw)
    save(img, "03_完整榜单.png")


def draw_vertical_gate(draw, x, y, w, h, pass_count, total, title):
    pass_pct = pass_count / total
    fail_pct = 1 - pass_pct
    draw.text((x + w / 2, y - 54), title, font=F(23, True), fill=INK, anchor="mm")
    pass_h = round(h * pass_pct)
    fail_h = h - pass_h
    draw.rounded_rectangle((x, y, x + w, y + h), radius=24, fill=GREEN)
    draw.rounded_rectangle((x, y, x + w, y + fail_h + 18), radius=24, fill=RED)
    draw.rectangle((x, y + 18, x + w, y + fail_h), fill=RED)
    draw.text((x + w / 2, y + fail_h / 2), f"未通过\n{fail_pct*100:.1f}%\n{total-pass_count}/{total}", font=F(19, True), fill="white", anchor="mm", align="center", spacing=5)
    draw.text((x + w / 2, y + fail_h + pass_h / 2), f"通过\n{pass_pct*100:.1f}%\n{pass_count}/{total}", font=F(21, True), fill="white", anchor="mm", align="center", spacing=5)


def card4(data, logo):
    img, draw = base_card("安全闸门：真正拉开差距的第一关", "统计单位为“产品 × 专科 × 轮次”的输出样本，不是产品数。", 4, logo)
    gates = data["gates"]
    total = gates["total"]
    draw_vertical_gate(draw, 180, 375, 220, 430, total["pass_a"], total["n"], "Step 1A 一票否决")
    draw_vertical_gate(draw, 500, 375, 220, 430, total["pass_b"], total["n"], "Step 1B 高风险警示")

    draw.text((54, 865), "分专科通过率", font=F(24, True), fill=INK)
    cols = [("Step 1A", 360), ("Step 1B", 625)]
    for label, x in cols:
        draw.text((x, 910), label, font=F(18, True), fill=MUTED, anchor="mm")
    dept_rows = list(gates["by_department"].items())
    for idx, (dept, row) in enumerate(dept_rows):
        y = 960 + idx * 105
        rounded(draw, (54, y - 28, 846, y + 58), fill=PANEL, radius=20)
        draw.text((82, y + 15), dept, font=F(22, True), fill=INK, anchor="lm")
        for key, x in [("pass_a", 360), ("pass_b", 625)]:
            value = row[key]
            pct = value / row["n"] * 100
            color = GREEN if pct >= 50 else RED
            draw.text((x, y + 2), f"{pct:.1f}%", font=F(25, True), fill=color, anchor="mm")
            draw.text((x, y + 31), f"{value}/{row['n']}", font=F(15), fill=MUTED, anchor="mm")

    rounded(draw, (54, 1195, 846, 1354), fill=AMBER_LIGHT, radius=24)
    draw.text((82, 1225), "如何理解", font=F(21, True), fill="#925B12")
    draw_wrapped(draw, (82, 1263), "未通过安全闸门会限制后续临床得分。低分可能同时反映安全红线、任务适配和回答质量，不能简化为单一能力判断。", F(19), "#78501C", 730, 8)
    footer(draw)
    save(img, "04_安全闸门.png")


def card5(data, logo):
    img, draw = base_card(
        "临床表现：专科差异显著",
        f"以下专科结果与子项目均基于{data['population']['products']}款产品的产品级均值。",
        5,
        logo,
    )
    rounded(draw, (54, 290, 846, 515), fill=PANEL, radius=24)
    draw.text((82, 320), "专科临床均分 / 60", font=F(22, True), fill=INK)
    specialties = specialty_rows(data, "clinical_specialty_means")
    for i, (name, value) in enumerate(specialties):
        y = 385 + i * 68
        draw.text((82, y + 12), name, font=F(19, True), fill=INK, anchor="lm")
        x0, bw = 240, 500
        draw.rounded_rectangle((x0, y, x0 + bw, y + 24), radius=12, fill="#E7ECF3")
        draw.rounded_rectangle((x0, y, x0 + bw * value / 60, y + 24), radius=12, fill=PURPLE)
        draw.text((800, y + 12), f"{value:.1f}", font=F(20, True), fill=PURPLE, anchor="rm")

    draw.text((54, 565), "临床子项目结构（均分 / 10）", font=F(24, True), fill=INK)
    labels = ["1.1 病情提炼", "1.2 诊断推理", "1.3 鉴别证据", "2.1 处置计划", "2.2 风险边界", "3.1 沟通教学"]
    dims = [sum(p["dim_means"][i] for p in data["products"]) / len(data["products"]) for i in range(6)]
    shades = ["#6F52D1", "#8064D9", "#9278E0", "#A08BE5", "#B19FEA", "#C0B2EE"]
    for i, (label, value) in enumerate(zip(labels, dims)):
        y = 630 + i * 92
        draw.text((58, y + 12), label, font=F(19, True), fill=INK, anchor="lm")
        x0, bw = 290, 460
        draw.rounded_rectangle((x0, y, x0 + bw, y + 26), radius=13, fill="#E6EAF1")
        draw.rounded_rectangle((x0, y, x0 + bw * value / 10, y + 26), radius=13, fill=shades[i])
        draw.text((812, y + 13), f"{value:.1f}", font=F(20, True), fill=PURPLE, anchor="rm")

    rounded(draw, (54, 1208, 846, 1355), fill=PURPLE_LIGHT, radius=24)
    draw_wrapped(draw, (82, 1240), "专科结果可能同时受到安全闸门与任务适配度影响。本图呈现观察到的差异，不据此推断单一原因。", F(19), "#51408D", 730, 8)
    footer(draw)
    save(img, "05_临床表现.png")


def radar_points(cx, cy, radius, values):
    points = []
    n = len(values)
    for i, value in enumerate(values):
        angle = -math.pi / 2 + i * 2 * math.pi / n
        r = radius * value / 100
        points.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
    return points


def draw_radar(draw, box, row, color):
    x0, y0, x1, y1 = box
    rounded(draw, box, fill=PANEL, radius=20)
    label_font = F(16, True)
    title_lines = wrap_lines(draw, row["label"], label_font, x1 - x0 - 20)[:2]
    ty = y0 + 16
    for j, line in enumerate(title_lines):
        draw.text(((x0 + x1) / 2, ty + j * 21), line, font=label_font, fill=INK, anchor="ma")
    draw.text(((x0 + x1) / 2, y0 + 61), f"技术综合 {row['composite_pct']:.1f}", font=F(14, True), fill=color, anchor="ma")
    cx, cy = (x0 + x1) / 2, y0 + 190
    radius = 76
    for level, outline in [(50, "#D9E0E9"), (100, "#B9C5D3")]:
        pts = radar_points(cx, cy, radius, [level] * 5)
        draw.line(pts + [pts[0]], fill=outline, width=2)
    for i in range(5):
        angle = -math.pi / 2 + i * 2 * math.pi / 5
        px, py = cx + math.cos(angle) * radius, cy + math.sin(angle) * radius
        draw.line((cx, cy, px, py), fill="#D9E0E9", width=1)
        lx, ly = cx + math.cos(angle) * (radius + 17), cy + math.sin(angle) * (radius + 17)
        draw.text((lx, ly), f"D{i+1}", font=F(14, True), fill=MUTED, anchor="mm")
    values = [row["dimension_pct"][f"D{i}"] for i in range(1, 6)]
    pts = radar_points(cx, cy, radius, values)
    fill_rgb = mix(color, "#FFFFFF", 0.62)
    draw.polygon(pts, fill=fill_rgb)
    draw.line(pts + [pts[0]], fill=color, width=4, joint="curve")
    for pt in pts:
        draw.ellipse((pt[0] - 3, pt[1] - 3, pt[0] + 3, pt[1] + 3), fill=color)
    draw.text((x0 + 14, y1 - 22), "径向刻度：50 / 100", font=F(12), fill=MUTED)


def card6(data, radar, logo):
    img, draw = base_card("技术量化：D1—D5能力雷达", "指定专科技术综合得分前6；所有维度已换算为0—100分。", 6, logo)
    rounded(draw, (54, 285, 846, 372), fill=CYAN_LIGHT, radius=22)
    technical_specialties = specialty_rows(data, "technical_specialty_means")
    for index, (name, value) in enumerate(technical_specialties[:2]):
        x = 82 + index * 408
        draw.text((x, 312), f"{name}技术均分", font=F(16, True), fill=INK)
        draw.text((x, 342), f"{value:.2f}/40", font=F(23, True), fill=CYAN)

    boxes = []
    for r in range(2):
        for c in range(3):
            x0 = 52 + c * 266
            y0 = 400 + r * 314
            boxes.append((x0, y0, x0 + 248, y0 + 292))
    for idx, (row, box) in enumerate(zip(radar["rows"], boxes)):
        draw_radar(draw, box, row, MODEL_COLORS[idx])

    rounded(draw, (54, 1045, 846, 1338), fill=PANEL, radius=24)
    draw.text((78, 1072), "维度说明", font=F(21, True), fill=INK)
    dimensions = [
        "D1 信息抽取准确性",
        "D2 事实判断待补分层清晰度",
        "D3 结构化整理与医学语言转译",
        "D4 初步诊断与风险分层",
        "D5 诊断依据链与闭环",
    ]
    for i, item in enumerate(dimensions):
        col, rr = i % 2, i // 2
        x = 78 + col * 382
        y = 1120 + rr * 68
        draw_wrapped(draw, (x, y), item, F(17, True if i == 4 else False), INK, 345, 5, max_lines=2)
    draw.text((78, 1310), "越接近外圈且越均衡，表示能力越高且短板越少。", font=F(15), fill=MUTED)
    footer(draw)
    save(img, "06_技术雷达.png")


def card7(data, logo):
    img, draw = base_card("双轨错位：临床高分不等于技术领先", "临床与技术排名未呈现稳定的强相关关系，应同时查看两条轨道。", 7, logo)
    rounded(draw, (54, 286, 438, 405), fill=PURPLE_LIGHT, radius=22)
    draw.text((78, 312), "Pearson 线性相关", font=F(18), fill=MUTED)
    draw.text((78, 354), f"r = {data['correlations']['clinical_vs_technical_pearson']:.3f}", font=F(31, True), fill=PURPLE)
    rounded(draw, (462, 286, 846, 405), fill=CYAN_LIGHT, radius=22)
    draw.text((486, 312), "Spearman 秩相关", font=F(18), fill=MUTED)
    draw.text((486, 354), f"ρ = {data['correlations']['clinical_vs_technical_spearman']:.3f}", font=F(31, True), fill=CYAN)

    draw.text((54, 445), "名次差较大的产品", font=F(23, True), fill=INK)
    draw.text((372, 482), "1", font=F(14), fill=MUTED, anchor="ma")
    draw.text((792, 482), "15", font=F(14), fill=MUTED, anchor="ma")
    draw.line((372, 506, 792, 506), fill=GRID, width=2)
    gaps = sorted(data["largest_rank_gaps"], key=lambda p: abs(p["rank_gap_clin_minus_tech"]), reverse=True)[:8]
    for i, p in enumerate(gaps):
        y = 550 + i * 72
        draw.text((58, y), p["product"], font=F(18, True), fill=INK, anchor="lm")
        cx = 372 + (p["clinical_rank"] - 1) / 14 * 420
        tx = 372 + (p["technical_rank"] - 1) / 14 * 420
        draw.line((min(cx, tx), y, max(cx, tx), y), fill="#BEC9D7", width=4)
        draw.ellipse((cx - 8, y - 8, cx + 8, y + 8), fill=PURPLE)
        draw.ellipse((tx - 8, y - 8, tx + 8, y + 8), fill=CYAN)
        draw.text((cx, y - 20), f"临{p['clinical_rank']}", font=F(12, True), fill=PURPLE, anchor="mm")
        draw.text((tx, y + 23), f"技{p['technical_rank']}", font=F(12, True), fill=CYAN, anchor="mm")

    draw.rectangle((54, 1132, 68, 1146), fill=PURPLE)
    draw.text((78, 1127), "临床排名", font=F(15), fill=MUTED)
    draw.rectangle((178, 1132, 192, 1146), fill=CYAN)
    draw.text((202, 1127), "技术排名", font=F(15), fill=MUTED)

    stat_items = [
        ("技术能力均值", f"{data['technical_quadrant_means']['ability_pct']:.1f}%", CYAN),
        ("技术稳定性均值", f"{data['technical_quadrant_means']['stability_pct']:.1f}%", GREEN),
        ("响应时长", f"{data['duration']['median']:.0f}s 中位数", AMBER),
    ]
    for i, (label, value, color) in enumerate(stat_items):
        x = 54 + i * 270
        rounded(draw, (x, 1182, x + 250, 1328), fill=PANEL, radius=22)
        draw.text((x + 22, 1208), label, font=F(16), fill=MUTED)
        draw.text((x + 22, 1252), value, font=F(25, True), fill=color)
        if i == 2:
            duration = data["duration"]
            if all(key in duration for key in ("mean", "min", "max")):
                draw.text(
                    (x + 22, 1292),
                    f"均值{duration['mean']:.0f}s｜{duration['min']:.0f}—{duration['max']:.0f}s",
                    font=F(13),
                    fill=MUTED,
                )
    footer(draw)
    save(img, "07_双轨错位.png")


def rank_color(rank: int, pool=15):
    t = (rank - 1) / max(pool - 1, 1)
    if t < 0.5:
        return mix("#D8F3EA", "#EDF4FA", t * 2)
    return mix("#EDF4FA", "#F8DEDF", (t - 0.5) * 2)


def card8(data, logo):
    revo = data["rank_evolution"]
    months = revo["month_order"]
    month_labels = [month_label(month) for month in months]
    full_coverage = sum(all(row["ranks"].get(month) is not None for month in months) for row in revo["rows"])
    img, draw = base_card(
        f"{month_labels[0]}—{month_labels[-1]}排名演化：格局在变化",
        f"累计{revo['all_products']}款产品，{full_coverage}款覆盖全部批次；只比较名次，不比较绝对分数。",
        8,
        logo,
    )
    rounded(draw, (54, 280, 846, 350), fill=AMBER_LIGHT, radius=20)
    method_note = revo.get("method_break_note", "各期专科范围或合成口径如有变化，应在发布前写入数据说明。")
    draw.text((76, 315), method_note, font=F(17), fill="#78501C", anchor="lm")

    x_name, x_cells, cell_w = 58, 352, 112
    draw.text((x_name, 382), "产品", font=F(17, True), fill=MUTED)
    for j, label in enumerate(month_labels):
        draw.text((x_cells + j * cell_w + 48, 382), label, font=F(17, True), fill=MUTED, anchor="ma")

    latest_month = months[-1]
    rows = sorted(revo["rows"], key=lambda r: (r["ranks"].get(latest_month) is None, r["ranks"].get(latest_month) or 99))
    y0, row_h = 422, 49
    for i, row in enumerate(rows):
        y = y0 + i * row_h
        if i % 2 == 0:
            draw.rectangle((50, y - 5, 850, y + row_h - 7), fill="#F9FBFD")
        draw.text((x_name, y + 17), row["product"], font=F(19, True if i < 3 else False), fill=INK, anchor="lm")
        for j, month in enumerate(months):
            rank = row["ranks"].get(month)
            x = x_cells + j * cell_w
            color = "#E8EDF3" if rank is None else rank_color(rank, revo["month_pools"][month])
            rounded(draw, (x, y, x + 94, y + 36), fill=color, radius=10)
            text = "—" if rank is None else str(rank)
            draw.text((x + 47, y + 18), text, font=F(20, True), fill="#8A96A8" if rank is None else INK, anchor="mm")

    draw.text((54, 1230), "月份间排名相关（Spearman ρ）", font=F(20, True), fill=INK)
    adjacent = revo["adjacent_spearman"]
    stats = [
        (
            f"{month_label(left)}→{month_label(right)}",
            adjacent.get(f"{left}_to_{right}"),
        )
        for left, right in zip(months, months[1:])
    ]
    stats.append(
        (
            f"{month_labels[0]}→{month_labels[-1]}",
            revo.get("first_to_last_spearman", revo.get("may_to_august_spearman")),
        )
    )
    for i, (label, value) in enumerate(stats):
        x = 54 + i * 202
        rounded(draw, (x, 1270, x + 184, 1360), fill=PANEL, radius=18)
        draw.text((x + 16, 1291), label, font=F(15), fill=MUTED)
        rendered_value = "—" if value is None else f"{value:.3f}"
        color = MUTED if value is None else (CYAN if value >= 0.5 else AMBER)
        draw.text((x + 16, 1322), rendered_value, font=F(22, True), fill=color)
    footer(draw)
    save(img, "08_历月排名演化.png")


def card9(data, logo):
    img, draw = base_card("怎样正确使用这份测评", "数据能帮助发现差异，也必须与样本、专科、版本和测试条件一起解读。", 9, logo)
    conclusions = [
        ("01", "安全合规优先", "安全闸门会直接影响临床有效得分，应先看失败样本，再看总排名。", GREEN_LIGHT, GREEN),
        ("02", "临床与技术双轨", "两条轨道未呈现稳定强相关，单轨领先不等于综合领先。", PURPLE_LIGHT, PURPLE),
        ("03", "专科适配显著", "不同专科的表现可能存在差异，不能用单专科结论外推全部场景。", CYAN_LIGHT, CYAN),
        ("04", "排名仍会波动", "不同批次的榜单格局可能变化，应结合连续观察，而非只看一次名次。", AMBER_LIGHT, AMBER),
    ]
    for i, (num, title, desc, fill, accent) in enumerate(conclusions):
        x = 54 + (i % 2) * 405
        y = 292 + (i // 2) * 250
        rounded(draw, (x, y, x + 378, y + 220), fill=fill, radius=25)
        draw.text((x + 28, y + 28), num, font=F(18, True), fill=accent)
        draw.text((x + 28, y + 65), title, font=F(25, True), fill=INK)
        draw_wrapped(draw, (x + 28, y + 111), desc, F(18), MUTED, 320, 7)

    draw.text((54, 830), "建议的使用方式", font=F(24, True), fill=INK)
    recommendations = [
        "按具体专科和真实任务做小规模验证",
        "优先复盘安全失败样本，而非只看均分",
        "完整保留模型版本、提示词和响应环境",
        "扩大题量并重复测评后，再支持采购或临床决策",
    ]
    for i, item in enumerate(recommendations):
        y = 888 + i * 62
        draw.ellipse((58, y + 4, 78, y + 24), fill=NAVY)
        draw.text((68, y + 14), str(i + 1), font=F(12, True), fill="white", anchor="mm")
        draw.text((94, y + 14), item, font=F(19), fill=INK, anchor="lm")

    rounded(draw, (54, 1155, 846, 1346), fill="#E9EEF5", radius=24)
    draw.text((80, 1182), "边界与限制", font=F(21, True), fill=INK)
    draw_wrapped(draw, (80, 1223), "本结果受题量、专科结构、模型版本、采集时间、网络与响应计时条件影响；响应时长仅作描述。内容不构成临床诊疗、产品采购、投资或商业背书。", F(18), MUTED, 730, 8)

    draw_logo(draw, img, logo, 54, 1374, 62)
    draw.text((174, 1400), "山甲AI医疗测评｜来自穿三甲研究院", font=F(18, True), fill=INK)
    draw.text((846, 1400), f"数据截至 {DATA_CUTOFF}｜09/09", font=F(15), fill=MUTED, anchor="ra")
    save(img, "09_结论与边界.png")


def make_contact_sheet():
    if OUTPUT_DIR is None:
        raise RuntimeError("OUTPUT_DIR is not configured")
    thumbs = []
    for i in range(1, 10):
        path = next(OUTPUT_DIR.glob(f"{i:02d}_*.png"))
        img = Image.open(path).convert("RGB")
        img.thumbnail((520, 866), Image.Resampling.LANCZOS)
        thumbs.append(img)
    sheet = Image.new("RGB", (1800, 2850), "#E8EDF4")
    draw = ImageDraw.Draw(sheet)
    draw.text((90, 50), "2D医生端测评｜微信公众号九图总览", font=F(36, True), fill=INK)
    for i, thumb in enumerate(thumbs):
        col, row = i % 3, i // 3
        x, y = 70 + col * 580, 130 + row * 900
        rounded(draw, (x - 10, y - 10, x + thumb.width + 10, y + thumb.height + 10), fill="white", radius=18)
        sheet.paste(thumb, (x, y))
    sheet.save(OUTPUT_DIR / "00_九图总览.png", format="PNG", optimize=True)


def make_mobile_qa_previews():
    if OUTPUT_DIR is None:
        raise RuntimeError("OUTPUT_DIR is not configured")
    qa_dir = OUTPUT_DIR / "_qa_mobile_375"
    qa_dir.mkdir(parents=True, exist_ok=True)
    for number in (3, 6, 8):
        source = next(OUTPUT_DIR.glob(f"{number:02d}_*.png"))
        image = Image.open(source).convert("RGB")
        image = image.resize((375, 625), Image.Resampling.LANCZOS)
        image.save(qa_dir / f"{number:02d}_375px.png", format="PNG", optimize=True)


def validate(data, radar):
    products = sorted(data["products"], key=lambda p: p["overall_rank"])
    assert len(products) == data["population"]["products"]
    assert len({p["product"] for p in products}) == len(products)
    assert [p["overall_rank"] for p in products] == list(range(1, len(products) + 1))
    assert all(abs((p["clinical"] + p["technical"]) - p["total"]) < 0.02 for p in products)
    gates = data["gates"]["total"]
    assert 0 <= gates["pass_a"] <= gates["n"]
    assert 0 <= gates["pass_b"] <= gates["n"]
    assert 1 <= len(radar["rows"]) <= 6
    dimension_keys = set(radar["rows"][0]["dimension_pct"])
    assert dimension_keys
    assert all(set(r["dimension_pct"]) == dimension_keys for r in radar["rows"])
    assert data["rank_evolution"]["all_products"] == len(data["rank_evolution"]["rows"])
    if OUTPUT_DIR is None:
        raise RuntimeError("OUTPUT_DIR is not configured")
    for i in range(1, 10):
        path = next(OUTPUT_DIR.glob(f"{i:02d}_*.png"))
        with Image.open(path) as image:
            assert image.size == (W, H), (path.name, image.size)
            assert image.mode == "RGB", (path.name, image.mode)


def main():
    global OUTPUT_DIR, PERIOD_LABEL, DATA_CUTOFF, FONT_REGULAR, FONT_BOLD
    parser = argparse.ArgumentParser(description="生成2D医生端微信公众号九图发布包")
    parser.add_argument("--analysis", required=True, help="标准化analysis_summary.json路径")
    parser.add_argument("--radar", required=True, help="技术雷达数据JSON路径")
    parser.add_argument("--out", required=True, help="输出目录")
    parser.add_argument("--logo", default=str(DEFAULT_LOGO), help="正式Logo文件路径；默认使用技能内置品牌资产")
    parser.add_argument("--period-label", default="本期", help="封面周期文字，例如某年某月")
    parser.add_argument("--data-cutoff", required=True, help="数据截止日期，建议使用 YYYY-MM-DD")
    parser.add_argument(
        "--font-regular",
        help="中文常规字体文件；也可设置 MEDICAL_EVAL_FONT_REGULAR",
    )
    parser.add_argument(
        "--font-bold",
        help="中文粗体字体文件；也可设置 MEDICAL_EVAL_FONT_BOLD",
    )
    args = parser.parse_args()
    OUTPUT_DIR = Path(args.out).resolve()
    PERIOD_LABEL = args.period_label
    DATA_CUTOFF = args.data_cutoff
    FONT_REGULAR = resolve_font(
        args.font_regular,
        "MEDICAL_EVAL_FONT_REGULAR",
        ("NotoSansCJK-Regular.ttc", "SourceHanSansCN-Regular.otf", "msyh.ttc"),
    )
    FONT_BOLD = resolve_font(
        args.font_bold,
        "MEDICAL_EVAL_FONT_BOLD",
        ("NotoSansCJK-Bold.ttc", "SourceHanSansCN-Bold.otf", "msyhbd.ttc", "msyh.ttc"),
    )
    data = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
    radar = json.loads(Path(args.radar).read_text(encoding="utf-8"))
    logo = load_logo(args.logo)

    card1(data, logo)
    card2(data, logo)
    card3(data, logo)
    card4(data, logo)
    card5(data, logo)
    card6(data, radar, logo)
    card7(data, logo)
    card8(data, logo)
    card9(data, logo)
    validate(data, radar)
    make_contact_sheet()
    make_mobile_qa_previews()
    print(f"Generated and validated 9 cards in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
