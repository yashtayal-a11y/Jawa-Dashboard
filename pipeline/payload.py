"""Builds the lead-disposition payload (same schema the TVS dashboard consumes) from Jawa lead / retail rows.
Port of build_payload() from the TVS pipeline, without pandas.

leads:      list of dicts {lid, lm, src, lt, mdl, st, city, cd, dl, sn}
retail_map: {lid: {'rtype': 'DMS'|'Call Out', 'rm': "Oct'26" or '', 'pm': purchased model, 'rd': 'YYYY-MM-DD' or ''}}
"""
import re, datetime

_CITY_ALIAS = {'New Delhi': 'Delhi', 'Bengaluru': 'Bangalore', 'Bengalore': 'Bangalore',
               'Prayagraj': 'Allahabad', 'Thiruvananthapuram': 'Trivandrum'}
_COMPOUND_SEP_RE = re.compile(r'(\s*[/,|&]\s*)')
AGE_BUCKET_LABELS = ['0-7 days', '8-14 days', '15-30 days', '30+ days']


def normalize_city(raw):
    s = re.sub(r'\s+', ' ', str(raw or '').strip())
    if not s: return 'Unknown'
    s = s.title()
    if s in _CITY_ALIAS: return _CITY_ALIAS[s]
    if _COMPOUND_SEP_RE.search(s):
        tokens = _COMPOUND_SEP_RE.split(s)
        parts, seps = tokens[0::2], tokens[1::2]
        canon = [_CITY_ALIAS.get(p.strip(), p.strip()) for p in parts]
        if len(set(canon)) == 1: return canon[0]
        out = canon[0]
        for sep, cp in zip(seps, canon[1:]): out += sep + cp
        return out
    return s


_MN = {m: i + 1 for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}


def _ym(m):
    mt = re.match(r"([A-Za-z]{3})'(\d{2})", m or '')
    return (2000 + int(mt.group(2))) * 100 + _MN[mt.group(1)] if mt and mt.group(1) in _MN else 0


def day_key(date_str, month):
    """YYYYMMDD when the date falls inside `month`, else YYYYMM00 ("no day recorded" for that month)."""
    ym = _ym(month); d = str(date_str or '').strip()
    if ym and re.match(r'^\d{4}-\d{2}-\d{2}', d) and int(d[:4]) * 100 + int(d[5:7]) == ym: return ym * 100 + int(d[8:10])
    return ym * 100


def age_bucket(days):
    return 0 if days <= 7 else 1 if days <= 14 else 2 if days <= 30 else 3


def classify_status(sn):
    """'O' open, 'B' booking / retailed, 'L' lost, 'U' blank. Same buckets as the TVS map, extended to the
    extra Jawa statuses by rule (Lost* -> L, Booked / Retail* -> B, anything else with text -> O)."""
    t = ' '.join((sn or '').split())
    if not t: return 'U'
    low = t.lower()
    if low.startswith('lost'): return 'L'
    if low.startswith('booked') or low.startswith('retail'): return 'B'
    return 'O'


def _date(s):
    try: return datetime.date.fromisoformat(str(s or '').strip()[:10])
    except Exception: return None


