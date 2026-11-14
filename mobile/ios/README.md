# iOS：结论与现状

## 结论

**汽水音乐 iOS 版对 `*.qishui.com` 全线做了证书 pinning（cronet / libsscronet 内置校验）。**

不越狱的情况下，Quantumult X / Surge / Loon 都只能做 MITM、不能 hook 进程，
所以**无法通过流量改写实现 VIP 解锁或去掉内嵌广告**。

## 证据链

三次对照实验，每次只改一个变量：

| # | 测试 | 结果 | 排除了什么 |
|---|---|---|---|
| 1 | `httpbin.org` 加 MITM + 改写脚本 | 页面出现注入字段 | 排除"证书没信任 / MITM 不可用" |
| 2 | `qishui.com` 系列加 MITM | App 立刻断网，连接 `0B/0B` `N/A` | 排除"只有个别域名 pin" |
| 3 | 只加 `api5-lq.qishui.com` | 该域名 `0B/0B`，**同秒其它 5 个 qishui 域名全部正常** | **确认 pinning** |

第 3 步是决定性的：同一时刻、同一个 App，没加 MITM 的域名全部正常流动，
唯一加了的那个 0 字节失败。这不是证书问题、不是网络问题、不是配置没生效。

## 当前推荐配置

**把 qishui 从 MITM 里全部移除**（否则 App 会断网），只保留去广告的连接层规则：

```
[filter_local]
HOST-SUFFIX, ads5-normal-gl2.zijieapi.com, REJECT
HOST-SUFFIX, lf-reward-video.bytedcdn.com, REJECT
HOST-SUFFIX, pglstatp.com, REJECT
HOST-SUFFIX, pangolin-sdk-toutiao.com, REJECT
```

完整版见 [`qx-soda-ads.conf`](qx-soda-ads.conf)。

> ⚠ 如果你靠"看广告换畅听时长"，**不要**用这套 REJECT —— 它会挡住激励视频，
> 导致拿不到免费时长。两者二选一。

**千万别拒这三个**（拒了不是没广告，是没声音／没界面）：

- `v11-luna.douyinvod.com` — 音视频 CDN
- `lf-res-3.douyinstatic.com` — 静态资源
- `app-alpha.bytedance.net` — 配置下发

## 如果想自己复核

用 httpbin 做一次自检，判断 MITM 链路是否正常（**不碰汽水，零风险**）：

```
[rewrite_local]
^https?://httpbin\.org/ url script-response-body <指向下面的自检脚本>
[mitm]
hostname = httpbin.org
```

自检脚本逻辑：往返回 JSON 里注入 `MITM_AND_REWRITE_BOTH_WORK` 字段。
**页面上能看到该字段 = MITM 与重写都通**；看不到 = 链路有问题
（这比"页面能不能打开"可靠 —— 没解密时页面照样能打开）。

自检通过后再去碰汽水域名。一次只加一个，加完立刻验证，坏了马上删。

## 常见坑

1. **jsDelivr 对 `@main` 有缓存**。改完脚本要立即生效，用 commit SHA 固定地址：
   `https://cdn.jsdelivr.net/gh/shiwenxin123/qx-soda-vip@<sha>/<path>`
   或者对 `@main` 跑 `https://purge.jsdelivr.net/gh/user/repo@main/file` 清缓存。
2. **QX 的 `hostname` 里 `*.qishui.com` 不保证匹配两级子域**（如 `api5-lq.qishui.com`），
   必须显式列出。这也是最早"加了规则没效果"的原因。
3. **中文乱码**：QX 在中文系统下会把脚本返回的字符串按 GBK 编码写回，
   脚本里要强制 `Content-Type: application/json; charset=utf-8`。
4. **一次别加多个域名**。之前一次加 6 个，App 全挂还分不清是谁的问题。

## 替代方案

iOS 走不通，但另外两条路是有效的：

| 方案 | 可行性 | 说明 |
|---|---|---|
| **Mac 版** | ✅ 已验证 | 改 asar，无损 1541kbps，无弹窗无广告。见仓库根目录 |
| **Android + root** | ✅ 可行 | Frida 过 pinning + mitmproxy。见 [`../android/README.md`](../android/README.md) |
| iOS 越狱 + Frida | ⚠️ 看设备 | iOS 18 及以后基本无公开越狱；脚本在 `../android/frida_pinning_bypass.js` |

如果只在 iPhone 上用，最实际的做法是：**保留手动看广告换时长，别折腾流量改写**。
