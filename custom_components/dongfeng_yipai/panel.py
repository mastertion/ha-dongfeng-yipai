"""Auto-registered dashboard panel for the Dongfeng eπ integration.

Registers a sidebar panel per config entry so the vehicle status page shows
up without any manual Lovelace editing.  The page is a small dependency-free
web component served by this integration itself; it resolves this entry's
entities through the entity registry (by config_entry_id, so it works
regardless of entity-id slug differences across HA versions) and re-renders
on every state update.
"""
from __future__ import annotations

import logging

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

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
      // fallback: anything with yipai in the entity id or vin in attrs
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
    const soc=sensors.find(s=>/powerSocStatus|battery/i.test(s.entity_id));
    let html='<div class="yp">';
    if(soc){
      const p=Math.max(0,Math.min(100,Number(soc.state)||0));
      html+=`<div class="yp-card yp-big"><div class="yp-title">${soc.attributes.friendly_name||'动力电池'}</div>
        <div class="yp-val">${p}<span class="yp-unit">%</span></div>
        <div class="yp-bar"><i style="width:${p}%"></i></div></div>`;
    }
    sensors.filter(s=>s!==soc).forEach(s=>{
      html+=`<div class="yp-card"><div class="yp-title">${s.attributes.friendly_name||s.entity_id}</div>
        <div class="yp-val">${fmt(s.state)}<span class="yp-unit">${s.attributes.unit_of_measurement||''}</span></div></div>`;
    });
    if(bins.length){
      html+='<div class="yp-card yp-big"><div class="yp-title">车辆状态</div><div class="yp-grid">';
      bins.forEach(b=>{
        const cls=b.state==='on'?'on':'warn';
        html+=`<span class="yp-chip ${cls}">${b.attributes.friendly_name||b.entity_id} ${b.state==='on'?'●':'○'}</span>`;
      });
      html+='</div></div>';
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


async def async_setup_panel(hass: HomeAssistant, entry: ConfigEntry) -> None:
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


async def async_remove_panel_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    from homeassistant.components.panel_custom import async_remove_panel

    vin = entry.data.get("vin", "vehicle")
    await async_remove_panel(hass, f"{DOMAIN}-{vin[-6:].lower()}")
