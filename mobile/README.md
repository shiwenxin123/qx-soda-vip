# 手机端：iOS / Android

Mac 端走的是**改 asar**（见根目录 README）；手机上没法这么改，只能走**流量改写**。
两端共用同一个改写脚本 `soda_vip_unlock.js`（QX / Surge / Loon / Surfboard 都兼容，
用 `$response.body` + `$done({body})` 这套 API）。

```
mobile/
├── ios/
│   ├── README.md         结论：全线 pinning，不越狱无解；附证据链与去广告配置
│   └── qx-soda-ads.conf  连接层去广告（不依赖 MITM，安全）
├── android/
│   ├── README.md               三条路线（改 APK / mitmproxy+Frida / Surfboard）
│   ├── soda_vip_unlock_mitm.py mitmproxy 插件，字段改写逻辑与 JS 版一致
│   ├── frida_pinning_bypass.js 过 cronet(libsscronet) 的证书校验
│   └── probe_apk.py            先跑这个：判断能不能改包、要不要过 pinning
└── tools/
    └── mp4_duration.py         读落盘音频的真实时长/码率（验证是否拿到完整音源）
```

## 两端的真实结论

| | iOS | Android |
|---|---|---|
| 证书 pinning | ✅ 有（cronet） | ✅ 有（同一个 cronet） |
| 能不能过 | ❌ 不越狱无解 | ✅ root + Frida 可以 |
| 结论 | 流量改写走不通 | 可行 |
| 详细 | [`ios/README.md`](ios/README.md) | [`android/README.md`](android/README.md) |

> iOS 那条结论是三次对照实验得出的，不是猜的：同一时刻同一个 App，
> 没加 MITM 的 5 个 qishui 域名全部正常流动，唯一加了的那个 `0B/0B` 失败。

## 验证口径（两端通用）

不要看播放条，要看**落盘的音频**：

```bash
python3 mobile/tools/mp4_duration.py <缓存目录>
# Android 先用 adb pull 拉回来
```

- `180~260s / 320kbps`，或 `900kbps+`（无损）→ 服务端给了完整音源，改写生效
- `30s` / `60s` → 服务端只签发试听切片，客户端/代理都变不出来

Mac 上的实测基线：

```
223.8s  324kbps      ← 正常
 60.0s  132kbps      ← 试听片段
```

## 脚本地址

```
https://cdn.jsdelivr.net/gh/shiwenxin123/qx-soda-vip@main/soda_vip_unlock.js
```

> 用 jsDelivr 而不是 raw：`raw.githubusercontent.com` 在部分网络下解析不了。
> jsDelivr 对 `@main` 有缓存，改完想立刻生效就换成 `@<commit-sha>`，
> 或对 `@main` 跑一次 `https://purge.jsdelivr.net/gh/user/repo@main/file`。
