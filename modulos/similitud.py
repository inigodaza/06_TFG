"""
Rama de evaluación del módulo de SIMILITUD DE PROYECTOS — Álvaro Subias · Kelvion.
Conexión C7 · Álvaro → Evaluación y Calidad.

Qué hace el módulo evaluado: dado un pedido nuevo, filtra el histórico de
proyectos por parámetros duros y ordena los que sobreviven por parecido,
combinando una señal semántica y una paramétrica con un peso declarado.

Qué hace esta rama, y en qué se diferencia de las otras dos
--------------------------------------------------------
En auditoría y en vigencia el evaluador lee los documentos de origen y calcula
por su cuenta qué debería haber salido. Aquí **no tengo el corpus**: las 97
fichas de proyecto no están, sólo tengo la salida. Así que la verdad de campo
se calcula de otra manera, y conviene decirlo en voz alta porque es una forma de
verificación distinta:

  1. **Aritmética y estructura** — recalculo la puntuación desde las señales y el
     peso declarados, el orden desde las puntuaciones, y compruebo que resultados
     y descartados particionan el corpus. Nada de esto se cree: se rehace.

  2. **Equivalencia en especificación** — de cada resultado, el módulo publica
     los `parametros_justificativos` con el valor del pedido y el de la
     candidata. Con eso puedo decidir por mi cuenta qué proyectos son
     equivalentes al pedido: los que coinciden exactamente en todos los
     parámetros categóricos y no se desvían más de la tolerancia en ninguno de
     los numéricos. Esa es la verdad de campo, y de ella salen las dos métricas
     de siempre: cuántos equivalentes coloca en cabeza y cuántos de los que
     coloca en cabeza lo son.

El umbral no es un ajuste fino. En los cuatro casos que entregó Álvaro, la mayor
desviación entre equivalentes es 7,7 % y la menor entre no equivalentes 19,6 %:
hay un hueco de más del doble. El evaluador **mide ese margen y lo declara**, así
que si un conjunto futuro no separa limpiamente, se ve.

Lo que esta rama NO puede comprobar, y hay que decirlo: si el filtro de la Capa 1
dejó fuera un proyecto que sí era equivalente. Los descartados sólo publican el
parámetro que los excluyó, no el resto de sus valores. Para eso harían falta las
fichas del corpus.
"""

import json
import math
from datetime import date

from nucleo import bateria as B
from nucleo import contraste as C
from nucleo import jueces as J

# ===========================================================================
# Ficha de la rama
# ===========================================================================

# Umbral de respaldo. Sólo se usa cuando el conjunto no separa por sí solo los
# dos grupos: en ese caso el evaluador lo dice, porque un corte impuesto sobre
# datos que no se separan hace discutible todo lo que viene detrás.
TOLERANCIA_RESPALDO = 0.10

# Un salto se considera separación real cuando cumple las dos condiciones:
# multiplicar la desviación al menos por SALTO_MINIMO, y ser un hueco al menos
# NITIDEZ_MINIMA veces más ancho que la dispersión interna del grupo más
# disperso. La segunda es la que distingue dos grupos de un continuo.
SALTO_MINIMO = 2.0
NITIDEZ_MINIMA = 1.0

# Suelo para no dividir por cero cuando una candidata coincide exactamente.
SUELO = 0.005

# Campos que Álvaro y yo pactamos. `extra_no_pactado` va aparte a propósito.
CAMPOS_PACTADOS = ["id_consulta", "fecha_hora", "pedido_consultado", "resultados",
                   "descartados", "esquema_version", "peso_semantico"]

CASOS = {
    1: "Aritmética de la puntuación declarada",
    2: "Orden del ranking",
    3: "Normalización de las señales",
    4: "Los proyectos equivalentes ocupan la cabeza del ranking",
    5: "Partición del corpus entre resultados y descartados",
    6: "Coherencia del pedido en todo el fichero",
    7: "Trazabilidad del descarte",
    8: "Aviso de lista vacía",
    9: "Declaración de los parámetros no verificados",
    10: "Repetibilidad del ranking",
    11: "La ordenación se reproduce desde los parámetros declarados",
}

ORIGEN = {1: "acuerdo de conexión", 2: "acuerdo de conexión",
          3: "acuerdo de conexión", 4: "calidad del ranking",
          5: "acuerdo de conexión", 6: "acuerdo de conexión",
          7: "acuerdo de conexión", 8: "comportamiento ante error",
          9: "campo propuesto por Álvaro", 10: "criterio transversal",
          11: "declarado por Álvaro 27/08"}

ALCANCE = {n: "ejecucion" for n in CASOS}

# Severidad por consecuencia aguas abajo. Aquí el destinatario es un ingeniero que
# decide si reutiliza un diseño: lo crítico es lo que le hace descartar un proyecto
# equivalente sin enterarse de que existía.
SEVERIDAD = {
    1: "alta",      # la puntuación no se sostiene, pero el orden puede seguir bien
    2: "alta",      # un orden mal construido se lee como jerarquía real
    3: "media",     # la escala se puede recalcular desde las señales publicadas
    4: "critica",   # un equivalente fuera de cabeza no se vuelve a mirar nunca
    5: "critica",   # un proyecto que no está ni en resultados ni en descartes se pierde
    6: "alta",      # comparar contra el pedido equivocado invalida la consulta entera
    7: "alta",      # sin motivo de descarte no se puede recurrir la exclusión
    8: "critica",   # una lista vacía sin causa se lee como «no hay nada parecido»
    9: "media",     # el extra no pactado informa, no decide
    10: "alta",     # sin repetibilidad ninguna medición anterior se sostiene
    11: "alta",     # el ranking sigue sirviendo, pero deja de ser auditable
}

ASPECTOS = {
    1: ("La puntuación emitida no se reproduce con la fórmula y el peso declarados",
        "Declarar en la propia salida el peso aplicado en esa ejecución y derivar la "
        "puntuación de las señales, no calcularla por separado: si los dos números no "
        "cuadran, la explicación que acompaña al ranking no explica el ranking."),
    2: ("El orden emitido no corresponde a las puntuaciones",
        "Derivar la posición de la puntuación en el momento de exportar, con un "
        "criterio de desempate explícito."),
    3: ("La normalización de las señales no cubre el rango completo",
        "Si la normalización es min-max sobre las candidatas supervivientes, el mejor "
        "debe valer 1 y el peor 0. Si no lo hace, la escala no es la declarada y las "
        "puntuaciones de dos consultas no son comparables entre sí."),
    4: ("Hay proyectos equivalentes que no llegan a la cabeza del ranking",
        "La causa está identificada y declarada por el autor el 27/08: el reparto de "
        "pesos es 1/N dentro de cada mitad —50 % a once numéricos, 50 % a siete "
        "categóricos blandos— y no una ponderación razonada por importancia de "
        "ingeniería. Por eso el tamaño físico puede desplazar a un proyecto que "
        "coincide en la especificación. Este caso no acusa de incoherencia: la "
        "puntuación es reproducible (caso 11). Lo que señala es que el orden "
        "resultante no es el que espera quien busca un precedente reutilizable. "
        "Álvaro lo asume como deuda técnica y lo deja fuera del alcance de su TFG "
        "por estar a seis días de la entrega; queda registrado aquí para que la "
        "decisión sea explícita y no un descuido."),
    5: ("Resultados y descartados no particionan el corpus",
        "Todo candidato evaluado debe aparecer exactamente una vez, en una lista o en "
        "la otra. Un proyecto que desaparece de las dos no es auditable."),
    6: ("El valor del pedido no es el mismo en todo el fichero",
        "Un mismo parámetro del pedido debe llevar el mismo valor en los resultados y "
        "en los descartados: si no, no se sabe contra qué se comparó."),
    7: ("Hay descartes sin justificación completa",
        "Cada descarte debe declarar el parámetro que lo excluyó y los dos valores "
        "enfrentados. Sin ellos, el descarte no se puede discutir."),
    8: ("El aviso de lista vacía no distingue las dos situaciones",
        "Una lista vacía puede significar «no hay proyectos parecidos» o «el filtro "
        "excluyó a todos por un parámetro». Son cosas distintas aguas abajo y el "
        "aviso es lo único que las separa."),
    9: ("No consta qué parámetros no han podido verificarse",
        "Una candidata que sobrevive porque le faltaba el dato no está verificada "
        "igual que una que sobrevive por coincidir. El campo `extra_no_pactado` "
        "cubre esto y debería entrar en el acuerdo, no quedarse como extra."),
    11: ("La ordenación publicada no se reproduce con los pesos declarados",
         "La puntuación de cada candidata debería salir de sumar la contribución de "
         "todos los parámetros que entran en la señal paramétrica —50 % numéricos, "
         "50 % categóricos blandos, media simple dentro de cada mitad— y normalizar "
         "min-max dentro del grupo. Si el número rehecho no coincide con el emitido, "
         "el reparto de pesos que se documenta no es el que se aplica, y entonces "
         "nadie de fuera puede auditar una posición del ranking."),
    10: ("El determinismo del ranking no está demostrado",
         "Ejecutar dos veces la misma consulta sobre el mismo corpus y comparar "
         "posiciones y puntuaciones, no la redacción."),
}

