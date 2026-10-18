"""Auto-registered dashboard panel for the Dongfeng eπ integration.

Registers a sidebar panel per config entry so the vehicle status page shows
up without any manual Lovelace editing.  The page is a small dependency-free
web component served by this integration itself; it resolves this entry's
entities through the entity registry (by config_entry_id, so it works
regardless of entity-id slug differences across HA versions) and re-renders
on every state update.

NOTE: panel_custom is a HACS frontend component and is NOT part of core
Home Assistant.  It must only ever be imported lazily inside a try/except —
a module-level import would break integration loading on installs without
that component.
"""
from __future__ import annotations

import logging

from aiohttp import web
from homeassistant.core import HomeAssistant
from homeassistant.components.http import HomeAssistantView

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

JS_URL = f"/{DOMAIN}/dashboard.js"

JS = r"""
class YipaiDashboard extends HTMLElement {
  set config(c){ this._cfg = c; }
  set hass(hass){
    this._hass = hass;
    if(!this._done){ this._init(); return; }
    if(this._t) return;
    this._t = setTimeout(()=>{ this._t=null; this._render(); }, 800);
  }
  async _init(){
    this._done = true;
    try{
      const regs = await this._hass.connection.sendMessagePromise(
        {type:'config/entity_registry/list'});
      const eid = this._cfg && this._cfg.entry_id;
      this._ids = regs.filter(r=>r.config_entry_id===eid).map(r=>r.entity_id);
    }catch(e){
      this._ids = Object.keys(this._hass.states).filter(id=>{
        const a=this._hass.states[id].attributes||{};
        return id.includes('yipai')||id.includes('e_pai')||String(a.friendly_name||'').includes('奕派');
      });
    }
    this.appendChild(this._style());
    this._root=document.createElement('div');
    this.appendChild(this._root);
    this._render();
  }
  _style(){
    const s=document.createElement('style');
    s.textContent=`
      .yp{font-family:system-ui,sans-serif;padding:12px;display:grid;
          grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;}
      .yp-card{background:var(--card-background-color,#1c1c1e);
          border-radius:14px;padding:14px 16px;box-shadow:0 1px 4px rgba(0,0,0,.25);}
      .yp-big{grid-column:span 2;}
      .yp-title{font-size:13px;opacity:.7;margin-bottom:6px;}
      .yp-val{font-size:26px;font-weight:600;}
      .yp-unit{font-size:14px;opacity:.6;margin-left:4px;}
      .yp-bar{height:8px;border-radius:4px;background:#3a3a3c;margin-top:8px;overflow:hidden;}
      .yp-bar>i{display:block;height:100%;background:#0099A8;border-radius:4px;}
      .yp-grid{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;}
      .yp-chip{font-size:13px;padding:6px 12px;border-radius:16px;background:#2c2c2e;}
      .yp-chip.on{background:#0a84ff;}.yp-chip.warn{background:#ff9f0a;color:#000;}
      .yp-btn{border:none;border-radius:10px;padding:10px 16px;margin:4px 6px 0 0;
          font-size:14px;background:#0099A8;color:#fff;cursor:pointer;}
      .yp-btn.off{background:#48484a;}
      .yp-row{margin:6px 0;display:flex;justify-content:space-between;font-size:14px;}
      .yp a{color:#0a84ff;text-decoration:none;}
      .yp-empty{opacity:.6;font-size:14px;padding:20px;}
      /* 小米汽车风格 hero 环 */
      .yp-hero{display:flex;gap:18px;align-items:center;flex-wrap:wrap;
          background:linear-gradient(150deg,#14352f 0%,#101a1c 70%);
          border-radius:20px;color:#eafffa;grid-column:1/-1;}
      .yp-hero .ring{position:relative;width:130px;height:130px;flex:0 0 auto;}
      .yp-hero svg{transform:rotate(-90deg);}
      .yp-hero .pct{position:absolute;inset:0;display:flex;flex-direction:column;
          justify-content:center;align-items:center;}
      .yp-hero .pct b{font-size:32px;font-weight:700;}
      .yp-hero .pct s{font-size:11px;opacity:.6;text-decoration:none;}
      .yp-hero .info{flex:1;min-width:170px;}
      .yp-hero .row b{font-size:15px;}
      .yp-hero .chip{background:rgba(255,255,255,.09);}
      .yp-hero .chip i{width:8px;height:8px;border-radius:50%;background:#7f8b8e;
          display:inline-block;margin-right:5px;}
      .yp-hero .chip.on i{background:#00e5b0;box-shadow:0 0 6px #00e5b0;}
      .yp-hero .chip.warn i{background:#ffb45a;}
      .yp-hero .upd{font-size:11px;opacity:.45;margin-top:8px;}
      @media(max-width:520px){.yp-hero{flex-direction:column;align-items:stretch}}
      @media(max-width:600px){.yp-big{grid-column:span 1;}}`;
    return s;
  }
  _call(domain,service,id){
    this._hass.connection.sendMessage({type:'call_service',domain,service,
      target:{entity_id:id}});
  }
  _render(){
    if(!this._root) return;
    const H=this._hass, ids=this._ids||[];
    const st=id=>H.states[id];
    const g=(pref)=>ids.filter(i=>i.startsWith(pref)).map(st).filter(Boolean);
    const sensors=g('sensor.'), bins=g('binary_sensor.'),
          switches=g('switch.'), buttons=g('button.'),
          trackers=g('device_tracker.');
    const fmt=v=>v==null?'--':v;
    const soc=sensors.find(s=>/powersocstatus|battery/i.test(s.entity_id));
    const rest=sensors.filter(s=>s!==soc&&!/last_report|updateTime/i.test(s.entity_id));
    let html='<div class="yp">';
    // ---- Xiaomi-style hero: battery ring + key numbers + chips ----
    if(soc){
      const p=Math.max(0,Math.min(100,Number(soc.state)||0));
      const col=p>50?'#00e5b0':p>20?'#ffd166':'#ff6b6b';
      const C=2*Math.PI*54;
      const range=sensors.find(s=>/endurance|remaining_range/i.test(s.entity_id));
      const total=sensors.find(s=>/totalmileage|total_mileage/i.test(s.entity_id));
      const cabin=sensors.find(s=>/accabin|cabin_temperature/i.test(s.entity_id));
      const outt=sensors.find(s=>/outtemperature|outside_temperature/i.test(s.entity_id));
      html+=`<div class="yp-card yp-hero">
        <div class="ring"><svg width="130" height="130" viewBox="0 0 130 130">
          <circle cx="65" cy="65" r="54" fill="none" stroke="rgba(255,255,255,.10)" stroke-width="10"/>
          <circle cx="65" cy="65" r="54" fill="none" stroke="${col}" stroke-width="10"
            stroke-linecap="round" stroke-dasharray="${C*p/100} ${C}"/>
        </svg><div class="pct"><b>${p}%</b><s>动力电池</s></div></div>
        <div class="info">
          <div class="yp-row"><span>剩余续航</span><b>${fmt(range?range.state:null)}${range?' '+(range.attributes.unit_of_measurement||'km'):''}</b></div>
          <div class="yp-row"><span>总里程</span><b>${fmt(total?total.state:null)}</b></div>
          <div class="yp-row"><span>车内 / 车外</span><b>${fmt(cabin?cabin.state:null)}℃ / ${fmt(outt?outt.state:null)}℃</b></div>
          <div class="yp-grid">`;
      bins.forEach(b=>{
        const nm=(b.attributes.friendly_name||b.entity_id.split('.').pop());
        const good=b.state==='on';
        html+=`<span class="yp-chip chip ${good?'on':'warn'}"><i></i>${nm}</span>`;
      });
      html+='</div></div></div>';
    }
    rest.forEach(s=>{
      html+=`<div class="yp-card"><div class="yp-title">${s.attributes.friendly_name||s.entity_id}</div>
        <div class="yp-val">${fmt(s.state)}<span class="yp-unit">${s.attributes.unit_of_measurement||''}</span></div></div>`;
    });
    const upd=sensors.find(s=>/last_report|updatetime/i.test(s.entity_id));
    if(upd){
      html+=`<div class="yp-card"><div class="yp-title">${upd.attributes.friendly_name||'最后上报'}</div>
        <div class="yp-val" style="font-size:15px">${fmt(upd.state)}</div></div>`;
    }
    switches.concat(buttons).forEach(e=>{
      const isSwitch=e.entity_id.startsWith('switch.');
      const on=isSwitch && e.state==='on';
      html+=`<div class="yp-card"><div class="yp-title">${e.attributes.friendly_name||e.entity_id}</div>
        <button class="yp-btn ${on?'':'off'}" data-id="${e.entity_id}" data-kind="${isSwitch?'switch':'button'}">
        ${isSwitch?(on?'停止充电':'开始充电'):(e.state==='unknown'?'按下':e.attributes.friendly_name||'按下')}</button></div>`;
    });
    trackers.forEach(t=>{
      const a=t.attributes||{};
      const lat=a.latitude, lon=a.longitude;
      html+=`<div class="yp-card"><div class="yp-title">${a.friendly_name||'车辆位置'}</div>
        <div class="yp-row"><span>经度</span><span>${fmt(lon)}</span></div>
        <div class="yp-row"><span>纬度</span><span>${fmt(lat)}</span></div>
        ${lat&&lon?`<a href="https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=15/${lat}/${lon}" target="_blank">在地图中查看 →</a>`:''}</div>`;
    });
    if(!ids.length) html+='<div class="yp-empty">尚未发现该车辆的实体，请确认集成实例已创建并重启完成。</div>';
    html+='</div>';
    this._root.innerHTML=html;
    this._root.querySelectorAll('.yp-btn').forEach(btn=>{
      btn.onclick=()=>{
        const id=btn.dataset.id;
        if(btn.dataset.kind==='switch'){
          this._call('switch', this._hass.states[id].state==='on'?'turn_off':'turn_on', id);
        } else {
          this._call('button','press', id);
        }
        setTimeout(()=>this._hass.callService('homeassistant','update_entity',
          {entity_id:this._ids}),1500);
      };
    });
  }
  connectedCallback(){ if(this._hass) this._render(); }
}
customElements.define('yipai-dashboard', YipaiDashboard);
"""


