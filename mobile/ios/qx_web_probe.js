/*
 * qx_web_probe.js — 网页版请求探针（Quantumult X / Surge 通用）
 *
 * 用途：把汽水音乐网页版的全部请求记下来，用于找出：
 *   1. 广告配置接口（缩短时长用）
 *   2. 播放上报接口（完成度校验）
 *   3. 领奖接口（自动化核心）
 *
 * 用法见 网页版-自动看广告方案.md
 *
 * 记录存在 QX 本地键 soda_web_log（最多 60 条，去重计数）。
 * 查看：QX → 设置 → 脚本 → 存储，或任意脚本里 $prefs.valueForKey('soda_web_log')
 */

const KEY = 'soda_web_log';
const MAX = 60;

// 只记录可能跟广告/任务/奖励有关的
const HINT = /(ad|ads|advert|reward|task|claim|receive|incentive|coin|gold|benefit|vip|member|duration|play_log|report)/i;

function load() {
  try {
    const raw = $prefs.valueForKey(KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function save(list) {
  try {
    $prefs.setValueForKey(JSON.stringify(list.slice(-MAX)), KEY);
  } catch (e) {}
}

const url = (typeof $request !== 'undefined' && $request && $request.url) || '';
const method = (typeof $request !== 'undefined' && $request && $request.method) || 'GET';

if (url && HINT.test(url)) {
  const list = load();
  const path = url.split('?')[0];
  const hit = list.find((x) => x.p === path && x.m === method);

  if (hit) {
    hit.n = (hit.n || 1) + 1;
    hit.t = new Date().toISOString().slice(11, 19);
  } else {
    list.push({
      t: new Date().toISOString().slice(11, 19),
      m: method,
      p: path,
      u: url,
      n: 1,
    });
    // 新接口首次出现时提醒
    $notify('新接口', method + ' ' + path.slice(-50), '共 ' + list.length + ' 条');
  }
  save(list);
  console.log('[soda-web] ' + method + ' ' + url);
}

$done({});
