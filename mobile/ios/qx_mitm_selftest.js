/*
 * qx_mitm_selftest.js — 判断 QX 的 MITM 到底通不通（不碰汽水，零风险）
 *
 * 用法：见 qx-mitm-selftest.conf
 *
 * 逻辑：
 *   这个脚本只会被 QX 在「成功解密 HTTPS」后调用。
 *   所以只要它跑起来（JS 计数 +1 / 弹通知），就证明：
 *     QX 根证书已安装 + 已在「证书信任设置」里打开 + MITM 开关已开
 *   如果它不跑，那跟汽水无关，是你 QX 的证书链路有问题。
 */

const url = ($request && $request.url) || '';

// 弹一条通知，肉眼可见
$notify(
  '✅ MITM 正常',
  '脚本已执行',
  url.slice(0, 60)
);

// 顺便把结果存起来，方便之后查
$prefs.setValueForKey(
  JSON.stringify({ t: new Date().toISOString(), url }),
  'mitm_selftest_last'
);

console.log('[selftest] MITM OK: ' + url);

// 原样放行，不改任何东西
$done({});
