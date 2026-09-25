"""The interactive shell around the field ledger: pick a game, or see the overview.

Why this is separate from field_ledger.py. That module renders ALL panels of a
game to static SVG and concatenates them. At 24 games that is a 3MB page holding
216 charts, which is the wrong shape for reading: you cannot choose a game, the
overview is buried, and the browser carries every chart whether you look at it or
not.

Here the per-game series are embedded as compact JSON and the charts are drawn in
JavaScript when a game is selected. So the page opens on the overview, the list
on the left is the selector, and only the selected game's panels exist in the DOM.
Still one self-contained file with no dependencies -- the charts are hand-written
SVG because this venv has no numpy/matplotlib/pandas.

Payload control: money and idle are downsampled to every 2nd turn and rounded to
integers. Full resolution is 720 points over a ~980px-wide chart, so half of them
land on the same pixel; the downsampling costs nothing visually and halves the
file.

Usage (normally reached through review_losses.py, which prepares the data):
  import ledger_app; open("out.html","w").write(ledger_app.render(games, stats, blurb))
"""
import json

CSS = """
:root{--ink:#16302a;--mut:#64766e;--line:#dbe6e0;--bg:#eff4f1;--card:#fff;
--green:#1d7b4a;--violet:#8357a8;--red:#b85348;--gold:#b9770e}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.55 "Segoe UI","Microsoft YaHei",system-ui,sans-serif}
a{color:var(--green)}
.top{position:sticky;top:0;z-index:20;background:#fff;border-bottom:1px solid var(--line);
display:flex;align-items:center;gap:18px;padding:11px 20px;box-shadow:0 2px 10px rgba(20,60,38,.05)}
.top h1{font-size:17px;margin:0;white-space:nowrap}
.tabs{display:flex;gap:6px}
.tab{padding:6px 15px;border-radius:9px;border:1px solid var(--line);background:#fff;
cursor:pointer;font-size:13px;color:var(--mut)}
.tab.on{background:#eaf5ef;border-color:#bfdccd;color:var(--ink);font-weight:600}
.who{margin-left:auto;color:var(--mut);font-size:12px;text-align:right}
.wrap{max-width:1280px;margin:0 auto;padding:18px 20px 60px}
.howto{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px 16px;
margin-bottom:16px}
.howto li{margin:3px 0;color:var(--mut)}
.howto b{color:var(--ink)}
.kpi{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.kpi div{background:#fff;border:1px solid var(--line);border-radius:11px;padding:9px 15px;min-width:104px}
.kpi span{display:block;color:var(--mut);font-size:11.5px}
.kpi b{font-size:19px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:12px 15px;margin-bottom:12px;box-shadow:0 3px 12px rgba(20,60,38,.05)}
.card h3{font-size:14px;margin:0 0 2px}
.note{color:var(--mut);font-size:11.5px;margin:6px 0 0}
.stat{color:var(--mut);font-size:11.5px;margin:0 0 8px}
.chart{width:100%;max-width:960px;height:auto;display:block}
.grid{stroke:#e8f0ec;stroke-width:1}
.axis{stroke:#a9bcb2;stroke-width:1}
.ax{fill:var(--mut);font-size:12px}
.axy{text-anchor:end}.mid{text-anchor:middle}
.sub2{fill:var(--mut);font-size:11.5px}
.ttl{fill:var(--ink);font-size:13px;font-weight:600}
.lg{fill:var(--mut);font-size:12px}
.mark{stroke:#b9cbc2;stroke-width:1;stroke-dasharray:4 4}
.mk{fill:#7f948a;font-size:10.5px}
table{border-collapse:collapse;width:100%;font-size:13px;margin-top:4px}
th,td{border-bottom:1px solid var(--line);padding:5px 9px;text-align:right}
th:first-child,td:first-child{text-align:left}
th{color:var(--mut);font-weight:600;background:#f6faf8;position:sticky;top:56px}
tr.sel{background:#eaf5ef}
tr.clk{cursor:pointer}
tr.clk:hover{background:#f2f8f5}
.win{color:var(--green);font-weight:700}.lose{color:var(--red);font-weight:700}
.tie{color:var(--mut);font-weight:700}
.split{display:grid;grid-template-columns:330px 1fr;gap:16px;align-items:start}
.side{background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden;
position:sticky;top:72px}
.side .filters{display:flex;gap:5px;padding:9px 10px;border-bottom:1px solid var(--line);
background:#f6faf8}
.side .filters button{flex:1;padding:5px 0;border-radius:8px;border:1px solid var(--line);
background:#fff;cursor:pointer;font-size:12px;color:var(--mut)}
.side .filters button.on{background:#eaf5ef;border-color:#bfdccd;color:var(--ink);font-weight:600}
.side .list{max-height:calc(100vh - 190px);overflow:auto}
.side .row{display:flex;gap:8px;align-items:baseline;padding:7px 11px;
border-bottom:1px solid #f0f5f2;cursor:pointer;font-size:12.5px}
.side .row:hover{background:#f2f8f5}
.side .row.sel{background:#eaf5ef;box-shadow:inset 3px 0 0 var(--green)}
.side .row .ep{font-variant-numeric:tabular-nums;color:var(--mut)}
.side .row .opp{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.side .row .mg{font-variant-numeric:tabular-nums;font-weight:600}
.hide{display:none}
.gtitle{font-size:15px;margin:0 0 2px}
.gsub{color:var(--mut);font-size:12px;margin:0 0 12px}
"""

