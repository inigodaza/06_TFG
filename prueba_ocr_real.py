"""
¿Sabe este sistema leer un documento que no ha visto nunca?

Los 13 escaneos de Martín tienen su texto guardado en un `.ocr.txt`, así que al
abrirlos la app no reconoce nada: lee lo ya reconocido. Eso hace la demo
utilizable, pero deja sin responder la única pregunta que importa de cara a un
documento nuevo — **¿funciona el reconocimiento, o funciona la caché?**

Este script apaga la caché y obliga al sistema a reconocer los 13 desde el PDF,
como haría con un documento que llegara mañana. Después extrae los campos del
texto reconocido y lo compara con lo que sale por el camino rápido. Si los dos
coinciden, la caché no está tapando nada: es el mismo trabajo, hecho antes.

    python3 prueba_ocr_real.py [--solo N]
"""

import re
import sys
import time
from pathlib import Path

from nucleo import pdf as P
from modulos import vigencia as V

CORPUS = Path("demo/datos/vigencia")
CAMPOS = [("fecha_emision", "firma"), ("fecha_inicio", "inicio"),
          ("anios_pactados", "plazo"), ("fecha_caducidad", "vencimiento"),
          ("prorroga_tipo", "prórroga"), ("antelacion", "preaviso"),
          ("familia", "familia"), ("direccion_objeto", "cadena")]


def campos_de(texto):
    c = V.extraer(texto) or {}
    return {k for k, _ in CAMPOS if c.get(k) not in (None, "", "no_consta", {}, [])}


def normalizar(t):
    return re.sub(r"\s+", " ", t or "").strip()


def parecido(a, b):
    """Porcentaje de palabras del texto guardado que reaparecen en el nuevo."""
    pa, pb = normalizar(a).lower().split(), set(normalizar(b).lower().split())
    if not pa:
        return 0.0
    return 100.0 * sum(1 for p in pa if p in pb) / len(pa)


def main(limite=None):
    docs = [p for p in sorted(CORPUS.glob("*.pdf"))
            if not p.stem.startswith("PRUEBA_")][:limite]
    print(f"Reconocimiento real de {len(docs)} documento(s), sin tocar la caché.\n")
    print(f"{'documento':46}{'pág':>4}{'seg':>7}{'car':>9}{'campos':>8}"
          f"{'=caché':>8}{'parecido':>10}")
    print("-" * 92)

    filas, t_total = [], time.time()
    for p in docs:
        guardado = Path(str(p)[:-4] + ".ocr.txt")
        texto_guardado = (guardado.read_text(encoding="utf-8")
                          if guardado.is_file() else "")
        oculto = guardado.with_suffix(".escondido")
        if guardado.is_file():
            guardado.rename(oculto)
        try:
            t0 = time.time()
            d = P.leer(p)
            seg = time.time() - t0
        finally:
            if oculto.is_file():
                oculto.rename(guardado)

        c_nuevo = campos_de(d["texto"])
        c_viejo = campos_de(texto_guardado) if texto_guardado else set()
        igual = "sí" if c_nuevo == c_viejo else "NO"
        sim = parecido(texto_guardado, d["texto"]) if texto_guardado else 0.0
        filas.append((p.stem, d, seg, c_nuevo, c_viejo, sim))
        print(f"{p.stem[:44]:46}{d['paginas']:>4}{seg:>7.0f}"
              f"{len(d['texto']):>9,}{len(c_nuevo):>6}/8{igual:>8}{sim:>9.1f}%"
              .replace(",", "."))

    print("-" * 92)
    print(f"{'TOTAL':46}{sum(f[1]['paginas'] for f in filas):>4}"
          f"{time.time()-t_total:>7.0f}")

    legibles = [f for f in filas if f[1]["legible"]]
    iguales = [f for f in filas if f[3] == f[4]]
    print(f"\n  Reconocidos con texto utilizable   {len(legibles)} de {len(filas)}")
    print(f"  Mismos campos que por la caché     {len(iguales)} de {len(filas)}")
    if filas:
        print(f"  Parecido medio con lo guardado     "
              f"{sum(f[5] for f in filas)/len(filas):5.1f} %")
        print(f"  Campos leídos en total             "
              f"{sum(len(f[3]) for f in filas)} de {8*len(filas)}")

    distintos = [f for f in filas if f[3] != f[4]]
    if distintos:
        print("\n  Dónde difiere el reconocimiento de lo guardado:")
        for nombre, _d, _s, nuevo, viejo, _sim in distintos:
            print(f"    · {nombre[:44]:46} "
                  f"sólo ahora: {sorted(nuevo - viejo) or '—'} · "
                  f"sólo antes: {sorted(viejo - nuevo) or '—'}")
    return 0


if __name__ == "__main__":
    n = None
    if "--solo" in sys.argv:
        n = int(sys.argv[sys.argv.index("--solo") + 1])
    sys.exit(main(n))
