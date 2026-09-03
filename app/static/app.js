/* ==========================================================
   Green Fay Contract Farming Platform — Phase 2 Frontend
   Vanilla JS SPA — readable, modular
   ========================================================== */

// ==================== GLOBALS ====================
let me = null;
let masterCache = { farmers: [], bookings: [], varieties: [], destinations: [], seasons: [], suppliers: [], bardanaTypes: [], transporters: [] };

const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];
const content = () => document.getElementById('content');
const today = () => new Date().toISOString().slice(0, 10);

// ==================== API HELPER ====================
async function api(url, opt = {}) {
  const r = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(opt.headers || {}) },
    ...opt
  });
  if (r.status === 401) { showLogin(); throw new Error('Unauthorized'); }
  if (!r.ok) {
    let detail = 'Request failed';
    try { detail = (await r.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  const ct = r.headers.get('content-type') || '';
  if (ct.includes('json')) return r.json();
  return r;
}

// ==================== FORMATTING ====================
function money(n) { return '₹' + Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 }); }
function num(n) { return Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 }); }
function pct(n) { return (n || 0).toFixed(1) + '%'; }
function fmtDate(d) { if (!d) return '—'; const dt = new Date(d); return dt.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); }
function statusTag(s) {
  const map = {
    'Active': 'green', 'Completed': 'green', 'Finalized': 'green',
    'In Progress': 'warn', 'Partial': 'warn', 'Draft': 'warn',
    'Not Started': 'grey', 'Not Paid': 'grey',
    'Cancelled': 'red', 'Excess Supplied': 'red', 'Excess': 'red',
    'Inactive': 'grey'
  };
  const cls = map[s] || 'grey';
  return `<span class="tag ${cls}">${s}</span>`;
}

// ==================== TOAST ====================
function toast(msg, type = 'success') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${type === 'success' ? '✓' : type === 'error' ? '✗' : '!'}</span> ${msg}`;
  document.getElementById('toastContainer').appendChild(el);
  setTimeout(() => { el.style.animation = 'slideOut 0.3s ease forwards'; setTimeout(() => el.remove(), 300); }, 3200);
}

// ==================== MODAL ====================
function modal(html, wide = false) {
  const el = document.createElement('div');
  el.className = 'modal';
  el.innerHTML = `<div class="modal-card${wide ? ' wide' : ''}">${html}</div>`;
  el.addEventListener('click', e => { if (e.target === el) el.remove(); });
  document.body.appendChild(el);
  return el;
}
function closeModal(btn) { btn.closest('.modal').remove(); }

// ==================== AUTH ====================
function showLogin() { document.getElementById('login').classList.remove('hidden'); document.getElementById('app').classList.add('hidden'); }
function showApp() { document.getElementById('login').classList.add('hidden'); document.getElementById('app').classList.remove('hidden'); }

document.getElementById('loginForm').onsubmit = async e => {
  e.preventDefault();
  const err = document.getElementById('loginError');
  err.textContent = '';
  try {
    const x = await api('/api/login', { method: 'POST', body: JSON.stringify({ email: document.getElementById('email').value, password: document.getElementById('password').value }) });
    me = x.user;
    showApp();
    document.getElementById('userName').textContent = me.name;
    await loadMasterCache();
    page('dashboard');
  } catch (ex) { err.textContent = ex.message; }
};

document.getElementById('logoutBtn').onclick = async () => {
  await api('/api/logout', { method: 'POST' });
  showLogin();
};

document.getElementById('nav').onclick = e => { if (e.target.dataset.page) page(e.target.dataset.page); };

async function init() {
  try {
    me = await api('/api/me');
    showApp();
    document.getElementById('userName').textContent = me.name;
    await loadMasterCache();
    page('dashboard');
  } catch { showLogin(); }
}
init();

// ==================== MASTER CACHE ====================
async function loadMasterCache() {
  try {
    const [varieties, destinations, seasons, suppliers, bardanaTypes, transporters] = await Promise.all([
      api('/api/masters/varieties'),
      api('/api/masters/destinations'),
      api('/api/masters/seasons'),
      api('/api/masters/suppliers'),
      api('/api/masters/bardana-types'),
      api('/api/masters/transporters')
    ]);
    masterCache.varieties = varieties;
    masterCache.destinations = destinations;
    masterCache.seasons = seasons;
    masterCache.suppliers = suppliers;
    masterCache.bardanaTypes = bardanaTypes;
    masterCache.transporters = transporters;
  } catch (_) {}
}

async function loadFarmers() {
  const data = await api('/api/farmers');
  masterCache.farmers = data.items || data;
  return masterCache.farmers;
}

async function loadBookings() {
  masterCache.bookings = await api('/api/bookings');
  return masterCache.bookings;
}

// ==================== NAVIGATION ====================
function setNav(name, title) {
  document.querySelectorAll('nav button').forEach(b => b.classList.toggle('active', b.dataset.page === name));
  document.getElementById('pageTitle').textContent = title;
}

const PAGES = {
  dashboard: ['Dashboard', dashboardPage],
  farmers: ['Farmers', farmersPage],
  bookings: ['Bookings', bookingsPage],
  contracts: ['Contract Due', contractsPage],
  seed: ['Seed & Payments', seedPage],
  bardana: ['Bardana', bardanaPage],
  dispatch: ['Procurement / Dispatch', dispatchPage],
  masters: ['Master Data', mastersPage],
  tax: ['Mandi Tax & Vikas Sulk', taxPage],
  reports: ['Reports & Exports', reportsPage],
  audit: ['Audit Trail', auditPage]
};

async function page(name) {
  if (!PAGES[name]) return;
  const [title, fn] = PAGES[name];
  setNav(name, title);
  content().innerHTML = '<div class="loading">Loading</div>';
  try { await fn(); } catch (ex) {
    content().innerHTML = `<div class="panel"><p class="error">Error loading page: ${ex.message}</p></div>`;
    console.error(ex);
  }
}

// ==================== DASHBOARD ====================
async function dashboardPage() {
  const d = await api('/api/dashboard');
  const cards = [
    ['Farmers', d.total_farmers, '👨‍🌾'],
    ['Total Acres', num(d.acres), '🌾'],
    ['Contract Bags', num(d.contracted_bags), '📦'],
    ['Pending Bags', num(d.pending_bags), '⏳'],
    ['With Seed Acres', num(d.with_seed_acres), '🌱'],
    ['Without Seed Acres', num(d.without_seed_acres), '🚜'],
    ['Seed Outstanding', money(d.seed_outstanding), '💰'],
    ['Bardana Issued', num(d.bardana_issued), '🛍'],
    ['Mandi Tax', money(d.mandi_tax), '🧾'],
    ['Vikas Sulk', money(d.vikas_sulk), '🧾']
  ];
  const pct_delivered = d.contracted_bags > 0 ? Math.min(100, d.delivered_bags / d.contracted_bags * 100) : 0;
  content().innerHTML = `
    <div class="grid cards">${cards.map(([label, val, icon]) => `
      <div class="card">
        <small>${icon} ${label}</small>
        <strong>${val}</strong>
      </div>`).join('')}
    </div>
    <div class="panel">
      <div class="panel-head"><div><h3>Procurement Progress</h3><p>Overall contracted vs. delivered (Finalized dispatches)</p></div></div>
      <div class="metric-line"><span>Delivered</span><div class="progress"><span style="width:${pct_delivered}%"></span></div><b>${num(d.delivered_bags)}</b></div>
      <div class="metric-line"><span>Pending</span><div class="progress"><span style="width:${100 - pct_delivered}%;background:#e8c070"></span></div><b>${num(d.pending_bags)}</b></div>
    </div>`;
}

// ==================== FARMERS ====================
let farmerPage = 1, farmerQ = '', farmerTotal = 0;

async function farmersPage() {
  await loadFarmers();
  renderFarmersPage();
}

function renderFarmersPage() {
  content().innerHTML = `
    <div class="panel">
      <div class="panel-head">
        <div><h3>Farmer Master</h3><p>Create and manage farmer profiles</p></div>
        <button class="btn green" onclick="openFarmerModal()">+ Add Farmer</button>
      </div>
      <div class="toolbar">
        <input id="farmerQ" placeholder="Search name, village, mobile, code..." value="${farmerQ}" style="flex:1;min-width:200px">
        <button class="btn" onclick="searchFarmers()">Search</button>
        <select id="farmerActiveFilter" onchange="searchFarmers()">
          <option value="">All Status</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Farmer ID</th><th>Name</th><th>Father/Relation</th><th>Village</th><th>Mobile</th><th>Status</th><th></th>
          </tr></thead>
          <tbody id="farmersTbody">${renderFarmerRows()}</tbody>
        </table>
      </div>
      <div class="pagination" id="farmerPagination">${renderPagination(farmerTotal, farmerPage, 50, 'goFarmerPage')}</div>
    </div>`;
  document.getElementById('farmerQ').onkeydown = e => { if (e.key === 'Enter') searchFarmers(); };
}

function renderFarmerRows() {
  if (!masterCache.farmers.length) return '<tr><td colspan="7"><div class="empty-state"><div class="empty-icon">👨‍🌾</div><p>No farmers found</p></div></td></tr>';
  return masterCache.farmers.map(f => `
    <tr>
      <td><span class="tag-text">${f.farmer_code || '—'}</span></td>
      <td><b>${f.name}</b></td>
      <td>${f.relation_name || '—'}</td>
      <td>${f.village || '—'}</td>
      <td>${f.mobile || '—'}</td>
      <td>${statusTag(f.active ? 'Active' : 'Inactive')}</td>
      <td class="actions">
        <button class="btn sm" onclick="openFarmer360(${f.id})">360°</button>
        <button class="btn sm" onclick="openEditFarmerModal(${f.id})">Edit</button>
      </td>
    </tr>`).join('');
}

async function searchFarmers() {
  farmerQ = document.getElementById('farmerQ')?.value || '';
  const active = document.getElementById('farmerActiveFilter')?.value;
  let url = `/api/farmers?q=${encodeURIComponent(farmerQ)}&page=${farmerPage}&per_page=50`;
  if (active) url += `&active=${active}`;
  const data = await api(url);
  masterCache.farmers = data.items || data;
  farmerTotal = data.total || masterCache.farmers.length;
  const tbody = document.getElementById('farmersTbody');
  if (tbody) tbody.innerHTML = renderFarmerRows();
  const pg = document.getElementById('farmerPagination');
  if (pg) pg.innerHTML = renderPagination(farmerTotal, farmerPage, 50, 'goFarmerPage');
}

window.goFarmerPage = p => { farmerPage = p; searchFarmers(); };

function renderPagination(total, page, perPage, fnName) {
  const pages = Math.ceil(total / perPage);
  if (pages <= 1) return `<span>Total: ${total}</span>`;
  let html = `<span>Total: ${total}</span>`;
  if (page > 1) html += `<button class="btn sm" onclick="${fnName}(${page - 1})">← Prev</button>`;
  html += `<span>Page ${page} of ${pages}</span>`;
  if (page < pages) html += `<button class="btn sm" onclick="${fnName}(${page + 1})">Next →</button>`;
  return html;
}

function openFarmerModal(prefill = {}) {
  const villageOpts = masterCache.varieties.length ? '' : '';
  const m = modal(`
    <div class="modal-head"><h3>Add Farmer</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <div id="dupWarn"></div>
    <form class="form" id="farmerForm">
      <div><label>Name *</label><input name="name" required value="${prefill.name || ''}"></div>
      <div><label>Father/Relation Name</label><input name="relation_name" value="${prefill.relation_name || ''}"></div>
      <div><label>Relation Type</label><select name="relation_type">
        <option ${prefill.relation_type === 'Father' ? 'selected' : ''}>Father</option>
        <option ${prefill.relation_type === 'Husband' ? 'selected' : ''}>Husband</option>
        <option ${prefill.relation_type === 'Son' ? 'selected' : ''}>Son</option>
        <option ${prefill.relation_type === 'Other' ? 'selected' : ''}>Other</option>
      </select></div>
      <div><label>Mobile (10 digits)</label><input name="mobile" maxlength="10" pattern="[0-9]{10}" value="${prefill.mobile || ''}"></div>
      <div><label>Alternate Mobile</label><input name="alternate_mobile" value="${prefill.alternate_mobile || ''}"></div>
      <div><label>Village</label><input name="village" value="${prefill.village || ''}"></div>
      <div><label>District</label><input name="district" value="${prefill.district || ''}"></div>
      <div><label>State</label><input name="state" value="${prefill.state || 'Punjab'}"></div>
      <div class="full"><label>Address</label><textarea name="address">${prefill.address || ''}</textarea></div>
      <div class="full"><label>Remarks</label><textarea name="remarks">${prefill.remarks || ''}</textarea></div>
      <div class="full"><button class="primary" type="submit">Create Farmer</button></div>
    </form>`);
  document.getElementById('farmerForm').onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    if (data.mobile && !/^[0-9]{10}$/.test(data.mobile)) { toast('Mobile must be exactly 10 digits', 'error'); return; }
    try {
      const res = await api('/api/farmers', { method: 'POST', body: JSON.stringify(data) });
      if (res.duplicate_warning && res.duplicate_warning.length > 0 && !data.force) {
        document.getElementById('dupWarn').innerHTML = `<div class="warning-box">⚠️ Possible duplicates found:<br>${res.duplicate_warning.map(d => `${d.name} · ${d.village} · ${d.mobile}`).join('<br>')}<br><button class="btn" onclick="forceSaveFarmer(${JSON.stringify(data).replace(/"/g, '&quot;')})">Save Anyway</button></div>`;
        return;
      }
      toast(`Farmer created: ${res.farmer_code}`);
      closeModal(e.target);
      await searchFarmers();
    } catch (ex) { toast(ex.message, 'error'); }
  };
}

