#!/usr/bin/env python3
"""
Kindle Ink Clock icon theme.

This keeps clock.py untouched and reuses its data/cache/main-loop helpers, while
rendering a weather-icon variant of the top weather strip.
"""
import os
import json
import time
import traceback

import clock as base


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(PROJECT_DIR, "assets", "icons", "meteocons", "png")
ICON_SIZE = 42
ICON_X = 52
ICON_GAP = 14

WEATHER_ICON_RULES = [
    ("thunderstorms", ("雷", "电", "闪")),
    ("snow", ("雪", "霰", "冰粒")),
    ("fog", ("雾", "霾", "沙尘", "浮尘")),
    ("rain", ("雨", "阵雨", "暴雨", "冻雨", "毛毛雨")),
    ("partly-cloudy-day", ("多云", "少云", "晴间多云")),
    ("cloudy", ("阴", "云")),
    ("clear-day", ("晴", "朗")),
]


def load_almanac():
    today = str(base.local_now().date())
    if base._almanac_mem["date"] == today:
        return base._almanac_mem
    if os.path.exists(base.ALMANAC_CACHE):
        try:
            with open(base.ALMANAC_CACHE) as f:
                data = json.load(f)
            if isinstance(data, dict):
                base._almanac_mem = data
                return base._almanac_mem
        except Exception:
            pass
    return base._almanac_mem


def select_weather_icon_key(weather_text):
    for icon_key, keywords in WEATHER_ICON_RULES:
        if any(keyword in weather_text for keyword in keywords):
            return icon_key
    return "cloudy"


def _load_icon_mask(icon_key, size=ICON_SIZE):
    from PIL import Image

    path = os.path.join(ICON_DIR, f"{icon_key}.png")
    if not os.path.exists(path):
        path = os.path.join(ICON_DIR, "cloudy.png")

    icon = Image.open(path).convert("RGBA")
    if icon.size != (size, size):
        icon = icon.resize((size, size), Image.Resampling.LANCZOS)

    return icon.getchannel("A")


def draw_weather_header(img, draw, y, weather, font):
    wtext = weather.get("text", f"{base.CITY_CN}  天气暂不可用")
    sr, ss = weather.get("sunrise", ""), weather.get("sunset", "")
    top_line = f"{wtext}    ↑{sr}  ↓{ss}" if (sr and ss) else wtext

    icon_key = select_weather_icon_key(wtext)
    icon_mask = _load_icon_mask(icon_key)
    icon_y = y - 4
    img.paste(0, (ICON_X, icon_y), icon_mask)

    tw, th, tb = base._text_size(draw, top_line, font)
    text_x = ICON_X + ICON_SIZE + ICON_GAP
    text_y = y + (ICON_SIZE - th) // 2 - tb[1] - 4
    draw.text((text_x, text_y), top_line, fill=80, font=font)


def render(weather, out_path="/tmp/clock.png"):
    from PIL import Image, ImageDraw

    now = base.local_now()
    almanac = load_almanac()
    img = Image.new("L", (base.SCREEN_W, base.SCREEN_H), 255)
    draw = ImageDraw.Draw(img)

    fonts = base._load_fonts()
    ft = fonts["ft"]
    fd = fonts["fd"]
    fw = fonts["fw"]
    fnum = fonts["fnum"]
    fhdr = fonts["fhdr"]
    flbl = fonts["flbl"]
    fwth = fonts["fwth"]
    falm = fonts["falm"]
    fsum = fonts["fsum"]

    y = base.TOP_SAFE_Y
    draw_weather_header(img, draw, y, weather, fwth)
    y += 38
    draw.line([(60, y), (base.SCREEN_W - 60, y)], fill=180, width=1)
    y += 14

    base.draw_centered(draw, y, now.strftime("%H:%M"), ft)
    y += 170

    base.draw_centered(draw, y, now.strftime("%Y年%m月%d日"), fd)
    y += 65

    weekday_s = "星期" + base.WEEKDAYS[now.weekday()]
    lunar_s = base.lunar_date_str(now.date())
    term_s = base.solar_term(now.date())
    right_s = f"{lunar_s}  {term_s}" if (lunar_s and term_s) else (lunar_s or term_s)
    line3 = f"{weekday_s}    {right_s}" if right_s else weekday_s
    base.draw_centered(draw, y, line3, fw, fill=60)
    y += 52

    draw.line([(60, y), (base.SCREEN_W - 60, y)], fill=160, width=1)
    y += 20

    y = base.draw_calendar(draw, y, now, fnum, fhdr, flbl)
    y += 8
    draw.line([(60, y), (base.SCREEN_W - 60, y)], fill=160, width=1)
    y += 14

    max_w = base.SCREEN_W - 60
    yi, ji = almanac.get("yi", []), almanac.get("ji", [])
    h_yi = base._almanac_height(draw, yi, falm, max_w)
    h_ji = base._almanac_height(draw, ji, falm, max_w)
    alm_h = h_yi + (8 + h_ji if h_yi and h_ji else h_ji)
    y_sum = base.SCREEN_H - base.TOP_SAFE_Y - 52
    y_alm = y + max(0, (y_sum - y - alm_h) // 2)
    y2 = base.draw_almanac_section(draw, y_alm, "宜", yi, falm, max_w)
    base.draw_almanac_section(draw, y2 + 8, "忌", ji, falm, max_w)

    base.draw_today_summary(draw, y_sum, now, fsum, max_w)

    if weather.get("warning"):
        base.draw_centered(draw, y + 4, weather["warning"], fwth, fill=40)

    img.save(out_path, compress_level=1)
    return img


def main():
    base.eips_msg("Icon clock starting...", "Please wait.")
    base.log("=== clock_icon_theme.py started ===")

    try:
        from PIL import Image  # noqa: F401
        base.log("Pillow OK")
    except ImportError:
        base.eips_msg("Installing Pillow...", "WiFi required.", "This may take 1-2 min.")
        base.log("Pillow not found, installing...")
        result = base.subprocess.run(
            ["/mnt/us/python3/bin/pip3", "install", "pillow"],
            capture_output=True, text=True
        )
        base.log(f"pip3: {result.stdout[-200:]} {result.stderr[-200:]}")
        if result.returncode != 0:
            base.eips_msg("Pillow install FAILED.", "Check WiFi & clock.log.")
            base.sys.exit(1)

    base._trim_log()
    base.load_holidays()
    weather = base.load_weather()
    last_slot = None
    tick = 0
    base.apply_backlight()
    base.prevent_sleep()

    while True:
        try:
            now = base.local_now()
            if tick % 5 == 0:
                base.apply_backlight()
                base.prevent_sleep()
            weather, last_slot = base.maybe_refresh_weather(now, last_slot)
            render(weather)
            base.display_image("/tmp/clock.png")
            tick += 1
        except Exception:
            base.log(f"icon theme loop error: {traceback.format_exc()}")
            time.sleep(10)

        now2 = base.local_now()
        if 0 <= now2.hour < 6:
            time.sleep(5 * 60)
        else:
            time.sleep(max(60 - now2.second, 1))


if __name__ == "__main__":
    main()
