/* ==========================================================================
   Loan Default Risk Dashboard — shared app engine
   Global cross-filtering + drill-down panel + shared chart helpers.
   Every page loads: chart.js, matrix plugin, app.js, then its page script.
   ========================================================================== */

/* ---------- Global state ---------- */
const APP = {
    rows: [],                 // row-level records (loaded once)
    filtered: [],             // rows passing the global filter bar
    listeners: [],            // callbacks fired when filters change
    charts: [],               // live Chart instances (destroyed on re-render)
    filters: {
        home: "All", verif: "All", purpose: "All", term: "All", inc: "All",
        maxDti: 40, minFico: 600,
    },
};

const COLORS = { accent: "#4f8cff", good: "#2fbf8f", warn: "#f5b942", bad: "#ef5b6b", muted: "#93a0b8" };
const FICO_ORDER  = ["620-659 Fair", "660-699 Good", "700-739 Very Good", "740+ Excellent"];
const DTI_ORDER   = ["0-9 Low", "10-19 Moderate", "20-29 High", "30+ Very High"];
const INCOME_ORDER= ["<40k", "40-70k", "70-100k", "100-150k", "150k+"];
const RATE_ORDER  = ["<8%", "8-12%", "12-16%", "16%+"];

/* ---------- Formatting ---------- */
const fmtK = v => v >= 1000 ? (v / 1000).toFixed(1) + "k" : String(Math.round(v));
const fmtM = v => "$" + (v / 1e6).toFixed(1) + "M";
const fmtUSD = v => "$" + Math.round(v).toLocaleString("en-US");
const pct = v => (v * 100).toFixed(2) + "%";
const ratePill = r => r < 10 ? "lo" : r < 18 ? "mid" : "hi";

/* ---------- Boot ---------- */
async function bootApp(pageInit) {
    Chart.defaults.color = "#6e675a";          /* axis text — muted ink for paper theme */
    Chart.defaults.borderColor = "rgba(31,36,48,.12)";   /* hairline gridlines */
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    try {
        const res = await fetch("/api/records");   /* Flask API — streamed from SQLite */
        APP.rows = await res.json();
    } catch (e) {
        document.querySelector(".page").innerHTML =
            `<div class="kpi alert" style="grid-column:1/-1"><div class="label">Error</div>
             <div class="value" style="font-size:15px">Could not reach /api/records (${e})</div>
             <div class="note">Start the Flask app (python app.py); the API reads data/loans.db.</div></div>`;
        return;
    }
    buildFilterBar();
    applyFilters();
    pageInit();                       // page builds its static chrome / charts
    renderAll();                      // first data-driven render
}

/* ---------- Global filter bar ---------- */
function buildFilterBar() {
    const bar = document.getElementById("filterbar");
    if (!bar) return;
    const uniq = key => [...new Set(APP.rows.map(r => r[key]))].sort();
    const opts = (arr, allLabel) =>
        [`<option value="All">${allLabel}</option>`,
         ...arr.map(v => `<option value="${v}">${v}</option>`)].join("");
    // income bands in their natural (non-alphabetical) order
    const incOpts = INCOME_ORDER.filter(b => APP.rows.some(r => r.incB === b));

    bar.innerHTML = `
        <div class="f-group"><label>Home Ownership</label>
            <select id="fHome">${opts(uniq("home"), "All")}</select></div>
        <div class="f-group"><label>Verification</label>
            <select id="fVerif">${opts(uniq("verif"), "All")}</select></div>
        <div class="f-group"><label>Purpose</label>
            <select id="fPurpose">${opts(uniq("purpose"), "All")}</select></div>
        <div class="f-group"><label>Term</label>
            <select id="fTerm">${opts(uniq("term"), "All")}</select></div>
        <div class="f-group"><label>Income Band</label>
            <select id="fInc">${opts(incOpts, "All")}</select></div>
        <div class="f-group"><label>Min FICO <span class="range-val" id="vFico">600</span></label>
            <input type="range" id="fFico" min="600" max="830" step="10" value="600"></div>
        <div class="f-group"><label>Max DTI <span class="range-val" id="vDti">40</span></label>
            <input type="range" id="fDti" min="0" max="40" step="1" value="40"></div>
        <button class="btn danger" id="fReset">↺ Reset</button>
        <div class="hit-count"><b id="hitCount">0</b> loans in scope</div>`;

    const bind = (id, key, isNum) => {
        document.getElementById(id).addEventListener("input", e => {
            APP.filters[key] = isNum ? +e.target.value : e.target.value;
            if (isNum) document.getElementById(id.replace("f", "v")).textContent = e.target.value;
            applyFilters();
        });
    };
    bind("fHome", "home"); bind("fVerif", "verif"); bind("fPurpose", "purpose");
    bind("fTerm", "term"); bind("fInc", "inc");
    bind("fFico", "minFico", true); bind("fDti", "maxDti", true);

    document.getElementById("fReset").onclick = () => {
        APP.filters = { home: "All", verif: "All", purpose: "All", term: "All", inc: "All", maxDti: 40, minFico: 600 };
        ["fHome", "fVerif", "fPurpose", "fTerm", "fInc"].forEach(id => document.getElementById(id).value = "All");
        document.getElementById("fFico").value = 600; document.getElementById("vFico").textContent = "600";
        document.getElementById("fDti").value = 40;  document.getElementById("vDti").textContent = "40";
        applyFilters();
        toast("Filters reset");
    };
}

