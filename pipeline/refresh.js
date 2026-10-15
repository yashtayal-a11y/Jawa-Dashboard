/* Manual refresh controls. BUILD_ID is stamped in at build time.
   - "Reload latest": fetches the newest published page (no cache). Also flags itself when a newer build is published.
   - "Run data refresh": opens the GitHub Actions workflow so an admin can click "Run workflow" (rebuilds from Drive, ~3 min). */
(function () {
  'use strict';
  var BUILD_ID = '__BUILD_ID__', BUILT = '__BUILT__', RUN_URL = '__RUN_URL__', AUTH_ON = __AUTH_ON__;
  var css = '.jw-rf{position:fixed;bottom:8px;left:8px;z-index:9000;display:flex;gap:6px;align-items:center;font-family:Inter,system-ui,sans-serif}' +
    '.jw-rf button,.jw-rf a{background:rgba(20,20,22,.88);color:#f1e3c8;border:1px solid #5a4528;border-radius:20px;padding:4px 10px;font-size:11px;font-weight:600;cursor:pointer;font-family:inherit;text-decoration:none}' +
    '.jw-rf button:hover,.jw-rf a:hover{background:#3a2a14}.jw-rf .new{background:#b8741a;color:#fff;border-color:#e0a458}' +
    '.jw-rf span{font-size:10px;color:#f1e3c8;background:rgba(20,20,22,.7);border-radius:12px;padding:3px 8px}';
  var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  var box = document.createElement('div'); box.className = 'jw-rf'; box.style.display = 'none';
  var info = document.createElement('span'); info.textContent = 'Built ' + BUILT;
  var reload = document.createElement('button'); reload.textContent = '↻ Reload latest data';
  reload.onclick = function () {
    try { sessionStorage.setItem('jawa_reload', '1'); } catch (e) {}
    var u = new URL(location.href); u.searchParams.set('r', Date.now()); location.replace(u.toString());
  };
  box.appendChild(info); box.appendChild(reload);

  function isAdmin() {
    if (!AUTH_ON) return true;                       // behind an outer login: GitHub itself decides who can run it
    try { var a = JSON.parse(sessionStorage.getItem('jawa_amj_auth') || 'null'); return !!a && a.role === 'admin'; } catch (e) { return false; }
  }
  var run = document.createElement('a'); run.textContent = '⚙ Run data refresh'; run.href = RUN_URL; run.target = '_blank'; run.rel = 'noopener';
  run.title = 'Opens GitHub Actions: click "Run workflow". The site updates in about 3-4 minutes, then use "Reload latest data".';
  document.body.appendChild(box);

  function sync() {
    box.style.display = document.body.classList.contains('jw-locked') ? 'none' : 'flex';
    if (isAdmin() && !run.parentNode) box.appendChild(run);
  }
  setInterval(sync, 1000); sync();

  function check() {
    fetch('version.json?t=' + Date.now(), { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (v) {
      if (v && v.id && v.id !== BUILD_ID) { reload.textContent = '● New data available, click to reload'; reload.className = 'new'; info.textContent = 'Built ' + BUILT + ' (newer: ' + v.built + ')'; }
    }).catch(function () {});
  }
  setInterval(check, 5 * 60 * 1000); setTimeout(check, 15000);
})();
