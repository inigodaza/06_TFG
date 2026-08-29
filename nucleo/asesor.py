"""
El asesor de mejora: el último eslabón, y el único que la IA no comparte con nadie.

Por qué existe
--------------
Durante un tiempo el modelo ocupó en este sistema tres ranuras que trabajaban **en
paralelo** al núcleo determinista: una vía de lectura alternativa, un panel
cualitativo colgado al lado, y un redactor que reformulaba lo ya escrito. Ninguna
de las tres consumía el veredicto para producir algo que las reglas no pudieran
producir. Competían o decoraban.

Este módulo es lo contrario, y es la forma que debería haber tenido desde el
principio: **no puede ejecutarse sin el veredicto determinista**, y produce lo
único que las reglas no saben hacer.

Las reglas saben decir *qué* está mal. No saben decir **qué hacer al respecto**,
ni cuál de tres fallos atacar primero, ni —sobre todo— reconocer que dos síntomas
que aparecen en sitios distintos son **la misma causa**.

El cruce, que es lo que aporta de verdad
-----------------------------------------
En el módulo de Martín, la batería dice:

    caso 8, severidad crítica — PRUEBA_5 se declara «Vigente» y no tiene ni fecha
    de firma ni duración

y el panel de jueces dice, por su cuenta:

    «distingue lo que sabe de lo que no puede saber» — no cumple, por unanimidad

Son el mismo problema visto desde dos sitios: el módulo no tiene un estado para
«no lo sé». La regla tiene la evidencia dura y no ve el patrón; el panel ve el
patrón y no tiene evidencia. Cruzarlos es lo que convierte dos observaciones en un
diagnóstico, y es justo lo que ninguna de las dos partes puede hacer sola.

Los tres candados
-----------------
1. **Sólo ve hechos calculados.** Recibe casos, severidades, hallazgos, requisitos
   y votos del panel. Nunca los documentos.
2. **Toda recomendación va anclada a un caso.** Si cita un caso que no existe, o
   uno que el módulo supera, la recomendación se descarta —no se corrige— y el
   descarte se cuenta. Es la misma regla de anclaje que gobierna los aspectos a
   mejorar del veredicto, aplicada a un texto generado.
3. **Hay versión sin modelo.** `deterministico()` ordena los aspectos ya escritos
   por severidad. Peor consejo, mismo formato, y lo declara.
"""

import json
import re

from . import llm
from .bateria import ORDEN_SEVERIDAD, SEVERIDADES
from .plantilla import severidad_de

ESQUEMA = {
    "type": "object",
    "required": ["recomendaciones"],
    "properties": {
        "diagnostico": {"type": "string"},
        "recomendaciones": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["titulo", "casos", "que_cambiar", "como_comprobarlo"],
                "properties": {
                    "titulo": {"type": "string"},
                    "casos": {"type": "array", "items": {"type": "integer"}},
                    "criterios": {"type": "array", "items": {"type": "string"}},
                    "por_que_primero": {"type": "string"},
                    "que_cambiar": {"type": "string"},
                    "como_comprobarlo": {"type": "string"},
                },
            },
        },
    },
}

PROMPT = (
    "Eres el asesor de un sistema de control de calidad de software. Te dan el "
    "resultado YA CALCULADO de evaluar un módulo y devuelves un plan de mejora "
    "para la persona que lo mantiene.\n\n"
    "REGLAS INNEGOCIABLES\n"
    "· Toda recomendación debe apoyarse en casos que hayan FALLADO o estén "
    "PENDIENTES. Cita sus números en `casos`. No inventes casos ni cites casos "
    "superados: una recomendación sin caso que la sostenga se descarta entera.\n"
    "· No inventes fallos, cifras ni causas que no estén en los datos. Puedes "
    "interpretar y agrupar lo que hay; no puedes añadir.\n"
    "· Un caso PENDIENTE o NO APLICABLE no es un fallo del módulo: es un dato que "
    "le falta al banco de pruebas. Si recomiendas algo sobre uno, que sea pedir "
    "ese dato, nunca corregir un defecto.\n\n"
    "QUÉ SE ESPERA DE TI, Y QUE LAS REGLAS NO SABEN HACER\n"
    "· **Agrupar por causa.** Si dos o tres casos fallan por la misma raíz, "
    "júntalos en UNA recomendación y explica la raíz. Eso vale más que repetir el "
    "enunciado de cada caso.\n"
    "· **Cruzar lo duro con lo cualitativo.** Si un caso fallido y un criterio del "
    "panel apuntan al mismo problema, dilo explícitamente: es el hallazgo más "
    "valioso que puedes producir.\n"
    "· **Priorizar.** Ordena por lo que más daño hace aguas abajo, usando la "
    "severidad declarada. Explica en `por_que_primero` por qué esa va antes.\n"
    "· **Cerrar el bucle.** En `como_comprobarlo`, di qué habría que volver a "
    "ejecutar para saber que quedó arreglado, en términos de los casos.\n\n"
    "TONO\n"
    "· Español, dirigido al responsable del módulo, de tú, como un compañero de "
    "equipo. Concreto y sin adornos. Nada de «cabe destacar» ni «se recomienda "
    "encarecidamente».\n"
    "· `que_cambiar` es una instrucción, no una reflexión: qué tocar y en qué "
    "sentido.\n"
    "· Como mucho cuatro recomendaciones. Si hay menos que decir, di menos."
)


