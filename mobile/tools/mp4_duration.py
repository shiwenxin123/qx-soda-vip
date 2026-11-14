#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mp4_duration.py — 读 MP4/M4A 的 mvhd，输出真实时长和码率

用途：验证"会员歌到底是不是完整音源"。汽水音乐把播放/缓存的音频落成 .bin
（其实是 M4A），文件名是 uuid，看不出时长。这个脚本直接解析 MP4 头。

用法：
    python3 mp4_duration.py <文件或目录> [...]

Android 缓存一般在：
    /sdcard/Android/data/com.soda.music/cache/... 或 files/...
拉回本地再跑：
    adb shell "ls -l /sdcard/Android/data/com.soda.music/cache" | head
    adb pull <路径> ./soda_cache/
iOS（越狱）：
    /var/mobile/Containers/Data/Application/<uuid>/Library/Caches/...
"""

import os
import struct
import sys

CONTAINERS = {"moov", "trak", "mdia", "minf", "stbl", "udta"}


def _mvhd_duration(fp, start, end):
    pos = start
    found = None
    while pos + 8 <= end:
        fp.seek(pos)
        head = fp.read(8)
        if len(head) < 8:
            break
        size = struct.unpack(">I", head[:4])[0]
        typ = head[4:8].decode("latin1", "replace")
        if size == 1:
            size = struct.unpack(">Q", fp.read(8))[0]
        elif size == 0:
            size = end - pos
        if size < 8:
            break
        if typ in CONTAINERS:
            r = _mvhd_duration(fp, pos + 8, pos + size)
            if r:
                found = found or r
        elif typ == "mvhd":
            fp.seek(pos + 8)
            d = fp.read(32)
            ver = d[0]
            if ver == 0:
                ts, dur = struct.unpack(">II", d[12:20])
            else:
                ts, dur = struct.unpack(">IQ", d[20:32])
            return dur / ts if ts else 0
        pos += size
    return found


def probe(path):
    size = os.path.getsize(path)
    with open(path, "rb") as fp:
        # 校验 ftyp（M4A/MP4 才有）
        head = fp.read(12)
        if len(head) < 12 or head[4:8] != b"ftyp":
            return None
        dur = _mvhd_duration(fp, 0, size) or 0
    kbps = int(size * 8 / dur / 1000) if dur else 0
    return dur, kbps, size


def main(argv):
    paths = []
    for a in argv:
        if os.path.isdir(a):
            for root, _, files in os.walk(a):
                for f in files:
                    p = os.path.join(root, f)
                    if os.path.getsize(p) > 100 * 1024:
                        paths.append(p)
        else:
            paths.append(a)

    paths.sort(key=lambda p: os.path.getmtime(p))
    print(f"{'时间':8} {'文件':12} {'大小':>9} {'时长':>8} {'码率':>8}")
    for p in paths:
        r = probe(p)
        if not r:
            continue
        dur, kbps, size = r
        import time
        t = time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(p)))
        flag = ""
        if dur and dur < 65:
            flag = "  ← 试听片段"
        elif kbps >= 900:
            flag = "  ← 无损"
        print(f"{t:8} {os.path.basename(p)[:8]:12} {size/1048576:8.1f}M "
              f"{dur:7.1f}s {kbps:7d}k{flag}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1:])
