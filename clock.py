#!/usr/bin/env python3
"""
Kindle Ink Clock — 运行在越狱 Kindle 上的全屏 e-ink 桌面时钟
部署路径: /mnt/us/extensions/clock/clock.py
"""
import subprocess, datetime, calendar, time, json, os, sys, traceback, math, re

# ── 可配置项 ────────────────────────────────────────────
CITY_CN       = "深圳"
CITY_SLUG     = "shenzhen"
DEBUG_MODE    = False             # True: 本机调试时有缓存就不主动抓取
WEATHER_CACHE = "/tmp/weather_cache.json"
SCREEN_W      = 758
SCREEN_H      = 1024
TOP_SAFE_Y    = 34                # 避开 Kindle 顶部系统状态栏
FONT_PATH     = "/mnt/us/fonts/MapleMono-NF-CN-Bold.ttf"
LOG_FILE      = "/mnt/us/extensions/clock/clock.log"
WEEKDAYS         = ["一", "二", "三", "四", "五", "六", "日"]
REFRESH_HOURS    = {6, 12, 18}      # Kindle 端天气刷新整点（夜间不联网）
BACKLIGHT_PATH   = "/sys/class/backlight/max77696-bl/brightness"

# ── 农历（本地计算，无需联网） ───────────────────────────
_STEMS    = "甲乙丙丁戊己庚辛壬癸"
_BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
_ZODIACS  = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
_MONTH_NAMES = ["正","二","三","四","五","六","七","八","九","十","冬","腊"]
_SYNODIC  = 29.53059   # 朔望月平均天数

# 正月初一（春节）公历日期，覆盖 2015-2036
_SPRING = {
    2015:(2,19),2016:(2,8), 2017:(1,28),2018:(2,16),2019:(2,5),
    2020:(1,25),2021:(2,12),2022:(2,1), 2023:(1,22),2024:(2,10),
    2025:(1,29),2026:(2,17),2027:(2,6), 2028:(1,26),2029:(2,13),
    2030:(2,3), 2031:(1,23),2032:(2,11),2033:(1,31),2034:(2,19),
    2035:(2,8), 2036:(1,28),
}
# 闰月：该年闰在第几月之后（0=无闰月）
_LEAP = {
    2020:4, 2023:2, 2025:6, 2033:11,
}

# 精确月份天数（朔望近似会在年末累积 ±1 天误差，此表优先使用）
# 顺序与 months 列表一致：正月、二月、…、闰N月（若有）、…、腊月
_MONTH_SIZES = {
    2025: (30,29,30,29,29,30,29,29,30,30,30,30,29),
    #      正  二  三  四  五  六 闰六 七  八  九  十 冬  腊
}

# ── 节气（21世纪公式，精度 ±1 天） ──────────────────────
# (月份, C系数, 名称)
_SOLAR_TERMS = [
    (1,  5.4055, "小寒"), (1,  20.12,  "大寒"),
    (2,  3.87,   "立春"), (2,  18.73,  "雨水"),
    (3,  5.63,   "惊蛰"), (3,  20.646, "春分"),
    (4,  4.81,   "清明"), (4,  20.1,   "谷雨"),
    (5,  5.52,   "立夏"), (5,  21.04,  "小满"),
    (6,  5.678,  "芒种"), (6,  21.37,  "夏至"),
    (7,  7.108,  "小暑"), (7,  22.83,  "大暑"),
    (8,  7.5,    "立秋"), (8,  23.13,  "处暑"),
    (9,  7.646,  "白露"), (9,  23.042, "秋分"),
    (10, 8.318,  "寒露"), (10, 23.438, "霜降"),
    (11, 7.438,  "立冬"), (11, 22.36,  "小雪"),
    (12, 7.18,   "大雪"), (12, 21.94,  "冬至"),
]

def solar_term(gdate):
    """返回当天节气名称，无则返回空字符串。"""
    Y = gdate.year % 100
    for month, C, name in _SOLAR_TERMS:
        day = int(Y * 0.2422 + C) - int(Y / 4)
        if gdate.month == month and gdate.day == day:
            return name
    return ""

def _lunar_day_str(d):
    ones = ["","一","二","三","四","五","六","七","八","九","十"]
    if d <= 10: return "初" + ones[d]
    if d == 20: return "二十"
    if d == 30: return "三十"
    if d <= 19: return "十" + ones[d-10]
    return "廿" + ones[d-20]

