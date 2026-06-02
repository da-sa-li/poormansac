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

// Saturation mixing ratio in kg_water/kg_dry_air from T (degC) and pressure (Pa).
const wSat = (t, p) => {
  const e = eSat(t);
  return (EPSILON * e) / (p - e);
};

const SVG_NS = "http://www.w3.org/2000/svg";

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
      t_max: 45,
      x_min: 0,
      x_max: 30,
      ...config,
    };
    this._built = false;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 6;
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
    const colCool = "var(--error-color, #db4437)";

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
    text(m.l + pw / 2, H - 4, "Dry-bulb temperature [°C]", { "text-anchor": "middle" });
    text(W - 4, m.t - 4, "x [g/kg]", { "text-anchor": "end" });

    // --- effective ambient pressure (hPa attribute -> Pa) ---
    const st = this._hass && this._hass.states ? this._hass.states[cfg.entity] : undefined;
    const pHpa = st ? Number(st.attributes.pressure) : NaN;
    const pPa = Number.isFinite(pHpa) && pHpa > 0 ? pHpa * 100 : 101325;

    // --- saturation curve (100% RH), clamped to the top edge ---
    let d = "";
    let pT = null;
    let pX = null;
    for (let t = tMin; t <= tMax + 1e-9; t += 1) {
      const xg = wSat(t, pPa) * 1000;
      if (xg <= xMax) {
        d += (d === "" ? "M" : "L") + X(t).toFixed(1) + " " + Y(xg).toFixed(1) + " ";
        pT = t;
        pX = xg;
      } else {
        if (pT !== null) {
          const f = (xMax - pX) / (xg - pX);
          const tc = pT + f * (t - pT);
          d += "L" + X(tc).toFixed(1) + " " + Y(xMax).toFixed(1) + " ";
        }
        break;
      }
    }
    add("path", { d, fill: "none", stroke: colSat, "stroke-width": 1.5 });

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
          add("line", {
            x1: X(T), y1: Y(xg), x2: X(seg.t), y2: Y(seg.x * 1000),
            stroke: colCool, "stroke-width": 2, "stroke-dasharray": "5 3",
            "stroke-linecap": "round",
          });
        }
      }
      add("circle", {
        cx: X(T), cy: Y(xg), r: 5, fill: colPoint,
        stroke: "var(--card-background-color, #fff)", "stroke-width": 1.5,
      });
      const hi = Number(a.heat_index);
      const lbl =
        T.toFixed(1) + " °C · " + xg.toFixed(1) + " g/kg" +
        (Number.isFinite(hi) ? " · HI " + hi.toFixed(1) + " °C" : "");
      text(X(T) + 9, Y(xg) - 8, lbl, {
        "text-anchor": "start", fill: "var(--primary-text-color, #212121)",
      });
    } else {
      text(m.l + pw / 2, m.t + ph / 2, "State unavailable", {
        "text-anchor": "middle", fill: colText,
      });
    }

    // --- legend (upper-left, above the saturation curve) ---
    const legend = [
      { c: colSat, s: "Saturation (100% RH)" },
      { c: colPoint, dot: true, s: "Current state" },
      { c: colCool, dash: true, s: "Cooling line" },
    ];
    let ly = m.t + 12;
    for (const it of legend) {
      if (it.dot) {
        add("circle", { cx: m.l + 13, cy: ly - 3, r: 4, fill: it.c });
      } else {
        add("line", {
          x1: m.l + 6, y1: ly - 3, x2: m.l + 20, y2: ly - 3,
          stroke: it.c, "stroke-width": 2,
          ...(it.dash ? { "stroke-dasharray": "5 3" } : {}),
        });
      }
      text(m.l + 26, ly, it.s, { "text-anchor": "start" });
      ly += 15;
    }
  }

  // Isenthalpic cooling line end point {t, x(kg/kg)}: walk T down, x rises,
  // stop at the saturation curve or the chart bounds.
  _coolingLine(t0, x0, dxdt, p, tFloor, xCeil) {
    let t = t0;
    const step = 0.1;
    for (let i = 0; i < 2000; i++) {
      const tn = t - step;
      const xn = x0 + dxdt * (tn - t0);
      if (xn >= wSat(tn, p) || tn <= tFloor || xn >= xCeil) {
        return { t: Math.max(tn, tFloor), x: Math.min(xn, xCeil) };
      }
      t = tn;
    }
    return { t, x: x0 + dxdt * (t - t0) };
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