def build_payload(leads, retail_map, built_iso):
    lm_idx, src_idx, lt_idx, mdl_idx, st_idx, zone_idx, city_idx = {}, {}, {}, {}, {}, {}, {}
    lm_arr, src_arr, lt_arr, mdl_arr, st_arr, zone_arr, city_arr = [], [], [], [], [], [], []
    dl_idx, dl_arr, sn_idx, sn_arr = {}, [], {}, []
    disp_idx, disp_arr = {}, []
    city_to_state = {}

    def ix(d, arr, v):
        if v not in d: d[v] = len(arr); arr.append(v)
        return d[v]

    M = {k: {} for k in ['monthly', 'sm', 'ltm', 'mm', 'stm', 'zm', 'bdm', 'cm', 'csm', 'cxm', 'cxsm', 'stcm', 'univ', 'mxst',
                         'mlt', 'stlt', 'cdm', 'cdsm', 'stdm', 'mxdl', 'ltdl']}
    U = {k: {} for k in ['monthly', 'sm', 'ltm', 'mm', 'stm', 'zm', 'bdm', 'cm', 'csm', 'cxm', 'cxsm', 'stcm', 'univ', 'mxst',
                         'mlt', 'stlt', 'cdm', 'cdsm', 'stdm', 'mxdl', 'ltdl']}
    disp, u_disp, pmr, u_pmr, dl_sn, snf, ram = {}, {}, {}, {}, {}, {}, {}
    dd, ddu = {}, {}
    ram_total = ram_valid = ram_neg = ram_no_rd = ram_no_cd = 0

    def bump(d, k, is_ret, rtype):
        v = d.get(k)
        if v is None: v = d[k] = [0, 0, 0, 0]
        v[0] += 1
        if is_ret:
            v[1] += 1
            ru = rtype.upper()
            if 'DMS' in ru: v[2] += 1
            elif 'CALL' in ru: v[3] += 1

    def ubump(d, kl, kr, is_ret, rtype):
        v = d.get(kl)
        if v is None: v = d[kl] = [0, 0, 0, 0]
        v[0] += 1
        if is_ret:
            w = d.get(kr)
            if w is None: w = d[kr] = [0, 0, 0, 0]
            w[1] += 1
            ru = rtype.upper()
            if 'DMS' in ru: w[2] += 1
            elif 'CALL' in ru: w[3] += 1

    for L in leads:
        lid, lm = L['lid'], L['lm']
        if not lm or not lid: continue
        src = L['src'] or 'Unknown'
        lt = L['lt'] or 'Unknown'
        mdl = L['mdl'] or 'Unknown'
        st = (L['st'] or '').strip().title() or 'Unknown'
        city = normalize_city(L['city'])
        li = ix(lm_idx, lm_arr, lm); si = ix(src_idx, src_arr, src); tti = ix(lt_idx, lt_arr, lt)
        mi = ix(mdl_idx, mdl_arr, mdl); sti = ix(st_idx, st_arr, st); zi = ix(zone_idx, zone_arr, 'Unknown')
        cti = ix(city_idx, city_arr, city); city_to_state[cti] = sti
        rt = retail_map.get(lid)
        is_ret = rt is not None
        rtype = rt['rtype'] if is_ret else ''
        bd = '0'

        bump(M['monthly'], f"{li}", is_ret, rtype)
        bump(M['sm'], f"{si}|{li}", is_ret, rtype)
        bump(M['ltm'], f"{tti}|{si}|{li}", is_ret, rtype)
        bump(M['mm'], f"{mi}|{si}|{li}", is_ret, rtype)
        bump(M['stm'], f"{sti}|{si}|{li}", is_ret, rtype)
        bump(M['mxst'], f"{mi}|{sti}|{li}", is_ret, rtype)
        bump(M['mlt'], f"{mi}|{tti}|{li}", is_ret, rtype)
        bump(M['stlt'], f"{sti}|{tti}|{li}", is_ret, rtype)
        bump(M['zm'], f"{zi}|{li}", is_ret, rtype)
        bump(M['bdm'], f"{bd}|{si}|{li}", is_ret, rtype)
        bump(M['cm'], f"{cti}|{li}", is_ret, rtype)
        bump(M['csm'], f"{cti}|{si}|{li}", is_ret, rtype)
        bump(M['cxm'], f"{cti}|{mi}|{li}", is_ret, rtype)
        bump(M['cxsm'], f"{cti}|{si}|{mi}|{li}", is_ret, rtype)
        bump(M['stcm'], f"{sti}|{cti}|{li}", is_ret, rtype)
        bump(M['univ'], f"{mi}|{si}|{sti}|{tti}|{li}", is_ret, rtype)

        sn = ' '.join((L['sn'] or '').split())
        if sn:
            sni = ix(sn_idx, sn_arr, sn)
            k = f"{sni}|{si}|{cti}|{mi}|{li}"; snf[k] = snf.get(k, 0) + 1

        dl = (L['dl'] or '').strip() or 'Unknown'
        dli = ix(dl_idx, dl_arr, dl)
        bump(M['cdm'], f"{cti}|{dli}|{li}", is_ret, rtype)
        bump(M['cdsm'], f"{cti}|{dli}|{si}|{li}", is_ret, rtype)
        bump(M['stdm'], f"{sti}|{dli}|{li}", is_ret, rtype)
        bump(M['mxdl'], f"{mi}|{dli}|{li}", is_ret, rtype)
        bump(M['ltdl'], f"{tti}|{dli}|{li}", is_ret, rtype)
        sc = classify_status(sn)
        sk = f"{cti}|{dli}|{li}"
        v = dl_sn.get(sk)
        if v is None: v = dl_sn[sk] = [0, 0, 0]
        if sc == 'B': v[1] += 1
        elif sc == 'L': v[2] += 1
        elif sc == 'O': v[0] += 1

        rm = rt.get('rm', '') if is_ret else ''
        um = rm if rm else lm
        uli = ix(lm_idx, lm_arr, um)
        ubump(U['monthly'], f"{li}", f"{uli}", is_ret, rtype)
        ubump(U['sm'], f"{si}|{li}", f"{si}|{uli}", is_ret, rtype)
        ubump(U['ltm'], f"{tti}|{si}|{li}", f"{tti}|{si}|{uli}", is_ret, rtype)
        ubump(U['mm'], f"{mi}|{si}|{li}", f"{mi}|{si}|{uli}", is_ret, rtype)
        ubump(U['stm'], f"{sti}|{si}|{li}", f"{sti}|{si}|{uli}", is_ret, rtype)
        ubump(U['mxst'], f"{mi}|{sti}|{li}", f"{mi}|{sti}|{uli}", is_ret, rtype)
        ubump(U['mlt'], f"{mi}|{tti}|{li}", f"{mi}|{tti}|{uli}", is_ret, rtype)
        ubump(U['stlt'], f"{sti}|{tti}|{li}", f"{sti}|{tti}|{uli}", is_ret, rtype)
        ubump(U['zm'], f"{zi}|{li}", f"{zi}|{uli}", is_ret, rtype)
        ubump(U['bdm'], f"{bd}|{si}|{li}", f"{bd}|{si}|{uli}", is_ret, rtype)
        ubump(U['stcm'], f"{sti}|{cti}|{li}", f"{sti}|{cti}|{uli}", is_ret, rtype)
        ubump(U['univ'], f"{mi}|{si}|{sti}|{tti}|{li}", f"{mi}|{si}|{sti}|{tti}|{uli}", is_ret, rtype)
        ubump(U['cm'], f"{cti}|{li}", f"{cti}|{uli}", is_ret, rtype)
        ubump(U['csm'], f"{cti}|{si}|{li}", f"{cti}|{si}|{uli}", is_ret, rtype)
        ubump(U['cxm'], f"{cti}|{mi}|{li}", f"{cti}|{mi}|{uli}", is_ret, rtype)
        ubump(U['cxsm'], f"{cti}|{si}|{mi}|{li}", f"{cti}|{si}|{mi}|{uli}", is_ret, rtype)
        ubump(U['stdm'], f"{sti}|{dli}|{li}", f"{sti}|{dli}|{uli}", is_ret, rtype)
        ubump(U['mxdl'], f"{mi}|{dli}|{li}", f"{mi}|{dli}|{uli}", is_ret, rtype)
        ubump(U['ltdl'], f"{tti}|{dli}|{li}", f"{tti}|{dli}|{uli}", is_ret, rtype)
        ubump(U['cdm'], f"{cti}|{dli}|{li}", f"{cti}|{dli}|{uli}", is_ret, rtype)
        ubump(U['cdsm'], f"{cti}|{dli}|{si}|{li}", f"{cti}|{dli}|{si}|{uli}", is_ret, rtype)

        # day-on-day: leads on their creation day; On Create retails sit on that day, On Update retails on their attribution day
        kd = (day_key(L['cd'], lm), mi, si, tti)
        v = dd.get(kd)
        if v is None: v = dd[kd] = [0, 0, 0, 0]
        v[0] += 1
        if is_ret:
            v[1] += 1
            if 'DMS' in rtype.upper(): v[2] += 1
            elif 'CALL' in rtype.upper(): v[3] += 1
            ku = (day_key(rt.get('ad'), um), mi, si, tti)
            w = ddu.get(ku)
            if w is None: w = ddu[ku] = [0, 0, 0]
            w[0] += 1
            if 'DMS' in rtype.upper(): w[1] += 1
            elif 'CALL' in rtype.upper(): w[2] += 1

        if is_ret:
            pm = (rt.get('pm') or '').strip() or 'Unknown'
            pmi = ix(mdl_idx, mdl_arr, pm)
            dmi = ix(disp_idx, disp_arr, pm)          # Jawa: the purchased model is its own dispersion family
            disp[f"{mi}|{dmi}|{li}"] = disp.get(f"{mi}|{dmi}|{li}", 0) + 1
            u_disp[f"{mi}|{dmi}|{uli}"] = u_disp.get(f"{mi}|{dmi}|{uli}", 0) + 1
            ru = rtype.upper()
            for d, k in ((pmr, f"{pmi}|{mi}|{si}|{li}"), (u_pmr, f"{pmi}|{mi}|{si}|{uli}")):
                v = d.get(k)
                if v is None: v = d[k] = [0, 0, 0]
                v[0] += 1
                if 'DMS' in ru: v[1] += 1
                elif 'CALL' in ru: v[2] += 1
            ram_total += 1
            rd, cd = _date(rt.get('rd')), _date(L['cd'])
            if rd is None: ram_no_rd += 1
            elif cd is None: ram_no_cd += 1
            else:
                days = (rd - cd).days
                if days < 0: ram_neg += 1
                else:
                    k = f"{mi}|{si}|{tti}|{sti}|{cti}|{age_bucket(days)}|{li}"
                    v = ram.get(k)
                    if v is None: v = ram[k] = [0, 0, 0]
                    v[0] += 1
                    if 'DMS' in ru: v[1] += 1
                    elif 'CALL' in ru: v[2] += 1
                    ram_valid += 1

    def rows(d):
        return [[*map(int, k.split('|')), *v] for k, v in d.items()]

    maps = {'lm': lm_arr, 'src': src_arr, 'lt': lt_arr, 'mdl': mdl_arr, 'st': st_arr, 'zone': zone_arr, 'city': city_arr,
            'city_state': [city_to_state.get(i) for i in range(len(city_arr))], 'ab': AGE_BUCKET_LABELS,
            'dlm': disp_arr, 'mdl_disp': list(mdl_arr), 'sn': sn_arr, 'dl': dl_arr}
    P = {'t': built_iso, 'rt_cols': 1, 'maps': maps}
    for k, d in M.items(): P[k] = rows(d)
    for k, d in U.items(): P['u_' + k] = rows(d)
    P['disp'] = [[*map(int, k.split('|')), v] for k, v in disp.items()]
    P['u_disp'] = [[*map(int, k.split('|')), v] for k, v in u_disp.items()]
    P['pmr'] = rows(pmr); P['u_pmr'] = rows(u_pmr)
    P['dl_sn'] = rows(dl_sn)
    P['ram'] = rows(ram)
    P['dd'] = [[*k, *v] for k, v in dd.items()]
    P['ddu'] = [[*k, *v] for k, v in ddu.items()]
    P['ram_meta'] = {'total': ram_total, 'valid': ram_valid, 'no_rd': ram_no_rd, 'no_cd': ram_no_cd, 'neg': ram_neg}
    P['snf'] = [[*map(int, k.split('|')), v] for k, v in snf.items()]
    return P