def lunar_date_str(gdate):
    """给定公历日期，返回农历字符串，如 '丙午年四月初八'。"""
    year = gdate.year
    if year not in _SPRING:
        return ""
    sm, sd = _SPRING[year]
    sf = datetime.date(year, sm, sd)
    if gdate < sf:
        year -= 1
        if year not in _SPRING:
            return ""
        sm, sd = _SPRING[year]
        sf = datetime.date(year, sm, sd)

    days   = (gdate - sf).days
    leap_m = _LEAP.get(year, 0)

    if year in _MONTH_SIZES:
        # 使用精确月份天数，从春节累加朔日偏移
        sizes = _MONTH_SIZES[year]
        months, start, si = [], 0, 0
        for m in range(1, 13):
            months.append((m, False, start))
            start += sizes[si]; si += 1
            if m == leap_m:
                months.append((m, True, start))
                start += sizes[si]; si += 1
    else:
        # 朔望月近似（精度 ±1 天）
        months, idx = [], 0
        for m in range(1, 13):
            months.append((m, False, round(idx * _SYNODIC)))
            idx += 1
            if m == leap_m:
                months.append((m, True, round(idx * _SYNODIC)))
                idx += 1

    cur_m, cur_leap, cur_start = months[0]
    for m_num, is_leap, start in months:
        if start > days:
            break
        cur_m, cur_leap, cur_start = m_num, is_leap, start

    lday    = max(1, min(30, days - cur_start + 1))
    offset  = year - 1984
    year_s  = _STEMS[offset % 10] + _BRANCHES[offset % 12] + _ZODIACS[offset % 12] + "年"
    month_s = ("闰" if cur_leap else "") + _MONTH_NAMES[cur_m-1] + "月"
    return year_s + month_s + _lunar_day_str(lday)

# ── 大陆法定节假日（从 iCloud ICS 获取，下方为兜底数据） ──
HOLIDAY_CACHE   = "/tmp/holiday_cache.json"
HOLIDAY_ICS_URL = "https://calendars.icloud.com/holidays/cn_zh.ics/"
HOLIDAY_TTL_DAYS = 30          # 缓存有效期（天）

# 兜底硬编码（ICS 获取失败时使用）
HOLIDAYS: dict = {
    (2025,  1,  1): "元旦",
    (2025,  1, 28): "春节", (2025,  1, 29): "春节", (2025,  1, 30): "春节",
    (2025,  1, 31): "春节", (2025,  2,  1): "春节", (2025,  2,  2): "春节",
    (2025,  2,  3): "春节", (2025,  2,  4): "春节",
    (2025,  4,  4): "清明", (2025,  4,  5): "清明", (2025,  4,  6): "清明",
    (2025,  5,  1): "劳动", (2025,  5,  2): "劳动", (2025,  5,  3): "劳动",
    (2025,  5,  4): "劳动", (2025,  5,  5): "劳动",
    (2025,  5, 31): "端午", (2025,  6,  1): "端午", (2025,  6,  2): "端午",
    (2025, 10,  1): "国庆", (2025, 10,  2): "国庆", (2025, 10,  3): "国庆",
    (2025, 10,  4): "国庆", (2025, 10,  5): "国庆", (2025, 10,  6): "国庆",
    (2025, 10,  7): "国庆", (2025, 10,  8): "国庆",
    (2026,  1,  1): "元旦",
    (2026,  2, 17): "春节", (2026,  2, 18): "春节", (2026,  2, 19): "春节",
    (2026,  2, 20): "春节", (2026,  2, 21): "春节", (2026,  2, 22): "春节",
    (2026,  2, 23): "春节",
    (2026,  4,  4): "清明", (2026,  4,  5): "清明", (2026,  4,  6): "清明",
    (2026,  5,  1): "劳动", (2026,  5,  2): "劳动", (2026,  5,  3): "劳动",
    (2026,  5,  4): "劳动", (2026,  5,  5): "劳动",
    (2026,  6, 19): "端午", (2026,  6, 20): "端午", (2026,  6, 21): "端午",
    (2026,  9, 25): "中秋", (2026,  9, 26): "中秋", (2026,  9, 27): "中秋",
    (2026, 10,  1): "国庆", (2026, 10,  2): "国庆", (2026, 10,  3): "国庆",
    (2026, 10,  4): "国庆", (2026, 10,  5): "国庆", (2026, 10,  6): "国庆",
    (2026, 10,  7): "国庆",
}
WORKDAY_OVERRIDES: set = {
    (2025,  1, 26), (2025,  2,  8),
    (2025,  4, 27),
    (2025,  9, 28), (2025, 10, 11),
    (2026,  2, 14), (2026,  2, 28),
    (2026,  9, 19), (2026, 10, 10),
}