# ---------------------------------------------------------------------------
# Criterios cualitativos
# ---------------------------------------------------------------------------
# La ranura de lectura sigue cerrada aquí y por buen motivo: el módulo entrega
# JSON, no hay documento que interpretar. Pero el módulo sí **escribe** cosas —el
# aviso de lista vacía, la lista de parámetros con la que justifica cada
# coincidencia— y sobre eso ninguna regla puede pronunciarse. Que un aviso sea
# aritméticamente correcto no significa que le sirva a quien lo lee.
#
# Los identificadores son sintéticos (SYN-xxxx), así que aquí el panel no toca
# datos de nadie: el permiso de lectura y el del panel son decisiones distintas
# porque exponen cosas distintas.

CUALITATIVOS = [
    J.criterio(
        "aviso_util",
        "El aviso de lista vacía explica la causa y qué hacer",
        "Cuando no hay ningún proyecto que ofrecer, ¿el mensaje deja claro por qué "
        "se ha quedado vacía la lista y qué podría hacer el usuario a "
        "continuación, o se limita a informar de que no hay resultados?",
        "Una lista vacía es el momento en que el usuario más necesita al módulo. "
        "Si el aviso no orienta, el usuario concluye que no hay proyectos "
        "parecidos, cuando lo que ha pasado es que un filtro los ha excluido "
        "todos."),
    J.criterio(
        "justificacion_pertinente",
        "Los parámetros justificativos sostienen la equivalencia",
        "¿Los parámetros que el módulo presenta como justificación de cada "
        "coincidencia son los que de verdad determinan que dos proyectos sean "
        "equiparables, o incluyen coincidencias triviales que engordan la "
        "apariencia de parecido sin aportar nada?",
        "El ingeniero decide reutilizar un diseño mirando esta justificación. Si "
        "está llena de coincidencias irrelevantes, la justificación deja de "
        "informar y empieza a persuadir."),
    J.criterio(
        "orden_honesto",
        "El orden no aparenta más firmeza de la que tiene",
        "Cuando varias posiciones consecutivas tienen puntuaciones casi idénticas, "
        "¿la salida advierte de algún modo de que ese orden es apretado, o "
        "presenta el ranking como si las diferencias fueran claras?",
        "Un ranking se lee como una jerarquía. Si el segundo y el quinto están "
        "separados por milésimas y nada lo indica, el módulo está transmitiendo "
        "una certeza que sus propios números no respaldan."),
]


def evidencia_panel(datos, tope_resultados=5, tope_descartes=6):
    """
    Aquí la evidencia no es la salida entera —son cien proyectos— sino lo que un
    usuario ve de verdad: la cabecera de resultados con su justificación, el aviso
    si lo hay, y una muestra de descartes. Recortar es parte del método, así que el
    recorte va escrito en la propia evidencia.
    """
    datos = datos or {}
    L = [f"CONSULTA: {datos.get('id_consulta', '(sin identificador)')}",
         f"PEDIDO CONSULTADO: {datos.get('pedido_consultado', '(sin descripción)')}",
         f"PESO SEMÁNTICO DECLARADO: {datos.get('peso_semantico')}", ""]

    aviso = datos.get("aviso_lista_vacia")
    if aviso:
        L += ["AVISO DE LISTA VACÍA EMITIDO POR EL MÓDULO:",
              json.dumps(aviso, ensure_ascii=False, indent=1), ""]
    else:
        L += ["AVISO DE LISTA VACÍA: no procede, la consulta ha devuelto "
              "resultados.", ""]

    resultados = datos.get("resultados") or []
    L.append(f"RESULTADOS ({len(resultados)} en total; se muestran los "
             f"{min(tope_resultados, len(resultados))} primeros):")
    for r in resultados[:tope_resultados]:
        L.append(f"  · posición {r.get('posicion')} — {r.get('id_proyecto')} — "
                 f"puntuación {r.get('puntuacion')}")
        for p in (r.get("parametros_justificativos") or []):
            L.append(f"      {p.get('parametro')}: pedido={p.get('valor_pedido')} "
                     f"| candidata={p.get('valor_candidata')}")
    L.append("")

    descartes = datos.get("descartados") or []
    L.append(f"DESCARTADOS ({len(descartes)} en total; muestra de "
             f"{min(tope_descartes, len(descartes))}):")
    for d in descartes[:tope_descartes]:
        L.append(f"  · {d.get('id_proyecto')} — excluido por "
                 f"{d.get('parametro')}: pedido={d.get('valor_pedido')} "
                 f"| candidata={d.get('valor_candidata')}")

    return "\n".join(L)


FICHA = {
    "id": "similitud",
    "nombre": "Similitud de proyectos",
    "responsable": "Álvaro Subias",
    "empresa": "Kelvion",
    "conexion": "C7 · Álvaro → Evaluación y Calidad",
    "estado_conexion": "documentada",
    "funcion": ("Ordena los proyectos del histórico por parecido con un pedido "
                "nuevo, combinando semejanza semántica y paramétrica."),
    "verifica": "Íñigo Daza",
    "operativo": True,
    # No hay texto libre en ninguna parte de esta rama: el módulo entrega JSON y
    # lo que se hace con él es aritmética. Un modelo no tiene nada que aportar.
    "ia_permitida": False,
    "motivo_ia": ("Este módulo entrega JSON estructurado y todo lo que hace el "
                  "evaluador es recalcularlo. No hay lectura que generalizar, así "
                  "que la ranura de IA se queda sin uso a propósito."),
    # El permiso de lectura y el del panel se deciden por separado porque exponen
    # cosas distintas. Aquí no hay lectura que generalizar, pero sí texto emitido
    # por el módulo que ninguna regla puede juzgar, y sobre identificadores
    # sintéticos: el panel queda abierto.
    "panel_permitido": True,
    "cualitativos": CUALITATIVOS,
    "unidad": ("proyecto", "los proyectos equivalentes al pedido"),
    "entrada": ("La exportación en JSON de una consulta. **Aquí no hay documentos "
                "que subir**: el módulo de Álvaro no lee PDF, consulta un histórico "
                "de proyectos ya indexado y devuelve un ranking. El JSON es a la vez "
                "el dato de origen y la salida a evaluar."),
    "entrada_respuesta": ("Sube el JSON de la consulta, o pégalo. Es a la vez el "
                          "dato de origen y la salida a evaluar."),
    "casos": CASOS,
    "aspectos": ASPECTOS,
    "alcance": ALCANCE,
    "severidad": SEVERIDAD,
    "origen_casos": ORIGEN,
    "esquema_salida": {
        "type": "object",
        "required": CAMPOS_PACTADOS,
        "properties": {
            "id_consulta": {"type": "string"},
            "peso_semantico": {"type": "number"},
            "resultados": {"type": "array"},
            "descartados": {"type": "array"},
            "aviso_lista_vacia": {"type": ["object", "null"]},
        },
    },
    "prompt_interpretacion": (
        "Aquí no hace falta modelo: el módulo entrega JSON estructurado. La ranura de "
        "IA de este bloque queda sin uso a propósito."
    ),
}


