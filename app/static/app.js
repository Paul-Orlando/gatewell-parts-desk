/* Gatewell Parts Desk - single-page app. Plain JavaScript, no build step.
   All permission checks happen on the server; the browser only hides tabs the role can't use. */
"use strict";

const S = { emp: null, meta: null, charts: [], chat: [], route: "inventory" };
const $ = (sel, el = document) => el.querySelector(sel);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const n = (v, d = 0) => (v === null || v === undefined || v === "" ? "—" : Number(v).toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d }));
const usd = (v, d = 2) => (v === null || v === undefined ? "—" : (Number(v) < 0 ? "−$" : "$") + n(Math.abs(v), d));
const monthLabel = (ym) => { const [y, m] = ym.split("-"); return new Date(Date.UTC(+y, +m - 1, 1)).toLocaleString("en-US", { month: "short", timeZone: "UTC" }) + " ’" + y.slice(2); };
const dayLabel = (iso) => (iso ? new Date(iso + "T12:00:00Z").toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" }) : "—");
const money = (v, ccy) => (v === null || v === undefined ? "—" : `${n(v, ["JPY", "KRW", "CLP"].includes(ccy) ? 0 : 2)} ${ccy || ""}`.trim());
const has = (o, k) => o && Object.prototype.hasOwnProperty.call(o, k);
const dt = (s) => (s ? s.replace("T", " ").replace("Z", " UTC") : "—");

/* ------------------------------------------------------------------ API */
async function api(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method || "GET",
    headers: { "Content-Type": "application/json", "X-Employee-Id": localStorage.getItem("gw_emp") || "" },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (res.status === 401) { signOut(); throw new Error("Please sign in."); }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { const err = new Error(data.detail || `Request failed (${res.status})`); err.status = res.status; err.data = data; throw err; }
  return data;
}
const qs = (o) => new URLSearchParams(Object.entries(o).filter(([, v]) => v !== "" && v !== null && v !== undefined)).toString();

/* ------------------------------------------------------------------ icons */
const ICON = {
  inventory: '<path d="M3 7l9-4 9 4-9 4-9-4z"/><path d="M3 7v10l9 4 9-4V7"/><path d="M12 11v10"/>',
  orders: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/>',
  assistant: '<path d="M4 5h16v11H9l-5 4z"/><path d="M8 10h8M8 13h5"/>',
  cases: '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
  analytics: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
};
const TAB = {
  inventory: ["Inventory", "Find parts by number, name or vehicle, and see stock at every warehouse."],
  orders: ["Orders", "Look up orders by number, customer, tracking number or part."],
  assistant: ["Assistant", "Ask about parts, stock, orders, shipping costs and policies. Answers come from live company data."],
  cases: ["Support cases", "Customer contacts that need a person, including handoffs from the chat."],
  analytics: ["Analytics", "Inventory levels, prices, sales and shipping costs for your area."],
};
const icon = (k) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[k]}</svg>`;

/* ------------------------------------------------------------------ sign-in */
function signOut() { localStorage.removeItem("gw_emp"); sessionStorage.clear(); location.hash = ""; location.reload(); }

/* The demo opens on six role cards, one per kind of user; the full employee list is folded below them. */
const PERSONAS = [
  { group: "Managers", title: "Operations Director", label: "Operations Director",
    sees: "Every warehouse and every tab, including costs, margins and exchange gains." },
  { group: "Managers", title: "Regional Manager", region: "Northeast", label: "Regional Manager, Northeast",
    sees: "The Northeast region (Newark), with costs and analytics." },
  { group: "Managers", title: "Warehouse Manager", warehouse: "ATL", label: "Warehouse Manager, Atlanta",
    sees: "The Atlanta warehouse, with costs and analytics." },
  { group: "Front line", title: "Customer Service Supervisor", label: "Customer Service Supervisor",
    sees: "Every warehouse, prices, support cases and analytics.", hidden: "Our costs" },
  { group: "Front line", title: "Customer Service Rep", label: "Customer Service Rep",
    sees: "Every warehouse, prices, quotes and support cases.", hidden: "Our costs, analytics" },
  { group: "Front line", title: "Warehouse Associate", warehouse: "ATL", label: "Warehouse Associate, Atlanta",
    sees: "Stock, bins, list prices and Atlanta's orders.", hidden: "Customer prices, costs, customer names" },
];
const GROUP_NOTE = { "Managers": "Wider view, including costs", "Front line": "Day-to-day work" };

async function showSignIn() {
  $("#signin").hidden = false;
  $("#app").hidden = true;
  const people = await fetch("/api/employees").then((r) => r.json());
  const pick = (p) => people.find((e) => e.title === p.title && (!p.warehouse || e.warehouse_code === p.warehouse) && (!p.region || e.region === p.region));
  const cards = PERSONAS.map((p) => ({ ...p, emp: pick(p) })).filter((p) => p.emp);
  $("#signin-roles").innerHTML = ["Managers", "Front line"].map((g) => `
    <section class="role-group"><h2>${esc(g)} <span>${esc(GROUP_NOTE[g])}</span></h2><div class="roles">
      ${cards.filter((c) => c.group === g).map((c) => `<button class="role-card" data-id="${esc(c.emp.employee_id)}">
        <span class="role-name">${esc(c.label)}</span>
        <span class="role-person">${esc(c.emp.name)}, ${esc(c.emp.work_location)}</span>
        <span class="role-sees">${esc(c.sees)}</span>
        ${c.hidden ? `<span class="role-hidden">${icon("lock")} Can't see: ${esc(c.hidden)}</span>` : ""}
      </button>`).join("")}
    </div></section>`).join("");
  $("#signin-count").textContent = people.length;

  const order = ["Management", "Customer Service Supervisor", "Customer Service", "Warehouse"];
  const render = (f = "") => {
    const fl = f.toLowerCase();
    const groups = order.map((g) => [g, people.filter((p) => p.app_role === g &&
      (`${p.name} ${p.title} ${p.warehouse_code || ""} ${p.region || ""} ${p.work_location}`).toLowerCase().includes(fl))]);
    $("#signin-list").innerHTML = groups.filter(([, ps]) => ps.length).map(([g, ps]) => `
      <div class="signin-group"><h3>${esc(g)}</h3><div class="people">
        ${ps.map((p) => `<button class="person" data-id="${esc(p.employee_id)}"><b>${esc(p.name)}</b>
          <span class="muted small">${esc(p.title)}, ${esc(p.work_location)}</span></button>`).join("")}
      </div></div>`).join("") || '<p class="empty">No one matches that search.</p>';
  };
  render();
  $("#signin-filter").oninput = (e) => render(e.target.value);
  $("#signin").onclick = (e) => {
    const b = e.target.closest(".person, .role-card");
    if (b) { localStorage.setItem("gw_emp", b.dataset.id); location.reload(); }
  };
}

/* ------------------------------------------------------------------ shell */
async function boot() {
  if (!localStorage.getItem("gw_emp")) return showSignIn();
  let me;
  try { me = await api("/api/me"); } catch { return showSignIn(); }
  S.emp = me.employee;
  S.meta = await api("/api/meta");
  $("#app").hidden = false;
  $("#me-name").textContent = S.emp.name;
  $("#me-role").textContent = `${S.emp.title}, ${S.emp.scope_label}`;
  $("#as-of").textContent = `Data as of ${me.as_of}`;
  $("#signout").onclick = signOut;
  $("#menu-btn").onclick = () => $(".rail").classList.toggle("open");
  $("#drawer-close").onclick = closeDrawer;
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });
  $("#nav").innerHTML = S.emp.tabs.map((t) => `<a href="#/${t}" data-tab="${t}">${icon(t)}<span>${TAB[t][0]}</span></a>`).join("");
  S.chat = JSON.parse(sessionStorage.getItem("gw_chat") || "[]");
  window.addEventListener("hashchange", route);
  route();
}

