/* Axios Famiglia - pannello per la barra laterale di Home Assistant
 *
 * Elemento personalizzato senza dipendenze: legge le entita' dell'integrazione
 * (sensor / calendar / event axios_<studente>_*) dall'oggetto `hass`.
 */

const WS_STUDENTS = "axios_famiglia/students";
const STORE_KEY = "axios_famiglia_student";
const PREFS_KEY = "axios_famiglia_prefs";
const STALE_AFTER_MS = 6 * 60 * 60 * 1000; // dati "non recenti" dopo 6 ore
const MONTHS_IT = { gen: 0, feb: 1, mar: 2, apr: 3, mag: 4, giu: 5, lug: 6, ago: 7, set: 8, ott: 9, nov: 10, dic: 11 };

// I nomi delle sezioni (tab.*) servono sia per la barra in basso sia per il titolo della pagina:
// una sola fonte, cosi' restano sempre uguali.
const TEXT = {
  it: {
    title: "AXIOS FAMIGLIA", subtitle: "REGISTRO ELETTRONICO",
    students: "STUDENTI", widgets: "WIDGET",
    sections: (n) => `${n} sezioni`, attention: "richiedono attenzione", allOk: "tutto in ordine",
    updated: "Aggiornato", stale: "Non aggiornato", unavailable: "Non disponibile",
    loading: "Caricamento…", noStudents: "Nessuno studente configurato.",
    empty: "Nessuna voce da mostrare.", menu: "Menu",
    settings: "Impostazioni", close: "Chiudi", theme: "TEMA", language: "LINGUA",
    system: "Sistema", light: "Chiaro", dark: "Scuro",
    integration: "Opzioni dell'integrazione",
    deviceOnly: "Le preferenze valgono solo per questo dispositivo.",
    tab: { home: "HOME", comm: "COMUNICAZIONI", agenda: "COMPITI E VERIFICHE", topics: "ARGOMENTI", absences: "ASSENZE E USCITE", notes: "ANNOTAZIONI E NOTE" },
    tile: { comm: "COMUNICAZIONI", homework: "COMPITI", tests: "VERIFICHE", annotations: "ANNOTAZIONI", notes: "NOTE DISCIPLINARI", absences: "ASSENZE", late: "RITARDI", exits: "USCITE ANTICIPATE", pct: "% ASSENZE", topics: "ARGOMENTI" },
    chip: { comm: "NON LETTE", homework: "COMPITI", tests: "VERIFICHE", annotations: "ANNOTAZIONI", notes: "NOTE DISCIPLINARI" },
    unreadOf: (t) => `non lette su ${t}`, allRead: "tutte lette", none: "nessuna",
    lastDays: (n) => `ultimi ${n} giorni`, totalAbs: "totali", sinceStart: "dall'inizio",
    tag: { homework: "COMPITI", test: "VERIFICA", annotation: "ANNOTAZIONE", note: "NOTA DISCIPLINARE", absence: "ASSENZA", late: "RITARDO", exit: "USCITA" },
    notCounted: "non conteggiata", unread: "NON LETTA", by: "di",
  },
  en: {
    title: "AXIOS FAMIGLIA", subtitle: "SCHOOL REGISTER",
    students: "STUDENTS", widgets: "WIDGETS",
    sections: (n) => `${n} sections`, attention: "need attention", allOk: "all good",
    updated: "Up to date", stale: "Outdated", unavailable: "Unavailable",
    loading: "Loading…", noStudents: "No student configured.",
    empty: "Nothing to show.", menu: "Menu",
    settings: "Settings", close: "Close", theme: "THEME", language: "LANGUAGE",
    system: "System", light: "Light", dark: "Dark",
    integration: "Integration options",
    deviceOnly: "Preferences apply to this device only.",
    tab: { home: "HOME", comm: "COMMUNICATIONS", agenda: "HOMEWORK AND TESTS", topics: "LESSON TOPICS", absences: "ABSENCES AND EXITS", notes: "ANNOTATIONS AND NOTES" },
    tile: { comm: "COMMUNICATIONS", homework: "HOMEWORK", tests: "TESTS", annotations: "ANNOTATIONS", notes: "DISCIPLINARY NOTES", absences: "ABSENCES", late: "LATE ENTRIES", exits: "EARLY EXITS", pct: "% ABSENCES", topics: "LESSON TOPICS" },
    chip: { comm: "UNREAD", homework: "HOMEWORK", tests: "TESTS", annotations: "ANNOTATIONS", notes: "DISCIPLINARY NOTES" },
    unreadOf: (t) => `unread of ${t}`, allRead: "all read", none: "none",
    lastDays: (n) => `last ${n} days`, totalAbs: "total", sinceStart: "since the start",
    tag: { homework: "HOMEWORK", test: "TEST", annotation: "ANNOTATION", note: "DISCIPLINARY NOTE", absence: "ABSENCE", late: "LATE", exit: "EARLY EXIT" },
    notCounted: "not counted", unread: "UNREAD", by: "by",
  },
};

