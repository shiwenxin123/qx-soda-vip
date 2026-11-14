# 阶段 3：单域名 MITM 测试（最后一次尝试）

## 先纠正：上一轮测试确实无效

你 01:37~01:39 的截图里，qishui 的接口**全都在正常跑**：

```
api5-lq.qishui.com:443   DIRECT   ↓254B ↑619B
api3-lf.qishui.com:443   DIRECT   ↓238B ↑603B
api3-lq.qishui.com:443   DIRECT   ↓238B ↑603B
api5-hl.qishui.com:443   DIRECT   ↓254B ↑619B
api3-hl.qishui.com:443   DIRECT   ↓238B ↑667B
conf3-lf.qishui.com:443  DIRECT   （在列表底部）
```

关键：**字节数正常流动**，说明 QX 只是转发、**没有做 MITM**
（因为 hostname 里已经删掉这些域名了）。所以 JS=0 是理所当然的，
不能证明 pinning。

同时确认了另一件事：**开屏广告没了** —— 说明 `[filter_local]` 的 REJECT 规则是生效的
（截图里 `dig.zjurl.cn` 显示 `REJECT`，那是短链跳转域名）。

## 现在只测一个：api5-lq.qishui.com

选它的理由：它是当前真正有流量（619B 上行）的接口之一，
且不像 log 域名那样一失败就拖垮整个 App。

```
[mitm]
hostname = api5-lq.qishui.com

[rewrite_local]
^https?://api5-lq\.qishui\.com/ url script-request-header https://cdn.jsdelivr.net/gh/shiwenxin123/qx-soda-vip@9a140b53d64f6bcd0a8ee8ccdf1fe8887155f7ab/mobile/ios/qx_soda_ad_probe.js
```

保存 → **重启 VPN** → 打开汽水播放一首歌 → 回 QX 网络活动搜索 `qishui`

| 现象 | 结论 | 行动 |
|---|---|---|
| **JS 计数 +1**，连接有字节 | ✅ 这个域名没 pin | 进阶段 4 |
| 连接 `0B/0B` `N/A`，App 报网络错误 | ❌ pinning 确认 | 立刻删掉，见下方结论 |
| 连接正常但 JS 仍 0 | hostname 没生效 | 检查是否保存到当前配置文件 |

**如果 App 报网络错误，立刻把 `hostname` 里那行删掉并重启 VPN。**

## 为什么只测一个

之前一次加了 6 个域名，App 全挂还分不清是谁。现在明确：**只有一个变量**。

而且这次不加 `log3-lf` / `log5-lf` —— 上次那批 638 次重连就是它们引起的
（日志域名失败 → App 判定网络异常 → 无限重试）。

## 如果这个也失败

那就是最后结论了：qishui 全线 pinning，iOS 不越狱无法改写。

届时可保留的成果：
- ✅ 开屏广告已去掉（`[filter_local]` REJECT，不依赖 MITM）
- ✅ Mac 端完整可用（`/Applications/汽水音乐 VIP.app`）
- ❌ iOS 端 VIP / 音效 / 无损：无解

## 如果成功（JS +1）

说明 API 域名可以解密。下一步：

1. 把规则换成主脚本：

```
[rewrite_local]
^https?://api5-lq\.qishui\.com/ url script-response-body https://cdn.jsdelivr.net/gh/shiwenxin123/qx-soda-vip@9a140b53d64f6bcd0a8ee8ccdf1fe8887155f7ab/soda_vip_unlock.js
```

2. 播放 VIP 歌，看 QX 里该请求的响应体：
   - 有 `is_vip` / `has_play_entitlement` → 改写生效
   - 响应体只有几百字节、没有会员字段 → 说明这个接口不承载会员态，
     真正的接口在别处（继续从网络活动里找大响应的 qishui 域名）
