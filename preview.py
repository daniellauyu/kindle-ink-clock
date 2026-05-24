#!/usr/bin/env python3
"""
本地预览工具 — 在 Mac 上渲染时钟 PNG，无需 Kindle。
用法：
  python3 preview.py
  python3 preview.py --time 14:32
  python3 preview.py --weather "深圳  晴  17°C~27°C" --lunar "丙午年四月初八"
  python3 preview.py --fetch      # 真实抓取 tianqi.com 一次
"""
import sys, os, subprocess, argparse

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

import clock
clock.FONT_PATH  = os.path.join(PROJECT_DIR, "fonts", "MapleMono-NF-CN-Bold.ttf")
clock.LOG_FILE   = "/tmp/kindle_clock_preview.log"
clock.DEBUG_MODE = False  # preview 时不走 DEBUG 逻辑

OUT = "/tmp/kindle_preview.png"

def main():
    parser = argparse.ArgumentParser(description="Kindle Ink Clock 本地预览")
    parser.add_argument("--weather", default="深圳  晴  17°C~27°C")
    parser.add_argument("--lunar",   default="丙午年四月初八")
    parser.add_argument("--sunrise", default="05:40")
    parser.add_argument("--sunset",  default="19:00")
    parser.add_argument("--warning", default="")
    parser.add_argument("--time",    default="", help="固定时间，如 14:32")
    parser.add_argument("--date",    default="", help="固定日期，如 2026-05-21")
    parser.add_argument("--fetch",   action="store_true",
                        help="真实抓取 tianqi.com（一次性，结果存入缓存）")
    parser.add_argument("--fetch-holidays", action="store_true",
                        help="真实抓取 iCloud 节假日 ICS 并打印结果")
    parser.add_argument("--fetch-almanac", action="store_true",
                        help="真实抓取今日老黄历宜忌")
    args = parser.parse_args()

    if args.date or args.time:
        base = clock.local_now()
        if args.date:
            y, mo, d = map(int, args.date.split("-"))
            base = base.replace(year=y, month=mo, day=d)
        if args.time:
            h, m = map(int, args.time.split(":"))
            base = base.replace(hour=h, minute=m, second=0)
        _fixed = base
        clock.local_now = lambda: _fixed

    if args.fetch_holidays:
        print("正在抓取 iCloud 节假日 ICS ...")
        hcache = clock.fetch_holidays(verbose=True)
        hols = hcache["holidays"]
        wdays = hcache.get("workday_overrides", [])
        print(f"  节假日: {len(hols)} 天")
        for k in sorted(hols)[:20]:
            print(f"    {k}: {hols[k]}")
        if len(hols) > 20:
            print(f"    ... 还有 {len(hols)-20} 条")
        print(f"  补班: {len(wdays)} 天")
        for k in sorted(wdays)[:10]:
            print(f"    {k}")

    if args.fetch:
        print("正在抓取 tianqi.com ...")
        weather = clock.fetch_weather(verbose=True)
        print(f"  天气: {weather['text']}")
        print(f"  日出: {weather['sunrise']}  日落: {weather['sunset']}")
    elif os.path.exists(clock.WEATHER_CACHE):
        weather = clock.load_weather()
        print(f"[cache] 使用缓存: {clock.WEATHER_CACHE}")
        print(f"  天气: {weather['text']}")
    else:
        weather = {
            "text":    args.weather,
            "lunar":   args.lunar,
            "sunrise": args.sunrise,
            "sunset":  args.sunset,
            "severe":  False,
            "warning": args.warning,
        }
        print("[mock] 使用模拟数据（无缓存，可先跑 --fetch）")

    if clock.load_holidays():
        print(f"[holidays] 已加载缓存: {clock.HOLIDAY_CACHE}")
    else:
        print("[holidays] 无缓存，使用硬编码数据（可先跑 --fetch-holidays）")

    if args.fetch_almanac:
        print("正在抓取老黄历 ...")
        alm = clock.fetch_almanac(verbose=True)
        print(f"  宜: {' '.join(alm.get('yi', []))}")
        print(f"  忌: {' '.join(alm.get('ji', []))}")
    else:
        alm = clock.load_almanac()
        if alm.get("yi") or alm.get("ji"):
            print(f"[almanac] 已加载缓存: {clock.ALMANAC_CACHE} ({alm.get('date','')})")
        else:
            print("[almanac] 无缓存（可先跑 --fetch-almanac）")

    target_date = clock.local_now().date()
    lunar = clock.lunar_date_str(target_date)
    term  = clock.solar_term(target_date)
    print(f"  农历: {lunar}  节气: {term or '无'}")

    clock.render(weather, out_path=OUT)
    print(f"已保存：{OUT}")
    subprocess.run(["open", OUT])

if __name__ == "__main__":
    main()
