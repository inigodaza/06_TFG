"""
El ciclo de mejora: lo que convierte medir en aprender.

El problema
-----------
Hasta ahora el evaluador no recordaba nada. Cada ejecución empezaba de cero, así
que podía decir «el caso 7 falla» pero nunca **«el caso 7 fallaba el 22 y hoy
pasa»**. Y esa segunda frase es justamente la que demuestra que la evaluación ha
servido para algo.

Un evaluador sin memoria mide. Con memoria, cierra el bucle:

    detectado  →  comunicado  →  corregido  →  verificado

Los dos primeros pasos ya estaban —la batería detecta, el plan de mejora se manda—.
Los dos últimos necesitan comparar dos ejecuciones separadas en el tiempo, y para
eso hay que guardar la primera.

Qué se guarda, y qué no
-----------------------
Una instantánea por evaluación: fecha, sujeto, métricas y el resultado de cada
caso. **No se guardan los documentos ni la salida del módulo** —eso son datos de
los compañeros y no tienen por qué vivir en el repositorio— sino el veredicto que
salió de ellos.

Con eso basta para lo único que se le pide: decir qué cambió y en qué dirección.

Por qué el registro es manual
-----------------------------
Guardar una instantánea es afirmar «esta evaluación cuenta». Si se guardara sola
en cada clic, el historial se llenaría de pruebas a medias —una salida pegada a
medias, una fecha de consulta mal puesta— y el antes/después dejaría de significar
nada. Se registra a propósito, igual que se firma un acta.
"""

import json
from datetime import date
from pathlib import Path

CARPETA = Path("historial")

# Un cambio de estado no vale lo mismo en las dos direcciones. Que un caso pase de
# fallido a superado es la prueba de que la evaluación sirvió; que retroceda es una
# regresión, y merece más ruido que una mejora.
MEJORAS = {("no_pasa", "pasa"): "corregido",
           ("pendiente", "pasa"): "verificado",
           ("pendiente", "no_pasa"): "ejercitado",
           ("no_aplica", "pasa"): "cubierto",
           ("no_aplica", "no_pasa"): "cubierto"}
REGRESIONES = {("pasa", "no_pasa"): "regresión",
               ("pasa", "pendiente"): "dejó de verificarse"}

TEXTO_CAMBIO = {
    "corregido": "corregido — fallaba y ahora se supera",
    "verificado": "verificado — estaba pendiente de un dato y ahora se supera",
    "ejercitado": "ejercitado — estaba pendiente y ahora se ha podido comprobar",
    "cubierto": "cubierto — el banco de pruebas no lo alcanzaba y ahora sí",
    "regresión": "REGRESIÓN — se superaba y ha dejado de superarse",
    "dejó de verificarse": "ha dejado de poder comprobarse",
}


def _fichero(id_modulo):
    return CARPETA / f"{id_modulo}.jsonl"


def instantanea(ficha, er, ev, nota=""):
    """El veredicto reducido a lo que hace falta para comparar."""
    return {
        "modulo": ficha["id"],
        "fecha": er["fecha"],
        "sujeto": er["sujeto"],
        "nota": nota,
        "metricas": {
            "tasa": er["resumen"]["tasa"],
            "cobertura": er["resumen"]["cobertura"],
            "exhaustividad": ev["contraste"].get("exhaustividad"),
            "precision": ev["contraste"].get("precision"),
            "superados": er["resumen"]["pasa"],
            "fallidos": er["resumen"]["no_pasa"],
        },
        "casos": {str(n): c["resultado"] for n, c in ev["casos"].items()},
    }


def registrar(ficha, er, ev, nota=""):
    """Añade una instantánea al historial del módulo. Devuelve la guardada."""
    snap = instantanea(ficha, er, ev, nota)
    try:
        CARPETA.mkdir(exist_ok=True)
        with _fichero(ficha["id"]).open("a", encoding="utf-8") as f:
            f.write(json.dumps(snap, ensure_ascii=False) + "\n")
    except OSError:
        pass          # sin disco no se pierde la evaluación, sólo la memoria
    return snap


def leer(id_modulo):
    """Todas las instantáneas guardadas, de la más antigua a la más reciente."""
    fichero = _fichero(id_modulo)
    if not fichero.is_file():
        return []
    fuera = []
    for linea in fichero.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            fuera.append(json.loads(linea))
        except json.JSONDecodeError:
            continue      # una línea corrupta no invalida el historial entero
    return fuera


def ultima(id_modulo):
    hist = leer(id_modulo)
    return hist[-1] if hist else None


