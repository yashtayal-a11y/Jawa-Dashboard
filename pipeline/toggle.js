/* Old / New dashboard switch. "Old" is this page; "New" is new.html (TVS-style lead-disposition dashboards) in a frame.
   The switch only appears when new.html is actually published next to this page. */
(function () {
  'use strict';
  var KEY = 'jawa_view', frame = null;
  var css = '.jw-vt{position:fixed;bottom:8px;left:50%;transform:translateX(-50%);z-index:9500;display:none;align-items:center;gap:2px;' +
    'background:rgba(20,20,22,.92);border:1px solid #5a4528;border-radius:22px;padding:3px;font-family:Inter,system-ui,sans-serif}' +
    '.jw-vt span{color:#a99771;font-size:10px;font-weight:700;padding:0 8px 0 10px;letter-spacing:.06em;text-transform:uppercase}' +
    '.jw-vt button{background:transparent;color:#f1e3c8;border:none;border-radius:18px;padding:5px 16px;font-size:12px;font-weight:700;cursor:pointer;font-family:inherit}' +
    '.jw-vt button.on{background:#b8741a;color:#fff}' +
    '.jw-nf{position:fixed;inset:0;z-index:8500;border:0;width:100%;height:100%;background:#f8fafc;display:none}';
  var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  var bar = document.createElement('div'); bar.className = 'jw-vt';
  var lab = document.createElement('span'); lab.textContent = 'Dashboards';
  var bOld = document.createElement('button'); bOld.textContent = 'Old';
  var bNew = document.createElement('button'); bNew.textContent = 'New';
  bar.appendChild(lab); bar.appendChild(bOld); bar.appendChild(bNew); document.body.appendChild(bar);

  function show(which) {
    try { sessionStorage.setItem(KEY, which); } catch (e) {}
    bOld.className = which === 'old' ? 'on' : ''; bNew.className = which === 'new' ? 'on' : '';
    if (which === 'new') {
      if (!frame) { frame = document.createElement('iframe'); frame.className = 'jw-nf'; frame.src = 'new.html?r=' + Date.now(); document.body.appendChild(frame); }
      frame.style.display = 'block'; document.body.style.overflow = 'hidden';
    } else {
      if (frame) frame.style.display = 'none'; document.body.style.overflow = '';
    }
  }
  bOld.onclick = function () { show('old'); }; bNew.onclick = function () { show('new'); };

  window.addEventListener('message', function (e) {
    if (e.data && e.data.jawa === 'signout') {
      var b = [].slice.call(document.querySelectorAll('.jw-pill')).filter(function (x) { return x.textContent === 'Sign Out'; })[0];
      if (b) b.click();
    }
  });

  function sync() {   // stay hidden behind the sign-in screen
    var locked = document.body.classList.contains('jw-locked');
    if (bar.dataset.ok === '1') bar.style.display = locked ? 'none' : 'flex';
    if (frame && locked) frame.style.display = 'none';
  }
  setInterval(sync, 700);

  fetch('new.html', { method: 'HEAD', cache: 'no-store' }).then(function (r) {
    if (!r.ok) return;
    bar.dataset.ok = '1'; sync();
    var want = null; try { want = sessionStorage.getItem(KEY); } catch (e) {}
    show(want === 'new' ? 'new' : 'old');
  }).catch(function () {});
})();
