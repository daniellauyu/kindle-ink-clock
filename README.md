# Kindle Ink Clock

将吃灰的 Kindle Paperwhite 2 改造为全屏 e-ink 桌面时钟。

![预览](docs/preview.png)

## 功能

- 大号时间显示（HH:MM）
- 日期 + 星期
- 本月日历（今天加框高亮）
- 实时天气 + 矢量天气图标（晴/多云/阴/雨/雪/雷/雾）
- 极端天气自动预警徽章
- 每 30 分钟联网同步天气 + NTP 校时，其余时间 WiFi 关闭省电
- 防锁屏，持续运行

## 适用设备

已在 **Kindle Paperwhite 2（KPW2，固件 5.12.2.2）** 上验证。
理论上适用于已越狱、安装了 Python3 的其他 Kindle 型号。

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
LAT        = 22.5431   # 纬度
LON        = 114.0579  # 经度
CITY_CN    = "深圳"    # 显示城市名
QWEATHER_KEY = ""      # 和风天气 Key（可选，用于气象预警）
WEATHER_INTERVAL = 30  # 天气刷新间隔（分钟）
FONT_PATH  = "/mnt/us/fonts/MapleMono-NF-CN-Bold.ttf"
```

### 3. 本地预览（Mac）

```bash
# 安装依赖
pip3 install pillow

# 预览当前时间
python3 preview.py

# 预览指定时间 + 天气
python3 preview.py --time 14:32 --weather "深圳  28°C  多云" --icon partly_cloudy

# 预览极端天气预警
python3 preview.py --icon thunder --weather "深圳  32°C  雷阵雨" --severe
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

## 天气数据

使用 [Open-Meteo](https://open-meteo.com/) — 完全免费、无需 API Key。

可选配 [和风天气](https://dev.qweather.com/) 免费 Key，启用中国气象预警。

## 许可

MIT License
