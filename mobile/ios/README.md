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
