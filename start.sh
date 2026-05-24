#!/bin/sh
# 启动时关背光（夜间持续由 clock.py 维持）
echo 0 > /sys/class/backlight/max77696-bl/brightness 2>/dev/null
nice -n 5 /mnt/us/python3/bin/python3.9 /mnt/us/extensions/clock/clock.py >> /mnt/us/extensions/clock/clock.log 2>&1 &