def comparar(anterior, actual, ficha=None):
    """
    Qué ha cambiado entre dos evaluaciones del mismo módulo.

    Separa mejoras de regresiones a propósito: un evaluador que sólo celebrase los
    avances y no señalase los retrocesos sería un evaluador complaciente, y la
    complacencia es exactamente lo que este sistema existe para evitar.
    """
    if not anterior:
        return None

    titulos = (ficha or {}).get("casos", {})
    mejoras, regresiones, otros = [], [], []
    for clave, ahora in (actual.get("casos") or {}).items():
        antes = (anterior.get("casos") or {}).get(clave)
        if antes is None or antes == ahora:
            continue
        fila = {"caso": int(clave), "titulo": titulos.get(int(clave), ""),
                "antes": antes, "ahora": ahora}
        if (antes, ahora) in MEJORAS:
            mejoras.append({**fila, "cambio": MEJORAS[(antes, ahora)]})
        elif (antes, ahora) in REGRESIONES:
            regresiones.append({**fila, "cambio": REGRESIONES[(antes, ahora)]})
        else:
            otros.append({**fila, "cambio": "cambio de estado"})

    deltas = {}
    for k, v in (actual.get("metricas") or {}).items():
        antes = (anterior.get("metricas") or {}).get(k)
        if isinstance(v, (int, float)) and isinstance(antes, (int, float)) and v != antes:
            deltas[k] = {"antes": antes, "ahora": v, "delta": round(v - antes, 1)}

    return {"desde": anterior.get("fecha"), "hasta": actual.get("fecha"),
            "mejoras": sorted(mejoras, key=lambda x: x["caso"]),
            "regresiones": sorted(regresiones, key=lambda x: x["caso"]),
            "otros": sorted(otros, key=lambda x: x["caso"]),
            "deltas": deltas,
            "sin_cambios": not (mejoras or regresiones or otros or deltas)}


def texto_evolucion(comp, nombre_modulo=""):
    """
    La frase que demuestra que la evaluación produjo algo. Es literalmente lo que
    hay que poder enseñar: qué se detectó, qué se corrigió y cuánto se movió.
    """
    if not comp:
        return ("Primera evaluación registrada de este módulo. A partir de la "
                "siguiente, el sistema podrá decir qué ha cambiado y en qué "
                "dirección.")
    if comp["sin_cambios"]:
        return (f"Sin cambios respecto de la evaluación del {comp['desde']}: los "
                f"mismos casos en el mismo estado y las mismas métricas.")

    t = f"Entre el {comp['desde']} y el {comp['hasta']}, "
    partes = []
    if comp["mejoras"]:
        partes.append(f"{len(comp['mejoras'])} caso(s) mejoran: "
                      + "; ".join(f"caso {m['caso']} {TEXTO_CAMBIO[m['cambio']]}"
                                  for m in comp["mejoras"]))
    if comp["regresiones"]:
        partes.append(f"{len(comp['regresiones'])} retroceden: "
                      + "; ".join(f"caso {r['caso']} {TEXTO_CAMBIO[r['cambio']]}"
                                  for r in comp["regresiones"]))
    t += ". ".join(partes) + ". " if partes else ""

    if comp["deltas"]:
        t += ("Métricas: "
              + "; ".join(f"{k} {d['antes']} → {d['ahora']} "
                          f"({'+' if d['delta'] > 0 else ''}{d['delta']})"
                          for k, d in sorted(comp["deltas"].items())) + ". ")

    if comp["mejoras"] and not comp["regresiones"]:
        t += ("Esto es lo que la evaluación ha producido: un fallo señalado, "
              "comunicado y corregido, con la comprobación hecha por el mismo "
              "banco de pruebas que lo encontró.")
    return t


def a_markdown(ficha, hist):
    """El historial completo, para adjuntarlo a la memoria."""
    if not hist:
        return f"# Historial · {ficha['nombre']}\n\nSin evaluaciones registradas."
    L = [f"# Historial de evaluación · {ficha['nombre']}", "",
         f"**Responsable:** {ficha['responsable']}", "",
         "| Fecha | Evaluado | Tasa | Cobertura | Exhaustividad | Precisión | Nota |",
         "|---|---|---|---|---|---|---|"]
    for s in hist:
        m = s["metricas"]
        L.append(f"| {s['fecha']} | {s['sujeto']} | {m['tasa']}% | "
                 f"{m['cobertura']}% | {m['exhaustividad']}% | {m['precision']}% | "
                 f"{s.get('nota', '')} |")
    L.append("")
    if len(hist) >= 2:
        comp = comparar(hist[-2], hist[-1], ficha)
        L += ["## Último cambio", "", texto_evolucion(comp, ficha["nombre"]), ""]
    return "\n".join(L)
