"""Card infrastructure for the Dongfeng eπ integration.

Registers native Home Assistant custom cards (no HACS frontend needed) that
reuse the official `hui-*` lovelace elements, styled like the Xiaomi car
cards: hero battery ring, status chips, charging progress with power/time,
4-tyre layout, remote action buttons, location card.

Entity matching uses regex over the *actual* entity ids HA generates from
translation keys (e.g. sensor.<device>_battery, binary_sensor.<device>_charging),
so it is stable regardless of the device slug.
"""
from __future__ import annotations

import logging

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARDS_JS_URL = f"/{DOMAIN}/cards.js"

CARDS_JS = r"""
// ---- Dongfeng eπ cards (Xiaomi-style), native custom cards ----
const K = customElements;

// first entity id whose name matches the regex
function F(h, pats) {
  if (!h || !h.states) return null;
  const ids = Object.keys(h.states);
  for (const p of pats) {
    const id = ids.find(x => p.test(x));
    if (id) return id;
  }
  return null;
}
function P(src) { return RegExp ? new RegExp(src) : null; }
function st(h, id) { return id && h.states[id] ? h.states[id] : null; }
function stateOf(h, id) { const s = st(h, id); return s ? s.state : null; }
function unitOf(h, id) { const s = st(h, id); return s && s.attributes ? (s.attributes.unit_of_measurement || '') : ''; }
function nameOf(h, id, dflt) { const s = st(h, id); return (s && s.attributes.friendly_name) || dflt || ''; }

function epiSensors(h) {
  return {
    soc:   F(h, [P('^sensor\\.[a-z0-9_]*battery$'), P('^sensor\\.[a-z0-9_]*power_soc_status$')]),
    range: F(h, [P('^sensor\\.[a-z0-9_]*remaining_range$')]),
    total: F(h, [P('^sensor\\.[a-z0-9_]*total_mileage$')]),
    power: F(h, [P('^sensor\\.[a-z0-9_]*charge_power$')]),
    time:  F(h, [P('^sensor\\.[a-z0-9_]*charge_remaining_time$')]),
    cabin: F(h, [P('^sensor\\.[a-z0-9_]*cabin_temperature$')]),
    out:   F(h, [P('^sensor\\.[a-z0-9_]*outside_temperature$')]),
    speed: F(h, [P('^sensor\\.[a-z0-9_]*speed$')]),
    upd:   F(h, [P('^sensor\\.[a-z0-9_]*last_report$')]),
    tlf: F(h, [P('^sensor\\.[a-z0-9_]*tyre_pressure_lf$')]),
    trf: F(h, [P('^sensor\\.[a-z0-9_]*tyre_pressure_rf$')]),
    tlr: F(h, [P('^sensor\\.[a-z0-9_]*tyre_pressure_lr$')]),
    trr: F(h, [P('^sensor\\.[a-z0-9_]*tyre_pressure_rr$')]),
  };
}
function epiOthers(h) {
  return {
    charging: F(h, [P('^binary_sensor\\.[a-z0-9_]*charging$')]),
    online:   F(h, [P('^binary_sensor\\.[a-z0-9_]*online$')]),
    locked:   F(h, [P('^binary_sensor\\.[a-z0-9_]*locked$')]),
    doors:    F(h, [P('^binary_sensor\\.[a-z0-9_]*doors_open$')]),
    port:     F(h, [P('^binary_sensor\\.[a-z0-9_]*charging_port(_open)?$')]),
    ac:       F(h, [P('^binary_sensor\\.[a-z0-9_]*air_conditioning$')]),
    mirror:   F(h, [P('^binary_sensor\\.[a-z0-9_]*mirror_folded$')]),
    sw:       F(h, [P('^switch\\.[a-z0-9_]*charge_switch$')]),
    btn:      F(h, [P('^button\\.[a-z0-9_]*refresh$')]),
    dt:       F(h, [P('^device_tracker\\.[a-z0-9_]*location$')]),
  };
}

function chip(label, good, text) {
  return `<span class="chip ${good ? 'on' : 'warn'}"><i></i>${label} ${text}</span>`;
}
function esc(x) { return String(x == null ? '' : x).replace(/&/g, '&amp;').replace(/</g, '&lt;'); }

const STYLE = `
 .epi{font-family:system-ui,sans-serif;color:var(--primary-text-color,#eef);padding:2px;}
 .epi .hero{display:flex;gap:18px;align-items:center;flex-wrap:wrap;
   background:linear-gradient(150deg,#14352f 0%,#101a1c 70%);
   border-radius:20px;padding:18px;color:#eafffa;}
 .epi .ring{position:relative;width:132px;height:132px;flex:0 0 auto;}
 .epi .ring svg{transform:rotate(-90deg);}
 .epi .pct{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;align-items:center;}
 .epi .pct b{font-size:33px;font-weight:700;}
 .epi .pct s{font-size:11px;opacity:.6;text-decoration:none;}
 .epi .info{flex:1;min-width:180px;}
 .epi .row{display:flex;justify-content:space-between;font-size:14px;margin:7px 0;}
 .epi .row b{font-size:16px;}
 .epi .chips{display:flex;flex-wrap:wrap;gap:7px;margin-top:9px;}
 .epi .chip{display:inline-flex;align-items:center;gap:5px;font-size:12.5px;padding:5px 11px;
   border-radius:14px;background:rgba(255,255,255,.09);}
 .epi .chip i{width:8px;height:8px;border-radius:50%;background:#7f8b8e;}
 .epi .chip.on i{background:#00e5b0;box-shadow:0 0 6px #00e5b0;}
 .epi .chip.warn i{background:#ffb45a;}
 .epi .upd{font-size:11px;opacity:.45;margin-top:9px;}
 .epi .card{background:var(--card-background-color,#1c1c1e);border-radius:18px;padding:16px;}
 .epi .bar{height:10px;border-radius:5px;background:rgba(128,128,128,.25);overflow:hidden;margin:10px 0;}
 .epi .bar i{display:block;height:100%;border-radius:5px;background:linear-gradient(90deg,#0099A8,#00e5b0);}
 .epi .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(105px,1fr));gap:10px;margin-top:6px;}
 .epi .g{background:rgba(128,128,128,.09);border-radius:12px;padding:10px;text-align:center;}
 .epi .g b{font-size:19px;display:block;}
 .epi .g s{font-size:11px;opacity:.6;text-decoration:none;}
 .epi .tyres{display:grid;grid-template-columns:56px 1fr;gap:14px;align-items:center;}
 .epi .carbox{height:120px;border-radius:24px;background:linear-gradient(180deg,#2c3a3d,#223033);
   border:1px solid rgba(255,255,255,.12);position:relative;}
 .epi .carbox::before,.epi .carbox::after{content:'';position:absolute;left:12px;right:12px;height:20px;
   border-radius:10px;background:rgba(255,255,255,.08);}
 .epi .carbox::before{top:12px;} .epi .carbox::after{bottom:12px;}
 .epi .ty{background:rgba(128,128,128,.09);border-radius:14px;padding:12px;text-align:center;}
 .epi .ty b{font-size:21px;display:block;} .epi .ty s{font-size:11px;opacity:.6;text-decoration:none;}
 .epi .ty.hot b{color:#ff6b6b;} .epi .ty.ok b{color:#00c48c;}
 .epi .acts{display:grid;grid-template-columns:repeat(auto-fit,minmax(88px,1fr));gap:10px;}
 .epi .a{border:none;border-radius:14px;padding:13px 6px;background:rgba(128,128,128,.12);color:inherit;
   cursor:pointer;font-size:12.5px;display:flex;flex-direction:column;gap:7px;align-items:center;}
 .epi .a em{font-style:normal;font-size:21px;} .epi .a:active{transform:scale(.95);}
 .epi .a.on{background:rgba(0,153,168,.3);color:#00d9c0;}
 .epi a{color:#4fb3ff;text-decoration:none;font-size:13px;}
 .epi .empty{opacity:.6;font-size:13px;padding:14px;}
 @media(max-width:520px){.epi .hero{flex-direction:column;align-items:stretch}}`;

class EpiCard extends HTMLElement {
  setConfig(c) { this._c = c || {}; }
  getCardSize() { return 4; }
  set hass(h) {
    this._h = h;
    if (!this.firstChild) { const t = document.createElement('style'); t.textContent = STYLE; this.appendChild(t); }
    if (this._raf) return;
    this._raf = requestAnimationFrame(() => { this._raf = null; this._paint(); });
  }
}

// ---------- hero: battery ring + numbers + chips ----------
class EpiHeroCard extends EpiCard {
  _paint() {
    const h = this._h; if (!h) return;
    const s = epiSensors(h), o = epiOthers(h);
    const soc = s.soc ? Number(stateOf(h, s.soc)) : null;
    const ok = soc != null && !isNaN(soc);
    const col = !ok ? '#5b6b6e' : soc > 50 ? '#00e5b0' : soc > 20 ? '#ffd166' : '#ff6b6b';
    const C = 2 * Math.PI * 54;
    const dash = ok ? C * Math.min(100, Math.max(0, soc)) / 100 : 0;
    const val = id => id ? `${esc(stateOf(h, id))}${unitOf(h, id) || ''}` : '--';
    let chips = '';
    if (o.online) chips += chip('车机', stateOf(h, o.online) === 'on', stateOf(h, o.online) === 'on' ? '在线' : '离线');
    if (o.locked) chips += chip('车门锁', stateOf(h, o.locked) === 'on', stateOf(h, o.locked) === 'on' ? '已上锁' : '未上锁');
    if (o.doors) chips += chip('车门', stateOf(h, o.doors) !== 'on', stateOf(h, o.doors) === 'on' ? '未关' : '已关严');
    if (o.charging) chips += chip('充电', stateOf(h, o.charging) === 'on', stateOf(h, o.charging) === 'on' ? '进行中' : '未充电');
    if (o.port) chips += chip('充电口盖', stateOf(h, o.port) !== 'on', stateOf(h, o.port) === 'on' ? '开' : '关');
    if (o.ac) chips += chip('空调', stateOf(h, o.ac) === 'on', stateOf(h, o.ac) === 'on' ? '运行' : '关闭');
    if (o.mirror) chips += chip('后视镜', stateOf(h, o.mirror) !== 'on', stateOf(h, o.mirror) === 'on' ? '折叠' : '展开');
    let upd = '';
    if (s.upd) { const v = stateOf(h, s.upd); if (v && v !== 'unknown' && v !== 'unavailable') upd = `<div class="upd">数据更新 ${esc(String(v).replace('T', ' ').slice(5, 16))}</div>`; }
    this.innerHTML = `<div class="epi"><div class="hero">
      <div class="ring"><svg width="132" height="132" viewBox="0 0 132 132">
        <circle cx="66" cy="66" r="54" fill="none" stroke="rgba(255,255,255,.10)" stroke-width="10"/>
        <circle cx="66" cy="66" r="54" fill="none" stroke="${col}" stroke-width="10" stroke-linecap="round"
          stroke-dasharray="${dash} ${C}"/></svg>
        <div class="pct"><b>${ok ? Math.round(soc) + '%' : '--'}</b><s>动力电池</s></div></div>
      <div class="info">
        <div class="row"><span>剩余续航</span><b>${val(s.range)}</b></div>
        <div class="row"><span>总里程</span><b>${val(s.total)}</b></div>
        <div class="row"><span>车内 / 车外</span><b>${val(s.cabin)} / ${val(s.out)}</b></div>
        <div class="chips">${chips}</div>${upd}
      </div></div></div>`;
  }
  static async getConfigElement() { return document.createElement('epi-editor'); }
  static getStubConfig() { return {}; }
}
if (!K.get('epi-hero-card')) K.define('epi-hero-card', EpiHeroCard);

// ---------- charging card ----------
class EpiChargeCard extends EpiCard {
  _paint() {
    const h = this._h; if (!h) return;
    const s = epiSensors(h), o = epiOthers(h);
    const soc = s.soc ? Number(stateOf(h, s.soc) || 0) : 0;
    const charging = stateOf(h, o.charging) === 'on';
    const kw = stateOf(h, s.power), mins = stateOf(h, s.time);
    const status = charging ? '充电中' : soc >= 100 ? '已充满' : '未充电';
    this.innerHTML = `<div class="epi"><div class="card">
      <div style="font-size:15px;margin-bottom:4px">⚡ 充电 ${charging ? '· 进行中' : ''}</div>
      <div class="bar"><i style="width:${Math.min(100, soc)}%"></i></div>
      <div class="grid">
        <div class="g"><b>${soc}%</b><s>当前电量</s></div>
        <div class="g"><b>${esc(kw) || '--'}</b><s>功率 kW</s></div>
        <div class="g"><b>${esc(mins) || '--'}</b><s>剩余分钟</s></div>
        <div class="g"><b style="color:${charging ? '#00c48c' : 'inherit'}">${status}</b><s>状态</s></div>
      </div>
      ${o.sw ? '<div style="margin-top:10px"><hui-toggle-entity controls="true" hide-name="true"></hui-toggle-entity></div>' : ''}
    </div></div>`;
    const tg = this.querySelector('hui-toggle-entity');
    if (tg) { tg.hass = h; tg.entityId = o.sw; }
  }
  static async getConfigElement() { return document.createElement('epi-editor'); }
  static getStubConfig() { return {}; }
}
if (!K.get('epi-charge-card')) K.define('epi-charge-card', EpiChargeCard);

// ---------- tyres card ----------
class EpiTyresCard extends EpiCard {
  _paint() {
    const h = this._h; if (!h) return;
    const s = epiSensors(h);
    const cell = (id, label) => {
      const v = id ? Number(stateOf(h, id)) : null;
      const cls = v == null || isNaN(v) ? '' : (v < 200 || v > 300 ? 'hot' : 'ok');
      return `<div class="ty ${cls}"><b>${v == null || isNaN(v) ? '--' : v}</b><s>${label}</s></div>`;
    };
    this.innerHTML = `<div class="epi"><div class="card">
      <div style="font-size:15px;margin-bottom:10px">🛞 胎压监测</div>
      <div class="tyres"><div class="carbox"></div>
        <div class="grid" style="grid-template-columns:1fr 1fr">
          ${cell(s.tlf, '左前')}${cell(s.trf, '右前')}${cell(s.tlr, '左后')}${cell(s.trr, '右后')}
        </div></div></div></div>`;
  }
  static async getConfigElement() { return document.createElement('epi-editor'); }
  static getStubConfig() { return {}; }
}
if (!K.get('epi-tyres-card')) K.define('epi-tyres-card', EpiTyresCard);

// ---------- remote actions card ----------
class EpiActionsCard extends EpiCard {
  _paint() {
    const h = this._h; if (!h) return;
    const o = epiOthers(h);
    const acOn = stateOf(h, o.ac) === 'on';
    const locked = stateOf(h, o.locked) === 'on';
    const swOn = stateOf(h, o.sw) === 'on';
    this.innerHTML = `<div class="epi"><div class="card">
      <div style="font-size:15px;margin-bottom:10px">🎛 远程状态与控制</div>
      <div class="acts">
        <button class="a ${acOn ? 'on' : ''}" data-act="ac"><em>❄️</em>空调 ${acOn ? '运行中' : '已关闭'}</button>
        <button class="a ${!locked ? 'on' : ''}" data-act="lock"><em>🔒</em>车锁 ${locked ? '已上锁' : '未上锁'}</button>
        <button class="a ${swOn ? 'on' : ''}" data-act="charge"><em>⚡</em>充电 ${swOn ? '停止' : '开始'}</button>
        <button class="a" data-act="refresh"><em>🔄</em>刷新状态</button>
      </div></div></div>`;
    this.querySelectorAll('.a').forEach(b => {
      b.onclick = () => {
        const a = b.dataset.act;
        if (a === 'charge' && o.sw) { h.callService('switch', swOn ? 'turn_off' : 'turn_on', { entity_id: o.sw }); }
        else if (a === 'refresh' && o.btn) { h.callService('button', 'press', { entity_id: o.btn }); }
        else if (a === 'ac' || a === 'lock') {
          h.connection.sendMessage({
            type: 'persistent_notification/create',
            title: '奕派',
            message: (a === 'ac' ? '空调' : '车锁') + '控制需接入真实车辆 token 后开启（当前会话为只读状态）',
          });
        }
      };
    });
  }
  static async getConfigElement() { return document.createElement('epi-editor'); }
  static getStubConfig() { return {}; }
}
if (!K.get('epi-actions-card')) K.define('epi-actions-card', EpiActionsCard);

// ---------- location card ----------
class EpiLocCard extends EpiCard {
  _paint() {
    const h = this._h; if (!h) return;
    const o = epiOthers(h);
    const s = st(h, o.dt);
    if (!s) { this.innerHTML = '<div class="epi"><div class="card"><div class="empty">暂无车辆位置实体（device_tracker 未创建）</div></div></div>'; return; }
    const a = s.attributes || {};
    const lat = a.latitude, lon = a.longitude;
    this.innerHTML = `<div class="epi"><div class="card">
      <div style="font-size:15px;margin-bottom:8px">📍 车辆位置</div>
      <div style="font-size:13px;opacity:.65;margin:4px 0">经纬度：${esc(lat)}, ${esc(lon)}</div>
      <div style="font-size:13px;opacity:.65;margin:4px 0">定位时间：${esc(a.position_time || String(s.last_changed).slice(11, 19))}</div>
      ${lat && lon ? `<a href="https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=16/${lat}/${lon}" target="_blank">在地图中查看 →</a>` : ''}
    </div></div>`;
  }
  static async getConfigElement() { return document.createElement('epi-editor'); }
  static getStubConfig() { return {}; }
}
if (!K.get('epi-loc-card')) K.define('epi-loc-card', EpiLocCard);

// ---------- minimal editor (cards take no options) ----------
class EpiEditor extends HTMLElement {
  setConfig(c) { this._c = c; this.innerHTML = '<ha-card><div class="card-content" style="font-size:13px;opacity:.7">奕派卡片自动绑定实体，无需配置选项。</div></ha-card>'; }
}
if (!K.get('epi-editor')) K.define('epi-editor', EpiEditor);

// ---------- custom cards registry (cards picker) ----------
(function () {
  window.customCards = window.customCards || [];
  const reg = [
    { type: 'epi-hero-card', name: '奕派 · 车辆总览', description: '小米风大环电量 + 续航 + 状态徽章' },
    { type: 'epi-charge-card', name: '奕派 · 充电', description: '充电进度、功率与剩余时间' },
    { type: 'epi-tyres-card', name: '奕派 · 胎压', description: '四轮胎压与车身俯视' },
    { type: 'epi-actions-card', name: '奕派 · 远程控制', description: '空调 / 车锁 / 充电 / 刷新' },
    { type: 'epi-loc-card', name: '奕派 · 车辆位置', description: '经纬度与地图链接' },
  ];
  for (const r of reg) {
    if (!window.customCards.some(c => c.type === r.type)) window.customCards.push(r);
  }
})();

window.__epiCardsReady = true;
"""


