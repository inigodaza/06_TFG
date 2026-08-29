"""
El informe para el compañero: redactado por el modelo, verificado por el sistema.

Qué hace y qué no
-----------------
El veredicto ya está calculado cuando esto se ejecuta. Aquí no se decide nada: se
cuenta. El modelo recibe un extracto de resultados —métricas, casos, requisitos—
y devuelve el texto que se le manda al compañero, en su idioma y dirigido a él.
Es la única ranura del sistema donde el modelo escribe prosa, y precisamente por
eso es la que más control necesita.

Tres controles, en orden
------------------------

**1 · Sólo ve lo que se le da.** El modelo no recibe los documentos originales ni
la salida cruda del módulo: recibe un `payload` construido a mano con lo que ya
está calculado. En las ramas cuyos datos no pueden salir —los PDF de Juan son
documentación real de un cliente— se recorta un paso más y ni siquiera viajan las
observaciones de los casos, que podrían citar valores del documento. El informe
sigue saliendo; sale con menos detalle, y el propio informe lo dice.

**2 · No puede inventar cifras.** Es el riesgo real: un texto bien escrito con un
porcentaje que nadie calculó. Después de redactar, `verificar_cifras()` extrae
todos los números del texto y comprueba que cada uno esté en el `payload`. Si
aparece uno que no estaba, se marca y el informe se entrega señalado. La
comprobación es determinista y se ejecuta siempre: el redactor va vigilado por el
mismo tipo de regla que el sistema aplica a los módulos que evalúa.

**3 · Hay versión sin modelo.** `deterministico()` compone el mismo informe con
plantillas. Si no hay clave, si la llamada falla o si el módulo tiene la IA
cerrada, el informe se genera igual y declara de dónde viene. Nada del sistema
depende de que el modelo esté disponible.
"""

import json
import re

from . import llm
from .bateria import ETIQUETA_CASO

# Cabecera que lleva todo informe, diga lo que diga el resto: quien lo recibe
# tiene que saber cómo se ha escrito antes de leerlo.
PROCEDENCIA = {
    "modelo": ("Redacción asistida por modelo sobre resultados ya calculados. "
               "Las cifras han sido verificadas automáticamente contra los datos "
               "de la evaluación."),
    "plantilla": ("Redacción generada por plantilla determinista, sin modelo."),
}

PROMPT = (
    "Redactas el informe de una evaluación de calidad de software. Te dan los "
    "resultados YA CALCULADOS en JSON y devuelves el texto que se le enviará al "
    "responsable del módulo evaluado.\n\n"
    "REGLAS INNEGOCIABLES\n"
    "· No calcules ni deduzcas nada. Toda cifra que escribas debe aparecer tal "
    "cual en el JSON. Si una cifra no está, no la menciones. No redondees, no "
    "sumes, no conviertas a fracciones ni digas «aproximadamente».\n"
    "· No inventes causas, ni fallos, ni recomendaciones que no estén en el JSON. "
    "Puedes reordenar y explicar lo que hay; no puedes añadir.\n"
    "· Un caso pendiente o no aplicable NO es un fallo del módulo. Un pendiente "
    "espera un dato de esta misma ejecución; uno no aplicable mide una situación "
    "que estos datos no contienen. Decirlo mal sería acusar al compañero de algo "
    "que no ha hecho.\n\n"
    "TONO\n"
    "· Español. Te diriges al responsable por su nombre, de tú, como un compañero "
    "de equipo que le manda un resultado —no como un proveedor ni como un "
    "inspector.\n"
    "· Directo y sin adornos. Nada de «excelente trabajo», «cabe destacar», «en "
    "aras de». Ni una fórmula de cortesía de relleno.\n"
    "· Lo que falla se dice claro y se dice por qué importa. Lo que funciona se "
    "menciona una vez y se sigue.\n\n"
    "FORMATO — Markdown, exactamente estas secciones y en este orden:\n"
    "## Qué se ha evaluado\n"
    "Dos o tres frases: qué módulo, sobre qué datos, con qué método.\n"
    "## Resultado\n"
    "Las métricas en prosa, explicando qué significa cada una. Distingue con "
    "claridad lo verificado de lo no ejercitado.\n"
    "## Qué conviene revisar\n"
    "Un apartado por aspecto a mejorar, con su corrección propuesta. Si no hay "
    "ninguno, dilo en una frase y pasa.\n"
    "## Qué necesito de ti\n"
    "La lista de requisitos, explicando para qué sirve cada uno. Si está vacía, "
    "dilo en una frase.\n\n"
    "No escribas encabezado ni despedida: el sistema los pone."
)