function route() {
  const t = (location.hash.replace("#/", "") || S.emp.tabs[0]).split("?")[0];
  S.route = S.emp.tabs.includes(t) ? t : S.emp.tabs[0];
  document.querySelectorAll("#nav a").forEach((a) => {
    if (a.dataset.tab === S.route) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  $(".rail").classList.remove("open");
  $("#page-title").textContent = TAB[S.route][0];
  closeDrawer();
  S.charts.forEach((c) => c.destroy()); S.charts = [];
  ({ inventory: viewInventory, orders: viewOrders, assistant: viewAssistant, cases: viewCases, analytics: viewAnalytics })[S.route]();
}

function intro() { return `<p class="page-intro">${esc(TAB[S.route][1])}</p>`; }
function openDrawer(title, html) {
  $("#drawer-title").innerHTML = title;
  $("#drawer-body").innerHTML = html;
  $("#drawer").classList.add("open");
  $("#drawer").setAttribute("aria-hidden", "false");
  $("#drawer-close").focus();
}
function closeDrawer() { $("#drawer").classList.remove("open"); $("#drawer").setAttribute("aria-hidden", "true"); dropDrawerChart(); }
function dropDrawerChart() { if (S.drawerChart) { S.drawerChart.destroy(); S.drawerChart = null; } }
const opt = (v, label, sel) => `<option value="${esc(v)}" ${String(v) === String(sel ?? "") ? "selected" : ""}>${esc(label)}</option>`;
const whOptions = (sel, all = "All warehouses") => opt("", all, sel) + S.meta.warehouses.map((w) => opt(w.warehouse_code, `${w.warehouse_code} ${w.city}, ${w.state}`, sel)).join("");
const facts = (pairs) => `<dl class="facts">${pairs.filter(([, v]) => v !== undefined).map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${v ?? "—"}</dd></div>`).join("")}</dl>`;
const lockNote = (what) => `<p class="lock">${esc(what)} isn't shown for your role.</p>`;

function stockStatus(r, aggregate = false) {
  const a = r.qty_available ?? 0;
  if (aggregate && a > 0) return '<span class="status good">&#10003; In stock</span>' +
    (r.warehouses_needing_reorder ? `<div class="small muted">Low at ${r.warehouses_needing_reorder} of ${r.warehouses_stocking}</div>` : "");
  if (a > 0 && (r.needs_reorder || r.warehouses_needing_reorder)) return '<span class="status warn">&#9650; Low</span>';
  if (a > 0) return '<span class="status good">&#10003; In stock</span>';
  if ((r.qty_in_transit ?? 0) > 0) return '<span class="status info">&#8635; Inbound</span>';
  return '<span class="status bad">&#10005; Out</span>';
}
function stockBar(r) {
  const tot = Math.max(1, (r.qty_available || 0) + (r.qty_reserved || 0) + (r.qty_in_transit || 0));
  const w = (x) => `${Math.max(0, (x || 0) / tot) * 96}px`;
  return `<span class="stockbar" title="Available ${n(r.qty_available)}, reserved ${n(r.qty_reserved)}, in transit ${n(r.qty_in_transit)}">
    ${r.qty_available ? `<i class="a" style="width:${w(r.qty_available)}"></i>` : ""}${r.qty_reserved ? `<i class="r" style="width:${w(r.qty_reserved)}"></i>` : ""}${r.qty_in_transit ? `<i class="t" style="width:${w(r.qty_in_transit)}"></i>` : ""}</span>`;
}
const orderStatus = (s) => {
  const cls = { Delivered: "good", Shipped: "info", Processing: "neutral", "Partially Backordered": "warn", Cancelled: "bad", Returned: "neutral" }[s] || "neutral";
  return `<span class="status ${cls}">${esc(s)}</span>`;
};