# ---------------------------------------------------------------------------
# Lo que ve el asesor
# ---------------------------------------------------------------------------

def payload(ficha, er, ev, panel=None):
    """
    El extracto que viaja: hechos calculados, nunca documentos. Se construye campo
    a campo para que se vea exactamente qué sale del sistema.
    """
    casos = []
    for n, caso in sorted(ev["casos"].items()):
        if caso["resultado"] == "pasa":
            continue          # lo que funciona no necesita consejo
        sev = severidad_de(ficha, n)
        casos.append({
            "numero": n,
            "titulo": ficha["casos"].get(n, ""),
            "resultado": caso["resultado"],
            "severidad": sev,
            "severidad_significa": SEVERIDADES[sev][1] if sev in SEVERIDADES else None,
            "esperado": caso.get("esperado"),
            "observado": caso.get("observado"),
            "observacion": caso["observacion"],
            "requiere": caso.get("requiere"),
            "correccion_ya_escrita": (ficha.get("aspectos") or {}).get(n, ("", ""))[1]
                                     or None,
        })

    p = {
        "modulo": ficha["nombre"], "responsable": er["responsable"],
        "funcion_declarada": ficha.get("funcion", ""),
        "quien_consume_la_salida": ficha.get("conexion", ""),
        "evaluado": er["sujeto"],
        "metricas": {
            "casos_superados": er["resumen"]["pasa"],
            "casos_con_evidencia": er["resumen"]["con_evidencia"],
            "tasa_acierto_pct": er["resumen"]["tasa"],
            "exhaustividad_pct": ev["contraste"].get("exhaustividad"),
            "precision_pct": ev["contraste"].get("precision"),
        },
        "casos_no_superados": casos,
        "hallazgos": [{"titulo": h["titulo"], "porque_importa": h["porque_importa"]}
                      for h in ev.get("hallazgos", [])],
    }

    if panel and panel.get("criterios"):
        p["criterios_cualitativos"] = {
            "como_se_juzgan": ("Tres jueces independientes con lentes declaradas. "
                               "Sólo cuenta lo que los tres coinciden; donde "
                               "discrepan queda declarado y no puntúa."),
            "acuerdo_kappa": (panel.get("fleiss") or {}).get("kappa"),
            "criterios": [{"criterio": c["titulo"], "veredicto": c["veredicto"],
                           "justificacion": c["justificacion"],
                           "porque_importa": c["porque_importa"]}
                          for c in panel["criterios"]
                          if c["veredicto"] != "cumple"],
        }
    return p


# ---------------------------------------------------------------------------
# El candado del anclaje
# ---------------------------------------------------------------------------

def verificar_anclaje(recomendaciones, ev):
    """
    Cada recomendación tiene que apoyarse en un caso real y no superado.

    Se descarta —no se corrige— la que cite un caso inexistente o uno que el
    módulo supera. Es la misma regla que gobierna los aspectos a mejorar del
    veredicto: un consejo sin evidencia que lo sostenga es exactamente el tipo de
    afirmación que este sistema le reprocha a los módulos que evalúa.

    Devuelve (validas, descartadas).
    """
    no_superados = {n for n, c in ev["casos"].items() if c["resultado"] != "pasa"}
    validas, descartadas = [], []
    for r in recomendaciones or []:
        citados = [c for c in (r.get("casos") or []) if isinstance(c, int)]
        existentes = [c for c in citados if c in ev["casos"]]
        anclados = [c for c in existentes if c in no_superados]
        if not citados:
            descartadas.append({**r, "motivo": "no cita ningún caso"})
        elif not existentes:
            descartadas.append({**r, "motivo": f"cita casos que no existen: "
                                               f"{citados}"})
        elif not anclados:
            descartadas.append({**r, "motivo": f"sólo cita casos que el módulo "
                                               f"supera: {existentes}"})
        else:
            validas.append({**r, "casos": anclados})
    return validas, descartadas


def ordenar(recomendaciones, ficha):
    """Por la peor severidad que toca cada una. La prioridad no la elige el modelo."""
    def peso(r):
        sevs = [severidad_de(ficha, n) for n in r.get("casos") or []]
        for i, s in enumerate(ORDEN_SEVERIDAD):
            if s in sevs:
                return i
        return len(ORDEN_SEVERIDAD)
    return sorted(recomendaciones, key=peso)


# ---------------------------------------------------------------------------
# Generación
# ---------------------------------------------------------------------------

