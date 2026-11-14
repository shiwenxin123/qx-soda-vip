# 汽水音乐 VIP 解锁 —— iOS / Android

Mac 端走的是**改 asar**（见仓库根目录 README）；手机上没法这么改，只能走**流量改写**。
两边共用同一个脚本：`soda_vip_unlock.js`（QX / Surge / Loon / Surfboard 都兼容，
用 `$response.body` + `$done({body})` 这套 API）。

```
mobile/
├── ios/
│   └── README.md               QX 装证书 → 加规则 → 验证是否被 pinning 挡
├── android/
│   ├── README.md               三条路线（改 APK / mitmproxy+Frida / Surfboard）
│   ├── soda_vip_unlock_mitm.py mitmproxy 插件，字段改写逻辑与 JS 版一致
│   ├── frida_pinning_bypass.js 过 cronet(libsscronet) 的证书校验
│   └── probe_apk.py            先跑这个：判断能不能改包、要不要过 pinning
└── tools/
    └── mp4_duration.py         读落盘音频的真实时长/码率（验证是否拿到完整音源）
```

## 先搞清楚一件事

手机端和 Mac 端的**难点不一样**：

| | Mac | iOS | Android |
|---|---|---|---|
| 客户端逻辑 | Electron，明文 JS，可直接改 | 原生，改不了（除非越狱） | 原生，加固则改不了 |
| 可行方案 | 改 asar（已验证） | 只能流量改写 | 改 APK 或流量改写 |
| 拦路虎 | 无 | **cronet 证书 pinning**，不越狱过不去 | 同左，但有 root 就能过 |

所以手机端第一件事不是装脚本，是**判断这个 App 让不让你解密流量**。

## 验证口径（两端通用）

不要看播放条，要看**落盘的音频**：

```bash
python3 mobile/tools/mp4_duration.py <缓存目录>
# 或 adb pull 到本地再跑
```

- `180~260s / 320kbps`，或 `900kbps+`（无损）→ 服务端给了完整音源，改写生效
- `30s` / `60s` → 服务端只签发试听切片，客户端/代理都变不出来

Mac 上的实测基线（同一套工具跑出来的）：

```
223.8s  324kbps      ← 正常
 60.0s  132kbps      ← 试听片段
```

## 脚本地址

```
https://cdn.jsdelivr.net/gh/shiwenxin123/qx-soda-vip@main/soda_vip_unlock.js
```

> 用 jsDelivr 而不是 raw：`raw.githubusercontent.com` 在部分网络下解析不了。
> jsDelivr 对 `@main` 有缓存，想立刻生效改成 `@<commit-sha>`。
