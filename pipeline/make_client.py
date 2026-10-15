"""Client copy of the dashboard: Source and Lead Type are collapsed to a single value in the
data itself (nothing source/lead-type level ships) and every source/lead-type view is removed."""
import copy

def rep(s, old, new, count=1):
    n = s.count(old)
    assert n >= 1, ('client transform: text not found in template', old[:80])
    if count == 1: assert n == 1, ('client transform: text not unique', n, old[:80])
    return s.replace(old, new)

def make_client(shell, DATA, app):
    d = copy.deepcopy(DATA)
    d['sources'] = ['Total']; d['leadtypes'] = ['All']
    for r in d['rows']: r[2] = 0; r[3] = 0
    # ---------- HTML
    h = shell
    h = rep(h, '<button class="tab-btn" data-tab="ltmonthly">Lead Type — Month on Month</button>',
               '<button class="tab-btn" data-tab="ltmonthly" style="display:none">Lead Type — Month on Month</button>')
    h = rep(h, '<div class="tab-content" id="tab-ltmonthly">', '<div class="tab-content" id="tab-ltmonthly" style="display:none !important">')
    # Overview: lead trend full width, drop Source Mix, Lead Type Split, Conversion by Source
    h = rep(h, '''  <div class="grid">
    <div class="panel">
      <h3>Monthly Trend by Source</h3>
      <div class="desc">Lead volume across the full period, split by acquisition source</div>''',
    '''  <div>
    <div class="panel">
      <h3>Monthly Lead Trend</h3>
      <div class="desc">Lead volume across the full period, by the month the lead was generated</div>''')
    h = rep(h, '''    <div class="panel">
      <h3>Source Mix</h3>''', '''    <div class="panel" style="display:none">
      <h3>Source Mix</h3>''')
    h = rep(h, '<h3>Monthly Retail Trend by Source</h3>', '<h3>Monthly Retail Trend</h3>')
    h = rep(h, 'Retail volume across the full period, split by acquisition source. ', 'Retail volume across the full period. ')
    h = rep(h, '''  <div class="grid">
    <div class="panel">
      <h3>Lead Type Split</h3>''', '''  <div class="grid" style="display:none">
    <div class="panel">
      <h3>Lead Type Split</h3>''')
    h = rep(h, " &middot; Lead Type shown as source-system codes", "")
    # Model MoM: no source split
    h = rep(h, '<button class="btn" id="tab8ExpandAll">Expand all months</button>', '<button class="btn" id="tab8ExpandAll" style="display:none">Expand all months</button>')
    h = rep(h, '<button class="btn" id="tab8CollapseAll">Collapse all months</button>', '<button class="btn" id="tab8CollapseAll" style="display:none">Collapse all months</button>')
    i = h.index('<table class="tier-table" id="tab8Table">'); j = h.index('<div class="paid-organic-legend"', i)
    k = h.index('</div>', j) + len('</div>')
    h = h[:j] + '<div style="margin-top:12px; font-size:11px;"><span style="color:#8fbfe0;">■</span> Leads <span style="color:#e0a458;">■</span> Retails <span style="color:#7fceac;">■</span> CR%</div>' + h[k:]
    h = rep(h, 'Respects the main filter bar above (State, Dealer, Model, Source, etc.)', 'Respects the main filter bar above (State, Dealer, Model, etc.)')
    h = rep(h, '(e.g. Dealer &rarr; Source &rarr; Lead Type)', '(e.g. State &rarr; City &rarr; Dealer)')
    h = rep(h, '</style>', '#tab8Thead .month-toggle{ cursor:default; } #tab8Thead .month-toggle-icon{ display:none; }\n</style>')
    assert h.count('{') == h.count('}')
    h = h.replace('<title>', '<title>', 1)

    # ---------- JS
    s = app
    s = rep(s, "  {key:'source', label:'Source', options: sources, counts: sourceCounts},\n  {key:'leadtype', label:'Lead Type', options: leadtypes, counts: leadtypeCounts},\n", '')
    s = rep(s, "  {key:'source',   label:'Source',              lead:it=>sources[it.s]},\n  {key:'lt',       label:'Lead Type',           lead:it=>leadtypes[it.lt]},\n", '')
    s = rep(s, "  {label:'Dealer × Source',           rows:['dealer','source'], col:''},\n  {label:'Dealer × Lead Type',        rows:['dealer','lt'],     col:''},\n", '')
    s = rep(s, "  {label:'Source × Lead Type',        rows:['source','lt'],     col:''},\n", '')
    # Model MoM: months never expand into source buckets
    s = rep(s, "function renderMonthSourceTable(theadEl, tbodyEl, dimField, dimLabels, firstColLabel, expandedSet, rerenderFn, retailMonthKey, rowsCollapsed, sortState){\n",
               "function renderMonthSourceTable(theadEl, tbodyEl, dimField, dimLabels, firstColLabel, expandedSet, rerenderFn, retailMonthKey, rowsCollapsed, sortState){\n  expandedSet.clear(); // client copy: no source split\n")
    s = rep(s, '<th colspan="3" class="total-band">Total (all sources)</th>', '<th colspan="3" class="total-band">Total</th>')
    a = s.index('const TAB8_DESC = {'); b = s.index('};', a) + 2
    s = s[:a] + '''const TAB8_DESC = {
  update: `Every model, broken out by month. <b>Leads</b> are counted in the month generated; <b>Retails</b> are counted in the month the sale was actually attributed (Performance/Update Month) &mdash; often a later month than the lead itself. Respects the main filter bar above.`,
  create: `Same view, but <b>retails are counted in the month the lead was originally created</b>, not the month the sale was attributed &mdash; a cohort view: "of the leads generated in March, how many eventually converted, no matter when the sale closed?" Respects the main filter bar above.`,
};''' + s[b:]
    return h, d, s