window.forceSaveFarmer = async data => {
  data.force = true;
  const res = await api('/api/farmers', { method: 'POST', body: JSON.stringify(data) });
  toast(`Farmer created: ${res.farmer_code}`);
  document.querySelector('.modal')?.remove();
  await searchFarmers();
};

async function openEditFarmerModal(id) {
  const f = await api(`/api/farmers/${id}`);
  const m = modal(`
    <div class="modal-head"><h3>Edit Farmer — ${f.farmer_code}</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <form class="form" id="editFarmerForm">
      <div><label>Name *</label><input name="name" required value="${f.name}"></div>
      <div><label>Father/Relation Name</label><input name="relation_name" value="${f.relation_name || ''}"></div>
      <div><label>Relation Type</label><select name="relation_type">
        ${['Father','Husband','Son','Other'].map(t => `<option ${f.relation_type===t?'selected':''}>${t}</option>`).join('')}
      </select></div>
      <div><label>Mobile</label><input name="mobile" value="${f.mobile || ''}"></div>
      <div><label>Alternate Mobile</label><input name="alternate_mobile" value="${f.alternate_mobile || ''}"></div>
      <div><label>Village</label><input name="village" value="${f.village || ''}"></div>
      <div><label>District</label><input name="district" value="${f.district || ''}"></div>
      <div><label>State</label><input name="state" value="${f.state || 'Punjab'}"></div>
      <div class="full"><label>Address</label><textarea name="address">${f.address || ''}</textarea></div>
      <div class="full"><label>Remarks</label><textarea name="remarks">${f.remarks || ''}</textarea></div>
      <div><label>Status</label><select name="active">
        <option value="true" ${f.active?'selected':''}>Active</option>
        <option value="false" ${!f.active?'selected':''}>Inactive</option>
      </select></div>
      <div class="full"><button class="primary" type="submit">Save Changes</button></div>
    </form>`);
  document.getElementById('editFarmerForm').onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.active = data.active === 'true';
    try {
      await api(`/api/farmers/${id}`, { method: 'PUT', body: JSON.stringify(data) });
      toast('Farmer updated');
      closeModal(e.target);
      await searchFarmers();
    } catch (ex) { toast(ex.message, 'error'); }
  };
}

async function openFarmer360(id) {
  const [f, summary] = await Promise.all([api(`/api/farmers/${id}`), api(`/api/farmers/${id}/summary`)]);
  const tabs = ['Bookings', 'Commitments', 'Seed Issues', 'Payments', 'Bardana', 'Dispatches', 'Audit'];
  const m = modal(`
    <div class="modal-head">
      <div class="farmer-header" style="margin:0;border:none;padding:0;background:none">
        <div class="farmer-avatar">${f.name[0]}</div>
        <div class="farmer-info">
          <h2 style="font-size:18px">${f.name}</h2>
          <p>${f.relation_name || ''} &bull; ${f.village || ''} &bull; ${f.mobile || ''}</p>
          <p><span class="tag-text">${f.farmer_code}</span></p>
        </div>
      </div>
      <button class="close-btn" onclick="closeModal(this)">×</button>
    </div>
    <div class="summary-cards" style="grid-template-columns:repeat(5,1fr);margin:14px 0">
      <div class="summary-card"><small>Bookings</small><strong>${summary.total_bookings}</strong></div>
      <div class="summary-card"><small>Acres</small><strong>${num(summary.total_acres)}</strong></div>
      <div class="summary-card"><small>Seed Value</small><strong>${money(summary.seed_value)}</strong></div>
      <div class="summary-card"><small>Seed Paid</small><strong>${money(summary.seed_paid)}</strong></div>
      <div class="summary-card"><small>Seed Balance</small><strong>${money(summary.seed_balance)}</strong></div>
      <div class="summary-card"><small>Bardana Issued</small><strong>${num(summary.bardana_issued)}</strong></div>
      <div class="summary-card"><small>Contract Bags</small><strong>${num(summary.contract_bags)}</strong></div>
      <div class="summary-card"><small>Received</small><strong>${num(summary.potato_received)}</strong></div>
      <div class="summary-card"><small>Pending</small><strong>${num(summary.contract_pending)}</strong></div>
      <div class="summary-card"><small>Status</small><strong style="font-size:14px">${statusTag(summary.payment_status)}</strong></div>
    </div>
    <div class="tabs">${tabs.map((t, i) => `<button class="tab-btn${i===0?' active':''}" onclick="switch360Tab(this,'tab360-${i}')">${t}</button>`).join('')}</div>
    ${tabs.map((_, i) => `<div class="tab-content${i===0?' active':''}" id="tab360-${i}"><div class="loading">Loading</div></div>`).join('')}`, true);

  // Load each tab
  load360Tab(id, 0, 'bookings');
  load360Tab(id, 1, 'commitments');
  load360Tab(id, 2, 'seed');
  load360Tab(id, 3, 'payments');
  load360Tab(id, 4, 'bardana');
  load360Tab(id, 5, 'dispatches');
  load360Tab(id, 6, 'audit');
}

window.switch360Tab = (btn, tabId) => {
  btn.closest('.modal-card').querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  btn.closest('.modal-card').querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.getElementById(tabId)?.classList.add('active');
};

async function load360Tab(farmerId, idx, section) {
  const el = document.getElementById(`tab360-${idx}`);
  if (!el) return;
  try {
    if (section === 'bookings') {
      const data = await api(`/api/bookings?farmer_id=${farmerId}`);
      el.innerHTML = data.length ? `<table><thead><tr><th>Booking</th><th>Season</th><th>Type</th><th>Acres</th><th>Status</th></tr></thead><tbody>
        ${data.map(b => `<tr><td>${b.booking_code}</td><td>${b.season}</td><td>${b.booking_type}</td><td>${num(b.total_acres)}</td><td>${statusTag(b.status)}</td></tr>`).join('')}
      </tbody></table>` : '<div class="empty-state"><p>No bookings</p></div>';
    } else if (section === 'commitments') {
      const data = await api(`/api/contracts/due?farmer_id=${farmerId}`);
      el.innerHTML = data.length ? `<table><thead><tr><th>Month</th><th>Variety</th><th>Contracted</th><th>Received</th><th>Pending</th><th>Status</th></tr></thead><tbody>
        ${data.map(c => `<tr><td>${c.contract_month} ${c.contract_year}</td><td>${c.variety||'—'}</td><td class="num">${num(c.contracted_bags)}</td><td class="num">${num(c.received_bags)}</td><td class="num">${num(c.pending_bags)}</td><td>${statusTag(c.status)}</td></tr>`).join('')}
      </tbody></table>` : '<div class="empty-state"><p>No commitments</p></div>';
    } else if (section === 'seed') {
      const data = await api(`/api/seed/issues?farmer_id=${farmerId}`);
      el.innerHTML = data.length ? `<table><thead><tr><th>Date</th><th>Variety</th><th>Packets</th><th>Rate</th><th>Value</th><th>Status</th></tr></thead><tbody>
        ${data.map(s => `<tr><td>${fmtDate(s.issue_date)}</td><td>${s.variety}</td><td>${num(s.packets)}</td><td>${money(s.rate)}</td><td>${money(s.total_value)}</td><td>${statusTag(s.status)}</td></tr>`).join('')}
      </tbody></table>` : '<div class="empty-state"><p>No seed issues</p></div>';
    } else if (section === 'payments') {
      const data = await api(`/api/seed/payments?farmer_id=${farmerId}`);
      el.innerHTML = data.length ? `<table><thead><tr><th>Date</th><th>Amount</th><th>Mode</th><th>Reference</th><th>Status</th></tr></thead><tbody>
        ${data.map(p => `<tr><td>${fmtDate(p.payment_date)}</td><td class="num">${money(p.amount)}</td><td>${p.mode||'—'}</td><td>${p.reference_no||'—'}</td><td>${statusTag(p.status)}</td></tr>`).join('')}
      </tbody></table>` : '<div class="empty-state"><p>No payments</p></div>';
    } else if (section === 'bardana') {
      const data = await api(`/api/bardana?farmer_id=${farmerId}`);
      el.innerHTML = data.length ? `<table><thead><tr><th>Date</th><th>Month</th><th>Bags</th><th>Challan</th><th>Status</th></tr></thead><tbody>
        ${data.map(b => `<tr><td>${fmtDate(b.issue_date)}</td><td>${b.contract_month||'—'}</td><td class="num">${num(b.bags_issued)}</td><td>${b.challan_ref||'—'}</td><td>${statusTag(b.status)}</td></tr>`).join('')}
      </tbody></table>` : '<div class="empty-state"><p>No bardana issues</p></div>';
    } else if (section === 'dispatches') {
      const data = await api(`/api/dispatches?farmer_id=${farmerId}`);
      el.innerHTML = data.length ? `<table><thead><tr><th>Dispatch</th><th>Date</th><th>Truck</th><th>Variety</th><th>Bags</th><th>Status</th></tr></thead><tbody>
        ${data.map(d => `<tr><td>${d.dispatch_code||d.id}</td><td>${fmtDate(d.date)}</td><td>${d.truck_no||'—'}</td><td>${d.variety||'—'}</td><td class="num">${num(d.bags)}</td><td>${statusTag(d.status)}</td></tr>`).join('')}
      </tbody></table>` : '<div class="empty-state"><p>No dispatches</p></div>';
    } else if (section === 'audit') {
      const data = await api(`/api/farmers/${farmerId}/audit`);
      el.innerHTML = data.length ? `<table><thead><tr><th>Time</th><th>Action</th><th>Details</th></tr></thead><tbody>
        ${data.map(a => `<tr><td>${new Date(a.created_at).toLocaleString()}</td><td>${statusTag(a.action)}</td><td>${a.details||''}</td></tr>`).join('')}
      </tbody></table>` : '<div class="empty-state"><p>No audit records</p></div>';
    }
  } catch (ex) { el.innerHTML = `<p class="error">Error: ${ex.message}</p>`; }
}

// ==================== BOOKINGS ====================
async function bookingsPage() {
  await Promise.all([loadFarmers(), loadBookings()]);
  content().innerHTML = `
    <div class="panel">
      <div class="panel-head">
        <div><h3>Bookings</h3><p>Contract agreements with variety lines and monthly commitments</p></div>
        <button class="btn green" onclick="openBookingModal()">+ New Booking</button>
      </div>
      <div class="toolbar">
        <select id="bSeasonFilter" onchange="filterBookings()">
          <option value="">All Seasons</option>
          ${masterCache.seasons.map(s => `<option>${s.name}</option>`).join('')}
        </select>
        <select id="bFarmerFilter" onchange="filterBookings()">
          <option value="">All Farmers</option>
          ${masterCache.farmers.map(f => `<option value="${f.id}">${f.name}</option>`).join('')}
        </select>
        <select id="bStatusFilter" onchange="filterBookings()">
          <option value="">All Status</option>
          ${['Draft','Active','Completed','Cancelled'].map(s => `<option>${s}</option>`).join('')}
        </select>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Booking</th><th>Farmer</th><th>Season</th><th>Agreement</th><th>Type</th><th>Acres</th><th>Destination</th><th>Status</th><th></th></tr></thead>
          <tbody id="bookingsTbody">${renderBookingRows(masterCache.bookings)}</tbody>
        </table>
      </div>
    </div>`;
}

function renderBookingRows(bks) {
  if (!bks.length) return '<tr><td colspan="9"><div class="empty-state"><div class="empty-icon">📋</div><p>No bookings found</p></div></td></tr>';
  return bks.map(b => `
    <tr>
      <td><span class="tag-text">${b.booking_code}</span></td>
      <td><b>${b.farmer}</b></td>
      <td>${b.season}</td>
      <td>${b.agreement_no || '—'}</td>
      <td>${b.booking_type}</td>
      <td>${num(b.total_acres)}</td>
      <td>${b.destination || '—'}</td>
      <td>${statusTag(b.status)}</td>
      <td><button class="btn sm" onclick="openBookingDetail(${b.id})">View</button></td>
    </tr>`).join('');
}

