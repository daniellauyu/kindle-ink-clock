# Kindle Ink Clock

将吃灰的 Kindle Paperwhite 2 改造为全屏 e-ink 桌面时钟。

![预览](docs/preview.png)

## 功能

- 大号时间显示（HH:MM）
- 顶部小字天气 + 日出/日落
- 日期 + 星期 + 农历含生肖（如丙午马年，本地计算，无需联网）+ 当日节气
- 本月日历（今天黑底白字反色、节假日灰底显示名称、节气小字标注、补班标"班"）
- 老黄历宜/忌（最多 2 行，自动垂直居中于日历与摘要栏之间）
- 底部摘要栏：今年第 N 天 / 第 N 周 / 下一个节假日倒计时
- 每天 6/12/18 时联网刷新天气，同步刷新节假日和老黄历；天气失败时黄历仍独立更新，并持续重试至成功
- 全天强制关闭背光（e-ink 无需背光，最大化省电）
- 夜间（0–6 点）屏幕每 5 分钟刷新一次，降低 CPU 和 e-ink 刷新功耗
- 防锁屏，持续运行
- 日志自动截断至最近 200 行，避免占满 Kindle 存储

## 界面布局

```
深圳  阴  27~32℃  ↑05:40  ↓19:00    ← 天气（顶部，距屏幕边距 34px）
─────────────────────────────────
            14:32                    ← 时间（大字）
         2026年5月24日
      星期日  丙午马年四月初八          ← 农历含生肖
─────────────────────────────────
   一   二   三   四   五   六   日
              小满  5   6   7   8
   9   10   11   12   13   14  ■24■   ← 今天黑底白字反色
  16   17   18   19   20   21   22
  春节 春节 春节 春节 春节 春节 春节   ← 节假日灰底+名称
  23   24   25   26   27   28
  春节                        班
─────────────────────────────────
宜  安葬  理发  破土  祭祀  解除  沐浴  ← 黄历居中于日历与摘要间
   扫舍  入殓
忌  搬家  结婚  入宅  领证  出行  作灶
   旅游  赴任
       今年第144天   第21周   端午节还有26天  ← 摘要栏，底部对齐
```

## 适用设备

已在 **Kindle Paperwhite 2（KPW2，固件 5.12.2.2）** 上验证。
理论上适用于已越狱、安装了 Python 3.9 的其他 Kindle 型号。

## 数据来源

| 数据 | 来源 | 刷新频率 |
|------|------|---------|
| 天气 | [tianqi.com](https://www.tianqi.com/) HTML 抓取 | 每天 3 次：6/12/18 时（夜间 0–6 时不联网） |
| 农历 | 本地算法（春节查表 + 朔望近似） | 无需联网 |
| 节气 | 本地公式（21 世纪精度 ±1 天） | 无需联网 |
| 法定节假日 | [iCloud 中国节假日 ICS](https://calendars.icloud.com/holidays/cn_zh.ics/) | 天气刷新时顺带检查，缓存超 30 天才重拉 |
| 老黄历宜/忌 | [wannianli.tianqi.com](https://wannianli.tianqi.com/) HTML 抓取 | 天气刷新时顺带检查，缓存日期不是今天才重拉 |

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
CITY_CN        = "深圳"     # 显示城市名
CITY_SLUG      = "shenzhen" # tianqi.com 城市路径
DEBUG_MODE     = False       # Kindle 生产环境保持 False；本机调试可设 True
TOP_SAFE_Y     = 34         # 顶部安全距离，避开 Kindle 系统状态栏
FONT_PATH      = "/mnt/us/fonts/MapleMono-NF-CN-Bold.ttf"
REFRESH_HOURS  = {6, 12, 18}     # 天气刷新整点（0 点不联网，减少夜间功耗）
BACKLIGHT_PATH   = "/sys/class/backlight/max77696-bl/brightness"  # KPW2 背光路径
WEATHER_CACHE    = "/tmp/weather_cache.json"   # 可改为持久路径（重启后保留缓存）
HOLIDAY_CACHE    = "/tmp/holiday_cache.json"
ALMANAC_CACHE    = "/tmp/almanac_cache.json"
HOLIDAY_TTL_DAYS = 30                          # 节假日缓存有效期（天）
```

> `preview.py` 会把 `DEBUG_MODE` 设为 `True`，本机预览默认只读缓存；需要联网调试时显式使用 `--fetch` / `--fetch-almanac`。

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
# 步骤一：在 Kindle 搜索栏输入 ;uzb，激活 USB 传输模式
# 步骤二：USB 连接 Mac，等待挂载为 /Volumes/Kindle
# 步骤三：在项目目录执行
./deploy.sh
# 步骤四：安全弹出 Kindle（Finder → 推出，或命令行 diskutil eject /Volumes/Kindle）
```

`deploy.sh` 会自动同步以下文件：

| 文件 | 目标路径 |
|------|---------|
| `clock.py` | `/Volumes/Kindle/extensions/clock/` |
| `config.xml` | `/Volumes/Kindle/extensions/clock/` |
| `menu.json` | `/Volumes/Kindle/extensions/clock/` |
| `start.sh` | `/Volumes/Kindle/extensions/clock/` |
| `fonts/MapleMono-NF-CN-Bold.ttf` | `/Volumes/Kindle/fonts/` |

### 5. 启动时钟

**首次启动（需 WiFi）：**

1. Kindle 开启 WiFi（设置 → 无线网络）
2. KUAL → Clock → **启动时钟（首次/联网）**
3. 屏幕显示 `Installing Pillow...`，等待约 1–2 分钟
4. Pillow 安装完成后自动渲染时钟，之后每次启动无需 WiFi

**后续更新代码后重启时钟：**

1. KUAL → Clock → **停止时钟**
2. KUAL → Clock → **启动时钟（首次/联网）**

> 排查问题：通过 `;uzb` 挂载 Kindle 后查看 `/extensions/clock/clock.log`（日志自动截断至最近 200 行）

## 项目结构

```
kindle-ink-clock/
├── clock.py        # 时钟主脚本（部署到 Kindle）
├── preview.py      # 本地 Mac 预览工具
├── deploy.sh       # 一键部署到 Kindle
├── config.xml      # KUAL 扩展描述
├── menu.json       # KUAL 菜单
├── start.sh        # Kindle 端启动脚本（关背光 + nice -n 5 + 启动 clock.py）
├── docs/           # 文档资源（preview.png 等）
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
