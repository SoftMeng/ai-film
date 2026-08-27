#!/bin/bash
# next-number.sh
# 读取创意MV/ 目录下最大编号 +1，输出三位补零字符串
# 用法：./scripts/next-number.sh

DIR="$(cd "$(dirname "$0")/.." && pwd)/创意MV"

if [ ! -d "$DIR" ]; then
    mkdir -p "$DIR"
fi

last=$(ls "$DIR" 2>/dev/null | grep -E '^[0-9]{3}\.txt$' | sort -r | head -1 | sed 's/\.txt//')

if [ -z "$last" ]; then
    echo "001"
else
    printf "%03d" $((10#$last + 1))
fi