async function filterBookings() {
  const season = document.getElementById('bSeasonFilter')?.value;
  const farmer = document.getElementById('bFarmerFilter')?.value;
  const status = document.getElementById('bStatusFilter')?.value;
  let url = '/api/bookings?';
  if (season) url += `season=${encodeURIComponent(season)}&`;
  if (farmer) url += `farmer_id=${farmer}&`;
  if (status) url += `status=${encodeURIComponent(status)}&`;
  const data = await api(url);
  const tbody = document.getElementById('bookingsTbody');
  if (tbody) tbody.innerHTML = renderBookingRows(data);
}

function openBookingModal() {
  const farmerOpts = masterCache.farmers.map(f => `<option value="${f.id}">${f.farmer_code} — ${f.name}</option>`).join('');
  const destOpts = masterCache.destinations.map(d => `<option>${d.name}</option>`).join('');
  const seasonOpts = masterCache.seasons.map(s => `<option value="${s.name}" ${s.active ? 'selected' : ''}>${s.name}</option>`).join('');
  const varOpts = masterCache.varieties.map(v => `<option value="${v.name}">${v.name}</option>`).join('');
  const m = modal(`
    <div class="modal-head"><h3>Create Booking</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <div id="bookingWarn"></div>
    <form id="bookingForm">
      <div class="form">
        <div><label>Farmer *</label><select name="farmer_id" required>${farmerOpts}</select></div>
        <div><label>Season *</label><select name="season">${seasonOpts}</select></div>
        <div><label>Booking Date</label><input type="date" name="booking_date" value="${today()}"></div>
        <div><label>Agreement No.</label><input name="agreement_no" placeholder="GF-2025-001"></div>
        <div><label>Receipt / Slip No.</label><input name="receipt_no"></div>
        <div><label>Booking Type</label><select name="booking_type">
          <option>Mixed</option><option>With Seed</option><option>Without Seed</option>
        </select></div>
        <div><label>Default Destination</label><select name="destination">${destOpts}</select></div>
        <div><label>Company/Program</label><input name="company_program" value="Green Fay Farm Foods"></div>
        <div class="full"><label>Remarks</label><textarea name="remarks"></textarea></div>
      </div>
      <hr class="section">
      <h4 style="margin:0 0 10px">Variety Lines</h4>
      <div id="varietyRows" class="variety-rows"></div>
      <button type="button" class="add-row-btn" onclick="addVarietyRow()">+ Add Variety</button>
      <hr class="section">
      <h4 style="margin:0 0 10px">Monthly Commitments</h4>
      <div id="commitmentRows" class="commitment-rows"></div>
      <button type="button" class="add-row-btn" onclick="addCommitmentRow()">+ Add Commitment</button>
      <button class="primary" type="submit">Create Booking</button>
    </form>`, true);

  addVarietyRow();
  addCommitmentRow();

  document.getElementById('bookingForm').onsubmit = async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const base = Object.fromEntries(fd);
    const varieties = collectVarietyRows();
    const commitments = collectCommitmentRows();
    if (!varieties.length) { toast('Add at least one variety', 'error'); return; }
    const body = { ...base, varieties, commitments, total_acres: varieties.reduce((s, v) => s + parseFloat(v.acres || 0), 0) };
    try {
      const res = await api('/api/bookings', { method: 'POST', body: JSON.stringify(body) });
      if (res.warning) document.getElementById('bookingWarn').innerHTML = `<div class="warning-box">⚠️ ${res.warning}</div>`;
      toast(`Booking created: ${res.booking_code}`);
      closeModal(e.target);
      await loadBookings();
      await bookingsPage();
    } catch (ex) { toast(ex.message, 'error'); }
  };
}

let varietyRowCount = 0;
function addVarietyRow() {
  const idx = varietyRowCount++;
  const varOpts = masterCache.varieties.map(v => `<option value="${v.name}">${v.name}</option>`).join('');
  const row = document.createElement('div');
  row.className = 'variety-row';
  row.id = `vrow-${idx}`;
  row.innerHTML = `
    <div><label>Variety *</label><select name="variety_${idx}" required>${varOpts}</select></div>
    <div><label>Acres *</label><input name="acres_${idx}" type="number" step="0.01" min="0.01" required></div>
    <div><label>Seed Mode</label><select name="seed_type_${idx}">
      <option>With Seed</option><option>Without Seed</option>
    </select></div>
    <div><label>Planned Packets</label><input name="packets_${idx}" type="number" min="0" value="0"></div>
    <div><label>Expected Buyback</label><input name="buyback_${idx}" type="number" min="0" value="0"></div>
    <button type="button" class="row-remove" onclick="this.closest('.variety-row').remove()" title="Remove">×</button>`;
  document.getElementById('varietyRows').appendChild(row);
}

function collectVarietyRows() {
  const rows = document.querySelectorAll('.variety-row');
  return Array.from(rows).map((row, i) => {
    const idx = row.id.replace('vrow-', '');
    return {
      variety: row.querySelector(`[name="variety_${idx}"]`)?.value,
      acres: row.querySelector(`[name="acres_${idx}"]`)?.value,
      seed_type: row.querySelector(`[name="seed_type_${idx}"]`)?.value,
      planned_seed_packets: row.querySelector(`[name="packets_${idx}"]`)?.value || 0,
      expected_buyback_qty: row.querySelector(`[name="buyback_${idx}"]`)?.value || 0,
    };
  }).filter(r => r.variety);
}

let commitmentRowCount = 0;
function addCommitmentRow() {
  const idx = commitmentRowCount++;
  const vOpts = masterCache.varieties.map(v => `<option value="${v.name}">${v.name}</option>`).join('');
  const destOpts = ['', ...masterCache.destinations.map(d => d.name)].map(d => `<option>${d}</option>`).join('');
  const row = document.createElement('div');
  row.className = 'commitment-row';
  row.id = `crow-${idx}`;
  row.innerHTML = `
    <div><label>Variety</label><select name="cvariety_${idx}">${vOpts}</select></div>
    <div><label>Month</label><select name="cmonth_${idx}">${MONTHS.map(m => `<option>${m}</option>`).join('')}</select></div>
    <div><label>Year</label><input name="cyear_${idx}" type="number" value="${new Date().getFullYear() + 1}" min="2020"></div>
    <div><label>Bags *</label><input name="cbags_${idx}" type="number" min="1" required></div>
    <div><label>Buyback Rate</label><input name="crate_${idx}" type="number" step="0.01" min="0" value="0"></div>
    <div><label>Destination</label><select name="cdest_${idx}">${destOpts}</select></div>
    <button type="button" class="row-remove" onclick="this.closest('.commitment-row').remove()" title="Remove">×</button>`;
  document.getElementById('commitmentRows').appendChild(row);
}

function collectCommitmentRows() {
  const rows = document.querySelectorAll('.commitment-row');
  const varieties = collectVarietyRows();
  return Array.from(rows).map(row => {
    const idx = row.id.replace('crow-', '');
    const cVariety = row.querySelector(`[name="cvariety_${idx}"]`)?.value;
    const vi = varieties.findIndex(v => v.variety === cVariety);
    return {
      variety_index: vi >= 0 ? vi : 0,
      contract_month: row.querySelector(`[name="cmonth_${idx}"]`)?.value,
      contract_year: parseInt(row.querySelector(`[name="cyear_${idx}"]`)?.value),
      contracted_bags: parseFloat(row.querySelector(`[name="cbags_${idx}"]`)?.value || 0),
      buyback_rate: parseFloat(row.querySelector(`[name="crate_${idx}"]`)?.value || 0),
      destination: row.querySelector(`[name="cdest_${idx}"]`)?.value,
    };
  }).filter(r => r.contracted_bags > 0);
}

async function openBookingDetail(id) {
  const b = await api(`/api/bookings/${id}`);
  const m = modal(`
    <div class="modal-head">
      <div>
        <div class="eyebrow">${b.booking_code}</div>
        <h3 style="margin:4px 0">${b.farmer?.name || ''}</h3>
        <p class="muted small">${b.season} · ${b.booking_type} · ${statusTag(b.status)}</p>
      </div>
      <button class="close-btn" onclick="closeModal(this)">×</button>
    </div>
    <div class="tabs">
      <button class="tab-btn active" onclick="switch360Tab(this,'bdtab-0')">Varieties</button>
      <button class="tab-btn" onclick="switch360Tab(this,'bdtab-1')">Commitments</button>
    </div>
    <div class="tab-content active" id="bdtab-0">
      <table><thead><tr><th>Variety</th><th>Acres</th><th>Seed Mode</th><th>Planned Packets</th><th>Expected Buyback</th></tr></thead>
      <tbody>${(b.varieties||[]).map(v => `<tr><td><b>${v.variety}</b></td><td>${num(v.acres)}</td><td>${v.seed_type}</td><td>${num(v.planned_seed_packets)}</td><td>${num(v.expected_buyback_qty)}</td></tr>`).join('')}</tbody>
      </table>
    </div>
    <div class="tab-content" id="bdtab-1">
      <table><thead><tr><th>Variety</th><th>Month</th><th>Contracted</th><th>Received</th><th>Pending</th><th>%</th><th>Status</th></tr></thead>
      <tbody>${(b.commitments||[]).map(c => `<tr>
        <td>${c.variety||'—'}</td><td>${c.contract_month} ${c.contract_year}</td>
        <td class="num">${num(c.contracted_bags)}</td><td class="num">${num(c.received_bags)}</td>
        <td class="num">${num(c.pending_bags)}</td><td>${pct(c.completion_pct)}</td><td>${statusTag(c.status)}</td>
      </tr>`).join('')}</tbody>
      </table>
    </div>
    <div style="margin-top:16px;display:flex;gap:8px">
      ${b.status !== 'Cancelled' ? `<button class="btn red" onclick="cancelBooking(${id},this)">Cancel Booking</button>` : ''}
    </div>`, true);
}

window.cancelBooking = async (id, btn) => {
  if (!confirm('Cancel this booking? This cannot be undone.')) return;
  try {
    await api(`/api/bookings/${id}/status`, { method: 'PUT', body: JSON.stringify({ status: 'Cancelled' }) });
    toast('Booking cancelled');
    closeModal(btn);
    await loadBookings();
    await bookingsPage();
  } catch (ex) { toast(ex.message, 'error'); }
};

// ==================== CONTRACTS DUE ====================
async function contractsPage() {
  const rows = await api('/api/contracts/due');
  content().innerHTML = `
    <div class="panel">
      <div class="panel-head"><div><h3>Contract Due / Procurement Dashboard</h3><p>Live commitment progress from finalized dispatches</p></div></div>
      <div class="toolbar">
        <select id="cdMonth" onchange="filterContracts()"><option value="">All Months</option>${MONTHS.map(m=>`<option>${m}</option>`).join('')}</select>
        <select id="cdVariety" onchange="filterContracts()"><option value="">All Varieties</option>${masterCache.varieties.map(v=>`<option>${v.name}</option>`).join('')}</select>
        <select id="cdStatus" onchange="filterContracts()">
          <option value="">All Status</option>
          ${['Not Started','In Progress','Completed','Excess Supplied','Cancelled'].map(s=>`<option>${s}</option>`).join('')}
        </select>
        <input id="cdFarmer" placeholder="Farmer name..." style="width:160px" oninput="filterContracts()">
        <select id="cdDest" onchange="filterContracts()"><option value="">All Destinations</option>${masterCache.destinations.map(d=>`<option>${d.name}</option>`).join('')}</select>
      </div>
      <div id="contractsTable" class="table-wrap">${renderContractsTable(rows)}</div>
    </div>`;
}

function renderContractsTable(rows) {
  if (!rows.length) return '<div class="empty-state"><div class="empty-icon">📦</div><p>No contract commitments found</p></div>';
  return `<table>
    <thead><tr><th>Farmer</th><th>Village</th><th>Booking</th><th>Variety</th><th>Month/Year</th><th>Destination</th>
    <th class="num">Contracted</th><th class="num">Received</th><th class="num">Pending</th><th>%</th><th>Status</th></tr></thead>
    <tbody>${rows.map(x => `<tr>
      <td><b>${x.farmer}</b></td>
      <td>${x.village||'—'}</td>
      <td><span class="tag-text">${x.booking}</span></td>
      <td>${x.variety||'—'}</td>
      <td>${x.contract_month} ${x.contract_year}</td>
      <td>${x.destination||'—'}</td>
      <td class="num">${num(x.contracted_bags)}</td>
      <td class="num">${num(x.received_bags)}</td>
      <td class="num">${num(x.pending_bags)}</td>
      <td><div class="progress" style="width:60px"><span style="width:${Math.min(100, x.completion_pct||0)}%"></span></div></td>
      <td>${statusTag(x.status)}</td>
    </tr>`).join('')}</tbody>
  </table>`;
}

