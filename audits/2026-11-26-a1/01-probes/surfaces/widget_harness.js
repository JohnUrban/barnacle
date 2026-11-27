// Runs a given barnacle-widget.js against local JSON with stubbed Scriptable API.
// usage: node widget_harness.js <widget.js> <forecast.json> <nowcast.json> <ISO now> <family>
const fs = require('fs');
const [,, widgetPath, fcPath, ncPath, nowIso, family] = process.argv;
const FIXED = Date.parse(nowIso);
const RealDate = Date;
class FakeDate extends RealDate {
  constructor(...a) { if (a.length === 0) super(FIXED); else super(...a); }
  static now() { return FIXED; }
}
const lines = [];
function mkStack(name) {
  return {
    addText(t) { const o = {text: t}; lines.push(o); return o; },
    addStack() { return mkStack(name + '>stack'); },
    addSpacer() {}, addImage(img) { lines.push({text: '[chart image]'}); return {}; },
    layoutHorizontally() {}, layoutVertically() {}, centerAlignContent() {},
  };
}
function ListWidget() { const s = mkStack('w'); return s; }
function Color(hex, a) { this.hex = hex; }
const Font = new Proxy({}, { get: () => (n) => ({size: n}) });
function Request(url) { this.url = url; this.loadJSON = async () => {
  if (url.indexOf('nowcast.json') >= 0) return JSON.parse(fs.readFileSync(ncPath));
  return JSON.parse(fs.readFileSync(fcPath)); }; }
function DrawContext() { return new Proxy({}, { get: (t, k) => k === 'getImage' ? () => ({img: true}) : (k in t ? t[k] : () => {}), set: (t,k,v)=>{t[k]=v;return true;} }); }
function Size() {} function Rect() {} function Point() {}
function Path() { return { move(){}, addLine(){} }; }
const config = { widgetFamily: family, runsInWidget: true };
const Script = { setWidget(w) {}, complete() {} };
const src = fs.readFileSync(widgetPath, 'utf8');
const fn = new Function('Date','ListWidget','Color','Font','Request','DrawContext','Size','Rect','Point','Path','config','Script',
  'return (async () => {' + src + '})();');
fn(FakeDate, ListWidget, Color, Font, Request, DrawContext, Size, Rect, Point, Path, config, Script).then(() => {
  for (const l of lines) console.log('  | ' + l.text + (l.textColor ? '   {color ' + l.textColor.hex + (l.font ? ', size ' + l.font.size : '') + '}' : ''));
}).catch(e => console.log('HARNESS ERROR', e));