JS = r"""
const C = {s0:"#1d7b4a", s1:"#8357a8",
  WHEAT:"#d9a441",CARROT:"#e07b39",TOMATO:"#c0392b",STRAWBERRY:"#d94f8a",MELON:"#4aa96c",
  PASTURE:"#8d6e52",WEED:"#4e5f45",EMPTY:"#dde5e0",LOCKED:"#98a49c",
  SELL:"#c0392b",BUY_PRODUCT:"#2471a3",BUY_SEED:"#1e8449",BUY_ANIMAL:"#7d3c98",
  BUY_LAND:"#b9770e",HIRE:"#5d6d7e"};
const CN = {WHEAT:"小麦",CARROT:"胡萝卜",TOMATO:"番茄",STRAWBERRY:"草莓",MELON:"瓜",
  PASTURE:"牧场",WEED:"杂草",EMPTY:"空",LOCKED:"锁",
  SELL:"卖出",BUY_PRODUCT:"买货物",BUY_SEED:"买种子",BUY_ANIMAL:"买动物",
  BUY_LAND:"买地",HIRE:"雇工",MILK:"牛奶",WOOL:"羊毛",FERTILIZER:"肥料",EGG:"蛋"};
const PAL = ["#c0392b","#2471a3","#1e8449","#7d3c98","#b9770e","#5d6d7e",
  "#d94f8a","#16a085","#8e44ad","#2c3e50"];
const W = 960;

function sc(v, lo, hi, a, b){ return hi<=lo ? (a+b)/2 : a+(b-a)*(v-lo)/(hi-lo); }
function el(tag, attrs, kids){
  const n = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  (kids||[]).forEach(c => n.appendChild(c));
  return n;
}
function T(x,y,s,cls,anchor){ const t=el("text",{x:x,y:y,class:cls||"ax"});
  if(anchor) t.setAttribute("text-anchor",anchor); t.textContent=s; return t; }
function svg(h){ const s=el("svg",{viewBox:"0 0 "+W+" "+h,class:"chart"}); return s; }
function axes(s, px0,px1,py0,py1, lo,hi, money, n){
  n = n||5;
  for (let i=0;i<=n;i++){
    const yv = lo+(hi-lo)*i/n, yy = sc(yv,lo,hi,py1,py0);
    s.appendChild(el("line",{x1:px0,y1:yy,x2:px1,y2:yy,class:"grid"}));
    s.appendChild(T(px0-8, yy+4, money? "$"+fmt(yv) : Math.round(yv).toLocaleString(), "ax axy"));
  }
}
function fmt(v){ const a=Math.abs(v);
  if(a>=1e6) return (v/1e6).toFixed(2)+"M";
  if(a>=1e4) return Math.round(v/1000)+"k";
  if(a>=1e3) return (v/1000).toFixed(1)+"k";
  return Math.round(v); }

function linePanel(o){
  const pts = o.series.flatMap(s=>s.pts);
  if(!pts.length) return null;
  const h = o.height||250, ml=66,mr=26,mt=52,mb=74;
  const px0=ml,px1=W-mr,py0=mt,py1=h-mb;
  const xlo=Math.min(...pts.map(p=>p[0])), xhi=Math.max(...pts.map(p=>p[0]));
  const hi = Math.max(...pts.map(p=>p[1]), 1), lo = 0;
  const s = svg(h);
  s.appendChild(T(ml,18,o.title,"ttl"));
  if(o.sub) s.appendChild(T(ml,34,o.sub,"sub2"));
  axes(s,px0,px1,py0,py1,lo,hi,o.money!==false);
  [xlo,(xlo+xhi)/2,xhi].forEach((xv,i)=>{
    s.appendChild(T(sc(xv,xlo,xhi,px0,px1), py1+18, Math.round(xv).toLocaleString(),
      "ax", i===0?"start":(i===2?"end":"middle")));
  });
  s.appendChild(T((px0+px1)/2, py1+36, o.xlabel||"", "ax mid"));
  o.series.forEach(se=>{
    const d = se.pts.map(p=>sc(p[0],xlo,xhi,px0,px1).toFixed(1)+","+sc(p[1],lo,hi,py1,py0).toFixed(1)).join(" ");
    s.appendChild(el("polyline",{points:d,fill:"none",stroke:se.color,"stroke-width":1.8}));
  });
  (o.markers||[]).forEach(m=>{
    const x = sc(m[0],xlo,xhi,px0,px1);
    s.appendChild(el("line",{x1:x,y1:py0,x2:x,y2:py1,class:"mark"}));
    s.appendChild(T(x+3, py0+11, m[1], "mk"));
  });
  let lx=ml;
  o.series.forEach(se=>{ s.appendChild(el("rect",{x:lx,y:py1+48,width:18,height:4,rx:2,fill:se.color}));
    s.appendChild(T(lx+23, py1+53, se.label, "lg")); lx += 34+13*se.label.length; });
  return s;
}

function stackedPanel(o){
  const days = o.days;
  if(!days.length) return null;
  const h=o.height||250, ml=66,mr=26,mt=52,mb=40;
  const px0=ml,px1=W-mr,py0=mt,py1=h-mb;
  const hi = Math.max(...days.map(d=>o.keys.reduce((a,k)=>a+(o.data[d]?.[k]||0),0)),1);
  const bw = Math.max(2,(px1-px0)/days.length-2);
  const s = svg(h);
  s.appendChild(T(ml,18,o.title,"ttl"));
  if(o.sub) s.appendChild(T(ml,34,o.sub,"sub2"));
  axes(s,px0,px1,py0,py1,0,hi,false);
  days.forEach((d,i)=>{
    const x = px0+(px1-px0)*(i+0.5)/days.length-bw/2; let acc=0;
    o.keys.forEach(k=>{
      const v = o.data[d]?.[k]||0; if(!v) return;
      const y0=sc(acc,0,hi,py1,py0), y1=sc(acc+v,0,hi,py1,py0);
      const r = el("rect",{x:x,y:y1,width:bw,height:Math.max(.8,y0-y1),
        fill:C[k]||"#888"});
      r.appendChild(el("title",{})).textContent = "第"+d+"天 "+(CN[k]||k)+": "+v;
      s.appendChild(r); acc+=v;
    });
    if(d%3===0) s.appendChild(T(x+bw/2, py1+18, d, "ax","middle"));
  });
  s.appendChild(T((px0+px1)/2, h-4, "第几天","ax mid"));
  let lx=ml;
  o.keys.forEach(k=>{ const cn=CN[k]||k;
    s.appendChild(el("rect",{x:lx,y:mt-18,width:11,height:11,rx:2,fill:C[k]||"#888"}));
    s.appendChild(T(lx+15, mt-9, cn, "lg")); lx += 24+13*cn.length; });
  return s;
}

function groupedPanel(o){
  const days = o.days; if(!days.length) return null;
  const h=250, ml=66,mr=26,mt=52,mb=40;
  const px0=ml,px1=W-mr,py0=mt,py1=h-mb;
  const all = days.flatMap(d=>o.series.map(s=>o.data[s.key]?.[d]||0));
  const lo = Math.min(0,...all), hi = Math.max(1,...all);
  const slot=(px1-px0)/days.length, bw=Math.max(2,slot/2-1.5);
  const s=svg(h);
  s.appendChild(T(ml,18,o.title,"ttl"));
  if(o.sub) s.appendChild(T(ml,34,o.sub,"sub2"));
  axes(s,px0,px1,py0,py1,lo,hi,true);
  const zero = sc(0,lo,hi,py1,py0);
  if(lo<0) s.appendChild(el("line",{x1:px0,y1:zero,x2:px1,y2:zero,class:"axis"}));
  days.forEach((d,i)=>{
    o.series.forEach((se,j)=>{
      const v=o.data[se.key]?.[d]||0;
      const x=px0+slot*i+slot/2+(j-(o.series.length-1)/2)*(bw+1.5)-bw/2;
      const y=sc(v,lo,hi,py1,py0);
      const r=el("rect",{x:x,y:Math.min(y,zero),width:bw,
        height:Math.max(.8,Math.abs(y-zero)),fill:se.color});
      r.appendChild(el("title",{})).textContent="第"+d+"天 "+se.label+": "+Math.round(v);
      s.appendChild(r);
    });
    if(d%3===0) s.appendChild(T(px0+slot*i+slot/2, py1+18, d, "ax","middle"));
  });
  s.appendChild(T((px0+px1)/2, h-4, "第几天","ax mid"));
  let lx=ml;
  o.series.forEach(se=>{ s.appendChild(el("rect",{x:lx,y:mt-18,width:11,height:11,rx:2,fill:se.color}));
    s.appendChild(T(lx+15, mt-9, se.label, "lg")); lx += 76; });
  return s;
}

function piePanel(o){
  const items = o.items.filter(x=>x[1]>0).sort((a,b)=>b[1]-a[1]);
  if(!items.length) return null;
  const total = items.reduce((a,x)=>a+x[1],0);
  const h=300, cx=190, cy=h/2, rad=Math.min(h/2-34,108);
  const s=svg(h);
  s.appendChild(T(24,20,o.title,"ttl"));
  if(o.sub) s.appendChild(T(24,37,o.sub,"sub2"));
  let ang=-90;
  items.forEach((it,i)=>{
    const sweep=360*it[1]/total, a0=ang*Math.PI/180, a1=(ang+sweep)*Math.PI/180;
    const col = PAL[i%PAL.length], nm = CN[it[0]]||it[0];
    let node;
    if(sweep>=359.99){ node = el("circle",{cx:cx,cy:cy,r:rad,fill:col}); }
    else{
      const x0=cx+rad*Math.cos(a0), y0=cy+rad*Math.sin(a0);
      const x1=cx+rad*Math.cos(a1), y1=cy+rad*Math.sin(a1);
      node = el("path",{d:`M ${cx} ${cy} L ${x0.toFixed(1)} ${y0.toFixed(1)} A ${rad} ${rad} 0 ${sweep>180?1:0} 1 ${x1.toFixed(1)} ${y1.toFixed(1)} Z`,fill:col});
    }
    node.appendChild(el("title",{})).textContent = nm+" "+
      Math.round(it[1]).toLocaleString()+" ("+(100*it[1]/total).toFixed(1)+"%)";
    s.appendChild(node); ang += sweep;
  });
  s.appendChild(el("circle",{cx:cx,cy:cy,r:Math.round(rad*0.52),fill:"#fff"}));
  s.appendChild(T(cx,cy-4,"合计","ax mid")).setAttribute("style","font-size:13px;fill:#16302a");
  const tot = T(cx,cy+16,"$"+Math.round(total).toLocaleString(),"ax mid");
  tot.setAttribute("style","font-size:15px;font-weight:700;fill:#16302a");
  s.appendChild(tot);
  let ly=62;
  items.forEach((it,i)=>{
    s.appendChild(el("rect",{x:350,y:ly-10,width:12,height:12,rx:3,fill:PAL[i%PAL.length]}));
    s.appendChild(T(368,ly,CN[it[0]]||it[0],"lg"));
    s.appendChild(T(W-24,ly,"$"+Math.round(it[1]).toLocaleString()+"   "+
      (100*it[1]/total).toFixed(1)+"%","lg","end"));
    ly+=21;
  });
  return s;
}

function card(title, sub, node, note){
  const d=document.createElement("div"); d.className="card";
  const h=document.createElement("h3"); h.textContent=title; d.appendChild(h);
  if(sub){ const p=document.createElement("p"); p.className="stat"; p.textContent=sub; d.appendChild(p); }
  if(node) d.appendChild(node);
  if(note){ const p=document.createElement("p"); p.className="note"; p.innerHTML=note; d.appendChild(p); }
  return d;
}

let GAMES=[], NAMES=[], cur=-1, filter="all";

function visible(){
  return GAMES.map((g,i)=>({g,i})).filter(o=>
    filter==="all" || (filter==="lose" ? o.g.margin<0 : o.g.margin>0));
}
function buildList(){
  const box=document.getElementById("list"); box.innerHTML="";
  visible().forEach(o=>{
    const r=document.createElement("div");
    r.className="row"+(o.i===cur?" sel":"");
    r.innerHTML = '<span class="ep">'+o.g.id+'</span>'+
      '<span class="opp">'+(o.g.opp||"")+'</span>'+
      '<span class="mg '+cls(o.g.margin)+'">'+(o.g.margin>0?"+":"")+
      Math.round(o.g.margin).toLocaleString()+'</span>';
    r.onclick=()=>{ cur=o.i; buildList(); renderGame(); };
    box.appendChild(r);
  });
}
function cls(m){ return m>0?"win":(m<0?"lose":"tie"); }

function renderGame(){
  const host=document.getElementById("detail");
  host.innerHTML="";
  if(cur<0){ host.innerHTML="<p class='note'>左侧选一局。</p>"; return; }
  const g=GAMES[cur];
  const t=document.createElement("h2"); t.className="gtitle";
  t.innerHTML = (g.ladder?("天梯对局 · episode <b>"+g.id+"</b>（提交 ref "+g.ref+"）")
                          :("本地模拟 · seed <b>"+g.id+"</b>"))
    + ' · <span class="'+cls(g.margin)+'">'+(g.margin>0?"我们赢":"我们输")
    + " $"+Math.abs(Math.round(g.margin)).toLocaleString()+"</span>";
  host.appendChild(t);
  const sub=document.createElement("p"); sub.className="gsub";
  sub.textContent = NAMES[0]+"（seat 0） vs "+(g.opp||"对手")+"（seat 1）";
  host.appendChild(sub);

  const k=document.createElement("div"); k.className="kpi";
  g.seats.forEach((s,si)=>{
    [["终局资金","$"+Math.round(s.kpi.money).toLocaleString()],
     ["干活比例", s.kpi.work+"%"],
     ["解锁店铺", s.kpi.shops],
     ["闲置单位·回合", s.kpi.idle.toLocaleString()]
    ].forEach(([lab,val])=>{
      const d=document.createElement("div");
      d.innerHTML="<span>seat "+si+" "+lab+"</span><b>"+val+"</b>";
      k.appendChild(d);
    });
  });
  host.appendChild(k);

  const d0=g.day||[];
  const money = linePanel({title:"现金曲线", sub:"纵轴 = 手上的钱；竖虚线是商店解锁时刻",
    series:[{label:NAMES[0],color:C.s0,pts:g.seats[0].money},
            {label:"对手",color:C.s1,pts:g.seats[1].money}],
    markers:g.markers, xlabel:"步 →（720 步 = 30 天）", money:true});
  if(money) host.appendChild(card("现金曲线",
    "差距在这条线上变宽的地方，就是这局被决定的地方。",
    money, "竖虚线是商店解锁的时刻（鼠标悬停看店名）。"));

  const idle = linePanel({title:"闲置的劳动力", sub:"每回合什么都不做的农民+雇工数",
    series:[{label:"我们",color:C.s0,pts:g.seats[0].idle},
            {label:"对手",color:C.s1,pts:g.seats[1].idle}],
    xlabel:"步 →", money:false, height:200});
  if(idle) host.appendChild(card("闲置的劳动力", null, idle,
    "<b>两边常常完全一样</b>——农场动作来自同一条磁带，所有反射层只改市场指令。"
    + "所以要看的是<b>绝对水平</b>，不是两者之差。"));

  const tileCols=document.createElement("div");
  tileCols.className="card";
  tileCols.innerHTML="<h3>地块账本</h3><p class='stat'>每天平均有多少格在种什么；空/杂草比例高 = 地没被用上。</p>";
  g.seats.forEach((s,si)=>{
    const n=stackedPanel({title:(si?"对手":"我们")+"（seat "+si+"）",
      sub:"纵轴 = 格数", days:d0, data:s.tiles,
      keys:["WHEAT","CARROT","TOMATO","STRAWBERRY","MELON","PASTURE","WEED","EMPTY","LOCKED"],
      height:230});
    if(n) tileCols.appendChild(n);
  });
  host.appendChild(tileCols);

  const cflow = groupedPanel({title:"每天现金净变化", sub:"同一天两根柱对比；突然转负 = 当天大额支出",
    days:d0, data:{"0":g.seats[0].flow,"1":g.seats[1].flow},
    series:[{key:"0",label:"我们",color:C.s0},{key:"1",label:"对手",color:C.s1}]});
  if(cflow) host.appendChild(card("每天现金净变化", null, cflow,
    "高柱子 = 那天出货多；转负 = 那天在买动物/买地。"));

  const mktCols=document.createElement("div");
  mktCols.className="card";
  mktCols.innerHTML="<h3>市场指令构成</h3><p class='stat'>每天下多少条、什么类型。每回合最多 10 条槽位。</p>";
  g.seats.forEach((s,si)=>{
    const n=stackedPanel({title:(si?"对手":"我们")+"（seat "+si+"）",
      sub:"纵轴 = 指令条数", days:d0, data:s.orders,
      keys:["SELL","BUY_PRODUCT","BUY_SEED","BUY_ANIMAL","BUY_LAND","HIRE"], height:230});
    if(n) mktCols.appendChild(n);
  });
  host.appendChild(mktCols);

  g.seats.forEach((s,si)=>{
    const n=piePanel({title:(si?"对手":"我们")+" 的下单金额构成（降序）",
      sub:"总量锚定真实现金流入；⚠️ 这是<b>下单</b>构成、不是成交构成",
      items:s.rev});
    if(n) host.appendChild(card((si?"对手":"我们")+"（seat "+si+"）· 下单构成", null, n,
      "引擎会中止超出棚存的卖单，而回放在收割前取棚存快照，所以<b>单靠回放分不开下单与成交</b>；"
      + "超量下单的品类（通常是肥料）占比偏高。"));
  });
}

function overview(){
  const host=document.getElementById("detail");
  host.innerHTML="";
  const S=STATS;
  const k=document.createElement("div"); k.className="kpi";
  [["对局数",S.n],["胜率",S.rate.toFixed(0)+"%"],
   ["胜 / 负 / 平",S.w+" / "+S.l+" / "+S.t],
   ["不同对手",S.opponents],
   ["|差距| 中位","$"+Math.round(S.median).toLocaleString()],
   ["最小 / 最大","$"+Math.round(S.closest).toLocaleString()+" / $"+Math.round(S.worst).toLocaleString()],
   ["差距 < $600",S.close_pct.toFixed(0)+"%"]
  ].forEach(([lab,val])=>{ const d=document.createElement("div");
    d.innerHTML="<span>"+lab+"</span><b>"+val+"</b>"; k.appendChild(d); });
  host.appendChild(k);

  const sorted=GAMES.map((g,i)=>({g,i})).sort((a,b)=>a.g.margin-b.g.margin);
  const tbl=document.createElement("div"); tbl.className="card";
  tbl.innerHTML="<h3>全部对局（按差距排序）</h3>"+
    "<p class='stat'>点任意一行跳到那一局的全部面板。这就是【选对局】的地方。</p>";
  const t=document.createElement("table");
  t.innerHTML="<tr><th>episode</th><th>结果</th><th>差距</th><th>对手</th></tr>";
  sorted.forEach(o=>{
    const tr=document.createElement("tr"); tr.className="clk";
    tr.innerHTML='<td>'+o.g.id+'</td><td class="'+cls(o.g.margin)+'">'+
      (o.g.margin>0?"胜":(o.g.margin<0?"负":"平"))+'</td><td>$'+
      (o.g.margin>0?"+":"")+Math.round(o.g.margin).toLocaleString()+
      '</td><td>'+(o.g.opp||"")+'</td>';
    tr.onclick=()=>{ cur=o.i; show("game"); buildList(); renderGame(); };
    t.appendChild(tr);
  });
  tbl.appendChild(t);
  host.appendChild(tbl);

  const bins=[0,50,100,200,400,600,1000,2000,1e9];
  const hist={}; const labels=[];
  for(let i=0;i<bins.length-1;i++){ labels.push("$"+bins[i]+"–"+bins[i+1]); hist[i]=0; }
  GAMES.forEach(g=>{ const m=Math.abs(g.margin);
    for(let i=0;i<bins.length-1;i++) if(m>=bins[i]&&m<bins[i+1]){ hist[i]++; break; } });
  const data={}; labels.forEach((l,i)=>data[i]={v:hist[i]});
  const hb=stackedPanel({title:"差距分布", sub:"横轴 = |差距| 区间，纵轴 = 局数",
    days:labels.map((_,i)=>i), data:data, keys:["v"], height:220});
  if(hb) host.appendChild(card("差距分布", null, hb,
    "柱子集中在左边 = 这个分段的对局是被几百块决定的。"));
}

function show(view){
  document.getElementById("overview").classList.toggle("hide", view!=="over");
  document.querySelector(".split").classList.toggle("hide", view!=="game");
  document.querySelectorAll(".tab").forEach(b=>
    b.classList.toggle("on", b.dataset.v===view));
  if(view==="over") overview(); else renderGame();
}

function boot(data){
  GAMES=data.games; NAMES=data.names; STATS=data.stats;
  document.getElementById("blurb").innerHTML=data.blurb;
  document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>show(b.dataset.v));
  document.querySelectorAll(".side .filters button").forEach(b=>b.onclick=()=>{
    filter=b.dataset.f;
    document.querySelectorAll(".side .filters button").forEach(x=>x.classList.toggle("on",x===b));
    buildList();
  });
  const vis=visible();
  if(vis.length) cur=vis[0].i;
  buildList();
  show("over");
}
"""

