# iOS 版：汽水音乐 VIP 解锁

iPhone 上没法像 Mac 那样改 asar（原生 App，字节加密 IPA 也拿不到干净包），
所以走**流量改写**：Quantumult X 解密 `*.qishui.com` 的响应，把会员字段改掉。
脚本和 Mac 版是同一个文件，托管在 GitHub，不用本地起服务。

---

## 一、装证书、开 MitM

1. QX → 右下角 ⚙️ → **MitM** → **生成证书**
2. 会跳 Safari 下载 `Quantumult X CA` → 允许
3. iPhone **设置 → 通用 → VPN 与设备管理** → 点描述文件 → 安装
4. iPhone **设置 → 通用 → 关于本机 → 证书信任设置** → 打开 `Quantumult X CA` 开关
5. 回 QX：**设置 → 重写** 打开，**MitM** 打开
6. **设置 → 其他设置 → VPN → 始终开启**（HTTP 响应类型重写必须开这个）

> 第 4 步最容易漏。只装描述文件不打开信任开关，QX 里能看到域名但拿不到明文。

## 二、加重写规则

QX → **重写** → 右上角 `+`（或"引用"里加一条本地规则）：

```
类型          script-response-body
匹配 URL      ^https?:\/\/[^\/]*qishui\.com\/
脚本          https://cdn.jsdelivr.net/gh/shiwenxin123/qx-soda-vip@main/soda_vip_unlock.js
```

保存至「当前配置文件」即可。也可以用仓库里 `mobile/ios/qx-soda-ios.conf` 的整段
合并进你现有配置。

## 三、先验证「到底能不能解密」

这一步决定 iOS 这边成不成，**先做再谈别的**：

1. 打开汽水音乐，随便播一首歌
2. QX → **网络活动**，找 `api.qishui.com` 或 `*.qishui.com` 的请求
   - 能看到请求路径、有响应、并被标记走了重写 → **通了，往下看第四节**
   - 只有一条 `CONNECT` 就断了、或者状态是"失败/隧道" → **被 pinning 挡了，看第五节**

## 四、通了之后怎么确认生效

跟 Mac 版同一套判定，在手机上做：

1. 搜「林俊杰」→ 结果行应该没有绿色 **VIP** 角标
2. 点《江南》→ 不应该弹"开通会员"
3. 播放条 → 看总时长是不是整首歌（3~4 分钟），能不能拖到 90% 之后
4. 音质菜单 → 「无损音质」「全景声」应该能选中，不再弹会员窗

判据解释：能播 ≠ 拿到了完整音源。服务端如果对非会员只签发 60 秒切片，
客户端改判也变不出完整音频 —— 这时表现是"不弹窗、能播，但 60 秒跳下一首"。

## 五、如果是 pinning（大概率）

汽水音乐用字节自家的 cronet 网络栈（iOS 上是同源的 `libsscronet`），
证书校验在 native 层，QX 没有 hook 能力，**不越狱就过不去**。

三条路，按代价排序：

| 路线 | 前提 | 说明 |
|---|---|---|
| A. 越狱 + Frida | 越狱设备 | `frida -U -f com.soda.music -l mobile/android/frida_pinning_bypass.js`（同一个脚本，iOS 也适用），再让 QX 或 mitmproxy 抓 |
| B. 只用 Mac 端 | 无 | iPhone 只当遥控/播放器不行；实际是"手机不折腾，Mac 上听" |
| C. 等 iOS 端 JS 化 | 无 | 如果哪天汽水 iOS 改成 WebView/JSBundle 承载业务，就能像 Mac 那样改包 |

## 六、判据：这台设备到底有没有吃到改写

和 Mac 一样看**落盘的音频**（越狱设备可读）：

```bash
# 越狱设备上找缓存
find /var/mobile/Containers/Data/Application -path "*SodaMusic*" -name "*.bin" 2>/dev/null | head
# 拉回电脑后用同一个工具看时长/码率
python3 mobile/tools/mp4_duration.py ./soda_cache/
```

- 时长 180~260s、码率 320k 或 900k+（无损）→ 拿到完整音源
- 时长 30s / 60s → 服务端只给了试听

不越狱就没有文件系统访问，只能在 App 里看播放条总时长。

