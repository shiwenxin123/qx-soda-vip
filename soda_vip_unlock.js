/*
 * soda_vip_unlock.js — 汽水音乐 VIP 状态 / 会员曲目解锁（响应体重写）
 *
 * 适用：Quantumult X / Surge / Loon 的 script-response-body
 * 用法：见同目录 soda_vip_unlock.conf
 *
 * 原理：服务端返回的 JSON 里，客户端的"要不要拦你"完全依赖这几个字段：
 *   commerce.membership.is_membership / membership_type
 *   commerce.trade.has_paid_order
 *   commerce.benefit_quality_map（各音质的时间窗）
 *   commerce.has_play_entitlement
 *   track.label_info.only_vip_playable / only_vip_download
 *   track.limited_free_info.limited_free
 *   video_model_type === 2（服务端说"这条是试听片段"）
 * 这里把它们统一改成"会员 + 可播 + 完整音源"的样子。
 *
 * 注意：音频地址本身由服务端签名下发。若接口回的 main_url 就是 30s 试听切片，
 *       客户端 / 代理都变不出完整音频，这条规则只能保证"客户端不再拦、不再降级、
 *       不再弹会员窗、音质请求按最高走"。判定方法见 README。
 */

const NOW = Math.floor(Date.now() / 1000);
const FAR = 4102444799; // 2099-12-31

// 一律改 true
const FORCE_TRUE = new Set([
  'is_vip', 'is_svip', 'is_membership', 'is_paying_user', 'is_paid',
  'has_paid_order', 'has_play_entitlement', 'has_download_entitlement',
  'limited_free', 'is_limited_free', 'is_ad_free', 'vip_valid',
  'can_play', 'can_play_full', 'playable', 'is_full'
]);

// 一律改 false（这些是"锁"）
const FORCE_FALSE = new Set([
  'only_vip_playable', 'only_vip_download', 'only_vip',
  'vip_only', 'need_vip', 'need_pay', 'need_purchase',
  'is_preview', 'is_preview_only', 'preview_only', 'is_trial',
  'is_about_to_expire', 'on_sale', 'locked'
]);

// 时间戳类字段拉到 2099
const EXPIRE_KEYS = new Set([
  'expire_time', 'expire_at', 'vip_expire_at', 'vip_expire_time',
  'membership_expire_time', 'end_time', 'valid_until', 'expired_at'
]);

const BENEFIT_FLAGS = [
  'benefit_play_spatial',
  'benefit_play_lossless',
  'benefit_play_highest',
  'benefit_play_higher',
  'benefit_play_medium'
];

function isObj(v) {
  return v && typeof v === 'object' && !Array.isArray(v);
}

function fullBenefitMap() {
  const m = {};
  for (const k of BENEFIT_FLAGS) m[k] = { start_time: 0, end_time: FAR };
  return m;
}

function fixMembership(o) {
  if (!isObj(o)) return;
  o.is_membership = true;
  o.is_paying_user = true;
  o.is_about_to_expire = false;
  if (!o.membership_type || o.membership_type === 'free' || o.membership_type === 'none') {
    o.membership_type = 'vip';
  }
  if ('expire_time' in o || o.membership_type) o.expire_time = FAR;
  if ('last_membership_type' in o) o.last_membership_type = o.membership_type;
  // 会员明细表：保证 vip / svip 两个槽都在且不过期
  if (isObj(o.membership_detail_map_v2) || 'membership_detail_map_v2' in o) {
    o.membership_detail_map_v2 = o.membership_detail_map_v2 || {};
    for (const t of ['vip', 'svip']) {
      const cur = o.membership_detail_map_v2[t] || {};
      cur.expire_time = FAR;
      cur.is_auto_renew = cur.is_auto_renew || false;
      o.membership_detail_map_v2[t] = cur;
    }
  }
}

function walk(node, depth) {
  if (depth > 12 || node === null || typeof node !== 'object') return node;
  if (Array.isArray(node)) {
    for (let i = 0; i < node.length; i++) node[i] = walk(node[i], depth + 1);
    return node;
  }

  for (const key of Object.keys(node)) {
    const v = node[key];

    if (FORCE_TRUE.has(key) && (v === false || v === 0 || v === null)) { node[key] = true; continue; }
    if (FORCE_FALSE.has(key) && (v === true || v === 1)) { node[key] = false; continue; }
    if (EXPIRE_KEYS.has(key) && typeof v === 'number' && v > 0 && v < NOW + 86400 * 30) {
      node[key] = FAR; continue;
    }

    if (key === 'membership_type' && typeof v === 'string' && /free|none|normal/.test(v)) {
      node[key] = 'vip'; continue;
    }
    if (key === 'group_payment_level') { node[key] = '0'; continue; }
    if (key === 'membership' || key === 'membership_info') { fixMembership(v); node[key] = walk(v, depth + 1); continue; }

    if (key === 'benefit_quality_map') {
      node[key] = Object.assign({}, v || {}, fullBenefitMap()); continue;
    }
    if (key === 'benefit_base' && isObj(v)) {
      v.quality = Object.assign({}, v.quality || {}, fullBenefitMap());
      node[key] = v; continue;
    }

    // 曲目标签：锁标记全清
    if (key === 'label_info' && isObj(v)) {
      v.only_vip_playable = false;
      v.only_vip_download = false;
      v.on_sale = false;
      node[key] = v; continue;
    }
    if (key === 'limited_free_info' && isObj(v)) { v.limited_free = true; node[key] = v; continue; }

    // 服务端说"这是试听版" —— 改成完整音源，客户端才会按 F 资源请求
    if (key === 'video_model_type' && v === 2) { node[key] = 1; continue; }

    node[key] = walk(v, depth + 1);
  }
  return node;
}

let body = $response.body || '';
let out;

try {
  const json = JSON.parse(body);
  walk(json, 0);
  out = JSON.stringify(json);
} catch (e) {
  // 非 JSON（protobuf / 二进制 / HTML）原样放行
  out = body;
}

$done({ body: out });