HOWTO = """<div class="howto"><b>怎么看</b>
<ul>
<li>上面两个页签：<b>总览</b>给出胜率与差距分布，<b>对局</b>是逐局细看。左侧列表可以按 全部/只看败局/只看胜局 过滤，点一行就切换。</li>
<li>每一局的面板顺序：<b>现金曲线</b>（谁什么时候被拉开）→ <b>劳动力</b> → <b>地块账本</b>（在种什么）→ <b>每日现金变化</b> → <b>市场指令</b> → <b>下单构成</b>。</li>
<li>我们的座位已归一到 seat 0，所以<b>左列永远是我们</b>。</li>
<li><b>竖虚线</b>是商店解锁时刻。鼠标悬停图上的柱子/扇区能看到具体数字。</li>
</ul></div>"""


def render(games, names, stats, blurb=""):
    """games: the compact per-game dicts built by review_losses.py."""
    data = {"games": games, "names": names, "stats": stats, "blurb": blurb}
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"""<!doctype html><meta charset='utf-8'><title>天梯对局复盘</title>
<style>{CSS}</style>
<div class="top">
  <h1>天梯对局复盘</h1>
  <div class="tabs">
    <div class="tab" data-v="over">总览</div>
    <div class="tab" data-v="game">对局</div>
  </div>
  <div class="who">{stats['n']} 局 &middot; 胜率 {stats['rate']:.0f}%</div>
</div>
<div class="wrap">
  <div id="blurb"></div>
  {HOWTO}
  <div id="overview"></div>
  <div class="split hide">
    <div class="side">
      <div class="filters">
        <button data-f="all" class="on">全部</button>
        <button data-f="lose">只看败局</button>
        <button data-f="win">只看胜局</button>
      </div>
      <div class="list" id="list"></div>
    </div>
    <div id="detail"></div>
  </div>
</div>
<script>
const DATA = {payload};
{JS}
boot(DATA);
</script>
"""
