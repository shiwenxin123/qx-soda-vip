/*
 * qx_soda_ad_probe.js — 广告接口探针（Quantumult X / Surge / Loon 通用）
 *
 * 目的：把汽水音乐里跟广告/激励相关的请求 URL 抓出来，用于两种用途：
 *   1. 精确点掉广告位（reject 掉正确的那个接口，而不是盲目屏蔽）
 *   2. 如果你想「自动看广告换听歌时长」，需要先知道"看完广告发奖励"那个回调
 *
 * 用法（QX）：
 *   [rewrite_local]
 *   ^https?:\/\/[^\/]*qishui\.com\/ url script-request-header https://cdn.jsdelivr.net/gh/shiwenxin123/qx-soda-vip@main/mobile/ios/qx_soda_ad_probe.js
 *   [mitm]
 *   hostname = ...(和主配置一样)
 *
 * 命中后会推送一条通知，并把最近 20 条记录存在 QX 本地（键名 soda_ad_probe）。
 * 看完一轮广告后，在 QX 的「脚本测试/存储」或任意脚本里读：
 *   $prefs.valueForKey('soda_ad_probe')
 */

const KEY = 'soda_ad_probe';
const MAX = 20;

// 只记录"可能跟广告/奖励有关"的请求，避免噪音把存储刷满
const HINT = /(media_ads|media_ad|ad_config|ad_configs|\bad\b|\bad_|_ad\b|ads|advert|advertise|reward|incentive|incent|ecpm|csj|pangolin|pangle|toutiao|union|激励|广告)/i;

function readStore() {
  try {
    const raw = $prefs.valueForKey(KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function saveStore(list) {
  try {
    $prefs.setValueForKey(JSON.stringify(list.slice(-MAX)), KEY);
  } catch (e) {}
}

const url = ($request && $request.url) || '';
const method = ($request && $request.method) || 'GET';

if (url && HINT.test(url)) {
  const rec = {
    t: new Date().toISOString().slice(11, 19),
    m: method,
    u: url,
  };
  const list = readStore();
  // 相同路径去重，但保留次数
  const key = url.split('?')[0] + method;
  const hit = list.find((x) => x.u.split('?')[0] + x.m === key);
  if (hit) {
    hit.n = (hit.n || 1) + 1;
    hit.t = rec.t;
  } else {
    rec.n = 1;
    list.push(rec);
  }
  saveStore(list);

  // 只在首次命中时打扰你，避免刷屏
  if (!hit) {
    const short = url.replace(/^https?:\/\//, '').slice(0, 80);
    $notify('汽水广告接口', method + ' ' + short, '已记录（累计 ' + list.length + ' 条）');
  }
}

$done({});