async function filterContracts() {
  const month = document.getElementById('cdMonth')?.value;
  const variety = document.getElementById('cdVariety')?.value;
  const status = document.getElementById('cdStatus')?.value;
  const farmer = document.getElementById('cdFarmer')?.value;
  const dest = document.getElementById('cdDest')?.value;
  let url = '/api/contracts/due?';
  if (month) url += `month=${encodeURIComponent(month)}&`;
  if (variety) url += `variety=${encodeURIComponent(variety)}&`;
  if (status) url += `status=${encodeURIComponent(status)}&`;
  if (farmer) url += `farmer=${encodeURIComponent(farmer)}&`;
  if (dest) url += `destination=${encodeURIComponent(dest)}&`;
  const rows = await api(url);
  const el = document.getElementById('contractsTable');
  if (el) el.innerHTML = renderContractsTable(rows);
}

// ==================== SEED & PAYMENTS ====================
async function seedPage() {
  await Promise.all([loadFarmers(), loadBookings()]);
  const issues = await api('/api/seed/issues');
  content().innerHTML = `
    <div class="panel">
      <div class="panel-head">
        <div><h3>Seed Distribution & Payments</h3><p>Issue tracking, rate snapshots, and payment balances</p></div>
        <div class="actions">
          <button class="btn green" onclick="openSeedIssueModal()">+ Seed Issue</button>
          <button class="btn" onclick="openPaymentModal()">+ Payment</button>
        </div>
      </div>
      <div class="toolbar">
        <select id="seedFarmerFilter" onchange="filterSeed()"><option value="">All Farmers</option>
          ${masterCache.farmers.map(f=>`<option value="${f.id}">${f.name}</option>`).join('')}
        </select>
        <select id="seedStatusFilter" onchange="filterSeed()"><option value="">All Status</option>
          ${['Not Paid','Partial','Completed','Excess'].map(s=>`<option>${s}</option>`).join('')}
        </select>
      </div>
      <div class="table-wrap" id="seedTable">
        ${renderSeedTable(issues)}
      </div>
    </div>`;
}

function renderSeedTable(rows) {
  if (!rows.length) return '<div class="empty-state"><div class="empty-icon">🌱</div><p>No seed issues found</p></div>';
  return `<table>
    <thead><tr><th>Farmer</th><th>Variety</th><th>Date</th><th>Packets</th><th class="num">Rate</th>
    <th class="num">Value</th><th class="num">Paid</th><th class="num">Balance</th><th>Status</th><th></th></tr></thead>
    <tbody>${rows.map(x => `<tr>
      <td><b>${x.farmer}</b></td>
      <td>${x.variety}</td>
      <td>${fmtDate(x.issue_date)}</td>
      <td>${num(x.packets)}</td>
      <td class="num">${money(x.rate)}</td>
      <td class="num">${money(x.total_value)}</td>
      <td class="num">${money(x.paid)}</td>
      <td class="num"><b>${money(x.balance)}</b></td>
      <td>${statusTag(x.payment_status || (x.balance <= 0 && x.total_value > 0 ? 'Completed' : x.paid > 0 ? 'Partial' : 'Not Paid'))}</td>
      <td>${x.status === 'Active' ? `<button class="btn sm red" onclick="cancelSeedIssue(${x.id})">Cancel</button>` : statusTag('Cancelled')}</td>
    </tr>`).join('')}</tbody>
  </table>`;
}

async function filterSeed() {
  const farmer = document.getElementById('seedFarmerFilter')?.value;
  let url = '/api/seed/issues?';
  if (farmer) url += `farmer_id=${farmer}&`;
  const rows = await api(url);
  const el = document.getElementById('seedTable');
  if (el) el.innerHTML = renderSeedTable(rows);
}

function openSeedIssueModal() {
  const bookingOpts = masterCache.bookings.map(b => `<option value="${b.id}" data-farmer="${b.farmer_id}">${b.booking_code} — ${b.farmer}</option>`).join('');
  const varOpts = masterCache.varieties.map(v => `<option value="${v.name}">${v.name}</option>`).join('');
  const supplierOpts = masterCache.suppliers.map(s => `<option value="${s.id}">${s.supplier_name}</option>`).join('');
  const m = modal(`
    <div class="modal-head"><h3>Issue Seed</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <form class="form" id="seedIssueForm">
      <div class="full"><label>Booking *</label><select name="booking_id" id="sBookingSelect" required onchange="onSeedBookingChange()">${bookingOpts}</select></div>
      <div><label>Variety *</label><select name="variety" id="sVarietySelect" required>${varOpts}</select></div>
      <div><label>Seed Supplier</label><select name="supplier_id">${supplierOpts}</select></div>
      <div><label>Issue Date</label><input type="date" name="issue_date" value="${today()}"></div>
      <div><label>Packets *</label><input type="number" name="packets" min="1" required oninput="calcSeedValue()"></div>
      <div><label>Rate / Packet (₹) *</label><input type="number" name="rate_per_packet" step="0.01" min="0" required oninput="calcSeedValue()" id="seedRateInput"></div>
      <div><label>Packet Weight (KG)</label><input type="number" name="packet_weight_kg" value="50" step="0.1"></div>
      <div><label>Seed Value (auto)</label><input type="text" id="seedValueDisplay" readonly disabled style="background:var(--lime2)"></div>
      <div><label>Challan / Reference</label><input name="challan_ref"></div>
      <div><label>Vehicle No.</label><input name="vehicle_no"></div>
      <div class="full"><label>Remarks</label><textarea name="remarks"></textarea></div>
      <div class="full"><button class="primary" type="submit">Save Seed Issue</button></div>
    </form>`);

  document.getElementById('seedIssueForm').onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    const sel = document.getElementById('sBookingSelect');
    data.farmer_id = parseInt(sel.selectedOptions[0].dataset.farmer);
    data.packets = parseFloat(data.packets);
    data.rate_per_packet = parseFloat(data.rate_per_packet);
    data.booking_id = parseInt(data.booking_id);
    try {
      const res = await api('/api/seed/issues', { method: 'POST', body: JSON.stringify(data) });
      toast(`Seed issue saved — Value: ${money(res.total_value)}`);
      closeModal(e.target);
      await seedPage();
    } catch (ex) { toast(ex.message, 'error'); }
  };
}

window.calcSeedValue = () => {
  const p = parseFloat(document.querySelector('[name="packets"]')?.value || 0);
  const r = parseFloat(document.getElementById('seedRateInput')?.value || 0);
  const el = document.getElementById('seedValueDisplay');
  if (el) el.value = money(p * r);
};

window.onSeedBookingChange = async () => {
  const bookingId = document.getElementById('sBookingSelect')?.value;
  const varSel = document.getElementById('sVarietySelect');
  if (!bookingId || !varSel) return;
  try {
    const b = await api(`/api/bookings/${bookingId}`);
    // Pre-fill variety from booking if only 1 variety
    if (b.varieties?.length === 1) varSel.value = b.varieties[0].variety;
  } catch (_) {}
};

window.cancelSeedIssue = async id => {
  const reason = prompt('Cancellation reason (required):');
  if (!reason) return;
  try {
    await api(`/api/seed/issues/${id}/cancel`, { method: 'PUT', body: JSON.stringify({ reason }) });
    toast('Seed issue cancelled');
    await seedPage();
  } catch (ex) { toast(ex.message, 'error'); }
};

async function openPaymentModal() {
  const issues = await api('/api/seed/issues?status=Active');
  const m = modal(`
    <div class="modal-head"><h3>Record Seed Payment</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <form class="form" id="paymentForm">
      <div class="full"><label>Seed Issue *</label><select name="seed_issue_id" required>
        ${issues.map(i => `<option value="${i.id}">${i.farmer} · ${i.variety} · Balance: ${money(i.balance)}</option>`).join('')}
      </select></div>
      <div><label>Payment Date</label><input type="date" name="payment_date" value="${today()}"></div>
      <div><label>Amount (₹) *</label><input type="number" name="amount" step="0.01" min="0.01" required></div>
      <div><label>Payment Mode</label><select name="mode">
        <option>Cash</option><option>Bank Transfer</option><option>UPI</option><option>Cheque</option><option>Adjustment</option><option>Other</option>
      </select></div>
      <div><label>Reference Number</label><input name="reference_no"></div>
      <div class="full"><label>Remarks</label><textarea name="remarks"></textarea></div>
      <div class="full"><button class="primary" type="submit">Record Payment</button></div>
    </form>`);
  document.getElementById('paymentForm').onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.seed_issue_id = parseInt(data.seed_issue_id);
    data.amount = parseFloat(data.amount);
    try {
      await api('/api/seed/payments', { method: 'POST', body: JSON.stringify(data) });
      toast('Payment recorded');
      closeModal(e.target);
      await seedPage();
    } catch (ex) { toast(ex.message, 'error'); }
  };
}

// ==================== BARDANA ====================
async function bardanaPage() {
  await Promise.all([loadFarmers(), loadBookings()]);
  const rows = await api('/api/bardana');
  content().innerHTML = `
    <div class="panel">
      <div class="panel-head">
        <div><h3>Bardana / Empty Bag Distribution</h3><p>Track bags supplied to farmers</p></div>
        <button class="btn green" onclick="openBardanaModal()">+ Issue Bardana</button>
      </div>
      <div class="toolbar">
        <select id="bardanaFarmerFilter" onchange="filterBardana()"><option value="">All Farmers</option>
          ${masterCache.farmers.map(f=>`<option value="${f.id}">${f.name}</option>`).join('')}
        </select>
      </div>
      <div id="bardanaTable" class="table-wrap">${renderBardanaTable(rows)}</div>
    </div>`;
}

function renderBardanaTable(rows) {
  if (!rows.length) return '<div class="empty-state"><div class="empty-icon">🛍</div><p>No bardana issues found</p></div>';
  return `<table>
    <thead><tr><th>Farmer</th><th>Booking</th><th>Date</th><th>Month</th><th>Type</th><th class="num">Bags</th><th>Challan</th><th>Vehicle</th><th>Status</th><th></th></tr></thead>
    <tbody>${rows.map(x => `<tr>
      <td><b>${x.farmer}</b></td>
      <td>${x.booking_id ? `#${x.booking_id}` : '—'}</td>
      <td>${fmtDate(x.issue_date)}</td>
      <td>${x.contract_month||'—'}</td>
      <td>${x.bardana_type||'Potato Storage Bag'}</td>
      <td class="num">${num(x.bags_issued)}</td>
      <td>${x.challan_ref||'—'}</td>
      <td>${x.vehicle_no||'—'}</td>
      <td>${statusTag(x.status||'Active')}</td>
      <td>${x.status === 'Active' ? `<button class="btn sm red" onclick="cancelBardana(${x.id})">Cancel</button>` : ''}</td>
    </tr>`).join('')}</tbody>
  </table>`;
}

async function filterBardana() {
  const farmer = document.getElementById('bardanaFarmerFilter')?.value;
  let url = '/api/bardana?';
  if (farmer) url += `farmer_id=${farmer}&`;
  const rows = await api(url);
  const el = document.getElementById('bardanaTable');
  if (el) el.innerHTML = renderBardanaTable(rows);
}

function openBardanaModal() {
  const bookingOpts = masterCache.bookings.map(b => `<option value="${b.id}" data-farmer="${b.farmer_id}">${b.booking_code} — ${b.farmer}</option>`).join('');
  const typeOpts = masterCache.bardanaTypes.map(t => `<option value="${t.name}">${t.name}</option>`).join('');
  const m = modal(`
    <div class="modal-head"><h3>Issue Bardana</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <form class="form" id="bardanaForm">
      <div class="full"><label>Booking *</label><select name="booking_id" id="bardanaBookingSel" required>${bookingOpts}</select></div>
      <div><label>Issue Date</label><input type="date" name="issue_date" value="${today()}"></div>
      <div><label>Contract Month</label><select name="contract_month"><option value="">—</option>${MONTHS.map(m=>`<option>${m}</option>`).join('')}</select></div>
      <div><label>Bardana Type</label><select name="bardana_type">${typeOpts}</select></div>
      <div><label>Bags Issued *</label><input type="number" name="bags_issued" min="1" required></div>
      <div><label>Challan / Reference</label><input name="challan_ref"></div>
      <div><label>Vehicle No.</label><input name="vehicle_no"></div>
      <div class="full"><label>Remarks</label><textarea name="remarks"></textarea></div>
      <div class="full"><button class="primary" type="submit">Save Bardana Issue</button></div>
    </form>`);
  document.getElementById('bardanaForm').onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    const sel = document.getElementById('bardanaBookingSel');
    data.farmer_id = parseInt(sel.selectedOptions[0].dataset.farmer);
    data.bags_issued = parseFloat(data.bags_issued);
    data.booking_id = parseInt(data.booking_id);
    try {
      await api('/api/bardana', { method: 'POST', body: JSON.stringify(data) });
      toast('Bardana issued');
      closeModal(e.target);
      await bardanaPage();
    } catch (ex) { toast(ex.message, 'error'); }
  };
}