# ---------------------------------------------------------------------------
# Lo que ve el modelo
# ---------------------------------------------------------------------------

def payload(ficha, er, ev, panel=None, incluir_observaciones=True):
    """
    El extracto que viaja. Se construye campo a campo a propósito: pasar el
    objeto entero sería cómodo y dejaría de estar claro qué sale del sistema.
    """
    r = er["resumen"]
    c = ev.get("contraste", {})

    casos = []
    for n, caso in sorted(ev["casos"].items()):
        fila = {"numero": n, "titulo": ficha["casos"].get(n, ""),
                "resultado": caso["resultado"]}
        if incluir_observaciones and caso.get("observacion"):
            fila["observacion"] = caso["observacion"]
        casos.append(fila)

    aspectos = []
    for a in er["aspectos"]:
        fila = {"titulo": a["titulo"], "caso": a["caso"],
                "nombre_caso": a["nombre_caso"], "estado": a["estado"],
                "correccion": a["correccion"]}
        if incluir_observaciones:
            fila["detalle"] = a["detalle"]
        aspectos.append(fila)

    p = {
        "modulo": er["modulo"], "responsable": er["responsable"],
        "empresa": er.get("empresa", ""), "conexion": er.get("conexion", ""),
        "funcion_declarada": ficha.get("funcion", ""),
        "evaluado": er["sujeto"], "fecha": er["fecha"],
        "modo_lectura": er.get("modo_lectura", "determinista"),
        "unidad": list(ficha.get("unidad", ("unidad", "unidades"))),
        "metricas": {
            "casos_disenados": r["total"],
            "casos_con_evidencia": r["con_evidencia"],
            "superados": r["pasa"], "fallidos": r["no_pasa"],
            "pendientes": r["pendiente"], "no_aplicables": r["no_aplica"],
            "tasa_acierto_pct": r["tasa"], "cobertura_bateria_pct": r["cobertura"],
            "exhaustividad_pct": c.get("exhaustividad"),
            "precision_pct": c.get("precision"),
        },
        "que_significan": {
            "tasa_acierto": "superados entre casos con evidencia; mide el módulo",
            "cobertura": "casos con evidencia entre casos diseñados; mide el banco "
                         "de pruebas del evaluador, no el módulo",
            "exhaustividad": f"de {ficha.get('unidad', ('', 'las unidades'))[1]} que "
                             f"el evaluador determina por su cuenta, cuántas resolvió "
                             f"el módulo",
            "precision": "de lo que el módulo emitió, cuánto se sostiene "
                         "documentalmente",
        },
        "casos": casos,
        "aspectos_a_mejorar": aspectos,
        "requisitos": [{"caso": q["caso"], "estado": q["estado"],
                        "titulo": ficha["casos"].get(q["caso"], ""),
                        "requiere": q["requiere"]} for q in er.get("requisitos", [])],
        "hallazgos_de_cobertura": [
            {"titulo": h["titulo"], "porque_importa": h["porque_importa"]}
            for h in ev.get("hallazgos", [])],
        "observaciones_recortadas": not incluir_observaciones,
    }

    if panel and panel.get("criterios"):
        p["panel_cualitativo"] = {
            "jueces": panel["perspectivas"],
            "criterios_evaluados": panel["total"],
            "con_acuerdo": panel["puntuables"],
            "cumple": panel["cumple"], "no_cumple": panel["no_cumple"],
            "en_discrepancia": panel["discrepancia"],
            "no_valorables": panel["no_valorable"],
            "kappa_fleiss": (panel.get("fleiss") or {}).get("kappa"),
            "detalle": [{"criterio": c_["titulo"], "veredicto": c_["veredicto"],
                         "justificacion": c_["justificacion"]}
                        for c_ in panel["criterios"]],
        }
    return p