# ===========================================================================
# 1. Lectura de la exportación
# ===========================================================================

def interpretar(texto, modo="determinista"):
    """
    Aquí no hay texto libre que interpretar: la salida ya viene estructurada.
    Lo único que se hace es leerla y avisar de lo que falte respecto al acuerdo.
    """
    texto = (texto or "").strip()
    if not texto:
        return None, []
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as e:
        return None, [f"El fichero no es JSON válido: {e}"]
    if not isinstance(datos, dict):
        return None, ["El JSON no es un objeto de consulta."]

    avisos = []
    faltan = [c for c in CAMPOS_PACTADOS if c not in datos]
    if faltan:
        avisos.append("Faltan campos del acuerdo de conexión: " + ", ".join(faltan))
    if "aviso_lista_vacia" not in datos:
        avisos.append("Falta la clave `aviso_lista_vacia`, que el acuerdo exige "
                      "siempre presente (nula cuando sí hay resultados).")
    extra = [k for k in datos if k not in CAMPOS_PACTADOS + ["aviso_lista_vacia"]]
    if extra:
        avisos.append("Claves fuera del acuerdo en la raíz: " + ", ".join(extra))
    return datos, avisos


# ===========================================================================
# 2. Verdad de campo: qué proyectos son equivalentes al pedido
# ===========================================================================

def _desviacion(a, b):
    """Desviación relativa entre dos valores numéricos. None si no lo son."""
    if isinstance(a, bool) or isinstance(b, bool):
        return None
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return None
    if a == 0:
        return 0.0 if b == 0 else float("inf")
    return abs(b - a) / abs(a)


def perfil(resultado):
    """
    Cómo de cerca está una candidata del pedido, mirando sólo lo que el propio
    módulo publica. Devuelve (categóricos que no coinciden, desviación máxima).
    """
    fallos, peor = [], 0.0
    for p in resultado.get("parametros_justificativos") or []:
        a, b = p.get("valor_pedido"), p.get("valor_candidata")
        d = _desviacion(a, b)
        if d is None:
            if a != b:
                fallos.append(p.get("parametro"))
        else:
            peor = max(peor, d)
    return fallos, peor


def umbral_automatico(desviaciones):
    """
    El umbral no se elige: se lee del conjunto.

    Se ordenan las desviaciones y se busca el corte que mejor separa dos grupos.
    Un salto sólo cuenta como separación si supera dos filtros:

      · **magnitud** — la desviación se multiplica al menos por SALTO_MINIMO
      · **nitidez**  — el hueco es al menos tan ancho como la dispersión interna
                       del grupo más disperso

    El segundo filtro es el que importa y no es evidente. Un conjunto que va de
    2 % en 2 % hasta el 14 % también duplica en su primer paso, y sin embargo no
    tiene dos grupos: es un continuo. Medir el hueco contra la dispersión lo
    distingue — ahí el mejor corte se queda en 0,55 y no llega al listón.

    Todo se mide en escala logarítmica, porque lo que compara el evaluador son
    proporciones: pasar de 2 % a 4 % y de 20 % a 40 % es el mismo salto.

    Si ningún corte pasa los dos filtros, no hay dos grupos: se aplica el umbral
    de respaldo y se declara, porque entonces la frontera la pone el evaluador y
    no los datos.

    Devuelve (umbral, diagnóstico).
    """
    ds = sorted(d for d in desviaciones
                if d is not None and d != float("inf"))
    if len(ds) < 3:
        return TOLERANCIA_RESPALDO, {
            "automatico": False,
            "motivo": (f"hacen falta al menos tres candidatas comparables para "
                       f"buscar una separación, y hay {len(ds)}")}

    logs = [math.log(max(d, SUELO)) for d in ds]
    mejor = None
    for i in range(1, len(ds)):
        hueco = logs[i] - logs[i - 1]
        dispersion = max(logs[i - 1] - logs[0], logs[-1] - logs[i], 1e-9)
        nitidez = hueco / dispersion
        razon = ds[i] / max(ds[i - 1], SUELO)
        if mejor is None or nitidez > mejor["nitidez"]:
            mejor = {"i": i, "nitidez": nitidez, "razon": razon,
                     "debajo": ds[i - 1], "encima": ds[i]}

    base = {"razon": mejor["razon"], "nitidez": mejor["nitidez"],
            "debajo": mejor["debajo"], "encima": mejor["encima"]}

    if mejor["razon"] < SALTO_MINIMO:
        return TOLERANCIA_RESPALDO, {
            **base, "automatico": False,
            "motivo": (f"el mejor corte del conjunto sólo multiplica la desviación "
                       f"por {mejor['razon']:.1f}, por debajo del ×{SALTO_MINIMO:.0f} "
                       f"que se exige")}
    if mejor["nitidez"] < NITIDEZ_MINIMA:
        return TOLERANCIA_RESPALDO, {
            **base, "automatico": False,
            "motivo": (f"las desviaciones forman un continuo: el mejor hueco "
                       f"({mejor['debajo']:.1%} a {mejor['encima']:.1%}) mide "
                       f"{mejor['nitidez']:.2f} veces la dispersión interna, y hace "
                       f"falta al menos {NITIDEZ_MINIMA:.0f}")}

    umbral = (max(mejor["debajo"], SUELO) * mejor["encima"]) ** 0.5
    return umbral, {
        **base, "automatico": True,
        "motivo": (f"el conjunto se separa solo: la desviación salta de "
                   f"{mejor['debajo']:.1%} a {mejor['encima']:.1%} —se multiplica por "
                   f"{mejor['razon']:.1f}— y ese hueco mide {mejor['nitidez']:.1f} "
                   f"veces la dispersión interna de los grupos")}


def verdad_de_campo(datos, tolerancia=None, contribuciones=None):
    """
    Un esperado por proyecto equivalente al pedido. Equivalente = coincide
    exactamente en todos los parámetros categóricos y no se desvía más de la
    tolerancia en ninguno de los numéricos.

    Se calcula sin mirar el orden que propone el módulo: el ranking es
    justamente lo que se está juzgando.
    """
    resultados = datos.get("resultados") or []
    perfiles = []
    for r in resultados:
        fallos, peor = perfil(r)
        perfiles.append({"id_proyecto": r.get("id_proyecto"),
                         "posicion": r.get("posicion"),
                         "categoricos_distintos": fallos, "desviacion": peor})

    # El umbral se deriva de las candidatas que superan el filtro categórico: son
    # las únicas comparables entre sí. Si quien llama impone uno, se respeta y se
    # declara como impuesto.
    comparables = [p["desviacion"] for p in perfiles if not p["categoricos_distintos"]]
    if tolerancia is None:
        tolerancia, diagnostico = umbral_automatico(comparables)
    else:
        diagnostico = {"automatico": False, "impuesto": True,
                       "motivo": "umbral fijado a mano desde la interfaz"}

    for p in perfiles:
        p["equivalente"] = (not p["categoricos_distintos"]
                            and p["desviacion"] <= tolerancia)

    equivalentes = [p for p in perfiles if p["equivalente"]]
    otros = [p for p in perfiles if not p["equivalente"]]

    # Margen del conjunto: si los dos grupos no se separan con holgura, el umbral
    # deja de ser defendible y hay que verlo.
    peor_equiv = max((p["desviacion"] for p in equivalentes), default=None)
    mejor_otro = min((p["desviacion"] for p in otros
                      if not p["categoricos_distintos"]), default=None)

    contexto = {
        "datos": datos, "perfiles": perfiles, "tolerancia": tolerancia,
        "umbral": diagnostico,
        "consulta": datos.get("id_consulta"), "peso": datos.get("peso_semantico"),
        "n_resultados": len(resultados), "n_descartados": len(datos.get("descartados") or []),
        "margen": (peor_equiv, mejor_otro),
        "contribuciones": contribuciones,
    }
    return equivalentes, contexto