window.cancelBardana = async id => {
  const reason = prompt('Cancellation reason:');
  if (!reason) return;
  try {
    await api(`/api/bardana/${id}/cancel`, { method: 'PUT', body: JSON.stringify({ reason }) });
    toast('Bardana issue cancelled');
    await bardanaPage();
  } catch (ex) { toast(ex.message, 'error'); }
};

// ==================== DISPATCH ====================
let dispatchLines = [];

async function dispatchPage() {
  await Promise.all([loadFarmers(), loadBookings()]);
  const rows = await api('/api/dispatches');
  content().innerHTML = `
    <div class="panel">
      <div class="panel-head">
        <div><h3>Procurement / Dispatch</h3><p>Truck header with multi-farmer/variety lines and automatic tax calculation</p></div>
        <button class="btn green" onclick="openDispatchModal()">+ New Dispatch</button>
      </div>
      <div class="toolbar">
        <select id="dStatusFilter" onchange="filterDispatches()"><option value="">All Status</option>
          ${['Draft','Finalized','Cancelled'].map(s=>`<option>${s}</option>`).join('')}
        </select>
        <input id="dTruckFilter" placeholder="Truck no..." style="width:140px" oninput="filterDispatches()">
        <input id="dFromDate" type="date" onchange="filterDispatches()">
        <input id="dToDate" type="date" onchange="filterDispatches()">
      </div>
      <div id="dispatchTable" class="table-wrap">${renderDispatchTable(rows)}</div>
    </div>`;
}

function renderDispatchTable(rows) {
  if (!rows.length) return '<div class="empty-state"><div class="empty-icon">🚛</div><p>No dispatches found</p></div>';
  return `<table>
    <thead><tr><th>Dispatch</th><th>Date</th><th>Truck</th><th>Destination</th><th class="num">Actual KG</th><th class="num">Mandi KG</th><th class="num">Mandi Tax</th><th class="num">Vikas Sulk</th><th>Status</th><th></th></tr></thead>
    <tbody>${rows.map(d => `<tr>
      <td><span class="tag-text">${d.dispatch_code||d.id}</span></td>
      <td>${fmtDate(d.date||d.dispatch_date)}</td>
      <td><b>${d.truck_no||'—'}</b></td>
      <td>${d.destination||'—'}</td>
      <td class="num">${num(d.actual_weight_kg)}</td>
      <td class="num">${num(d.mandi_weight_kg)}</td>
      <td class="num">${money(d.mandi_tax)}</td>
      <td class="num">${money(d.vikas_sulk)}</td>
      <td>${statusTag(d.status||'Draft')}</td>
      <td class="actions">
        <button class="btn sm" onclick="openDispatchDetail(${d.id})">View</button>
        ${d.status === 'Draft' ? `<button class="btn sm green" onclick="finalizeDispatch(${d.id})">Finalize</button>` : ''}
        ${d.status !== 'Cancelled' ? `<button class="btn sm red" onclick="cancelDispatch(${d.id})">Cancel</button>` : ''}
      </td>
    </tr>`).join('')}</tbody>
  </table>`;
}

async function filterDispatches() {
  const status = document.getElementById('dStatusFilter')?.value;
  const truck = document.getElementById('dTruckFilter')?.value;
  const from = document.getElementById('dFromDate')?.value;
  const to = document.getElementById('dToDate')?.value;
  let url = '/api/dispatches?';
  if (status) url += `status=${encodeURIComponent(status)}&`;
  if (truck) url += `truck_no=${encodeURIComponent(truck)}&`;
  if (from) url += `date_from=${from}&`;
  if (to) url += `date_to=${to}&`;
  const rows = await api(url);
  const el = document.getElementById('dispatchTable');
  if (el) el.innerHTML = renderDispatchTable(rows);
}

async function openDispatchModal() {
  const contracts = await api('/api/contracts/due');
  const destOpts = masterCache.destinations.map(d => `<option>${d.name}</option>`).join('');
  const transOpts = ['<option value="">— None —</option>', ...masterCache.transporters.map(t => `<option value="${t.id}">${t.transporter_name}</option>`)].join('');
  dispatchLines = [];

  const m = modal(`
    <div class="modal-head"><h3>New Potato Dispatch</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <div class="notice">Tax is calculated from the Mandi Weight using the effective tax rate for the dispatch date. Only Finalized dispatches affect contract balances.</div>
    <form id="dispatchForm">
      <div class="form">
        <div><label>Dispatch Date *</label><input type="date" name="dispatch_date" value="${today()}" required oninput="lookupTaxRate()"></div>
        <div><label>Truck Number *</label><input name="truck_no" required placeholder="PB10AB1234"></div>
        <div><label>Transporter</label><select name="transporter_id">${transOpts}</select></div>
        <div><label>Destination</label><select name="destination">${destOpts}</select></div>
        <div><label>Gatepass No.</label><input name="gatepass_no"></div>
        <div><label>9R Number</label><input name="nine_r_no"></div>
        <div><label>Actual Weight (KG)</label><input type="number" name="actual_weight_kg" min="0" value="25000" oninput="calcDispatchTax()"></div>
        <div><label>Mandi / Taxable Weight (KG)</label><input type="number" name="mandi_weight_kg" min="0" value="25000" oninput="calcDispatchTax()" id="mandiWeightInput"></div>
        <div class="full"><label>Remarks</label><textarea name="remarks"></textarea></div>
      </div>
      <div id="taxPreview" class="notice" style="margin-top:8px"></div>
      <hr class="section">
      <h4 style="margin:0 0 10px">Dispatch Lines (Farmers/Varieties)</h4>
      <div id="dispatchLineRows" class="variety-rows"></div>
      <button type="button" class="add-row-btn" onclick="addDispatchLine(${JSON.stringify(contracts).replace(/"/g, '&quot;')})">+ Add Farmer/Variety Line</button>
      <button class="primary" type="submit" style="margin-top:14px">Save Dispatch (Draft)</button>
    </form>`, true);

  lookupTaxRate();
  addDispatchLineFromContracts(contracts);

  document.getElementById('dispatchForm').onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.actual_weight_kg = parseFloat(data.actual_weight_kg || 0);
    data.mandi_weight_kg = parseFloat(data.mandi_weight_kg || 0);
    data.lines = collectDispatchLines();
    if (!data.lines.length) { toast('Add at least one dispatch line', 'error'); return; }
    try {
      const res = await api('/api/dispatches', { method: 'POST', body: JSON.stringify(data) });
      toast(`Dispatch ${res.dispatch_code} saved — Tax: ${money(res.mandi_tax)} + ${money(res.vikas_sulk)}`);
      closeModal(e.target);
      await dispatchPage();
    } catch (ex) { toast(ex.message, 'error'); }
  };
}

window.lookupTaxRate = async () => {
  const dt = document.querySelector('[name="dispatch_date"]')?.value;
  if (!dt) return;
  try {
    const r = await api(`/api/masters/tax-rates/for-date?date=${dt}`);
    if (r) {
      document.getElementById('taxPreview').innerHTML = `Tax Rate (${r.effective_from}): Mandi ₹${r.mandi_rate_per_qtl}/Qtl (cap ₹${r.mandi_cap||'none'}) · Vikas ₹${r.vikas_rate_per_qtl}/Qtl (cap ₹${r.vikas_cap||'none'})`;
      calcDispatchTax(r);
    }
  } catch (_) { document.getElementById('taxPreview').innerHTML = '<span class="error">⚠ No tax rate found for this date</span>'; }
};

window.calcDispatchTax = (rate) => {
  const mw = parseFloat(document.getElementById('mandiWeightInput')?.value || 0);
  if (!rate || !mw) return;
  const qtl = mw / 100;
  const mandi = rate.mandi_cap ? Math.min(qtl * rate.mandi_rate_per_qtl, rate.mandi_cap) : qtl * rate.mandi_rate_per_qtl;
  const vikas = rate.vikas_cap ? Math.min(qtl * rate.vikas_rate_per_qtl, rate.vikas_cap) : qtl * rate.vikas_rate_per_qtl;
  document.getElementById('taxPreview').innerHTML += ` → <b>Mandi Tax: ${money(mandi)} · Vikas Sulk: ${money(vikas)}</b>`;
};

let dlCount = 0;
function addDispatchLineFromContracts(contracts) {
  const row = addDispatchLine(contracts);
}

window.addDispatchLine = (contracts) => {
  const idx = dlCount++;
  const contractOpts = contracts.map(c => `<option value="${c.id}" data-farmer="${c.farmer_id}" data-booking="${c.booking_id}" data-variety="${c.variety||''}">${c.farmer} · ${c.variety||'?'} · ${c.contract_month} · Bal:${num(c.pending_bags)}</option>`).join('');
  const row = document.createElement('div');
  row.className = 'dispatch-line-row';
  row.id = `dlrow-${idx}`;
  row.innerHTML = `
    <div><label>Contract *</label><select name="dl_commitment_${idx}" required style="font-size:12px">${contractOpts}</select></div>
    <div><label>Variety</label><input name="dl_variety_${idx}" placeholder="auto-filled" style="background:var(--lime2)" readonly></div>
    <div><label>Bags *</label><input type="number" name="dl_bags_${idx}" min="1" required></div>
    <div><label>Weight (KG)</label><input type="number" name="dl_weight_${idx}" min="0"></div>
    <div><label>Remarks</label><input name="dl_remarks_${idx}"></div>
    <div></div>
    <button type="button" class="row-remove" onclick="this.closest('.dispatch-line-row').remove()" title="Remove">×</button>`;
  document.getElementById('dispatchLineRows').appendChild(row);

  // Auto-fill variety from commitment selection
  const sel = row.querySelector(`[name="dl_commitment_${idx}"]`);
  const varInput = row.querySelector(`[name="dl_variety_${idx}"]`);
  if (sel && varInput) {
    const setVariety = () => { varInput.value = sel.selectedOptions[0]?.dataset.variety || ''; };
    sel.addEventListener('change', setVariety);
    setVariety();
  }
};

function collectDispatchLines() {
  const rows = document.querySelectorAll('.dispatch-line-row');
  return Array.from(rows).map(row => {
    const idx = row.id.replace('dlrow-', '');
    const sel = row.querySelector(`[name="dl_commitment_${idx}"]`);
    if (!sel) return null;
    const opt = sel.selectedOptions[0];
    return {
      commitment_id: parseInt(sel.value),
      farmer_id: parseInt(opt.dataset.farmer),
      booking_id: parseInt(opt.dataset.booking),
      variety: opt.dataset.variety || row.querySelector(`[name="dl_variety_${idx}"]`)?.value,
      bags: parseFloat(row.querySelector(`[name="dl_bags_${idx}"]`)?.value || 0),
      weight_kg: parseFloat(row.querySelector(`[name="dl_weight_${idx}"]`)?.value || 0),
      remarks: row.querySelector(`[name="dl_remarks_${idx}"]`)?.value,
    };
  }).filter(r => r && r.bags > 0);
}

async function openDispatchDetail(id) {
  const d = await api(`/api/dispatches/${id}`);
  modal(`
    <div class="modal-head">
      <div><div class="eyebrow">${d.dispatch_code}</div><h3>${fmtDate(d.dispatch_date||d.date)}</h3><p class="muted">${d.truck_no||'—'} → ${d.destination||'—'} ${statusTag(d.status)}</p></div>
      <button class="close-btn" onclick="closeModal(this)">×</button>
    </div>
    <div class="form cols-3" style="margin-bottom:14px">
      <div><small>Actual Weight</small><b>${num(d.actual_weight_kg)} KG</b></div>
      <div><small>Mandi Weight</small><b>${num(d.mandi_weight_kg)} KG</b></div>
      <div><small>Gatepass</small><b>${d.gatepass_no||'—'}</b></div>
      <div><small>9R No.</small><b>${d.nine_r_no||'—'}</b></div>
      <div><small>Mandi Tax</small><b>${money(d.mandi_tax)}</b></div>
      <div><small>Vikas Sulk</small><b>${money(d.vikas_sulk)}</b></div>
    </div>
    <table><thead><tr><th>Farmer</th><th>Variety</th><th>Bags</th><th>Weight KG</th></tr></thead>
    <tbody>${(d.lines||[]).map(l => `<tr><td>${l.farmer||'—'}</td><td>${l.variety}</td><td class="num">${num(l.bags)}</td><td class="num">${num(l.weight_kg)}</td></tr>`).join('')}</tbody>
    </table>`, true);
}