/* ------------------------------------------------------------------ inventory */
async function viewInventory() {
  const defWh = S.emp.role === "warehouse" ? S.emp.warehouse_code : "";
  const st = JSON.parse(sessionStorage.getItem("gw_inv") || "null") || { q: "", make: "", model: "", year: "", category: "", warehouse: defWh, stock_filter: "" };
  $("#main").innerHTML = intro() + `
    <form class="filters" id="inv-form">
      <label class="field grow"><span>Part number, name or brand</span><input name="q" type="search" value="${esc(st.q)}" placeholder="e.g. brake pads front, 68253600AW"></label>
      <label class="field"><span>Make</span><select name="make">${opt("", "Any make")}${S.meta.makes.map((m) => opt(m, m, st.make)).join("")}</select></label>
      <label class="field"><span>Model</span><select name="model"><option value="">Any model</option></select></label>
      <label class="field"><span>Year</span><select name="year"><option value="">Any year</option></select></label>
      <label class="field"><span>Category</span><select name="category">${opt("", "All categories")}${S.meta.categories.map((c) => opt(c, c, st.category)).join("")}</select></label>
      <label class="field"><span>Warehouse</span><select name="warehouse">${whOptions(st.warehouse)}</select></label>
      <div class="field"><span>Show</span><div class="seg" id="inv-seg">
        ${[["", "All"], ["low", "Low"], ["out", "Out"], ["missing", "Missing"], ["aged", "Aged 180+ days"]].map(([v, l]) => `<button type="button" data-v="${v}" aria-pressed="${st.stock_filter === v}">${l}</button>`).join("")}
      </div></div>
      <button class="btn" type="submit">Search</button>
    </form>
    <div id="inv-results"><p class="empty">Loading…</p></div>`;
  const f = $("#inv-form");
  const loadModels = async () => {
    const make = f.make.value;
    f.model.innerHTML = '<option value="">Any model</option>'; f.year.innerHTML = '<option value="">Any year</option>';
    if (!make) return;
    const v = await api(`/api/vehicles?${qs({ make })}`);
    f.model.innerHTML = opt("", "Any model") + v.models.map((m) => opt(m, m, st.model)).join("");
    if (st.model && v.models.includes(st.model)) await loadYears();
  };
  const loadYears = async () => {
    f.year.innerHTML = '<option value="">Any year</option>';
    if (!f.model.value) return;
    const v = await api(`/api/vehicles?${qs({ make: f.make.value, model: f.model.value })}`);
    f.year.innerHTML = opt("", "Any year") + v.years.map((y) => opt(y, y, st.year)).join("");
  };
  f.make.onchange = () => { st.model = ""; st.year = ""; loadModels(); };
  f.model.onchange = () => { st.year = ""; loadYears(); };
  $("#inv-seg").onclick = (e) => {
    const b = e.target.closest("button"); if (!b) return;
    st.stock_filter = b.dataset.v;
    $("#inv-seg").querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
    run();
  };
  const run = async () => {
    Object.assign(st, { q: f.q.value, make: f.make.value, model: f.model.value, year: f.year.value, category: f.category.value, warehouse: f.warehouse.value });
    sessionStorage.setItem("gw_inv", JSON.stringify(st));
    $("#inv-results").innerHTML = '<p class="empty">Searching…</p>';
    try {
      const d = await api(`/api/inventory?${qs({ ...st, limit: 100 })}`);
      const cost = S.emp.can_see_cost;
      $("#inv-results").innerHTML = `<p class="result-count">${n(d.total)} parts${d.total > d.count ? ` (first ${n(d.count)} shown; narrow the search to see more)` : ""}, stock at ${esc(d.warehouse)}</p>` +
        (d.count ? `<div class="table-wrap"><table><thead><tr><th>Part</th><th>Fits</th><th>Stock</th><th class="num">Available</th><th class="num">On hand</th><th class="num">In transit</th><th class="num">Backordered</th><th class="num">Missing</th><th class="num">List price</th>${cost ? '<th class="num">Stock value</th>' : ""}</tr></thead><tbody>
        ${d.results.map((r) => `<tr class="clickable" data-pn="${esc(r.part_number)}" tabindex="0">
          <td><div class="pn">${esc(r.part_number)}</div><div>${esc(r.part_name)}</div><div class="muted small">${esc(r.brand)}${r.quality_tier !== "OEM" ? `, ${esc(r.quality_tier)}` : ""}${r.hazmat ? ", hazmat" : ""}</div></td>
          <td class="small">${esc(r.fits_summary)}</td>
          <td>${stockStatus(r, !st.warehouse)}${stockBar(r)}</td>
          <td class="num">${n(r.qty_available)}</td><td class="num">${n(r.qty_on_hand)}</td><td class="num">${n(r.qty_in_transit)}</td>
          <td class="num">${n(r.qty_backordered)}</td><td class="num">${n(r.qty_missing)}</td><td class="num">${usd(r.list_price_usd)}</td>
          ${cost ? `<td class="num">${usd(r.stock_value_usd, 0)}</td>` : ""}</tr>`).join("")}
        </tbody></table></div>` : '<p class="empty">No parts match. Try fewer words, or clear the vehicle and category filters.</p>');
    } catch (e) { $("#inv-results").innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
  };
  f.onsubmit = (e) => { e.preventDefault(); run(); };
  $("#inv-results").onclick = (e) => { const tr = e.target.closest("tr[data-pn]"); if (tr) partDrawer(tr.dataset.pn); };
  $("#inv-results").onkeydown = (e) => { const tr = e.target.closest("tr[data-pn]"); if (tr && e.key === "Enter") { e.preventDefault(); partDrawer(tr.dataset.pn); } };
  await loadModels();
  run();
}

async function partDrawer(pn) {
  dropDrawerChart();
  openDrawer(`<span class="pn">${esc(pn)}</span>`, '<p class="empty">Loading…</p>');
  const d = await api(`/api/parts/${encodeURIComponent(pn)}`);
  const p = d.part;
  const cost = S.emp.can_see_cost;
  $("#drawer-title").innerHTML = `<span class="pn" style="font-size:22px">${esc(p.part_number)}</span> <span class="muted" style="font-family:var(--font);font-weight:500;font-size:16px">${esc(p.part_name)}</span>`;
  $("#drawer-body").innerHTML = `
    ${d.replacement ? `<p class="note">This number was replaced by <b>${esc(d.replacement.part_number)}</b> on ${esc(p.supersession_date)}. Sell the replacement.</p>` : ""}
    <section>${facts([["Brand", esc(p.brand)], ["Quality", esc(p.quality_tier)], ["Condition", esc(p.condition)], ["Category", esc(p.category)],
      ["Size class", esc(p.size_class)], ["Weight", `${n(p.weight_lb, 1)} lb (${n(p.weight_kg, 1)} kg)`], ["Box", `${n(p.length_cm)} x ${n(p.width_cm)} x ${n(p.height_cm)} cm`],
      ["Shipping class", esc(p.shipping_class)], ["Hazmat", p.hazmat ? esc(p.hazmat_note) : "No"], ["List price", usd(p.list_price_usd)],
      ...(has(p, "unit_cost_usd") ? [["Our unit cost", usd(p.unit_cost_usd)]] : []), ["Core charge", p.core_charge_usd ? usd(p.core_charge_usd) : "None"],
      ["Supplier", d.supplier ? `${esc(d.supplier.supplier_name)}, ${esc(d.supplier.country)}` : "—"]])}</section>
    <section><h3>Stock by warehouse</h3>
      <div class="table-wrap"><table><thead><tr><th>Warehouse</th><th>Bin</th><th>Status</th><th class="num">Available</th><th class="num">Reserved</th><th class="num">Damaged</th><th class="num">Missing</th><th class="num">In transit</th><th class="num">Backordered</th><th class="num">Reorder at</th></tr></thead><tbody>
      ${d.stock_by_warehouse.map((s) => `<tr><td><b>${esc(s.warehouse_code)}</b> <span class="muted small">${esc(s.warehouse_city)}</span></td><td><span class="bin">${esc(s.bin_location)}</span></td>
        <td>${stockStatus(s)}</td><td class="num">${n(s.qty_available)}</td><td class="num">${n(s.qty_reserved)}</td><td class="num">${n(s.qty_damaged)}</td><td class="num">${n(s.qty_missing)}</td>
        <td class="num">${n(s.qty_in_transit)}</td><td class="num">${n(s.qty_backordered)}</td><td class="num">${n(s.reorder_point)}</td></tr>`).join("") || '<tr><td colspan="10" class="empty">Not stocked anywhere.</td></tr>'}
      </tbody></table></div></section>
    ${d.in_transit.length ? `<section><h3>On the way</h3><div class="table-wrap"><table><thead><tr><th>Shipment</th><th>From</th><th>To</th><th>Status</th><th>ETA (local)</th><th class="num">Qty</th></tr></thead><tbody>
      ${d.in_transit.map((t) => `<tr><td>${esc(t.shipment_id)}<div class="muted small">${esc(t.carrier)}, ${esc(t.mode)}</div></td><td>${esc(t.origin_name)}<div class="muted small">${esc(t.origin_country)}</div></td><td>${esc(t.destination_warehouse)}</td>
        <td><span class="status ${t.status === "In Transit" ? "info" : "warn"}">${esc(t.status)}</span>${t.exception_note ? `<div class="small muted">${esc(t.exception_note)}</div>` : ""}</td><td class="small">${esc((t.eta_destination_local || "").replace("T", " "))}</td><td class="num">${n(t.quantity)}</td></tr>`).join("")}
      </tbody></table></div></section>` : ""}
    <section><h3>Shipping quote</h3>
      <form id="quote-form" class="filters" style="margin:0">
        <label class="field"><span>Quantity</span><input name="qty" type="number" min="1" value="1" style="width:80px"></label>
        <label class="field"><span>Country</span><select name="country">${S.meta.countries.map((c) => opt(c.country_code, c.country_name, "US")).join("")}</select></label>
        <label class="field"><span>State</span><select name="state">${S.meta.states.map((s) => opt(s.state_code, s.state_name, "GA")).join("")}</select></label>
        <label class="field" style="flex-direction:row;align-items:center;gap:6px"><input name="res" type="checkbox" checked> Home address</label>
        <button class="btn" type="submit">Get rates</button>
      </form><div id="quote-out"></div></section>
    <section><h3>Fits</h3><ul class="small">${d.fits.map((f) => `<li>${esc(f.year_from)}–${esc(f.year_to)} ${esc(f.make)} ${esc(f.model)} <span class="muted">${esc(f.engines)}</span></li>`).join("")}</ul></section>
    ${d.equivalents.length ? `<section><h3>Equivalent parts</h3><div class="table-wrap"><table><thead><tr><th>Part</th><th>Brand</th><th>Quality</th><th class="num">List price</th><th class="num">Available</th></tr></thead><tbody>
      ${d.equivalents.map((x) => `<tr class="clickable" data-pn="${esc(x.part_number)}"><td class="pn">${esc(x.part_number)}</td><td>${esc(x.brand)}</td><td>${esc(x.quality_tier)}</td><td class="num">${usd(x.list_price_usd)}</td><td class="num">${n(x.qty_available)}</td></tr>`).join("")}
      </tbody></table></div></section>` : ""}
    <section><h3>Units sold per month</h3><p class="sub small muted">Last 12 months, ${esc(S.emp.scope_label)}${d.monthly_sales.some((m) => m.units) ? "" : ". No sales in this period"}</p>
      <div class="chart-box small"><canvas id="c-part-sales" aria-label="Units sold per month, last 12 months" role="img"></canvas></div>
      ${tableView(d.monthly_sales, [["order_month", "Month", 0, (v) => esc(monthLabel(v))], ["units", "Units", 1],
        ...(has(d.monthly_sales[0] || {}, "revenue_usd") ? [["revenue_usd", "Revenue", 1, (v) => usd(v, 0)]] : [])])}</section>`;
  S.drawerChart = chart("c-part-sales", { own: true, data: { labels: d.monthly_sales.map((m) => monthLabel(m.order_month)),
    datasets: [{ label: "Units sold", data: d.monthly_sales.map((m) => m.units), backgroundColor: cssVar("--series-1") }] } });
  const qf = $("#quote-form");
  qf.country.onchange = () => { qf.state.disabled = qf.country.value !== "US"; };
  qf.onsubmit = async (e) => {
    e.preventDefault();
    $("#quote-out").innerHTML = '<p class="empty">Getting rates…</p>';
    const body = { items: [{ part_number: p.part_number, quantity: Number(qf.qty.value) || 1 }], ship_to_country: qf.country.value,
      ship_to_state: qf.country.value === "US" ? qf.state.value : null, residential: qf.res.checked };
    try { $("#quote-out").innerHTML = renderQuote(await api("/api/quote", { method: "POST", body })); }
    catch (err) { $("#quote-out").innerHTML = `<p class="empty">${esc(err.message)}</p>`; }
  };
  $("#drawer-body").onclick = (e) => { const tr = e.target.closest("tr[data-pn]"); if (tr) partDrawer(tr.dataset.pn); };
}

function renderQuote(q) {
  if (!q.ok) return `<p class="note">${esc(q.message)}</p>`;
  const charges = q.options.some((o) => has(o, "cost_usd"));     // roles without prices get carriers and dates only
  const local = charges && q.currency && q.currency !== "USD";
  const fq = q.full_quote && q.full_quote.ok ? q.full_quote : null;
  return `<p class="small muted" style="margin:10px 0 6px">Ships from ${esc(q.ship_from)} to ${esc(q.ship_to)}, zone ${esc(q.zone)}, ${n(q.package_count)} package(s), ${n(q.total_weight_lb, 1)} lb. ${q.notes.map(esc).join(" ")}</p>
    <div class="table-wrap"><table><thead><tr><th>Carrier</th><th>Service</th>${charges ? '<th class="num">Shipping</th>' : ""}${local ? `<th class="num">In ${esc(q.currency)}</th>` : ""}${fq ? `<th class="num">Customer total (${esc(fq.currency)})</th>` : ""}<th>Delivery by</th></tr></thead><tbody>
    ${q.options.map((o, i) => `<tr><td><b>${esc(o.carrier)}</b></td><td>${esc(o.service)}${o.customer_pays_usd === 0 ? ' <span class="status good">Free for customer</span>' : ""}</td>
      ${charges ? `<td class="num">${usd(o.cost_usd)}</td>` : ""}${local ? `<td class="num">${money(o.cost_local, q.currency)}</td>` : ""}${fq ? `<td class="num">${money(fq.options[i]?.total, fq.currency)}</td>` : ""}<td style="white-space:nowrap">${dayLabel(o.estimated_delivery_by)}</td></tr>`).join("")}
    </tbody></table></div>
    ${q.unavailable.length ? `<p class="small muted" style="margin-top:8px">Not available: ${q.unavailable.map((u) => `${esc(u.service)} (${esc(u.reason)})`).join("; ")}</p>` : ""}
    ${fq ? `<p class="small muted">${esc(fq.import_tax)}</p>` : ""}
    <p class="small muted">${esc(q.disclaimer)}</p>`;
}

/* ------------------------------------------------------------------ orders */
async function viewOrders() {
  const st = JSON.parse(sessionStorage.getItem("gw_ord") || "null") || { q: "", status: "", order_type: "", warehouse: "", days: "30" };
  const scoped = S.emp.scope !== "Company";
  $("#main").innerHTML = intro() + (scoped ? `<p class="small muted" style="margin-top:-8px">Showing orders shipped from ${esc(S.emp.scope_label)}.</p>` : "") + `
    <form class="filters" id="ord-form">
      <label class="field grow"><span>Order, customer, tracking or part number</span><input name="q" type="search" value="${esc(st.q)}" placeholder="e.g. SO-031950, D0042, 1Z…"></label>
      <label class="field"><span>Status</span><select name="status">${opt("", "Any status")}${S.meta.order_statuses.map((s) => opt(s, s, st.status)).join("")}</select></label>
      <label class="field"><span>Type</span><select name="order_type">${opt("", "Domestic and international")}${opt("Domestic", "Domestic", st.order_type)}${opt("International", "International", st.order_type)}</select></label>
      ${scoped ? "" : `<label class="field"><span>Warehouse</span><select name="warehouse">${whOptions(st.warehouse)}</select></label>`}
      <div class="field"><span>Placed in</span><div class="seg" id="ord-seg">${[["7", "7 days"], ["30", "30 days"], ["90", "90 days"], ["", "Any time"]].map(([v, l]) => `<button type="button" data-v="${v}" aria-pressed="${st.days === v}">${l}</button>`).join("")}</div></div>
      <button class="btn" type="submit">Search</button>
    </form><div id="ord-results"></div>`;
  const f = $("#ord-form");
  const run = async () => {
    Object.assign(st, { q: f.q.value, status: f.status.value, order_type: f.order_type.value, warehouse: f.warehouse ? f.warehouse.value : "" });
    sessionStorage.setItem("gw_ord", JSON.stringify(st));
    $("#ord-results").innerHTML = '<p class="empty">Searching…</p>';
    const d = await api(`/api/orders?${qs({ ...st, days: st.q ? "" : st.days, limit: 100 })}`);
    const m = S.emp.can_see_money, c = S.emp.can_see_customer;
    $("#ord-results").innerHTML = `<p class="result-count">${n(d.total)} orders${d.total > d.count ? ` (latest ${n(d.count)} shown)` : ""}</p>` + (d.count ? `
      <div class="table-wrap"><table><thead><tr><th>Order</th><th>Placed (customer time)</th><th>Customer</th><th>Ship to</th><th>From</th><th>Status</th><th>Carrier</th>${m ? '<th class="num">Total</th>' : ""}</tr></thead><tbody>
      ${d.results.map((o) => `<tr class="clickable" data-id="${esc(o.order_id)}" tabindex="0"><td class="pn">${esc(o.order_id)}</td><td class="small">${esc((o.ordered_at_local || "").replace("T", " "))}</td>
        <td>${c ? esc(o.customer_name) : esc(o.customer_id)}<div class="muted small">${esc(o.customer_type)}, ${esc(o.order_type)}</div></td>
        <td>${esc([o.ship_to_city, o.ship_to_state].filter(Boolean).join(", ") || "")}<div class="muted small">${esc(o.ship_to_country)}</div></td><td>${esc(o.fulfillment_warehouse)}</td>
        <td>${orderStatus(o.status)}${o.customs_status && o.customs_status.startsWith("Held") ? '<div><span class="status warn">Customs hold</span></div>' : ""}</td>
        <td class="small">${esc(o.carrier_service)}</td>${m ? `<td class="num">${money(o.total_due_local, o.billing_currency)}</td>` : ""}</tr>`).join("")}
      </tbody></table></div>` : '<p class="empty">No orders match. Check the number, or widen the date range.</p>');
  };
  $("#ord-seg").onclick = (e) => { const b = e.target.closest("button"); if (!b) return; st.days = b.dataset.v; $("#ord-seg").querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b)); run(); };
  f.onsubmit = (e) => { e.preventDefault(); run(); };
  $("#ord-results").onclick = (e) => { const tr = e.target.closest("tr[data-id]"); if (tr) orderDrawer(tr.dataset.id); };
  $("#ord-results").onkeydown = (e) => { const tr = e.target.closest("tr[data-id]"); if (tr && e.key === "Enter") { e.preventDefault(); orderDrawer(tr.dataset.id); } };
  run();
}

