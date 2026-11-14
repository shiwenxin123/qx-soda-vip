#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_apk.py — 判断汽水音乐 APK 该走哪条路

用法：
    python3 probe_apk.py /path/to/汽水音乐.apk

它会报告：
  1. 是否加固（libDexHelper / libjiagu / libshella / libmobisec 等）
  2. assets 里有没有内嵌的 JS bundle（有的话，客户端补丁可像 Mac 版那样直接改）
  3. 关键字段（only_vip_playable / hasPlayEntitlement 等）命中在哪些文件里
  4. 网络栈（libsscronet / libttnet）与 pinning 相关符号是否存在

输出最后会给出一条建议路线。
"""

import os
import re
import sys
import zipfile

MARKERS = [
    "only_vip_playable",
    "only_vip_download",
    "hasPlayEntitlement",
    "has_play_entitlement",
    "benefit_quality_map",
    "video_model_type",
    "limited_free_info",
]

PACKERS = [
    "libDexHelper", "libjiagu", "libshella", "libshell", "libmobisec",
    "libnesec", "libtup", "libsgmain", "libfakejni", "libexec.so",
    "libapp.so",  # 可能是 flutter/加固
]

NETLIBS = ["libsscronet", "libttnet", "libcronet", "libssl"]

PIN_MARKERS = [b"VerifyCert", b"ssl_verify", b"X509_verify_cert", b"cert_pinning"]


def main(path):
    if not os.path.isfile(path):
        print("找不到文件:", path)
        return 1

    size = os.path.getsize(path) / 1048576
    print(f"APK: {path}  ({size:.1f} MB)")

    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        libs = [n for n in names if n.startswith("lib/")]
        assets = [n for n in names if n.startswith("assets/")]

        print("\n== 架构 ==")
        archs = sorted({n.split("/")[1] for n in libs if n.count("/") >= 2})
        print("  " + ", ".join(archs) if archs else "  (无 lib 目录)")

        print("\n== 加固检测 ==")
        hits = [n for n in libs if any(p.rstrip(".so") in os.path.basename(n) for p in PACKERS)]
        if hits:
            print("  ⚠ 命中加固特征:")
            for h in hits[:8]:
                print("    " + h)
            packed = True
        else:
            print("  未发现常见加固库")
            packed = False

        print("\n== 网络栈 ==")
        net = [n for n in libs if any(k in os.path.basename(n) for k in NETLIBS)]
        for n in sorted(set(net))[:8]:
            print("  " + n)
        if not net:
            print("  (未发现)")

        print("\n== 关键字段命中 ==")
        found = {}
        scan = [n for n in assets if n.endswith((".js", ".json", ".bundle", ".txt"))]
        scan += [n for n in names if n.endswith(".dex")]
        for n in scan:
            try:
                data = z.read(n)
            except Exception:
                continue
            for mk in MARKERS:
                if mk.encode() in data:
                    found.setdefault(mk, []).append(n)
        if found:
            for mk, files in found.items():
                print(f"  {mk}: {', '.join(files[:3])}")
        else:
            print("  (assets/dex 里没直接命中；大概率逻辑在 native 或加密 bundle 里)")

        print("\n== pinning 特征 ==")
        pin_hit = []
        for n in net[:4]:
            try:
                data = z.read(n)
            except Exception:
                continue
            for pm in PIN_MARKERS:
                if pm in data:
                    pin_hit.append((os.path.basename(n), pm.decode()))
        for lib, pm in pin_hit[:6]:
            print(f"  {lib}: {pm}")

    print("\n== 建议路线 ==")
    if found and not packed:
        print("  ★ 客户端补丁可行：字段在明文 bundle/dex 里，未加固。")
        print("    解包 → 改字段 → 重打包 → apksigner 重新签名（会掉登录态）。")
    if pin_hit:
        print("  ★ 流量改写需要先过 pinning：")
        print("    root + Frida:  frida -U -f com.soda.music -l frida_pinning_bypass.js")
        print("    然后 mitmdump -s soda_vip_unlock_mitm.py，手机代理指向电脑")
    elif net:
        print("  ★ 可先直接试 mitmproxy：装系统证书 → 代理 → 看能不能解密")
    else:
        print("  ★ APK 结构异常，先确认是不是完整包")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
