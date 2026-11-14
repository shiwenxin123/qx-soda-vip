# qx-soda-vip

汽水音乐（Soda Music）Mac 端的 Quantumult X 响应体重写脚本：把服务端下发的会员态、
会员曲目标记、音质权益统一改写成"已开通、可播、完整音源"。

> 只做客户端/流量层的字段改写。服务端签发的音频地址本身不受控制——若接口下发的
> `main_url` 就是 60 秒试听切片，这条规则变不出完整音轨。

## 用法

### 1. 安装证书并开启 MitM

QX → 设置 → MitM → 生成证书 → 安装到系统钥匙串 → 设为"始终信任"。
QX 的根证书本身已在解密 `*.qishui.com`（可用下面命令确认）：

```bash
echo | openssl s_client -connect api.qishui.com:443 \
  -servername api.qishui.com 2>/dev/null | openssl x509 -noout -issuer -subject
# issuer= /OU=CA/CN=Quantumult X CA xxxx
# subject= .../CN=*.qishui.com
```

### 2. 加一条重写规则

QX → 重写规则 → `+`：

| 字段 | 值 |
|---|---|
| 类型 | `script-response-body` |
| 用以匹配的 URL | `^https?:\/\/[^\/]*qishui\.com\/` |
| 脚本路径 | 下方 raw 地址之一 |
| 保存至 | 当前配置文件 |

脚本地址二选一（国内建议 jsDelivr，raw.githubusercontent 有时连不上）：

```
# jsDelivr（推荐）
https://cdn.jsdelivr.net/gh/shiwenxin123/qx-soda-vip@main/soda_vip_unlock.js

# GitHub raw（国内常被墙，备用）
https://raw.githubusercontent.com/shiwenxin123/qx-soda-vip/main/soda_vip_unlock.js
```

改了脚本想让 QX 重新拉取：把规则删掉重加一次，或 QX 里清一次脚本缓存。

`[mitm] hostname` 需要覆盖实际域名，形如：

```
hostname = api.qishui.com, *.qishui.com, aweme.snssdk.com, lf-*.douyin.com
```

## 改写了哪些字段

| 类别 | 字段 | 处理 |
|---|---|---|
| 会员态 | `is_vip` `is_svip` `is_membership` `is_paying_user` `has_paid_order` `has_play_entitlement` `is_ad_free` | 置 `true` |
| 会员态 | `membership_type`（`free`/`none`/`normal`） | 改 `vip` |
| 会员态 | `expire_time` `end_time` `vip_expire_at` … | 拉到 2099 |
| 会员明细 | `membership_detail_map_v2.vip` / `.svip` | 补 `expire_time`，去掉 `is_about_to_expire` |
| 曲目锁 | `only_vip_playable` `only_vip_download` `vip_only` `need_pay` `on_sale` `locked` | 置 `false` |
| 曲目锁 | `limited_free` `is_limited_free` | 置 `true` |
| 试听标记 | `is_preview` `is_trial` `preview_only` | 置 `false` |
| 试听标记 | `video_model_type == 2` | 改 `1` |
| 音质权益 | `benefit_quality_map` / `benefit_base.quality` | 注入 5 项 `benefit_play_*` 全时段 |
| 商务埋点 | `group_payment_level` | 改 `"0"` |

## 自测

用真实结构跑一遍，确认改写结果：

```bash
node -e '
global.$response={body:JSON.stringify({commerce:{membership:{is_membership:false,membership_type:"free"},is_vip:false,has_play_entitlement:false},
track:{label_info:{only_vip_playable:true,on_sale:true},video_model:{video_model_type:2}}})};
global.$done=r=>{const o=JSON.parse(r.body);console.log(o.commerce.is_vip,o.commerce.membership.membership_type,o.track.label_info.only_vip_playable,o.track.video_model.video_model_type)};
require("./soda_vip_unlock.js")'
# 期望输出：true vip false 1
```

## 许可

仅用于本机研究与互操作实验，不附带任何担保。

## 手机端（iOS / Android）

Mac 的改包方案不适用于手机；手机走流量改写，脚本与本仓库同一个文件。

- **iOS**：Quantumult X 装证书 → 加重写规则 → 验证是否被证书 pinning 挡。
  详见 [`mobile/ios/README.md`](mobile/ios/README.md)
- **Android**：先跑 `mobile/android/probe_apk.py` 判断能不能改包，
  再按结果选「改 APK / mitmproxy+Frida / Surfboard」。
  详见 [`mobile/android/README.md`](mobile/android/README.md)

两个通用的核对工具：

- `mobile/android/soda_vip_unlock_mitm.py` — mitmproxy 插件，改写逻辑与 JS 版一致
- `mobile/android/frida_pinning_bypass.js` — 过字节 cronet（libsscronet）的证书校验
- `mobile/tools/mp4_duration.py` — 读落盘音频的真实时长/码率，判断是否拿到完整音源

手机端第一件事不是装脚本，是**判断 App 让不让你解密流量**：汽水用字节自家 cronet，
证书校验在 native 层，iOS 不越狱过不去；Android 有 root 可以用 Frida 过。