// Icone SVG (24x24, tratto): nessuna dipendenza da font o da emoji
const ICONS = {
  home: '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  sliders: '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
  megaphone: '<path d="M3 11v2a1 1 0 0 0 1 1h2l5 4V6L6 10H4a1 1 0 0 0-1 1z"/><path d="M15 9a4 4 0 0 1 0 6"/><path d="M18 6.5a8 8 0 0 1 0 11"/>',
  book: '<path d="M4 5a2 2 0 0 1 2-2h13v15H6a2 2 0 0 0-2 2z"/><path d="M4 20a2 2 0 0 0 2 1h13v-3"/><path d="M9 8h6"/>',
  clipboard: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4h6v3H9z"/><path d="M9 14l2 2 4-4"/>',
  note: '<path d="M6 3h9l4 4v14H6z"/><path d="M15 3v4h4"/><path d="M9 12h7M9 16h5"/>',
  alert: '<path d="M12 3L2.5 20h19z"/><path d="M12 9.5v5"/><path d="M12 17.2v.3"/>',
  calx: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/><path d="M10 13.5l4 4M14 13.5l-4 4"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  exit: '<path d="M10 4H5v16h5"/><path d="M14 8l4 4-4 4"/><path d="M18 12H9"/>',
  percent: '<path d="M19 5L5 19"/><circle cx="7" cy="7" r="2.2"/><circle cx="17" cy="17" r="2.2"/>',
  openbook: '<path d="M2 5h7a3 3 0 0 1 3 3v12a2 2 0 0 0-2-2H2z"/><path d="M22 5h-7a3 3 0 0 0-3 3v12a2 2 0 0 1 2-2h8z"/>',
  check: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16 9.5"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.7 6.7 0 0 0 9.8 9.8z"/>',
  monitor: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18z"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  ext: '<path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
};

const COLORS = {
  blue: "#2f80ed", orange: "#f08a24", purple: "#8b5cf6", pink: "#e8478b", yellow: "#d9a406",
  red: "#e5484d", green: "#18a058", teal: "#0ea5b7", indigo: "#4f5bd5", slate: "#64748b",
};

// Barra in basso: [vista, icona, colore]
const NAV = [
  ["home", "home", "teal"],
  ["comm", "megaphone", "orange"],
  ["agenda", "book", "purple"],
  ["topics", "openbook", "indigo"],
  ["absences", "calx", "blue"],
  ["notes", "note", "yellow"],
];

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function parseDate(text) {
  if (!text) return null;
  const s = String(text);
  let m = s.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (m) return new Date(+m[1], +m[2] - 1, +m[3]);
  m = s.match(/(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})/);
  if (m) { let y = +m[3]; if (y < 100) y += 2000; return new Date(y, +m[2] - 1, +m[1]); }
  m = s.match(/(\d{1,2})\s+([A-Za-zàèéìòù]+)\.?\s+(\d{4})/);
  if (m) {
    const mo = MONTHS_IT[m[2].toLowerCase().slice(0, 3)];
    if (mo !== undefined) return new Date(+m[3], mo, +m[1]);
  }
  return null;
}
const byDateDesc = (a, b) => (b.d ? b.d.getTime() : -1) - (a.d ? a.d.getTime() : -1);
const clip = (text, n) => { const t = String(text || "").replace(/\s+/g, " ").trim(); return t.length > n ? t.slice(0, n - 1).trimEnd() + "…" : t; };

class AxiosFamigliaPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._students = null; // null = non ancora caricati
    this._student = null;
    this._view = "home";
    this._sig = "";
    this._topics = {};
    this._topicsStamp = {};
    this._topicsFail = {};
    this._topicsVersion = 0;
    this._clock = null;
    this._settingsOpen = false;
    this._prefs = this._loadPrefs();
    this._onKey = (e) => {
      if (e.key === "Escape" && this._settingsOpen) { this._settingsOpen = false; this._render(false); }
    };
    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
  }

  connectedCallback() {
    this._clock = setInterval(() => this._tick(), 20000);
    document.addEventListener("keydown", this._onKey);
  }
  disconnectedCallback() {
    clearInterval(this._clock);
    document.removeEventListener("keydown", this._onKey);
  }

  set narrow(v) { this.classList.toggle("narrow", !!v); }
  set panel(_p) { /* nessuna configurazione */ }

  set hass(h) {
    const first = !this._hass;
    this._hass = h;
    this._applyTheme();
    if (first) this._init();
    else this._maybeRender();
  }

  // ---------- preferenze (tema e lingua), salvate per dispositivo ----------
  _loadPrefs() {
    const out = { theme: "system", lang: "system" };
    try {
      const raw = JSON.parse(localStorage.getItem(PREFS_KEY) || "{}");
      if (["system", "light", "dark"].includes(raw.theme)) out.theme = raw.theme;
      if (["system", "en", "it"].includes(raw.lang)) out.lang = raw.lang;
    } catch (_e) { /* ignora */ }
    return out;
  }
  _savePrefs() {
    try { localStorage.setItem(PREFS_KEY, JSON.stringify(this._prefs)); } catch (_e) { /* ignora */ }
  }
  _applyTheme() {
    const p = this._prefs.theme;
    const dark = p === "dark" || (p === "system" && !!(this._hass && this._hass.themes && this._hass.themes.darkMode));
    this.classList.toggle("dark", dark);
  }
  get _lang() {
    const l = this._prefs.lang === "system" ? (this._hass?.language || "en") : this._prefs.lang;
    return String(l).toLowerCase().startsWith("it") ? "it" : "en";
  }
  get _loc() { return this._lang === "it" ? "it-IT" : "en-GB"; }
  _t() { return TEXT[this._lang]; }

  async _init() {
    this._render(true);
    try {
      const res = await this._hass.callWS({ type: WS_STUDENTS });
      this._students = Array.isArray(res) ? res : [];
    } catch (_e) {
      this._students = [];
    }
    if (!this._students.length) this._students = this._discover();
    let saved = null;
    try { saved = localStorage.getItem(STORE_KEY); } catch (_e) { /* ignora */ }
    this._student = this._students.find((s) => s.slug === saved)?.slug || this._students[0]?.slug || null;
    this._render(true);
    if (this._student) this._loadTopics(this._student);
  }

  // Se il comando WebSocket non risponde, ricava gli studenti dalle entita' presenti
  _discover() {
    const out = [];
    for (const id of Object.keys(this._hass.states)) {
      const m = id.match(/^sensor\.axios_(.+)_last_update$/);
      if (m) out.push({ slug: m[1], name: m[1].split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ") });
    }
    return out;
  }

  // ---------- accesso ai dati ----------
  _s(slug, dom, key) { return this._hass.states[`${dom}.axios_${slug}_${key}`]; }
  _n(st) {
    if (!st || st.state === "unavailable" || st.state === "unknown") return null;
    const v = Number(st.state);
    return Number.isFinite(v) ? v : null;
  }

  _model(slug) {
    const S = (k, dom = "sensor") => this._s(slug, dom, k);
    const A = (st) => (st && st.attributes) || {};
    const comm = S("communications");
    const comms = (A(comm).elenco || []).map((c) => ({ ...c, d: parseDate(c.date) })).sort(byDateDesc);
    const unread = this._n(S("communications_unread")) ?? comms.filter((c) => c.unread).length;
    const rows = (sensor, field) => (A(S(sensor)).elenco || []).filter((r) => r[field]).map((r) => ({ d: parseDate(r.date), text: r[field], dateText: r.date }));
    const homework = rows("homework", "homework").sort(byDateDesc);
    const tests = rows("homework", "tests").sort(byDateDesc);
    const annotations = rows("annotations", "annotations").sort(byDateDesc);
    const notes = rows("disciplinary_notes", "disciplinary_notes").sort(byDateDesc);
    const kind = (desc) => {
      const x = String(desc || "").toLowerCase();
      if (x.includes("uscit") || x.includes("exit")) return "exit";
      if (x.includes("ritard") || x.includes("entrat") || x.includes("late")) return "late";
      return "absence";
    };
    const events = (A(S("absences")).eventi || []).map((e) => ({ ...e, d: parseDate(e.date), kind: kind(e.description) })).sort(byDateDesc);
    const lt = S("last_topics");
    let topics = this._topics[slug];
    if (!topics) {
      const txt = A(lt).argomenti;
      topics = txt ? [{ d: parseDate(A(lt).data_iso || lt.state), text: txt }] : [];
    }
    topics = [...topics].sort(byDateDesc);
    const main = [S("communications"), S("absences"), S("homework"), S("last_update")];
    const available = main.every((x) => x && x.state !== "unavailable");
    const updated = S("last_update")?.state;
    const ts = updated ? Date.parse(updated) : NaN;
    return {
      slug, comms, unread, totalComms: this._n(comm) ?? comms.length,
      homework, tests, annotations, notes, events, topics,
      annCount: this._n(S("annotations")) ?? annotations.length,
      noteCount: this._n(S("disciplinary_notes")) ?? notes.length,
      absences: this._n(S("absences")), late: this._n(S("late_entries")), exits: this._n(S("early_exits")), pct: this._n(S("absence_percentage")),
      windowDays: A(S("homework")).giorni_considerati ?? 14,
      lastTopics: { text: A(lt).argomenti || "", d: parseDate(A(lt).data_iso || lt?.state) },
      available, ts: Number.isFinite(ts) ? ts : null,
      stale: Number.isFinite(ts) ? Date.now() - ts > STALE_AFTER_MS : false,
    };
  }

  // ---------- aggiornamento ----------
  _entityIds() {
    const keys = ["communications", "communications_unread", "absences", "late_entries", "early_exits", "absence_percentage", "homework", "annotations", "disciplinary_notes", "last_topics", "last_update"];
    const ids = [];
    for (const s of this._students || []) {
      for (const k of keys) ids.push(`sensor.axios_${s.slug}_${k}`);
      ids.push(`event.axios_${s.slug}_news`);
    }
    return ids;
  }

  _maybeRender() {
    if (!this._students) return;
    const st = this._hass.states;
    const sig = this._entityIds().map((id) => (st[id] ? st[id].last_updated : "-")).join("|")
      + `#${this._view}#${this._student}#${this._lang}#${this.classList.contains("dark")}#${this._topicsVersion}`;
    if (sig === this._sig) return;
    this._sig = sig;
    this._render(false);
    if (this._student) this._loadTopics(this._student);
  }

  async _loadTopics(slug) {
    const eid = `calendar.axios_${slug}_topics`;
    if (!this._hass.states[eid]) return;
    const stamp = this._s(slug, "sensor", "last_update")?.state || "";
    if (this._topicsStamp[slug] === stamp) return;
    if (Date.now() - (this._topicsFail[slug] || 0) < 60000) return;
    this._topicsStamp[slug] = stamp;
    const start = new Date(); start.setDate(start.getDate() - 120);
    const end = new Date(); end.setDate(end.getDate() + 7);
    try {
      const ev = await this._hass.callApi("GET", `calendars/${eid}?start=${encodeURIComponent(start.toISOString())}&end=${encodeURIComponent(end.toISOString())}`);
      this._topics[slug] = (ev || [])
        .map((e) => ({ d: parseDate(String((e.start && (e.start.date || e.start.dateTime)) || "").slice(0, 10)), text: e.description || e.summary || "" }))
        .filter((x) => x.d && x.text);
      this._topicsVersion++;
      this._maybeRender();
    } catch (err) {
      this._topicsStamp[slug] = null;
      this._topicsFail[slug] = Date.now();
      console.warn("Axios Famiglia: calendario argomenti non disponibile", err);
    }
  }

  _tick() {
    const el = this.shadowRoot.querySelector("[data-clock]");
    if (!el) return;
    const now = new Date();
    el.querySelector("b").textContent = now.toLocaleTimeString(this._loc, { hour: "2-digit", minute: "2-digit" });
    el.querySelector("span").textContent = this._fmtShortDate(now);
  }

  _fmtShortDate(d) {
    return d.toLocaleDateString(this._loc, { weekday: "short", day: "numeric", month: "short" }).replace(/\./g, "").toUpperCase();
  }

  _rel(ts) {
    if (!ts) return "—";
    const rtf = new Intl.RelativeTimeFormat(this._loc, { numeric: "auto" });
    const diff = (ts - Date.now()) / 1000;
    const a = Math.abs(diff);
    if (a < 3600) return rtf.format(Math.round(diff / 60), "minute");
    if (a < 86400) return rtf.format(Math.round(diff / 3600), "hour");
    return rtf.format(Math.round(diff / 86400), "day");
  }

  // ---------- eventi ----------
  _onClick(ev) {
    const el = ev.target.closest("[data-act]");
    if (!el) return;
    const { act, val, group } = el.dataset;
    if (act === "menu") this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }));
    else if (act === "settings") { this._settingsOpen = true; this._render(false); }
    else if (act === "close") { this._settingsOpen = false; this._render(false); }
    else if (act === "pref") {
      if (group !== "theme" && group !== "lang") return;
      this._prefs = { ...this._prefs, [group]: val };
      this._savePrefs();
      this._applyTheme();
      this._render(false);
    } else if (act === "integration") {
      this._settingsOpen = false;
      this._render(false);
      history.pushState(null, "", "/config/integrations/integration/axios_famiglia");
      window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
    } else if (act === "view") { this._view = val; this._render(true, true); }
    else if (act === "student") {
      this._student = val;
      try { localStorage.setItem(STORE_KEY, val); } catch (_e) { /* ignora */ }
      this._render(true);
      this._loadTopics(val);
    }
  }

  // ---------- rendering ----------
  _icon(name, size = 20) {
    return `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]}</svg>`;
  }

  _render(force, toTop = false) {
    const root = this.shadowRoot;
    const scroller = root.querySelector(".scroll");
    const keep = scroller && !toTop ? scroller.scrollTop : 0;
    root.innerHTML = `<style>${CSS}</style>${this._html()}`;
    const again = root.querySelector(".scroll");
    if (again) again.scrollTop = keep;
    const active = root.querySelector(".tab.on");
    if (active) active.scrollIntoView({ block: "nearest", inline: "center" });
  }

  _html() {
    const t = this._t();
    if (this._students === null) return `<div class="app"><div class="scroll"><div class="empty">${t.loading}</div></div></div>`;
    if (!this._students.length) return `<div class="app"><div class="scroll"><div class="empty">${t.noStudents}</div></div></div>`;
    const m = this._model(this._student);
    const status = !m.available ? "red" : m.stale ? "orange" : "green";
    const statusText = !m.available ? t.unavailable : m.stale ? t.stale : t.updated;
    const now = new Date();
    const isAdmin = !!this._hass.user?.is_admin;
    const body = this._view === "home" ? this._home(m) : this._list(m);
    return `<div class="app">
      <div class="scroll"><div class="wrap">
        <section class="card hero">
          <div class="top">
            <button class="iconbtn" data-act="menu" aria-label="${t.menu}">${this._icon("menu", 20)}</button>
            <div class="ttl"><h1>${t.title}</h1><small>${t.subtitle}</small></div>
            <div class="right"><span class="dot ${status}" title="${esc(statusText)}"></span>
              <button class="iconbtn ghost" data-act="settings" aria-label="${t.settings}">${this._icon("sliders", 19)}</button></div>
          </div>
          <div class="bar">
            <div class="schips">${this._students.map((s) => `<button class="schip ${s.slug === this._student ? "on" : ""}" data-act="student" data-val="${esc(s.slug)}">${esc(s.name)}</button>`).join("")}</div>
            <div class="clock" data-clock><b>${now.toLocaleTimeString(this._loc, { hour: "2-digit", minute: "2-digit" })}</b><span>${this._fmtShortDate(now)}</span></div>
          </div>
        </section>
        ${body}
      </div></div>
      ${this._nav()}
    </div>${this._settingsSheet(isAdmin)}`;
  }

  _tiles(m) {
    const t = this._t();
    const num = (v) => (v === null || v === undefined ? "–" : String(v));
    const seg = (ratio) => {
      const r = Math.max(0, Math.min(1, ratio || 0));
      const on = r > 0 ? Math.max(1, Math.round(r * 6)) : 0;
      return `<span class="seg">${Array.from({ length: 6 }, (_, i) => `<i class="${i < on ? "on" : ""}"></i>`).join("")}</span>`;
    };
    const dayShort = (d) => (d ? d.toLocaleDateString(this._loc, { weekday: "short", day: "numeric" }).replace(/\./g, "") : "–");
    const lastEvent = m.events[0];
    return [
      { id: "comm", view: "comm", icon: "megaphone", color: m.unread > 0 ? "orange" : "blue", value: num(m.unread), attn: m.unread > 0,
        cap: m.totalComms ? (m.unread > 0 ? t.unreadOf(m.totalComms) : t.allRead) : t.none, bar: seg(m.totalComms ? m.unread / m.totalComms : 0) },
      { id: "homework", view: "agenda", icon: "book", color: "purple", value: String(m.homework.length), cap: t.lastDays(m.windowDays), bar: seg(m.homework.length / 6) },
      { id: "tests", view: "agenda", icon: "clipboard", color: "pink", value: String(m.tests.length), cap: m.tests[0] ? clip(m.tests[0].text, 44) : t.none, bar: seg(m.tests.length / 6) },
      { id: "annotations", view: "notes", icon: "note", color: "yellow", value: num(m.annCount), cap: m.annotations[0] ? clip(m.annotations[0].text, 44) : t.none, bar: seg(m.annCount / 6) },
      { id: "notes", view: "notes", icon: "alert", color: m.noteCount > 0 ? "red" : "slate", value: num(m.noteCount), attn: m.noteCount > 0,
        cap: m.notes[0] ? clip(m.notes[0].text, 44) : t.none, bar: seg(m.noteCount / 3) },
      { id: "absences", view: "absences", icon: "calx", color: "blue", value: num(m.absences), cap: lastEvent ? clip(lastEvent.description, 44) : t.none, bar: seg((m.pct || 0) / 20) },
      { id: "late", view: "absences", icon: "clock", color: "orange", value: num(m.late), cap: t.totalAbs, bar: seg((m.late || 0) / 6) },
      { id: "exits", view: "absences", icon: "exit", color: "teal", value: num(m.exits), cap: t.totalAbs, bar: seg((m.exits || 0) / 6) },
      { id: "pct", view: "absences", icon: "percent", color: "green", value: m.pct === null ? "–" : String(m.pct).replace(".", ","), unit: "%", cap: t.sinceStart, bar: seg((m.pct || 0) / 20) },
      { id: "topics", view: "topics", icon: "openbook", color: "indigo", value: dayShort(m.lastTopics.d || m.topics[0]?.d), small: true, cap: clip(m.lastTopics.text || m.topics[0]?.text, 48) || t.none, bar: seg(m.topics.length ? 1 : 0) },
    ];
  }

  _home(m) {
    const t = this._t();
    const tiles = this._tiles(m);
    const attention = tiles.filter((x) => x.attn).map((x) => t.tile[x.id]);
    const chips = [
      { k: "comm", n: m.unread, icon: "megaphone", c: "orange" }, { k: "homework", n: m.homework.length, icon: "book", c: "purple" },
      { k: "tests", n: m.tests.length, icon: "clipboard", c: "pink" }, { k: "annotations", n: m.annCount, icon: "note", c: "yellow" },
      { k: "notes", n: m.noteCount, icon: "alert", c: "red" },
    ].filter((x) => x.n > 0);
    const chipLabel = (k) => t.chip[k] || t.tile[k];
    const summary = chips.length
      ? chips.map((x) => `<div class="sum" style="--fg:${COLORS[x.c]}"><span class="ico">${this._icon(x.icon, 16)}</span><b>${x.n}</b><small>${chipLabel(x.k)}</small></div>`).join("")
      : `<div class="sum" style="--fg:${COLORS.green}"><span class="ico">${this._icon("check", 16)}</span><small>${t.allOk.toUpperCase()}</small></div>`;
    return `
      <section class="card summary">${summary}</section>
      <div class="sec">${t.students}</div>
      <div class="people">${this._students.map((s) => this._person(s)).join("")}</div>
      <div class="sec">${t.widgets}</div>
      <div class="warn ${attention.length ? "" : "okk"}">${t.sections(tiles.length)} · ${attention.length ? `${attention.length} ${t.attention}: ${attention.join(", ")}` : t.allOk}</div>
      <div class="tiles">${tiles.map((x) => `
        <button class="tile ${x.attn ? "attn" : ""}" data-act="view" data-val="${x.view}" style="--fg:${COLORS[x.color]}">
          <div class="hd"><span class="ti">${this._icon(x.icon, 18)}</span><span class="tl">${t.tile[x.id]}</span></div>
          <div class="vrow"><div class="val ${x.small ? "s" : ""}">${esc(x.value)}${x.unit ? `<small>${x.unit}</small>` : ""}</div>${x.bar}</div>
          <div class="cap">${esc(x.cap)}</div>
        </button>`).join("")}</div>`;
  }

  _person(s) {
    const t = this._t();
    const m = this._model(s.slug);
    const color = !m.available ? "red" : m.stale ? "orange" : "green";
    const label = !m.available ? t.unavailable : m.stale ? t.stale : t.updated;
    return `<button class="person ${s.slug === this._student ? "on" : ""}" data-act="student" data-val="${esc(s.slug)}">
      <div class="prow"><span class="av ${color}"><i>${esc((s.name || "?").trim().charAt(0).toUpperCase())}</i></span>
        <div class="pn"><b>${esc(s.name)}</b><span class="pill ${color}">${label}</span></div></div>
      <div class="pstat"><span>${this._icon("clock", 12)} ${this._rel(m.ts)}</span>${m.unread > 0 ? `<span class="u">${this._icon("megaphone", 12)} ${m.unread}</span>` : ""}</div>
    </button>`;
  }

  _list(m) {
    const t = this._t();
    let items = [];
    if (this._view === "comm") {
      items = m.comms.map((c) => ({ d: c.d, tag: c.type || "", color: c.unread ? "orange" : "blue", text: c.title, meta: [c.author ? `${t.by} ${c.author}` : "", c.unread ? t.unread : ""].filter(Boolean).join(" · "), unread: c.unread }));
    } else if (this._view === "agenda") {
      items = [
        ...m.homework.map((x) => ({ d: x.d, tag: t.tag.homework, color: "purple", text: x.text })),
        ...m.tests.map((x) => ({ d: x.d, tag: t.tag.test, color: "pink", text: x.text })),
      ].sort(byDateDesc);
    } else if (this._view === "notes") {
      items = [
        ...m.annotations.map((x) => ({ d: x.d, tag: t.tag.annotation, color: "yellow", text: x.text })),
        ...m.notes.map((x) => ({ d: x.d, tag: t.tag.note, color: "red", text: x.text })),
      ].sort(byDateDesc);
    } else if (this._view === "absences") {
      const col = { absence: "blue", late: "orange", exit: "teal" };
      items = m.events.map((e) => ({ d: e.d, tag: t.tag[e.kind], color: col[e.kind], text: e.description, meta: e.counts === false ? t.notCounted : "" }));
    } else if (this._view === "topics") {
      items = m.topics.map((x) => ({ d: x.d, tag: "", color: "indigo", text: x.text, topics: true }));
    }
    const rows = items.map((it) => {
      const d = it.d;
      const day = d ? d.getDate() : "–";
      const mon = d ? d.toLocaleDateString(this._loc, { month: "short" }).replace(/\./g, "").toUpperCase() : "";
      const wd = d ? d.toLocaleDateString(this._loc, { weekday: "long" }) : "";
      const text = it.topics ? esc(it.text).replace(/([A-ZÀÈÉÌÒÙ][A-ZÀÈÉÌÒÙ' ]{2,}):/g, "<b>$1</b>:") : esc(it.text);
      return `<div class="item ${it.unread ? "unread" : ""}" style="--fg:${COLORS[it.color]}">
        <div class="date"><b>${day}</b><span>${mon}</span></div>
        <div class="body">
          ${it.tag || wd ? `<div class="line">${it.tag ? `<span class="tag">${esc(it.tag)}</span>` : ""}${wd ? `<span class="wd">${esc(wd)}</span>` : ""}</div>` : ""}
          <div class="txt">${text}</div>
          ${it.meta ? `<div class="meta">${esc(it.meta)}</div>` : ""}
        </div></div>`;
    }).join("");
    // Il titolo e' lo stesso testo della voce nella barra in basso
    return `<div class="sec">${t.tab[this._view]}</div>${rows || `<div class="card empty">${t.empty}</div>`}`;
  }

  _nav() {
    const t = this._t();
    return `<nav class="navwrap"><div class="nav card">${NAV.map(([k, ic, color]) => `
      <button class="tab ${this._view === k ? "on" : ""}" data-act="view" data-val="${k}" style="--fg:${COLORS[color]}">
        <span class="tb">${this._icon(ic, 21)}</span><span class="tn">${t.tab[k]}</span></button>`).join("")}</div></nav>`;
  }

  _settingsSheet(isAdmin) {
    if (!this._settingsOpen) return "";
    const t = this._t();
    const p = this._prefs;
    const opt = (group, value, inner, label) => `<button class="opt ${p[group] === value ? "on" : ""}" data-act="pref" data-group="${group}" data-val="${value}" aria-pressed="${p[group] === value}">${inner}<span>${label}</span></button>`;
    return `<div class="overlay" role="dialog" aria-modal="true" aria-label="${esc(t.settings)}">
      <div class="backdrop" data-act="close"></div>
      <div class="sheet card">
        <div class="shead"><h2>${t.settings}</h2><button class="iconbtn" data-act="close" aria-label="${t.close}">${this._icon("x", 18)}</button></div>
        <div class="ssec">${t.theme}</div>
        <div class="opts">
          ${opt("theme", "system", this._icon("monitor", 20), t.system)}
          ${opt("theme", "light", this._icon("sun", 20), t.light)}
          ${opt("theme", "dark", this._icon("moon", 20), t.dark)}
        </div>
        <div class="ssec">${t.language}</div>
        <div class="opts">
          ${opt("lang", "system", this._icon("globe", 20), t.system)}
          ${opt("lang", "en", '<b class="code">EN</b>', "English")}
          ${opt("lang", "it", '<b class="code">IT</b>', "Italiano")}
        </div>
        ${isAdmin ? `<button class="linkrow" data-act="integration">${this._icon("sliders", 18)}<span>${t.integration}</span>${this._icon("ext", 16)}</button>` : ""}
        <p class="hint">${t.deviceOnly}</p>
      </div>
    </div>`;
  }
}

const CSS = `
:host{display:block;position:relative;height:100vh;height:100dvh;overflow:hidden;--bg:#eef2f8;--card:#fff;--text:#16213a;--muted:#7a869f;--line:rgba(22,33,58,.07);--chip:#f1f4f9;--accent:#1b7a4f;
  --shadow:0 1px 2px rgba(22,33,58,.04),0 10px 28px rgba(22,33,58,.08);
  font-family:Inter,"Segoe UI",Roboto,system-ui,-apple-system,sans-serif;color:var(--text);background:var(--bg)}
:host(.dark){--bg:#0d1424;--card:#172036;--text:#e9eefb;--muted:#8fa0bf;--line:rgba(233,238,251,.09);--chip:#202b45;--accent:#4ade99;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 28px rgba(0,0,0,.35)}
*{box-sizing:border-box}
button{font:inherit;color:inherit;border:0;background:none;cursor:pointer;text-align:left;padding:0}
.app{display:flex;flex-direction:column;height:100%}
.scroll{flex:1;min-height:0;overflow-y:auto;padding:14px 14px 6px;-webkit-overflow-scrolling:touch}
.wrap{width:100%;padding-bottom:8px}
.card{background:var(--card);border-radius:24px;box-shadow:var(--shadow)}
.hero{padding:14px 16px 14px;margin-bottom:12px}
.top{display:grid;grid-template-columns:56px 1fr 96px;align-items:center}
.iconbtn{width:42px;height:42px;border-radius:14px;display:grid;place-items:center;background:var(--chip);color:var(--text)}
.iconbtn.ghost{background:transparent;color:#7c6fe0}
.ttl{text-align:center;min-width:0}
.ttl h1{margin:0;font:800 23px/1 "Barlow Condensed","Roboto Condensed","Arial Narrow",Inter,sans-serif;letter-spacing:.04em;color:var(--accent);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ttl small{display:block;margin-top:7px;font-size:9.5px;letter-spacing:.22em;font-weight:800;color:var(--muted)}
.right{display:flex;gap:10px;align-items:center;justify-content:flex-end}
.dot{width:10px;height:10px;border-radius:50%}
.dot.green{background:#16a34a;box-shadow:0 0 0 4px rgba(22,163,74,.16)}
.dot.orange{background:#f08a24;box-shadow:0 0 0 4px rgba(240,138,36,.18)}
.dot.red{background:#e5484d;box-shadow:0 0 0 4px rgba(229,72,77,.18)}
.bar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:14px;padding:7px 8px 7px 8px;border:1px solid var(--line);border-radius:18px;background:color-mix(in srgb,var(--chip) 60%,var(--card))}
.schips{display:flex;gap:6px;overflow-x:auto;min-width:0;scrollbar-width:none}
.schip{padding:8px 14px;border-radius:12px;font-size:12px;font-weight:700;color:var(--muted);white-space:nowrap}
.schip.on{background:var(--card);color:var(--text);box-shadow:0 2px 8px rgba(22,33,58,.1)}
.clock{flex:0 0 auto;text-align:right;border-left:1px solid var(--line);padding:2px 8px 2px 14px}
.clock b{display:block;font-size:16px;font-weight:800;line-height:1.1}
.clock span{font-size:9px;letter-spacing:.14em;font-weight:800;color:var(--muted)}
.summary{display:flex;gap:6px 22px;align-items:center;padding:12px 16px;border-radius:20px;overflow-x:auto;scrollbar-width:none}
.sum{display:flex;align-items:center;gap:9px;flex:0 0 auto}
.sum .ico{width:30px;height:30px;border-radius:10px;display:grid;place-items:center;color:var(--fg);background:color-mix(in srgb,var(--fg) 15%,var(--card))}
.sum b{font-size:15px;font-weight:800}
.sum small{font-size:9px;letter-spacing:.12em;font-weight:800;color:var(--muted);line-height:1.2}
.sec{display:flex;align-items:center;gap:12px;margin:24px 4px 10px;font-size:11px;letter-spacing:.2em;font-weight:800;color:var(--muted)}
.sec::after{content:"";flex:1;height:1px;background:var(--line)}
.warn{margin:-4px 4px 12px;font-size:11px;font-weight:700;color:#d2700a}
.warn.okk{color:#18a058}
.people{display:flex;flex-wrap:wrap;gap:12px}
.person{width:196px;padding:12px;border-radius:20px;background:var(--card);box-shadow:var(--shadow);display:block;border:2px solid transparent}
.person.on{border-color:color-mix(in srgb,var(--accent) 55%,transparent)}
.prow{display:flex;gap:12px;align-items:center}
.av{flex:0 0 auto;width:56px;height:56px;border-radius:50%;padding:3px;border:3px solid #22c55e;display:grid;place-items:center}
.av.orange{border-color:#f08a24}.av.red{border-color:#e5484d}
.av i{font-style:normal;width:100%;height:100%;border-radius:50%;display:grid;place-items:center;font-weight:800;font-size:20px;color:#fff;background:linear-gradient(135deg,#6a8cff,#7c5cf0)}
.pn{min-width:0}.pn b{display:block;font-size:15px;font-weight:800;margin-bottom:5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pill{display:inline-block;white-space:nowrap;font-size:9.5px;font-weight:800;letter-spacing:.04em;color:#fff;padding:3px 9px;border-radius:8px}
.pill.green{background:#16a34a}.pill.orange{background:#f08a24}.pill.red{background:#e5484d}
.pstat{display:flex;gap:10px;align-items:center;margin-top:10px;padding:6px 10px;border-radius:12px;background:color-mix(in srgb,#16a34a 10%,var(--card));font-size:10px;font-weight:800;color:var(--muted)}
.pstat span{display:inline-flex;align-items:center;gap:5px}.pstat .u{color:#d2700a;margin-left:auto}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:12px}
.tile{position:relative;min-width:0;display:flex;flex-direction:column;min-height:128px;padding:14px;border-radius:20px;box-shadow:var(--shadow);
  background:linear-gradient(160deg,var(--card) 42%,color-mix(in srgb,var(--fg) 17%,var(--card)) 165%)}
.tile.attn{box-shadow:0 1px 2px rgba(22,33,58,.04),0 10px 28px color-mix(in srgb,var(--fg) 22%,transparent)}
.tile .hd{display:flex;align-items:center;gap:9px}
.ti{flex:0 0 auto;width:34px;height:34px;border-radius:11px;display:grid;place-items:center;color:var(--fg);background:color-mix(in srgb,var(--fg) 15%,var(--card))}
.tl{font-size:9.5px;font-weight:800;letter-spacing:.12em;color:var(--muted);line-height:1.25}
.vrow{display:flex;align-items:flex-end;justify-content:space-between;gap:8px;margin:14px 0 8px}
.val{margin:0;font-size:36px;font-weight:800;line-height:1;letter-spacing:-.01em;min-width:0}
.val.s{font-size:26px;text-transform:capitalize}
.val small{margin-left:2px;font-size:16px;font-weight:700;color:var(--muted)}
.cap{margin-top:auto;font-size:10.5px;font-weight:600;line-height:1.35;color:var(--muted);overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;line-clamp:2;-webkit-box-orient:vertical;word-break:break-word}
.seg{display:flex;gap:3px;flex:0 0 auto;padding-bottom:3px}
.seg i{width:6px;height:14px;border-radius:3px;background:var(--line)}
.seg i.on{background:var(--fg)}
.item{display:flex;gap:14px;align-items:flex-start;margin-bottom:10px;padding:14px;border-radius:20px;background:var(--card);box-shadow:var(--shadow)}
.item.unread{box-shadow:inset 4px 0 0 var(--fg),var(--shadow)}
.date{flex:0 0 54px;padding:9px 0 8px;border-radius:15px;text-align:center;color:var(--fg);background:color-mix(in srgb,var(--fg) 14%,var(--card))}
.date b{display:block;font-size:21px;font-weight:800;line-height:1}
.date span{display:block;margin-top:3px;font-size:9px;font-weight:800;letter-spacing:.12em}
.body{flex:1;min-width:0}
.line{display:flex;gap:10px;align-items:center;margin-bottom:6px;flex-wrap:wrap}
.tag{font-size:9px;font-weight:800;letter-spacing:.1em;padding:3px 9px;border-radius:8px;color:var(--fg);background:color-mix(in srgb,var(--fg) 14%,var(--card))}
.wd{font-size:11px;font-weight:700;color:var(--muted);text-transform:capitalize}
.txt{font-size:14px;line-height:1.5;white-space:pre-wrap;word-break:break-word}
.txt b{font-weight:800}
.meta{margin-top:5px;font-size:11px;font-weight:600;color:var(--muted)}
.empty{padding:28px;text-align:center;color:var(--muted);font-weight:600}
.navwrap{flex:0 0 auto;padding:4px 14px calc(14px + env(safe-area-inset-bottom,0px))}
.nav{display:flex;gap:4px;padding:8px;overflow-x:auto;scrollbar-width:none;border-radius:26px}
.tab{flex:1 0 auto;min-width:96px;display:flex;flex-direction:column;align-items:center;gap:6px;padding:8px 8px 9px;border-radius:18px;border:2px solid transparent;color:var(--muted);font-size:9.5px;font-weight:800;letter-spacing:.06em;text-align:center}
.tb{width:38px;height:38px;border-radius:13px;display:grid;place-items:center;color:var(--fg);background:color-mix(in srgb,var(--fg) 15%,var(--card))}
.tn{max-width:116px;line-height:1.2}
.tab.on{color:var(--text);background:color-mix(in srgb,var(--fg) 10%,var(--card));border-color:color-mix(in srgb,var(--fg) 50%,transparent)}
.tab.on .tb{background:var(--fg);color:#fff}
.overlay{position:absolute;inset:0;z-index:30;display:flex;align-items:center;justify-content:center;padding:14px}
.backdrop{position:absolute;inset:0;background:rgba(10,16,30,.5);backdrop-filter:blur(3px)}
.sheet{position:relative;width:min(440px,100%);max-height:100%;overflow-y:auto;padding:18px 18px 16px}
.shead{display:flex;align-items:center;justify-content:space-between}
.shead h2{margin:0;font-size:18px;font-weight:800}
.ssec{margin:16px 2px 8px;font-size:10px;letter-spacing:.2em;font-weight:800;color:var(--muted)}
.opts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.opt{display:flex;flex-direction:column;align-items:center;gap:7px;padding:12px 6px;border-radius:16px;background:var(--chip);border:2px solid transparent;font-size:12px;font-weight:700;color:var(--muted);text-align:center}
.opt.on{border-color:var(--accent);color:var(--text);background:color-mix(in srgb,var(--accent) 12%,var(--card))}
.opt .code{display:grid;place-items:center;width:20px;height:20px;font-size:12px;font-weight:800;letter-spacing:.03em}
.linkrow{display:flex;align-items:center;gap:10px;width:100%;margin-top:18px;padding:12px 14px;border-radius:16px;background:var(--chip);font-size:13px;font-weight:700}
.linkrow span{flex:1}
.hint{margin:14px 2px 0;font-size:11px;font-weight:600;color:var(--muted)}
:host(.narrow) .overlay{align-items:flex-end}
:host(.narrow) .top{grid-template-columns:48px 1fr 70px}
:host(.narrow) .ttl h1{font-size:19px}
:host(.narrow) .person{width:100%}
:host(.narrow) .tiles{grid-template-columns:repeat(2,minmax(0,1fr))}
@media (max-width:640px){.tiles{grid-template-columns:repeat(2,minmax(0,1fr))}.person{width:100%}.clock b{font-size:14px}}
`;

if (!customElements.get("axios-famiglia-panel")) {
  customElements.define("axios-famiglia-panel", AxiosFamigliaPanel);
}
