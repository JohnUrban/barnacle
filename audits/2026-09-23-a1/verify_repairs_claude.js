// Round-02 verification probe (Claude): the town map's repaired selector/display in an offline VM with synthetic state. Expects REPAIRED behaviour; run from the repo root with `node audits/2026-09-23-a1/verify_repairs_claude.js`.
const fs = require('fs'), vm = require('vm'), path = require('path');
const html = fs.readFileSync(path.resolve('docs/highlands.html'), 'utf8');
const b0 = html.indexOf('  function instMs(t) {');
const b1 = html.indexOf('  function syncScrub() {');
const e1 = html.indexOf('  tSlider.addEventListener("input"', b1);
if (b0 < 0 || b1 < 0 || e1 < 0) throw Error('anchors');
const helpers = html.slice(b0, html.indexOf('  }\n', html.indexOf('  function potFor(p) {')) + 4);
const handlers = {}; const store = {};
const ctx = {
  SERIES: [
    {time:'2026-09-23 05:00-04:00', tide_navd88:8, water_navd88:8, burst_risk:false},          // PAST crest
    {time:'2026-09-24 12:00-04:00', tide_navd88:2, water_navd88:6, burst_risk:false},          // future low tide, rain water 6
    {time:'2026-09-24 18:00-04:00', tide_navd88:4, water_navd88:4, burst_risk:false, outlook:true}
  ],
  rainBox:{checked:false}, tSlider:{value:0}, slider:{value:0}, tLabel:{textContent:''},
  POTD:{}, POT:9, MLLW_OFF:2.82, requestRender:()=>{}, buildLegend:()=>{},
  localStorage:{setItem:(k,v)=>{store[k]=v;}}, Date,
  document:{getElementById:id=>({addEventListener:(_,f)=>{handlers[id]=f;}})}
};
vm.createContext(ctx);
vm.runInContext(helpers + '\n' + html.slice(b1, e1), ctx);
handlers['town-worst-flood']();
const sel = ctx.SERIES[ctx.tSlider.value];
const out = { selected_time: sel.time, selected_water: sel.water_navd88,
  displayed_water: Number((Number(ctx.slider.value) - ctx.MLLW_OFF).toFixed(2)),
  rain_view_on: ctx.rainBox.checked, persisted: store['barnacle-town-rain'] };
handlers['town-worst-tide']();
out.worst_tide_time = ctx.SERIES[ctx.tSlider.value].time;
// per-day POT applies only to production points
out.pot_for_outlook_point = ctx.potFor(ctx.SERIES[2]);
out.pot_for_prod_point = ctx.potFor(ctx.SERIES[1]);
console.log(JSON.stringify(out, null, 2));
if (out.selected_time !== '2026-09-24 12:00-04:00' || out.displayed_water !== 6 || !out.rain_view_on) throw Error('town repair not effective');
if (out.worst_tide_time === '2026-09-23 05:00-04:00') throw Error('history won the worst-tide button');