window.finalizeDispatch = async id => {
  if (!confirm('Finalize this dispatch? This will lock it and update contract balances.')) return;
  try {
    await api(`/api/dispatches/${id}/finalize`, { method: 'POST', body: '{}' });
    toast('Dispatch finalized');
    await dispatchPage();
  } catch (ex) { toast(ex.message, 'error'); }
};

window.cancelDispatch = async id => {
  const reason = prompt('Cancellation reason (required):');
  if (!reason) return;
  try {
    await api(`/api/dispatches/${id}/cancel`, { method: 'POST', body: JSON.stringify({ reason }) });
    toast('Dispatch cancelled');
    await dispatchPage();
  } catch (ex) { toast(ex.message, 'error'); }
};

// ==================== MASTERS ====================
const MASTER_SECTIONS = ['Seasons', 'Villages', 'Varieties', 'Destinations', 'Suppliers', 'Seed Rates', 'Buyback Rates', 'Bardana Types', 'Transporters'];
let activeMasterSection = 'Seasons';

async function mastersPage() {
  content().innerHTML = `
    <div class="masters-nav" id="mastersNav">
      ${MASTER_SECTIONS.map(s => `<button class="${s === activeMasterSection ? 'active' : ''}" onclick="switchMaster('${s}')">${s}</button>`).join('')}
    </div>
    <div id="masterContent"><div class="loading">Loading</div></div>`;
  await loadMasterSection(activeMasterSection);
}

window.switchMaster = async section => {
  activeMasterSection = section;
  document.querySelectorAll('.masters-nav button').forEach(b => b.classList.toggle('active', b.textContent === section));
  document.getElementById('masterContent').innerHTML = '<div class="loading">Loading</div>';
  await loadMasterSection(section);
};

async function loadMasterSection(section) {
  const el = document.getElementById('masterContent');
  try {
    switch (section) {
      case 'Seasons': el.innerHTML = await renderSeasons(); break;
      case 'Villages': el.innerHTML = await renderVillages(); break;
      case 'Varieties': el.innerHTML = await renderVarieties(); break;
      case 'Destinations': el.innerHTML = await renderDestinations(); break;
      case 'Suppliers': el.innerHTML = await renderSuppliers(); break;
      case 'Seed Rates': el.innerHTML = await renderSeedRates(); break;
      case 'Buyback Rates': el.innerHTML = await renderBuybackRates(); break;
      case 'Bardana Types': el.innerHTML = await renderBardanaTypes(); break;
      case 'Transporters': el.innerHTML = await renderTransporters(); break;
    }
  } catch (ex) { el.innerHTML = `<p class="error">Error: ${ex.message}</p>`; }
}

async function renderSeasons() {
  const rows = await api('/api/masters/seasons');
  return `<div class="panel">
    <div class="panel-head"><div><h3>Seasons</h3></div><button class="btn green" onclick="openSeasonModal()">+ Add Season</button></div>
    <table><thead><tr><th>Name</th><th>Start</th><th>End</th><th>Status</th><th></th></tr></thead>
    <tbody>${rows.map(r => `<tr>
      <td><b>${r.name}</b></td><td>${fmtDate(r.start_date)}</td><td>${fmtDate(r.end_date)}</td>
      <td>${statusTag(r.active ? 'Active' : 'Inactive')}</td>
      <td><button class="btn sm" onclick="editSeason(${r.id},'${r.name}')">Edit</button></td>
    </tr>`).join('')}
    ${!rows.length ? '<tr><td colspan="5"><div class="empty-state"><p>No seasons</p></div></td></tr>' : ''}
    </tbody></table></div>`;
}

window.openSeasonModal = (existing = null) => {
  const m = modal(`
    <div class="modal-head"><h3>${existing ? 'Edit' : 'Add'} Season</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <form class="form" id="seasonForm">
      <div class="full"><label>Season Name *</label><input name="name" required value="${existing?.name || ''}" placeholder="2025-26"></div>
      <div><label>Start Date *</label><input type="date" name="start_date" required value="${existing?.start_date || ''}"></div>
      <div><label>End Date *</label><input type="date" name="end_date" required value="${existing?.end_date || ''}"></div>
      <div class="full"><label>Status</label><select name="active">
        <option value="true" ${!existing || existing.active ? 'selected' : ''}>Active</option>
        <option value="false" ${existing && !existing.active ? 'selected' : ''}>Inactive</option>
      </select></div>
      <div class="full"><button class="primary" type="submit">${existing ? 'Save Changes' : 'Create Season'}</button></div>
    </form>`);
  document.getElementById('seasonForm').onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.active = data.active === 'true';
    try {
      if (existing) await api(`/api/masters/seasons/${existing.id}`, { method: 'PUT', body: JSON.stringify(data) });
      else await api('/api/masters/seasons', { method: 'POST', body: JSON.stringify(data) });
      toast(existing ? 'Season updated' : 'Season created');
      closeModal(e.target);
      await loadMasterSection('Seasons');
      await loadMasterCache();
    } catch (ex) { toast(ex.message, 'error'); }
  };
};

window.editSeason = async (id, name) => {
  const rows = await api('/api/masters/seasons');
  const s = rows.find(r => r.id === id);
  if (s) openSeasonModal(s);
};

async function renderVarieties() {
  const rows = await api('/api/masters/varieties');
  return `<div class="panel">
    <div class="panel-head"><div><h3>Varieties</h3></div><button class="btn green" onclick="openVarietyModal()">+ Add Variety</button></div>
    <table><thead><tr><th>Code</th><th>Name</th><th>Packets/Acre</th><th>Bags/Acre</th><th>Status</th><th></th></tr></thead>
    <tbody>${rows.map(r => `<tr>
      <td><span class="tag-text">${r.code}</span></td><td><b>${r.name}</b></td>
      <td>${r.default_seed_packets_per_acre}</td><td>${r.default_buyback_bags_per_acre}</td>
      <td>${statusTag(r.active ? 'Active' : 'Inactive')}</td>
      <td><button class="btn sm" onclick="editVariety(${r.id})">Edit</button></td>
    </tr>`).join('')}
    ${!rows.length ? '<tr><td colspan="6"><div class="empty-state"><p>No varieties</p></div></td></tr>' : ''}
    </tbody></table></div>`;
}

window.openVarietyModal = (existing = null) => {
  const m = modal(`
    <div class="modal-head"><h3>${existing ? 'Edit' : 'Add'} Variety</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <form class="form" id="varietyForm">
      <div><label>Name *</label><input name="name" required value="${existing?.name || ''}"></div>
      <div><label>Code *</label><input name="code" required value="${existing?.code || ''}" placeholder="LR"></div>
      <div><label>Default Packets/Acre</label><input type="number" name="default_seed_packets_per_acre" value="${existing?.default_seed_packets_per_acre || 25}" step="0.1"></div>
      <div><label>Default Bags/Acre</label><input type="number" name="default_buyback_bags_per_acre" value="${existing?.default_buyback_bags_per_acre || 250}" step="0.1"></div>
      <div class="full"><label>Status</label><select name="active">
        <option value="true" ${!existing || existing.active ? 'selected' : ''}>Active</option>
        <option value="false" ${existing && !existing.active ? 'selected' : ''}>Inactive</option>
      </select></div>
      <div class="full"><button class="primary" type="submit">${existing ? 'Save' : 'Create'}</button></div>
    </form>`);
  document.getElementById('varietyForm').onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.active = data.active === 'true';
    data.default_seed_packets_per_acre = parseFloat(data.default_seed_packets_per_acre);
    data.default_buyback_bags_per_acre = parseFloat(data.default_buyback_bags_per_acre);
    try {
      if (existing) await api(`/api/masters/varieties/${existing.id}`, { method: 'PUT', body: JSON.stringify(data) });
      else await api('/api/masters/varieties', { method: 'POST', body: JSON.stringify(data) });
      toast(existing ? 'Variety updated' : 'Variety created');
      closeModal(e.target);
      await loadMasterSection('Varieties');
      await loadMasterCache();
    } catch (ex) { toast(ex.message, 'error'); }
  };
};

window.editVariety = async id => {
  const rows = await api('/api/masters/varieties');
  const v = rows.find(r => r.id === id);
  if (v) openVarietyModal(v);
};

async function renderVillages() {
  const rows = await api('/api/masters/villages');
  return `<div class="panel">
    <div class="panel-head"><div><h3>Villages</h3></div><button class="btn green" onclick="openVillageModal()">+ Add Village</button></div>
    <table><thead><tr><th>Village Name</th><th>District</th><th>State</th><th>Status</th><th></th></tr></thead>
    <tbody>${rows.map(r => `<tr>
      <td><b>${r.village_name}</b></td><td>${r.district||'—'}</td><td>${r.state||'—'}</td>
      <td>${statusTag(r.active ? 'Active' : 'Inactive')}</td>
      <td><button class="btn sm" onclick="editVillage(${r.id})">Edit</button></td>
    </tr>`).join('')}
    ${!rows.length ? '<tr><td colspan="5"><div class="empty-state"><p>No villages</p></div></td></tr>' : ''}
    </tbody></table></div>`;
}

window.openVillageModal = (existing = null) => {
  const m = modal(`
    <div class="modal-head"><h3>${existing ? 'Edit' : 'Add'} Village</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <form class="form" id="villageForm">
      <div class="full"><label>Village Name *</label><input name="village_name" required value="${existing?.village_name || ''}"></div>
      <div><label>District</label><input name="district" value="${existing?.district || ''}"></div>
      <div><label>State</label><input name="state" value="${existing?.state || 'Punjab'}"></div>
      <div class="full"><label>Status</label><select name="active">
        <option value="true" ${!existing || existing.active ? 'selected' : ''}>Active</option>
        <option value="false" ${existing && !existing.active ? 'selected' : ''}>Inactive</option>
      </select></div>
      <div class="full"><button class="primary" type="submit">${existing ? 'Save' : 'Create'}</button></div>
    </form>`);
  document.getElementById('villageForm').onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.active = data.active === 'true';
    try {
      if (existing) await api(`/api/masters/villages/${existing.id}`, { method: 'PUT', body: JSON.stringify(data) });
      else await api('/api/masters/villages', { method: 'POST', body: JSON.stringify(data) });
      toast('Village saved');
      closeModal(e.target);
      await loadMasterSection('Villages');
    } catch (ex) { toast(ex.message, 'error'); }
  };
};

window.editVillage = async id => {
  const rows = await api('/api/masters/villages');
  const v = rows.find(r => r.id === id);
  if (v) openVillageModal(v);
};

async function renderDestinations() {
  const rows = await api('/api/masters/destinations');
  return `<div class="panel">
    <div class="panel-head"><div><h3>Destinations</h3></div><button class="btn green" onclick="openDestinationModal()">+ Add</button></div>
    <table><thead><tr><th>Name</th><th>Address</th><th>Status</th><th></th></tr></thead>
    <tbody>${rows.map(r => `<tr><td><b>${r.name}</b></td><td>${r.address||'—'}</td><td>${statusTag(r.active ? 'Active' : 'Inactive')}</td>
      <td><button class="btn sm" onclick="editDestination(${r.id})">Edit</button></td></tr>`).join('')}
    ${!rows.length ? '<tr><td colspan="4"><div class="empty-state"><p>No destinations</p></div></td></tr>' : ''}
    </tbody></table></div>`;
}

window.openDestinationModal = (existing = null) => {
  const m = modal(`
    <div class="modal-head"><h3>${existing ? 'Edit' : 'Add'} Destination</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <form class="form" id="destForm">
      <div class="full"><label>Name *</label><input name="name" required value="${existing?.name || ''}"></div>
      <div class="full"><label>Address</label><textarea name="address">${existing?.address || ''}</textarea></div>
      <div class="full"><label>Status</label><select name="active">
        <option value="true" ${!existing || existing.active ? 'selected' : ''}>Active</option>
        <option value="false" ${existing && !existing.active ? 'selected' : ''}>Inactive</option>
      </select></div>
      <div class="full"><button class="primary" type="submit">${existing ? 'Save' : 'Create'}</button></div>
    </form>`);
  document.getElementById('destForm').onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.active = data.active === 'true';
    try {
      if (existing) await api(`/api/masters/destinations/${existing.id}`, { method: 'PUT', body: JSON.stringify(data) });
      else await api('/api/masters/destinations', { method: 'POST', body: JSON.stringify(data) });
      toast('Destination saved');
      closeModal(e.target);
      await loadMasterSection('Destinations');
      await loadMasterCache();
    } catch (ex) { toast(ex.message, 'error'); }
  };
};