# ---------------------------------------------------------------------------
# El control de cifras
# ---------------------------------------------------------------------------

_NUM = re.compile(r"\d+(?:[.,]\d+)?")
# Marcadores de lista y encabezados: su numeración es del formato, no un dato.
_ORDINAL = re.compile(r"(?m)^\s{0,4}(?:[-*>]\s*)?\d{1,2}[.)]\s")
_ENCABEZADO = re.compile(r"(?m)^#{1,6}\s")


def _normalizar(n):
    """1.0, 1,0 y 1 son el mismo número; que se escriban distinto no importa."""
    n = n.replace(",", ".")
    if "." in n:
        n = n.rstrip("0").rstrip(".")
    return n or "0"


def cifras_permitidas(p):
    """Todo número que aparece en el extracto, incluidos los de fechas y textos."""
    crudo = json.dumps(p, ensure_ascii=False, default=str)
    return {_normalizar(m) for m in _NUM.findall(crudo)}


def verificar_cifras(texto, permitidas):
    """
    Comprueba que el redactor no se ha inventado ningún número.

    Es el control que convierte «lo ha escrito un modelo» en algo que se puede
    firmar. No juzga el estilo ni el contenido: sólo que cada cifra del texto
    existiera antes de escribirlo.
    """
    # Primero los encabezados y luego la numeración: así «### 2. Resultado» pierde
    # las dos marcas y no deja un 2 suelto que parezca un dato.
    limpio = _ORDINAL.sub("", _ENCABEZADO.sub("", texto or ""))
    encontradas = [_normalizar(m) for m in _NUM.findall(limpio)]
    intrusas = sorted({n for n in encontradas if n not in permitidas},
                      key=lambda x: (len(x), x))
    return {"ok": not intrusas, "intrusas": intrusas,
            "cifras_en_texto": len(encontradas),
            "cifras_disponibles": len(permitidas)}


# ---------------------------------------------------------------------------
# Redacción
# ---------------------------------------------------------------------------

def _cabecera(er, origen):
    return (f"# Informe de evaluación · {er['modulo']}\n\n"
            f"**Para:** {er['responsable']}"
            + (f" · {er['empresa']}" if er.get("empresa") else "") + "  \n"
            f"**De:** Íñigo Daza · Evaluación y Calidad  \n"
            f"**Conexión:** {er.get('conexion', '')}  \n"
            f"**Fecha:** {er['fecha']}\n\n"
            f"> {PROCEDENCIA[origen]}\n")


def _pie(er, verificacion, recortado):
    L = ["\n---\n",
         "*Cada punto de este informe está anclado a un caso de la batería de "
         "pruebas. Los casos pendientes y los no aplicables no cuentan ni a favor "
         "ni en contra del módulo: los primeros esperan un dato de esta misma "
         "ejecución, los segundos miden situaciones que estos datos no contienen.*"]
    if recortado:
        L.append("\n*Las observaciones caso a caso no se han incluido en la "
                 "redacción: los documentos de este módulo contienen datos que no "
                 "pueden salir del sistema. El detalle completo está en el "
                 "EvaluationResult exportable.*")
    if verificacion and not verificacion["ok"]:
        L.append(f"\n*Aviso de control: la verificación automática ha encontrado "
                 f"cifras en el texto que no figuran en los resultados calculados "
                 f"({', '.join(verificacion['intrusas'])}). Revísalas antes de "
                 f"enviar el informe.*")
    elif verificacion:
        L.append(f"\n*Control de cifras superado: las {verificacion['cifras_en_texto']} "
                 f"cifras del texto figuran en los resultados calculados.*")
    return "\n".join(L)