def adelantamientos(perfiles):
    """
    Proyectos no equivalentes que van por delante de alguno que sí lo es.

    La precisión en cabeza mide cuántos huecos del top-N ocupa quien no debería,
    pero se queda corta: un no equivalente en la posición N+1 que adelanta a un
    equivalente en la N+2 tampoco está bien colocado y no aparece en esa cuenta.
    Esto lo recoge.
    """
    eq = [p for p in perfiles if p["equivalente"] and p["posicion"]]
    no_eq = [p for p in perfiles if not p["equivalente"] and p["posicion"]]
    out = []
    for x in no_eq:
        superados = [e["id_proyecto"] for e in eq if e["posicion"] > x["posicion"]]
        if superados:
            out.append({"proyecto": x["id_proyecto"], "posicion": x["posicion"],
                        "desviacion": x["desviacion"], "adelanta_a": superados})
    return out


def cabeza(datos, n):
    """Los n primeros del ranking, que es donde deberían estar los equivalentes."""
    orden = sorted(datos.get("resultados") or [],
                   key=lambda r: r.get("posicion") or 0)
    return [{"id_proyecto": r.get("id_proyecto"), "posicion": r.get("posicion"),
             "resultado": r} for r in orden[:n]]


# ===========================================================================
# 3. Recálculos independientes
# ===========================================================================

def recalcular_puntuaciones(datos, tol=1e-9):
    """puntuación = w · semántico_normalizado + (1 − w) · paramétrico_normalizado."""
    w = datos.get("peso_semantico")
    out = []
    for r in datos.get("resultados") or []:
        s = ((r.get("senales") or {}).get("semantico") or {}).get("normalizado")
        p = ((r.get("senales") or {}).get("parametrico") or {}).get("normalizado")
        emitida = r.get("puntuacion")
        if None in (w, s, p, emitida):
            out.append({"id_proyecto": r.get("id_proyecto"), "cuadra": False,
                        "emitida": emitida, "recalculada": None})
            continue
        calc = w * s + (1 - w) * p
        out.append({"id_proyecto": r.get("id_proyecto"),
                    "cuadra": abs(calc - emitida) <= tol,
                    "emitida": emitida, "recalculada": calc})
    return out


def revisar_orden(datos):
    """Posiciones consecutivas desde 1 y puntuación que no sube al bajar."""
    rs = datos.get("resultados") or []
    posiciones = [r.get("posicion") for r in rs]
    consecutivas = posiciones == list(range(1, len(rs) + 1))
    inversiones = []
    for a, b in zip(rs, rs[1:]):
        if (a.get("puntuacion") or 0) < (b.get("puntuacion") or 0):
            inversiones.append((a.get("id_proyecto"), b.get("id_proyecto")))
    return consecutivas, inversiones


def revisar_normalizacion(datos, tol=1e-9):
    """Si la escala es min-max, el mejor vale 1 y el peor 0 en cada señal."""
    rs = datos.get("resultados") or []
    fuera = []
    for señal in ("semantico", "parametrico"):
        vals = [((r.get("senales") or {}).get(señal) or {}).get("normalizado")
                for r in rs]
        vals = [v for v in vals if isinstance(v, (int, float))]
        if len(vals) < 2:
            continue
        if abs(max(vals) - 1.0) > tol or abs(min(vals)) > tol:
            fuera.append((señal, round(min(vals), 4), round(max(vals), 4)))
    return fuera


def revisar_pedido(datos):
    """El mismo parámetro del pedido debe llevar el mismo valor en todo el fichero."""
    visto, choques = {}, []
    for r in datos.get("resultados") or []:
        for p in r.get("parametros_justificativos") or []:
            k, v = p.get("parametro"), p.get("valor_pedido")
            if k in visto and visto[k] != v:
                choques.append((k, visto[k], v))
            visto.setdefault(k, v)
    for x in datos.get("descartados") or []:
        k, v = x.get("parametro"), x.get("valor_pedido")
        if k in visto and visto[k] != v:
            choques.append((k, visto[k], v))
        visto.setdefault(k, v)
    return visto, choques


def revisar_particion(datos):
    """Cada candidata aparece exactamente una vez: o en resultados o en descartados."""
    ids_r = [r.get("id_proyecto") for r in datos.get("resultados") or []]
    ids_d = [x.get("id_proyecto") for x in datos.get("descartados") or []]
    solape = sorted(set(ids_r) & set(ids_d))
    repes = sorted({i for i in ids_r if ids_r.count(i) > 1}
                   | {i for i in ids_d if ids_d.count(i) > 1})
    return {"n_resultados": len(ids_r), "n_descartados": len(ids_d),
            "corpus": len(set(ids_r) | set(ids_d)), "solape": solape,
            "repetidos": repes}


# Cuánto tienen que separarse dos candidatas para que una inversión cuente. Por
# debajo de esto son empates y no dicen nada.
MARGEN_INVERSION = 0.01


def _rangos(valores):
    orden = sorted(range(len(valores)), key=lambda i: valores[i])
    r = [0.0] * len(valores)
    i = 0
    while i < len(orden):
        j = i
        while j + 1 < len(orden) and valores[orden[j + 1]] == valores[orden[i]]:
            j += 1
        medio = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[orden[k]] = medio
        i = j + 1
    return r


def spearman(xs, ys):
    """Correlación de rangos. Aquí interesa el signo tanto como la magnitud."""
    if len(xs) < 3:
        return None
    rx, ry = _rangos(xs), _rangos(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx) ** 0.5
    dy = sum((b - my) ** 2 for b in ry) ** 0.5
    return round(num / (dx * dy), 3) if dx and dy else None


def revisar_calibracion(datos):
    """
    ¿La puntuación mide lo que dice medir?

    Los demás casos comprueban que el ranking está bien **construido**: que la
    aritmética cuadra, que el orden sigue a la puntuación, que las escalas
    normalizan. Todos ellos pasarían aunque la puntuación fuese un número al azar,
    porque sólo miran su coherencia interna.

    Éste mira otra cosa: si el número **significa** algo. El módulo publica, en
    `parametros_justificativos`, los valores del pedido y de cada candidata. De ahí
    sale una medida independiente de cuánto se parecen de verdad — la desviación
    máxima en los parámetros duros—. Si la puntuación midiera parecido, las dos
    magnitudes tendrían que moverse en sentidos contrarios: más desviación, menos
    puntuación.

    Cuando `peso_semantico` es 0 la exigencia es total, porque entonces la
    puntuación **es** la señal paramétrica y no hay nada más que la explique. Con
    peso mayor que cero parte del número viene de una señal semántica que el
    evaluador no puede recalcular sin el corpus, así que la incoherencia se
    informa pero no se puntúa: acusar sin poder demostrarlo sería justo lo que este
    sistema le reprocha a los módulos que evalúa.
    """
    res = [r for r in (datos.get("resultados") or [])
           if r.get("puntuacion") is not None]
    peso = datos.get("peso_semantico")
    exigible = (peso == 0)

    if len(res) < 3:
        return {"exigible": False, "n": len(res), "rho": None, "inversiones": [],
                "peso_semantico": peso,
                "motivo": "hacen falta al menos tres resultados para hablar de "
                          "correspondencia"}

    desviaciones = [perfil(r)[1] for r in res]
    puntuaciones = [r["puntuacion"] for r in res]

    inversiones = []
    for i in range(len(res)):
        for j in range(len(res)):
            if (desviaciones[i] < desviaciones[j] - MARGEN_INVERSION
                    and puntuaciones[i] < puntuaciones[j] - MARGEN_INVERSION):
                inversiones.append({
                    "mejor": res[i].get("id_proyecto"),
                    "peor": res[j].get("id_proyecto"),
                    "desv_mejor": desviaciones[i], "desv_peor": desviaciones[j],
                    "punt_mejor": puntuaciones[i], "punt_peor": puntuaciones[j],
                    "factor": (desviaciones[j] / desviaciones[i]
                               if desviaciones[i] > 0 else None)})

    # La inversión más escandalosa primero: la que más multiplica la desviación.
    inversiones.sort(key=lambda x: -(x["factor"] or 0))

    return {"exigible": exigible, "n": len(res), "peso_semantico": peso,
            "rho": spearman(desviaciones, puntuaciones),
            "inversiones": inversiones,
            "motivo": None if exigible else
                      (f"el peso semántico es {peso}, así que parte de la puntuación "
                       f"viene de una señal que el evaluador no puede recalcular sin "
                       f"el corpus")}


