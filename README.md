# Kindle Ink Clock

将吃灰的 Kindle Paperwhite 2 改造为全屏 e-ink 桌面时钟。

![预览](docs/preview.png)

## 功能

- 大号时间显示（HH:MM）
- 顶部小字天气 + 日出/日落
- 日期 + 星期 + 农历（本地计算，无需联网）+ 当日节气
- 本月日历（今天加框、节假日灰底显示名称、节气小字标注、补班标"班"）
- 底部老黄历宜/忌
- 每 6 小时联网同步天气 + NTP 校时，天气刷新同步更新老黄历（每日一次）
- 法定节假日从 iCloud ICS 订阅获取，30 天缓存一次
- 防锁屏，持续运行

## 界面布局

```
深圳  阴  27~32℃  ↑05:40  ↓19:00    ← 天气（小字）
─────────────────────────────────
            14:32                    ← 时间（大字）
         2026年5月24日
      星期日  丙午年四月初八
─────────────────────────────────
   一   二   三   四   五   六   日
              小满  5   6   7   8
   9   10   11   12   13   14  [15]   ← 今天加框
  16   17   18   19   20   21   22
  春节 春节 春节 春节 春节 春节 春节   ← 节假日灰底+名称
  23   24   25   26   27   28
  春节                        班
─────────────────────────────────
宜  安葬  理发  破土  祭祀  解除  沐浴
   扫舍  入殓
忌  搬家  结婚  入宅  领证  出行  作灶
   旅游  赴任
```

## 适用设备

已在 **Kindle Paperwhite 2（KPW2，固件 5.12.2.2）** 上验证。
理论上适用于已越狱、安装了 Python 3.9 的其他 Kindle 型号。

## 数据来源

| 数据 | 来源 | 刷新频率 |
|------|------|---------|
| 天气 | [tianqi.com](https://www.tianqi.com/) HTML 抓取 | 每天 4 次（0/6/12/18 时） |
| 农历 | 本地算法（春节查表 + 朔望近似） | 无需联网 |
| 节气 | 本地公式（21 世纪精度 ±1 天） | 无需联网 |
| 法定节假日 | [iCloud 中国节假日 ICS](https://calendars.icloud.com/holidays/cn_zh.ics/) | 30 天一次 |
| 老黄历宜/忌 | [wannianli.tianqi.com](https://wannianli.tianqi.com/) HTML 抓取 | 每天一次 |

## 依赖

| 依赖 | 说明 |
|------|------|
| Python 3.9 | 通过 KUAL + MRPI 安装（NiLuJe 构建） |
| Pillow | 首次启动自动联网安装 |
| 支持中文的 TTF 字体 | 放入 `fonts/` 目录，推荐 MapleMono NF CN |

## 快速开始

### 1. 越狱 Kindle

参考 [WatchThis 越狱教程](https://www.mobileread.com/forums/showthread.php?t=346037)，安装 KUAL 和 Python3。

### 2. 配置

编辑 `clock.py` 顶部的可配置项：

```python
CITY_CN      = "深圳"     # 显示城市名
CITY_SLUG    = "shenzhen" # tianqi.com 城市路径
DEBUG_MODE   = True        # True: 有缓存就不重新抓取（调试用）
FONT_PATH    = "/mnt/us/fonts/MapleMono-NF-CN-Bold.ttf"
REFRESH_HOURS = {0, 6, 12, 18}  # 每天天气刷新时刻
```

> 部署到 Kindle 前将 `DEBUG_MODE` 改为 `False`。

### 3. 本地预览（Mac）

```bash
# 安装依赖
pip3 install pillow

# 预览当前时间（使用缓存数据，无缓存显示模拟数据）
python3 preview.py

# 抓取真实天气并预览
python3 preview.py --fetch

# 抓取节假日 ICS 并预览
python3 preview.py --fetch-holidays

# 抓取老黄历并预览
python3 preview.py --fetch-almanac

# 预览指定日期（测试节假日/节气显示）
python3 preview.py --date 2026-02-16
python3 preview.py --time 14:32
```

### 4. 部署到 Kindle

```bash
# 先在 Kindle 搜索栏输入 ;uzb 并用 USB 连接
./deploy.sh
```

### 5. 启动时钟

在 Kindle 上：KUAL → Clock → **启动时钟（首次/联网）**

> 首次启动需开启 WiFi，脚本会自动安装 Pillow（约 1–2 分钟）。

## 项目结构

```
kindle-ink-clock/
├── clock.py        # 时钟主脚本（部署到 Kindle）
├── preview.py      # 本地 Mac 预览工具
├── deploy.sh       # 一键部署到 Kindle
├── config.xml      # KUAL 扩展描述
├── menu.json       # KUAL 菜单
├── start.sh        # Kindle 端启动脚本
└── fonts/          # 放入字体文件（不入 git）
```

## 缓存文件

| 文件 | 内容 | 位置 |
|------|------|------|
| `weather_cache.json` | 天气文本 + 日出日落 | `/tmp/` |
| `holiday_cache.json` | 节假日 + 补班日 | `/tmp/` |
| `almanac_cache.json` | 老黄历宜/忌 | `/tmp/` |

## 许可

MIT License