class YipaiDashboardJSView(HomeAssistantView):
    """Serve the dashboard web component JS."""

    url = JS_URL
    name = "dongfeng_yipai:dashboard.js"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        return web.Response(text=JS, content_type="application/javascript")


async def async_setup_panel(hass: HomeAssistant, entry) -> None:
    # Lazy import: panel_custom lives in HACS frontend, never in core HA.
    from homeassistant.components.panel_custom import async_register_panel

    data = hass.data.setdefault(DOMAIN, {})
    if not data.get("_js_view"):
        hass.http.register_view(YipaiDashboardJSView())
        data["_js_view"] = True

    vin = entry.data.get("vin", "vehicle")
    path = f"{DOMAIN}-{vin[-6:].lower()}"
    await async_register_panel(
        hass,
        frontend_url_path=path,
        webcomponent_name="yipai-dashboard",
        sidebar_title=f"奕派 {vin[-6:]}",
        sidebar_icon="mdi:car-electric",
        js_url=JS_URL,
        config={"entry_id": entry.entry_id, "vin": vin},
        require_admin=False,
    )


async def async_remove_panel_entry(hass: HomeAssistant, entry) -> None:
    from homeassistant.components.panel_custom import async_remove_panel

    vin = entry.data.get("vin", "vehicle")
    await async_remove_panel(hass, f"{DOMAIN}-{vin[-6:].lower()}")
