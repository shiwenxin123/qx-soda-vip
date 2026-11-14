# 汽水音乐 VIP 解锁

针对汽水音乐（Soda Music，`com.soda.music`）的会员限制与广告处理方案。
Mac 端走**改包**，手机端走**流量改写**，两条路的结论差别很大。

| 端 | 方案 | 状态 |
|---|---|---|
| **macOS** | 改 `main.asar` 里的渲染层 / 播放器层 JS | ✅ 完整可用（无损 1541kbps，无弹窗无广告） |
| **iOS** | 流量改写（QX MITM） | ❌ 全线证书 pinning，不越狱无解 |
| **Android** | 改 APK / mitmproxy+Frida | ✅ 可行（需 root 过 pinning） |

---

## Mac 端

### 已完成的产物

```
/Applications/汽水音乐 VIP.app      打好补丁的完整应用（528MB，ad-hoc 签名）
/Applications/汽水音乐.app          原版，保留作更新源与回退
```

启动：

```bash
env -u ELECTRON_RUN_AS_NODE open -n "/Applications/汽水音乐 VIP.app"
```

> 别在带 `ELECTRON_RUN_AS_NODE=1` 的 shell 里直接跑二进制，会被当 node 秒退。

### 重新构建

```bash
python3 patch_soda.py            # 解包 → 打补丁 → 重打包 → 重签 → 自检
python3 patch_soda.py --verify   # 只检查补丁锚点是否还命中（官方更新后先跑这个）
```

`main.asar` 不在 `ElectronAsarIntegrity` 校验表里，脚本顺手删掉该键避免完整性校验。

### 逆向要点

`/Applications/汽水音乐.app` 是 Electron 包，会员判定全在明文 JS 里：

```
Contents/Resources/main.asar
  assets/main-qyF8NE99.js     2.7MB  页面、音质菜单、会员弹窗、会员态
  assets/player-BJbYe8nS.js    64KB  播放器内核（选音源 / 试听判定）
```

会员判定集中在两处：

1. **`commerce` 共享状态** — `hasPlayEntitlement` / `isVip` / `vipExpireAt`、
   服务端下发的 `membership.*`、`benefit_quality_map`（各音质权益时间窗）
2. **曲目 `label_info`** — `only_vip_playable` / `only_vip_download` / `on_sale`

播放链路：

```
setMedia()
  └─ checkPlayableIsPreview()        ← 非会员返回 true = 走试听
       └─ getPlayablePlayInfo(track, quality, isPreview)
            └─ modelManager.getDetail() → video_model.video_list[]
                 ├─ video_model_type === 2   ← 服务端说"这是试听"
                 └─ main_url / backup_url    ← 真正的音频地址
```

### 13 处补丁

| # | 位置 | 改动 |
|---|---|---|
| 1 | player `checkPlayableIsPreview` | `return!1` |
| 2 | player `isPreview()` | `return!1` |
| 3 | player `getPlayablePlayInfo` | `o=s.video_model_type===2` → `o=!1` |
| 4 | player `checkPlayableQualityPlayable` | `return!0` |
| 5 | player `computePlayableQualities` | 直接返回全部 `bit_rates` |
| 6 | main `checkIsPreviewPlayable` | `return!1` |
| 7 | main `isLimitedFree` | `computed(()=>!0)` |
| 8 | main `interceptPopupEnabled` | `computed(()=>!1)` |
| 9 | main `commerce` 初始态 | VIP/entitlement 全真，到期 2099 |
| 10 | main `getQualityBenefitFlags` | 返回全部 5 个 `benefit_play_*` |
| 11 | main `checkQualityBenefitFlags` | `return!0` |
| 12 | main `checkBaseQualityBenefit` | `return!0` |
| 13 | main `checkPlayableUnplayable` | 付费专辑拦截条件改 `!1` |

兜底：残留的 `only_vip_playable` 全部改名成未定义字段，VIP 角标/锁图标一并消失。

### 实测（游客态，未登录）

真正落盘的音频（解析 MP4 `mvhd`）：

```
8.5MB  218.8s  324kbps     9.2MB  237.2s  324kbps
7.7MB  199.6s  324kbps     9.6MB  247.9s  324kbps
5.2MB  135.5s  324kbps     9.0MB  233.4s  324kbps
                           31.1MB 169.4s 1541kbps  ← 无损
```

A/B 对照（同一台机、同一网络、都是未登录游客）：

| 检查点 | 原版 | 补丁版 |
|---|---|---|
| 搜索结果 | `江南 VIP 原唱` | `江南 原唱` |
| 点 VIP 歌 | 弹「请前往 App 购买会员」 | 直接播放 |
| 播放条音质 | `标准音质` | `无损音质` |

**边界**：服务端对少数曲目仍只签发 60s 试听片段（缓存里会出现
`0.9MB / 60.0s / 132kbps` 这种），这类歌客户端变不出完整音轨。

---

## 手机端

| | iOS | Android |
|---|---|---|
| 证书 pinning | ✅ 有（cronet） | ✅ 有（同一个 cronet） |
| 能否绕过 | ❌ 不越狱无解 | ✅ root + Frida |
| 结论 | 流量改写走不通 | 可行 |

- iOS：[`mobile/ios/README.md`](mobile/ios/README.md) — 三次对照实验的证据链、
  当前推荐配置（只留连接层去广告）、以及为什么不要再用 MITM
- Android：[`mobile/android/README.md`](mobile/android/README.md) — 三条路线 +
  Frida pinning bypass + mitmproxy 插件 + APK 探针
- 验证工具：[`mobile/tools/mp4_duration.py`](mobile/tools/mp4_duration.py)

---

## 文件清单

```
项目/
├── patch_soda.py              Mac 补丁器（含 --verify）
├── soda_vip_unlock.js         流量改写脚本（QX/Surge/Loon/Surfboard 通用）
├── soda_vip_unlock.conf       QX 规则模板
└── mobile/
    ├── README.md              手机端总览
    ├── ios/README.md          iOS 结论 + qx-soda-ads.conf
    ├── android/               README + mitmproxy 插件 + Frida 脚本 + APK 探针
    └── tools/mp4_duration.py  缓存音频时长/码率检测
```

## 已知边界

1. **音频地址由服务端签发**。改动只能让客户端不再拦截、不再降级，
   变不出服务端没给的音频。
2. **iOS 全线 pinning**，不越狱无法通过流量层改写。
3. **官方更新后会覆盖补丁**。更新完跑 `patch_soda.py --verify` 检查锚点，
   还在就重新生成。
4. 重新签名会让 MAS 应用失去 App Store 身份，登录态/收藏可能受影响。
