/*
 * qx_mitm_selftest.js — 判断 QX 的 MITM + 重写是否真的生效（v2）
 *
 * v2 改动：不再只弹通知，而是**直接改页面内容**。
 *   因为「页面能打开」证明不了任何事 —— 没解密时页面照样能打开。
 *   唯一可靠的证据是：页面上出现了原本不存在的内容。
 *
 * 用法：见 qx-mitm-selftest.conf
 */

const url = (typeof $request !== 'undefined' && $request && $request.url) || '';
let body = (typeof $response !== 'undefined' && $response && $response.body) || '';

let out = body;

try {
  const j = JSON.parse(body);
  // 往返回的 JSON 里塞一个显眼字段
  j.MITM_SELFTEST = 'MITM_AND_REWRITE_BOTH_WORK';
  j.MITM_TIME = new Date().toISOString();
  out = JSON.stringify(j, null, 2);
} catch (e) {
  // 不是 JSON 就纯文本标记
  out = 'MITM_OK\n' + body;
}

$notify('MITM self-test', 'rewrite works', url.slice(0, 50));
console.log('[selftest] rewrote: ' + url);

// 强制 UTF-8，否则 QX 可能按系统 locale 编码导致中文乱码
const h = Object.assign({}, ($response && $response.headers) || {});
h['Content-Type'] = 'application/json; charset=utf-8';
$done({ body: out, headers: h });