async function orderDrawer(id) {
  openDrawer(`<span class="pn" style="font-size:22px">${esc(id)}</span>`, '<p class="empty">Loading…</p>');
  let d;
  try { d = await api(`/api/orders/${encodeURIComponent(id)}`); } catch (e) { $("#drawer-body").innerHTML = `<p class="empty">${esc(e.message)}</p>`; return; }
  const o = d.order, cu = d.customer, m = S.emp.can_see_money;
  $("#drawer-body").innerHTML = `
    <section>${facts([["Status", orderStatus(o.status)], ["Type", esc(o.order_type)], ["Placed (customer time)", esc((o.ordered_at_local || "").replace("T", " "))],
      ["Channel", esc(o.channel)], ["Ships from", esc(o.fulfillment_warehouse)], ["Ship to", esc([o.ship_to_city, o.ship_to_state, o.ship_to_country].filter(Boolean).join(", "))]])}</section>
    <section><h3>Customer</h3>${facts([["Customer", S.emp.can_see_customer ? `${esc(cu.customer_name)} (${esc(cu.customer_id)})` : esc(cu.customer_id)], ["Type", esc(cu.customer_type)],
      ["Time zone", esc(cu.timezone)], ...(m ? [["Terms", esc(cu.payment_terms)], ["Billing currency", esc(cu.billing_currency)]] : []), ...(cu.franchise_make ? [["Franchise", esc(cu.franchise_make)]] : [])])}</section>
    <section><h3>Items</h3><div class="table-wrap"><table><thead><tr><th>Part</th><th>Bin</th><th class="num">Qty</th><th>Status</th><th>For vehicle</th>${m ? '<th class="num">Line total</th>' : ""}</tr></thead><tbody>
      ${d.lines.map((l) => `<tr><td><span class="pn">${esc(l.part_number)}</span><div class="small">${esc(l.part_name)}</div><div class="muted small">${esc(l.brand)}${l.core_status ? `, core ${esc(l.core_status.toLowerCase())}` : ""}</div></td>
        <td>${l.bin_location ? `<span class="bin">${esc(l.bin_location)}</span>` : "—"}</td><td class="num">${n(l.quantity)}</td><td>${orderStatus(l.line_status)}</td><td class="small">${esc(l.for_vehicle)}</td>
        ${m ? `<td class="num">${money(l.line_total_local, l.currency)}</td>` : ""}</tr>`).join("")}</tbody></table></div></section>
    <section><h3>Shipping</h3>${facts([["Carrier", esc(o.carrier)], ["Service", esc(o.carrier_service)], ["Tracking", o.tracking_number ? `<span class="pn">${esc(o.tracking_number)}</span>` : "Not shipped yet"],
      ["Shipped", dt(o.shipped_at_utc)], ["Delivered (customer time)", esc((o.delivered_at_local || "—").replace("T", " "))],
      ...(o.order_type === "International" ? [["Customs", esc(o.customs_status)], ["Incoterm", esc(o.incoterm)], ["Import tax paid by", esc(o.import_tax_paid_by)], ["Export documents", esc(o.export_documents)]] : []),
      ...(has(o, "carrier_cost_usd") ? [["Our carrier cost (est.)", usd(o.carrier_cost_usd)], ["Shipping margin", usd(o.shipping_margin_usd)]] : [])])}</section>
    ${m ? `<section><h3>Money</h3>${facts([["Currency", esc(o.billing_currency)], ["Goods", money(o.goods_total_local, o.billing_currency)], ["Shipping", money(o.shipping_local, o.billing_currency)],
      ...(o.import_tax_name ? [[`${o.import_tax_name} (${o.import_tax_pct}%)`, money(o.import_tax_local, o.billing_currency)]] : []), ["Total due", `<b>${money(o.total_due_local, o.billing_currency)}</b>`],
      ["In USD at order rate", usd(o.order_total_usd)], ...(o.billing_currency !== "USD" ? [["Rate used", `${n(o.fx_rate_units_per_usd, 4)} per USD on ${esc(o.fx_rate_date)}`]] : []),
      ["Payment", esc(o.payment_status)], ["Paid", dt(o.paid_at_utc)], ...(has(o, "fx_gain_loss_usd") && o.billing_currency !== "USD" ? [["FX gain/loss", usd(o.fx_gain_loss_usd)]] : [])])}</section>` : lockNote("Pricing and payment")}
    <section><h3>Support cases</h3>${d.support_cases.length ? `<ul>${d.support_cases.map((c) => `<li><b>${esc(c.case_id)}</b> ${esc(c.contact_reason)}, ${esc(c.status)}</li>`).join("")}</ul>` : '<p class="muted small">None for this order.</p>'}</section>`;
}