# ---------------------------------------------------------------------------
# Reproducción del ranking desde la tabla de contribuciones
# ---------------------------------------------------------------------------
# Declarado por Álvaro el 27/08/2026, después de que este evaluador marcase
# inversiones entre desviación y puntuación:
#
#   · La puntuación paramétrica reparte 50 % a los numéricos y 50 % a los
#     categóricos blandos, y dentro de cada mitad todos pesan igual (media
#     simple, 1/N).
#   · Los 11 numéricos pesan ≈4,5 % cada uno; los 7 categóricos blandos ≈7,1 %.
#   · Los 6 categóricos duros aportan 0 %: son los filtros de la Capa 1 y todos
#     los supervivientes los cumplen por construcción.
#   · `parametros_justificativos` publica 8 parámetros duros. Seis valen cero y
#     los otros dos —presión y temperatura de diseño— suman menos del 10 %.
#
# Es decir: la justificación que acompaña a cada resultado NO explica su
# posición. Ésa fue la corrección que Álvaro le hizo a este evaluador, y por eso
# el caso 11 dejó de preguntar «¿la puntuación sigue a la desviación publicada?»
# —una pregunta cuya respuesta correcta es «no, y no pasa nada»— y pasó a
# preguntar lo único que sí es exigible: **¿la ordenación se reproduce desde los
# parámetros que Álvaro declara que entran, con los pesos que declara?**
#
# La diferencia importa: la primera versión producía falsos positivos sobre
# salidas correctas; ésta no puede, porque no supone nada sobre qué parámetro
# debería importar. Sólo rehace la cuenta declarada.

PESOS_DECLARADOS = {
    "numericos": 0.50, "categoricos_blandos": 0.50, "categoricos_duros": 0.0,
    "fuente": "Álvaro Subias, 27/08/2026",
    "reparto": "media simple (1/N) dentro de cada mitad",
}

# Columnas mínimas de la tabla de contribuciones.
COLUMNAS_CONTRIB = ["grupo", "candidato", "parametro", "tipo", "dura",
                    "contribucion_a_bruto"]

TOL_REPRODUCCION = 0.005   # las contribuciones vienen redondeadas a 4 decimales


def cargar_contribuciones(texto):
    """
    Lee la tabla de contribución por parámetro (CSV). Una fila por parámetro y
    candidata. Devuelve {grupo: {candidata: {parametro: (contribucion, dura)}}}.

    Que la tabla venga en un fichero aparte y no dentro de la salida es
    exactamente el hallazgo de trazabilidad: hoy hace falta pedírsela al autor.
    """
    import csv, io
    filas = list(csv.DictReader(io.StringIO(texto.lstrip("﻿"))))
    if not filas:
        raise ValueError("La tabla de contribuciones está vacía.")
    faltan = [c for c in COLUMNAS_CONTRIB if c not in filas[0]]
    if faltan:
        raise ValueError("Faltan columnas en la tabla: " + ", ".join(faltan))

    tabla = {}
    for f in filas:
        c = (f.get("contribucion_a_bruto") or "").strip()
        try:
            valor = float(c) if c else 0.0
        except ValueError:
            valor = 0.0
        dura = str(f.get("dura", "")).strip().lower() in ("true", "1", "sí", "si")
        (tabla.setdefault(f["grupo"], {})
              .setdefault(f["candidato"], {}))[f["parametro"]] = (valor, dura)
    return tabla


def peso_de_justificativos(tabla):
    """
    Cuánto de la puntuación pueden explicar, como máximo, los parámetros que el
    módulo publica como justificativos.

    No mide lo que aportan en una candidata concreta —eso depende de lo bien que
    coincida— sino el techo: el peso que tendrían si coincidieran perfectamente.
    Se obtiene dividiendo cada contribución observada entre su cercanía, que es
    lo que la tabla ya trae por columna.
    """
    duros_num, blandos, num = set(), set(), set()
    for grupo in tabla.values():
        for params in grupo.values():
            for nombre, (_, dura) in params.items():
                (duros_num if dura else blandos).add(nombre)
    # Los duros categóricos no traen contribución: no cuentan.
    return {"duros_con_peso": sorted(duros_num), "otros": sorted(blandos),
            "n_duros": len(duros_num), "n_otros": len(blandos)}


def reproducir_ranking(datos, tabla):
    """
    Rehace la ordenación desde la tabla de contribuciones y la compara con la
    publicada.

    El bruto de cada candidata es la suma de las contribuciones de todos sus
    parámetros. La puntuación publicada es ese bruto normalizado min-max dentro
    del grupo: el mejor vale 1 y el peor 0 —la misma escala que ya comprueba el
    caso 3—. Si las dos cosas cuadran, la puntuación es auditable por un tercero
    con la tabla delante, que es todo lo que este caso afirma.

    Devuelve `exigible=False` si no hay tabla para este pedido: el caso queda
    pendiente con lo que hace falta para cerrarlo, no falla.
    """
    res = [r for r in (datos.get("resultados") or [])
           if r.get("puntuacion") is not None]
    ped = datos.get("pedido_consultado")
    pedido = ped if isinstance(ped, str) else (
        (ped or {}).get("id_proyecto") or (ped or {}).get("id")
        or datos.get("id_consulta"))

    if not tabla:
        return {"exigible": False, "motivo": "no se ha aportado la tabla de "
                                             "contribución por parámetro",
                "filas": [], "discrepancias": [], "grupo": None}
    if len(res) < 2:
        return {"exigible": False, "motivo": "hacen falta al menos dos resultados "
                                             "para comprobar una escala min-max",
                "filas": [], "discrepancias": [], "grupo": None}

    # El grupo de la tabla se identifica por el pedido. `pedido_consultado` suele
    # venir como una frase larga («SYN-0041.md (oferta …) — caso con …»), así que
    # se busca el identificador dentro; y si aun así no aparece, se elige el grupo
    # que más candidatas de esta consulta cubra.
    # Los identificadores del JSON llevan extensión («SYN-0042.md») y los de la
    # tabla no. Se normalizan por el identificador desnudo.
    def _desnudo(x):
        x = str(x or "")
        return x.rsplit(".", 1)[0] if x.lower().endswith(".md") else x

    ids = [_desnudo(r.get("id_proyecto")) for r in res]
    grupo = next((g for g in tabla if g == pedido), None)
    if grupo is None and isinstance(pedido, str):
        grupo = next((g for g in tabla if g in pedido), None)
    if grupo is None:
        cubre = {g: sum(1 for i in ids if i in c) for g, c in tabla.items()}
        mejor = max(cubre, key=cubre.get, default=None)
        if mejor is not None and cubre[mejor] >= 2:
            grupo = mejor
    if grupo is None:
        return {"exigible": False,
                "motivo": (f"la tabla aportada no cubre esta consulta "
                           f"(pedido {pedido}); cubre "
                           + ", ".join(sorted(tabla))),
                "filas": [], "discrepancias": [], "grupo": None}

    fila_grupo = tabla[grupo]
    brutos = {i: sum(v for v, _ in fila_grupo[i].values())
              for i in ids if i in fila_grupo}
    if len(brutos) < 2:
        return {"exigible": False,
                "motivo": f"la tabla sólo cubre {len(brutos)} de las {len(ids)} "
                          f"candidatas de esta consulta",
                "filas": [], "discrepancias": [], "grupo": grupo}

    lo, hi = min(brutos.values()), max(brutos.values())
    span = hi - lo

    filas, discrepancias = [], []
    for r in res:
        i = _desnudo(r.get("id_proyecto"))
        if i not in brutos:
            continue
        rehecha = (brutos[i] - lo) / span if span else 1.0
        emitida = r["puntuacion"]
        d = abs(rehecha - emitida)
        filas.append({"id_proyecto": i, "bruto": round(brutos[i], 4),
                      "rehecha": round(rehecha, 4), "emitida": round(emitida, 4),
                      "delta": round(d, 4), "cuadra": d <= TOL_REPRODUCCION})
        if d > TOL_REPRODUCCION:
            discrepancias.append(filas[-1])

    orden_emitido = [f["id_proyecto"] for f in
                     sorted(filas, key=lambda x: -x["emitida"])]
    orden_rehecho = [f["id_proyecto"] for f in
                     sorted(filas, key=lambda x: -x["rehecha"])]

    return {"exigible": True, "motivo": None, "grupo": grupo, "filas": filas,
            "discrepancias": discrepancias,
            "orden_coincide": orden_emitido == orden_rehecho,
            "orden_emitido": orden_emitido, "orden_rehecho": orden_rehecho,
            "peor_delta": max((f["delta"] for f in filas), default=0.0),
            "n": len(filas)}


