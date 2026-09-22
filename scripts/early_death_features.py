"""Per-episode feature table for the early-death analysis.  See early_death_deepdive.py.""" 
import json, collections, statistics as st

DATA='results/early_death_data.json'
ROUTES='results/early_death_routes.json'

def load():
    data=json.load(open(DATA,encoding='utf-8'))
    routes={r['ep']:r for r in json.load(open(ROUTES,encoding='utf-8'))}
    return data,routes

def gh(r,tag,day,key,d=0):
    s=r['snap_h23'].get('%s:%d'%(tag,day))
    return s.get(key,d) if s else d

def diff(r,day):
    return gh(r,'us',day,'money')-gh(r,'them',day,'money')

def cum(r,tag,key,lo,hi):
    """sum over days lo..hi of snapshot key"""
    return sum((r['snap_h23'].get('%s:%d'%(tag,d)) or {}).get(key,0) for d in range(lo,hi+1))

def evbuy(r,tag,item,lo,hi):
    n=0
    for d in range(lo,hi+1):
        e=r['events'].get('%s:%d'%(tag,d))
        if e: n+=e['buys'].get('BUY_ANIMAL:%s'%item,0)
    return n

def evop(r,tag,op,lo,hi):
    n=0
    for d in range(lo,hi+1):
        e=r['events'].get('%s:%d'%(tag,d))
        if e: n+=e['unit_ops'].get(op,0)
    return n

def evsell(r,tag,lo,hi):
    c=collections.Counter()
    for d in range(lo,hi+1):
        e=r['events'].get('%s:%d'%(tag,d))
        if e:
            for k,v in e['sells'].items(): c[k]+=v
    return c

def evhire(r,tag,lo,hi):
    n=0
    for d in range(lo,hi+1):
        e=r['events'].get('%s:%d'%(tag,d))
        if e: n+=e['hire_orders']
    return n

def evland(r,tag,lo,hi):
    n=0
    for d in range(lo,hi+1):
        e=r['events'].get('%s:%d'%(tag,d))
        if e: n+=e['buy_land_orders']
    return n

def escapes(r,tag,lo,hi):
    return sum((r['tile_events'].get(tag,{}).get(str(d)) or {}).get('escape',0) for d in range(lo,hi+1))

def droughts(r,tag,lo,hi):
    return sum((r['tile_events'].get(tag,{}).get(str(d)) or {}).get('drought_death',0) for d in range(lo,hi+1))

