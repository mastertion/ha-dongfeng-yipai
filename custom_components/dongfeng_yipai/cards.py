"""Card infrastructure for the Dongfeng eπ integration.

Registers native Home Assistant custom cards (no HACS frontend needed) that
reuse the official `hui-*` lovelace elements, styled like the Xiaomi car
cards: hero battery gauge with ring, mileage/range glance, status chips,
charging progress with power/time, 4-tyre layout, remote action buttons.
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
// ---- Dongfeng eπ cards, registered as native HA custom cards ----
const K = customElements;
if (window.loadLovelace) { window.loadLovelace(); }

function normState(s){ return s===undefined||s===null?String.prototype:' '+s+' '; }
function pickIds(hass, keys){
  const out={};
  for (const [k, cands] of Object.entries(keys)){
    for (const c of cands){
      if (hass.states[c]) { out[k]=c; break; }
    }
    out[k]=out[k]||null;
  }
  return out;
}

// ---------- 1) epi-hero-card : big battery ring + range + status chips ----
class EpiHeroCard extends HTMLElement {
  setConfig(c){ this._c=c||{}; }
  static async getConfigElement(){ return document.createElement('epi-hero-editor'); }
  static getStubConfig(){ return {entity:null, range:null}; }
  set hass(h){
    this._h=h; if(!this.firstChild) this.appendChild(this._tpl());
    this._render();
  }
  _tpl(){
    const t=document.createElement('style');
    t.textContent=`
     .eh{font-family:system-ui,sans-serif;background:linear-gradient(150deg,#14352f 0%,#101a1c 70%);
        border-radius:20px;padding:18px;color:#eafffa;display:flex;gap:18px;align-items:center;flex-wrap:wrap;}
     .eh .ring{position:relative;width:140px;height:140px;flex:0 0 auto;}
     .eh svg{transform:rotate(-90deg);}
     .eh .pct{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;align-items:center;}
     .eh .pct b{font-size:34px;font-weight:700;}
     .eh .pct s{font-size:11px;opacity:.6;text-decoration:none;}
     .eh .info{flex:1;min-width:180px;}
     .eh .row{display:flex;justify-content:space-between;font-size:14px;margin:7px 0;}
     .eh .row b{font-size:16px}
     .eh .chips{display:flex;flex-wrap:wrap;gap:7px;margin-top:9px;}
     .eh .chip{display:inline-flex;align-items:center;gap:5px;font-size:12.5px;padding:5px 11px;
        border-radius:14px;background:rgba(255,255,255,.09);}
     .eh .chip i{width:8px;height:8px;border-radius:50%;background:#7f8b8e;}
     .eh .chip.on i{background:#00e5b0;box-shadow:0 0 6px #00e5b0;}
     .eh .chip.warn i{background:#ffb45a;}
     .eh .upd{font-size:11px;opacity:.45;margin-top:9px;}
     @media(max-width:520px){.eh{flex-direction:column;align-items:stretch}}`;
    return t;
  }
  _render(){
    if(!this._h||!this._c) return;
    const h=this._h;
    const ids=pickIds(h,{
      soc:[this._c.entity,...['sensor.yipai_powersocstatus','sensor.epai_000001_power_soc_status'].filter(Boolean)],
      range:[this._c.range,'sensor.yipai_endurancemileage','sensor.epai_000001_endurance_mileage'],
      total:['sensor.yipai_totalmileage','sensor.epai_000001_total_mileage'],
      cabin:['sensor.yipai_accabintemperature','sensor.epai_000001_ac_cabin_temperature'],
      out:['sensor.yipai_outtemperature','sensor.epai_000001_out_temperature'],
      updt:['sensor.yipai_updatetime','sensor.epai_000001_update_time'],
      charging:['binary_sensor.yipai_charging','binary_sensor.epai_000001_charging'],
      online:['binary_sensor.yipai_online','binary_sensor.epai_000001_online'],
      locked:['binary_sensor.yipai_locked','binary_sensor.epai_000001_locked'],
      doors:['binary_sensor.yipai_doors','binary_sensor.epai_000001_doors'],
      port:['binary_sensor.yipai_charging_port','binary_sensor.epai_000001_charging_port'],
      ac:['binary_sensor.yipai_ac_on','binary_sensor.epai_000001_ac_on'],
    });
    const st=id=>h.states[id];
    const soc=ids.soc?Number(st(ids.soc).state):null;
    const socOn = soc!=null && !isNaN(soc);
    const col = socOn ? (soc>50?'#00e5b0':soc>20?'#ffd166':'#ff6b6b') : '#5b6b6e';
    const C=2*Math.PI*58;
    const dash = socOn ? C*Math.min(100,soc)/100 : 0;
    const chip=(id,label,onIs,notId)=>{
      if(!id) return '';
      const s=st(id); const on = s.state==='on';
      const good = (onIs? on : !on);
      return `<span class="chip ${good?'on':'warn'}"><i></i>${label} ${on? (notId||'开'):( (this._c.off&&this._c.off[label])||'关')}</span>`;
    };
    const lockChip = ids.locked? (()=>{const s=st(ids.locked);return `<span class="chip ${s.state==='on'?'on':'warn'}"><i></i>车门 ${s.state==='on'?'已上锁':'未上锁'}</span>`})() : '';
    const chgChip = ids.charging? (()=>{const s=st(ids.charging);return `<span class="chip ${s.state==='on'?'on':''}"><i></i>充电 ${s.state==='on'?'进行中':'未充电'}</span>`})() : '';
    const onChip = ids.online? (()=>{const s=st(ids.online);return `<span class="chip ${s.state==='on'?'on':'warn'}"><i></i>车机 ${s.state==='on'?'在线':'离线'}</span>`})() : '';
    const v=(id,u)=>id?`${st(id).state}${u||st(id).attributes.unit_of_measurement||''}`:'--';
    let upd='';
    if(ids.updt){const s=st(ids.updt); if(s.state!=='unknown'&&s.state!=='unavailable') upd=`<div class="upd">更新于 ${s.state.replace('T',' ').slice(5,16)}</div>`;}
    this.innerHTML=`<div class="eh">
      <div class="ring"><svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r="58" fill="none" stroke="rgba(255,255,255,.10)" stroke-width="10"/>
        <circle cx="70" cy="70" r="58" fill="none" stroke="${col}" stroke-width="10" stroke-linecap="round"
          stroke-dasharray="${dash} ${C}"/>
      </svg><div class="pct"><b>${socOn?Math.round(soc)+'%':'--'}</b><s>动力电池</s></div></div>
      <div class="info">
        <div class="row"><span>剩余续航</span><b>${v(ids.range,' km')}</b></div>
        <div class="row"><span>总里程</span><b>${v(ids.total,' km')}</b></div>
        <div class="row"><span>车内 / 车外</span><b>${v(ids.cabin,'℃')} / ${v(ids.out,'℃')}</b></div>
        <div class="chips">${onChip}${lockChip}${chgChip}
          ${chip(ids.doors,'车门',false)}${chip(ids.port,'充电口盖',true)}${chip(ids.ac,'空调',true)}
        </div>${upd}
      </div></div>`;
    this.style.display='block';
  }
}
if(!K.get('epi-hero-card')) K.define('epi-hero-card', EpiHeroCard);

// ---------- 2) epi-charge-card : charging progress + power/time + switch ----
class EpiChargeCard extends HTMLElement {
  setConfig(c){ this._c=c||{}; }
  static async getConfigElement(){ return document.createElement('epi-hero-editor'); }
  set hass(h){ this._h=h; if(!this.firstChild)this.appendChild(this._tpl()); this._render(); }
  _tpl(){const t=document.createElement('style');t.textContent=`
    .ec{font-family:system-ui,sans-serif;background:var(--card-background-color,#1c1c1e);border-radius:18px;padding:16px;color:var(--primary-text-color,#eee);}
    .ec .hd{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;}
    .ec .hd b{font-size:15px}
    .ec .bar{height:10px;border-radius:5px;background:rgba(128,128,128,.25);overflow:hidden;margin:10px 0;}
    .ec .bar i{display:block;height:100%;border-radius:5px;background:linear-gradient(90deg,#0099A8,#00e5b0);}
    .ec .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:10px;margin-top:6px;}
    .ec .g{background:rgba(128,128,128,.09);border-radius:12px;padding:9px;text-align:center;}
    .ec .g b{font-size:19px;display:block}
    .ec .g s{font-size:11px;opacity:.6;text-decoration:none}
    .ec .sw{float:right}
    .ec .done{color:#00c48c;font-size:13px}`;return t;}
  _render(){
    if(!this._h||!this._c) return;
    const h=this._h;
    const ids=pickIds(h,{
      soc:['sensor.yipai_powersocstatus','sensor.epai_000001_power_soc_status'],
      kw:['sensor.yipai_charge_power_kw','sensor.epai_000001_charge_power_kw'],
      min:['sensor.yipai_batterypackchrgdchrgetimelength','sensor.epai_000001_battery_pack_chrg_dchrg_time_length'],
      chg:['binary_sensor.yipai_charging','binary_sensor.epai_000001_charging'],
      sw:['switch.yipai_charge_switch','switch.epai_000001_charge_switch'],
    });
    const st=id=>id&&h.states[id]?h.states[id].state:null;
    const soc=Number(st(ids.soc)||0);
    const charging=st(ids.chg)==='on';
    const swHtml=ids.sw?`<hui-entity-entity row-tile="" style="float:right" title=""></hui-entity-entity>`:'';
    this.innerHTML=`<div class="ec">
      <div class="hd"><b>⚡ 充电状态 ${charging?'· 进行中':soc>=100?'· 已充满':''}</b></div>
      <div class="bar"><i style="width:${Math.min(100,soc)}%"></i></div>
      <div class="grid">
        <div class="g"><b>${soc}%</b><s>当前电量</s></div>
        <div class="g"><b>${st(ids.kw)||'--'}</b><s>功率 kW</s></div>
        <div class="g"><b>${st(ids.min)||'--'}</b><s>剩余分钟</s></div>
        <div class="g"><b class="done">${charging?'充电中':soc>=100?'已完成':'未充电'}</b><s>状态</s></div>
      </div></div>${swHtml}`;
    if(ids.sw){const el=this.querySelector('hui-entity-entity');
      if(el){el.hass=h;el.entityId=ids.sw;}}
    this.style.display='block';
  }
}
if(!K.get('epi-charge-card')) K.define('epi-charge-card', EpiChargeCard);

// ---------- 3) epi-tyres-card : 2x2 tyre pressures + car top view ----------
class EpiTyresCard extends HTMLElement {
  setConfig(c){ this._c=c||{}; }
  static async getConfigElement(){ return document.createElement('epi-hero-editor'); }
  set hass(h){ this._h=h; if(!this.firstChild)this.appendChild(this._tpl()); this._render(); }
  _tpl(){const t=document.createElement('style');t.textContent=`
    .et{font-family:system-ui,sans-serif;background:var(--card-background-color,#1c1c1e);border-radius:18px;padding:16px;color:var(--primary-text-color,#eee);}
    .et .wrap{display:grid;grid-template-columns:64px 1fr;gap:14px;align-items:center;}
    .et .car{height:130px;border-radius:26px;background:linear-gradient(180deg,#2c3a3d,#223033);border:1px solid rgba(255,255,255,.10);position:relative;}
    .et .car::before{content:'';position:absolute;top:14px;left:14px;right:14px;height:22px;border-radius:10px;background:rgba(255,255,255,.08);}
    .et .car::after{content:'';position:absolute;bottom:14px;left:14px;right:14px;height:22px;border-radius:10px;background:rgba(255,255,255,.08);}
    .et .grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
    .et .ty{background:rgba(128,128,128,.09);border-radius:14px;padding:12px;text-align:center;}
    .et .ty b{font-size:21px;display:block}
    .et .ty s{font-size:11px;opacity:.6;text-decoration:none}
    .et .ty.hot b{color:#ff6b6b}.et .ty.ok b{color:#00c48c}`;return t;}
  _render(){
    if(!this._h||!this._c) return;
    const h=this._h;
    const ids=pickIds(h,{
      lf:['sensor.yipai_tyre_left_front','sensor.epai_000001_tyre_left_front'],
      rf:['sensor.yipai_tyre_right_front','sensor.epai_000001_tyre_right_front'],
      lr:['sensor.yipai_tyre_left_rear','sensor.epai_000001_tyre_left_rear'],
      rr:['sensor.yipai_tyre_right_rear','sensor.epai_000001_tyre_right_rear'],
    });
    const cell=(id,label)=>{
      const s=id&&h.states[id]?Number(h.states[id].state):null;
      const cls=s==null?'':(s<200||s>300?'hot':'ok');
      return `<div class="ty ${cls}"><b>${s==null?'--':s}</b><s>${label}</s></div>`;
    };
    this.innerHTML=`<div class="et"><div style="font-size:15px;margin-bottom:10px">🛞 胎压监测</div>
      <div class="wrap"><div class="car"></div>
      <div class="grid">${cell(ids.lf,'左前')}${cell(ids.rf,'右前')}${cell(ids.lr,'左后')}${cell(ids.rr,'右后')}</div>
      </div></div>`;
    this.style.display='block';
  }
}
if(!K.get('epi-tyres-card')) K.define('epi-tyres-card', EpiTyresCard);

// ---------- 4) epi-actions-card : remote action tiles ----------
class EpiActionsCard extends HTMLElement {
  setConfig(c){ this._c=c||{}; }
  static async getConfigElement(){ return document.createElement('epi-hero-editor'); }
  set hass(h){ this._h=h; if(!this.firstChild)this.appendChild(this._tpl()); this._render(); }
  _tpl(){const t=document.createElement('style');t.textContent=`
    .ea{font-family:system-ui,sans-serif;background:var(--card-background-color,#1c1c1e);border-radius:18px;padding:16px;color:var(--primary-text-color,#eee);}
    .ea .t{display:grid;grid-template-columns:repeat(auto-fit,minmax(90px,1fr));gap:10px;}
    .ea .a{border:none;border-radius:14px;padding:13px 6px;background:rgba(128,128,128,.10);color:inherit;cursor:pointer;font-size:12.5px;display:flex;flex-direction:column;gap:7px;align-items:center;}
    .ea .a em{font-style:normal;font-size:20px}
    .ea .a:active{transform:scale(.95)}
    .ea .a.on{background:rgba(0,153,168,.25);color:#00d9c0}`;return t;}
  _render(){
    if(!this._h||!this._c) return;
    const h=this._h;
    const ids=pickIds(h,{
      sw:['switch.yipai_charge_switch','switch.epai_000001_charge_switch'],
      btn:['button.yipai_refresh','button.epai_000001_refresh'],
      ac:['binary_sensor.yipai_ac_on','binary_sensor.epai_000001_ac_on'],
      lock:['binary_sensor.yipai_locked','binary_sensor.epai_000001_locked'],
    });
    const st=id=>id&&h.states[id];
    const acOn=st(ids.ac)&&st(ids.ac).state==='on';
    const locked=st(ids.lock)&&st(ids.lock).state==='on';
    const swOn=st(ids.sw)&&st(ids.sw).state==='on';
    this.innerHTML=`<div class="ea"><div style="font-size:15px;margin-bottom:10px">🎛 远程控制</div>
      <div class="t">
        <button class="a ${acOn?'on':''}" data-act="ac"><em>❄️</em>空调 ${acOn?'运行中':'已关闭'}</button>
        <button class="a ${locked?'':'on'}" data-act="lock"><em>🔒</em>车锁 ${locked?'已上锁':'未上锁'}</button>
        <button class="a ${swOn?'on':''}" data-act="charge"><em>⚡</em>充电 ${swOn?'停止':'开始'}</button>
        <button class="a" data-act="refresh"><em>🔄</em>刷新状态</button>
      </div></div>`;
    this.querySelectorAll('.a').forEach(b=>b.onclick=()=>{
      const a=b.dataset.act;
      if(a==='charge'&&ids.sw){h.callService('switch', swOn?'turn_off':'turn_on',{entity_id:ids.sw});}
      else if(a==='refresh'&&ids.btn){h.callService('button','press',{entity_id:ids.btn});}
      else if(a==='ac'||a==='lock'){/* 演示模式无控车接口，仅提示 */
        h.connection.sendMessage({type:'persistent_notification/create',
          message:(a==='ac'?'空调':'车锁')+'控制需真实车辆 token（抓包受限，当前为演示模式）',
          title:'奕派演示模式'});}
    });
    this.style.display='block';
  }
}
if(!K.get('epi-actions-card')) K.define('epi-actions-card', EpiActionsCard);

// ---------- 5) epi-loc-card : vehicle position card ----------
class EpiLocCard extends HTMLElement {
  setConfig(c){ this._c=c||{}; }
  static async getConfigElement(){ return document.createElement('epi-hero-editor'); }
  set hass(h){ this._h=h; if(!this.firstChild)this.appendChild(this._tpl()); this._render(); }
  _tpl(){const t=document.createElement('style');t.textContent=`
    .el{font-family:system-ui,sans-serif;background:var(--card-background-color,#1c1c1e);border-radius:18px;padding:16px;color:var(--primary-text-color,#eee);}
    .el .n{font-size:13px;opacity:.6;margin:4px 0;}
    .el a{color:#4fb3ff;text-decoration:none;font-size:13px}`;return t;}
  _render(){
    if(!this._h||!this._c) return;
    const h=this._h;
    const id=pickIds(h,{dt:['device_tracker.yipai_location','device_tracker.epai_000001_location']}).dt;
    if(!id||!h.states[id]){this.innerHTML='<div class="el">暂无车辆位置</div>';return;}
    const a=h.states[id].attributes||{};
    const lat=a.latitude, lon=a.longitude;
    this.innerHTML=`<div class="el"><div style="font-size:15px;margin-bottom:8px">📍 车辆位置</div>
      <div class="n">经纬度：${lat||'--'}, ${lon||'--'}</div>
      <div class="n">定位时间：${a.position_time||h.states[id].last_updated.slice(11,19)}</div>
      ${lat?`<a href="https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=16/${lat}/${lon}" target="_blank">在地图中查看 →</a>`:''}</div>`;
    this.style.display='block';
  }
}
if(!K.get('epi-loc-card')) K.define('epi-loc-card', EpiLocCard);

// ---------- simple config editor shared by all cards ----------
class EpiEditor extends HTMLElement {
  setConfig(c){ this._c=c; }
  set hass(h){ this._h=h; if(!this.firstChild) this._build(); }
  _build(){
    this.innerHTML=`<ha-card><div class="card-content">
      <paper-input label="电量实体 entity_id" value=""></paper-input>
      <paper-input label="续航实体 entity_id" value=""></paper-input>
      </div><div class="card-actions"><mwc-button>Rename</mwc-button></div></ha-card>`;
  }
}
if(!K.get('epi-hero-editor')) K.define('epi-hero-editor', EpiEditor);

// ---------- register with custom-cards registry ----------
(function(){
  const reg={
    'epi-hero-card':{name:'奕派 · 车辆总览',description:'小米风大环电量+续航+状态徽章',preview:true},
    'epi-charge-card':{name:'奕派 · 充电',description:'充电进度条+功率/剩余时间'},
    'epi-tyres-card':{name:'奕派 · 胎压',description:'四轮胎压与俯视图'},
    'epi-actions-card':{name:'奕派 · 远程控制',description:'空调/车锁/充电/刷新'},
    'epi-loc-card':{name:'奕派 · 车辆位置',description:'经纬度与地图链接'},
  };
  window.customCards=window.customCards||[];
  for(const [tag,info] of Object.entries(reg)){
    if(!window.customCards.some(c=>c.type===tag)) window.customCards.push({type:tag,...info});
  }
})();
"""