/* ---------- Filter application ---------- */
function applyFilters() {
    const f = APP.filters;
    APP.filtered = APP.rows.filter(r =>
        (f.home === "All" || r.home === f.home) &&
        (f.verif === "All" || r.verif === f.verif) &&
        (f.purpose === "All" || r.purpose === f.purpose) &&
        (f.term === "All" || r.term === f.term) &&
        (f.inc === "All" || r.incB === f.inc) &&
        r.fico >= f.minFico && r.dti <= f.maxDti
    );
    const el = document.getElementById("hitCount");
    if (el) el.textContent = APP.filtered.length.toLocaleString("en-US");
    renderAll();
}

function onFilterChange(fn) { APP.listeners.push(fn); }
function renderAll() { APP.listeners.forEach(fn => { try { fn(); } catch (e) { console.error(e); } }); }

/* ---------- Chart registry (destroy + rebuild on filter change) ---------- */
function makeChart(canvasId, config) {
    const existing = Chart.getChart(canvasId);
    if (existing) existing.destroy();
    const el = document.getElementById(canvasId);
    if (!el) return null;
    const c = new Chart(el, config);
    APP.charts.push(c);
    return c;
}

/* ---------- Aggregation helpers ---------- */
function groupBy(rows, keyFn) {
    const m = new Map();
    for (const r of rows) {
        const k = keyFn(r);
        if (!m.has(k)) m.set(k, { n: 0, defaults: 0, volume: 0, loss: 0, rateSum: 0, ficoSum: 0, dtiSum: 0, incSum: 0 });
        const g = m.get(k);
        g.n++; g.defaults += r.def; g.volume += r.amt; g.loss += r.loss;
        g.rateSum += r.rate; g.ficoSum += r.fico; g.dtiSum += r.dti; g.incSum += r.inc;
    }
    for (const g of m.values()) {
        g.defaultRate = g.n ? 100 * g.defaults / g.n : 0;
        g.avgRate = g.n ? g.rateSum / g.n : 0;
        g.avgFico = g.n ? g.ficoSum / g.n : 0;
        g.avgDti = g.n ? g.dtiSum / g.n : 0;
        g.avgInc = g.n ? g.incSum / g.n : 0;
    }
    return m;
}

function kpiCard(label, value, note, cls) {
    return `<div class="kpi ${cls || ""}"><div class="label">${label}</div>
            <div class="value">${value}</div><div class="note">${note}</div></div>`;
}

/* ---------- Portfolio KPIs from filtered rows ---------- */
function computeKpis(rows) {
    const n = rows.length;
    const defaults = rows.reduce((s, r) => s + r.def, 0);
    const volume = rows.reduce((s, r) => s + r.amt, 0);
    const loss = rows.reduce((s, r) => s + r.loss, 0);
    const avgRate = n ? rows.reduce((s, r) => s + r.rate, 0) / n : 0;
    const avgFico = n ? rows.reduce((s, r) => s + r.fico, 0) / n : 0;
    const avgDti = n ? rows.reduce((s, r) => s + r.dti, 0) / n : 0;
    const avgInc = n ? rows.reduce((s, r) => s + r.inc, 0) / n : 0;
    return { n, defaults, volume, loss, avgRate, avgFico, avgDti, avgInc, defaultRate: n ? 100 * defaults / n : 0 };
}

/* ---------- Standard chart configs ---------- */
function barConfig(labels, values, color, { horizontal = false, maxBar = 34, suffix = "%" } = {}) {
    const pctTicks = { callback: v => v + suffix };
    return {
        type: "bar",
        data: { labels, datasets: [{ data: values, backgroundColor: color, borderRadius: 6, maxBarThickness: maxBar }] },
        options: {
            indexAxis: horizontal ? "y" : "x",
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: horizontal ? { beginAtZero: true, ticks: pctTicks } : { ticks: { maxRotation: 30 } },
                y: horizontal ? { ticks: { autoSkip: false } } : { beginAtZero: true, ticks: pctTicks }
            }
        }
    };
}