/* ------------------------------------------------------------------ support cases */
async function viewCases() {
  const st = { status: "active", department: "", q: "" };
  $("#main").innerHTML = intro() + `
    <form class="filters" id="case-form">
      <label class="field grow"><span>Case, order or customer</span><input name="q" type="search" placeholder="e.g. CS-001180, SO-031950"></label>
      <label class="field"><span>Team</span><select name="department">${opt("", "All teams")}${S.meta.departments.map((d) => opt(d.department_id, d.department_name)).join("")}</select></label>
      <div class="field"><span>Status</span><div class="seg" id="case-seg">${[["active", "Needs attention"], ["Queued (after hours)", "Queued after hours"], ["Resolved", "Resolved"], ["", "All"]].map(([v, l]) => `<button type="button" data-v="${v}" aria-pressed="${st.status === v}">${l}</button>`).join("")}</div></div>
      <button class="btn" type="submit">Search</button>
    </form><div id="case-results"></div>`;
  const f = $("#case-form");
  const run = async () => {
    Object.assign(st, { q: f.q.value, department: f.department.value });
    const d = await api(`/api/cases?${qs(st)}`);
    $("#case-results").innerHTML = `<p class="result-count">${n(d.count)} cases</p>` + (d.count ? `<div class="table-wrap"><table><thead><tr><th>Case</th><th>Opened (customer time)</th><th>Customer</th><th>Reason</th><th>Team</th><th>Came in by</th><th>Language</th><th>Status</th><th>Assigned</th></tr></thead><tbody>
      ${d.results.map((c) => `<tr class="clickable" data-id="${esc(c.case_id)}"><td class="pn">${esc(c.case_id)}</td><td class="small">${esc((c.opened_at_customer_local || "").replace("T", " "))}</td>
        <td>${esc(c.customer_name || c.customer_id)}<div class="muted small">${esc(c.customer_type)}</div></td><td>${esc(c.contact_reason)}${c.order_id ? `<div class="muted small">${esc(c.order_id)}</div>` : ""}</td>
        <td>${esc(c.department_name)}</td><td class="small">${esc(c.channel)}${c.ai_handoff_reason ? `<div class="muted">${esc(c.ai_handoff_reason)}</div>` : ""}</td><td>${esc(c.language)}</td>
        <td><span class="status ${c.status === "Resolved" ? "good" : c.status.startsWith("Queued") ? "warn" : "info"}">${esc(c.status)}</span></td><td class="small">${esc(c.assigned_name || "Unassigned")}</td></tr>`).join("")}
      </tbody></table></div>` : '<p class="empty">No cases match.</p>');
    $("#case-results").onclick = (e) => {
      const tr = e.target.closest("tr[data-id]"); if (!tr) return;
      const c = d.results.find((x) => x.case_id === tr.dataset.id);
      openDrawer(`<span class="pn" style="font-size:22px">${esc(c.case_id)}</span>`, `<section>${facts([["Status", esc(c.status)], ["Team", esc(c.department_name)], ["Reason", esc(c.contact_reason)],
        ["Customer", esc(c.customer_name || c.customer_id)], ["Order", esc(c.order_id || "None")], ["Came in by", esc(c.channel)], ["Why the chat handed off", esc(c.ai_handoff_reason || "—")],
        ["Opened (customer time)", esc((c.opened_at_customer_local || "").replace("T", " "))], ["Opened (St. Louis time)", esc((c.opened_at_hq_local || "").replace("T", " "))],
        ["After hours", c.opened_after_hours ? "Yes" : "No"], ["Language", esc(c.language)], ["Priority", esc(c.priority)], ["Assigned to", esc(c.assigned_name || "Unassigned")],
        ["First response", c.first_response_minutes != null ? `${n(c.first_response_minutes)} min` : "Waiting"], ["Resolved", dt(c.resolved_at_utc)]])}</section>
        ${c.notes ? `<section><h3>Notes</h3><p>${esc(c.notes)}</p></section>` : ""}`);
    };
  };
  $("#case-seg").onclick = (e) => { const b = e.target.closest("button"); if (!b) return; st.status = b.dataset.v; $("#case-seg").querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b)); run(); };
  f.onsubmit = (e) => { e.preventDefault(); run(); };
  run();
}

/* ------------------------------------------------------------------ assistant */
const TOOL_LABEL = { search_inventory: "inventory search", get_part_details: "part details", find_in_transit: "inbound shipments", search_orders: "order search",
  get_order: "order details", get_part_price: "part price", quote_shipping: "shipping rates", full_quote: "customer total", list_support_cases: "support cases",
  analytics_summary: "analytics", search_faq: "FAQ", contact_team: "team contacts", escalate_to_person: "handoff to a person", propose_support_case: "new support case" };