class EpiCardsJSView(HomeAssistantView):
    """Serve the custom card JS bundle."""

    url = CARDS_JS_URL
    name = "dongfeng_yipai:cards.js"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        return web.Response(text=CARDS_JS, content_type="application/javascript")


async def _try_register_resource(hass: HomeAssistant) -> bool:
    """Add our cards.js to Lovelace custom resources (idempotent)."""
    collection = hass.data.get("lovelace_resources")
    if collection is None:
        return False
    items = await collection.async_get_items()
    if any(str(i.get("url", "")).endswith(f"/{DOMAIN}/cards.js") for i in items):
        return True
    await collection.async_create_item({"res_type": "module", "url": CARDS_JS_URL})
    _LOGGER.info("奕派自定义卡片已注册到 Lovelace 资源")
    return True


async def ensure_cards_resources(hass: HomeAssistant) -> None:
    """Serve cards.js via HTTP and register it into Lovelace resources."""
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
        _LOGGER.debug("奕派卡片资源立即注册失败，启动后重试", exc_info=True)

    # Lovelace may not be initialised yet during entry setup -> retry once
    # the whole instance has started.
    if data.get("_cards_hook"):
        return
    data["_cards_hook"] = True

    async def _retry(_event) -> None:
        for _ in range(5):
            try:
                if await _try_register_resource(hass):
                    return
            except Exception:  # noqa: BLE001
                pass
            import asyncio

            await asyncio.sleep(10)

    from homeassistant.core import Event, callback  # local imports only

    @callback
    def _on_started(_ev: Event) -> None:
        hass.async_create_task(_retry(_ev))

    hass.bus.async_listen_once("homeassistant_started", _on_started)