window.editDestination = async id => {
  const rows = await api('/api/masters/destinations');
  const d = rows.find(r => r.id === id);
  if (d) openDestinationModal(d);
};

async function renderSuppliers() {
  const rows = await api('/api/masters/suppliers');
  return `<div class="panel">
    <div class="panel-head"><div><h3>Seed Suppliers</h3></div><button class="btn green" onclick="openSupplierModal()">+ Add</button></div>
    <table><thead><tr><th>Supplier Name</th><th>Status</th><th></th></tr></thead>
    <tbody>${rows.map(r => `<tr><td><b>${r.supplier_name}</b></td><td>${statusTag(r.active ? 'Active' : 'Inactive')}</td>
      <td><button class="btn sm" onclick="editSupplier(${r.id})">Edit</button></td></tr>`).join('')}
    ${!rows.length ? '<tr><td colspan="3"><div class="empty-state"><p>No suppliers</p></div></td></tr>' : ''}
    </tbody></table></div>`;
}

window.openSupplierModal = (existing = null) => {
  const m = modal(`
    <div class="modal-head"><h3>${existing ? 'Edit' : 'Add'} Supplier</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <form class="form cols-1" id="supplierForm">
      <div><label>Supplier Name *</label><input name="supplier_name" required value="${existing?.supplier_name || ''}"></div>
      <div><label>Status</label><select name="active">
        <option value="true" ${!existing || existing.active ? 'selected' : ''}>Active</option>
        <option value="false" ${existing && !existing.active ? 'selected' : ''}>Inactive</option>
      </select></div>
      <div><button class="primary" type="submit">${existing ? 'Save' : 'Create'}</button></div>
    </form>`);
  document.getElementById('supplierForm').onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.active = data.active === 'true';
    try {
      if (existing) await api(`/api/masters/suppliers/${existing.id}`, { method: 'PUT', body: JSON.stringify(data) });
      else await api('/api/masters/suppliers', { method: 'POST', body: JSON.stringify(data) });
      toast('Supplier saved');
      closeModal(e.target);
      await loadMasterSection('Suppliers');
      await loadMasterCache();
    } catch (ex) { toast(ex.message, 'error'); }
  };
};

window.editSupplier = async id => {
  const rows = await api('/api/masters/suppliers');
  const s = rows.find(r => r.id === id);
  if (s) openSupplierModal(s);
};

async function renderSeedRates() {
  const rows = await api('/api/masters/seed-rates');
  return `<div class="panel">
    <div class="panel-head"><div><h3>Seed Rate Master</h3></div><button class="btn green" onclick="openSeedRateModal()">+ Add Rate</button></div>
    <table><thead><tr><th>Variety</th><th>Season</th><th>Effective From</th><th>Effective To</th><th class="num">Rate/Packet</th><th>Packet KG</th><th>Status</th><th></th></tr></thead>
    <tbody>${rows.map(r => `<tr>
      <td><b>${r.variety_name||r.variety_id}</b></td><td>${r.season_name||r.season_id}</td>
      <td>${fmtDate(r.effective_from)}</td><td>${fmtDate(r.effective_to)||'—'}</td>
      <td class="num">${money(r.rate_per_packet)}</td><td>${r.packet_weight_kg} KG</td>
      <td>${statusTag(r.active ? 'Active' : 'Inactive')}</td>
      <td><button class="btn sm" onclick="editSeedRate(${r.id})">Edit</button></td>
    </tr>`).join('')}
    ${!rows.length ? '<tr><td colspan="8"><div class="empty-state"><p>No seed rates configured</p></div></td></tr>' : ''}
    </tbody></table></div>`;
}

window.openSeedRateModal = (existing = null) => {
  const varOpts = masterCache.varieties.map(v => `<option value="${v.id}" ${existing?.variety_id===v.id?'selected':''}>${v.name}</option>`).join('');
  const seaOpts = masterCache.seasons.map(s => `<option value="${s.id}" ${existing?.season_id===s.id?'selected':''}>${s.name}</option>`).join('');
  const m = modal(`
    <div class="modal-head"><h3>${existing ? 'Edit' : 'Add'} Seed Rate</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <form class="form" id="seedRateForm">
      <div><label>Variety *</label><select name="variety_id" required>${varOpts}</select></div>
      <div><label>Season *</label><select name="season_id" required>${seaOpts}</select></div>
      <div><label>Effective From *</label><input type="date" name="effective_from" required value="${existing?.effective_from||''}"></div>
      <div><label>Effective To</label><input type="date" name="effective_to" value="${existing?.effective_to||''}"></div>
      <div><label>Rate / Packet (₹) *</label><input type="number" name="rate_per_packet" step="0.01" min="0" required value="${existing?.rate_per_packet||''}"></div>
      <div><label>Packet Weight (KG)</label><input type="number" name="packet_weight_kg" value="${existing?.packet_weight_kg||50}" step="0.1"></div>
      <div class="full"><label>Status</label><select name="active">
        <option value="true" ${!existing||existing.active?'selected':''}>Active</option>
        <option value="false" ${existing&&!existing.active?'selected':''}>Inactive</option>
      </select></div>
      <div class="full"><button class="primary" type="submit">${existing ? 'Save' : 'Create'}</button></div>
    </form>`);
  document.getElementById('seedRateForm').onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.active = data.active === 'true';
    data.variety_id = parseInt(data.variety_id);
    data.season_id = parseInt(data.season_id);
    data.rate_per_packet = parseFloat(data.rate_per_packet);
    data.packet_weight_kg = parseFloat(data.packet_weight_kg);
    try {
      if (existing) await api(`/api/masters/seed-rates/${existing.id}`, { method: 'PUT', body: JSON.stringify(data) });
      else await api('/api/masters/seed-rates', { method: 'POST', body: JSON.stringify(data) });
      toast('Seed rate saved');
      closeModal(e.target);
      await loadMasterSection('Seed Rates');
    } catch (ex) { toast(ex.message, 'error'); }
  };
};

window.editSeedRate = async id => {
  const rows = await api('/api/masters/seed-rates');
  const r = rows.find(x => x.id === id);
  if (r) openSeedRateModal(r);
};

async function renderBuybackRates() {
  const rows = await api('/api/masters/buyback-rates');
  return `<div class="panel">
    <div class="panel-head"><div><h3>Buyback Rate Master</h3></div><button class="btn green" onclick="openBuybackRateModal()">+ Add Rate</button></div>
    <table><thead><tr><th>Variety</th><th>Season</th><th>Month</th><th>Destination</th><th class="num">Rate/Bag</th><th>From</th><th>To</th><th>Status</th><th></th></tr></thead>
    <tbody>${rows.map(r => `<tr>
      <td>${r.variety_name||'Any'}</td><td>${r.season_name||r.season_id}</td><td>${r.contract_month}</td>
      <td>${r.destination_name||'Any'}</td><td class="num">${money(r.rate_per_bag)}</td>
      <td>${fmtDate(r.effective_from)}</td><td>${fmtDate(r.effective_to)||'—'}</td>
      <td>${statusTag(r.active ? 'Active' : 'Inactive')}</td>
      <td><button class="btn sm" onclick="editBuybackRate(${r.id})">Edit</button></td>
    </tr>`).join('')}
    ${!rows.length ? '<tr><td colspan="9"><div class="empty-state"><p>No buyback rates configured</p></div></td></tr>' : ''}
    </tbody></table></div>`;
}

window.openBuybackRateModal = (existing = null) => {
  const varOpts = `<option value="">Any</option>` + masterCache.varieties.map(v => `<option value="${v.id}" ${existing?.variety_id===v.id?'selected':''}>${v.name}</option>`).join('');
  const seaOpts = masterCache.seasons.map(s => `<option value="${s.id}" ${existing?.season_id===s.id?'selected':''}>${s.name}</option>`).join('');
  const destOpts = `<option value="">Any</option>` + masterCache.destinations.map(d => `<option value="${d.id}" ${existing?.destination_id===d.id?'selected':''}>${d.name}</option>`).join('');
  const m = modal(`
    <div class="modal-head"><h3>${existing ? 'Edit' : 'Add'} Buyback Rate</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <form class="form" id="buybackRateForm">
      <div><label>Variety (blank = all)</label><select name="variety_id">${varOpts}</select></div>
      <div><label>Season *</label><select name="season_id" required>${seaOpts}</select></div>
      <div><label>Contract Month *</label><select name="contract_month" required>${MONTHS.map(m=>`<option ${existing?.contract_month===m?'selected':''}>${m}</option>`).join('')}</select></div>
      <div><label>Destination (blank = all)</label><select name="destination_id">${destOpts}</select></div>
      <div><label>Effective From *</label><input type="date" name="effective_from" required value="${existing?.effective_from||''}"></div>
      <div><label>Effective To</label><input type="date" name="effective_to" value="${existing?.effective_to||''}"></div>
      <div><label>Rate / Bag (₹) *</label><input type="number" name="rate_per_bag" step="0.01" min="0" required value="${existing?.rate_per_bag||''}"></div>
      <div><label>Status</label><select name="active">
        <option value="true" ${!existing||existing.active?'selected':''}>Active</option>
        <option value="false" ${existing&&!existing.active?'selected':''}>Inactive</option>
      </select></div>
      <div class="full"><button class="primary" type="submit">${existing ? 'Save' : 'Create'}</button></div>
    </form>`);
  document.getElementById('buybackRateForm').onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.active = data.active === 'true';
    if (data.variety_id) data.variety_id = parseInt(data.variety_id); else delete data.variety_id;
    if (data.destination_id) data.destination_id = parseInt(data.destination_id); else delete data.destination_id;
    data.season_id = parseInt(data.season_id);
    data.rate_per_bag = parseFloat(data.rate_per_bag);
    try {
      if (existing) await api(`/api/masters/buyback-rates/${existing.id}`, { method: 'PUT', body: JSON.stringify(data) });
      else await api('/api/masters/buyback-rates', { method: 'POST', body: JSON.stringify(data) });
      toast('Buyback rate saved');
      closeModal(e.target);
      await loadMasterSection('Buyback Rates');
    } catch (ex) { toast(ex.message, 'error'); }
  };
};

window.editBuybackRate = async id => {
  const rows = await api('/api/masters/buyback-rates');
  const r = rows.find(x => x.id === id);
  if (r) openBuybackRateModal(r);
};

async function renderBardanaTypes() {
  const rows = await api('/api/masters/bardana-types');
  return `<div class="panel">
    <div class="panel-head"><div><h3>Bardana Types</h3></div><button class="btn green" onclick="openBardanaTypeModal()">+ Add</button></div>
    <table><thead><tr><th>Name</th><th>Capacity (KG)</th><th>Status</th><th></th></tr></thead>
    <tbody>${rows.map(r => `<tr><td><b>${r.name}</b></td><td>${r.bag_capacity||'—'}</td><td>${statusTag(r.active ? 'Active' : 'Inactive')}</td>
      <td><button class="btn sm" onclick="editBardanaType(${r.id})">Edit</button></td></tr>`).join('')}
    ${!rows.length ? '<tr><td colspan="4"><div class="empty-state"><p>No bardana types</p></div></td></tr>' : ''}
    </tbody></table></div>`;
}

window.openBardanaTypeModal = (existing = null) => {
  const m = modal(`
    <div class="modal-head"><h3>${existing ? 'Edit' : 'Add'} Bardana Type</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <form class="form" id="bardanaTypeForm">
      <div class="full"><label>Name *</label><input name="name" required value="${existing?.name||''}"></div>
      <div><label>Bag Capacity (KG)</label><input type="number" name="bag_capacity" value="${existing?.bag_capacity||50}" step="0.1"></div>
      <div><label>Status</label><select name="active">
        <option value="true" ${!existing||existing.active?'selected':''}>Active</option>
        <option value="false" ${existing&&!existing.active?'selected':''}>Inactive</option>
      </select></div>
      <div class="full"><button class="primary" type="submit">${existing ? 'Save' : 'Create'}</button></div>
    </form>`);
  document.getElementById('bardanaTypeForm').onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.active = data.active === 'true';
    data.bag_capacity = parseFloat(data.bag_capacity);
    try {
      if (existing) await api(`/api/masters/bardana-types/${existing.id}`, { method: 'PUT', body: JSON.stringify(data) });
      else await api('/api/masters/bardana-types', { method: 'POST', body: JSON.stringify(data) });
      toast('Bardana type saved');
      closeModal(e.target);
      await loadMasterSection('Bardana Types');
      await loadMasterCache();
    } catch (ex) { toast(ex.message, 'error'); }
  };
};

window.editBardanaType = async id => {
  const rows = await api('/api/masters/bardana-types');
  const r = rows.find(x => x.id === id);
  if (r) openBardanaTypeModal(r);
};