def deterministico(ficha, er, ev, panel=None):
    """El mismo informe, sin modelo. Es el suelo del sistema, no un premio de consolación."""
    r = er["resumen"]
    L = ["## Qué se ha evaluado", "",
         f"He evaluado **{er['modulo']}** sobre {er['sujeto']}, contrastando la "
         f"salida real del módulo contra los documentos de origen. La lectura de "
         f"los documentos se ha hecho en modo *{er.get('modo_lectura', 'determinista')}* "
         f"y el juicio es determinista: las mismas entradas dan el mismo resultado.",
         "", "## Resultado", "", er["valoracion"], ""]

    if panel and panel.get("criterios"):
        from .jueces import texto_panel
        L += ["### Criterios cualitativos", "", texto_panel(panel), ""]

    L += ["## Qué conviene revisar", ""]
    if er["aspectos"]:
        for i, a in enumerate(er["aspectos"], 1):
            L += [f"**{i}. {a['titulo']}**  ",
                  f"*Caso {a['caso']} · {a['nombre_caso']} · {ETIQUETA_CASO[a['estado']]}*",
                  "", a["detalle"], "", f"Corrección propuesta: {a['correccion']}", ""]
    else:
        L += ["No hay aspectos a mejorar: todos los casos con evidencia se superan.", ""]

    L += ["## Qué necesito de ti", ""]
    if er.get("requisitos"):
        L += ["Ninguno de estos puntos es un defecto del módulo: son datos que el "
              "banco de pruebas todavía no tiene y sin los cuales hay casos "
              "diseñados que no puedo ejercitar.", ""]
        for q in er["requisitos"]:
            L.append(f"- **{ficha['casos'].get(q['caso'], '')}** (caso {q['caso']}, "
                     f"{q['estado'].replace('_', ' ')}): {q['requiere']}")
        L.append("")
    else:
        L += ["Nada por ahora: la batería ha podido ejercitarse entera con los "
              "datos aportados.", ""]

    if panel and panel.get("requisitos"):
        L += ["Además, el panel de jueces no ha alcanzado acuerdo en estos "
              "criterios, que quedan pendientes de arbitraje:", ""]
        for q in panel["requisitos"]:
            L.append(f"- **{q['criterio']}**: {q['requiere']}")
        L.append("")

    return "\n".join(L)


def generar(ficha, er, ev, panel=None, usar_modelo=True, incluir_observaciones=None):
    """
    Devuelve {texto, origen, verificacion, aviso}.

    `incluir_observaciones` por defecto sigue al permiso de datos de la rama: si
    la rama no puede mandar sus documentos a un tercero, tampoco manda las
    observaciones que los citan.
    """
    if incluir_observaciones is None:
        incluir_observaciones = bool(ficha.get("ia_permitida", False))

    p = payload(ficha, er, ev, panel, incluir_observaciones)
    aviso = None
    cuerpo, origen, verificacion = None, "plantilla", None

    if usar_modelo and llm.esta_disponible():
        try:
            cuerpo = llm.redactar(
                PROMPT, json.dumps(p, ensure_ascii=False, indent=1, default=str))
            origen = "modelo"
            verificacion = verificar_cifras(cuerpo, cifras_permitidas(p))
        except llm.NoDisponible as e:
            aviso = (f"No se ha podido redactar con el modelo ({e}). El informe se "
                     f"ha generado con la plantilla determinista.")
            cuerpo = None
    elif usar_modelo:
        aviso = (f"El componente de IA no está conectado ({llm.por_que_no()}). "
                 f"El informe se ha generado con la plantilla determinista.")

    if cuerpo is None:
        cuerpo = deterministico(ficha, er, ev, panel)

    texto = (_cabecera(er, origen) + "\n" + cuerpo.strip() + "\n"
             + _pie(er, verificacion, not incluir_observaciones))
    return {"texto": texto, "origen": origen, "verificacion": verificacion,
            "aviso": aviso, "payload": p}


def coste(ficha, er, ev, panel=None, incluir_observaciones=None):
    """Si el informe ya está en caché, el botón no gasta. Se dice antes de pulsarlo."""
    if incluir_observaciones is None:
        incluir_observaciones = bool(ficha.get("ia_permitida", False))
    p = payload(ficha, er, ev, panel, incluir_observaciones)
    texto = json.dumps(p, ensure_ascii=False, indent=1, default=str)
    return {"total": 1, "nuevas": 0 if llm.en_cache(PROMPT, texto, "texto/1") else 1}