---

## 附：实测主机名（重要，决定规则生不生效）

iPhone 上 QX「DNS 缓存」页看到的汽水真实接口主机是**两级子域 + `-lf` 后缀**：

```
api3-lf.qishui.com     api5-lf.qishui.com
conf3-lf.qishui.com    conf5-lf.qishui.com
log3-lf.qishui.com     log5-lf.qishui.com
```

QX 的 `[mitm] hostname` 里只写 `*.qishui.com` **不保证跨两层匹配**。
匹配不上 → 只看到 CONNECT、拿不到明文 → 规则等于没加，表现就是
「加了重写但还是弹会员 / 还是有广告」。

所以 `qx-soda-ios.conf` v2 里是显式列出来的：

```
hostname = qishui.com, *.qishui.com, *-lf.qishui.com,
           api.qishui.com, api3-lf.qishui.com, api5-lf.qishui.com,
           conf3-lf.qishui.com, conf5-lf.qishui.com,
           log3-lf.qishui.com, log5-lf.qishui.com,
           aweme.snssdk.com, lf-*.douyin.com, *.douyin.com,
           *.pglstatp.com, *.pangolin-sdk-toutiao.com
```

改完记得：QX 首页关掉再开一次（或设置里「重新载入配置」），MITM 才会重新读 hostname。

## 附：广告怎么去

汽水广告位大体三块：

| 来源 | 特征 | 处理 |
|---|---|---|
| 自有广告位 | `*/luna/media_ads` | `url reject-dict`（返回空 JSON，SDK 不会疯狂重试） |
| 激励视频/任务 | URL 含 `reward` / `incentive` / `ad_complete` | 先 probe 抓，再决定 reject 还是重放 |
| 抖音广告联盟 | `pglstatp` / `pangolin-sdk-toutiao` / `adsdk` | `url reject` |

`qx-soda-ios.conf` 里已经带了前两块 + 联盟域的 reject。

> 注意：如果 VIP 改写真的生效（`is_ad_free` 被置真），很多广告位会自己消失。
> **还有广告 = 改写没生效**，先按上面查 hostname，别急着堆广告规则。

## 附：「每天自动看广告」怎么做

两种思路，成本和成功率差很多：

### 甲：让广告瞬间播完（推荐先试）

改写广告配置里的时长字段，1 秒播完即算完成：

```
[rewrite_local]
^https?://[^/]*qishui\.com/luna/(media_ads|ad_config) url script-response-body https://cdn.jsdelivr.net/gh/shiwenxin123/qx-soda-vip@main/mobile/ios/qx_soda_ad_auto.js
```

`qx_soda_ad_auto.js` 会把 `duration / ad_duration / skip_time` 之类字段压到 1 或 0。
成功率取决于服务端有没有二次校验「观看时长」；有校验的话会判失败。

### 乙：重放奖励回调（有效但容易被风控）

1. 先挂探针，把真实接口抓出来：

```
[rewrite_local]
^https?://[^/]*qishui\.com/ url script-request-header https://cdn.jsdelivr.net/gh/shiwenxin123/qx-soda-vip@main/mobile/ios/qx_soda_ad_probe.js
```

2. 看一轮广告，QX 会推送命中的 URL，同时存到本地键 `soda_ad_probe`
3. 把抓到的那个 POST 填进 `qx_soda_ad_auto.js` 的 `replayReward()`，按需重放

> 同一个 `request_id` / `ad_id` 复用会被服务端拒，需要每次重新拉一次广告配置拿新 id。
> 这条路线本质上是在伪造观看记录，账号侧有被标记的风险，自己权衡。

### 丙：不折腾广告

如果 VIP 改写生效了，广告位通常直接没了，不需要「看广告换时长」。
先把 `hostname` 改对、确认 `api5-lf` 的响应能被改写，再回来看这条。

---

## 故障排查：加了规则后「网络出错，请检查网络」

**先看两个数字**（QX 网络活动页顶部）：

