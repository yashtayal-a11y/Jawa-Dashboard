#!/usr/bin/env python3
"""
Jawa performance dashboard: daily build from Google Drive.

  python build.py --inputs <dir> --live <live.json> --sources <sources.json> --out <dir>

  inputs/   (decrypted private bundle) frozen.json, bridge.json, mappings.json, shell.html, app.js,
            clpl_retails.json, city_tiers.csv
  live.json running archive of Drive leads (so a month never disappears when a rolling sheet is
            overwritten) plus the mobile ids handed out so far. Read and rewritten each run.
  sources   {"leads":[{"label":..,"id":..,"required":bool}], "retail":{"id":..,"gid":"0"}}

History rules
  * Lead months up to Apr'26 are frozen (validated earlier from the FY master; Drive has no Apr'26).
  * Lead months from May'26 come from the Drive "JAWA" tabs, keyed by enquiryId.
  * Retails come from the retail attribution sheet (Process = Jawa), matched by enquiryId.
  * Customer mobiles are encrypted in the sheets; they are only used as salted hashes for de-duplication.
"""
import sys, os, re, io, csv, json, time, hashlib, argparse, datetime, urllib.request, urllib.parse
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_client import make_client

MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
LIVE_FROM = "May'26"
ALIAS = {'Yezdi Scrambler 350': 'Yezdi Scrambler', 'Yezdi Scrambler (2022-2025)': 'Yezdi Scrambler',
         '2024 Yezdi Adventure': 'Yezdi Adventure', '2025 Yezdi Adventure': 'Yezdi Adventure',
         '2024 Yezdi Roadster': 'Yezdi Roadster'}
BAD = {'None', 'nan', 'NaN', '#N/A', 'NULL'}
csv.field_size_limit(1 << 24)


def s(v):
    t = '' if v is None else str(v).strip()
    return '' if t in BAD else t
def mkey(m): return int(m[-2:]) * 12 + MON.index(m[:3])
def norm_month(v):
    t = s(v)
    m = re.match(r"^([A-Za-z]{3})[a-z]*'?\s?(?:20)?(\d{2})$", t)           # Oct'2026 / Oct'26
    if m and m.group(1).title() in MON: return f"{m.group(1).title()}'{m.group(2)}"
    m = re.match(r'^(\d{4})-(\d{2})', t)                                   # 2026-10-13
    if m and 1 <= int(m.group(2)) <= 12: return f"{MON[int(m.group(2)) - 1]}'{m.group(1)[2:]}"
    return ''
def norm_dealer(c): return re.sub(r'[\s_]+$', '', s(c))
def log(*a): print(*a, flush=True)


# ---------------------------------------------------------------- fetch
def fetch_csv(sheet_id, sheet_name=None, gid=None, tries=5):
    if sheet_name:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(sheet_name)}"
    else:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid or 0}"
    err = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=300) as r:
                raw = r.read()
            text = raw.decode('utf-8-sig')
            if text.lstrip()[:1] == '<': raise RuntimeError('got HTML (sheet not shared or tab missing)')
            return list(csv.DictReader(io.StringIO(text)))
        except Exception as e:
            err = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f'fetch failed after {tries} tries: {type(err).__name__}: {err}')


# ---------------------------------------------------------------- parse
def parse_leads(rows, salt):
    """Drive JAWA tab rows -> compact lead records keyed by enquiryId."""
    out = {}
    for r in rows:
        eid = s(r.get('enquiryId'))
        if not eid: continue
        date = s(r.get('Date'))[:10]
        lm = norm_month(r.get('Lead_Month')) or norm_month(date)
        if not lm: continue
        mob = s(r.get('encrypt_mobile_number'))
        model = s(r.get('model')); model = ALIAS.get(model, model) or 'Unspecified'
        dealer = norm_dealer(r.get('oem_crm_id')) or norm_dealer(r.get('verified_dealer'))
        rec = [lm, model, dealer, s(r.get('Dealer_Name')), s(r.get('City')), s(r.get('State')), s(r.get('Status_Name')),
               hashlib.sha256((salt + mob).encode()).hexdigest()[:20] if mob else '', date or 'Unknown', s(r.get('updateTime'))]
        old = out.get(eid)
        if old is None or rec[9] > old[9]: out[eid] = rec
    return out


