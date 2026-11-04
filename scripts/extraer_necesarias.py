#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrae la tabla del PDF oficial "Consolidado notas necesarias último
periodo" (PuntoEdu) a JSON para generar_data.py.

Método: extract_text(extraction_mode="layout") — estable entre versiones de
pypdf (el visitor por coordenadas cambió de comportamiento en pypdf 6.x).
Cada fila de estudiante es una línea con Nro + nombre + 18 notas en este
orden: A.NAT QUIM FIS C.NAT C.SOC C.E.P FIL A.MAT.GEO Geom.Anali MAT L.CAST
ING ED_ART REL ET_VAL ED_FIS TEC_INF COMP_SOC.

Uso:
    python3 scripts/extraer_necesarias.py PDF.pdf [--out _fuente/necesarias_10A.json]
"""
import argparse, json, os, re

FILA_RE = re.compile(r"^\s{0,4}(\d{1,2})\s+([A-ZÁÉÍÓÚÑ].*?)((?:\s+\d\.\d){18})\s*$")


def extraer(pdf_path):
    from pypdf import PdfReader
    r = PdfReader(pdf_path)
    tabla = []
    for p in r.pages:
        texto = p.extract_text(extraction_mode="layout")
        for line in texto.splitlines():
            m = FILA_RE.match(line)
            if not m:
                continue
            nro, nombre, notas = int(m.group(1)), m.group(2).strip(), m.group(3).split()
            tabla.append({"nro": nro, "nombre": re.sub(r"\s+", " ", nombre),
                          "vals": notas})
    # deduplicar por si una fila se imprimiera dos veces
    vistos, unicos = set(), []
    for d in tabla:
        if d["nro"] in vistos:
            continue
        vistos.add(d["nro"])
        unicos.append(d)
    unicos.sort(key=lambda d: d["nro"])
    return unicos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "_fuente", "necesarias_10A.json"))
    a = ap.parse_args()
    tabla = extraer(a.pdf)
    if len(tabla) < 10:
        raise SystemExit(f"solo {len(tabla)} filas extraídas — revisar PDF")
    for d in tabla:
        assert len(d["vals"]) == 18, f"fila {d['nro']} sin 18 notas"
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(tabla, fh, ensure_ascii=False, indent=1)
    print(f"OK: {len(tabla)} estudiantes -> {a.out}")
    print("primera fila:", tabla[0]["nombre"], tabla[0]["vals"][:6], "...")


if __name__ == "__main__":
    main()
