# 安卓版：汽水音乐 VIP 解锁

安卓比 iOS 灵活：**能改 APK，也能过证书校验**。三条路线，按"要不要 root"排序。

先跑一遍探针，决定走哪条：

```bash
python3 mobile/android/probe_apk.py /path/to/汽水音乐.apk
```

它会告诉你：有没有加固、字段在不在明文 bundle 里、网络栈是什么、有没有 pinning 特征。

---

## 路线 A：改 APK（不用 root，但会掉登录态）

**前提**：探针显示 `未发现常见加固库` + 关键字段命中在 `assets/*.js` 里。

汽水的会员判定和 Mac 版同源（同一套 `only_vip_playable` / `hasPlayEntitlement` 字段），
如果业务代码在 assets 的 JS bundle 里，改法和 Mac 完全一样：

```bash
# 1. 解包
apktool d -f -s 汽水音乐.apk -o soda_src      # -s 不反编译 dex，快
# 或者直接 unzip（如果只需要改 assets）
unzip -o 汽水音乐.apk 'assets/*' -d soda_src

# 2. 找到 bundle，按 Mac 版那 13 条补丁点改
grep -rl "only_vip_playable" soda_src/assets/

# 3. 重打包
zip -r soda_patched.apk . -x "*.apk"

# 4. 重新签名（必须，否则装不上）
keytool -genkey -v -keystore soda.keystore -alias soda -keyalg RSA -keysize 2048 -validity 10000
apksigner sign --ks soda.keystore --ks-pass pass:123456 soda_patched.apk
adb install -r soda_patched.apk
```

> 代价：换签名 = 新应用身份，**登录态、收藏、缓存全丢**，而且大概率触发服务端的签名校验/风控。
> 所以只有"确实没加固、字段明文"时才值得走这条。

## 路线 B：mitmproxy + Frida（要 root，最稳）

汽水用 `libsscronet.so`（字节自家 cronet），证书校验在 native 层，
**直接挂代理会看到证书错误**，必须先过 pinning。

### B1. 装证书

```bash
# 电脑上跑 mitmproxy，先让它生成 CA
mitmdump --listen-port 8080     # 启动后 ~/.mitmproxy/mitmproxy-ca-cert.cer 生成
```

安卓 7 以后**用户证书不被 App 信任**，必须装成系统证书：

```bash
# 有 Magisk：装 "Move Certificates" 模块，把用户证书搬进系统
# 或者手动（需要 root + remount）
HASH=$(openssl x509 -inform PEM -subject_hash_old -in mitmproxy-ca-cert.pem | head -1)
cp mitmproxy-ca-cert.pem /system/etc/security/cacerts/$HASH.0
chmod 644 /system/etc/security/cacerts/$HASH.0
# 重启
```

### B2. 过 pinning

```bash
# 手机连电脑，装 frida-server 并启动
frida -U -f com.soda.music -l mobile/android/frida_pinning_bypass.js --no-pause
```

脚本做三件事：Java 层 TrustManager/OkHttp 放过、BoringSSL `SSL_get_verify_result`→0 /
`X509_verify_cert`→1、`SSL_CTX_set_verify` 清掉 `SSL_VERIFY_PEER` 位。
日志里出现 `全部就绪` 就说明挂上了。

### B3. 跑改写

```bash
mitmdump -s mobile/android/soda_vip_unlock_mitm.py --listen-host 0.0.0.0 --listen-port 8080
# 手机 Wi-Fi → 代理 → 手动 → <电脑内网IP>:8080
```

看到 `[soda] rewrote api.qishui.com/...` 就是命中并改写成功了。

## 路线 C：机内代理 + 脚本（Surfboard，要 root）

不想让电脑常开，可以用安卓的 Surfboard（支持 MITM + 脚本，脚本 API 和 Surge/Loon 同款）：

```
[Script]
http-response ^https?:\/\/[^\/]*qishui\.com\/ script-path=https://cdn.jsdelivr.net/gh/shiwenxin123/qx-soda-vip@main/soda_vip_unlock.js, requires-body=true, timeout=60
```

仓库里的 `soda_vip_unlock.js` 用的是 `$response.body` / `$done({body})`，与 Surfboard 兼容，
**不用改脚本**。但 Surfboard 没有 native hook，pinning 一样要先用 Frida/so patch 处理掉。

---

## 验证

和 Mac 版同一套判据——看**落盘的音频**，别看播放条：

```bash
# 找缓存（路径随版本变，先看应用数据目录）
adb shell "ls -l /sdcard/Android/data/com.soda.music/cache 2>/dev/null | head"
adb pull /sdcard/Android/data/com.soda.music/cache ./soda_cache/

python3 mobile/tools/mp4_duration.py ./soda_cache/
```

输出示例（Mac 上实测过）：

```
16:36  1db8b045   8.7M  223.8s   324k
16:36  91cd76ff   0.9M   60.0s   132k  ← 试听片段
```

- `180~260s / 320k` 或 `900k+`（无损）→ 完整音源，成了
- `30s` / `60s` → 服务端只签发试听，客户端和代理都变不出完整音频

## 三条路线怎么选

| | 要 root | 掉登录态 | 成功率 | 适合 |
|---|---|---|---|---|
| A 改 APK | 否 | 是 | 看是否加固 | 探针显示明文且未加固 |
| B mitmproxy+Frida | 是 | 否 | 高 | 折腾得起、要保账号 |
| C Surfboard | 是 | 否 | 中（仍要过 pinning） | 想脱离电脑 |

> 补充：如果只是为了听歌，安卓还有更省事的一条——**用 Mac 版**（已经装好且验证过），
> 手机端不折腾。三条路线里 B 最接近 Mac 的体验。