class EpiCardsJSView(HomeAssistantView):
    """Serve the custom card JS bundle."""

    url = CARDS_JS_URL
    name = "dongfeng_yipai:cards.js"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        return web.Response(
            text=CARDS_JS,
            content_type="application/javascript",
            headers={"Cache-Control": "no-store"},
        )


async def _try_register_resource(hass: HomeAssistant) -> bool:
    """Add cards.js to Lovelace custom resources (idempotent)."""
    collection = hass.data.get("lovelace_resources")
    if collection is None:
        return False
    items = await collection.async_get_items()
    if any(str(i.get("url", "")).endswith(f"/{DOMAIN}/cards.js") for i in items):
        return True
    await collection.async_create_item({"type": "module", "url": CARDS_JS_URL})
    _LOGGER.info("奕派自定义卡片已注册到 Lovelace 资源")
    return True


async def ensure_cards_resources(hass: HomeAssistant) -> None:
    """Serve cards.js over HTTP and register it into Lovelace resources."""
    if not hass.http or not hasattr(hass.http, "register_view"):
        return

    data = hass.data.setdefault(DOMAIN, {})
    if not data.get("_cards_view"):
        hass.http.register_view(EpiCardsJSView())
        data["_cards_view"] = True

    try:
        if await _try_register_resource(hass):
            return
    except Exception:  # pragma: no cover - best effort
        _LOGGER.debug("奕派卡片资源立即注册失败，启动完成后重试", exc_info=True)

    if data.get("_cards_hook"):
        return
    data["_cards_hook"] = True

    async def _retry() -> None:
        import asyncio

        for _ in range(6):
            await asyncio.sleep(10)
            try:
                if await _try_register_resource(hass):
                    return
            except Exception:  # noqa: BLE001
                pass

    from homeassistant.core import Event, callback

    @callback
    def _on_started(_ev: Event) -> None:
        hass.async_create_task(_retry())

    hass.bus.async_listen_once("homeassistant_started", _on_started)