function md(text) {
  const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, '<span class="pn">$1</span>')
    .replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/(^|[\s(])(https?:\/\/[^\s)<]+)/g, '$1<a href="$2" target="_blank" rel="noopener">$2</a>');
  const lines = String(text || "").split("\n"); const out = []; let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (/^\s*\|/.test(l)) {
      const rows = []; while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(lines[i++]);
      const cells = (r) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      const body = rows.filter((r) => !/^\s*\|?\s*:?-{2,}/.test(r));
      out.push(`<div class="table-wrap"><table><thead><tr>${cells(body[0]).map((c) => `<th>${inline(c)}</th>`).join("")}</tr></thead><tbody>${body.slice(1).map((r) => `<tr>${cells(r).map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
      continue;
    }
    if (/^\s*([-*]|\d+\.)\s+/.test(l)) {
      const items = []; const ordered = /^\s*\d+\./.test(l);
      while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) items.push(lines[i++].replace(/^\s*([-*]|\d+\.)\s+/, ""));
      out.push(`<${ordered ? "ol" : "ul"}>${items.map((x) => `<li>${inline(x)}</li>`).join("")}</${ordered ? "ol" : "ul"}>`);
      continue;
    }
    if (/^#{1,4}\s/.test(l)) { out.push(`<p><b>${inline(l.replace(/^#+\s/, ""))}</b></p>`); i++; continue; }
    if (l.trim()) { const para = []; while (i < lines.length && lines[i].trim() && !/^\s*(\||[-*]\s|\d+\.\s|#)/.test(lines[i])) para.push(lines[i++]); out.push(`<p>${para.map(inline).join("<br>")}</p>`); continue; }
    i++;
  }
  return out.join("");
}

function handoffCard(h) {
  const c = h.contact;
  return `<div class="handoff"><h4>${esc(c.department)}</h4>
    <div>${esc(c.phone)}, <a href="mailto:${esc(c.email)}">${esc(c.email)}</a></div>
    <div class="small">${c.open_now ? `<span class="status good">&#10003; Open now</span> until ${esc(c.closes_at)}` : `<span class="status warn">&#9679; Closed</span> opens ${esc(c.next_open)}`}</div>
    <div class="small muted">Languages: ${esc(c.languages)}</div>
    ${h.faq_suggestions && h.faq_suggestions.length ? `<div class="small" style="margin-top:6px">FAQ: ${h.faq_suggestions.map((f) => `<a href="${esc(f.url)}" target="_blank" rel="noopener">${esc(f.question)}</a>`).join(", ")}</div>` : ""}
    <div class="small"><a href="${esc(c.faq_page)}" target="_blank" rel="noopener">Full FAQ page</a></div></div>`;
}

/* A case the assistant prepared. Nothing is saved until the employee clicks Create case. */
function caseCard(c, i) {
  const facts = `<div class="small">${esc(c.customer_name || c.customer_id)} (${esc(c.customer_id)})${c.order_id ? `, order ${esc(c.order_id)}` : ""}</div>
    <div>${esc(c.contact_reason)}</div>${c.notes ? `<div class="small muted">${esc(c.notes)}</div>` : ""}`;
  if (c.created) return `<div class="handoff"><h4>Support case ${esc(c.created.case_id)} created</h4>${facts}
    <div class="small"><span class="status good">&#10003; ${esc(c.created.status)}</span> ${esc(c.created.department)}, ${esc(c.created.phone)}</div></div>`;
  if (c.cancelled) return `<div class="handoff"><h4>Case not created</h4>${facts}</div>`;
  return `<div class="handoff"><h4>New support case for ${esc(c.department)}</h4>${facts}
    <div class="small muted" style="margin:4px 0 8px">Not saved yet. Check the details, then create it.</div>
    ${c.error ? `<p class="small" role="alert">${esc(c.error)}</p>` : ""}
    <button class="btn small" type="button" data-case-create="${i}">Create case</button>
    <button class="btn ghost small" type="button" data-case-cancel="${i}">Cancel</button></div>`;
}

function renderChat() {
  const log = $("#chat-log");
  log.innerHTML = S.chat.length ? S.chat.map((m, i) => m.role === "user" ? `<div class="msg user">${esc(m.content)}</div>` : `<div class="msg bot"><div class="who">Assistant</div>${md(m.content)}
    ${m.tools && m.tools.length ? `<div class="lookups">${[...new Set(m.tools.map((t) => TOOL_LABEL[t.tool] || t.tool))].map((t) => `<span>Checked ${esc(t)}</span>`).join("")}</div>` : ""}
    ${m.handoff ? handoffCard(m.handoff) : ""}${m.pending_case ? caseCard(m.pending_case, i) : ""}</div>`).join("")
    : `<div class="msg bot"><div class="who">Assistant</div><p>Hi ${esc(S.emp.name.split(" ")[0])}. Ask me about parts, stock, orders, shipping costs or company policy. I look everything up in company data, and if I can't answer I'll tell you who can.</p></div>`;
  log.scrollTop = log.scrollHeight;
}

function renderDemo(d) {
  const el = $("#demo-note"); if (!el) return;
  S.demo = d;
  if (!d || !d.enabled) { el.hidden = true; return; }
  el.hidden = false;
  const left = d.remaining;
  el.className = `demo-note ${left === 0 ? "out" : ""}`;
  el.innerHTML = left > 0
    ? `<b>Demo version.</b> You have ${left} of ${d.limit} assistant questions left.`
    : `<b>Demo version.</b> You've used all ${d.limit} assistant questions. The other tabs still work.`;
  const f = $("#chat-form");
  if (f) { f.m.disabled = left === 0; f.querySelector("button").disabled = left === 0; if (left === 0) f.m.placeholder = "The demo question limit has been reached."; }
  document.querySelectorAll(".suggestion").forEach((b) => { b.disabled = left === 0; });
}

async function viewAssistant() {
  $("#main").innerHTML = intro() + `<p id="demo-note" class="demo-note" hidden></p><div class="chat"><div class="chat-col"><div class="chat-log" id="chat-log" aria-live="polite"></div>
    <form class="chat-input" id="chat-form"><textarea name="m" rows="2" placeholder="Ask a question, e.g. Do we have rear rotors for a 2020 RAV4 in Dallas?" aria-label="Your question"></textarea>
    <button class="btn" type="submit">Send</button></form></div>
    <div class="chat-side"><h3>Try asking</h3><div id="sugg"></div>
      <button class="btn ghost small" id="chat-clear" type="button">Start a new conversation</button>
      <p class="small muted">Answers are based on company data as of the time shown in the menu. Shipping rates are estimates.</p></div></div>`;
  renderChat();
  const f = $("#chat-form");
  const send = async (text) => {
    text = text.trim(); if (!text) return;
    S.chat.push({ role: "user", content: text }); renderChat();
    f.m.value = ""; f.querySelector("button").disabled = true;
    $("#chat-log").insertAdjacentHTML("beforeend", '<div class="msg bot typing" id="typing">Looking that up…</div>');
    try {
      const r = await api("/api/chat", { method: "POST", body: { messages: S.chat.map(({ role, content }) => ({ role, content })) } });
      S.chat.push({ role: "assistant", content: r.reply || "I couldn't find an answer.", tools: r.tools_used, handoff: r.handoff,
                    pending_case: r.pending_case });
      if (r.demo) renderDemo(r.demo);
    } catch (e) {
      if (e.status === 429) { S.chat.push({ role: "assistant", content: e.message }); renderDemo(e.data && e.data.demo); }
      else S.chat.push({ role: "assistant", content: `Something went wrong: ${e.message}. Try again, or call Customer Service at (800) 555-0142.` });
    }
    sessionStorage.setItem("gw_chat", JSON.stringify(S.chat));
    f.querySelector("button").disabled = !!(S.demo && S.demo.enabled && S.demo.remaining === 0);
    renderChat(); if (!f.m.disabled) f.m.focus();
  };
  f.onsubmit = (e) => { e.preventDefault(); send(f.m.value); };
  f.m.onkeydown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(f.m.value); } };
  $("#chat-clear").onclick = () => { S.chat = []; sessionStorage.removeItem("gw_chat"); renderChat(); };
  $("#chat-log").onclick = async (e) => {
    const b = e.target.closest("[data-case-create], [data-case-cancel]"); if (!b) return;
    const c = S.chat[Number(b.dataset.caseCreate ?? b.dataset.caseCancel)].pending_case;
    if (b.dataset.caseCancel !== undefined) c.cancelled = true;
    else {
      b.disabled = true;
      try { c.created = await api("/api/cases/confirm", { method: "POST", body: { proposal_id: c.proposal_id } }); c.error = null; }
      catch (err) { c.error = err.message; }
    }
    sessionStorage.setItem("gw_chat", JSON.stringify(S.chat));
    renderChat();
  };
  const s = await api("/api/assistant/suggestions");
  $("#sugg").innerHTML = s.suggestions.map((x) => `<button class="suggestion" type="button">${esc(x)}</button>`).join("");
  renderDemo(await api("/api/demo-status"));
  $("#sugg").onclick = (e) => { const b = e.target.closest(".suggestion"); if (b) send(b.textContent); };
}

/* ------------------------------------------------------------------ analytics */
const cssVar = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
function chart(id, cfg) {
  const el = document.getElementById(id); if (!el || !window.Chart) return;
  const ink2 = cssVar("--ink-2"), rule = cssVar("--rule");
  Chart.defaults.font.family = '"Public Sans", system-ui, sans-serif';
  Chart.defaults.color = ink2;
  const base = { responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
    plugins: { legend: { display: cfg.data.datasets.length > 1, position: "top", align: "start", labels: { boxWidth: 12, boxHeight: 12, useBorderRadius: true, borderRadius: 3 } },
      tooltip: { callbacks: cfg.money ? { label: (c) => `${c.dataset.label}: ${usd(c.parsed[cfg.horizontal ? "x" : "y"], 0)}` } : {} } },
    scales: { x: { grid: { display: !!cfg.horizontal, color: rule }, ticks: { maxRotation: 0, autoSkipPadding: 12 } },
      y: { grid: { display: !cfg.horizontal, color: rule }, border: { display: false }, ticks: {} } } };
  if (cfg.money) base.scales[cfg.horizontal ? "x" : "y"].ticks.callback = (v) => usd(v, 0);
  const room = (cfg.horizontal ? el.clientHeight : el.clientWidth) / Math.max(cfg.data.labels.length, 1);
  if (cfg.data.labels.length <= 12 && room >= (cfg.horizontal ? 18 : 52)) base.scales[cfg.horizontal ? "y" : "x"].ticks.autoSkip = false;
  if (cfg.stacked) { base.scales.x.stacked = true; base.scales.y.stacked = true; }
  if (cfg.horizontal) base.indexAxis = "y";
  cfg.data.datasets.forEach((ds) => Object.assign(ds, { borderRadius: 4, borderSkipped: "start", maxBarThickness: 34 }, cfg.stacked ? { borderColor: cssVar("--surface"), borderWidth: { top: 2 } } : {}));
  const c = new Chart(el, { type: cfg.type || "bar", data: cfg.data, options: base });
  if (!cfg.own) S.charts.push(c);                 // dashboard charts are destroyed together on reload
  return c;
}
const tableView = (rows, cols) => `<details><summary>Show as table</summary><div class="table-wrap" style="margin-top:6px"><table><thead><tr>${cols.map(([, l, num]) => `<th class="${num ? "num" : ""}">${esc(l)}</th>`).join("")}</tr></thead><tbody>
  ${rows.map((r) => `<tr>${cols.map(([k, , num, f]) => `<td class="${num ? "num" : ""}">${f ? f(r[k]) : num ? n(r[k]) : esc(r[k])}</td>`).join("")}</tr>`).join("")}</tbody></table></div></details>`;

async function viewAnalytics() {
  const st = { period: "90", warehouse: "", category: "", ...JSON.parse(sessionStorage.getItem("gw_an") || "null") };
  $("#main").innerHTML = intro() + `<div class="filters" id="an-filters">
      <div class="field"><span>Sales period</span><div class="seg" id="an-seg">${[["30", "30 days"], ["90", "90 days"], ["365", "12 months"], ["all", "All time"]].map(([v, l]) => `<button type="button" data-v="${v}" aria-pressed="${st.period === v}">${l}</button>`).join("")}</div></div>
      <label class="field"><span>Warehouse</span><select id="an-wh"></select></label>
      <label class="field"><span>Category</span><select id="an-cat">${opt("", "All categories", st.category)}${S.meta.categories.map((c) => opt(c, c, st.category)).join("")}</select></label>
      <p class="small muted" id="an-scope" style="margin:0 0 6px auto"></p></div><div id="an-body"><p class="empty">Loading…</p></div>`;
  const load = async () => {
    sessionStorage.setItem("gw_an", JSON.stringify(st));
    S.charts.forEach((c) => c.destroy()); S.charts = [];
    const d = await api(`/api/analytics?${qs(st)}`);
    $("#an-wh").innerHTML = opt("", d.warehouses.length > 1 ? (S.emp.scope === "Company" ? "All warehouses" : `All in ${S.emp.scope_label.toLowerCase()}`) : d.warehouses[0], st.warehouse) + (d.warehouses.length > 1 ? d.warehouses.map((w) => opt(w, w, st.warehouse)).join("") : "");
    $("#an-scope").textContent = `Your view: ${d.scope}. Data as of ${d.as_of}.`;
    const k = d.kpis, cost = has(k, "stock_value_usd"), split = !d.note;   // split = shipping and FX can be shown
    const period = { 30: "last 30 days", 90: "last 90 days", 365: "last 12 months", all: "all time" }[st.period]
      + (st.category ? `, ${st.category} only` : "");
    const only = st.category ? `, ${esc(st.category)} only` : "";
    // Panels in reading order, laid out two per row. With a category selected, shipping panels are left out
    // (shipping is per order) and revenue by region takes their place.
    const panels = [
      `<div class="panel"><h3>Revenue by month</h3><p class="sub">Domestic and international, all time${only}. The last month is month to date.</p><div class="chart-box"><canvas id="c-sales"></canvas></div>
        ${tableView(d.sales_by_month, [["label", "Month"], ["domestic_revenue_usd", "Domestic", 1, (v) => usd(v, 0)], ["international_revenue_usd", "International", 1, (v) => usd(v, 0)], ["orders", "Orders", 1]])}</div>`,
      cost && split ? `<div class="panel"><h3>Shipping: what it cost vs. what we charged</h3><p class="sub">By month, all time (last month to date). The gap is shipping we absorb, mostly free shipping and dealer delivery.</p><div class="chart-box"><canvas id="c-ship-month"></canvas></div>
        ${tableView(d.sales_by_month, [["label", "Month"], ["carrier_cost_usd", "Carrier cost", 1, (v) => usd(v, 0)], ["shipping_usd", "Charged", 1, (v) => usd(v, 0)]])}</div>` : "",
      !cost || !split ? `<div class="panel"><h3>Revenue by region</h3><p class="sub">${esc(period)}</p><div class="chart-box"><canvas id="c-region"></canvas></div>
        ${tableView(d.revenue_by_region, [["label", "Region"], ["orders", "Orders", 1], ["revenue_usd", "Revenue", 1, (v) => usd(v, 0)]])}</div>` : "",
      split ? `<div class="panel"><h3>Shipping cost by carrier</h3><p class="sub">${cost ? "Average carrier cost per order" : "Average shipping charged per order"}, ${esc(period)}</p><div class="chart-box"><canvas id="c-carrier"></canvas></div>
        ${tableView(d.shipping_by_carrier, [["label", "Carrier"], ["orders", "Orders", 1], ...(cost ? [["avg_carrier_cost_usd", "Avg cost", 1, (v) => usd(v)], ["cost_pct_of_revenue", "% of revenue", 1, (v) => `${v}%`]] : []), ["avg_charged_usd", "Avg charged", 1, (v) => usd(v)]])}</div>` : "",
      `<div class="panel"><h3>Average list price by category</h3><p class="sub">OEM, Premium and Value parts</p><div class="chart-box"><canvas id="c-price"></canvas></div>
        ${tableView(d.price_by_group, [["label", "Category"], ["oem_avg_price_usd", "OEM", 1, (v) => usd(v)], ["premium_avg_price_usd", "Premium", 1, (v) => usd(v)], ["value_avg_price_usd", "Value", 1, (v) => usd(v)], ...(cost ? [["avg_cost_pct_of_list", "Cost % of list", 1, (v) => `${v}%`]] : [])])}</div>`,
      `<div class="panel"><h3>Units on hand by category</h3><p class="sub">Right now${only}</p><div class="chart-box"><canvas id="c-inv-group"></canvas></div>
        ${tableView(d.inventory_by_group, [["label", "Category"], ["units", "On hand", 1], ["available", "Available", 1], ...(cost ? [["stock_value_usd", "Value", 1, (v) => usd(v, 0)]] : [])])}</div>`,
      `<div class="panel"><h3>Units on hand by warehouse</h3><p class="sub">Right now${only}, with units missing in the table</p><div class="chart-box"><canvas id="c-inv-wh"></canvas></div>
        ${tableView(d.inventory_by_warehouse, [["label", "Warehouse"], ["units", "On hand", 1], ["in_transit", "In transit", 1], ["missing", "Missing", 1], ["needs_reorder", "Low-stock parts", 1], ...(cost ? [["stock_value_usd", "Value", 1, (v) => usd(v, 0)]] : [])])}</div>`,
      `<div class="panel"><h3>How long stock has sat</h3><p class="sub">Units by days since last sale or receipt${only}</p><div class="chart-box"><canvas id="c-aging"></canvas></div>
        ${tableView(d.stock_aging, [["label", "Age"], ["units", "Units", 1], ...(cost ? [["stock_value_usd", "Value", 1, (v) => usd(v, 0)]] : [])])}</div>`,
      `<div class="panel"><h3>Revenue by category</h3><p class="sub">${esc(period)}</p><div class="chart-box"><canvas id="c-sales-group"></canvas></div>
        ${tableView(d.sales_by_group, [["label", "Category"], ["units", "Units", 1], ["revenue_usd", "Revenue", 1, (v) => usd(v, 0)]])}</div>`,
    ].filter(Boolean);
    const kpi = (v, l, s = "") => `<div class="kpi"><div class="v">${v}</div><div class="l">${esc(l)}</div>${s ? `<div class="s">${esc(s)}</div>` : ""}</div>`;
    $("#an-body").innerHTML = `
      <div class="kpis">
        ${kpi(n(k.units_on_hand), "Units on hand", `${n(k.skus_stocked)} parts stocked`)}
        ${cost ? kpi(usd(k.stock_value_usd, 0), "Inventory value", "at our cost") : ""}
        ${kpi(n(k.units_in_transit), "Units in transit")}
        ${kpi(n(k.skus_needing_reorder), "Low stock", `${n(k.skus_out_of_stock)} out of stock with demand`)}
        ${kpi(n(k.units_missing), "Units missing", cost ? `${usd(k.missing_value_usd, 0)} at cost` : "under review")}
        ${kpi(usd(k.revenue_usd, 0), "Revenue", `${n(k.orders)} orders, ${period}`)}
        ${kpi(n(k.units_sold), "Units sold", `${k.international_revenue_pct ?? 0}% of revenue international`)}
        ${cost && split ? kpi(`${k.shipping_cost_pct_of_revenue ?? 0}%`, "Shipping cost of revenue", `${usd(k.carrier_cost_usd, 0)} paid, ${usd(k.shipping_usd, 0)} charged`) : ""}
        ${cost && split ? kpi(usd(k.fx_gain_loss_usd, 0), "Exchange gain/loss", "realized on paid invoices") : ""}
      </div>
      ${!split ? `<p class="lock" style="margin:0 0 16px">${esc(d.note)}</p>` : ""}
      ${panels.map((x, i) => (i % 2 ? "" : `<div class="grid2">${x}${panels[i + 1] || ""}</div>`)).join("")}
      <div class="panel" style="margin-bottom:16px"><h3>Low stock to reorder</h3><p class="sub">Parts at or below their reorder point, backorders first${only}. Select a part for its details.</p>
        <div class="table-wrap"><table><thead><tr><th>Part</th><th>Warehouse</th><th class="num">Available</th><th class="num">Reorder at</th><th class="num">In transit</th><th class="num">Backordered</th><th class="num">Days of cover</th></tr></thead><tbody>
        ${d.low_stock.map((r) => `<tr class="clickable" data-pn="${esc(r.part_number)}" tabindex="0"><td><span class="pn">${esc(r.part_number)}</span> <span class="small">${esc(r.part_name)}</span><div class="muted small">${esc(r.fits_summary)}</div></td><td>${esc(r.warehouse_code)}</td>
          <td class="num">${n(r.qty_available)}</td><td class="num">${n(r.reorder_point)}</td><td class="num">${n(r.qty_in_transit)}</td><td class="num">${r.qty_backordered ? `<span class="status warn">${n(r.qty_backordered)}</span>` : "0"}</td><td class="num">${n(r.days_of_cover, 1)}</td></tr>`).join("") || '<tr><td colspan="7" class="empty">Nothing below its reorder point.</td></tr>'}
        </tbody></table></div></div>
      <div class="grid2">
        <div class="panel"><h3>Top parts by revenue</h3><p class="sub">${esc(period)}. Select a part for its details.</p><div class="table-wrap"><table><thead><tr><th>Part</th><th class="num">Units</th><th class="num">Revenue</th></tr></thead><tbody>
          ${d.top_parts.map((r) => `<tr class="clickable" data-pn="${esc(r.part_number)}" tabindex="0"><td><span class="pn">${esc(r.part_number)}</span> <span class="small">${esc(r.part_name)}</span><div class="muted small">${esc(r.fits_summary)}</div></td><td class="num">${n(r.units)}</td><td class="num">${usd(r.revenue_usd, 0)}</td></tr>`).join("")}
          </tbody></table></div></div>
        <div class="panel"><h3>International sales by country</h3><p class="sub">${esc(period)}, billed in each customer's currency</p><div class="table-wrap"><table><thead><tr><th>Country</th><th class="num">Orders</th><th class="num">Billed</th><th class="num">In USD</th>${cost && split ? '<th class="num">FX gain/loss</th>' : ""}</tr></thead><tbody>
          ${d.revenue_by_country.map((r) => `<tr><td>${esc(r.label)}</td><td class="num">${n(r.orders)}</td><td class="num" style="white-space:nowrap">${money(r.billed_local, r.currency)}</td><td class="num">${usd(r.revenue_usd, 0)}</td>${cost && split ? `<td class="num">${usd(r.fx_gain_loss_usd, 0)}</td>` : ""}</tr>`).join("") || '<tr><td colspan="5" class="empty">No international orders in this view.</td></tr>'}
          </tbody></table></div></div>
      </div>`;
    const s1 = cssVar("--series-1"), s2 = cssVar("--series-2"), s3 = cssVar("--series-3");
    const L = (rows) => rows.map((r) => (/^\d{4}-\d{2}$/.test(r.label) ? monthLabel(r.label) : r.label));
    chart("c-sales", { stacked: true, money: true, data: { labels: L(d.sales_by_month), datasets: [
      { label: "Domestic", data: d.sales_by_month.map((r) => r.domestic_revenue_usd), backgroundColor: s1 },
      { label: "International", data: d.sales_by_month.map((r) => r.international_revenue_usd), backgroundColor: s2 }] } });
    if (cost && split) chart("c-ship-month", { type: "line", money: true, data: { labels: L(d.sales_by_month), datasets: [
      { label: "Carrier cost", data: d.sales_by_month.map((r) => r.carrier_cost_usd), borderColor: s2, backgroundColor: s2, borderWidth: 2, pointRadius: 0, pointHoverRadius: 5 },
      { label: "Charged to customers", data: d.sales_by_month.map((r) => r.shipping_usd), borderColor: s1, backgroundColor: s1, borderWidth: 2, pointRadius: 0, pointHoverRadius: 5 }] } });
    if (!cost || !split) chart("c-region", { horizontal: true, money: true, data: { labels: L(d.revenue_by_region), datasets: [{ label: "Revenue", data: d.revenue_by_region.map((r) => r.revenue_usd), backgroundColor: s1 }] } });
    if (split) chart("c-carrier", { horizontal: true, money: true, data: { labels: L(d.shipping_by_carrier), datasets: [{ label: cost ? "Avg carrier cost" : "Avg charged", data: d.shipping_by_carrier.map((r) => cost ? r.avg_carrier_cost_usd : r.avg_charged_usd), backgroundColor: s1 }] } });
    chart("c-price", { money: true, data: { labels: L(d.price_by_group), datasets: [
      { label: "OEM", data: d.price_by_group.map((r) => r.oem_avg_price_usd), backgroundColor: s1 },
      { label: "Premium", data: d.price_by_group.map((r) => r.premium_avg_price_usd), backgroundColor: s2 },
      { label: "Value", data: d.price_by_group.map((r) => r.value_avg_price_usd), backgroundColor: s3 }] } });
    chart("c-inv-group", { horizontal: true, data: { labels: L(d.inventory_by_group), datasets: [{ label: "Units on hand", data: d.inventory_by_group.map((r) => r.units), backgroundColor: s1 }] } });
    chart("c-inv-wh", { data: { labels: L(d.inventory_by_warehouse), datasets: [{ label: "Units on hand", data: d.inventory_by_warehouse.map((r) => r.units), backgroundColor: s1 }] } });
    chart("c-aging", { data: { labels: L(d.stock_aging), datasets: [{ label: "Units", data: d.stock_aging.map((r) => r.units), backgroundColor: s1 }] } });
    chart("c-sales-group", { horizontal: true, money: true, data: { labels: L(d.sales_by_group), datasets: [{ label: "Revenue", data: d.sales_by_group.map((r) => r.revenue_usd), backgroundColor: s1 }] } });
  };
  $("#an-seg").onclick = (e) => { const b = e.target.closest("button"); if (!b) return; st.period = b.dataset.v; $("#an-seg").querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b)); load(); };
  $("#an-filters").onchange = (e) => {
    if (e.target.id === "an-wh") { st.warehouse = e.target.value; load(); }
    if (e.target.id === "an-cat") { st.category = e.target.value; load(); }
  };
  // Enter must not also "click" the drawer's Close button, which gets focus as the drawer opens
  const openPart = (e) => { const tr = e.target.closest("tr[data-pn]"); if (tr && (e.type === "click" || e.key === "Enter")) { e.preventDefault(); partDrawer(tr.dataset.pn); } };
  $("#an-body").onclick = openPart;
  $("#an-body").onkeydown = openPart;
  const wait = () => (window.Chart ? load() : setTimeout(wait, 50));
  wait();
}

boot();
