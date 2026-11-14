#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
汽水音乐 (com.soda.music) macOS 2.9.1  VIP 判定去除补丁器

做什么:
  1. 把 /Applications/汽水音乐.app 复制一份到工作目录
  2. 解包 Contents/Resources/main.asar,改里面的渲染层 / 播放器层 JS
  3. 重新打包 main.asar,覆盖回副本
  4. ad-hoc 重签名副本
  5. 校验:补丁点全部命中、旧字符串清零、签名可用

改了什么:
  [音源] 播放器把"试听模式(preview)"判定写死为 false,始终按完整音源("F")请求
  [拦截] 会员弹窗拦截(interceptPopupEnabled / checkIsPreviewPlayable)全部短路
  [状态] commerce 初始态直接置为 VIP/SVIP 有效
  [音质] 无损(lossless)/全景声(spatial)权益判定直接放行
  [列表] only_vip_playable 标记整体失效(VIP 角标 / 锁图标消失)
  [专辑] 付费数字专辑的"请到 App 购买"拦截去掉

用法:
  python3 patch_soda.py            # 生成副本
  python3 patch_soda.py --verify   # 只检查补丁点在新版本里是否还存在
"""

import os
import shutil
import subprocess
import sys
import tempfile

SRC_APP = "/Applications/汽水音乐.app"
WORK = os.path.dirname(os.path.abspath(__file__))
OUT_APP = "/Applications/汽水音乐 VIP.app"   # 装到 /Applications,改名只动显示名
ASAR = "Contents/Resources/main.asar"

MAIN_JS = "assets/main-qyF8NE99.js"
PLAYER_JS = "assets/player-BJbYe8nS.js"

# (文件, 原文, 替换文, 期望命中数)
PATCHES = [
    # ---------- 音源: 试听判定 ----------
    (PLAYER_JS,
     "checkPlayableIsPreview(e){return this.service.commerceState.value.hasPlayEntitlement?!1:e.label_info?.only_vip_playable?this.service.queueState.value.queue?.limitedFreeInfos[e.key]?.limited_free?!1:!this.service.commerceState.value.hasPlayEntitlement:!1}",
     "checkPlayableIsPreview(e){return!1}",
     1),

    (PLAYER_JS,
     "isPreview(){const e=this.state.value.mediaDetail;if(e)return e.video_model_type===2;const t=this.queueState.value.queue?.currentPlayableKey;if(!t)return!1;const r=this.queueState.value.queue?.playables[t];if(!r)return!1;const i=this.queueState.value.queue?.limitedFreeInfos[t];return this.commerceState.value.hasPlayEntitlement||i?.limited_free?!1:r.label_info?.only_vip_playable??!1}",
     "isPreview(){return!1}",
     1),

    # video_model_type===2 表示服务端给的"试听片段",强制当作完整音源
    (PLAYER_JS,
     "const n=s.video_model,o=s.video_model_type===2",
     "const n=s.video_model,o=!1",
     1),

    # ---------- 音质: 无损 / 全景声 / 极高 ----------
    (PLAYER_JS,
     "checkPlayableQualityPlayable(e,t){return Pe({playable:e,benefitQuality:this.commerceState.value.commerceInfo?.benefit_base?.quality}).includes(t)}",
     "checkPlayableQualityPlayable(e,t){return!0}",
     1),

    (PLAYER_JS,
     "computePlayableQualities(){const{queue:e}=this.queueState.value;if(!e||!e.currentPlayableKey)return[];const t=e.playables[e.currentPlayableKey];return t?(t?t.track:void 0)?Pe({playable:t,benefitQuality:this.commerceState.value.commerceInfo?.benefit_base?.quality}):[]:[]}",
     "computePlayableQualities(){const{queue:e}=this.queueState.value;if(!e||!e.currentPlayableKey)return[];const t=e.playables[e.currentPlayableKey];return t&&t.track?[...t.bit_rates?.map(i=>i.quality)??[]]:[]}",
     1),

    # ---------- 渲染层: 试听/拦截判定 ----------
    (MAIN_JS,
     "function S(x){return e.value.cacheInfo?.isPreview||x?.video_model_type===2?!0:r.value.hasPlayEntitlement||w.value?.limited_free?!1:x?.playable.label_info?.only_vip_playable??v.value?.label_info?.only_vip_playable??!1}",
     "function S(x){return!1}",
     1),

    (MAIN_JS,
     "isLimitedFree:computed(()=>r.value.hasPlayEntitlement||!v.value?.label_info?.only_vip_playable||k.value?!1:w.value?.limited_free??!1)",
     "isLimitedFree:computed(()=>!0)",
     1),

    (MAIN_JS,
     "interceptPopupEnabled:computed(()=>{const x=t.value.queue?.metaInfo.type;if(!x)return!1;const D=n.value.data.luna_pc_common_server_params?.client_intercept_strategy?.[x];return D?D.should_intercept_with_popup??!1:!0})",
     "interceptPopupEnabled:computed(()=>!1)",
     1),

    # ---------- 会员态默认值 ----------
    (MAIN_JS,
     'isVip:!1,isFreeVip:!1,vipExpireAt:0,hasPlayEntitlement:!1,type:"free"',
     'isVip:!0,isFreeVip:!0,vipExpireAt:4102415999,hasPlayEntitlement:!0,type:"vip"',
     1),

    # ---------- 音质权益 ----------
    (MAIN_JS,
     'function getQualityBenefitFlags(e){const t=new Set;for(const[r,n]of Object.entries(e?.benefit_quality_map??{})){const v=dayjs(getCurrentTime());v.isAfter(dayjs.unix(n.start_time))&&v.isBefore(dayjs.unix(n.end_time))&&t.add(r)}return t}',
     'function getQualityBenefitFlags(e){return new Set(["benefit_play_spatial","benefit_play_lossless","benefit_play_highest","benefit_play_higher","benefit_play_medium"])}',
     1),

    (MAIN_JS,
     'function checkQualityBenefitFlags(e,t){switch(t){case PlayQuality.spatial:return e.has("benefit_play_spatial");case PlayQuality.lossless:return e.has("benefit_play_lossless");case PlayQuality.highest:return e.has("benefit_play_highest");case PlayQuality.higher:return e.has("benefit_play_higher");case PlayQuality.medium:return e.has("benefit_play_medium");default:throw new Error(`Failed to check quality benefit: unknown quality: ${t}`)}}',
     'function checkQualityBenefitFlags(e,t){return!0}',
     1),

    (MAIN_JS,
     "async function checkBaseQualityBenefit(e){const{info:t}=await protocolOf(ServiceId.sharedState).get(\"user\");if(!t)return[PlayQuality.highest,PlayQuality.higher,PlayQuality.medium].includes(e);const{commerceInfo:r}=await protocolOf(ServiceId.sharedState).get(\"commerce\"),n=await getQualityBenefitFlags(r?.benefit_base?.quality);return checkQualityBenefitFlags(n,e)}",
     "async function checkBaseQualityBenefit(e){return!0}",
     1),

    # ---------- 付费专辑拦截 ----------
    (MAIN_JS,
     'e.label_info?.on_sale&&!getCommerceState()?.purchasedDigitalAlbumsIds.includes(e.album?.id??"")',
     "!1",
     1),
]

# 兜底:把剩下的 only_vip_playable 标记整体改成未定义字段(渲染层全部判假)
SOFT_RENAME = ("only_vip_playable", "only_vip_playable_off")


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=isinstance(cmd, str), check=True,
                          capture_output=True, text=True, **kw)


def main():
    verify_only = "--verify" in sys.argv

    # 1. 解包到临时目录
    tmp = tempfile.mkdtemp(prefix="soda-patch-")
    print(f"[1/6] 解包 {ASAR} -> {tmp}")
    sh(["npx", "--yes", "@electron/asar", "extract",
        os.path.join(SRC_APP, ASAR), tmp])

    # 2. 打补丁
    print("[2/6] 应用补丁")
    for fname, old, new, want in PATCHES:
        path = os.path.join(tmp, fname)
        src = open(path, encoding="utf-8").read()
        got = src.count(old)
        tag = "OK " if got == want else "MISS"
        print(f"      {tag} {fname} x{got}  ({old[:48]}...)")
        if got != want:
            print("      -> 目标版本 JS 结构变了,这条补丁点没命中")
            continue
        if not verify_only:
            open(path, "w", encoding="utf-8").write(src.replace(old, new))

    if verify_only:
        shutil.rmtree(tmp, ignore_errors=True)
        return

    # 3. 软改:残留的 only_vip_playable
    print("[3/6] 清理残留 VIP 标记")
    for fname in (MAIN_JS, PLAYER_JS):
        path = os.path.join(tmp, fname)
        src = open(path, encoding="utf-8").read()
        n = src.count(SOFT_RENAME[0])
        open(path, "w", encoding="utf-8").write(src.replace(*SOFT_RENAME))
        print(f"      {fname}: {n} 处")

    # 4. 重新打包
    print("[4/6] 复制 App 并重新打包 main.asar")
    if os.path.exists(OUT_APP):
        shutil.rmtree(OUT_APP)
    sh(["ditto", SRC_APP, OUT_APP])
    new_asar = os.path.join(WORK, "main.patched.asar")
    sh(["npx", "--yes", "@electron/asar", "pack", tmp, new_asar])
    target = os.path.join(OUT_APP, ASAR)
    os.remove(target)
    shutil.copy2(new_asar, target)

    # Info.plist 里的 asar integrity 只覆盖 app*.asar,main.asar 不在校验范围;
    # 保险起见把整段删掉(没有它 Electron 就不做完整性校验)
    plist = os.path.join(OUT_APP, "Contents/Info.plist")
    if sh(["/usr/libexec/PlistBuddy", "-c", "Print :ElectronAsarIntegrity", plist],
          **{}).returncode == 0:
        sh(["/usr/libexec/PlistBuddy", "-c", "Delete :ElectronAsarIntegrity", plist])

    # 显示名改成「汽水音乐 VIP」好跟原版区分。
    # 注意只能改 CFBundleDisplayName —— Electron 靠 CFBundleName 去找
    # "汽水音乐 Helper.app",改了会报 Unable to find helper app 起不来。
    sh(["/usr/libexec/PlistBuddy", "-c",
        "Set :CFBundleDisplayName 汽水音乐 VIP", plist])

    # 5. 重签名
    print("[5/6] ad-hoc 重签名")
    sh(["codesign", "--force", "--deep", "--sign", "-", OUT_APP])
    info = sh(["codesign", "-dv", OUT_APP], )
    print("      " + (info.stderr.strip().splitlines() or ["?"])[-1])

    # 6. 校验
    print("[6/6] 校验")
    chk = tempfile.mkdtemp(prefix="soda-check-")
    sh(["npx", "--yes", "@electron/asar", "extract", target, chk])
    main_src = open(os.path.join(chk, MAIN_JS), encoding="utf-8").read()
    player_src = open(os.path.join(chk, PLAYER_JS), encoding="utf-8").read()
    checks = {
        "试听判定已假 (player.isPreview)": "isPreview(){return!1}" in player_src,
        "试听请求已关 (checkPlayableIsPreview)": "checkPlayableIsPreview(e){return!1}" in player_src,
        "完整音源标记 (o=!1)": "const n=s.video_model,o=!1" in player_src,
        "音质放行 (checkPlayableQualityPlayable)": "checkPlayableQualityPlayable(e,t){return!0}" in player_src,
        "拦截弹窗已关": "interceptPopupEnabled:computed(()=>!1)" in main_src,
        "会员态已置真": 'hasPlayEntitlement:!0,type:"vip"' in main_src,
        "音质权益已放行": "function checkQualityBenefitFlags(e,t){return!0}" in main_src,
        "VIP 标记已清零": all(
            s.count("only_vip_playable") == s.count("only_vip_playable_off")
            for s in (main_src, player_src)),
    }
    for k, v in checks.items():
        print(f"      {'PASS' if v else 'FAIL'}  {k}")

    shutil.rmtree(chk, ignore_errors=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n产物: {OUT_APP}")
    print("启动: open \"" + OUT_APP + "\"")


if __name__ == "__main__":
    main()
