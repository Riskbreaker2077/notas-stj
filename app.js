/* Consulta de notas 10°A · STJ — estático, sin dependencias.
   Login: código (id PuntoEdu) + documento (verificación por SHA-256 con salt).
   La nota necesaria se muestra tal como viene del consolidado oficial. */
(function () {
  "use strict";
  const D = window.__NOTAS_DATA;
  const $ = (id) => document.getElementById(id);
  const loginView = $("login-view"), resultView = $("result-view");
  const form = $("login-form"), err = $("login-error");
  const toggleDocBtn = $("toggle-doc"), docInput = $("doc");

  const sha256hex = async (s) => {
    const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
    return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, "0")).join("");
  };

  const fmt = (v) => (v === null || v === undefined) ? "—" : (Math.round(v * 10) / 10).toFixed(1);
  const baja = (v) => (v !== null && v !== undefined && v < 3);

  function estadoCell(req) {
    if (req === null || req === undefined) return { cls: "gris", req: "—", txt: "Sin dato" };
    if (req <= 0) return { cls: "ok", req: "0.0", txt: "Asegurada" };
    if (req > 5) return { cls: "bad", req: fmt(req), txt: "Recuperación final" };
    return { cls: "warn", req: fmt(req), txt: "Con " + fmt(req) + " o más pasas" };
  }

  function fila(nombre, s, sub) {
    const e = estadoCell(s ? s[2] : null);
    const p1 = s ? s[0] : null, p2 = s ? s[1] : null;
    const tdNota = (v) => (v === null || v === undefined)
      ? '<span class="na">—</span>'
      : '<span class="nota-val">' + fmt(v) + "</span>";
    const labelHtml = sub
      ? '<span class="sub-name"><span class="sub-arrow" aria-hidden="true">↳</span><span>' + nombre + "</span></span>"
      : '<span class="area-name">' + nombre + "</span>";

    return '<tr class="' + (sub ? "subrow" : "arearow") + '">' +
      "<td>" + labelHtml + "</td>" +
      '<td class="nota' + (baja(p1) ? " baja" : "") + '">' + tdNota(p1) + "</td>" +
      '<td class="nota' + (baja(p2) ? " baja" : "") + '">' + tdNota(p2) + "</td>" +
      '<td><div class="req-wrap"><span class="req ' + e.cls + '">' + e.req + '</span><span class="estado ' + e.cls + '">' + e.txt + "</span></div></td>" +
      "</tr>";
  }

  function render(est) {
    $("student-name").textContent = est.n;
    const sedeTxt = D.meta && D.meta.sede ? " · " + D.meta.sede : "";
    $("student-meta").textContent = "Grupo " + D.meta.grupo + sedeTxt + " · Código " + est.c;

    const prev = $("aviso-banner");
    if (prev) prev.remove();
    if (est.aviso) {
      const div = document.createElement("div");
      div.id = "aviso-banner";
      div.className = "aviso";
      div.setAttribute("role", "status");
      div.textContent = est.aviso;
      $("summary").insertAdjacentElement("beforebegin", div);
    }

    let ok = 0, warn = 0, bad = 0, gris = 0;
    for (const a of D.areas) {
      const cls = estadoCell((est.ar[a.s] || [])[2]).cls;
      if (cls === "ok") ok++; else if (cls === "warn") warn++;
      else if (cls === "bad") bad++; else gris++;
    }
    const chips = [];
    if (ok) chips.push('<span class="chip ok">' + ok + " asegurada" + (ok > 1 ? "s" : "") + "</span>");
    if (warn) chips.push('<span class="chip warn">' + warn + " por asegurar</span>");
    if (bad) chips.push('<span class="chip bad">' + bad + " sin posibilidad</span>");
    if (gris) chips.push('<span class="chip gris">' + gris + " sin dato</span>");
    $("summary").innerHTML = chips.join("");

    let html = "";
    for (const a of D.areas) {
      html += fila(a.n, est.ar[a.s], false);
      for (const sub of (a.subs || [])) html += fila(sub.n, est.subs[sub.s], true);
    }
    $("grades-body").innerHTML = html;

    $("foot-meta").textContent = D.meta.grupo + " · corte " + D.meta.corte + " · " + D.meta.fuente;

    loginView.hidden = true;
    resultView.hidden = false;
  }

  async function intentar(codigo, doc) {
    const digits = (doc || "").replace(/\D/g, "");
    if (!digits || !codigo) return null;
    const alts = new Set([digits, digits.replace(/^0+/, "")]);
    const hs = [];
    for (const a of alts) if (a) hs.push(await sha256hex(D.salt + a));
    return D.estudiantes.find((e) => e.c === codigo && hs.indexOf(e.h) >= 0) || null;
  }

  if (toggleDocBtn && docInput) {
    toggleDocBtn.addEventListener("click", () => {
      const isPwd = docInput.type === "password";
      docInput.type = isPwd ? "text" : "password";
      toggleDocBtn.setAttribute("aria-pressed", String(isPwd));
    });
  }

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    err.hidden = true;
    const est = await intentar($("codigo").value.trim(), $("doc").value);
    if (!est) { err.hidden = false; return; }
    sessionStorage.setItem("stj_codigo", est.c);
    render(est);
  });

  $("logout").addEventListener("click", () => {
    sessionStorage.removeItem("stj_codigo");
    resultView.hidden = true;
    loginView.hidden = false;
    if (docInput) docInput.type = "password";
    form.reset();
  });

  const saved = sessionStorage.getItem("stj_codigo");
  if (saved) {
    const est = D.estudiantes.find((e) => e.c === saved);
    if (est) render(est);
    else sessionStorage.removeItem("stj_codigo");
  }
})();