def build(data,routes):
    rows=[]
    for r in data:
        days=[d for d in range(30) if 'us:%d'%d in r['snap_h23']]
        pos=[d for d in days if diff(r,d)>0]
        late=[diff(r,d) for d in range(11,30) if 'us:%d'%d in r['snap_h23']]
        f={
          'ep':r['ep'],'dir':r['dir'],'opp':r['opp'],'seat':r['us_seat'],
          'margin':r['margin'],'win':r['win'],
          'pnd':(max(pos)+1) if pos else None,'last_pos':max(pos) if pos else None,
          'route':routes.get(r['ep'],{}).get('logic_route'),
          'expert':routes.get(r['ep'],{}).get('expert'),
          'shops':','.join(routes.get(r['ep'],{}).get('shops_pair') or []),
          'diff6':diff(r,6),'diff10':diff(r,10),'diff12':diff(r,12),'diff15':diff(r,15),
          'late_span':(max(late)-min(late)) if late else None,
          'late_min':min(late) if late else None,'late_max':max(late) if late else None,
          'us_money6':gh(r,'us',6,'money'),'us_money10':gh(r,'us',10,'money'),
          'us_money12':gh(r,'us',12,'money'),'th_money12':gh(r,'them',12,'money'),
          'herd6':gh(r,'us',6,'herd_total'),'herd6t':gh(r,'them',6,'herd_total'),
          'herd10':gh(r,'us',10,'herd_total'),'herd10t':gh(r,'them',10,'herd_total'),
          'herd12':gh(r,'us',12,'herd_total'),'herd12t':gh(r,'them',12,'herd_total'),
          'herd29':gh(r,'us',29,'herd_total'),'herd29t':gh(r,'them',29,'herd_total'),
          'past12':gh(r,'us',12,'pasture'),'past12t':gh(r,'them',12,'pasture'),
          'coop12':gh(r,'us',12,'coop'),'coop12t':gh(r,'them',12,'coop'),
          'struct12':gh(r,'us',12,'struct_total'),'struct12t':gh(r,'them',12,'struct_total'),
          'emptyp12':gh(r,'us',12,'empty_pasture'),'emptyp12t':gh(r,'them',12,'empty_pasture'),
          'emptyp6':gh(r,'us',6,'empty_pasture'),'emptyp6t':gh(r,'them',6,'empty_pasture'),
          'crops12':gh(r,'us',12,'crops_total'),'crops12t':gh(r,'them',12,'crops_total'),
          'crops10':gh(r,'us',10,'crops_total'),'crops10t':gh(r,'them',10,'crops_total'),
          'hands12':gh(r,'us',12,'hands'),'hands12t':gh(r,'them',12,'hands'),
          'hands6':gh(r,'us',6,'hands'),'hands6t':gh(r,'them',6,'hands'),
          'hands10':gh(r,'us',10,'hands'),'hands10t':gh(r,'them',10,'hands'),
          'buyanim6_10':sum(evbuy(r,'us',a,6,10) for a in ('COW','SHEEP','GOOSE')),
          'buyanim6_10t':sum(evbuy(r,'them',a,6,10) for a in ('COW','SHEEP','GOOSE')),
          'buyanim0_5':sum(evbuy(r,'us',a,0,5) for a in ('COW','SHEEP','GOOSE')),
          'buyanim0_5t':sum(evbuy(r,'them',a,0,5) for a in ('COW','SHEEP','GOOSE')),
          'buyanim11_29':sum(evbuy(r,'us',a,11,29) for a in ('COW','SHEEP','GOOSE')),
          'buyanim11_29t':sum(evbuy(r,'them',a,11,29) for a in ('COW','SHEEP','GOOSE')),
          'buyanim_all':sum(evbuy(r,'us',a,0,29) for a in ('COW','SHEEP','GOOSE')),
          'place6_10':evop(r,'us','PLACE',6,10),'place6_10t':evop(r,'them','PLACE',6,10),
          'buildp6_10':sum(evop(r,'us',o,6,10) for o in ('BUILD_PASTURE','BUILD_COOP')),
          'buildp6_10t':sum(evop(r,'them',o,6,10) for o in ('BUILD_PASTURE','BUILD_COOP')),
          'buildp0_5':sum(evop(r,'us',o,0,5) for o in ('BUILD_PASTURE','BUILD_COOP')),
          'buildp0_5t':sum(evop(r,'them',o,0,5) for o in ('BUILD_PASTURE','BUILD_COOP')),
          'buildp11_29':sum(evop(r,'us',o,11,29) for o in ('BUILD_PASTURE','BUILD_COOP')),
          'land_by10':evland(r,'us',0,10),'land_by10t':evland(r,'them',0,10),
          'land_day':next((d for d in range(30) if evland(r,'us',d,d)),None),
          'land_dayt':next((d for d in range(30) if evland(r,'them',d,d)),None),
          'esc_by10':escapes(r,'us',0,10),'esc_by10t':escapes(r,'them',0,10),
          'esc_by29':escapes(r,'us',0,29),'esc_by29t':escapes(r,'them',0,29),
          'drought_by10':droughts(r,'us',0,10),'drought_by10t':droughts(r,'them',0,10),
          'drought_by29':droughts(r,'us',0,29),'drought_by29t':droughts(r,'them',0,29),
          'unfed_streak_6_10':cum(r,'us','unfed_streak1',6,10),
          'unfed_streak_6_10t':cum(r,'them','unfed_streak1',6,10),
          'unfed_today_6_10':cum(r,'us','unfed_today',6,10),
          'unfed_today_6_10t':cum(r,'them','unfed_today',6,10),
          'uwater_6_10':cum(r,'us','unwater_streak1',6,10),
          'uwater_6_10t':cum(r,'them','unwater_streak1',6,10),
          'weeds12':gh(r,'us',12,'weeds'),'weeds12t':gh(r,'them',12,'weeds'),
          'empty12':gh(r,'us',12,'empty_tiles'),'empty12t':gh(r,'them',12,'empty_tiles'),
          'hire_6_10':evhire(r,'us',6,10),'hire_6_10t':evhire(r,'them',6,10),
          'hire_0_5':evhire(r,'us',0,5),'hire_0_5t':evhire(r,'them',0,5),
          'sell6_10':sum(evsell(r,'us',6,10).values()),
          'sell6_10t':sum(evsell(r,'them',6,10).values()),
          'sell0_5':sum(evsell(r,'us',0,5).values()),
          'sell0_5t':sum(evsell(r,'them',0,5).values()),
          'sell_all':sum(evsell(r,'us',0,29).values()),
          'sell_allt':sum(evsell(r,'them',0,29).values()),
          'milksell_6_10':evsell(r,'us',6,10).get('MILK',0),
          'milksell_6_10t':evsell(r,'them',6,10).get('MILK',0),
        }
        f['sell6_10_net']=f['sell6_10']-f['sell6_10t']
        f['frozen']= (f['late_span'] is not None and f['late_span']<300)
        rows.append(f)
    return rows
