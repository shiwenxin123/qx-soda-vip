#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
soda_vip_unlock_mitm.py — 汽水音乐 VIP 解锁（mitmproxy 版，Android / iOS / 任意走代理的设备通用）

用法：
    mitmdump -s soda_vip_unlock_mitm.py --listen-host 0.0.0.0 --listen-port 8080
    # 手机 Wi-Fi 代理指向 <电脑内网IP>:8080，并在手机上信任 mitmproxy 的 CA

只处理 *.qishui.com 的 JSON 响应，其它域名/非 JSON 一律原样放行。
字段改写规则与 Quantumult X 的 soda_vip_unlock.js 完全一致（见仓库 README）。
"""

import json
import re

from mitmproxy import ctx, http

HOST_RE = re.compile(r"(^|\.)qishui\.com$", re.I)

NOW = 0  # 运行时用 time.time() 覆盖
FAR = 4102444799  # 2099-12-31

FORCE_TRUE = {
    "is_vip", "is_svip", "is_membership", "is_paying_user", "is_paid",
    "has_paid_order", "has_play_entitlement", "has_download_entitlement",
    "limited_free", "is_limited_free", "is_ad_free", "vip_valid",
    "can_play", "can_play_full", "playable", "is_full",
}

FORCE_FALSE = {
    "only_vip_playable", "only_vip_download", "only_vip",
    "vip_only", "need_vip", "need_pay", "need_purchase",
    "is_preview", "is_preview_only", "preview_only", "is_trial",
    "is_about_to_expire", "on_sale", "locked",
}

EXPIRE_KEYS = {
    "expire_time", "expire_at", "vip_expire_at", "vip_expire_time",
    "membership_expire_time", "end_time", "valid_until", "expired_at",
}

BENEFIT_FLAGS = [
    "benefit_play_spatial",
    "benefit_play_lossless",
    "benefit_play_highest",
    "benefit_play_higher",
    "benefit_play_medium",
]

FREE_TYPES = ("free", "none", "normal")


def _full_benefit_map():
    return {k: {"start_time": 0, "end_time": FAR} for k in BENEFIT_FLAGS}


def _fix_membership(o):
    if not isinstance(o, dict):
        return
    o["is_membership"] = True
    o["is_paying_user"] = True
    o["is_about_to_expire"] = False
    mt = o.get("membership_type")
    if not mt or mt in FREE_TYPES:
        o["membership_type"] = "vip"
    if "expire_time" in o or o.get("membership_type"):
        o["expire_time"] = FAR
    if "last_membership_type" in o:
        o["last_membership_type"] = o["membership_type"]
    detail = o.get("membership_detail_map_v2")
    if isinstance(detail, dict):
        for t in ("vip", "svip"):
            cur = detail.get(t) or {}
            cur["expire_time"] = FAR
            cur.setdefault("is_auto_renew", False)
            detail[t] = cur


def transform(node, depth=0, now=None):
    if now is None:
        now = NOW
    if depth > 12 or not isinstance(node, (dict, list)):
        return node

    if isinstance(node, list):
        for i, v in enumerate(node):
            node[i] = transform(v, depth + 1, now)
        return node

    for key, v in list(node.items()):
        if key in FORCE_TRUE and (v is False or v == 0 or v is None):
            node[key] = True
            continue
        if key in FORCE_FALSE and (v is True or v == 1):
            node[key] = False
            continue
        if key in EXPIRE_KEYS and isinstance(v, (int, float)) and 0 < v < now + 86400 * 30:
            node[key] = FAR
            continue
        if key == "membership_type" and isinstance(v, str) and v.lower() in FREE_TYPES:
            node[key] = "vip"
            continue
        if key == "group_payment_level":
            node[key] = "0"
            continue
        if key in ("membership", "membership_info"):
            _fix_membership(v)
            node[key] = transform(v, depth + 1, now)
            continue
        if key == "benefit_quality_map" and isinstance(v, dict):
            merged = dict(v)
            merged.update(_full_benefit_map())
            node[key] = merged
            continue
        if key == "benefit_base" and isinstance(v, dict):
            q = dict(v.get("quality") or {})
            q.update(_full_benefit_map())
            v["quality"] = q
            node[key] = v
            continue
        if key == "label_info" and isinstance(v, dict):
            v["only_vip_playable"] = False
            v["only_vip_download"] = False
            v["on_sale"] = False
            node[key] = v
            continue
        if key == "limited_free_info" and isinstance(v, dict):
            v["limited_free"] = True
            node[key] = v
            continue
        if key == "video_model_type" and v == 2:
            node[key] = 1
            continue
        node[key] = transform(v, depth + 1, now)

    return node


class SodaVipUnlock:
    def __init__(self):
        self.hits = 0

    def response(self, flow: http.HTTPFlow):
        host = flow.request.pretty_host or ""
        if not HOST_RE.search(host):
            return
        ct = (flow.response.headers.get("content-type") or "").lower()
        if "json" not in ct:
            return
        raw = flow.response.content
        if not raw:
            return
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return

        import time
        now = int(time.time())
        global NOW
        NOW = now
        out = transform(data, now=now)

        flow.response.content = json.dumps(out, ensure_ascii=False).encode("utf-8")
        self.hits += 1
        ctx.log.info(f"[soda] rewrote {host}{flow.request.path} (#{self.hits})")


addons = [SodaVipUnlock()]
