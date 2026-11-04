#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera data.js para el sitio de consulta STJ.

Fuentes:
  - Consolidado PuntoEdu P1 y P2 (informe=2): nota del ÁREA y de cada
    asignatura por periodo.
  - Consolidado "Notas necesarias último periodo" (PuntoEdu): la nota que
    cada estudiante necesita en P3 por área y asignatura — VALOR OFICIAL,
    se publica tal cual (semántica verificada: coincide con la fórmula
    SIEE 2.1.17 definitiva = P1*30% + P2*30% + P3*40%, aprueba >= 3.0).
  - Hoja Drive "BD - STJ - 2026" (Main) → _fuente/mapa_codigos.json:
    CÓDIGO DEL PORTAL ESTUDIANTES (el del login, NO el id interno de
    PuntoEdu). Alias 115 = Giraldo Taba Juanita (fila de la hoja quedó
    como placeholder 'Juanita Juanita').
  - Base local estudiantes_stj.db: número de documento (contraseña).
    El documento NUNCA se publica: solo SHA-256(salt+doc).

Uso:
    python3 scripts/generar_data.py \
        [--p1 XLS] [--p2 XLS] [--nec JSON] [--db DB]

El JSON de notas necesarias se produce una vez por corte desde el PDF
oficial (ver scripts/extraer_necesarias.py).
"""
import argparse, hashlib, json, os, re, sqlite3, unicodedata, uuid

# Avisos individuales (decisión de dirección; se muestran tal cual al estudiante)
AVISOS = {
    "LEON RIOS": (
        "📌 Atención: no tienes notas del primer periodo cargadas en el sistema. "
        "Tu nota del primer periodo será el promedio del primero y el segundo periodo."
    ),
}

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRUPO_DB = "12"  # ID interno de 10A en PuntoEdu

# 11 áreas académicas del Informe de Jornada (REL y COMP_SOC quedan fuera:
# religión no decide promoción y COMP_SOC es comportamiento)
AREAS = ["A.NAT", "C.SOC", "C.E.P", "FIL", "A.MAT.GEO", "L.CAST", "ING",
         "ED_ART", "ET_VAL", "ED_FIS", "TEC_INF"]
AREA_NOMBRE = {
    "A.NAT": "Ciencias Naturales", "C.SOC": "Ciencias Sociales",
    "C.E.P": "Ciencias Económicas y Políticas", "FIL": "Filosofía",
    "A.MAT.GEO": "Matemáticas", "L.CAST": "Lengua Castellana", "ING": "Inglés",
    "ED_ART": "Educación Artística", "ET_VAL": "Ética y Valores",
    "ED_FIS": "Educación Física", "TEC_INF": "Tecnología e Informática",
}
SUBS = {"A.NAT": ["QUIM", "FIS", "C.NAT"], "A.MAT.GEO": ["Geom.Anali", "MAT"]}
SUB_NOMBRE = {"QUIM": "Química", "FIS": "Física", "C.NAT": "Biología",
              "Geom.Anali": "Geometría Analítica", "MAT": "Matemáticas"}
# columnas del consolidado de notas necesarias / consolidados P1-P2, en orden
NEC_COLS = ["A.NAT", "QUIM", "FIS", "C.NAT", "C.SOC", "C.E.P", "FIL",
            "A.MAT.GEO", "Geom.Anali", "MAT", "L.CAST", "ING", "ED_ART",
            "REL", "ET_VAL", "ED_FIS", "TEC_INF", "COMP_SOC"]
SUB = re.compile(r"\(\s*\d+[.,]?\d*\s*%\s*\)")
META = {"Nro", "NOMBRE LOS ESTUDIANTES", "PROM", "PUESTO", "TOTAL SUPERIOR",
        "TOTAL ALTO", "TOTAL BASICO", "TOTAL BAJO", "PROMOCION"}


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.upper()).strip()


def nota(cell):
    if cell in (None, ""):
        return None
    try:
        v = float(cell)
        return round(v, 2) if v > 0 else None  # 0.0 = sin nota cargada
    except (TypeError, ValueError):
        return None


def parse_consolidado(path):
    """{nombre: {col: nota}} con col según el orden de NEC_COLS."""
    import xlrd
    wb = xlrd.open_workbook(path, ignore_workbook_corruption=True)
    sh = wb.sheet_by_index(0)
    hr = next(r for r in range(sh.nrows)
              if str(sh.cell_value(r, 0)).strip().upper() == "NRO")
    hdr = [str(sh.cell_value(hr, c)).strip() for c in range(sh.ncols)]
    nota_cols = [c for c, h in enumerate(hdr) if h and h not in META]
    data = {}
    for r in range(hr + 1, sh.nrows):
        nom = str(sh.cell_value(r, 1)).strip()
        nro = str(sh.cell_value(r, 0)).strip()
        if not nom or not re.match(r"^\d+(\.0)?$", nro):
            continue
        vals = {}
        for i, c in enumerate(nota_cols[:18]):
            vals[NEC_COLS[i]] = nota(sh.cell_value(r, c))
        data[nom] = vals
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--p1", default=os.path.join(BASE, "_fuente", "consolidado_excel_10_P1.xls"))
    ap.add_argument("--p2", default=os.path.join(BASE, "_fuente", "consolidado_excel_10_P2.xls"))
    ap.add_argument("--nec", default=os.path.join(BASE, "_fuente", "necesarias_10A.json"))
    ap.add_argument("--db", default="/home/camilo/.hermes/profiles/colegio/datos/estudiantes_stj.db")
    a = ap.parse_args()

    p1 = parse_consolidado(a.p1)
    p2 = parse_consolidado(a.p2)
    with open(a.nec, encoding="utf-8") as fh:
        nec_raw = json.load(fh)
    nec = {norm(d["nombre"]): {NEC_COLS[i]: float(v)
                               for i, v in enumerate(d["vals"])}
           for d in nec_raw}

    con = sqlite3.connect(a.db)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM estudiantes WHERE curso=?", (GRUPO_DB,)).fetchall()
    con.close()
    db_by_nombre = {}
    for r in rows:
        for clave in (norm(r["apellido"] + " " + (r["nombres"] or "")),
                      norm(r["nombre_completo"] or "")):
            db_by_nombre.setdefault(clave, r)

    with open(os.path.join(BASE, "_fuente", "mapa_codigos.json"), encoding="utf-8") as fh:
        mapa_codigos = json.load(fh)

    salt = ""
    out_path = os.path.join(BASE, "data.js")
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as fh:
            m = re.search(r'"salt":"([0-9a-f]+)"', fh.read())
            salt = m.group(1) if m else ""
    salt = salt or uuid.uuid4().hex

    import hashlib
    estudiantes, problemas, sin_nota, desajustes, logins = [], [], [], [], []
    for nombre in sorted(p1):
        row = db_by_nombre.get(norm(nombre))
        if row is None or not row["num_doc"]:
            problemas.append(f"sin cruce en base local: {nombre}")
            continue
        codigo = mapa_codigos.get(nombre)
        if not codigo:
            problemas.append(f"sin código de portal (hoja BD): {nombre}")
            continue
        nn = norm(nombre)
        if nn not in nec:
            problemas.append(f"sin nota necesaria (documento): {nombre}")
            continue
        doc = re.sub(r"\D", "", str(row["num_doc"]))
        h = hashlib.sha256((salt + doc).encode()).hexdigest()
        ar, subs = {}, {}
        for sigla in AREAS:
            n1, n2 = p1[nombre].get(sigla), p2[nombre].get(sigla)
            req = nec[nn].get(sigla)
            if n1 is None or n2 is None:
                sin_nota.append(f"{nombre}·{sigla}")
            ar[sigla] = [n1, n2, req]
            for s_ in SUBS.get(sigla, []):
                subs[s_] = [p1[nombre].get(s_), p2[nombre].get(s_), nec[nn].get(s_)]
            # QA informativa: coherencia documento vs fórmula SIEE
            if n1 is not None and n2 is not None and req is not None:
                calc = round((3.0 - 0.3 * (n1 + n2)) / 0.4 + 1e-9, 1)
                if abs(calc - req) > 0.05:
                    desajustes.append(f"{nombre.split()[0]}·{sigla}: doc={req} calc={calc}")
        est = {
            "c": codigo,
            "n": f'{(row["nombres"] or "").title()} {(row["apellido"] or "").title()}',
            "h": h, "ar": ar, "subs": subs,
        }
        aviso = next((t for frag, t in AVISOS.items() if norm(frag) in nn), "")
        if aviso:
            est["aviso"] = aviso
        estudiantes.append(est)
        logins.append((est["n"], codigo, str(row["num_doc"])))
    if len({e["c"] for e in estudiantes}) != len(estudiantes):
        problemas.append("códigos duplicados")

    areas_out = [{"s": s, "n": AREA_NOMBRE[s],
                  "subs": [{"s": x, "n": SUB_NOMBRE[x]} for x in SUBS.get(s, [])]}
                 for s in AREAS]
    data = {
        "salt": salt,
        "meta": {"grupo": "10A", "sede": "IE Santa Teresa de Jesús, Armenia",
                 "corte": "2026-11-04",
                 "fuente": "PuntoEdu · Consolidado P1 y P2 + Notas necesarias último periodo",
                 "formula": "Definitiva = P1×30% + P2×30% + P3×40% (SIEE 2.1.17) · se aprueba con 3.0 o más"},
        "areas": areas_out,
        "estudiantes": estudiantes,
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("window.__NOTAS_DATA = ")
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")

    # ---------- QA ----------
    print(f"estudiantes publicados: {len(estudiantes)} / consolidado: {len(p1)} / base: {len(rows)} / doc: {len(nec)}")
    for p in problemas:
        print("PROBLEMA:", p)
    if sin_nota:
        print(f"celdas sin nota P1/P2 ({len(sin_nota)}):", "; ".join(sin_nota))
    print(f"desajustes doc vs fórmula ({len(desajustes)}):")
    for d in desajustes:
        print("  ", d)
    est = {"asegurada": 0, "alcanzable": 0, "recuperacion": 0}
    for e in estudiantes:
        for sigla in AREAS:
            req = e["ar"][sigla][2]
            if req is None:
                continue
            est["asegurada" if req <= 0 else "recuperacion" if req > 5 else "alcanzable"] += 1
    print("estados según documento (estudiante×área):", est)

    # ---------- logins (FUERA del repo público) ----------
    logins_path = os.path.join(os.path.dirname(BASE), "logins-10A.md")
    lineas = [
        "# Logins plataforma de notas · 10°A (corte 2026-11-04)", "",
        "Código = el del portal estudiantes (hoja BD - STJ - 2026, pestaña Main).",
        "Contraseña = número de documento.",
        "⚠️ Este archivo NO va al repo público.", "",
        "| # | Estudiante | Código | Contraseña (documento) |",
        "|---|---|---|---|",
    ]
    for i, (n, c, d) in enumerate(logins, 1):
        lineas.append(f"| {i} | {n} | {c} | {d} |")
    with open(logins_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas) + "\n")
    print(f"-> {logins_path} ({len(logins)} logins)")
    print("->", out_path)


if __name__ == "__main__":
    main()
