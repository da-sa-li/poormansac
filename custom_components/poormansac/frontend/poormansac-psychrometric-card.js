/*
 * Poor Man's AC - Psychrometric (Carrier) chart Lovelace card.
 *
 * Buildless vanilla custom element, loaded as an ES module via
 * frontend.add_extra_js_url -> <script type="module">. No build step, no Lit.
 *
 * Geometry note: eSat()/wSat() below are a deliberate, minimal port of
 * calc.saturation_vapour_pressure() and calc.mixing_ratio() (SI units) from the
 * Python side - only the chart's bounding geometry. The comfort physics
 * (heat_index, d_hi) is NOT duplicated here; it is read from the entity's
 * attributes. calc.py remains the single source of truth for the decision.
 */

const EPSILON = 0.621945; // == calc._EPSILON (ratio of molar masses water/air)

// Saturation vapour pressure over water in Pa from temperature in degC (Magnus).
const eSat = (t) => 611.2 * Math.exp((17.62 * t) / (243.12 + t));

// Mixing ratio in kg_water/kg_dry_air at relative humidity rh (0..1) from
// T (degC) and pressure (Pa). rh = 1 gives the saturation mixing ratio.
const wRH = (t, p, rh) => {
  const e = rh * eSat(t);
  return (EPSILON * e) / (p - e);
};

// Saturation mixing ratio in kg_water/kg_dry_air from T (degC) and pressure (Pa).
const wSat = (t, p) => wRH(t, p, 1);

// Relative humidity (0..1) from mixing ratio w (kg/kg), T (degC) and pressure
// (Pa). Inverts wRH: e = p*w/(EPSILON + w), then rh = e / eSat(t).
const rhFromW = (w, t, p) => (p * w) / (EPSILON + w) / eSat(t);

// Partial derivatives of the heat index polynomial: exact ports of calc.py
// d_hi_d_t / d_hi_d_x, needed to locate the sign-change optimum along the
// cooling path in the frontend without an extra round-trip to the backend.
const _dHIdT = (t, x) => {
  const e1 = Math.exp(-0.0533 * t);
  const e2 = Math.exp(-0.1066 * t);
  const tk = 273.15 + t;
  const tk2 = tk * tk;
  const x2 = x * x;
  return (
    1.61139 - 0.0246162 * t +
    e1 * x * (136.452 - 8.5257 * t + 0.129052 * t * t
              - 15.7986 * tk + 0.712523 * t * tk - 0.00687847 * t * t * tk) +
    e2 * x2 * (-111.8394 * tk + 4.93978 * t * tk - 0.0243904 * t * t * tk
                + 8.43093 * tk2 - 0.287681 * t * tk2 + 0.00130001 * t * t * tk2)
  );
};
const _dHIdX = (t, x) => {
  const e1 = Math.exp(-0.0533 * t);
  const e2 = Math.exp(-0.1066 * t);
  const tk = 273.15 + t;
  const tk2 = tk * tk;
  return (
    e1 * tk * (136.452 - 8.5257 * t + 0.129052 * t * t) +
    e2 * tk2 * x * (-111.8394 + 4.93978 * t - 0.0243904 * t * t)
  );
};
// Total differential along the isenthalpic cooling path (dxdt in kg/kg/K).
// Positive = cooling still beneficial; negative = cooling detrimental.
// Sign convention: this is -(d_hi_cooling with delta_t=-1 from calc.py).
const _dHICooling = (t, x, dxdt) => _dHIdT(t, x) + _dHIdX(t, x) * dxdt;

// Keys selectable for the state-point label, in display order.
const POINT_LABEL_KEYS = ["t", "x", "hi", "rh"];

// Upper bound on rh_lines, so a misconfiguration can't spawn an unbounded
// number of SVG paths and stall the frontend. 100 curves is already far denser
// than the chart can usefully show.
const MAX_RH_LINES = 100;

const SVG_NS = "http://www.w3.org/2000/svg";