# ===========================================================================
# 4. Contraste y batería
# ===========================================================================

def _comparar(esperado, reportado):
    """
    El emparejamiento es por identificador, así que lo que se comprueba aquí es
    que lo que el módulo publica sobre ese proyecto se sostiene: que sus
    parámetros justificativos citan el mismo pedido que el resto del fichero.
    """
    r = reportado.get("resultado") or {}
    fallos, peor = perfil(r)
    if fallos:
        return False, (f"lo coloca en cabeza pero sus parámetros {', '.join(fallos)} "
                       f"no coinciden con los del pedido")
    return True, ""


ETIQUETAS_TABLA = {"si": "En cabeza", "error": "En cabeza con datos que no cuadran",
                   "no": "Fuera de cabeza"}


def evaluar(esperados, contexto, repeticion=None, modo_lectura="determinista",
            evidencias=None):
    datos = contexto["datos"]
    tolerancia = contexto["tolerancia"]
    perfiles = contexto["perfiles"]
    n = len(esperados)
    reportados = cabeza(datos, n)

    contraste = C.contrastar(esperados, reportados,
                             clave=lambda x: x["id_proyecto"], comparar=_comparar)
    casos = {}

    # 1 — aritmética de la puntuación                       [acuerdo de conexión]
    recalc = recalcular_puntuaciones(datos)
    malas = [x for x in recalc if not x["cuadra"]]
    casos[1] = B.caso(
        bool(recalc) and not malas,
        (f"Las {len(recalc)} puntuaciones se reproducen con la fórmula declarada "
         f"y un peso semántico de {contexto['peso']}."
         if not malas else
         "No cuadran: " + "; ".join(
             f"{x['id_proyecto']} emite {x['emitida']} y la fórmula da "
             f"{x['recalculada']}" for x in malas[:4]))
        if recalc else "La consulta no devuelve resultados que recalcular.",
        no_aplica=not recalc,
        requiere="una consulta con al menos un resultado" if not recalc else None)

    # 2 — orden del ranking                                 [acuerdo de conexión]
    consecutivas, inversiones = revisar_orden(datos)
    casos[2] = B.caso(
        bool(datos.get("resultados")) and consecutivas and not inversiones,
        (f"{contexto['n_resultados']} posiciones consecutivas desde 1 y puntuación "
         f"monótona decreciente."
         if consecutivas and not inversiones else
         ("Las posiciones no son consecutivas desde 1. " if not consecutivas else "")
         + ("Puntuación que sube al bajar de posición: "
            + "; ".join(f"{a} antes que {b}" for a, b in inversiones[:3]) + "."
            if inversiones else ""))
        if datos.get("resultados") else "La consulta no devuelve ranking que ordenar.",
        no_aplica=not datos.get("resultados"),
        requiere="una consulta con resultados" if not datos.get("resultados") else None)

    # 3 — normalización de las señales                      [acuerdo de conexión]
    fuera = revisar_normalizacion(datos)
    hay_dos = len(datos.get("resultados") or []) >= 2
    casos[3] = B.caso(
        hay_dos and not fuera,
        ("Las dos señales normalizan al rango completo: el mejor vale 1 y el peor 0."
         if not fuera else
         "Fuera de rango: " + "; ".join(f"{s} va de {mn} a {mx}" for s, mn, mx in fuera))
        if hay_dos else
        "Hacen falta al menos dos resultados para comprobar una escala min-max.",
        no_aplica=not hay_dos,
        requiere="una consulta con dos o más resultados" if not hay_dos else None)

    # 4 — los equivalentes en cabeza                         [calidad del ranking]
    peor_equiv, mejor_otro = contexto["margen"]
    fuera_cabeza = [e["id_proyecto"] for e in contraste["omitidas"]]
    colados = [r["id_proyecto"] for r in contraste["falsas"]]
    adelantan = adelantamientos(perfiles)
    diag = contexto.get("umbral") or {}
    margen = (f" Umbral de equivalencia: {tolerancia:.1%}, "
              + ("derivado del propio conjunto — " if diag.get("automatico")
                 else "de respaldo — ") + diag.get("motivo", "") + ".")
    if peor_equiv is not None and mejor_otro is not None:
        margen += (f" El equivalente que más se desvía está al {peor_equiv:.1%} y el "
                   f"no equivalente que menos, al {mejor_otro:.1%}.")
    casos[4] = B.caso(
        bool(esperados) and not fuera_cabeza and not colados and not adelantan,
        (f"{n} proyecto(s) equivalente(s) al pedido; el módulo coloca "
         f"{len(contraste['detectadas'])} en las {n} primeras posiciones."
         + (f" Fuera de cabeza: "
            + ", ".join(f"{i} (posición "
                        f"{next(p['posicion'] for p in perfiles if p['id_proyecto'] == i)})"
                        for i in fuera_cabeza) + "." if fuera_cabeza else "")
         + (f" Colados en cabeza sin ser equivalentes: {', '.join(colados)}."
            if colados else "")
         + (" Adelantan a algún equivalente, con la desviación que llevan: "
            + "; ".join(f"{a['proyecto']} en la posición {a['posicion']} "
                        f"({a['desviacion']:.0%} de desviación) pasa por delante de "
                        f"{', '.join(a['adelanta_a'])}" for a in adelantan) + "."
            if adelantan else "")
         + margen
         if esperados else
         "Ningún resultado es equivalente al pedido dentro de la tolerancia, así que "
         "no hay cabeza de ranking que juzgar."),
        no_aplica=not esperados,
        requiere=("una consulta cuyo pedido tenga al menos un proyecto equivalente en "
                  "el corpus") if not esperados else None)

    # 5 — partición del corpus                              [acuerdo de conexión]
    part = revisar_particion(datos)
    casos[5] = B.caso(
        not part["solape"] and not part["repetidos"],
        f"{part['n_resultados']} resultados y {part['n_descartados']} descartados "
        f"sobre {part['corpus']} candidatas, sin solapamiento ni repeticiones."
        + (f" Aparecen en las dos listas: {', '.join(part['solape'])}."
           if part["solape"] else "")
        + (f" Repetidos dentro de una lista: {', '.join(part['repetidos'])}."
           if part["repetidos"] else ""))

    # 6 — coherencia del pedido                             [acuerdo de conexión]
    pedido, choques = revisar_pedido(datos)
    casos[6] = B.caso(
        bool(pedido) and not choques,
        (f"El único parámetro del pedido lleva el mismo valor en los "
         f"{part['n_descartados']} descartados." if len(pedido) == 1 else
         f"Los {len(pedido)} parámetros del pedido llevan el mismo valor en los "
         f"resultados y en los {part['n_descartados']} descartados.")
        + (" Discrepan: " + "; ".join(f"{k}: {a} frente a {b}"
                                      for k, a, b in choques[:3]) + "."
           if choques else ""),
        omitir=not pedido,
        requiere="una consulta que declare los parámetros del pedido" if not pedido else None)

    # 7 — trazabilidad del descarte                         [acuerdo de conexión]
    ds = datos.get("descartados") or []
    incompletos = [x.get("id_proyecto") for x in ds
                   if not x.get("parametro") or "valor_pedido" not in x
                   or "valor_candidata" not in x]
    casos[7] = B.caso(
        bool(ds) and not incompletos,
        f"Los {len(ds)} descartes declaran el parámetro que los excluyó y los dos "
        f"valores enfrentados."
        + (f" Sin justificación completa: {', '.join(incompletos[:5])}."
           if incompletos else "")
        if ds else "Esta consulta no descarta ninguna candidata.",
        no_aplica=not ds,
        requiere="una consulta con candidatas descartadas" if not ds else None)

    # 8 — aviso de lista vacía                          [comportamiento ante error]
    vacia = not datos.get("resultados")
    aviso = datos.get("aviso_lista_vacia")
    if vacia:
        conteo = (aviso or {}).get("conteo_por_parametro") or {}
        real = {}
        for x in ds:
            real[x.get("parametro")] = real.get(x.get("parametro"), 0) + 1
        casos[8] = B.caso(
            bool(aviso) and conteo == real,
            (f"La lista está vacía y el aviso lo explica: «{(aviso or {}).get('mensaje', '')}»"
             + ("" if conteo == real else
                f" El recuento del aviso {conteo} no coincide con los descartes "
                f"reales {real}."))
            if aviso else
            "La lista está vacía y no hay aviso que explique por qué: aguas abajo no "
            "se puede distinguir de «no hay proyectos parecidos».")
    else:
        casos[8] = B.caso(
            aviso is None,
            "Hay resultados y el aviso de lista vacía viene a nulo, como exige el "
            "acuerdo." if aviso is None else
            "Hay resultados y aun así se emite aviso de lista vacía.")

    # 9 — parámetros no verificados                    [campo propuesto por Álvaro]
    con_extra = [r for r in datos.get("resultados") or []
                 if isinstance(r.get("extra_no_pactado"), dict)]
    no_verif = [(r.get("id_proyecto"),
                 r["extra_no_pactado"].get("parametros_no_verificados") or [])
                for r in con_extra]
    con_algo = [(i, v) for i, v in no_verif if v]
    if not con_extra:
        casos[9] = B.caso(False, "Ningún resultado declara el campo "
                                 "`extra_no_pactado`.", omitir=True,
                          requiere="una consulta cuyos resultados declaren el campo")
    elif not con_algo:
        casos[9] = B.caso(
            False,
            f"Los {len(con_extra)} resultados declaran el campo, pero la lista de "
            f"parámetros no verificados viene vacía en todos: el campo está, y no "
            f"puede comprobarse que funcione.",
            no_aplica=True,
            requiere=("una consulta con al menos una candidata que sobreviva al filtro "
                      "por faltarle el dato de un parámetro duro"))
    else:
        casos[9] = B.caso(
            True,
            f"{len(con_algo)} de {len(con_extra)} resultados declaran parámetros sin "
            f"verificar: "
            + "; ".join(f"{i}: {', '.join(v)}" for i, v in con_algo[:3]) + ".")

    # 10 — repetibilidad                                   [criterio transversal]
    if repeticion is None:
        casos[10] = B.caso(False, "No se ha aportado una segunda ejecución.",
                           omitir=True,
                           requiere=("una segunda exportación de la misma consulta "
                                     "sobre el mismo corpus"))
    else:
        firma = lambda d: [(r.get("posicion"), r.get("id_proyecto"),
                            round(r.get("puntuacion") or 0, 9))
                           for r in sorted(d.get("resultados") or [],
                                           key=lambda x: x.get("posicion") or 0)]
        f1, f2 = firma(datos), firma(repeticion)
        casos[10] = B.caso(
            f1 == f2,
            f"Las dos ejecuciones devuelven el mismo ranking en las {len(f1)} "
            f"posiciones, con las mismas puntuaciones." if f1 == f2 else
            "El ranking varía entre ejecuciones: "
            + "; ".join(f"posición {a[0]}: {a[1]} frente a {b[1]}"
                        for a, b in zip(f1, f2) if a != b))

    # --- Hallazgos de cobertura
    hallazgos = []
    if contexto["peso"] == 0:
        hallazgos.append(B.hallazgo(
            "La señal semántica se calcula y no se usa",
            "El peso semántico de esta consulta es 0, así que el ranking es "
            "íntegramente paramétrico. Las señales semánticas se calculan, se "
            "normalizan y se publican, pero no entran en la puntuación.",
            "La decisión de Álvaro está tomada y medida —en un corpus sintético que "
            "comparte plantilla, el texto se parece demasiado y la señal semántica "
            "empeora el ranking—, pero conviene que quede escrito en el registro de "
            "conexiones: hoy lo que viaja por C7 es un ranking paramétrico, y quien "
            "lo consuma no debería suponer que hay comprensión de texto detrás. Al "
            "re-medirlo con documentos reales, este hallazgo se cierra o se confirma."))

    if perfiles and not (contexto.get("umbral") or {}).get("automatico") \
            and not (contexto.get("umbral") or {}).get("impuesto"):
        hallazgos.append(B.hallazgo(
            "El conjunto no separa por sí solo los proyectos equivalentes",
            "Las desviaciones de las candidatas forman un continuo, sin ningún salto "
            "que permita leer una frontera. "
            + (contexto.get("umbral") or {}).get("motivo", ""),
            "Cuando los datos no se separan, el corte lo pone el evaluador y no el "
            "conjunto, y entonces la exhaustividad y la precisión de este caso "
            "dependen de un número elegido. Hay que decirlo: en esta consulta se está "
            "aplicando el umbral de respaldo, y el resultado del ranking es "
            "discutible hasta que se acuerde el criterio de equivalencia con el "
            "autor del módulo."))

    if part["corpus"] and part["corpus"] < 97:
        hallazgos.append(B.hallazgo(
            "El corpus evaluado no es el mismo en todas las consultas",
            f"Esta consulta evalúa {part['corpus']} candidatas. Cuando el pedido "
            f"procede de una ficha del propio corpus, esa ficha se autoexcluye y el "
            f"total baja en una.",
            "El comportamiento es correcto —un proyecto no debe parecerse a sí "
            "mismo— pero no está escrito en el acuerdo de conexión. Quien compare "
            "dos consultas verá 96 y 97 candidatas sin saber por qué."))

    tabla = [{"Posición": p["posicion"], "Proyecto": p["id_proyecto"],
              "Desviación máxima": f"{p['desviacion']:.1%}",
              "Categóricos que no coinciden":
                  ", ".join(p["categoricos_distintos"]) or "—",
              "Equivalente al pedido": "Sí" if p["equivalente"] else "No",
              "En cabeza": ("Sí" if p["posicion"] and p["posicion"] <= n else "No")}
             for p in perfiles]

    # 11 — la ordenación se reproduce                 [declarado por Álvaro 27/08]
    # Los diez casos anteriores comprueban que el ranking está bien construido:
    # todos pasarían aunque la puntuación fuese un número al azar, porque sólo
    # miran su coherencia interna. Éste comprueba que el número se puede rehacer
    # desde fuera con la regla que el autor declara. No supone nada sobre qué
    # parámetro debería pesar más — esa suposición era la versión anterior de
    # este caso, y era falsa.
    rep = reproducir_ranking(datos, contexto.get("contribuciones"))
    if not rep["exigible"]:
        casos[11] = B.caso(
            False,
            f"No se puede rehacer la ordenación: {rep['motivo']}.",
            omitir=True,
            requiere=("la tabla de contribución por parámetro de esta consulta —una "
                      "fila por candidata y parámetro, con lo que aporta al bruto—, "
                      "que es lo que permite reproducir la puntuación sin el corpus"))
    else:
        ok = not rep["discrepancias"] and rep["orden_coincide"]
        casos[11] = B.caso(
            ok,
            (f"Las {rep['n']} puntuaciones del grupo {rep['grupo']} se rehacen "
             f"sumando la contribución de cada parámetro y normalizando min-max; "
             f"la mayor diferencia con lo emitido es {rep['peor_delta']:.4f}, dentro "
             f"del redondeo de la tabla. El orden rehecho coincide con el publicado."
             if ok else
             ((f"{len(rep['discrepancias'])} puntuación(es) no se rehacen: "
               + "; ".join(f"{x['id_proyecto']} emite {x['emitida']} y la tabla da "
                           f"{x['rehecha']}" for x in rep["discrepancias"][:4]) + ". ")
              if rep["discrepancias"] else "")
             + ("El orden rehecho no coincide con el publicado: "
                + " > ".join(rep["orden_rehecho"][:5]) + " frente a "
                + " > ".join(rep["orden_emitido"][:5]) + "."
                if not rep["orden_coincide"] else "")),
            evidencia=rep["filas"][:8] or None)

    # El diagnóstico que Álvaro corrigió: se conserva, degradado a hallazgo.
    cal = revisar_calibracion(datos)
    if cal["exigible"] and cal["inversiones"]:
        x = cal["inversiones"][0]
        hallazgos.append(B.hallazgo(
            "La justificación publicada no explica la posición en el ranking",
            (f"Correlación de rangos ρ = {cal['rho']} entre la desviación en los "
             f"parámetros justificativos y la puntuación, sobre {cal['n']} "
             f"resultados: {len(cal['inversiones'])} par(es) en los que el proyecto "
             f"que más se desvía puntúa más. El más llamativo, {x['peor']} se desvía "
             f"{x['desv_peor']:.1%} y puntúa {x['punt_peor']:.3f} mientras "
             f"{x['mejor']} se desvía {x['desv_mejor']:.1%} y puntúa "
             f"{x['punt_mejor']:.3f}."),
            "Esto NO es un fallo del módulo, y merece la pena decir por qué: los ocho "
            "parámetros de `parametros_justificativos` son filtros de la Capa 1, así "
            "que todos los supervivientes los cumplen y seis de ellos aportan cero a "
            "la puntuación; los otros dos suman menos del 10 %. Quien decide son "
            "siete categóricos secundarios que no se publican. La salida es correcta; "
            "lo que falta es la advertencia. Debe entrar en el acuerdo de conexión: "
            "«`parametros_justificativos` es informativo y no explica la posición». "
            "Sin esa línea, cualquier consumidor de C7 —este evaluador incluido, en "
            "su versión anterior— leerá la justificación como si justificara."))

    # --- Desglose esperado / observado para la plantilla común -------------
    def _l(xs, vacio="ninguno"):
        xs = [str(x) for x in xs if x]
        return ", ".join(xs) if xs else vacio

    NADA = "— el conjunto no contiene esta situación —"
    FALTA = "— no aportado en esta ejecución —"

    _res = datos.get("resultados") or []
    _ds = datos.get("descartados") or []
    _recalc = recalcular_puntuaciones(datos)
    _malas = [x for x in _recalc if not x["cuadra"]]
    _equis = [p["id_proyecto"] for p in perfiles if p["equivalente"]]
    _cabeza = [p["id_proyecto"] for p in perfiles
               if p["posicion"] and p["posicion"] <= n]
    _fuera = revisar_normalizacion(datos)
    _consec, _inv = revisar_orden(datos)
    _aviso = datos.get("aviso_lista_vacia")
    _extra = [r for r in _res if isinstance(r.get("extra_no_pactado"), dict)]

    _d = {
        1: (f"{len(_recalc)} puntuación(es) reproducibles con peso "
            f"{contexto['peso']}" if _recalc else "sin resultados que recalcular",
            (_l([f"{x['id_proyecto']}: emite {x['emitida']}, la fórmula da "
                 f"{x['recalculada']}" for x in _malas]) if _malas
             else f"las {len(_recalc)} cuadran") if _recalc else NADA),
        2: ("posiciones consecutivas desde 1 y puntuación decreciente",
            (("posiciones consecutivas" if _consec else "posiciones no consecutivas")
             + ("; sin inversiones" if not _inv else
                "; sube al bajar de posición: "
                + _l([f"{a} antes que {b}" for a, b in _inv[:3]])))
            if _res else NADA),
        3: ("cada señal de 0 a 1 sobre las supervivientes",
            (_l([f"{s}: de {mn} a {mx}" for s, mn, mx in _fuera])
             if _fuera else "las dos señales cubren el rango completo")
            if len(_res) >= 2 else NADA),
        4: (f"en las {len(esperados)} primeras posiciones: " + _l(_equis),
            "en cabeza: " + _l(_cabeza)),
        5: (f"cada candidata una sola vez, en resultados o en descartes "
            f"({len(_res) + len(_ds)} en total)",
            f"{len(_res)} resultado(s) y {len(_ds)} descarte(s)"),
        6: ("el mismo valor del pedido en todo el fichero",
            _l(sorted({p for p in (contexto.get("pedido_incoherente") or [])}),
               "sin discrepancias")),
        7: ("cada descarte con parámetro y los dos valores enfrentados",
            f"{len(_ds)} descarte(s) declarados" if _ds else NADA),
        8: ("aviso con la causa cuando la lista queda vacía",
            (f"«{(_aviso or {}).get('mensaje', '')}»" if _aviso else "sin aviso")
            if not _res else "hay resultados; aviso a nulo"
            if _aviso is None else "hay resultados y aun así se emite aviso"),
        9: ("parámetros no verificados declarados por resultado",
            f"{len(_extra)} resultado(s) declaran el campo" if _extra else FALTA),
        11: ("cada puntuación igual a la suma de contribuciones normalizada "
             "min-max, y el mismo orden",
             (f"{rep['n']} rehechas, peor diferencia {rep['peor_delta']:.4f}, "
              f"orden {'coincide' if rep['orden_coincide'] else 'difiere'}"
              if rep["exigible"] else f"no reproducible: {rep['motivo']}")),
        10: ("el mismo ranking en dos exportaciones seguidas",
             ("coincide" if casos[10]["resultado"] == "pasa" else "difiere")
             if repeticion is not None else FALTA),
    }
    for _n, (_esp, _obs) in _d.items():
        if _n in casos:
            casos[_n]["esperado"], casos[_n]["observado"] = _esp, _obs

    return {"esperados": esperados, "reportados": reportados, "contraste": contraste,
            "casos": casos, "hallazgos": hallazgos, "tabla_contraste": tabla,
            "adelantamientos": adelantan, "contexto": contexto,
            "modo_lectura": modo_lectura}