| 现象 | 含义 | 处理 |
|---|---|---|
| 大量 `qishui` 连接，`0B ↑ 0B ↓`、状态 `N/A`、红叉 | QX 尝试解密但握手被拒 | 大概率 pinning → 回滚 MITM |
| 顶部 `JS` 计数一直是 `0` | 没有任何脚本被执行过 | 说明这些请求压根没被解密 |
| 连接数一直涨（633/634/635…） | App 在无限重试 | 说明它等不到响应 |

三条同时成立 = **QX 的 MITM 被汽水的证书校验挡了**，而且挡住之后 App 直接判网络故障。

### 立刻恢复

把 qishui 从 `[mitm] hostname` 里摘掉（见 `rollback-qx-soda.conf`），保存后
**关掉 VPN 再打开**。App 立刻恢复正常。

### 想确认到底是 pinning 还是证书没信任

1. QX 网络活动里找一个**别的 App** 的 HTTPS 请求（比如微信、Safari）
   - 它也是 `0B / N/A / JS=0` → 全局 MITM 没工作，是**证书信任开关没开**
     （iOS 设置 → 通用 → 关于本机 → 证书信任设置）
   - 别的 App 正常解密、只有 qishui 不行 → 就是**汽水自己 pinning**
2. 用 Safari 打开 `https://api5-lf.qishui.com/`
   - 能打开且证书没警告 → 系统层信任没问题，问题在 App 的 pinning
   - 弹证书警告 → 证书没装好/没信任

### 判定 pinning 之后的选项

iOS 不越狱 **没有**通用绕过手段（QX/Surge/Loon 都只能做 MITM，不能 hook）。
能走的只有：

1. **越狱 + Frida**：`mobile/android/frida_pinning_bypass.js`（同一个脚本 iOS 也适用）
   `frida -U -f com.soda.music -l frida_pinning_bypass.js`
2. **iPhone 不折腾**：继续用已经打好的 Mac 版（`/Applications/汽水音乐 VIP.app`）
3. 等 iOS 端把业务逻辑挪到 WebView/JSBundle（目前不是）

> 换句话说：iOS 这条路能不能通，**在做任何脚本之前**用 `JS` 计数就能判断。
> `JS=0` 就没必要继续调脚本了。

---

## ★ 更正：真正的流量不在 qishui.com

2026-11-14 23:59 的网络活动截图推翻了我之前的判断。汽水实际跑的是**字节的共享域名**：

| 域名 | 用途 | 证据 |
|---|---|---|
| `ads5-normal-gl2.zijieapi.com` | **广告 API** | 9KB↓ / 5KB↑，有完整往返 |
| `lf-reward-video.bytedcdn.com` | **激励视频素材** | 7KB↓ / 1KB↑ |
| `v11-luna.douyinvod.com` | 音视频 CDN | **1MB↓** ← 正在放歌 |
| `lf-res-3.douyinstatic.com` | 静态资源（封面/图标） | 46KB↓ |
| `app-alpha.bytedance.net` | 字节配置下发 | 0B（走别的通道） |
| `log5-lf.qishui.com` | 只是日志上报 | 之前那一堆 |

**所以之前把 qishui.com 加进 MITM 是在解错的东西**：那批 `log*-lf.qishui.com`
是日志通道，本来就没什么可改的；真正的广告和业务都在 `zijieapi` / `bytedance` 系域名上。

## 去广告：不需要 MITM（推荐先做这个）

`qx-soda-ads.conf` 用 `[filter_local]` + `HOST-SUFFIX → REJECT` 在**连接层**拒绝广告域名。
不碰 TLS、不用证书、不会被 pinning 挡，也不会把 App 搞成「网络出错」。

```
[filter_local]
HOST-SUFFIX, ads5-normal-gl2.zijieapi.com, REJECT
HOST-SUFFIX, lf-reward-video.bytedcdn.com, REJECT
HOST-SUFFIX, pglstatp.com, REJECT
HOST-SUFFIX, pangolin-sdk-toutiao.com, REJECT
```

**千万别拒**这三个（拒了就不是没广告，是没声音/没界面）：
- `v11-luna.douyinvod.com` — 音视频 CDN
- `lf-res-3.douyinstatic.com` — 静态资源
- `app-alpha.bytedance.net` — 配置下发

### 「每天自动看广告换时长」怎么落地

激励流程拆开是三段：**拉广告配置 → 播 bytedcdn 上的视频 → 回调发奖励**。

