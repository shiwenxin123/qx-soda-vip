/*
 * frida_pinning_bypass.js — 让汽水音乐（iOS/Android）的 TLS 校验放过 MITM 证书
 *
 * 汽水音乐用字节自己的 cronet（libsscronet.so / iOS 同名 dylib）做网络栈，
 * 证书校验在 native 层（IDA 里能看到 VerifyCert 一类的函数，校验失败返回 1）。
 * 这个脚本三条路一起堵：
 *   1. Java 层 TrustManager / OkHttp CertificatePinner / HostnameVerifier 直接放过
 *   2. BoringSSL 通用符号：SSL_get_verify_result → 0、X509_verify_cert → 1、
 *      SSL_CTX_set_verify → 强制 SSL_VERIFY_NONE
 *   3. 扫一遍已加载的所有 so/dylib，把上面这些符号在每个模块里都挂上
 *      （cronet 常把自己的 BoringSSL 静态链进去，符号不一定在 libssl 里）
 *
 * 用法（Android）：
 *   frida -U -f com.soda.music -l frida_pinning_bypass.js --no-pause
 * 用法（iOS，越狱）：
 *   frida -U -f com.soda.music -l frida_pinning_bypass.js
 *
 * 只做"放行证书"，不改业务数据；业务改写交给 mitmproxy addon 或 QX。
 */

'use strict';

var hooked = {};

function log(msg) {
  console.log('[soda-pin] ' + msg);
}

/* ---------------- 1. Java 层 ---------------- */

function hookJava() {
  if (typeof Java === 'undefined' || !Java.available) {
    log('Java 不可用，跳过 Java 层');
    return;
  }
  Java.perform(function () {
    // 1.1 X509TrustManager：所有 checkServerTrusted 变空实现
    try {
      var TM = Java.use('javax.net.ssl.X509TrustManager');
      var cls = Java.enumerateLoadedClassesSync();
      var seen = 0;
      cls.forEach(function (name) {
        if (!/TrustManager|TrustKit|CertificatePinner|HostnameVerifier/i.test(name)) return;
        try {
          var C = Java.use(name);
          if (C.checkServerTrusted) {
            C.checkServerTrusted.overloads.forEach(function (ov) {
              ov.implementation = function () {
                return;
              };
            });
            seen++;
          }
          if (C.verify) {
            C.verify.overloads.forEach(function (ov) {
              if (ov.argumentTypes.length === 2) {
                ov.implementation = function () {
                  return true;
                };
              }
            });
          }
        } catch (e) {}
      });
      log('Java TrustManager 处理 ' + seen + ' 个类');
    } catch (e) {
      log('Java 层 hook 失败: ' + e.message);
    }

    // 1.2 OkHttp CertificatePinner.check(host, peerCertificates) → 直接返回
    try {
      var Pinner = Java.use('okhttp3.CertificatePinner');
      Pinner.check.overloads.forEach(function (ov) {
        ov.implementation = function () {
          return;
        };
      });
      log('OkHttp CertificatePinner 已放过');
    } catch (e) {
      log('没有 okhttp3.CertificatePinner（cronet 不走 OkHttp，正常）');
    }
  });
}

/* ---------------- 2. native BoringSSL ---------------- */

function hookNativeSymbols() {
  var targets = [
    // [符号名, 处理函数]
    ['SSL_get_verify_result', function () { return 0; }],          // 0 = X509_V_OK
    ['X509_verify_cert', function () { return 1; }],               // 1 = 校验通过
    ['X509_verify_cert_error_string', function () { return Memory.allocUtf8String('ok'); }],
    ['SSL_CTX_set_verify', function (ctxPtr, mode, cb) { /* 保留原调用, 下面再补一刀 */ }],
  ];

  // 枚举所有已加载模块，逐个找符号（cronet 把 boringssl 静态链接进去了）
  Process.enumerateModules().forEach(function (mod) {
    targets.forEach(function (t) {
      var name = t[0];
      var key = mod.name + '!' + name;
      if (hooked[key]) return;
      var addr = null;
      try {
        addr = Module.findExportByName(mod.name, name);
      } catch (e) {}
      if (!addr) return;
      try {
        Interceptor.attach(addr, {
          onLeave: function (retval) {
            // 统一把返回值改成"通过"
            if (name === 'SSL_get_verify_result') {
              retval.replace(ptr(0));
            } else if (name === 'X509_verify_cert') {
              retval.replace(ptr(1));
            } else if (name === 'X509_verify_cert_error_string') {
              retval.replace(Memory.allocUtf8String('ok'));
            }
          },
        });
        hooked[key] = true;
        log('hook ' + mod.name + '!' + name + ' @ ' + addr);
      } catch (e) {}
    });
  });

  // SSL_CTX_set_verify：把 mode 里的 SSL_VERIFY_PEER(0x01) 位清掉
  Process.enumerateModules().forEach(function (mod) {
    var addr = null;
    try {
      addr = Module.findExportByName(mod.name, 'SSL_CTX_set_verify');
    } catch (e) {}
    if (!addr || hooked[mod.name + '!setverify']) return;
    try {
      Interceptor.attach(addr, {
        onEnter: function (args) {
          var mode = args[1].toInt32();
          args[1] = ptr(mode & ~0x01); // 清 SSL_VERIFY_PEER
        },
      });
      hooked[mod.name + '!setverify'] = true;
      log('SSL_CTX_set_verify 已降级 @ ' + mod.name);
    } catch (e) {}
  });
}

/* ---------------- 3. 兜底：直接改内存里的校验结果 ---------------- */

function hookFallback() {
  // 有些 cronet 用 SSL_get0_peer_certificates + 自己比对指纹，
  // 那类只能靠 "SSL_get_verify_result" 这一层的返回值骗过去，已在上面处理。
  // 这里再挂一个 SSL_get_verify_result 的导出兜底（libssl / Cronet 都试）。
  ['libssl.so', 'libcronet.so', 'libsscronet.so', 'libttnet.so'].forEach(function (m) {
    var a = null;
    try {
      a = Module.findExportByName(m, 'SSL_get_verify_result');
    } catch (e) {}
    if (!a || hooked[m]) return;
    Interceptor.attach(a, { onLeave: function (r) { r.replace(ptr(0)); } });
    hooked[m] = true;
    log('fallback hook ' + m);
  });
}

/* ---------------- 启动 ---------------- */

setTimeout(function () {
  hookJava();
  hookNativeSymbols();
  hookFallback();
  log('全部就绪；接下来的请求应该能正常解密（mitmproxy 里能看到 qishui.com 的明文）');
}, 0);