const I18N = {
  de: {
    xAxis: "Trockentemperatur [°C]",
    saturation: "Sättigung (100 % rF)",
    relHumidity: "Rel. Feuchte ",
    currentState: "Aktueller Zustand",
    coolingBeneficial: "Kühlung sinnvoll",
    coolingDetrimental: "Kühlung schädlich",
    unavailable: "Zustand nicht verfügbar",
  },
  en: {
    xAxis: "Dry-bulb temperature [°C]",
    saturation: "Saturation (100% RH)",
    relHumidity: "Rel. humidity ",
    currentState: "Current state",
    coolingBeneficial: "Cooling beneficial",
    coolingDetrimental: "Cooling detrimental",
    unavailable: "State unavailable",
  },
};

class PoorMansACPsychrometricCard extends HTMLElement {
  static getStubConfig(hass) {
    let entity = "";
    if (hass && hass.states) {
      for (const id of Object.keys(hass.states)) {
        if (!id.startsWith("binary_sensor.")) continue;
        const a = hass.states[id].attributes || {};
        if ("temperature" in a && "mixing_ratio" in a && "dx_dt" in a) {
          entity = id;
          break;
        }
      }
    }
    return { type: "custom:poormansac-psychrometric-card", entity };
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error(
        'Define "entity": the Poor Man\'s AC cooling-recommended binary_sensor.'
      );
    }
    this._config = {
      title: "Psychrometric chart",
      t_min: 0,
      t_max: 40,
      x_min: 0,
      x_max: 50,
      rh_lines: 5,
      point_label: ["t", "x", "hi"],
      ...config,
    };
    for (const k of ["t_min", "t_max", "x_min", "x_max"]) {
      if (!Number.isFinite(Number(this._config[k]))) {
        throw new Error(`Invalid "${k}": expected a finite number.`);
      }
    }
    const n = Number(this._config.rh_lines);
    if (!Number.isInteger(n) || n < 0 || n > MAX_RH_LINES) {
      throw new Error(
        `Invalid "rh_lines": expected an integer between 0 and ${MAX_RH_LINES}.`
      );
    }
    this._config.rh_lines = n;
    const labels = this._config.point_label;
    if (!Array.isArray(labels) || labels.some((k) => !POINT_LABEL_KEYS.includes(k))) {
      throw new Error(
        `Invalid "point_label": expected a list of [${POINT_LABEL_KEYS.join(", ")}].`
      );
    }
    if (Number(this._config.t_min) >= Number(this._config.t_max)) {
      throw new Error('"t_min" must be smaller than "t_max".');
    }
    if (Number(this._config.x_min) >= Number(this._config.x_max)) {
      throw new Error('"x_min" must be smaller than "x_max".');
    }
    this._built = false;
  }

  set hass(hass) {
    const prev = this._hass;
    this._hass = hass;
    // Lovelace calls this on every state change in HA; only repaint when the
    // configured entity's state object actually changed (HA keeps the same
    // object reference while nothing changed).
    const ent = this._config && this._config.entity;
    if (this._built && prev && ent && prev.states[ent] === hass.states[ent]) {
      return;
    }
    this._render();
  }

  getCardSize() {
    return 6;
  }

  _t(key) {
    const lang = this._hass?.language ?? "en";
    return (I18N[lang] ?? I18N.en)[key] ?? I18N.en[key];
  }

  _build() {
    this.innerHTML = "";
    const card = document.createElement("ha-card");
    if (this._config.title) card.setAttribute("header", this._config.title);
    const content = document.createElement("div");
    content.style.padding = "4px 12px 12px";
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 480 300");
    svg.setAttribute("width", "100%");
    svg.style.display = "block";
    svg.style.fontFamily = "var(--paper-font-body1_-_font-family, sans-serif)";
    svg.style.fontSize = "11px";
    content.appendChild(svg);
    card.appendChild(content);
    this.appendChild(card);
    this._svg = svg;
    this._built = true;
  }

  _render() {
    if (!this._config) return;
    if (!this._built) this._build();
    const cfg = this._config;
    const svg = this._svg;
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    const W = 480;
    const H = 300;
    const m = { l: 48, r: 56, t: 16, b: 38 };
    const pw = W - m.l - m.r;
    const ph = H - m.t - m.b;

    const tMin = Number(cfg.t_min);
    const tMax = Number(cfg.t_max);
    const xMin = Number(cfg.x_min);
    const xMax = Number(cfg.x_max);

    const X = (t) => m.l + ((t - tMin) / (tMax - tMin)) * pw;
    const Y = (x) => m.t + ((xMax - x) / (xMax - xMin)) * ph; // x in g/kg

    const colText = "var(--secondary-text-color, #888)";
    const colGrid = "var(--divider-color, #ddd)";
    const colSat = "var(--info-color, #4099ff)";
    const colPoint = "var(--primary-color, #03a9f4)";
    const colCoolBlu = "var(--primary-color, #03a9f4)"; // beneficial part of cooling line
    const colCoolRed = "var(--error-color, #db4437)";   // detrimental part

    const add = (tag, attrs, parent = svg) => {
      const el = document.createElementNS(SVG_NS, tag);
      for (const k in attrs) el.setAttribute(k, attrs[k]);
      parent.appendChild(el);
      return el;
    };
    const text = (x, y, s, attrs = {}) => {
      const el = add("text", { x, y, fill: colText, ...attrs });
      el.textContent = s;
      return el;
    };

    // --- grid + axes ---
    for (let t = Math.ceil(tMin / 5) * 5; t <= tMax + 1e-9; t += 5) {
      const x = X(t);
      add("line", { x1: x, y1: m.t, x2: x, y2: m.t + ph, stroke: colGrid, "stroke-width": 0.5 });
      text(x, m.t + ph + 14, String(t), { "text-anchor": "middle" });
    }
    for (let x = Math.ceil(xMin / 5) * 5; x <= xMax + 1e-9; x += 5) {
      const y = Y(x);
      add("line", { x1: m.l, y1: y, x2: m.l + pw, y2: y, stroke: colGrid, "stroke-width": 0.5 });
      text(m.l + pw + 6, y + 3, String(x), { "text-anchor": "start" });
    }
    add("rect", { x: m.l, y: m.t, width: pw, height: ph, fill: "none", stroke: colGrid, "stroke-width": 1 });
    text(m.l + pw / 2, H - 4, this._t("xAxis"), { "text-anchor": "middle" });
    text(W - 4, m.t - 4, "x [g/kg]", { "text-anchor": "end" });

    // --- effective ambient pressure (hPa attribute -> Pa) ---
    const st = this._hass && this._hass.states ? this._hass.states[cfg.entity] : undefined;
    const pHpa = st ? Number(st.attributes.pressure) : NaN;
    const pPa = Number.isFinite(pHpa) && pHpa > 0 ? pHpa * 100 : 101325;

    // --- constant relative-humidity curves, clamped to the chart bounds ---
    // Each curve x(T) = wRH(T, p, rh) rises monotonically with T, so it enters
    // the plot area once through the bottom edge (x = xMin) and leaves once
    // through the top edge (x = xMax); both crossings are interpolated so the
    // visible path stays inside [xMin, xMax]. The returned point is where the
    // visible curve ends, used to anchor a label.
    const rhPath = (rh) => {
      let d = "";
      let pT = null;
      let pX = null;
      let endT = null;
      let endX = null;
      for (let t = tMin; t <= tMax + 1e-9; t += 1) {
        const xg = wRH(t, pPa, rh) * 1000;
        // Entering from below the bottom edge: start the path at xMin.
        if (pT !== null && pX < xMin && xg >= xMin) {
          const f = (xMin - pX) / (xg - pX);
          const te = pT + f * (t - pT);
          d += (d === "" ? "M" : "L") + X(te).toFixed(1) + " " + Y(xMin).toFixed(1) + " ";
          endT = te;
          endX = xMin;
        }
        // Leaving through the top edge: finish the path at xMax and stop.
        if (pT !== null && pX <= xMax && xg > xMax) {
          const f = (xMax - pX) / (xg - pX);
          const tc = pT + f * (t - pT);
          d += (d === "" ? "M" : "L") + X(tc).toFixed(1) + " " + Y(xMax).toFixed(1) + " ";
          endT = tc;
          endX = xMax;
          break;
        }
        if (xg >= xMin && xg <= xMax) {
          d += (d === "" ? "M" : "L") + X(t).toFixed(1) + " " + Y(xg).toFixed(1) + " ";
          endT = t;
          endX = xg;
        }
        pT = t;
        pX = xg;
      }
      return { d, endT, endX };
    };

    // rh_lines = N draws N equally spaced curves at i/N for i = 1..N, so the
    // top one is the saturation curve (100% RH) and 0% RH is never drawn; N = 0
    // draws nothing. Lower-RH lines are drawn first so the saturation curve and
    // the state point sit on top. The saturation curve is thick and labelled via
    // the legend; the inner iso-lines are thin, dimmed, and labelled in place.
    const nRH = Number(cfg.rh_lines);
    for (let i = 1; i <= nRH; i++) {
      const rh = i / nRH;
      const { d, endT, endX } = rhPath(rh);
      if (!d) continue;
      if (rh >= 1 - 1e-9) {
        add("path", { d, fill: "none", stroke: colSat, "stroke-width": 1.5 });
      } else {
        add("path", {
          d, fill: "none", stroke: colSat, "stroke-width": 0.75, opacity: 0.5,
        });
        if (endT !== null) {
          text(X(endT) - 2, Y(endX) - 3, Math.round(rh * 100) + "%", {
            "text-anchor": "end", fill: colSat, opacity: 0.8, "font-size": "9px",
          });
        }
      }
    }

    // --- current state + isenthalpic cooling line ---
    const a = st ? st.attributes : {};
    const T = Number(a.temperature);
    const xg = Number(a.mixing_ratio); // g/kg
    const dxdt = Number(a.dx_dt); // kg/kg per K (SI)
    const havePoint = Number.isFinite(T) && Number.isFinite(xg);

    if (havePoint) {
      if (Number.isFinite(dxdt) && dxdt !== 0) {
        const seg = this._coolingLine(T, xg / 1000, dxdt, pPa, tMin, xMax / 1000);
        if (seg && seg.t < T - 1e-6) {
          // Dash patterns differ so color-blind users can also distinguish segments.
          const dashBlu = { "stroke-width": 2, "stroke-dasharray": "5 3", "stroke-linecap": "round" };
          const dashRed = { "stroke-width": 2, "stroke-dasharray": "2 5", "stroke-linecap": "round" };
          const hasOpt = seg.tOpt !== null && seg.tOpt > seg.t + 1e-6 && seg.tOpt < T - 1e-6;
          if (hasOpt) {
            const xgOpt = (xg / 1000 + dxdt * (seg.tOpt - T)) * 1000; // g/kg at optimum
            add("line", { x1: X(T), y1: Y(xg), x2: X(seg.tOpt), y2: Y(xgOpt),
              stroke: colCoolBlu, ...dashBlu });
            add("line", { x1: X(seg.tOpt), y1: Y(xgOpt), x2: X(seg.t), y2: Y(seg.x * 1000),
              stroke: colCoolRed, ...dashRed });
          } else {
            const beneficial = _dHICooling(T, xg / 1000, dxdt) >= 0;
            add("line", { x1: X(T), y1: Y(xg), x2: X(seg.t), y2: Y(seg.x * 1000),
              stroke: beneficial ? colCoolBlu : colCoolRed,
              ...(beneficial ? dashBlu : dashRed) });
          }
        }
      }
      add("circle", {
        cx: X(T), cy: Y(xg), r: 5, fill: colPoint,
        stroke: "var(--card-background-color, #fff)", "stroke-width": 1.5,
      });
      // Label content is selected via point_label; each value is dropped when
      // it is not available, and the whole label is skipped when none remain.
      const hi = Number(a.heat_index);
      const rh = rhFromW(xg / 1000, T, pPa);
      const parts = {
        t: T.toFixed(1) + " °C",
        x: xg.toFixed(1) + " g/kg",
        hi: Number.isFinite(hi) ? "HI " + hi.toFixed(1) + " °C" : null,
        rh: Number.isFinite(rh) ? "RH " + Math.round(rh * 100) + " %" : null,
      };
      const lbl = cfg.point_label.map((k) => parts[k]).filter(Boolean).join(" · ");
      if (lbl) {
        text(X(T) + 9, Y(xg) - 8, lbl, {
          "text-anchor": "start", fill: "var(--primary-text-color, #212121)",
        });
      }
    } else {
      text(m.l + pw / 2, m.t + ph / 2, this._t("unavailable"), {
        "text-anchor": "middle", fill: colText,
      });
    }

    // --- legend (upper-left, above the saturation curve) ---
    const legend = [];
    if (nRH >= 1) {
      legend.push({ c: colSat, s: this._t("saturation") });
    }
    if (nRH >= 2) {
      const step = 100 / nRH;
      const lo = Math.round(step);
      const hi = Math.round((nRH - 1) * step);
      const range = lo === hi ? lo + "%" : lo + "–" + hi + "%";
      legend.push({ c: colSat, thin: true, s: this._t("relHumidity") + range });
    }
    legend.push({ c: colPoint, dot: true, s: this._t("currentState") });
    legend.push({ c: colCoolBlu, dashArray: "5 3", s: this._t("coolingBeneficial") });
    legend.push({ c: colCoolRed, dashArray: "2 5", s: this._t("coolingDetrimental") });
    let ly = m.t + 12;
    for (const it of legend) {
      if (it.dot) {
        add("circle", { cx: m.l + 13, cy: ly - 3, r: 4, fill: it.c });
      } else {
        add("line", {
          x1: m.l + 6, y1: ly - 3, x2: m.l + 20, y2: ly - 3,
          stroke: it.c, "stroke-width": it.thin ? 0.75 : 2,
          ...(it.thin ? { opacity: 0.5 } : {}),
          ...(it.dashArray ? { "stroke-dasharray": it.dashArray } : {}),
        });
      }
      text(m.l + 26, ly, it.s, { "text-anchor": "start" });
      ly += 15;
    }
  }

  // Isenthalpic cooling line end point {t, x(kg/kg), tOpt}: walk T down, x
  // rises, stop at the saturation curve or the chart bounds.  tOpt is the
  // temperature where _dHICooling changes sign from positive (beneficial) to
  // negative (detrimental), or null when no such crossing exists in the path.
  _coolingLine(t0, x0, dxdt, p, tFloor, xCeil) {
    const xLine = (t) => x0 + dxdt * (t - t0);
    // Already at/above saturation: evaporative cooling can't help; collapse.
    if (xLine(t0) >= wSat(t0, p)) return { t: t0, x: xLine(t0), tOpt: null };
    let t = t0;
    const step = 0.1;
    let prevDHI = _dHICooling(t0, x0, dxdt);
    let tOpt = null;
    for (let i = 0; i < 2000; i++) {
      const tn = t - step;
      const xn = xLine(tn);
      const currDHI = _dHICooling(tn, xn, dxdt);
      // Detect the first beneficial → detrimental crossing (+ → −).
      if (tOpt === null && prevDHI > 0 && currDHI <= 0) {
        const f = prevDHI / (prevDHI - currDHI); // linear interpolation fraction
        tOpt = t - f * step;
      }
      if (xn >= wSat(tn, p)) {
        // Crossing in [tn, t]: interpolate the residual (line - wSat) to zero so
        // the endpoint lands exactly on the saturation curve, not above it.
        const r = xLine(t) - wSat(t, p);
        const rn = xn - wSat(tn, p);
        const tc = t + (r / (r - rn)) * (tn - t);
        return { t: tc, x: wSat(tc, p), tOpt };
      }
      if (tn <= tFloor || xn >= xCeil) {
        // Interpolate the exact boundary crossing rather than clamping, so the
        // returned point always lies on the isenthalpic line.
        const hits = [];
        if (tn <= tFloor) hits.push({ t: tFloor, x: xLine(tFloor) });
        if (xn >= xCeil) {
          const f = (xCeil - xLine(t)) / (xn - xLine(t));
          hits.push({ t: t + f * (tn - t), x: xCeil });
        }
        const end = hits.reduce(
          (best, hit) => (best === null || hit.t > best.t ? hit : best),
          null
        );
        return { ...end, tOpt };
      }
      t = tn;
      prevDHI = currDHI;
    }
    return { t, x: xLine(t), tOpt };
  }
}

if (!customElements.get("poormansac-psychrometric-card")) {
  customElements.define("poormansac-psychrometric-card", PoorMansACPsychrometricCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "poormansac-psychrometric-card",
  name: "Poor Man's AC Psychrometric Chart",
  description:
    "Carrier psychrometric chart with the current air state and the adiabatic (evaporative) cooling line.",
  preview: false,
  documentationURL: "https://github.com/da-sa-li/poormansac",
});
