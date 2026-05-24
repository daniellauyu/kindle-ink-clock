#!/usr/bin/env python3
"""
本地预览脚本 — 在 Mac 上渲染时钟 PNG，不需要 Kindle。
用法：python3 preview.py
     python3 preview.py --weather "深圳  28°C  多云" --icon rain --time "14:32"
"""
import sys, os, subprocess, datetime, argparse

# 让 preview.py 能 import clock.py 里的函数
sys.path.insert(0, os.path.dirname(__file__))

# 临时 patch：把 Kindle 专用路径换成本地路径
import clock as _clock_module
_clock_module.FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts/MapleMono-NF-CN-Bold.ttf")

from clock import render, local_now

OUT = "/tmp/kindle_preview.png"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weather", default="深圳  28°C  多云")
    parser.add_argument("--icon",    default="partly_cloudy",
                        choices=["sun","partly_cloudy","cloud","fog",
                                 "rain","shower","drizzle","snow","thunder"])
    parser.add_argument("--severe",  action="store_true")
    parser.add_argument("--warning", default="")
    parser.add_argument("--time",    default="",
                        help="固定时间，如 14:32（不填则用当前时间）")
    args = parser.parse_args()

    # 如果指定了固定时间，monkey-patch local_now
    if args.time:
        h, m = map(int, args.time.split(":"))
        fixed = local_now().replace(hour=h, minute=m, second=0)
        _clock_module.local_now = lambda: fixed

    weather = {
        "text":    args.weather,
        "icon":    args.icon,
        "severe":  args.severe,
        "warning": args.warning,
    }

    # patch eips → 保存到本地文件
    import subprocess as sp
    _orig_run = sp.run
    def _fake_run(cmd, **kw):
        if isinstance(cmd, list) and cmd[0] == "eips":
            return
        return _orig_run(cmd, **kw)
    sp.run = _fake_run

    # 渲染
    from PIL import Image
    import clock as clk
    now = clk.local_now()
    img = Image.new("L", (clk.SCREEN_W, clk.SCREEN_H), 255)
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(img)

    ft    = ImageFont.truetype(clk.FONT_PATH, 160)
    fd    = ImageFont.truetype(clk.FONT_PATH, 52)
    fw    = ImageFont.truetype(clk.FONT_PATH, 44)
    fc    = ImageFont.truetype(clk.FONT_PATH, 36)
    fs    = ImageFont.truetype(clk.FONT_PATH, 38)
    fwarn = ImageFont.truetype(clk.FONT_PATH, 28)

    y = 80
    clk.draw_centered(draw, y, now.strftime("%H:%M"), ft);            y += 185
    clk.draw_centered(draw, y, now.strftime("%Y年%m月%d日"), fd);     y += 68
    clk.draw_centered(draw, y, "星期"+clk.WEEKDAYS[now.weekday()], fw, fill=60); y += 72
    draw.line([(60,y),(clk.SCREEN_W-60,y)], fill=180, width=1);       y += 22
    y = clk.draw_calendar(draw, y, now, fc, fs)
    y += 12
    draw.line([(60,y),(clk.SCREEN_W-60,y)], fill=180, width=1);       y += 18

    wtext = weather["text"]
    wicon = weather["icon"]
    show_badge = weather["severe"] or bool(weather["warning"])
    icon_s = 22
    icon_cy = y + icon_s + 4
    text_y  = y + 4
    tb = draw.textbbox((0,0), wtext, font=fs)
    tw = tb[2]-tb[0]
    badge_w = (icon_s*2+8) if show_badge else 0
    total_w = badge_w + icon_s*2 + 12 + tw
    sx = (clk.SCREEN_W - total_w) // 2
    if show_badge:
        clk.draw_warning_badge(draw, sx+icon_s, icon_cy, icon_s)
        sx += icon_s*2+8
    clk.draw_weather_icon(draw, sx+icon_s, icon_cy, wicon, icon_s)
    draw.text((sx+icon_s*2+12, text_y), wtext, fill=60, font=fs)
    if weather["warning"]:
        y += icon_s*2+14
        clk.draw_centered(draw, y, weather["warning"], fwarn, fill=40)

    img.save(OUT)
    print(f"已保存：{OUT}")
    subprocess.run(["open", OUT])

if __name__ == "__main__":
    main()