async function renderTransporters() {
  const rows = await api('/api/masters/transporters');
  return `<div class="panel">
    <div class="panel-head"><div><h3>Transporters</h3></div><button class="btn green" onclick="openTransporterModal()">+ Add</button></div>
    <table><thead><tr><th>Name</th><th>Phone</th><th>Address</th><th>Status</th><th></th></tr></thead>
    <tbody>${rows.map(r => `<tr><td><b>${r.transporter_name}</b></td><td>${r.phone||'—'}</td><td>${r.address||'—'}</td>
      <td>${statusTag(r.active ? 'Active' : 'Inactive')}</td>
      <td><button class="btn sm" onclick="editTransporter(${r.id})">Edit</button></td></tr>`).join('')}
    ${!rows.length ? '<tr><td colspan="5"><div class="empty-state"><p>No transporters</p></div></td></tr>' : ''}
    </tbody></table></div>`;
}

window.openTransporterModal = (existing = null) => {
  const m = modal(`
    <div class="modal-head"><h3>${existing ? 'Edit' : 'Add'} Transporter</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <form class="form" id="transporterForm">
      <div class="full"><label>Name *</label><input name="transporter_name" required value="${existing?.transporter_name||''}"></div>
      <div><label>Phone</label><input name="phone" value="${existing?.phone||''}"></div>
      <div class="full"><label>Address</label><textarea name="address">${existing?.address||''}</textarea></div>
      <div class="full"><label>Status</label><select name="active">
        <option value="true" ${!existing||existing.active?'selected':''}>Active</option>
        <option value="false" ${existing&&!existing.active?'selected':''}>Inactive</option>
      </select></div>
      <div class="full"><button class="primary" type="submit">${existing ? 'Save' : 'Create'}</button></div>
    </form>`);
  document.getElementById('transporterForm').onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.active = data.active === 'true';
    try {
      if (existing) await api(`/api/masters/transporters/${existing.id}`, { method: 'PUT', body: JSON.stringify(data) });
      else await api('/api/masters/transporters', { method: 'POST', body: JSON.stringify(data) });
      toast('Transporter saved');
      closeModal(e.target);
      await loadMasterSection('Transporters');
      await loadMasterCache();
    } catch (ex) { toast(ex.message, 'error'); }
  };
};

window.editTransporter = async id => {
  const rows = await api('/api/masters/transporters');
  const r = rows.find(x => x.id === id);
  if (r) openTransporterModal(r);
};

// ==================== TAX PAGE ====================
async function taxPage() {
  const [rates, dispatches] = await Promise.all([api('/api/masters/tax-rates'), api('/api/dispatches')]);
  const finalized = dispatches.filter(d => d.status === 'Finalized');
  content().innerHTML = `
    <div class="panel">
      <div class="panel-head"><div><h3>Mandi Tax Rate Master</h3></div><button class="btn green" onclick="openTaxRateModal()">+ Add Rate</button></div>
      <div class="grid cards-4">${rates.map(r => `
        <div class="card">
          <small>Effective ${fmtDate(r.effective_from)}${r.effective_to ? ' – ' + fmtDate(r.effective_to) : ' onwards'}</small>
          <strong style="font-size:16px">${money(r.mandi_rate_per_qtl)}/Qtl</strong>
          <div class="card-sub">Vikas: ${money(r.vikas_rate_per_qtl)}/Qtl<br>
          Mandi Cap: ${r.mandi_cap ? money(r.mandi_cap) : 'None'} &bull; Vikas Cap: ${r.vikas_cap ? money(r.vikas_cap) : 'None'}</div>
          <div style="margin-top:8px">${statusTag(r.active ? 'Active' : 'Inactive')}</div>
        </div>`).join('')}
      </div>
    </div>
    <div class="panel">
      <div class="panel-head"><div><h3>Tax Register (Finalized Dispatches)</h3></div></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Dispatch</th><th>Date</th><th>Truck</th><th class="num">Mandi KG</th><th class="num">Mandi Tax</th><th class="num">Vikas Sulk</th><th class="num">Total</th></tr></thead>
          <tbody>${finalized.map(d => `<tr>
            <td>${d.dispatch_code||d.id}</td><td>${fmtDate(d.date||d.dispatch_date)}</td><td>${d.truck_no||'—'}</td>
            <td class="num">${num(d.mandi_weight_kg)} KG</td>
            <td class="num">${money(d.mandi_tax)}</td><td class="num">${money(d.vikas_sulk)}</td>
            <td class="num"><b>${money(d.mandi_tax + d.vikas_sulk)}</b></td>
          </tr>`).join('')}
          ${finalized.length ? `<tr style="font-weight:800;background:var(--lime2)">
            <td colspan="4">TOTAL</td>
            <td class="num">${money(finalized.reduce((s,d)=>s+d.mandi_tax,0))}</td>
            <td class="num">${money(finalized.reduce((s,d)=>s+d.vikas_sulk,0))}</td>
            <td class="num">${money(finalized.reduce((s,d)=>s+d.mandi_tax+d.vikas_sulk,0))}</td>
          </tr>` : '<tr><td colspan="7"><div class="empty-state"><p>No finalized dispatches yet</p></div></td></tr>'}
          </tbody>
        </table>
      </div>
    </div>`;
}

window.openTaxRateModal = (existing = null) => {
  const m = modal(`
    <div class="modal-head"><h3>${existing ? 'Edit' : 'Add'} Tax Rate</h3><button class="close-btn" onclick="closeModal(this)">×</button></div>
    <form class="form" id="taxRateForm">
      <div><label>Effective From *</label><input type="date" name="effective_from" required value="${existing?.effective_from||''}"></div>
      <div><label>Effective To (blank = open-ended)</label><input type="date" name="effective_to" value="${existing?.effective_to||''}"></div>
      <div><label>Mandi Rate (₹/Qtl) *</label><input type="number" name="mandi_rate_per_qtl" step="0.01" required value="${existing?.mandi_rate_per_qtl||''}"></div>
      <div><label>Vikas Rate (₹/Qtl) *</label><input type="number" name="vikas_rate_per_qtl" step="0.01" required value="${existing?.vikas_rate_per_qtl||''}"></div>
      <div><label>Mandi Cap (₹, blank = none)</label><input type="number" name="mandi_cap" step="0.01" value="${existing?.mandi_cap||''}"></div>
      <div><label>Vikas Cap (₹, blank = none)</label><input type="number" name="vikas_cap" step="0.01" value="${existing?.vikas_cap||''}"></div>
      <div class="full"><label>Remarks</label><textarea name="remarks">${existing?.remarks||''}</textarea></div>
      <div class="full"><label>Status</label><select name="active">
        <option value="true" ${!existing||existing.active?'selected':''}>Active</option>
        <option value="false" ${existing&&!existing.active?'selected':''}>Inactive</option>
      </select></div>
      <div class="full"><button class="primary" type="submit">${existing ? 'Save' : 'Create'}</button></div>
    </form>`);
  document.getElementById('taxRateForm').onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    data.active = data.active === 'true';
    data.mandi_rate_per_qtl = parseFloat(data.mandi_rate_per_qtl);
    data.vikas_rate_per_qtl = parseFloat(data.vikas_rate_per_qtl);
    if (data.mandi_cap) data.mandi_cap = parseFloat(data.mandi_cap); else delete data.mandi_cap;
    if (data.vikas_cap) data.vikas_cap = parseFloat(data.vikas_cap); else delete data.vikas_cap;
    if (!data.effective_to) delete data.effective_to;
    try {
      if (existing) await api(`/api/masters/tax-rates/${existing.id}`, { method: 'PUT', body: JSON.stringify(data) });
      else await api('/api/masters/tax-rates', { method: 'POST', body: JSON.stringify(data) });
      toast('Tax rate saved');
      closeModal(e.target);
      await taxPage();
    } catch (ex) { toast(ex.message, 'error'); }
  };
};

// ==================== REPORTS ====================
async function reportsPage() {
  const seaOpts = masterCache.seasons.map(s => `<option value="${s.name}">${s.name}</option>`).join('');
  const varOpts = masterCache.varieties.map(v => `<option value="${v.name}">${v.name}</option>`).join('');
  const destOpts = masterCache.destinations.map(d => `<option value="${d.name}">${d.name}</option>`).join('');
  const monthOpts = MONTHS.map(m => `<option value="${m}">${m}</option>`).join('');

  content().innerHTML = `
    <div class="panel">
      <div class="panel-head"><div><h3>Report Filters</h3><p>Apply filters then download XLSX or PDF</p></div></div>
      <div class="form cols-3">
        <div><label>Season</label><select id="rf_season"><option value="">All</option>${seaOpts}</select></div>
        <div><label>Variety</label><select id="rf_variety"><option value="">All</option>${varOpts}</select></div>
        <div><label>Destination</label><select id="rf_dest"><option value="">All</option>${destOpts}</select></div>
        <div><label>Contract Month</label><select id="rf_month"><option value="">All</option>${monthOpts}</select></div>
        <div><label>From Date</label><input type="date" id="rf_from"></div>
        <div><label>To Date</label><input type="date" id="rf_to"></div>
        <div><label>Booking Type</label><select id="rf_btype"><option value="">All</option><option>With Seed</option><option>Without Seed</option><option>Mixed</option></select></div>
        <div><label>Payment Status</label><select id="rf_pstatus"><option value="">All</option><option>Not Paid</option><option>Partial</option><option>Completed</option></select></div>
        <div><label>Proc. Status</label><select id="rf_cstatus"><option value="">All</option><option>Not Started</option><option>In Progress</option><option>Completed</option><option>Excess Supplied</option></select></div>
      </div>
    </div>
    <div class="report-grid" style="margin-top:16px">
      ${makeReportCard('Farmer Register', 'All farmers with contact details', 'farmers')}
      ${makeReportCard('Booking Register', 'All bookings with farmer and season', 'bookings')}
      ${makeReportCard('Month-wise Contracts', 'Contract commitments by month with progress', 'contracts', true)}
      ${makeReportCard('Seed Distribution', 'All seed issues with rates and values', 'seed-distribution')}
      ${makeReportCard('Seed Payment Outstanding', 'Farmers with pending seed payments', 'seed-outstanding', true)}
      ${makeReportCard('Bardana Issued', 'Bardana distribution register', 'bardana')}
      ${makeReportCard('Procurement Due', 'Pending procurement by farmer and month', 'procurement-due', true)}
      ${makeReportCard('Dispatch Register', 'All truck dispatches with tax details', 'dispatch-register', true)}
      ${makeReportCard('Mandi Tax & Vikas Sulk', 'Tax calculation register per dispatch', 'mandi-tax', true)}
    </div>`;
}

function makeReportCard(title, desc, key, hasPdf = false) {
  return `<div class="report-card">
    <small>Report</small>
    <strong>${title}</strong>
    <p>${desc}</p>
    <div class="report-actions">
      <a class="report-link xlsx" onclick="downloadReport('${key}','xlsx')">📊 XLSX</a>
      ${hasPdf ? `<a class="report-link pdf" onclick="downloadReport('${key}','pdf')">📄 PDF</a>` : ''}
      <a class="report-link" href="/api/reports/contracts.csv" download>📋 CSV</a>
    </div>
  </div>`;
}

window.downloadReport = (key, format) => {
  const params = new URLSearchParams();
  const add = (id, param) => { const v = document.getElementById(id)?.value; if (v) params.set(param, v); };
  add('rf_season', 'season');
  add('rf_variety', 'variety');
  add('rf_dest', 'destination');
  add('rf_month', 'month');
  add('rf_from', 'date_from');
  add('rf_to', 'date_to');
  add('rf_btype', 'booking_type');
  add('rf_pstatus', 'payment_status');
  add('rf_cstatus', 'status');
  const url = `/api/reports/${key}.${format}?${params.toString()}`;
  window.open(url, '_blank');
};

// ==================== AUDIT ====================
async function auditPage() {
  const rows = await api('/api/audit');
  content().innerHTML = `
    <div class="panel">
      <div class="panel-head"><div><h3>Audit Trail</h3><p>Last 200 operational changes recorded with user and timestamp</p></div></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Time</th><th>User</th><th>Module</th><th>Entity</th><th>ID</th><th>Action</th><th>Details</th></tr></thead>
          <tbody>${rows.length ? rows.map(x => `<tr>
            <td>${new Date(x.created_at).toLocaleString()}</td>
            <td>${x.user_name||'—'}</td>
            <td>${x.module||x.entity}</td>
            <td>${x.entity}</td>
            <td>${x.entity_id||'—'}</td>
            <td>${statusTag(x.action)}</td>
            <td>${x.details||''}</td>
          </tr>`).join('') : '<tr><td colspan="7"><div class="empty-state"><div class="empty-icon">📝</div><p>No audit records yet</p></div></td></tr>'}
          </tbody>
        </table>
      </div>
    </div>`;
}
