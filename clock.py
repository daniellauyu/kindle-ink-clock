#!/usr/bin/env python3
import subprocess, datetime, calendar, time, json, os, sys, traceback, math

LOG_FILE = "/mnt/us/extensions/clock/clock.log"

def local_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=8)

def eips_msg(line1, line2="", line3=""):
    subprocess.run(["eips", "-c"])
    time.sleep(0.5)
    if line1: subprocess.run(["eips", "5", "8",  line1])
    if line2: subprocess.run(["eips", "5", "10", line2])
    if line3: subprocess.run(["eips", "5", "12", line3])

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{local_now().strftime('%H:%M:%S')}] {msg}\n")

eips_msg("Clock starting...", "Please wait.")
log("=== clock.py started ===")

try:
    from PIL import Image, ImageDraw, ImageFont
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
        from PIL import Image, ImageDraw, ImageFont
        log("Pillow installed OK")
    except ImportError as e:
        eips_msg("Pillow import failed.", str(e)[:40])
        sys.exit(1)

LAT        = 22.5431
LON        = 114.0579
CITY_CN    = "深圳"
QWEATHER_KEY = ""
WEATHER_INTERVAL = 30
WEATHER_CACHE    = "/tmp/weather_cache.json"
SCREEN_W, SCREEN_H = 758, 1024
FONT_PATH  = "/mnt/us/fonts/MapleMono-NF-CN-Bold.ttf"
WEEKDAYS   = ["一", "二", "三", "四", "五", "六", "日"]

WMO_MAP = {
    0:("晴","sun"),1:("晴","sun"),2:("多云","partly_cloudy"),3:("阴","cloud"),
    45:("雾","fog"),48:("冻雾","fog"),
    51:("小毛雨","drizzle"),53:("中毛雨","drizzle"),55:("大毛雨","drizzle"),
    56:("小冻毛雨","drizzle"),57:("大冻毛雨","drizzle"),
    61:("小雨","rain"),63:("中雨","rain"),65:("大雨","rain"),
    66:("小冻雨","rain"),67:("大冻雨","rain"),
    71:("小雪","snow"),73:("中雪","snow"),75:("大雪","snow"),77:("米雪","snow"),
    80:("小阵雨","shower"),81:("中阵雨","shower"),82:("大阵雨","shower"),
    85:("小阵雪","snow"),86:("大阵雪","snow"),
    95:("雷阵雨","thunder"),96:("雷雨夹冰雹","thunder"),99:("强雷雨夹冰雹","thunder"),
}
SEVERE_KEYWORDS = {"暴雨","暴风雪","冰雹","强雷雨","大阵雨","大雨","大雪"}

def wifi_on():
    subprocess.run(["lipc-set-prop","com.lab126.wifid","enable","1"],capture_output=True)
    time.sleep(5)

def wifi_off():
    subprocess.run(["lipc-set-prop","com.lab126.wifid","enable","0"],capture_output=True)

def sync_time():
    subprocess.run(["ntpdate","-u","pool.ntp.org"],capture_output=True)

def fetch_weather():
    try:
        import urllib.request, ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        url = (f"https://api.open-meteo.com/v1/forecast"
               f"?latitude={LAT}&longitude={LON}"
               f"&current=temperature_2m,weather_code"
               f"&timezone=Asia%2FShanghai&forecast_days=1")
        with urllib.request.urlopen(url, timeout=10, context=ctx) as r:
            data = json.loads(r.read())
        cur  = data["current"]
        temp = round(cur["temperature_2m"])
        code = int(cur["weather_code"])
        desc_cn, icon_type = WMO_MAP.get(code, ("未知","sun"))
        warning = ""
        if QWEATHER_KEY:
            try:
                wurl = (f"https://devapi.qweather.com/v7/warning/now"
                        f"?location={LON},{LAT}&key={QWEATHER_KEY}")
                with urllib.request.urlopen(wurl, timeout=8, context=ctx) as wr:
                    wdata = json.loads(wr.read())
                if wdata.get("warning"):
                    w = wdata["warning"][0]
                    warning = f"[预警] {w.get('typeName','')} {w.get('level','')}级"
            except Exception as we:
                log(f"warning fetch failed: {we}")
        is_severe = any(kw in desc_cn for kw in SEVERE_KEYWORDS)
        cache = {"text":f"{CITY_CN}  {temp}°C  {desc_cn}","icon":icon_type,
                 "severe":is_severe,"warning":warning}
        with open(WEATHER_CACHE,"w") as f:
            json.dump(cache, f, ensure_ascii=False)
        log(f"weather OK: {cache['text']}")
        return cache
    except Exception as e:
        log(f"weather fetch failed: {e}")
        if os.path.exists(WEATHER_CACHE):
            try:
                return json.load(open(WEATHER_CACHE))
            except Exception:
                pass
        return {"text":"天气暂不可用","icon":"sun","severe":False,"warning":""}