拒掉 `lf-reward-video.bytedcdn.com` 后，第二段拿不到素材。这时有两种结果：

- 广告 SDK 判失败 → 直接跳过，**免费获得跳过**（多数版本是这样，等于白嫖）
- 广告 SDK 仍然回调"完成" → 连奖励也一起拿到（部分实现有这毛病）

先只加这一条试一次，看广告是"跳过"还是"卡住"。卡住的话再退回只拒 `ads5-normal-gl2`。

## MITM 到底能不能用：分阶段测

`qx-soda-mitm-staged-test.conf` 给了三步法，核心是**一次只加一个域名**：

1. 只解密 `ads5-normal-gl2.zijieapi.com`（广告域名，坏了也不影响听歌）
2. 看 QX 顶部 **JS 计数是否 +1**
   - `+1` → 能解密，继续
   - 仍是 `0`、连接 `0B/0B` → **pinning**，iOS 不越狱到此为止
3. 逐个加业务域名，每次只加一个并试播

> 我上次的错：一次加了 6 个 qishui 域名，App 全挂还分不清是谁的问题。
> 而且加错了对象 —— 那些是日志域名。

---

## ★★ 先做这一步：MITM 自检（在碰汽水之前）

现在有三个症状同时存在：

1. 加 `[filter_local]` REJECT 广告域名 → 网络正常，但**广告还在**
2. **VIP / 音效等特权不生效**
3. 之前把 qishui 加进 MITM → App 直接「网络出错」

这三条指向**同一个根因**：QX 的 HTTPS 解密没有真正生效。
而"解密没生效"有两个可能，症状一模一样、必须分清：

| 可能 | 症状 | 修复成本 |
|---|---|---|
| **A. QX 根证书没被系统信任** | 一 MITM 就断网、JS 计数永远 0 | 打开一个开关 |
| **B. 汽水自己做了证书校验(pinning)** | 同上 | iOS 不越狱无解 |

90% 的情况是 A —— 因为 iOS 要在**两个不同地方**各做一次设置，漏掉第二步就
是"描述文件装了但证书不受信任"，表现和 pinning 完全一样。

### 自检怎么做（零风险，不碰汽水）

用 `qx-mitm-selftest.conf`：只给 `httpbin.org` 加 MITM + 一个只弹通知的脚本。

1. 合并配置 → 保存 → 重启 VPN
2. Safari 打开 `https://httpbin.org/get`
3. 看有没有弹出「✅ MITM 正常」

- **弹了** → MITM 通，问题在 pinning（B），iOS 这条路到头了
- **没弹 / 页面打不开 / 提示"非私人连接"** → 是 A，按下面修

### 修 A（漏一步都不行）

1. QX → 设置 → MitM → 生成证书
2. QX → 设置 → MitM → 配置证书 → Safari 下载描述文件 → 允许
3. iOS 设置 → 通用 → **VPN与设备管理** → 安装 `Quantumult X CA`
4. iOS 设置 → 通用 → 关于本机 → **证书信任设置** → 打开开关 ← **最容易漏**
5. QX → 设置 → MitM → 打开 MitM
6. QX → 设置 → 重写 → 打开重写

修完再跑一次自检，**通过之前别给汽水加任何 MITM 域名**。

### 为什么"广告还在"也是同一个原因

字节系 App 的广告多半**内嵌在主接口的 JSON 里**下发，素材才走 CDN。
所以连接层 REJECT 广告 CDN 只能让素材下不来（App 显示占位/跳过），
广告位本身还在 —— 因为广告数据是跟主接口一起回来的。

**这种广告只能改响应体**，也就是必须 MITM 生效。所以"广告还在"和"VIP 不生效"
不是两个问题，是一个问题的两个表现。

## 当前状态小结

| 能力 | 状态 | 原因 |
|---|---|---|
| 网络正常 | ✅ | 已回滚 qishui 的 MITM |
| 去广告（连接层） | ⚠️ 部分 | 只挡了素材，广告位仍在 |
| VIP / 音效 / 无损 | ❌ | 需要改响应体，MITM 未生效 |
| Mac 端全部功能 | ✅ | 改 asar，已验证 |
