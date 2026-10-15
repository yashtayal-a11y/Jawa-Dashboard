/* Sign-in and admin panel, same access service and flow as the TVS dashboard.
   The dashboard script (#jawa-app) only starts after a role of admin / full / viewer comes back. */
(function () {
  'use strict';
  var APPS_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbxpSAY5rtnfCT92KTciIrWmraLOOJ_ZKE7Jrq3S9WWOsFSdjDGsZTXLGHZlnWawU7hu/exec';
  var ALLOWED_DOMAINS = ['girnarsoft.com', 'girnarcare.com'];
  var SESSION_KEY = 'jawa_amj_auth';
  var DELAYS = [0, 500, 1000, 2000, 3000, 5000];
  var started = false, auth = null;

  var css = '' +
    '.jw-ov{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#0d0d0f 0%,#3a2410 100%);z-index:100000;font-family:Inter,system-ui,sans-serif}' +
    '.jw-card{background:#fff;border-radius:20px;padding:40px 44px;max-width:440px;width:90%;box-shadow:0 24px 60px rgba(0,0,0,.35);color:#0f172a}' +
    '.jw-logo{display:flex;align-items:center;gap:12px;margin-bottom:22px}' +
    '.jw-mark{width:40px;height:40px;border-radius:10px;background:linear-gradient(135deg,#8a5a12,#e0a458);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:900;font-size:15px}' +
    '.jw-brand{font-size:13px;font-weight:800}.jw-brand small{display:block;font-size:10px;font-weight:600;color:#8a5a12}' +
    '.jw-title{font-size:22px;font-weight:800;margin-bottom:4px}.jw-sub{font-size:12px;color:#64748B;margin-bottom:22px;line-height:1.5}' +
    '.jw-label{display:block;font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}' +
    '.jw-in{width:100%;box-sizing:border-box;padding:10px 14px;border:1.5px solid #E2E8F0;border-radius:10px;font-size:13px;font-family:inherit;outline:none}.jw-in:focus{border-color:#c8861f}' +
    '.jw-btn{width:100%;padding:12px;background:#b8741a;color:#fff;border:none;border-radius:10px;font-size:13px;font-weight:700;font-family:inherit;cursor:pointer;margin-top:12px}.jw-btn:hover{background:#8a5a12}.jw-btn:disabled{background:#CBD5E1;cursor:not-allowed}' +
    '.jw-note{font-size:10px;color:#94A3B8;text-align:center;margin-top:16px;line-height:1.5}' +
    '.jw-err{background:#FEE2E2;border:1px solid #FECACA;border-radius:8px;padding:8px 12px;font-size:11px;color:#B91C1C;margin-bottom:12px}' +
    '.jw-ok{background:#DCFCE7;border:1px solid #BBF7D0;border-radius:8px;padding:8px 12px;font-size:11px;color:#166534;margin-bottom:12px}' +
    '.jw-warn{background:#FEF3C7;border:1px solid #FDE68A;border-radius:8px;padding:10px 14px;font-size:12px;color:#92400E;margin-bottom:16px}' +
    '.jw-back{background:none;border:none;color:#94A3B8;font-size:11px;cursor:pointer;font-family:inherit;margin-top:12px;text-decoration:underline;display:block;margin-left:auto;margin-right:auto}' +
    '.jw-chip{position:fixed;bottom:8px;right:8px;z-index:9000;display:flex;gap:6px;align-items:center;font-family:Inter,system-ui,sans-serif}' +
    '.jw-pill{background:rgba(20,20,22,.88);color:#f1e3c8;border:1px solid #5a4528;border-radius:20px;padding:4px 10px;font-size:11px;font-weight:600;cursor:pointer;font-family:inherit}.jw-pill:hover{background:#3a2a14}' +
    '.jw-pill.static{cursor:default}.jw-pill.static:hover{background:rgba(20,20,22,.88)}' +
    '.jw-admin{position:fixed;inset:0;z-index:100001;background:#f8fafc;overflow:auto;font-family:Inter,system-ui,sans-serif;color:#0f172a}' +
    '.jw-nav{background:#fff;border-bottom:1px solid #E2E8F0;padding:12px 24px;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}' +
    '.jw-wrap{max-width:860px;margin:32px auto;padding:0 20px;display:flex;flex-direction:column;gap:20px}' +
    '.jw-panel{background:#fff;border:1px solid #E2E8F0;border-radius:14px;padding:26px 30px;box-shadow:0 4px 16px rgba(0,0,0,.06)}' +
    '.jw-h{font-size:16px;font-weight:800;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center}' +
    '.jw-hs{font-size:11px;color:#64748B;margin-bottom:14px}' +
    '.jw-req{display:flex;align-items:center;justify-content:space-between;padding:12px 14px;border:1px solid #E2E8F0;border-radius:10px;margin-bottom:8px;gap:12px;flex-wrap:wrap}' +
    '.jw-sel{border:1px solid #E2E8F0;border-radius:8px;padding:5px 8px;font-size:11px;font-family:inherit;background:#fff}' +
    '.jw-yes{background:#DCFCE7;color:#166534;border:1px solid #BBF7D0;border-radius:8px;padding:5px 14px;font-size:11px;font-weight:700;cursor:pointer;font-family:inherit}.jw-yes:disabled{opacity:.5;cursor:not-allowed}' +
    '.jw-no{background:#FEE2E2;color:#B91C1C;border:1px solid #FECACA;border-radius:8px;padding:5px 14px;font-size:11px;font-weight:700;cursor:pointer;font-family:inherit}' +
    '.jw-sm{background:#fff;border:1px solid #CBD5E1;border-radius:8px;padding:5px 12px;font-size:11px;cursor:pointer;font-family:inherit}' +
    '.jw-tbl{width:100%;border-collapse:collapse;font-size:12px}.jw-tbl th{background:#3a2a14;color:#fff;text-align:left;padding:9px 12px;font-size:11px;letter-spacing:.06em}.jw-tbl td{padding:9px 12px;border-bottom:1px solid #E2E8F0}' +
    '.jw-badge{padding:2px 10px;border-radius:12px;font-weight:700;font-size:11px}' +
    'body.jw-locked{overflow:hidden}';
  var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
  document.body.classList.add('jw-locked');

  function el(tag, attrs, kids) {
    var e = document.createElement(tag);
    for (var k in (attrs || {})) {
      if (k === 'class') e.className = attrs[k];
      else if (k === 'text') e.textContent = attrs[k];
      else if (k.slice(0, 2) === 'on') e.addEventListener(k.slice(2), attrs[k]);
      else e.setAttribute(k, attrs[k]);
    }
    [].concat(kids || []).forEach(function (c) { if (c != null && c !== false) e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
    return e;
  }
  var layer = null;
  function show(node) { if (layer) layer.remove(); layer = node; document.body.appendChild(node); }
  function clear() { if (layer) { layer.remove(); layer = null; } }
  function logo() {
    return el('div', { class: 'jw-logo' }, [el('div', { class: 'jw-mark', text: 'J' }),
      el('div', { class: 'jw-brand' }, ['Jawa Yezdi BSA', el('small', { text: 'Performance Dashboard' })])]);
  }
  function card(children) { return el('div', { class: 'jw-ov' }, el('div', { class: 'jw-card' }, [logo()].concat(children))); }

  // ---------------- access service
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  async function safeJson(r, label) {
    if (!r.ok) throw new Error(label + ': server returned ' + r.status);
    var t = await r.text();
    if (t.trim().charAt(0) === '<') throw new Error('Access service temporarily unavailable, please try again in a few seconds.');
    return JSON.parse(t);
  }
  async function fetchRole(email, onProg) {
    for (var a = 0; a < DELAYS.length; a++) {
      if (DELAYS[a]) await sleep(DELAYS[a]);
      if (onProg) onProg(a + 1, DELAYS.length);
      var ctrl = new AbortController(), tm = setTimeout(function () { ctrl.abort(); }, 25000);
      try { return await safeJson(await fetch(APPS_SCRIPT_URL + '?action=checkRole&email=' + encodeURIComponent(email), { signal: ctrl.signal }), 'checkRole'); }
      catch (e) { /* retry */ } finally { clearTimeout(tm); }
    }
    throw new Error('Access service is temporarily unavailable. Please try again in 1-2 minutes.');
  }
  async function post(action, body) {
    return safeJson(await fetch(APPS_SCRIPT_URL + '?action=' + action, { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body: JSON.stringify(body) }), action);
  }
  async function get(action, email) { return safeJson(await fetch(APPS_SCRIPT_URL + '?action=' + action + '&email=' + encodeURIComponent(email)), action); }

  // ---------------- screens
  function loginScreen(msg) {
    var inp = el('input', { class: 'jw-in', type: 'email', required: 'required', placeholder: 'you@girnarsoft.com', autofocus: 'autofocus' });
    var btn = el('button', { class: 'jw-btn', type: 'submit', text: 'Continue →' });
    var note = el('div', { class: 'jw-note' }); var err = el('div', { class: 'jw-err', style: 'display:none' });
    if (msg) { err.textContent = msg; err.style.display = ''; }
    var form = el('form', { onsubmit: async function (ev) {
      ev.preventDefault();
      var e = inp.value.trim().toLowerCase(); if (!e) return;
      var dom = e.split('@')[1] || '';
      if (ALLOWED_DOMAINS.indexOf(dom) < 0) return restricted();
      btn.disabled = true; btn.textContent = 'Checking…'; err.style.display = 'none';
      try {
        var res = await fetchRole(e, function (n, t) { if (n > 1) note.textContent = 'Access service is responding slowly, retrying (' + n + '/' + t + ')…'; });
        if (res.error) throw new Error(res.error);
        setAuth(e, '', res.role);
      } catch (ex) { err.textContent = 'Could not verify access: ' + ex.message; err.style.display = ''; btn.disabled = false; btn.textContent = 'Continue →'; note.textContent = ''; }
    } }, [el('label', { class: 'jw-label', text: 'Work Email' }), inp, btn, note]);
    show(card([el('div', { class: 'jw-title', text: 'Sign In' }), el('div', { class: 'jw-sub', text: 'Enter your work email to access the dashboard.' }), err, form,
      el('div', { class: 'jw-note', text: 'Access is limited to @girnarsoft.com and @girnarcare.com email addresses.' })]));
  }
  function restricted() {
    show(card([el('div', { class: 'jw-title', text: 'Access Denied' }), el('div', { class: 'jw-sub', text: 'This dashboard is only accessible to @girnarsoft.com and @girnarcare.com email addresses.' }),
      el('div', { class: 'jw-err', text: '⛔ Your email domain is not authorised' }), el('button', { class: 'jw-back', text: '← Try a different email', onclick: signOut })]));
  }
  function requestScreen(email) {
    var name = el('input', { class: 'jw-in', type: 'text', required: 'required', placeholder: 'Full name', autofocus: 'autofocus' });
    var err = el('div', { class: 'jw-err', style: 'display:none' }); var btn = el('button', { class: 'jw-btn', type: 'submit', text: 'Request Access' });
    var form = el('form', { onsubmit: async function (ev) {
      ev.preventDefault(); if (!name.value.trim()) return;
      btn.disabled = true; btn.textContent = 'Submitting…';
      try {
        var res = await post('requestAccess', { email: email, name: name.value.trim() });
        if (res.error) throw new Error(res.error);
        if (res.role) return setAuth(email, name.value.trim(), res.role);
        show(card([el('div', { class: 'jw-ok', text: '✓ Access request submitted.' }), el('div', { class: 'jw-sub', text: "Your request has been sent to an admin. You'll be able to sign in once approved." }),
          el('button', { class: 'jw-back', text: '← Back to sign in', onclick: signOut })]));
      } catch (ex) { err.textContent = 'Request failed: ' + ex.message; err.style.display = ''; btn.disabled = false; btn.textContent = 'Request Access'; }
    } }, [el('label', { class: 'jw-label', text: 'Your Name' }), name, btn]);
    show(card([el('div', { class: 'jw-title', text: 'Request Access' }), el('div', { class: 'jw-sub', text: "You don't have access yet. Submit a request and an admin will review it." }), err,
      el('div', { class: 'jw-sub', style: 'background:#F0F4FF;border-radius:8px;padding:8px 12px;font-family:monospace', text: email }), form,
      el('button', { class: 'jw-back', text: '← Use a different email', onclick: signOut })]));
  }
  var pendTimer = null;
  function pendingScreen(email) {
    var btn = el('button', { class: 'jw-btn', text: '↻ Check Now', onclick: async function () {
      btn.disabled = true; try { var r = await fetchRole(email); if (r.role !== 'pending') setAuth(email, '', r.role); } catch (e) {} btn.disabled = false; } });
    clearInterval(pendTimer);
    pendTimer = setInterval(async function () { try { var r = await fetchRole(email); if (r.role !== 'pending') { clearInterval(pendTimer); setAuth(email, '', r.role); } } catch (e) {} }, 30000);
    show(card([el('div', { class: 'jw-title', text: 'Access Pending' }), el('div', { class: 'jw-sub', text: 'Your access request is awaiting admin approval.' }),
      el('div', { class: 'jw-warn', text: '⏳ Request pending review, auto-checking every 30s' }), btn,
      el('button', { class: 'jw-back', text: '← Use a different email', onclick: signOut })]));
  }

  // ---------------- admin panel
  function adminPanel() {
    var msg = el('div'), umsg = el('div');
    var pendBox = el('div', null, 'Loading…'), userBox = el('div', null, 'Loading…');
    var BADGE = { admin: ['#EDE9FE', '#6D28D9'], full: ['#D1FAE5', '#065F46'], viewer: ['#DBEAFE', '#1E40AF'] };
    async function loadPending() {
      pendBox.textContent = 'Loading…';
      try {
        var res = await get('getPending', auth.email), p = res.pending || {}, keys = Object.keys(p);
        pendBox.textContent = '';
        if (!keys.length) { pendBox.appendChild(el('div', { style: 'text-align:center;padding:28px;color:#94A3B8', text: '🎉 No pending requests' })); return; }
        keys.forEach(function (email) {
          var sel = el('select', { class: 'jw-sel' }, [el('option', { value: 'viewer', text: 'Viewer' }), el('option', { value: 'full', text: 'Full Access' })]);
          var ok = el('button', { class: 'jw-yes', text: 'Approve' }), no = el('button', { class: 'jw-no', text: 'Reject' });
          async function act(decision) {
            ok.disabled = no.disabled = true;
            try {
              await post('reviewRequest', { adminEmail: auth.email, targetEmail: email, decision: decision, role: sel.value });
              msg.className = 'jw-ok'; msg.textContent = decision === 'approve' ? '✓ Approved ' + email + ' as ' + sel.value : '✓ Rejected ' + email;
              loadPending(); loadUsers();
            } catch (e) { alert('Error: ' + e.message); ok.disabled = no.disabled = false; }
          }
          ok.addEventListener('click', function () { act('approve'); }); no.addEventListener('click', function () { act('reject'); });
          var when = p[email].requestedAt ? new Date(p[email].requestedAt).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';
          pendBox.appendChild(el('div', { class: 'jw-req' }, [
            el('div', null, [el('div', { style: 'font-weight:700;font-size:13px', text: p[email].name || '(no name)' }), el('div', { style: 'font-size:11px;color:#64748B;font-family:monospace', text: email }),
              el('div', { style: 'font-size:10px;color:#94A3B8', text: 'Requested: ' + when })]),
            el('div', { style: 'display:flex;gap:8px;align-items:center' }, [sel, ok, no])]));
        });
      } catch (e) { pendBox.textContent = 'Could not load requests: ' + e.message; }
    }
    async function loadUsers() {
      userBox.textContent = 'Loading…';
      try {
        var res = await get('getUsers', auth.email), u = res.users || {};
        var order = { admin: 0, full: 1, viewer: 2 };
        var keys = Object.keys(u).sort(function (a, b) { return (order[u[a].role] == null ? 3 : order[u[a].role]) - (order[u[b].role] == null ? 3 : order[u[b].role]); });
        var tb = el('tbody');
        keys.forEach(function (email) {
          var info = u[email], b = BADGE[info.role] || BADGE.viewer, cell = el('td');
          if (info.role === 'admin') cell.appendChild(el('span', { style: 'color:#94A3B8', text: '—' }));
          else {
            var sel = el('select', { class: 'jw-sel' }, [el('option', { value: 'viewer', text: 'Viewer' }), el('option', { value: 'full', text: 'Full' }), el('option', { value: 'remove', text: 'Remove Access' })]);
            sel.value = info.role; var save = el('button', { class: 'jw-yes', text: 'Save' });
            save.addEventListener('click', async function () {
              if (sel.value === info.role) return; save.disabled = true;
              try { await post('updateRole', { adminEmail: auth.email, targetEmail: email, role: sel.value }); umsg.className = 'jw-ok'; umsg.textContent = '✓ Updated ' + email; loadUsers(); }
              catch (e) { alert('Error: ' + e.message); save.disabled = false; }
            });
            cell.appendChild(el('div', { style: 'display:flex;gap:6px' }, [sel, save]));
          }
          tb.appendChild(el('tr', null, [el('td', { text: email }), el('td', { text: info.name || '—' }),
            el('td', null, el('span', { class: 'jw-badge', style: 'background:' + b[0] + ';color:' + b[1], text: info.role })), cell]));
        });
        userBox.textContent = '';
        userBox.appendChild(el('div', { style: 'overflow-x:auto' }, el('table', { class: 'jw-tbl' }, [el('thead', null, el('tr', null, ['EMAIL', 'NAME', 'ROLE', 'CHANGE TO'].map(function (h) { return el('th', { text: h }); }))), tb])));
      } catch (e) { userBox.textContent = 'Could not load users: ' + e.message; }
    }
    var root = el('div', { class: 'jw-admin' }, [
      el('div', { class: 'jw-nav' }, [
        el('div', { style: 'display:flex;gap:12px;align-items:center' }, [el('div', { class: 'jw-mark', text: 'J' }), el('div', null, [el('div', { style: 'font-size:13px;font-weight:800', text: 'Jawa Yezdi BSA' }), el('div', { style: 'font-size:10px;font-weight:600;color:#8a5a12', text: 'Admin Panel — Performance Dashboard' })])]),
        el('div', { style: 'display:flex;gap:8px;align-items:center' }, [el('span', { style: 'font-size:11px;color:#475569', text: auth.email }),
          el('button', { class: 'jw-sm', text: '📊 View Dashboard', onclick: function () { clear(); layer = null; } }), el('button', { class: 'jw-sm', text: 'Sign Out', onclick: signOut })])]),
      el('div', { class: 'jw-wrap' }, [
        el('div', { class: 'jw-panel' }, [el('div', { class: 'jw-h' }, ['Access Requests', el('button', { class: 'jw-sm', text: '⟳ Refresh', onclick: loadPending })]), el('div', { class: 'jw-hs', text: 'Approve or reject pending access requests.' }), msg, pendBox]),
        el('div', { class: 'jw-panel' }, [el('div', { class: 'jw-h' }, ['👥 User Access Management', el('button', { class: 'jw-sm', text: '⟳ Refresh', onclick: loadUsers })]),
          el('div', { class: 'jw-hs', text: 'viewer / full — see the dashboard; admin — also manages users. The user list is shared with the TVS dashboard.' }), umsg, userBox])])]);
    show(root); loadPending(); loadUsers();
  }

  // ---------------- flow
  function chip() {
    var old = document.getElementById('jw-chip'); if (old) old.remove();
    var kids = [el('span', { class: 'jw-pill static', text: auth.email })];
    if (auth.role === 'admin') kids.push(el('button', { class: 'jw-pill', text: '⚙ Admin Panel', onclick: adminPanel }));
    kids.push(el('button', { class: 'jw-pill', text: 'Sign Out', onclick: signOut }));
    var c = el('div', { class: 'jw-chip', id: 'jw-chip' }, kids); document.body.appendChild(c);
  }
  function signOut() {
    try { sessionStorage.removeItem(SESSION_KEY); } catch (e) {}
    if (started) location.reload(); else { auth = null; var c = document.getElementById('jw-chip'); if (c) c.remove(); loginScreen(); }
  }
  function startApp() {
    if (started) return; started = true;
    var s = document.createElement('script'); s.textContent = document.getElementById('jawa-app').textContent;
    document.body.appendChild(s);
  }
  function setAuth(email, name, role) {
    auth = { email: email, name: name, role: role };
    if (role === 'admin' || role === 'full' || role === 'viewer') {
      try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(auth)); } catch (e) {}
      clear(); document.body.classList.remove('jw-locked'); startApp(); chip();
    } else {
      try { sessionStorage.removeItem(SESSION_KEY); } catch (e) {}
      if (role === 'pending') pendingScreen(email);
      else if (role === 'restricted') restricted();
      else if (role === 'none') requestScreen(email);
      else loginScreen('Unexpected response from the access service.');
    }
  }

  var cached = null;
  try { cached = JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null'); } catch (e) {}
  if (cached && cached.email) {
    show(el('div', { class: 'jw-ov' }, el('div', { style: 'color:#f1e3c8;font-size:13px', text: 'Checking access…' })));
    fetchRole(cached.email).then(function (r) { setAuth(cached.email, cached.name || '', r.role); }).catch(function () { loginScreen(); });
  } else loginScreen();
})();