def deterministico(ficha, er, ev):
    """
    Sin modelo: los aspectos que ya están escritos en la ficha, ordenados por
    severidad. Es peor consejo —texto fijo, escrito antes de ver los datos— pero
    es honesto y mantiene el formato.
    """
    recs = []
    for a in er.get("aspectos", []):
        n = a["caso"]
        recs.append({
            "titulo": a["titulo"],
            "casos": [n],
            "que_cambiar": a["correccion"],
            "como_comprobarlo": f"Volver a evaluar y comprobar que el caso {n} "
                                f"pasa a superado.",
            "por_que_primero": (SEVERIDADES[severidad_de(ficha, n)][1]
                                if severidad_de(ficha, n) in SEVERIDADES else ""),
        })
    return {"diagnostico": "", "recomendaciones": ordenar(recs, ficha)}


def aconsejar(ficha, er, ev, panel=None, usar_modelo=True):
    """
    Devuelve {recomendaciones, descartadas, origen, aviso, diagnostico, payload}.

    `origen` distingue el consejo del modelo del de plantilla, y va a la vista: un
    plan de mejora tiene que decir quién lo escribió.
    """
    p = payload(ficha, er, ev, panel)
    aviso, descartadas = None, []

    if not p["casos_no_superados"]:
        return {"recomendaciones": [], "descartadas": [], "origen": "ninguno",
                "aviso": None, "payload": p,
                "diagnostico": "Todos los casos con evidencia se superan. No hay "
                               "nada que recomendar sobre esta ejecución; lo que "
                               "queda es ampliar el banco de pruebas."}

    if usar_modelo and llm.esta_disponible():
        try:
            bruto = llm.consultar(
                PROMPT, json.dumps(p, ensure_ascii=False, indent=1, default=str),
                ESQUEMA)
            validas, descartadas = verificar_anclaje(
                (bruto or {}).get("recomendaciones"), ev)
            if validas:
                return {"recomendaciones": ordenar(validas, ficha),
                        "descartadas": descartadas, "origen": "modelo",
                        "diagnostico": (bruto or {}).get("diagnostico", ""),
                        "aviso": None, "payload": p}
            aviso = ("Ninguna de las recomendaciones del modelo se sostenía en un "
                     "caso fallido, así que se han descartado todas. Se muestran "
                     "las correcciones ya escritas en la batería.")
        except llm.NoDisponible as e:
            aviso = (f"El asesor no ha podido consultarse ({e}). Se muestran las "
                     f"correcciones ya escritas en la batería.")
    elif usar_modelo:
        aviso = (f"El asesor de IA no está conectado ({llm.por_que_no()}). Se "
                 f"muestran las correcciones ya escritas en la batería.")

    det = deterministico(ficha, er, ev)
    return {**det, "descartadas": descartadas, "origen": "plantilla",
            "aviso": aviso, "payload": p}


def coste(ficha, er, ev, panel=None):
    """¿Cuesta una llamada o sale de caché? Se dice antes de ofrecer el botón."""
    p = payload(ficha, er, ev, panel)
    texto = json.dumps(p, ensure_ascii=False, indent=1, default=str)
    return {"total": 1, "nuevas": 0 if llm.en_cache(PROMPT, texto, ESQUEMA) else 1}


def a_markdown(ficha, er, res):
    """El plan de mejora como documento, para mandárselo al compañero."""
    L = [f"# Plan de mejora · {ficha['nombre']}", "",
         f"**Para:** {er['responsable']}", f"**Evaluado:** {er['sujeto']}",
         f"**Fecha:** {er['fecha']}", ""]
    if res["origen"] == "modelo":
        L += ["> Recomendaciones redactadas por modelo sobre el veredicto ya "
              "calculado. Cada una está anclada a un caso fallido o pendiente de la "
              "batería; las que no lo estaban se descartaron automáticamente.", ""]
    elif res["origen"] == "plantilla":
        L += ["> Correcciones escritas en la batería, ordenadas por severidad. Sin "
              "modelo.", ""]
    if res.get("diagnostico"):
        L += ["## Diagnóstico", "", res["diagnostico"], ""]
    if not res["recomendaciones"]:
        L += ["Sin recomendaciones.", ""]
    for i, r in enumerate(res["recomendaciones"], 1):
        L += [f"## {i}. {r['titulo']}", "",
              f"*Casos {', '.join(str(c) for c in r['casos'])}"
              + (f" · criterios: {', '.join(r['criterios'])}"
                 if r.get("criterios") else "") + "*", ""]
        if r.get("por_que_primero"):
            L += [f"**Por qué importa:** {r['por_que_primero']}", ""]
        L += [f"**Qué cambiar:** {r['que_cambiar']}", "",
              f"**Cómo comprobar que quedó arreglado:** {r['como_comprobarlo']}", ""]
    if res.get("descartadas"):
        L += ["---", "",
              f"*{len(res['descartadas'])} recomendación(es) del modelo se "
              f"descartaron por no apoyarse en ningún caso fallido de la batería.*"]
    return "\n".join(L)