def _cloud(draw,cx,cy,s):
    draw.ellipse([cx-s,cy-s//3,cx+s//2,cy+s//2],fill=160,outline=0,width=1)
    draw.ellipse([cx-s//2,cy-s*3//4,cx+s//5,cy+s//4],fill=160,outline=0,width=1)
    draw.ellipse([cx-s//5,cy-s//2,cx+s*2//3,cy+s//4],fill=160,outline=0,width=1)

def _sun(draw,cx,cy,s):
    r=s*10//22
    draw.ellipse([cx-r,cy-r,cx+r,cy+r],outline=0,width=2)
    for i in range(8):
        a=i*math.pi/4
        draw.line([int(cx+(r+3)*math.cos(a)),int(cy+(r+3)*math.sin(a)),
                   int(cx+(r+9)*math.cos(a)),int(cy+(r+9)*math.sin(a))],fill=0,width=2)

def _rain_drops(draw,cx,cy,s):
    for dx in [-s//2,0,s//2]:
        draw.line([cx+dx,cy,cx+dx-3,cy+s*3//4],fill=0,width=2)

def _snow_flakes(draw,cx,cy,s):
    for dx in [-s//2,0,s//2]:
        x,y=cx+dx,cy+s//4
        for a in [0,math.pi/3,math.pi*2/3]:
            draw.line([int(x-5*math.cos(a)),int(y-5*math.sin(a)),
                       int(x+5*math.cos(a)),int(y+5*math.sin(a))],fill=0,width=1)

def draw_weather_icon(draw,cx,cy,icon_type,s=22):
    if icon_type=="sun":
        _sun(draw,cx,cy,s)
    elif icon_type=="partly_cloudy":
        _sun(draw,cx+s//3,cy-s//3,s*14//22)
        _cloud(draw,cx-s//5,cy+s//5,s*16//22)
    elif icon_type=="cloud":
        _cloud(draw,cx,cy,s)
    elif icon_type=="fog":
        for dy in [-s//2,-s//6,s//6,s//2]:
            w=s-abs(dy)//2
            draw.line([cx-w,cy+dy,cx+w,cy+dy],fill=80,width=3)
    elif icon_type in ("rain","shower"):
        _cloud(draw,cx,cy-s//4,s)
        _rain_drops(draw,cx,cy+s//4,s)
    elif icon_type=="drizzle":
        _cloud(draw,cx,cy-s//4,s)
        for dx in [-s//3,s//3]:
            draw.line([cx+dx,cy+s//4,cx+dx-2,cy+s//2],fill=80,width=1)
    elif icon_type=="snow":
        _cloud(draw,cx,cy-s//4,s)
        _snow_flakes(draw,cx,cy+s//4,s)
    elif icon_type=="thunder":
        _cloud(draw,cx,cy-s//4,s)
        pts=[(cx+4,cy-s//4),(cx-4,cy+s//8),(cx+2,cy+s//8),(cx-6,cy+s*2//3)]
        draw.line(pts,fill=0,width=3)
    else:
        _sun(draw,cx,cy,s)

def draw_warning_badge(draw,cx,cy,s=18):
    h=int(s*1.73)
    pts=[(cx,cy-h*2//3),(cx-s,cy+h//3),(cx+s,cy+h//3)]
    draw.polygon(pts,outline=0,fill=40,width=2)
    draw.line([cx,cy-h//3,cx,cy+h//6],fill=255,width=3)
    draw.ellipse([cx-2,cy+h//4,cx+2,cy+h//3+2],fill=255)

def draw_centered(draw,y,text,font,fill=0):
    bbox=draw.textbbox((0,0),text,font=font)
    x=(SCREEN_W-(bbox[2]-bbox[0]))//2
    draw.text((x,y),text,fill=fill,font=font)
    return bbox[3]-bbox[1]

def draw_calendar(draw,top_y,now,font_cal,font_small):
    year,month,today=now.year,now.month,now.day
    cal=calendar.monthcalendar(year,month)
    draw_centered(draw,top_y,f"{year} 年 {month} 月",font_small)
    y=top_y+48
    draw_centered(draw,y,"  ".join(WEEKDAYS),font_cal,fill=80)
    y+=42
    cell_w=SCREEN_W//7
    for week in cal:
        x=0
        for day in week:
            if day!=0:
                ds=f"{day:2d}"
                bb=draw.textbbox((0,0),ds,font=font_cal)
                tx=x+(cell_w-(bb[2]-bb[0]))//2
                if day==today:
                    draw.rectangle([tx-6,y-3,tx+(bb[2]-bb[0])+6,y+(bb[3]-bb[1])+3],
                                   outline=0,width=2)
                draw.text((tx,y),ds,fill=0,font=font_cal)
            x+=cell_w
        y+=40
    return y

def render(weather):
    now=local_now()
    img=Image.new("L",(SCREEN_W,SCREEN_H),255)
    draw=ImageDraw.Draw(img)
    ft=ImageFont.truetype(FONT_PATH,160)
    fd=ImageFont.truetype(FONT_PATH,52)
    fw=ImageFont.truetype(FONT_PATH,44)
    fc=ImageFont.truetype(FONT_PATH,36)
    fs=ImageFont.truetype(FONT_PATH,38)
    fwarn=ImageFont.truetype(FONT_PATH,28)

    y=80
    draw_centered(draw,y,now.strftime("%H:%M"),ft)
    y+=185
    draw_centered(draw,y,now.strftime("%Y年%m月%d日"),fd)
    y+=68
    draw_centered(draw,y,"星期"+WEEKDAYS[now.weekday()],fw,fill=60)
    y+=72
    draw.line([(60,y),(SCREEN_W-60,y)],fill=180,width=1)
    y+=22
    y=draw_calendar(draw,y,now,fc,fs)
    y+=12
    draw.line([(60,y),(SCREEN_W-60,y)],fill=180,width=1)
    y+=18

    wtext=weather.get("text","天气暂不可用")
    wicon=weather.get("icon","sun")
    severe=weather.get("severe",False)
    warning=weather.get("warning","")
    show_badge=severe or bool(warning)
    icon_s=22
    icon_cy=y+icon_s+4
    text_y=y+4
    tb=draw.textbbox((0,0),wtext,font=fs)
    tw=tb[2]-tb[0]
    badge_w=(icon_s*2+8) if show_badge else 0
    total_w=badge_w+icon_s*2+12+tw
    sx=(SCREEN_W-total_w)//2
    if show_badge:
        draw_warning_badge(draw,sx+icon_s,icon_cy,icon_s)
        sx+=icon_s*2+8
    draw_weather_icon(draw,sx+icon_s,icon_cy,wicon,icon_s)
    draw.text((sx+icon_s*2+12,text_y),wtext,fill=60,font=fs)
    if warning:
        y+=icon_s*2+14
        draw_centered(draw,y,warning,fwarn,fill=40)

    img.save("/tmp/clock.png")
    subprocess.run(["eips","-g","/tmp/clock.png"])

def prevent_sleep():
    subprocess.run(["lipc-set-prop","com.lab126.powerd","preventScreenSaver","1"],
                   capture_output=True)

def main():
    weather={"text":"正在获取天气...","icon":"sun","severe":False,"warning":""}
    last_weather_min=-WEATHER_INTERVAL
    prevent_sleep()  # 启动时立即禁用屏保
    while True:
        try:
            now=local_now()
            elapsed=now.minute+now.hour*60
            if elapsed-last_weather_min>=WEATHER_INTERVAL or last_weather_min<0:
                wifi_on()
                sync_time()
                weather=fetch_weather()
                wifi_off()
                last_weather_min=elapsed
            render(weather)
            prevent_sleep()  # 每分钟刷新一次防锁屏标记
        except Exception as e:
            log(f"render error: {traceback.format_exc()}")
            eips_msg("Clock error:",str(e)[:40],"See clock.log")
            time.sleep(10)
        sleep_sec=60-local_now().second
        time.sleep(max(sleep_sec,1))

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        log(f"FATAL: {traceback.format_exc()}")
        eips_msg("Clock crashed:",str(e)[:40],"See clock.log")
