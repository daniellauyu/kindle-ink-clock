#!/bin/bash
# 将本地修改同步到 Kindle（需先用 ;uzb 挂载）
KINDLE="/Volumes/Kindle/extensions/clock"

if [ ! -d "$KINDLE" ]; then
    echo "❌ Kindle 未挂载，请先在 Kindle 搜索栏输入 ;uzb 并连接 USB"
    exit 1
fi

cp clock.py   "$KINDLE/"
cp menu.json  "$KINDLE/"
cp config.xml "$KINDLE/"
cp start.sh   "$KINDLE/"
cp fonts/MapleMono-NF-CN-Bold.ttf /Volumes/Kindle/fonts/

echo "✅ 已同步到 Kindle，请安全弹出后在 KUAL 重新启动时钟"