def parse_retails(rows):
    out = {}
    for r in rows:
        if s(r.get('Process')) != 'Jawa': continue
        eid = s(r.get('enquiryId'))
        if not eid: continue
        model = s(r.get('purchasedModel')); model = ALIAS.get(model, model)
        pm = norm_month(r.get('Performance Month')) or norm_month(r.get('performanceMonth'))
        rec = {'model': model, 'pm': pm, 'src': 'DMS' if s(r.get('Call Type')).upper() == 'DMS' else 'VOC',
               'cm': norm_month(r.get('Create Month')) or norm_month(r.get('createTime')),
               'org': s(r.get('Organization')), 'att': s(r.get('Retail_Attribution_Date'))}
        old = out.get(eid)
        if old is None or rec['att'] > old['att']: out[eid] = rec
    return out


def status_class(st, mp):
    if st in mp: return mp[st]
    t = st.lower()
    cat = 'Lost' if t.startswith('lost') else ('Converted' if ('book' in t or t.startswith('retail')) else 'Active')
    return [cat, 'Not Determined']


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inputs', required=True); ap.add_argument('--live', required=True)
    ap.add_argument('--sources', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--offline', help='dir of pre-downloaded CSVs named <label>.csv and retail.csv (testing)')
    A = ap.parse_args()
    I = lambda n: os.path.join(A.inputs, n)
    src = json.load(open(A.sources)); bridge = json.load(open(I('bridge.json')))
    maps = json.load(open(I('mappings.json'))); frozen = json.load(open(I('frozen.json')))
    salt = bridge['salt']; mob_idx = dict(bridge['map'])
    live = json.load(open(A.live)) if os.path.exists(A.live) else {'leads': {}, 'newmob': {}}
    mob_idx.update(live.get('newmob', {}))
    next_idx = max([bridge['next_idx']] + [v + 1 for v in mob_idx.values()])

    # ---- 1. leads from Drive, merged into the running archive
    leads = {k: v for k, v in live.get('leads', {}).items()}
    log(f"archive carried in: {len(leads):,} leads")
    for sh in src['leads']:
        try:
            if A.offline: rows = list(csv.DictReader(open(os.path.join(A.offline, sh['label'] + '.csv'), encoding='utf-8')))
            else: rows = fetch_csv(sh['id'], sheet_name='JAWA')
        except Exception as e:
            if sh.get('required'): sys.exit(f"required sheet '{sh['label']}' failed: {e}")
            log(f"  WARN sheet '{sh['label']}' skipped: {e}"); continue
        got = parse_leads(rows, salt); n = 0
        for eid, rec in got.items():
            if mkey(rec[0]) < mkey(LIVE_FROM): continue
            old = leads.get(eid)
            if old is None or rec[9] >= old[9]: leads[eid] = rec; n += 1
        log(f"  {sh['label']:10} {len(rows):7,} rows -> {n:7,} leads kept/updated")
    if not leads: sys.exit('no live leads at all; refusing to publish')

    # ---- 2. retails
    rs = src['retail']
    try:
        rrows = list(csv.DictReader(open(os.path.join(A.offline, 'retail.csv'), encoding='utf-8'))) if A.offline \
            else fetch_csv(rs['id'], gid=rs.get('gid'))
    except Exception as e:
        sys.exit(f'retail sheet failed: {e}')
    retails = parse_retails(rrows)
    log(f"retail sheet: {len(rrows):,} rows, {len(retails):,} Jawa retails")

    # ---- 3. dealers
    ct = {}
    for r in csv.DictReader(open(I('city_tiers.csv'), encoding='utf-8')): ct[s(r['city']).lower()] = s(r['Mapping'])
    dealers_all = frozen['dealers']; fmeta = {}
    for d, m in zip(dealers_all, frozen['dealerMeta']):
        k = norm_dealer(d)
        if k not in fmeta or (fmeta[k][4] is None and m[4] is not None): fmeta[k] = m
    latest = {}
    for rec in sorted(leads.values(), key=lambda x: x[9]): latest[rec[2]] = rec

    # ---- 4. assemble every row as a dict
    allrows = []
    F = frozen
    for r in F['rows']:       # [lm, model, dealer, sc, q, cs, isRetail, mob, date, retailModel, perfMonth, retailSource]
        allrows.append({'lm': F['months'][r[0]], 'model': F['models'][r[1]], 'dealer': norm_dealer(F['dealers'][r[2]]),
                        'sc': F['statuscats'][r[3]], 'q': F['qualstatus'][r[4]], 'cs': F['currstatus'][r[5]], 'mob': r[7],
                        'date': F['dates'][r[8]], 'rm': F['retailModels'][r[9]] if r[9] >= 0 else '',
                        'pm': F['months'][r[10]] if r[10] >= 0 else '', 'rsrc': {0: 'DMS', 1: 'VOC'}.get(r[11], '') if r[6] else ''})
    used = set(); nlive = 0
    for eid, rec in leads.items():
        lm, model, dealer, dname, city, state, st, mh, date, upd = rec
        if mh:
            if mh not in mob_idx: mob_idx[mh] = next_idx; live.setdefault('newmob', {})[mh] = next_idx; next_idx += 1
            mob = mob_idx[mh]
        else:
            mob = next_idx; next_idx += 1                                 # no mobile: never merge with another lead
        cat, q = status_class(st, maps['status'])
        row = {'lm': lm, 'model': model, 'dealer': dealer, 'sc': cat, 'q': q, 'cs': st, 'mob': mob, 'date': date,
               'rm': '', 'pm': '', 'rsrc': ''}
        rt = retails.get(eid)
        if rt:
            used.add(eid)
            row.update(rm=rt['model'] or model, pm=rt['pm'], rsrc=rt['src'])
        allrows.append(row); nlive += 1
    # retails whose lead is not in Drive: new-month ones become retail-only rows, older ones belong to frozen leads
    orphan_new = orphan_frozen = 0
    name2code = {m[0].strip().lower(): k for k, m in fmeta.items()}
    for eid, rt in retails.items():
        if eid in used: continue
        if rt['cm'] and mkey(rt['cm']) >= mkey(LIVE_FROM):
            code = name2code.get(rt['org'].strip().lower(), 'UNKNOWN')
            if code == 'UNKNOWN' and 'UNKNOWN' not in fmeta: fmeta['UNKNOWN'] = [rt['org'] or 'Unknown dealer', 'Unknown', 'Unknown', 'ROI', None, 0]
            allrows.append({'lm': rt['cm'], 'model': rt['model'] or 'Unspecified', 'dealer': code, 'sc': 'Converted',
                            'q': 'Qualified', 'cs': 'Retail Attribution', 'mob': next_idx, 'date': 'Unknown',
                            'rm': rt['model'], 'pm': rt['pm'], 'rsrc': rt['src']})
            next_idx += 1; orphan_new += 1
        else:
            orphan_frozen += 1
    log(f"live leads {nlive:,}; retail-only rows {orphan_new}; retails on frozen months (already in frozen data, not re-added) {orphan_frozen}")

    # ---- 5. encode
    months = sorted({x['lm'] for x in allrows} | {x['pm'] for x in allrows if x['pm']}, key=mkey)
    def enc(vals): v = sorted(set(vals)); return v, {x: i for i, x in enumerate(v)}
    models, mo = enc(x['model'] for x in allrows); scs, sc = enc(x['sc'] for x in allrows)
    qs, qu = enc(x['q'] for x in allrows); css, cu = enc(x['cs'] for x in allrows)
    dates, da = enc(x['date'] for x in allrows); rms, rmi = enc(x['rm'] for x in allrows if x['rm'])
    dealers, di = enc(x['dealer'] for x in allrows); mi = {m: i for i, m in enumerate(months)}
    meta = []; newd = []
    for dc in dealers:
        if dc in fmeta: meta.append(fmeta[dc]); continue
        l = latest.get(dc)
        if l: meta.append([l[3] or dc, l[4] or 'Unknown', l[5] or 'Unknown', ct.get((l[4] or '').lower(), 'ROI'), None, 0]); newd.append(dc)
        else: meta.append([dc, 'Unknown', 'Unknown', 'ROI', None, 0])
    rows = []
    for x in allrows:
        isr = 1 if x['rm'] else 0
        rows.append([mi[x['lm']], mo[x['model']], 0, 0, di[x['dealer']], sc[x['sc']], qu[x['q']], cu[x['cs']], isr, x['mob'],
                     da[x['date']], rmi[x['rm']] if isr else -1, mi[x['pm']] if (isr and x['pm']) else -1,
                     {'DMS': 0, 'VOC': 1}.get(x['rsrc'], 2) if isr else 2])
    DATA = {'months': months, 'models': models, 'sources': ['Total'], 'leadtypes': ['All'], 'statuscats': scs, 'qualstatus': qs,
            'currstatus': css, 'dealers': dealers, 'dealerMeta': meta, 'dates': dates, 'rows': rows, 'retailModels': rms,
            'retailSources': ['DMS', 'VOC', '']}

    # ---- 6. render (client copy: Source / Lead Type already collapsed above)
    shell = open(I('shell.html'), encoding='utf-8').read(); app = open(I('app.js'), encoding='utf-8').read()
    clpl = {k: v for k, v in json.load(open(I('clpl_retails.json'))).items() if not k.startswith('_')}
    a = app.index('const CLPL_RETAILS = {'); b = app.index('};', a) + 2
    app = app[:a] + 'const CLPL_RETAILS = ' + json.dumps(clpl) + ';' + app[b:]
    today = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=5, minutes=30)
    period = f"{months[0]}–{months[-1]}"
    shell, n = re.subn(r"Jawa Performance Dashboard \(May'25–[A-Z][a-z]{2}'\d\d\)", f"Jawa Performance Dashboard ({period})", shell)
    assert n >= 1, 'title pattern not found in shell.html'
    shell = shell.replace("May'25 to Jun'26<br>", f"{months[0]} to {months[-1]}<br>").replace('Source: Master Lead File', 'Source: Bike CPS LMS sheets')
    app, n = re.subn(r"document\.getElementById\('genDate'\)\.textContent = [^\n]*",
                     "document.getElementById('genDate').textContent = " + json.dumps('Data as of ' + today.strftime('%d %b %Y, %H:%M IST')) + ';', app, count=1)
    assert n == 1, 'genDate line not found in app.js'
    ch, cdata, capp = make_client(shell, DATA, app)
    auth_on = os.environ.get('JAWA_AUTH', '').lower() != 'off'
    build_id = today.strftime('%Y%m%d%H%M%S'); built = today.strftime('%d %b %H:%M IST')
    repo = os.environ.get('GITHUB_REPOSITORY', 'yashtayal-a11y/Jawa-Dashboard')
    rjs = (open(os.path.join(HERE, 'refresh.js'), encoding='utf-8').read().replace('__BUILD_ID__', build_id).replace('__BUILT__', built)
           .replace('__RUN_URL__', f'https://github.com/{repo}/actions/workflows/deploy.yml').replace('__AUTH_ON__', 'true' if auth_on else 'false'))
    REFRESH = '<script>\n' + rjs + '\n</script>\n'
    data_js = json.dumps(cdata, separators=(',', ':'))
    if not auth_on:                                            # an outer login (Cloudflare Access) is in place
        html = ch + '<script>\nconst DATA = ' + data_js + ';\n</script>\n<script>\n' + capp + '\n</script>\n' + REFRESH + '</body>\n</html>'
    else:
        # the dashboard script is kept inert (text/plain) and started by auth.js once a user is signed in
        auth = open(os.path.join(HERE, 'auth.js'), encoding='utf-8').read()
        html = (ch + '<script>\nconst DATA = ' + data_js + ';\n</script>\n'
                '<script type="text/plain" id="jawa-app">\n' + capp.replace('</script', '<\\/script') + '\n</script>\n'
                '<script>\n' + auth + '\n</script>\n' + REFRESH + '</body>\n</html>')
    os.makedirs(A.out, exist_ok=True)
    open(os.path.join(A.out, 'client.html'), 'w', encoding='utf-8').write(html)

    live['leads'] = leads
    json.dump(live, open(A.live, 'w'), separators=(',', ':'))

    # ---- report
    agg = defaultdict(lambda: [0, 0, 0, 0])
    for r in rows:
        agg[months[r[0]]][0] += 1
        if r[8]:
            agg[months[r[0]]][1] += 1; k = months[r[12]] if r[12] >= 0 else '(no perf month)'
            agg[k][2] += 1; agg[k][3] += r[13] == 0
    log(f"\nTOTAL leads {len(rows):,} | unique mobiles {len({r[9] for r in rows}):,} | retails {sum(r[8] for r in rows):,} | dealers {len(dealers)} | models {len(models)}")
    if newd: log(f"new dealers (OEM tier = Unclassified): {len(newd)}")
    log(f"{'Month':14}{'Leads':>9}{'Ret(lead mo)':>14}{'Ret(perf mo)':>14}{'DMS':>7}")
    for m in sorted(agg, key=lambda m: mkey(m) if "'" in m else 99999):
        log(f"{m:14}{agg[m][0]:9,}{agg[m][1]:14,}{agg[m][2]:14,}{agg[m][3]:7,}")
    json.dump({'built_ist': today.strftime('%Y-%m-%d %H:%M'), 'leads': len(rows), 'months': months[-1]},
              open(os.path.join(A.out, 'summary.json'), 'w'))
    json.dump({'id': build_id, 'built': built}, open(os.path.join(A.out, 'version.json'), 'w'))


if __name__ == '__main__':
    main()