def fetch_holidays(verbose=False):
    """下载并解析 iCloud 节假日 ICS，返回解析后的缓存 dict。"""
    import urllib.request, ssl, gzip as _gzip

    def _p(msg):
        if verbose: print(msg)
        log(msg)

    _p(f"[holidays] GET {HOLIDAY_ICS_URL}")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    req = urllib.request.Request(HOLIDAY_ICS_URL,
                                 headers={"Accept-Encoding": "gzip",
                                          "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        raw = r.read()
    try:
        ics = _gzip.decompress(raw).decode("utf-8")
    except Exception:
        ics = raw.decode("utf-8", errors="replace")
    _p(f"[holidays] {len(ics)} chars")

    hols, wdays = {}, []
    for vevent in re.findall(r'BEGIN:VEVENT([\s\S]*?)END:VEVENT', ics):
        sm = re.search(r'SUMMARY[^:]*:(.*)',      vevent)
        dm = re.search(r'DTSTART[^:]*:(\d{8})',   vevent)
        em = re.search(r'DTEND[^:]*:(\d{8})',     vevent)
        xm = re.search(r'X-APPLE-SPECIAL-DAY:(.*)', vevent)
        if not (dm and xm):
            continue
        special  = xm.group(1).strip()
        name     = re.sub(r'[（(][休班][）)]', '',
                          sm.group(1) if sm else "").strip()
        s_str    = dm.group(1)
        e_str    = em.group(1) if em else s_str
        start    = datetime.date(int(s_str[:4]), int(s_str[4:6]), int(s_str[6:]))
        end      = datetime.date(int(e_str[:4]), int(e_str[4:6]), int(e_str[6:]))
        if end == start:
            end  = start + datetime.timedelta(days=1)

        d = start
        while d < end:
            key = f"{d.year},{d.month},{d.day}"
            if special == "WORK-HOLIDAY":
                hols[key] = name
            elif special == "ALTERNATE-WORKDAY":
                wdays.append(key)
            d += datetime.timedelta(days=1)

    _p(f"[holidays] {len(hols)} holiday days, {len(wdays)} workday overrides")
    cache = {"holidays": hols, "workday_overrides": wdays,
             "fetched": str(local_now().date())}
    with open(HOLIDAY_CACHE, "w") as f:
        json.dump(cache, f, ensure_ascii=False)
    return cache

def _apply_holiday_cache(cache):
    global HOLIDAYS, WORKDAY_OVERRIDES
    HOLIDAYS = {
        tuple(int(x) for x in k.split(",")): v
        for k, v in cache["holidays"].items()
    }
    WORKDAY_OVERRIDES = {
        tuple(int(x) for x in k.split(","))
        for k in cache.get("workday_overrides", [])
    }

def load_holidays():
    """从缓存加载节假日数据（不联网）。"""
    if os.path.exists(HOLIDAY_CACHE):
        try:
            with open(HOLIDAY_CACHE) as f:
                _apply_holiday_cache(json.load(f))
            return True
        except Exception:
            pass
    return False

def maybe_refresh_holidays():
    """缓存超过 TTL 则重新抓取（调用前 WiFi 应已开启）。"""
    today = local_now().date()
    if os.path.exists(HOLIDAY_CACHE):
        try:
            with open(HOLIDAY_CACHE) as f:
                cache = json.load(f)
            fetched = datetime.date.fromisoformat(
                cache.get("fetched", "2000-01-01"))
            if (today - fetched).days < HOLIDAY_TTL_DAYS:
                _apply_holiday_cache(cache)
                return
        except Exception:
            pass
    try:
        _apply_holiday_cache(fetch_holidays())
    except Exception as e:
        log(f"holiday refresh failed: {e}")

# ── 老黄历（每日抓取一次） ───────────────────────────────
ALMANAC_CACHE = "/tmp/almanac_cache.json"
ALMANAC_BASE  = "https://wannianli.tianqi.com/laohuangli/"

def fetch_almanac(target_date=None, verbose=False):
    """抓取并解析老黄历宜忌，保存缓存并返回 dict。"""
    import urllib.request, ssl

    if target_date is None:
        target_date = local_now().date()

    def _p(msg):
        if verbose: print(msg)
        log(msg)

    url = ALMANAC_BASE + target_date.strftime("%Y%m%d") + "/"
    _p(f"[almanac] GET {url}")
    req = urllib.request.Request(url, headers={
        "User-Agent":      ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"),
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "identity",
        "Referer":         "https://wannianli.tianqi.com/",
    })
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE

    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        html = r.read().decode("utf-8", errors="replace")
    _p(f"[almanac] {len(html)} bytes")

    yi, ji = [], []
    for tag, block in re.findall(r'(<ul[^>]*yi_ji_right[^>]*>)([\s\S]*?)</ul>', html):
        items = re.findall(r'<li>([^<]+)</li>', block)
        if 'class="yi"' in tag or 'class="yi"' in block:
            yi = items
        elif 'class="ji"' in tag or 'class="ji"' in block:
            ji = items

    _p(f"[almanac] 宜:{len(yi)} 忌:{len(ji)}")
    cache = {"date": str(target_date), "yi": yi, "ji": ji}
    with open(ALMANAC_CACHE, "w") as f:
        json.dump(cache, f, ensure_ascii=False)
    return cache

_almanac_mem = {"date": "", "yi": [], "ji": []}

def load_almanac():
    global _almanac_mem
    today = str(local_now().date())
    if _almanac_mem["date"] == today:
        return _almanac_mem
    if os.path.exists(ALMANAC_CACHE):
        try:
            with open(ALMANAC_CACHE) as f:
                data = json.load(f)
            if isinstance(data, dict):
                _almanac_mem = data
                return _almanac_mem
        except Exception:
            pass
    return _almanac_mem

def maybe_refresh_almanac():
    """日期变化时重新抓取（调用前 WiFi 已开启）。"""
    today = str(local_now().date())
    if load_almanac().get("date") == today:
        return
    try:
        fetch_almanac()
        _almanac_mem.clear()   # 强制下次 load_almanac 重读文件
        _almanac_mem.update({"date": "", "yi": [], "ji": []})
    except Exception as e:
        log(f"almanac refresh failed: {e}")

# ── 工具 ────────────────────────────────────────────────
def local_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=8)

def log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{local_now().strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass

def _trim_log(max_lines=200):
    try:
        if not os.path.exists(LOG_FILE):
            return
        with open(LOG_FILE) as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            with open(LOG_FILE, "w") as f:
                f.writelines(lines[-max_lines:])
    except Exception:
        pass

def eips_msg(line1, line2="", line3=""):
    subprocess.run(["eips", "-c"])
    time.sleep(0.5)
    if line1: subprocess.run(["eips", "5", "8",  line1])
    if line2: subprocess.run(["eips", "5", "10", line2])
    if line3: subprocess.run(["eips", "5", "12", line3])

def display_image(path):
    subprocess.run(["eips", "-g", path])

# ── WiFi / NTP / 防锁屏 ─────────────────────────────────
def wifi_on():
    subprocess.run(["lipc-set-prop", "com.lab126.wifid", "enable", "1"],
                   capture_output=True)
    time.sleep(3)

def wifi_off():
    subprocess.run(["lipc-set-prop", "com.lab126.wifid", "enable", "0"],
                   capture_output=True)

def sync_time():
    subprocess.run(["ntpdate", "-u", "pool.ntp.org"], capture_output=True)

def prevent_sleep():
    subprocess.run(["lipc-set-prop", "com.lab126.powerd", "preventScreenSaver", "1"],
                   capture_output=True)

def apply_backlight():
    """全天关闭背光，e-ink 无需背光即可阅读。"""
    try:
        with open(BACKLIGHT_PATH, "w") as f:
            f.write("0")
    except Exception as e:
        log(f"backlight off failed: {e}")

# ── 天气（抓取 tianqi.com） ──────────────────────────────
def _current_slot(now):
    """返回当前时刻所属的刷新档位 (date, hour)，hour ∈ REFRESH_HOURS。"""
    for h in sorted(REFRESH_HOURS, reverse=True):
        if now.hour >= h:
            return (now.date(), h)
    return (now.date() - datetime.timedelta(days=1), max(REFRESH_HOURS))

def fetch_weather(verbose=False):
    import urllib.request, ssl

    def _print(msg):
        if verbose:
            print(msg)
        log(msg)

    url = f"https://www.tianqi.com/{CITY_SLUG}/"
    _print(f"[fetch] GET {url}")
    req = urllib.request.Request(url, headers={
        "User-Agent":      ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"),
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "identity",
        "Referer":         "https://www.tianqi.com/",
        "Connection":      "close",
    })
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE

    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        html = r.read().decode("utf-8", errors="replace")

    _print(f"[fetch] response {len(html)} bytes")
    if len(html) < 500:
        raise ValueError(f"response too short ({len(html)} bytes), possible block")

    # ── 天气描述 + 温度 ──────────────────────────────────
    weather_text = f"{CITY_CN}  天气暂不可用"
    m = re.search(r'<dd[^>]*class=["\']weather["\'][^>]*>([\s\S]*?)</dd>', html)
    if m:
        block = m.group(1)
        _print(f"[parse] weather block: {block[:200]!r}")
        spans = re.findall(r'<span[^>]*><b[^>]*>(.*?)</b>(.*?)</span>', block, re.DOTALL)
        _print(f"[parse] spans found: {spans}")
        if spans:
            desc = re.sub(r'<[^>]+>', '', spans[0][0]).strip()
            rest = re.sub(r'<[^>]+>', '', spans[0][1]).strip()
            temp = rest
            if len(spans) > 1:
                t2 = re.sub(r'<[^>]+>', '',
                            spans[1][0] + spans[1][1]).strip()
                if t2:
                    temp = t2
            parts = [p for p in [desc, temp] if p]
            if parts:
                weather_text = f"{CITY_CN}  {'  '.join(parts)}"
    else:
        _print("[parse] weather block NOT found — regex miss, site may have changed")

    _print(f"[parse] weather_text = {weather_text!r}")

    # ── 日出 / 日落 ──────────────────────────────────────
    sunrise, sunset = "", ""
    m2 = re.search(r'日出[：:]\s*([\d:]+)\s*<br\s*/?>\s*日落[：:]\s*([\d:]+)', html)
    if m2:
        sunrise = m2.group(1).strip()
        sunset  = m2.group(2).strip()
        _print(f"[parse] sunrise={sunrise!r} sunset={sunset!r}")
    else:
        _print("[parse] sunrise/sunset NOT found")

    cache = {
        "text":    weather_text,
        "sunrise": sunrise,
        "sunset":  sunset,
        "severe":  False,
        "warning": "",
    }
    with open(WEATHER_CACHE, "w") as f:
        json.dump(cache, f, ensure_ascii=False)
    _print(f"[fetch] cache written to {WEATHER_CACHE}")
    log(f"weather OK: {weather_text!r}  ↑{sunrise} ↓{sunset}")
    return cache

def load_weather():
    default = {"text": f"{CITY_CN}  天气暂不可用", "sunrise": "",
               "sunset": "", "severe": False, "warning": ""}
    if os.path.exists(WEATHER_CACHE):
        try:
            with open(WEATHER_CACHE) as f:
                data = json.load(f)
            if isinstance(data, dict):
                merged = default.copy()
                merged.update(data)
                return merged
        except Exception:
            pass
    return default

def maybe_refresh_weather(now, last_slot):
    slot = _current_slot(now)
    if DEBUG_MODE and os.path.exists(WEATHER_CACHE):
        return load_weather(), slot
    if last_slot == slot:
        return load_weather(), last_slot

    wifi_on()
    sync_time()

    ok = False
    try:
        w = fetch_weather()
        ok = True
    except Exception as e:
        log(f"weather error: {e}")

    try:
        maybe_refresh_holidays()
    except Exception as e:
        log(f"holiday refresh error: {e}")

    try:
        maybe_refresh_almanac()
    except Exception as e:
        log(f"almanac refresh error: {e}")

    wifi_off()
    # 天气失败时不推进 slot，下次循环继续重试
    return load_weather(), (slot if ok else last_slot)

# ── 老黄历排版 ──────────────────────────────────────────
def _text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1], bb

def _draw_round_rect(draw, box, radius, outline=0, fill=255, width=1):
    """兼容旧版 Pillow 的圆角矩形绘制。"""
    try:
        draw.rounded_rectangle(box, radius=radius, outline=outline,
                               fill=fill, width=width)
        return
    except AttributeError:
        pass

    x1, y1, x2, y2 = box
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    draw.pieslice([x1, y1, x1 + radius * 2, y1 + radius * 2],
                  180, 270, fill=fill)
    draw.pieslice([x2 - radius * 2, y1, x2, y1 + radius * 2],
                  270, 360, fill=fill)
    draw.pieslice([x1, y2 - radius * 2, x1 + radius * 2, y2],
                  90, 180, fill=fill)
    draw.pieslice([x2 - radius * 2, y2 - radius * 2, x2, y2],
                  0, 90, fill=fill)
    draw.arc([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270,
             fill=outline, width=width)
    draw.arc([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360,
             fill=outline, width=width)
    draw.arc([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180,
             fill=outline, width=width)
    draw.arc([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90,
             fill=outline, width=width)
    draw.line([x1 + radius, y1, x2 - radius, y1], fill=outline, width=width)
    draw.line([x1 + radius, y2, x2 - radius, y2], fill=outline, width=width)
    draw.line([x1, y1 + radius, x1, y2 - radius], fill=outline, width=width)
    draw.line([x2, y1 + radius, x2, y2 - radius], fill=outline, width=width)

def draw_almanac_section(draw, y, title, items, font, max_w):
    """绘制一组老黄历标签，全部项目按宽度自动换行。"""
    if not items:
        return y

    left_x = 30
    right_x = left_x + max_w
    marker = 44
    gap = 7
    row_gap = 10
    pill_h = 34
    pill_pad_x = 12
    tag_x0 = left_x + marker + 14
    rows = []
    row = []
    row_w = 0
    for item in items:
        tw, th, tb = _text_size(draw, item, font)
        pill_w = tw + pill_pad_x * 2
        next_w = pill_w if not row else row_w + gap + pill_w
        if row and tag_x0 + next_w > right_x:
            rows.append(row)
            row = []
            row_w = 0
        row.append((item, pill_w, th, tb))
        row_w = pill_w if row_w == 0 else row_w + gap + pill_w
    if row:
        rows.append(row)
    rows = rows[:2]  # 最多显示 2 行

    block_h = len(rows) * pill_h + max(0, len(rows) - 1) * row_gap
    marker_y = y + max(0, (block_h - marker) // 2)
    draw.ellipse([left_x, marker_y, left_x + marker, marker_y + marker],
                 outline=0, width=2)
    tw, th, tb = _text_size(draw, title, font)
    draw.text((left_x + (marker - tw) // 2 - tb[0],
               marker_y + (marker - th) // 2 - tb[1]),
              title, fill=0, font=font)

    row_y = y
    for row in rows:
        x = tag_x0
        for item, pill_w, th, tb in row:
            _draw_round_rect(draw, [x, row_y, x + pill_w, row_y + pill_h],
                             radius=pill_h // 2, outline=0, fill=255, width=1)
            draw.text((x + pill_pad_x - tb[0],
                       row_y + (pill_h - th) // 2 - tb[1]),
                      item, fill=40, font=font)
            x += pill_w + gap

        row_y += pill_h + row_gap

    return y + block_h + 12

def _almanac_height(draw, items, font, max_w):
    """预计算一组黄历标签的高度，与 draw_almanac_section 逻辑一致。"""
    if not items:
        return 0
    pill_h, pill_pad_x, gap, row_gap = 34, 12, 7, 10
    tag_x0 = 30 + 44 + 14
    right_x = 30 + max_w
    rows, row, row_w = [], [], 0
    for item in items:
        tw, th, tb = _text_size(draw, item, font)
        pill_w = tw + pill_pad_x * 2
        next_w = pill_w if not row else row_w + gap + pill_w
        if row and tag_x0 + next_w > right_x:
            rows.append(row); row = []; row_w = 0
        row.append((item, pill_w, th, tb))
        row_w = pill_w if row_w == 0 else row_w + gap + pill_w
    if row:
        rows.append(row)
    rows = rows[:2]
    block_h = len(rows) * pill_h + max(0, len(rows) - 1) * row_gap
    return block_h + 12

def _next_holiday_summary(gdate):
    future = []
    for key, name in HOLIDAYS.items():
        if key in WORKDAY_OVERRIDES:
            continue
        hdate = datetime.date(*key)
        if hdate == gdate:
            return name
        if hdate > gdate:
            future.append((hdate, name))

    if not future:
        return ""

    hdate, name = min(future, key=lambda x: x[0])
    return f"{name}还有{(hdate - gdate).days}天"

def draw_today_summary(draw, y, now, font, max_w):
    gdate = now.date()
    parts = [
        f"今年第{gdate.timetuple().tm_yday}天",
        f"第{gdate.isocalendar().week}周",
    ]
    holiday = _next_holiday_summary(gdate)
    if holiday:
        parts.append(holiday)

    text = "   ".join(parts)
    x = 30
    h = 52
    _draw_round_rect(draw, [x, y, x + max_w, y + h],
                     radius=6, outline=160, fill=255, width=1)
    tw, th, tb = _text_size(draw, text, font)
    draw.text((x + (max_w - tw) // 2 - tb[0],
               y + (h - th) // 2 - tb[1]),
              text, fill=60, font=font)
    return y + h

# ── 日历绘制 ────────────────────────────────────────────
def draw_centered(draw, y, text, font, fill=0):
    bbox = draw.textbbox((0, 0), text, font=font)
    # 减去 bbox[0] 使字形视觉中心对齐屏幕中心
    x = (SCREEN_W - (bbox[2] - bbox[0])) // 2 - bbox[0]
    draw.text((x, y), text, fill=fill, font=font)
    return bbox[3] - bbox[1]

def draw_calendar(draw, top_y, now, font_num, font_hdr, font_lbl):
    year, month, today = now.year, now.month, now.day
    cal    = calendar.monthcalendar(year, month)
    cell_w = SCREEN_W // 7
    cell_h = 56   # 日期数字 + 下方标签行

    # 星期表头
    y = top_y
    for i, wd in enumerate(WEEKDAYS):
        bb = draw.textbbox((0, 0), wd, font=font_hdr)
        tx = i * cell_w + (cell_w - (bb[2]-bb[0])) // 2 - bb[0]
        draw.text((tx, y), wd, fill=80, font=font_hdr)
    y += 36

    for week in cal:
        for i, day in enumerate(week):
            if day == 0:
                continue
            key        = (year, month, day)
            is_today   = (day == today)
            is_holiday = (key in HOLIDAYS) and (key not in WORKDAY_OVERRIDES)
            is_workday = key in WORKDAY_OVERRIDES
            hol_name   = HOLIDAYS.get(key, "")
            term       = solar_term(datetime.date(year, month, day))

            ds = str(day)
            bb = draw.textbbox((0, 0), ds, font=font_num)
            tw = bb[2] - bb[0]
            tx = i * cell_w + (cell_w - tw) // 2 - bb[0]

            gl = tx + bb[0]; gt = y + bb[1]
            gr = tx + bb[2]; gb = y + bb[3]
            pad = 4

            if is_today:
                draw.rectangle([gl-pad, gt-pad, gr+pad, gb+pad], fill=0)
            elif is_holiday:
                draw.rectangle([gl-pad, gt-pad, gr+pad, gb+pad], fill=210)

            draw.text((tx, y), ds, fill=255 if is_today else 0, font=font_num)

            # 标签行：节假日名 > 补班"班" > 节气
            if is_holiday and hol_name:
                label, fill = hol_name, 60
            elif is_workday:
                label, fill = "班", 80
            elif term:
                label, fill = term, 100
            else:
                label = ""

            if label:
                lbb = draw.textbbox((0, 0), label, font=font_lbl)
                lw  = lbb[2] - lbb[0]
                lx  = i * cell_w + (cell_w - lw) // 2 - lbb[0]
                ly  = y + bb[3] + 3
                draw.text((lx, ly), label, fill=fill, font=font_lbl)

        y += cell_h

    return y

# ── 字体缓存（进程内只加载一次，避免每分钟重复读 TTF） ────────
_FONTS = {}

def _load_fonts():
    if not _FONTS:
        from PIL import ImageFont
        _FONTS.update({
            'ft':   ImageFont.truetype(FONT_PATH, 155),
            'fd':   ImageFont.truetype(FONT_PATH, 50),
            'fw':   ImageFont.truetype(FONT_PATH, 36),
            'fnum': ImageFont.truetype(FONT_PATH, 34),
            'fhdr': ImageFont.truetype(FONT_PATH, 30),
            'flbl': ImageFont.truetype(FONT_PATH, 16),
            'fwth': ImageFont.truetype(FONT_PATH, 28),
            'falm': ImageFont.truetype(FONT_PATH, 22),
            'fsum': ImageFont.truetype(FONT_PATH, 28),
        })
    return _FONTS

# ── 渲染 ────────────────────────────────────────────────
def render(weather, out_path="/tmp/clock.png"):
    from PIL import Image, ImageDraw

    now     = local_now()
    almanac = load_almanac()
    img     = Image.new("L", (SCREEN_W, SCREEN_H), 255)
    draw    = ImageDraw.Draw(img)

    fonts = _load_fonts()
    ft   = fonts['ft']
    fd   = fonts['fd']
    fw   = fonts['fw']
    fnum = fonts['fnum']
    fhdr = fonts['fhdr']
    flbl = fonts['flbl']
    fwth = fonts['fwth']
    falm = fonts['falm']
    fsum = fonts['fsum']

    # ── 顶部天气（小字）─────────────────────────────────
    y = TOP_SAFE_Y
    wtext    = weather.get("text", f"{CITY_CN}  天气暂不可用")
    sr, ss   = weather.get("sunrise", ""), weather.get("sunset", "")
    top_line = f"{wtext}    ↑{sr}  ↓{ss}" if (sr and ss) else wtext
    draw_centered(draw, y, top_line, fwth, fill=80)
    y += 38
    draw.line([(60, y), (SCREEN_W-60, y)], fill=180, width=1)
    y += 14

    # ── 时间 ─────────────────────────────────────────────
    draw_centered(draw, y, now.strftime("%H:%M"), ft);                    y += 170

    # ── 日期 ─────────────────────────────────────────────
    draw_centered(draw, y, now.strftime("%Y年%m月%d日"), fd);             y += 65

    # ── 星期 + 农历 + 节气 ───────────────────────────────
    weekday_s = "星期" + WEEKDAYS[now.weekday()]
    lunar_s   = lunar_date_str(now.date())
    term_s    = solar_term(now.date())
    right_s   = f"{lunar_s}  {term_s}" if (lunar_s and term_s) else (lunar_s or term_s)
    line3     = f"{weekday_s}    {right_s}" if right_s else weekday_s
    draw_centered(draw, y, line3, fw, fill=60);                           y += 52

    draw.line([(60, y), (SCREEN_W-60, y)], fill=160, width=1);           y += 20

    # ── 日历 ─────────────────────────────────────────────
    y = draw_calendar(draw, y, now, fnum, fhdr, flbl);                   y += 8
    draw.line([(60, y), (SCREEN_W-60, y)], fill=160, width=1);           y += 14

    # ── 老黄历：在日历分隔线与今日摘要之间垂直居中 ──────────
    max_w  = SCREEN_W - 60
    yi, ji = almanac.get("yi", []), almanac.get("ji", [])
    h_yi   = _almanac_height(draw, yi, falm, max_w)
    h_ji   = _almanac_height(draw, ji, falm, max_w)
    alm_h  = h_yi + (8 + h_ji if h_yi and h_ji else h_ji)
    y_sum  = SCREEN_H - TOP_SAFE_Y - 52
    y_alm  = y + max(0, (y_sum - y - alm_h) // 2)
    y2     = draw_almanac_section(draw, y_alm, "宜", yi, falm, max_w)
    draw_almanac_section(draw, y2 + (8 if yi else 0), "忌", ji, falm, max_w)

    # ── 今日摘要：底部距屏幕边距与顶部天气一致 ──────────────
    draw_today_summary(draw, y_sum, now, fsum, max_w)

    if weather.get("warning"):
        draw_centered(draw, y_sum - 38, weather["warning"], fwth, fill=40)

    img.save(out_path, compress_level=1)
    return img

# ── 主循环 ───────────────────────────────────────────────
def main():
    eips_msg("Clock starting...", "Please wait.")
    log("=== clock.py started ===")

    try:
        from PIL import Image
        log("Pillow OK")
    except ImportError:
        eips_msg("Installing Pillow...", "WiFi required.", "This may take 1-2 min.")
        log("Pillow not found, installing...")
        result = subprocess.run(
            ["/mnt/us/python3/bin/pip3", "install", "pillow"],
            capture_output=True, text=True
        )
        log(f"pip3: {result.stdout[-200:]} {result.stderr[-200:]}")
        if result.returncode != 0:
            eips_msg("Pillow install FAILED.", "Check WiFi & clock.log.")
            sys.exit(1)
        try:
            from PIL import Image
            log("Pillow installed OK")
        except ImportError as e:
            eips_msg("Pillow import failed.", str(e)[:40])
            sys.exit(1)

    _trim_log()
    load_holidays()
    weather   = load_weather()
    last_slot = _current_slot(local_now())
    tick      = 0
    apply_backlight()
    prevent_sleep()

    while True:
        try:
            now = local_now()
            # 背光和防锁屏每 5 分钟维持一次，减少 subprocess 和 flash 写入
            if tick % 5 == 0:
                apply_backlight()
                prevent_sleep()
            weather, last_slot = maybe_refresh_weather(now, last_slot)
            render(weather)
            display_image("/tmp/clock.png")
        except Exception:
            log(f"loop error: {traceback.format_exc()}")
            time.sleep(10)

        tick += 1

        now2 = local_now()
        if 0 <= now2.hour < 6:
            time.sleep(5 * 60)   # 夜间 5 分钟刷一次，减少 eips 和 CPU 唤醒
        else:
            time.sleep(max(60 - now2.second, 1))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FATAL: {traceback.format_exc()}")
        eips_msg("Clock crashed:", str(e)[:40], "See clock.log")