def resumen_consulta(datos):
    """
    Qué es esta consulta, en cristiano.

    Existe porque el nombre del fichero y el JSON crudo no dicen nada a quien no
    los escribió. Sin esto, la pantalla pide elegir entre cuatro ficheros sin
    explicar qué distingue a uno de otro, y el evaluador acaba enseñando un
    veredicto sobre algo que el usuario no sabe qué es.
    """
    datos = datos or {}
    crudo = datos.get("pedido_consultado") or ""
    # Álvaro escribe el pedido y una nota separados por «--». La nota es lo que
    # explica de qué va el caso, así que se saca a la superficie.
    partes = [x.strip() for x in crudo.split("--") if x.strip()]
    pedido = partes[0] if partes else "(sin identificar)"
    nota = " · ".join(partes[1:]) if len(partes) > 1 else ""

    res = datos.get("resultados") or []
    esperados, ctx = verdad_de_campo(datos)
    return {
        "pedido": pedido,
        "nota": nota,
        "consulta": datos.get("id_consulta") or "(sin identificador)",
        "resultados": len(res),
        "descartados": len(datos.get("descartados") or []),
        "corpus": len(res) + len(datos.get("descartados") or []),
        "peso_semantico": datos.get("peso_semantico"),
        "equivalentes": len(esperados),
        "ids_equivalentes": [e["id_proyecto"] for e in esperados],
        "tolerancia": ctx["tolerancia"],
        "lista_vacia": not res,
    }


def sujeto(contexto):
    return f"la consulta {contexto['consulta']}"
