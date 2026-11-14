/*
 * qx_soda_ad_auto.js — 「看完广告自动领奖励」模板（Quantumult X）
 *
 * ⚠ 这是模板，不是开箱即用：不同版本汽水的激励接口路径/参数会变，
 *   先用 qx_soda_ad_probe.js 抓出真实接口，把下面的 AD_DONE_PATTERN 和
 *   buildRewardBody() 改对，再启用。
 *
 * 思路（三种，按可行性排序）：
 *   甲. 直接静音掉广告：把广告素材请求 reject 掉，客户端无素材可播 → 多数实现会直接
 *       判定"失败/跳过"，但有的版本会给"补偿时长"。稳定性差，先试。
 *   乙. 改写广告时长：把广告配置里的 duration 改成 0/1 秒，让播放器瞬间播完。
 *   丙. 重放奖励回调：抓到 "reward/完成观看" 的 POST，按原样重放 N 次。
 *       最有效，但最容易被判异常（同一个 request_id 复用会被服务端拒）。
 *
 * 下面实现的是「乙 + 丙」的组合骨架。
 */

const AD_DONE_PATTERN = /(reward|incentive|ad_complete|watch_ad|finish_ad)/i;
const REWARD_TIMES = 5; // 每轮补几次

// 汽水广告配置接口（先用 probe 确认路径）
const AD_CONFIG_PATTERN = /\/luna\/(media_ads|ad_config|feed.*ad)/i;

/* ---------- 乙：把广告时长改短 ---------- */
function shrinkAdConfig(body) {
  try {
    const j = JSON.parse(body);
    const walk = (o, d) => {
      if (!o || typeof o !== 'object' || d > 10) return;
      for (const k of Object.keys(o)) {
        if (/^(duration|video_duration|ad_duration|play_duration)$/i.test(k) && typeof o[k] === 'number') {
          o[k] = 1;
        }
        if (/^(skip_time|skippable_after|can_skip_after)$/i.test(k) && typeof o[k] === 'number') {
          o[k] = 0;
        }
        walk(o[k], d + 1);
      }
    };
    walk(j, 0);
    return JSON.stringify(j);
  } catch (e) {
    return null;
  }
}

/* ---------- 丙：重放奖励 ---------- */
function replayReward() {
  // 这里需要你把 probe 抓到的真实接口填进来
  // 例：
  // const req = {
  //   url: 'https://api5-lf.qishui.com/luna/xxx/reward',
  //   headers: { 'Content-Type': 'application/json', Cookie: $request.headers.Cookie },
  //   body: JSON.stringify({ task_id: '...', ad_id: '...' }),
  // };
  // let left = REWARD_TIMES;
  // const fire = () => {
  //   if (left-- <= 0) return;
  //   $task.fetch(req).then(() => setTimeout(fire, 1500)).catch(() => setTimeout(fire, 3000));
  // };
  // fire();
  console.log('[soda-ad] replayReward 未配置：先用 probe 抓接口再填这里');
}

const url = ($request && $request.url) || '';
const method = ($request && $request.method) || 'GET';

/* 请求阶段：命中奖励接口 → 记录（供重放） */
if (method === 'POST' && AD_DONE_PATTERN.test(url)) {
  $prefs.setValueForKey(
    JSON.stringify({ url, headers: $request.headers, body: $request.body || '' }),
    'soda_last_reward_req'
  );
  console.log('[soda-ad] 捕获奖励请求: ' + url);
}

/* 响应阶段：命中广告配置 → 缩时长 */
let body = typeof $response !== 'undefined' && $response.body ? $response.body : null;
if (body && AD_CONFIG_PATTERN.test(url)) {
  const shrunk = shrinkAdConfig(body);
  if (shrunk) {
    console.log('[soda-ad] 广告配置时长已压缩: ' + url);
    $done({ body: shrunk });
  } else {
    $done({});
  }
} else {
  $done({});
}
