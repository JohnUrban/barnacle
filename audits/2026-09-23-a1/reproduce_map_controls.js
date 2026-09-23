// Offline execution of the actual town-map selector/display functions.
// Synthetic levels only; no browser, network or production writes.
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const root = path.resolve(__dirname, '../..');
const html = fs.readFileSync(path.join(root, 'docs/highlands.html'), 'utf8');
const begin = html.indexOf('  function syncScrub() {');
const end = html.indexOf('  tSlider.addEventListener("input"', begin);
if (begin < 0 || end < 0) throw Error('source anchors changed');
const handlers = {};
const context = {
  SERIES: [
    {time:'2026-09-24 12:00-04:00',tide_navd88:2,water_navd88:6,burst_risk:false},
    {time:'2026-09-24 18:00-04:00',tide_navd88:4,water_navd88:4,burst_risk:false}
  ],
  rainBox:{checked:false},tSlider:{value:0},slider:{value:0},tLabel:{textContent:''},
  POTD:{},POT:null,MLLW_OFF:2.82,requestRender:()=>{},
  document:{getElementById:id=>({addEventListener:(_,f)=>{handlers[id]=f;}})}
};
vm.createContext(context);
vm.runInContext(html.slice(begin,end), context);
handlers['town-worst-flood']();
const result = {
  selected_water_navd88: context.SERIES[context.tSlider.value].water_navd88,
  displayed_water_navd88: Number(context.slider.value)-context.MLLW_OFF,
  rain_enabled:context.rainBox.checked
};
if(result.selected_water_navd88!==6 || Math.abs(result.displayed_water_navd88-2)>1e-6)
  throw Error('candidate changed: re-review this probe');
console.log(JSON.stringify(result,null,2));