/* Click-to-filter on categorical bar charts (cross-filtering) */
function enableClickFilter(chart, key) {
    if (!chart) return;
    const selectId = { home: "fHome", verif: "fVerif", purpose: "fPurpose", term: "fTerm", inc: "fInc" }[key];
    chart.options.onClick = (evt) => {
        const items = chart.getElementsAtEventForMode(evt, "nearest", { intersect: true }, true);
        if (!items.length) return;
        const label = chart.data.labels[items[0].index];
        const sel = document.getElementById(selectId);
        if (!sel) return;
        sel.value = (sel.value === label) ? "All" : label;   // toggle
        sel.dispatchEvent(new Event("input"));
        toast(`Filtered: ${key} = ${sel.value}`);
    };
    chart.options.plugins.tooltip = {
        ...chart.options.plugins.tooltip,
        callbacks: { afterLabel: () => "↳ click bar to filter" }
    };
}

/* Click-to-drill on charts whose dimension is not a global filter */
function enableClickDrill(chart, labelOf, rowsFor) {
    if (!chart) return;
    chart.options.onClick = (evt, elements, chart) => {
        if (!elements.length) return;
        const i = elements[0].index;
        openDrill(labelOf(i, chart), rowsFor(i, chart));
    };
    chart.options.plugins.tooltip = {
        ...chart.options.plugins.tooltip,
        callbacks: { afterLabel: () => "↳ click bar to inspect" }
    };
}

/* ---------- Drill-down side panel ---------- */
function openDrill(title, rows) {
    const k = computeKpis(rows);
    const homeMix = [...groupBy(rows, r => r.home).entries()]
        .sort((a, b) => b[1].n - a[1].n).slice(0, 3)
        .map(([h, g]) => `${h} ${((100 * g.n / k.n) || 0).toFixed(0)}%`).join(" · ");
    const purposeWorst = [...groupBy(rows, r => r.purpose).entries()]
        .sort((a, b) => b[1].defaultRate - a[1].defaultRate)[0];

    document.getElementById("drillTitle").textContent = title;
    document.getElementById("drillBody").innerHTML = `
        <div class="stat-line"><span>Loans</span><span>${k.n.toLocaleString("en-US")}</span></div>
        <div class="stat-line"><span>Defaulted</span><span>${k.defaults.toLocaleString("en-US")}</span></div>
        <div class="stat-line"><span>Default rate</span>
            <span class="pill ${ratePill(k.defaultRate)}">${k.defaultRate.toFixed(2)}%</span></div>
        <div class="stat-line"><span>Volume</span><span>${fmtM(k.volume)}</span></div>
        <div class="stat-line"><span>Est. loss @ default</span><span style="color:var(--bad)">${fmtM(k.loss)}</span></div>
        <div class="stat-line"><span>Avg interest rate</span><span>${k.avgRate.toFixed(2)}%</span></div>
        <div class="stat-line"><span>Avg FICO</span><span>${Math.round(k.avgFico)}</span></div>
        <div class="stat-line"><span>Avg DTI</span><span>${k.avgDti.toFixed(1)}</span></div>
        <div class="mini-note"><b style="color:var(--ink)">Mix:</b> ${homeMix || "—"}<br>
            <b style="color:var(--ink)">Riskiest purpose here:</b>
            ${purposeWorst ? `${purposeWorst[0]} (${purposeWorst[1].defaultRate.toFixed(1)}% default)` : "—"}</div>
        <canvas id="drillChart" style="margin-top:16px"></canvas>`;
    document.getElementById("drillPanel").classList.add("open");
    document.getElementById("drillOverlay").classList.add("show");

    // mini distribution: default rate by FICO band within selection
    const bands = FICO_ORDER.map(b => [b, groupBy(rows.filter(r => r.ficoB === b), () => "x").get("x")])
        .filter(([, g]) => g && g.n > 20);
    const dc = document.getElementById("drillChart");
    dc.style.height = "180px";
    dc.parentElement.style.position = "relative";
    new Chart(dc, {
        type: "bar",
        data: {
            labels: bands.map(([b]) => b),
            datasets: [{ data: bands.map(([, g]) => g.defaultRate),
                backgroundColor: COLORS.accent, borderRadius: 5, maxBarThickness: 30 }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false }, title: { display: true, text: "Default % by FICO band (selection)" } },
            scales: { y: { beginAtZero: true, ticks: { callback: v => v + "%" } } }
        }
    });
}
function closeDrill() {
    document.getElementById("drillPanel").classList.remove("open");
    document.getElementById("drillOverlay").classList.remove("show");
}

/* ---------- Toast ---------- */
let toastTimer;
function toast(msg) {
    let el = document.querySelector(".toast");
    if (!el) { el = document.createElement("div"); el.className = "toast"; document.body.appendChild(el); }
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("show"), 2200);
}

/* ---------- Nav helper: active tab ---------- */
function setActiveTab() {
    const page = document.body.dataset.page;
    document.querySelectorAll(".nav a.tab").forEach(a => {
        a.classList.toggle("active", a.dataset.page === page);
    });
}
