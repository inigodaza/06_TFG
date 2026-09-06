"""
Rama de evaluación del módulo de CONTRADICCIONES Y VALIDACIÓN HUMANA
— Mencía Viñuelas · GraphyCems.

OPERATIVA desde el 22/08/2026, con la exportación del PED1004 que pidió la
batería y que Mencía entregó.

La particularidad de este módulo es que no termina en la detección: incorpora una
decisión humana y debe conservar su rastro. Por eso buena parte de los casos no
miran si encuentra las contradicciones, sino si lo que entrega permite a una
persona revisarlas y si esa revisión queda registrada de forma verificable.

Cómo se calcula aquí la verdad de campo
---------------------------------------
Este módulo entrega una exportación relacional: los hechos extraídos de cada
documento por un lado y las contradicciones por otro. Eso permite una
comprobación mejor que contrastar contra un PDF: **el evaluador ignora la tabla
de contradicciones y la recalcula desde los hechos**. Dos hechos activos del
mismo grupo y del mismo campo con valores distintos son una contradicción, la
haya visto el módulo o no.

Es el contraste más limpio de todo el sistema, porque la fuente y la salida vienen
en el mismo fichero y no hay lectura de por medio que pueda introducir error.

Verdad de campo del PED1004, escrita antes de ejecutar nada
------------------------------------------------------------
Dos hechos activos del campo `fecha_entrega`:

  · Confirmacion_PED1004.pdf → 25/08/2026 («Fecha de entrega confirmada al cliente»)
  · Pedido_PED1004.pdf       → 12/08/2026 («Fecha de entrega comprometida»)

Una contradicción esperada. El módulo emite exactamente esa, con severidad
`medium`, método `deterministic_date`, y una resolución humana que valida el
hecho A —25/08/2026, «Director de Producción», 02/08/2026 14:52—.

El fallo que aparece está en el caso 7 y no se ve mirando la contradicción, se ve
mirando los hechos: **después de resolver, los dos hechos siguen con
`is_active = 1`**. El valor descartado se conserva, que es lo que había que pedir,
pero no queda marcado como descartado. Quien consulte los hechos activos del
pedido recupera las dos fechas sin saber cuál ganó, salvo que reconstruya la
decisión atravesando dos tablas más.
"""

import json

from nucleo import bateria as B
from nucleo import contraste as C
from nucleo import jueces as J
from nucleo.texto import fecha_de, formato_normal, plano

CASOS = {
    1: "Detección de la contradicción con campo, valores y documentos de origen",
    2: "Ausencia de contradicciones cuando los documentos coinciden",
    3: "Literalidad del fragmento aportado como evidencia",
    4: "Declaración del método de detección: regla determinista o IA",
    5: "Registro de la revisión humana: estado, revisor y momento",
    6: "Consulta posterior a la validación: valor confirmado y su procedencia",
    7: "Conservación del valor descartado, marcado como rechazado",
    8: "Aviso de documento no agrupable por pérdida del identificador",
    9: "Distinción entre ausencia de contradicciones e imposibilidad de comprobar",
    10: "Repetibilidad del resultado entre ejecuciones",
    11: "La validación la hace quien tiene autoridad sobre la categoría",
    12: "El rastro de una decisión sobrevive a la decisión siguiente",
    13: "Resolver no altera los hechos ni las contradicciones ya detectadas",
}

ORIGEN = {n: "acuerdo de conexión" for n in CASOS}
ORIGEN[9] = "criterio transversal del evaluador"
ORIGEN[10] = "criterio transversal del evaluador"
# El primero del sistema que no se puede comprobar mirando un solo módulo: las
# validaciones las emite Mencía y el organigrama lo declara Pablo.
ORIGEN[11] = "cruce de C6 (Mencía) con la ontología de autoridad (Pablo)"
ORIGEN[12] = "criterio transversal del evaluador"
ORIGEN[13] = "criterio transversal del evaluador"

ALCANCE = {n: "ejecucion" for n in CASOS}

# Severidad por consecuencia aguas abajo. Aquí el destinatario es la persona que
# valida: lo crítico es lo que la deja decidir sobre una base falsa, o lo que borra
# el rastro de lo que decidió.
SEVERIDAD = {
    1: "critica",   # una contradicción no detectada llega a producción como acuerdo
    2: "alta",      # una contradicción inventada quema tiempo de revisión humana
    3: "alta",      # sin evidencia literal hay que abrir los PDF para decidir
    4: "media",     # el método informa de la fiabilidad, no del contenido
    5: "critica",   # una validación sin rastro no es una validación
    6: "critica",   # el valor confirmado sin procedencia no se puede recurrir
    7: "alta",      # el descartado sigue ahí, pero indistinguible del bueno
    8: "critica",   # un documento fuera del grupo desaparece en silencio
    9: "critica",   # una salida vacía por ilegible se lee como pedido correcto
    10: "alta",     # sin repetibilidad ninguna medición anterior se sostiene
    11: "critica",  # una validación sin autoridad viaja como si fuera firme
    12: "alta",     # se pierde quién decidió antes y qué se revocó
    13: "critica",  # si resolver toca la evidencia, el veredicto se apoya en humo
}

ASPECTOS = {
    1: ("La contradicción no se precisa lo suficiente para poder revisarla",
        "Emitir campo afectado, los dos valores enfrentados y el documento de "
        "procedencia de cada uno: advertir de que hay un conflicto sin decir cuál "
        "no es revisable."),
    3: ("La evidencia aportada no es literal",
        "Citar el fragmento tal como aparece en el documento; si se trunca, "
        "indicarlo."),
    4: ("No consta por qué vía se ha detectado cada contradicción",
        "Declarar el método en cada contradicción, con las dos categorías "
        "diferenciadas de forma explícita."),
    5: ("El rastro de la revisión humana está incompleto",
        "Registrar los tres datos —estado, identidad del revisor y marca temporal— "
        "asociados a la contradicción concreta."),
    6: ("El valor confirmado no se puede consultar con su procedencia",
        "Que la resolución cite el hecho que valida y que el valor resuelto coincida "
        "con el de ese hecho: si no coinciden, la validación deja de ser trazable."),
    7: ("El valor descartado deja de distinguirse del vigente",
        "Al resolver, marcar el hecho descartado —`is_active = 0` o un estado propio "
        "por hecho—. Conservarlo está bien; conservarlo indistinguible del ganador "
        "convierte el histórico en ambigüedad: quien consulte los hechos activos del "
        "pedido recupera los dos valores sin saber cuál se validó."),
    9: ("No consta distinción entre ausencia de contradicciones e ilegibilidad",
        "Diferenciar ambas salidas: una salida vacía por documento ilegible llegaría "
        "a validación humana como señal de pedido correcto."),
    11: ("Una validación puede cerrarse sin que conste que quien la hizo tenía "
         "autoridad sobre ese ámbito",
         "Emitir en la exportación el identificador de rol de quien resuelve "
         "—`resolved_by_role_id` ya existe y viene a nulo— y la categoría de la "
         "contradicción, que ya viaja. Con esos dos campos, cualquiera puede "
         "comprobar contra el organigrama si la decisión la tomó quien podía. "
         "Hoy el módulo lo sabe y lo enseña en pantalla, pero no lo publica: "
         "desde fuera, una propuesta pendiente y una validación firme se ven "
         "exactamente igual."),
    12: ("Cuando alguien revoca una decisión anterior, la anterior desaparece",
         "Conservar las decisiones anteriores en vez de actualizar la fila, o "
         "publicar un campo que declare que hubo una previa y cuál era. El "
         "documento del módulo dice en §2.1 que la tabla es mutable y en §6 que "
         "«nada se sobrescribe»: hay que elegir una de las dos, porque la "
         "auditoría posterior depende de cuál sea cierta."),
    13: ("No consta que la evidencia quede intacta al resolver",
         "Que dos exportaciones del mismo pedido, antes y después de una "
         "resolución, devuelvan los mismos hechos y las mismas contradicciones. "
         "La decisión se pone encima de la evidencia; si la evidencia cambia, el "
         "veredicto se apoya en algo que ya no existe."),
    10: ("El determinismo del resultado no está demostrado",
         "Dos ejecuciones consecutivas sobre el mismo pedido, comparadas por campo, "
         "severidad y huella, no por el texto emitido. El módulo ya emite "
         "`fingerprint` en cada contradicción, así que la comprobación es inmediata "
         "en cuanto haya una segunda exportación."),
}

# Vocabulario de la exportación. Se declara para que el intérprete no adivine y
# para que el veredicto pueda decir qué familia de método se ha ejercitado.
METODOS_DETERMINISTAS = ("deterministic", "rule", "regla", "exact")
METODOS_IA = ("llm", "ia", "ai", "model", "semantic", "embedding")

RESOLUCIONES = {"validate_a": "a", "validate_b": "b", "valida_a": "a",
                "valida_b": "b"}


# ---------------------------------------------------------------------------
# Criterios cualitativos
# ---------------------------------------------------------------------------

CUALITATIVOS = [
    J.criterio(
        "revisable",
        "La contradicción se puede resolver sin abrir los documentos",
        "¿Puede una persona decidir cuál de los dos valores es el correcto leyendo "
        "únicamente lo que el módulo entrega —campo, valores, documentos de origen "
        "y fragmentos de evidencia—, o necesita abrir los PDF para decidir?",
        "Este módulo existe para que alguien decida. Si para decidir hay que abrir "
        "los documentos, el módulo ha detectado el problema pero no ha reducido el "
        "trabajo, que era lo que venía a hacer."),
    J.criterio(
        "severidad",
        "La severidad guarda proporción con la consecuencia",
        "¿La severidad asignada a la contradicción se corresponde con el daño real "
        "que causaría no resolverla, teniendo en cuenta qué campo afecta y cuánto "
        "difieren los valores?",
        "Una severidad que no discrimina obliga a revisarlo todo con la misma "
        "atención, y entonces la cola de revisión no está priorizada: está "
        "simplemente ordenada por fecha."),
    J.criterio(
        "rastro_autonomo",
        "El rastro de la decisión se sostiene solo",
        "Alguien que abra esta exportación dentro de un año, sin conocer el caso, "
        "¿puede saber qué se decidió, quién lo decidió, cuándo y qué valor quedó "
        "descartado, sin tener que reconstruirlo cruzando tablas?",
        "Un registro de auditoría que hay que reconstruir no es un registro de "
        "auditoría. La validación humana sólo aporta garantía si su rastro se lee "
        "sin instrucciones."),
]


def evidencia_panel(datos, tope=6):
    """
    Lo que ven los jueces: la contradicción tal como llega a quien tiene que
    resolverla, con sus hechos y su resolución si la hay. No se les da la verdad
    de campo ni el resultado de la batería: están juzgando si esto se sostiene
    solo, que es la situación del revisor.
    """
    datos = datos or {}
    hechos = {h["id"]: h for h in datos.get("hechos", [])}
    L = [f"PEDIDO: {datos.get('grupo') or '(sin identificar)'}",
         f"MÉTODO DE AGRUPACIÓN: {datos.get('metodo_agrupacion')} "
         f"(confianza declarada: {datos.get('confianza_agrupacion')})", ""]

    L.append(f"CONTRADICCIONES EMITIDAS ({len(datos.get('contradicciones', []))}):")
    for c in (datos.get("contradicciones") or [])[:tope]:
        L.append(f"  · campo «{c['campo']}» · severidad {c['severidad']} · "
                 f"método {c['metodo']}")
        for lado, hid in (("A", c["hecho_a"]), ("B", c["hecho_b"])):
            h = hechos.get(hid)
            if h:
                L.append(f"      hecho {lado}: {h['documento']} → "
                         f"«{h['etiqueta']}» = {h['valor']}"
                         f"  [activo: {'sí' if h['activo'] else 'no'}]")
                L.append(f"        evidencia citada: {h['evidencia'] or '(ninguna)'}")
        r = c.get("resolucion")
        if r:
            L.append(f"      resolución: {r['tipo']} → valor {r['valor']} · "
                     f"por {r['revisor']} · {r['momento']}")
        else:
            L.append("      resolución: ninguna registrada")
    L.append("")

    sueltos = [h for h in datos.get("hechos", [])
               if not any(h["id"] in (c["hecho_a"], c["hecho_b"])
                          for c in datos.get("contradicciones", []))]
    L.append(f"HECHOS EXTRAÍDOS SIN CONTRADICCIÓN ASOCIADA: {len(sueltos)}")
    for h in sueltos[:tope]:
        L.append(f"  · {h['documento']} → «{h['etiqueta']}» = {h['valor']}")

    return "\n".join(L)


FICHA = {
    "id": "contradicciones",
    "nombre": "Contradicciones y validación humana",
    "responsable": "Mencía Viñuelas",
    "empresa": "GraphyCems",
    "conexion": "C6 · Mencía → Evaluación y Calidad",
    "estado_conexion": "documentada",
    "funcion": ("Detecta contradicciones entre los documentos de un pedido, "
                "las presenta con su evidencia y conserva el rastro de la "
                "revisión humana."),
    "verifica": "Íñigo Daza",
    "operativo": True,
    # El módulo entrega una exportación relacional: no hay documento que
    # interpretar, y el evaluador se limita a rehacer la aritmética de los hechos.
    "ia_permitida": False,
    "motivo_ia": ("La exportación ya viene estructurada y la verdad de campo se "
                  "recalcula desde los propios hechos. No hay lectura que "
                  "generalizar, así que la ranura de lectura se queda sin uso."),
    # Decisión declarada y revisable: esta exportación no contiene ningún dato
    # identificable de cliente —dos fechas, un rol y dos nombres de fichero—, así
    # que el panel puede leerla. Si una exportación futura trae razón social,
    # importes o referencias de cliente, esta autorización hay que revisarla antes
    # de convocar al panel.
    "panel_permitido": True,
    "cualitativos": CUALITATIVOS,
    "unidad": ("contradicción", "las contradicciones"),
    "entrada": ("La exportación del pedido en JSON, tal como la genera el módulo. "
                "Trae los hechos extraídos, las contradicciones y las resoluciones "
                "humanas en el mismo fichero."),
    "entrada_respuesta": ("Sube la exportación en JSON, o pégala. Es a la vez la "
                          "fuente y la salida: el evaluador recalcula las "
                          "contradicciones desde los hechos y las contrasta contra "
                          "las que el módulo declara."),
    "casos": CASOS,
    "aspectos": ASPECTOS,
    "alcance": ALCANCE,
    "severidad": SEVERIDAD,
    "origen_casos": ORIGEN,
    "esquema_salida": {
        "type": "object",
        "properties": {
            "document_group": {"type": "array"},
            "extracted_facts": {"type": "array"},
            "contradictions": {"type": "array"},
            "contradiction_resolutions": {"type": "array"},
        },
    },
    "prompt_interpretacion": (
        "Aquí no hace falta modelo: el módulo entrega una exportación relacional y "
        "el evaluador la recorre. La ranura queda declarada por simetría con el "
        "resto de ramas."
    ),
}


# ---------------------------------------------------------------------------
# Interpretación de la exportación
# ---------------------------------------------------------------------------

def interpretar(texto, modo="determinista"):
    """
    Exportación en JSON -> estructura normalizada. Devuelve (datos, avisos).

    Nada de lo que se lee aquí se da por bueno: los nombres de tabla se aceptan
    tal cual porque son el acuerdo de conexión, pero el contenido se vuelve a
    calcular después.
    """
    avisos = []
    if not (texto or "").strip():
        return None, ["No hay exportación que interpretar."]
    try:
        crudo = json.loads(texto)
    except json.JSONDecodeError as e:
        return None, [f"La exportación no es JSON válido: {e}"]
    if not isinstance(crudo, dict):
        return None, ["Se esperaba un objeto JSON con las tablas de la exportación."]

    for tabla in ("document_group", "extracted_facts", "contradictions"):
        if tabla not in crudo:
            avisos.append(f"La exportación no trae la tabla «{tabla}».")

    grupos = crudo.get("document_group") or []
    grupo = grupos[0] if grupos else {}
    if len(grupos) > 1:
        avisos.append(f"La exportación trae {len(grupos)} grupos; se evalúa el "
                      f"primero ({grupo.get('group_key')}).")

    hechos = []
    for h in (crudo.get("extracted_facts") or []):
        hechos.append({
            "id": h.get("id"),
            "grupo": h.get("group_id"),
            "documento": h.get("document_name") or "",
            "campo": h.get("field_name") or "",
            "etiqueta": h.get("raw_field_label") or "",
            "valor": h.get("value_text"),
            "valor_normalizado": h.get("value_normalized"),
            "evidencia": h.get("evidence_excerpt") or "",
            "activo": bool(h.get("is_active", 1)),
            "categoria": h.get("categoria"),
        })

    resoluciones = {}
    for r in (crudo.get("contradiction_resolutions") or []):
        resoluciones[r.get("contradiction_id")] = {
            "tipo": r.get("resolution_type"),
            "valor": r.get("resolved_value"),
            "revisor": r.get("resolved_by"),
            "revisor_rol_id": r.get("resolved_by_role_id"),
            "momento": r.get("resolved_at"),
        }

    contradicciones = []
    for c in (crudo.get("contradictions") or []):
        contradicciones.append({
            "id": c.get("id"),
            "grupo": c.get("group_id"),
            "campo": c.get("field_name") or "",
            "hecho_a": c.get("fact_a_id"),
            "hecho_b": c.get("fact_b_id"),
            "severidad": c.get("severity") or "",
            "metodo": c.get("detection_method") or "",
            "huella": c.get("fingerprint"),
            # La categoría es lo que enlaza con el organigrama de Pablo: dice de
            # qué ámbito es la contradicción y, por tanto, quién puede validarla.
            # Venía en la exportación desde el principio y el intérprete la
            # tiraba, así que el caso de autoridad no tenía con qué trabajar.
            "categoria": c.get("categoria"),
            "resolucion": resoluciones.get(c.get("id")),
        })

    if not hechos:
        avisos.append("La exportación no trae hechos extraídos: sin ellos el "
                      "evaluador no puede recalcular nada por su cuenta.")
    else:
        _mancos = [h["id"] for h in hechos
                   if not (h["campo"] or "").strip() or h["valor"] in (None, "")]
        if _mancos:
            avisos.append(
                f"{len(_mancos)} hecho(s) llegan sin campo o sin valor "
                f"(ids: {', '.join(str(i) for i in _mancos[:8])}"
                f"{'…' if len(_mancos) > 8 else ''}). No pueden contradecir a "
                f"nadie, así que quedan fuera del contraste: un hecho vacío que "
                f"«coincide» con otro hecho vacío no es una comprobación "
                f"superada, es una comprobación que no se ha hecho.")

    datos = {
        "grupo": grupo.get("group_key") or grupo.get("label"),
        "grupo_id": grupo.get("id"),
        "metodo_agrupacion": grupo.get("grouping_method"),
        "confianza_agrupacion": grupo.get("grouping_confidence"),
        "hechos": hechos,
        "contradicciones": contradicciones,
        "resoluciones": resoluciones,
        "documentos": sorted({h["documento"] for h in hechos if h["documento"]}),
        "tablas": sorted(crudo.keys()),
    }
    return datos, avisos


# ---------------------------------------------------------------------------
# Verdad de campo: se recalcula desde los hechos, ignorando lo que el módulo dice
# ---------------------------------------------------------------------------

def _mismo(valor_a, valor_b):
    """
    ¿Dicen lo mismo los dos hechos? Las fechas se comparan como fechas —dd/mm/aaaa
    y aaaa-mm-dd son la misma— y lo demás por texto normalizado.
    """
    fa, fb = fecha_de(str(valor_a or "")), fecha_de(str(valor_b or ""))
    if fa and fb:
        return fa == fb
    na, nb = formato_normal(valor_a), formato_normal(valor_b)
    if na is not None and nb is not None:
        return na == nb
    return plano(str(valor_a or "")) == plano(str(valor_b or ""))


def verdad_de_campo(datos):
    """
    Recorre los hechos que estuvieron en juego, los agrupa por campo y declara una
    contradicción allí donde dos documentos no dicen lo mismo. La tabla
    `contradictions` del módulo no se mira: se contrasta contra esto.

    Por qué no basta con los hechos activos
    ----------------------------------------
    Lo destapó el propio ciclo de mejora. Si el módulo corrige el fallo del caso 7
    —marcar como inactivo el valor descartado tras la validación humana— entonces
    ya sólo queda un hecho activo en ese campo, el evaluador deja de derivar la
    contradicción, y **la precisión se hunde al 0 %: el módulo emite una
    contradicción que la verdad de campo ya no contempla**.

    Sería absurdo. El evaluador estaría castigando exactamente la corrección que él
    mismo pidió, y el compañero que hiciera caso al informe empeoraría su nota.

    Una contradicción resuelta **existió**. Así que también cuentan los hechos
    desactivados cuya desactivación se explica por una revisión humana registrada.
    Para saberlo se usa `contradiction_resolutions` —el rastro de la decisión, un
    hecho sobre lo que ocurrió— y no la tabla de contradicciones, que es lo que se
    está evaluando.
    """
    # Un hecho inactivo sólo vuelve a contar si una persona decidió sobre él.
    resueltos = set()
    for c in datos.get("contradicciones") or []:
        if c.get("resolucion"):
            resueltos.update({c.get("hecho_a"), c.get("hecho_b")})

    # Un hecho sin campo o sin valor no puede contradecir a nadie.
    #
    # Parece una obviedad y no lo era: una exportación con dos hechos vacíos
    # —sólo el `id`, sin `field_name` ni `value_text`— los agrupaba a los dos bajo
    # el campo «» y, como sus valores coincidían (ninguno con ninguno), el caso 2
    # daba **superado**: «un campo con varios documentos que coinciden y el módulo
    # no levanta contradicción en ninguno».
    #
    # Es un aprobado sobre la nada, y es peor que un fallo: el módulo se lleva un
    # caso superado sin que se haya comprobado nada suyo, y la tasa sube. Un
    # evaluador que aprueba con la entrada vacía no está midiendo, está contando.
    incompletos = [h for h in datos["hechos"]
                   if not (h.get("campo") or "").strip()
                   or h.get("valor") in (None, "")]
    utiles = [h for h in datos["hechos"] if h not in incompletos]

    en_juego = [h for h in utiles if h["activo"] or h["id"] in resueltos]
    por_campo = {}
    for h in en_juego:
        por_campo.setdefault(h["campo"], []).append(h)

    esperados, coincidentes = [], []
    for campo, hs in sorted(por_campo.items()):
        if len(hs) < 2:
            continue
        conflicto = None
        for i in range(len(hs)):
            for k in range(i + 1, len(hs)):
                if not _mismo(hs[i]["valor"], hs[k]["valor"]):
                    conflicto = (hs[i], hs[k])
                    break
            if conflicto:
                break
        if conflicto:
            a, b = conflicto
            esperados.append({
                "clave": f"{datos['grupo']}::{campo}",
                "campo": campo,
                "hechos": {a["id"], b["id"]},
                "valores": [a["valor"], b["valor"]],
                "documentos": [a["documento"], b["documento"]],
            })
        else:
            coincidentes.append({"campo": campo, "hechos": len(hs),
                                 "valor": hs[0]["valor"]})

    contexto = {
        "datos": datos,
        "pedido": datos["grupo"],
        "hechos_incompletos": [h["id"] for h in incompletos],
        "campos_con_varios_documentos": sum(1 for hs in por_campo.values() if len(hs) >= 2),
        "campos_coincidentes": coincidentes,
        "hechos_activos": sum(1 for h in datos["hechos"] if h["activo"]),
        "hechos_en_juego": len(en_juego),
        "hechos_totales": len(datos["hechos"]),
    }
    return esperados, contexto


def _comparar(esperado, reportado):
    """
    Una contradicción reportada se sostiene si señala los dos hechos que están en
    conflicto de verdad. Señalar el campo correcto pero apuntar a otros hechos no
    es un acierto a medias: aguas abajo se revisaría el documento equivocado.
    """
    citados = {reportado["hecho_a"], reportado["hecho_b"]}
    if citados != esperado["hechos"]:
        return False, (f"señala los hechos {sorted(x for x in citados if x is not None)} "
                       f"y los que están en conflicto son "
                       f"{sorted(esperado['hechos'])}")
    if not reportado["severidad"]:
        return False, "no declara severidad"
    if not reportado["metodo"]:
        return False, "no declara el método de detección"
    return True, ""


def familia_metodo(metodo):
    m = (metodo or "").lower()
    if any(t in m for t in METODOS_IA):
        return "ia"
    if any(t in m for t in METODOS_DETERMINISTAS):
        return "determinista"
    return "sin clasificar"


# ---------------------------------------------------------------------------
# Batería
# ---------------------------------------------------------------------------

def comparar_estados(antes, despues):
    """
    Qué ha pasado entre dos exportaciones del mismo pedido.

    Por qué la unidad de evaluación de este módulo es la decisión
    -------------------------------------------------------------
    A un lector se le mide con una foto: se le dan documentos y se mira si lo que
    dice coincide con lo que ponen. Este módulo no es un lector. Registra
    **decisiones humanas** y promete conservarlas, y una promesa sobre el tiempo
    no se puede comprobar con una sola foto.

    Con dos exportaciones —antes y después de que alguien resuelva— se pueden
    comprobar tres cosas que de una en una son invisibles:

      · **Lo que ha cambiado.** Apareció una resolución, se desactivó un hecho.
      · **Lo que NO debía cambiar.** Los hechos originales y las contradicciones
        detectadas tienen que seguir diciendo lo mismo: la decisión se pone
        encima, no encima de la evidencia.
      · **Lo que se ha perdido.** Una decisión anterior que ya no está.

    Lo tercero es lo que su propio documento no resuelve: en §2.1 dice que la
    tabla de resoluciones es mutable y que hay como mucho una fila por
    contradicción; en §6 dice que «nada se sobrescribe». Las dos cosas no pueden
    ser ciertas a la vez, y con dos exportaciones delante no hay que discutirlo.

    Devuelve un diccionario; no juzga. Juzgar es de los casos.
    """
    def por_id(coleccion):
        return {c["id"]: c for c in coleccion if c.get("id") is not None}

    ha, hd = por_id(antes["hechos"]), por_id(despues["hechos"])
    ca, cd = por_id(antes["contradicciones"]), por_id(despues["contradicciones"])

    def resoluciones(datos):
        return {c["id"]: c.get("resolucion") for c in datos["contradicciones"]
                if c.get("resolucion")}

    ra, rd = resoluciones(antes), resoluciones(despues)

    def firma_hecho(h):
        return (h.get("campo"), h.get("valor"), h.get("documento"))

    def firma_contra(c):
        return (c.get("campo"), c.get("hecho_a"), c.get("hecho_b"),
                c.get("severidad"))

    def firma_resol(r):
        return (r.get("tipo"), r.get("valor"), r.get("revisor"))

    return {
        # Lo que cambia y debe poder cambiar
        "resoluciones_nuevas": sorted(set(rd) - set(ra)),
        "resoluciones_retiradas": sorted(set(ra) - set(rd)),
        "resoluciones_cambiadas": sorted(
            i for i in set(ra) & set(rd) if firma_resol(ra[i]) != firma_resol(rd[i])),
        "hechos_desactivados": sorted(i for i in set(ha) & set(hd)
                                      if ha[i]["activo"] and not hd[i]["activo"]),
        "hechos_reactivados": sorted(i for i in set(ha) & set(hd)
                                     if not ha[i]["activo"] and hd[i]["activo"]),
        # Lo que NO debería cambiar: la evidencia y lo detectado sobre ella
        "hechos_alterados": sorted(i for i in set(ha) & set(hd)
                                   if firma_hecho(ha[i]) != firma_hecho(hd[i])),
        "hechos_desaparecidos": sorted(set(ha) - set(hd)),
        "contradicciones_alteradas": sorted(
            i for i in set(ca) & set(cd) if firma_contra(ca[i]) != firma_contra(cd[i])),
        "contradicciones_desaparecidas": sorted(set(ca) - set(cd)),
        "contradicciones_nuevas": sorted(set(cd) - set(ca)),
        # El detalle de cada resolución que cambia, para poder contarlo
        "detalle_cambios": [
            {"contradiccion": i,
             "antes": {"revisor": ra[i].get("revisor"), "valor": ra[i].get("valor"),
                       "tipo": ra[i].get("tipo"), "momento": ra[i].get("momento")},
             "despues": {"revisor": rd[i].get("revisor"), "valor": rd[i].get("valor"),
                         "tipo": rd[i].get("tipo"), "momento": rd[i].get("momento")}}
            for i in sorted(set(ra) & set(rd))
            if firma_resol(ra[i]) != firma_resol(rd[i])],
    }


def evaluar(esperados, contexto, repeticion=None, modo_lectura="determinista",
            estado_previo=None):
    datos = contexto["datos"]
    reportadas = datos["contradicciones"]
    hechos = {h["id"]: h for h in datos["hechos"]}

    contraste = C.contrastar(esperados, reportadas,
                             clave=lambda x: (x["clave"] if "clave" in x
                                              else f"{datos['grupo']}::{x['campo']}"),
                             comparar=_comparar)
    casos, hallazgos = {}, []

    # 1 — la contradicción existe y es revisable            [acuerdo de conexión]
    faltan = [e["campo"] for e in contraste["omitidas"]]
    sobran = [r["campo"] for r in contraste["falsas"]]
    con_error = [m["motivo"] for m in contraste["motivos"]]
    sin_documento = [r["campo"] for r in reportadas
                     if not (hechos.get(r["hecho_a"], {}).get("documento")
                             and hechos.get(r["hecho_b"], {}).get("documento"))]
    casos[1] = B.caso(
        bool(esperados) and not faltan and not sobran and not con_error
        and not sin_documento,
        (f"El evaluador deriva {len(esperados)} contradicción(es) de los "
         f"{contexto['hechos_en_juego']} hechos en juego y el módulo emite "
         f"{len(reportadas)}. "
         + (f"Cada una cita los dos hechos en conflicto, con su campo, sus dos "
            f"valores y el documento de procedencia de cada uno."
            if not (faltan or sobran or con_error or sin_documento) else
            (f"No detecta: {', '.join(faltan)}. " if faltan else "")
            + (f"Emite sin respaldo en los hechos: {', '.join(sobran)}. " if sobran else "")
            + ("; ".join(con_error) + ". " if con_error else "")
            + (f"Sin documento de procedencia: {', '.join(sin_documento)}."
               if sin_documento else "")))
        if esperados else
        "Los hechos activos no contienen ningún conflicto que detectar.",
        no_aplica=not esperados,
        requiere=("una exportación cuyos documentos discrepen en algún campo"
                  if not esperados else None))

    # 2 — no inventa contradicciones donde no las hay       [acuerdo de conexión]
    coincidentes = contexto["campos_coincidentes"]
    falsas_en_coincidentes = [r["campo"] for r in contraste["falsas"]
                              if any(c["campo"] == r["campo"] for c in coincidentes)]
    casos[2] = B.caso(
        bool(coincidentes) and not falsas_en_coincidentes,
        (f"{len(coincidentes)} campo(s) con varios documentos que coinciden "
         f"({', '.join(c['campo'] for c in coincidentes)}) y el módulo no levanta "
         f"contradicción en ninguno."
         if coincidentes and not falsas_en_coincidentes else
         f"Levanta contradicción en campos donde los documentos coinciden: "
         f"{', '.join(falsas_en_coincidentes)}."
         if falsas_en_coincidentes else
         "Este pedido no tiene ningún campo en el que dos documentos coincidan: "
         "todos los campos con más de un hecho están en conflicto."),
        no_aplica=not coincidentes,
        requiere=("una exportación con algún campo en el que dos documentos digan "
                  "lo mismo — sirve el mismo pedido si tiene más campos extraídos"
                  if not coincidentes else None))

    # 3 — literalidad de la evidencia                       [acuerdo de conexión]
    # Sin los PDF no se puede confirmar que el fragmento sea literal, pero sí se
    # puede refutar: si el fragmento no contiene el valor que dice sostener, no es
    # literal y no hacen falta los documentos para saberlo. Prueba negativa
    # concluyente, prueba positiva no: por eso pasa a pendiente en vez de a
    # superado.
    implicados = [h for h in datos["hechos"]
                  if any(h["id"] in (r["hecho_a"], r["hecho_b"]) for r in reportadas)]
    sin_evidencia = [h["documento"] for h in implicados if not h["evidencia"]]
    incoherentes = [f"{h['documento']}: el fragmento no contiene «{h['valor']}»"
                    for h in implicados
                    if h["evidencia"] and plano(str(h["valor"] or "")) not in
                    plano(h["evidencia"])]
    coherentes = len(implicados) - len(sin_evidencia) - len(incoherentes)
    roto = bool(sin_evidencia or incoherentes)
    casos[3] = B.caso(
        not roto,
        ((f"Sin evidencia: {', '.join(sin_evidencia)}. " if sin_evidencia else "")
         + ("; ".join(incoherentes) + "." if incoherentes else ""))
        if roto else
        (f"Los {coherentes} fragmentos aportados contienen la etiqueta y el valor "
         f"que dicen sostener, así que son coherentes. La literalidad frente al "
         f"documento original no se puede confirmar sin los PDF: la comprobación "
         f"negativa es concluyente, la positiva no."),
        omitir=not roto and bool(implicados),
        no_aplica=not implicados,
        requiere=("los dos PDF del pedido para contrastar cada fragmento contra su "
                  "original" if implicados else
                  "una exportación con contradicciones que citen evidencia"))

    # 4 — declaración del método                            [acuerdo de conexión]
    sin_metodo = [r["campo"] for r in reportadas if not r["metodo"]]
    familias = sorted({familia_metodo(r["metodo"]) for r in reportadas})
    sin_clasificar = [r["metodo"] for r in reportadas
                      if familia_metodo(r["metodo"]) == "sin clasificar"]
    casos[4] = B.caso(
        bool(reportadas) and not sin_metodo and not sin_clasificar,
        (f"{'La contradicción declara' if len(reportadas) == 1 else f'Las {len(reportadas)} contradicciones declaran'} método "
         f"({', '.join(sorted({r['metodo'] for r in reportadas}))}), reconocible "
         f"como {' y '.join(familias)}."
         if not (sin_metodo or sin_clasificar) else
         (f"Sin método declarado: {', '.join(sin_metodo)}. " if sin_metodo else "")
         + (f"Método no reconocible como regla ni como IA: "
            f"{', '.join(sin_clasificar)}." if sin_clasificar else ""))
        if reportadas else "El módulo no emite contradicciones que declarar.",
        no_aplica=not reportadas,
        requiere="una exportación con al menos una contradicción" if not reportadas else None)

    # 5 — rastro de la revisión humana                      [acuerdo de conexión]
    resueltas = [r for r in reportadas if r.get("resolucion")]
    incompletas = []
    for r in resueltas:
        res = r["resolucion"]
        faltan_datos = [n for n, v in (("estado", res["tipo"]),
                                       ("revisor", res["revisor"]),
                                       ("momento", res["momento"])) if not v]
        if faltan_datos:
            incompletas.append(f"{r['campo']}: falta {', '.join(faltan_datos)}")
    casos[5] = B.caso(
        bool(resueltas) and not incompletas,
        (f"{len(resueltas)} de {len(reportadas)} contradicción(es) llevan revisión "
         f"registrada, con estado, revisor y marca temporal asociados a la "
         f"contradicción concreta: "
         + "; ".join(f"«{r['campo']}» → {r['resolucion']['tipo']} por "
                     f"{r['resolucion']['revisor']} el {r['resolucion']['momento']}"
                     for r in resueltas[:3]) + "."
         if not incompletas else "; ".join(incompletas) + ".")
        if resueltas else
        "Ninguna contradicción de esta exportación ha pasado por revisión humana.",
        no_aplica=not resueltas,
        requiere=("una exportación con al menos una contradicción ya resuelta"
                  if not resueltas else None))

    # 6 — consulta posterior: valor confirmado y procedencia [acuerdo de conexión]
    # Comprobación independiente de verdad: la resolución dice qué lado valida, y
    # ese lado tiene un valor propio. Si no coinciden, la validación apunta a un
    # sitio y afirma otro, y no hay forma de saber cuál vale.
    descuadres, trazadas = [], []
    for r in resueltas:
        res = r["resolucion"]
        lado = RESOLUCIONES.get((res["tipo"] or "").lower())
        hid = r["hecho_a"] if lado == "a" else r["hecho_b"] if lado == "b" else None
        h = hechos.get(hid)
        if h is None:
            descuadres.append(f"«{r['campo']}»: la resolución «{res['tipo']}» no "
                              f"identifica cuál de los dos hechos valida")
        elif not _mismo(h["valor"], res["valor"]):
            descuadres.append(f"«{r['campo']}»: valida el hecho de {h['documento']} "
                              f"({h['valor']}) pero registra {res['valor']}")
        else:
            trazadas.append(f"«{r['campo']}» → {res['valor']}, procedente de "
                            f"{h['documento']}")
    casos[6] = B.caso(
        bool(resueltas) and not descuadres,
        ("Tras la validación, el valor confirmado se consulta con su procedencia: "
         + "; ".join(trazadas) + "."
         if not descuadres else "; ".join(descuadres) + ".")
        if resueltas else
        "Sin revisiones registradas no hay valor confirmado que consultar.",
        no_aplica=not resueltas,
        requiere=("una exportación con al menos una contradicción ya resuelta"
                  if not resueltas else None))

    # 7 — el valor descartado, marcado como descartado      [acuerdo de conexión]
    perdedores_activos = []
    for r in resueltas:
        lado = RESOLUCIONES.get((r["resolucion"]["tipo"] or "").lower())
        hid = r["hecho_b"] if lado == "a" else r["hecho_a"] if lado == "b" else None
        h = hechos.get(hid)
        if h is not None and h["activo"]:
            perdedores_activos.append(h)
    casos[7] = B.caso(
        bool(resueltas) and not perdedores_activos,
        (f"El valor descartado se conserva y queda distinguible del vigente."
         if not perdedores_activos else
         f"El valor descartado se conserva, pero sigue marcado como activo: "
         + "; ".join(f"{h['documento']} → {h['valor']} (is_active = 1, igual que el "
                     f"valor validado)" for h in perdedores_activos)
         + f". Quien consulte los hechos activos del pedido recupera "
           f"{contexto['hechos_activos']} valores para el mismo campo sin saber "
           f"cuál se validó, salvo que atraviese las tablas de contradicciones y "
           f"resoluciones.")
        if resueltas else
        "Sin revisiones registradas no hay valor descartado que conservar.",
        no_aplica=not resueltas,
        requiere=("una exportación con al menos una contradicción ya resuelta"
                  if not resueltas else None))

    # 8 — documento no agrupable                            [acuerdo de conexión]
    huerfanos = [h["documento"] for h in datos["hechos"] if not h["grupo"]]
    casos[8] = B.caso(
        not huerfanos,
        (f"Todos los hechos ({contexto['hechos_totales']}) pertenecen al grupo "
         f"{datos['grupo']}, agrupado por {datos['metodo_agrupacion']} con "
         f"confianza declarada «{datos['confianza_agrupacion']}». Esta exportación "
         f"no contiene ningún documento que el módulo no haya sabido agrupar, así "
         f"que el aviso no se puede ejercitar."),
        no_aplica=True,
        requiere=("una exportación que incluya un documento cuyo nombre no permita "
                  "deducir el pedido — la agrupación es por patrón de nombre de "
                  "fichero, así que basta con renombrar uno"))

    # 9 — ausencia frente a imposibilidad              [criterio del evaluador]
    casos[9] = B.caso(
        False,
        "Esta exportación contiene contradicciones y todos sus documentos se han "
        "leído, así que no se puede ver qué emite el módulo cuando no encuentra "
        "nada y cuando no ha podido mirar. Son dos salidas que no deben parecerse: "
        "un pedido con un PDF ilegible llegaría a validación humana como pedido "
        "correcto.",
        no_aplica=True,
        requiere=("dos exportaciones más: una de un pedido sin contradicciones y "
                  "otra de un pedido con un documento ilegible o ausente, para "
                  "comprobar que se distinguen"))

    # 10 — repetibilidad                                [criterio del evaluador]
    if repeticion is None:
        casos[10] = B.caso(
            False,
            "No se ha aportado una segunda exportación del mismo pedido.",
            omitir=True,
            requiere=("una segunda exportación del PED1004 sin cambiar nada. El "
                      "módulo ya emite `fingerprint` en cada contradicción, así que "
                      "basta con comparar huellas"))
    else:
        antes = {(c["campo"], c["severidad"], c["huella"]) for c in reportadas}
        ahora = {(c["campo"], c["severidad"], c["huella"])
                 for c in repeticion["contradicciones"]}
        casos[10] = B.caso(
            antes == ahora,
            (f"Dos ejecuciones sobre el mismo pedido devuelven las mismas "
             f"{len(antes)} contradicción(es), con la misma severidad y la misma "
             f"huella."
             if antes == ahora else
             f"Difieren entre ejecuciones: {sorted(antes ^ ahora)}."))

    # 11 — ¿validó quien tenía autoridad?     [cruce con la ontología de Pablo]
    #
    # El primer caso del sistema que no se puede comprobar mirando un solo
    # módulo. Mencía emite quién validó y de qué categoría era la contradicción;
    # Pablo declara quién manda sobre cada área. Ninguno de los dos puede
    # contestar solo, y el evaluador tiene los dos delante.
    from nucleo import autoridad as AUT
    onto = AUT.cargar()
    if not resueltas:
        casos[11] = B.caso(
            False, "Ninguna contradicción de esta exportación está resuelta, así "
                   "que no hay ninguna validación cuya autoridad comprobar.",
            omitir=True,
            requiere="una exportación con al menos una contradicción resuelta")
    elif not onto:
        casos[11] = B.caso(
            False, "No hay organigrama de autoridad cargado.", omitir=True,
            requiere=("la matriz de autoridad de Pablo en "
                      "`referencia/ontologia_autoridad.json`"))
    else:
        veredictos = []
        for r in resueltas:
            cat = r.get("categoria")
            quien = (r["resolucion"] or {}).get("revisor")
            v, motivo = AUT.tiene_autoridad(quien, cat, onto)
            veredictos.append({"campo": r["campo"], "revisor": quien,
                               "categoria": cat, "podia": v, "motivo": motivo})
        sin_autoridad = [v for v in veredictos if v["podia"] is False]
        no_comprobables = [v for v in veredictos if v["podia"] is None]
        confirmada = AUT.confirmada(onto)

        detalle = "; ".join(
            f"{v['campo']}: {v['revisor']} sobre «{v['categoria']}» — {v['motivo']}"
            for v in veredictos)

        categorias_ok = AUT.categorias_confirmadas()

        if not sin_autoridad and not no_comprobables:
            # Todas las validaciones las hizo quien podía. Si alguna de las dos
            # piezas del cruce sigue sin firmar, el caso pasa pero lo declara: un
            # aprobado que se apoya en un mapa sin firmar es un aprobado con
            # asterisco, y el asterisco se escribe.
            asterisco = ""
            if not confirmada:
                asterisco = (" (El organigrama lo ha extraído el evaluador de una "
                             "lámina y está pendiente de que Pablo lo confirme.)")
            elif not categorias_ok:
                asterisco = (" (El organigrama es de Pablo, pero la correspondencia "
                             "entre las categorías de Mencía y sus áreas la ha "
                             "supuesto el evaluador.)")
            casos[11] = B.caso(
                True,
                f"Las {len(veredictos)} validación(es) las hizo quien manda sobre "
                f"su área. {detalle}" + asterisco)
        elif no_comprobables and not sin_autoridad:
            casos[11] = B.caso(
                False,
                f"No se puede comprobar la autoridad de "
                f"{len(no_comprobables)} de {len(veredictos)} validación(es). "
                f"{detalle}",
                omitir=True,
                requiere=("que la exportación identifique el rol de quien resuelve "
                          "—`resolved_by_role_id` existe y viene a nulo— o que el "
                          "organigrama cubra los roles que aparecen"))
        elif not confirmada:
            # No se puede fallar a nadie con un mapa que su autor no ha firmado.
            casos[11] = B.caso(
                False,
                f"{len(sin_autoridad)} de {len(veredictos)} validación(es) las "
                f"hizo alguien que, según el organigrama, no manda sobre esa "
                f"área. {detalle}. **No se cuenta como fallo**: el organigrama lo "
                f"ha extraído el evaluador de una lámina y Pablo todavía no lo ha "
                f"confirmado, así que el desacuerdo puede estar en mi lectura.",
                omitir=True,
                requiere=("que Pablo confirme la matriz de autoridad; hasta "
                          "entonces el cruce se declara pero no puntúa"))
        elif not categorias_ok:
            # El organigrama sí lo firma Pablo. Lo que no firma nadie es de qué
            # área es cada categoría, y el veredicto depende entero de eso: con
            # `cantidad_pedida` en Producción sale un culpable y en Comercial sale
            # otro. Se declara el desacuerdo y no se le cuenta a Mencía.
            casos[11] = B.caso(
                False,
                f"{len(sin_autoridad)} de {len(veredictos)} validación(es) las "
                f"hizo alguien que, según el organigrama de Pablo, no manda sobre "
                f"esa área. {detalle}. **No se cuenta como fallo**: la matriz es "
                f"suya y responde de ella, pero el paso intermedio —de qué área es "
                f"cada categoría— lo he supuesto yo, y el veredicto depende entero "
                f"de ese paso.",
                omitir=True,
                requiere=("el mapa campo/categoría → ámbito, escrito por Pablo. "
                          "Sin él el cruce se declara pero no puntúa"))
        else:
            casos[11] = B.caso(
                False,
                f"{len(sin_autoridad)} de {len(veredictos)} validación(es) las "
                f"cerró alguien sin autoridad sobre esa área. {detalle}")

    # 12 y 13 — sólo se pueden ver con dos exportaciones del mismo pedido
    if estado_previo is None:
        pendiente = B.caso(
            False,
            "Sólo se ha aportado una exportación. Este módulo registra decisiones "
            "humanas y promete conservarlas, y una promesa sobre el tiempo no se "
            "comprueba con una sola foto: hacen falta dos, antes y después de que "
            "alguien resuelva.",
            omitir=True,
            requiere=("una exportación del mismo pedido tomada ANTES de resolver "
                      "la contradicción, y otra tomada DESPUÉS"))
        casos[12] = pendiente
        casos[13] = dict(pendiente)
    else:
        cambios = comparar_estados(estado_previo, datos)

        perdidas = cambios["resoluciones_retiradas"]
        revocadas = cambios["detalle_cambios"]
        casos[12] = B.caso(
            not perdidas and not revocadas,
            ("Entre las dos exportaciones no se ha perdido ninguna decisión "
             "anterior." if not perdidas and not revocadas else
             (f"Desaparecen las resoluciones de {perdidas}. " if perdidas else "")
             + "".join(
                 f"La decisión de «{c['antes']['revisor']}» ({c['antes']['valor']}) "
                 f"la sustituye la de «{c['despues']['revisor']}» "
                 f"({c['despues']['valor']}) y la primera ya no aparece en la "
                 f"exportación: quien audite esto después no sabrá que hubo una "
                 f"decisión previa ni de quién. "
                 for c in revocadas)))

        tocados = (cambios["hechos_alterados"] + cambios["hechos_desaparecidos"]
                   + cambios["contradicciones_alteradas"]
                   + cambios["contradicciones_desaparecidas"])
        casos[13] = B.caso(
            not tocados,
            ("Resolver no ha tocado la evidencia: los mismos hechos con los mismos "
             "valores y las mismas contradicciones detectadas, antes y después."
             if not tocados else
             f"Al resolver cambia la evidencia. Hechos alterados: "
             f"{cambios['hechos_alterados']}; hechos que desaparecen: "
             f"{cambios['hechos_desaparecidos']}; contradicciones alteradas: "
             f"{cambios['contradicciones_alteradas']}; contradicciones que "
             f"desaparecen: {cambios['contradicciones_desaparecidas']}. La "
             f"decisión se pone encima de la evidencia, no en su lugar."))

    # --- hallazgos de cobertura -------------------------------------------
    if resueltas and all(r["resolucion"].get("revisor_rol_id") is None
                         for r in resueltas):
        hallazgos.append(B.hallazgo(
            "La identidad del revisor es texto libre, no una referencia",
            "Las resoluciones registran el revisor como cadena de texto "
            "(«" + "», «".join(sorted({r["resolucion"]["revisor"] for r in resueltas
                                       if r["resolucion"]["revisor"]})) + "») y "
            "dejan `resolved_by_role_id` a nulo, que es el campo previsto para "
            "identificarlo.",
            "El rastro identifica un cargo, no a una persona. Dos personas que "
            "ocupen el puesto en momentos distintos quedan indistinguibles, y una "
            "cadena de texto no se puede cruzar con el directorio de la empresa: "
            "es exactamente el eslabón que una auditoría pediría cerrar.",
            [{"Contradicción": r["campo"], "Revisor registrado": r["resolucion"]["revisor"],
              "Referencia de rol": "nula"} for r in resueltas]))

    familias_vistas = {familia_metodo(r["metodo"]) for r in reportadas}
    if reportadas and "ia" not in familias_vistas:
        hallazgos.append(B.hallazgo(
            "Sólo se ha ejercitado la vía determinista de detección",
            (f"La única contradicción de esta exportación se ha detectado"
             if len(reportadas) == 1 else
             f"Las {len(reportadas)} contradicciones de esta exportación se han "
             f"detectado")
            + " por regla determinista. La taxonomía de métodos existe y se "
              "declara, pero la rama de detección por IA no aparece en estos datos.",
            "El caso 4 comprueba que el método se declara, no que las dos familias "
            "se distingan de verdad. Mientras no llegue una contradicción detectada "
            "por IA, la mitad de esa taxonomía está sin verificar."))

    if datos["metodo_agrupacion"] == "filename_pattern":
        hallazgos.append(B.hallazgo(
            "La agrupación depende del nombre del fichero",
            f"El grupo {datos['grupo']} se ha formado por patrón de nombre de "
            f"fichero, con confianza declarada «{datos['confianza_agrupacion']}». "
            f"La exportación no tiene ningún sitio donde aparecería un documento "
            f"que no se hubiera podido agrupar.",
            "Renombrar un PDF al subirlo saca ese documento del pedido sin que nada "
            "lo advierta, y sus contradicciones dejan de existir en silencio. Es el "
            "caso 8, y hoy no se puede ejercitar porque la exportación no contempla "
            "la situación."))

    # --- Desglose esperado / observado para la plantilla común -------------
    # No decide nada: los trece casos ya están resueltos. Sólo separa en dos
    # columnas lo que la observación contaba fundido en un párrafo.
    def _l(xs, vacio="ninguno"):
        xs = [str(x) for x in xs if x]
        return ", ".join(xs) if xs else vacio

    NADA = "— el conjunto no contiene esta situación —"
    FALTA = "— no aportado en esta ejecución —"

    _res = [r for r in reportadas if r.get("resolucion")]
    _campos_coin = [c["campo"] for c in contexto["campos_coincidentes"]]
    _implicados = [h for h in datos["hechos"]
                   if any(h["id"] in (r["hecho_a"], r["hecho_b"]) for r in reportadas)]
    _perdedores = []
    for r in _res:
        lado = RESOLUCIONES.get((r["resolucion"]["tipo"] or "").lower())
        hid = r["hecho_b"] if lado == "a" else r["hecho_a"] if lado == "b" else None
        if hechos.get(hid):
            _perdedores.append(hechos[hid])

    _d = {
        1: (_l([f"{e['campo']}: {e['valores'][0]} vs {e['valores'][1]}"
                for e in esperados]) if esperados else "ninguna contradicción",
            _l([f"{r['campo']}: hechos {r['hecho_a']} y {r['hecho_b']}"
                for r in reportadas])),
        2: (("sin contradicción en: " + _l(_campos_coin)) if _campos_coin
            else "ningún campo con documentos coincidentes",
            _l([r["campo"] for r in reportadas if r["campo"] in _campos_coin],
               "ninguna levantada ahí") if _campos_coin else NADA),
        3: ("cada evidencia contiene la etiqueta y el valor que sostiene",
            f"{len(_implicados)} fragmento(s) aportado(s), "
            f"{sum(1 for h in _implicados if h['evidencia'])} con texto citado"
            if _implicados else NADA),
        4: ("método declarado en cada contradicción",
            _l(sorted({f"{r['campo']}: {r['metodo'] or 'sin declarar'}"
                       for r in reportadas})) if reportadas else NADA),
        5: ("estado, revisor y momento en cada revisión",
            _l([f"{r['campo']}: {r['resolucion']['tipo']} por "
                f"{r['resolucion']['revisor']} el {r['resolucion']['momento']}"
                for r in _res]) if _res else NADA),
        6: (_l([f"{r['campo']}: el valor del hecho que valida" for r in _res])
            if _res else "ninguna revisión registrada",
            _l([f"{r['campo']}: {r['resolucion']['valor']}" for r in _res])
            if _res else NADA),
        7: (_l([f"{h['documento']} ({h['valor']}) marcado como descartado"
                for h in _perdedores]) if _perdedores
            else "ninguna revisión registrada",
            _l([f"{h['documento']}: is_active = {1 if h['activo'] else 0}"
                for h in _perdedores]) if _perdedores else NADA),
        8: ("aviso por cada documento no agrupable",
            f"{contexto['hechos_totales']} hecho(s), todos en el grupo "
            f"{datos['grupo']}; la exportación no contempla documentos sin agrupar"),
        9: ("salida vacía por ausencia distinguible de salida vacía por ilegible",
            NADA),
        10: ("las mismas contradicciones, severidad y huella en dos ejecuciones",
             ("coinciden" if casos[10]["resultado"] == "pasa" else "difieren")
             if repeticion is not None else FALTA),
        11: ("cada validación, hecha por quien manda sobre su categoría",
             _l([f"{r['campo']} ({r.get('categoria') or 'sin categoría'}): "
                 f"{r['resolucion']['revisor']}" for r in _res]) if _res else NADA),
        12: ("ninguna decisión anterior desaparece al tomarse la siguiente",
             FALTA if estado_previo is None else
             ("ninguna se pierde" if casos[12]["resultado"] == "pasa"
              else "se pierde al menos una")),
        13: ("los mismos hechos y las mismas contradicciones antes y después",
             FALTA if estado_previo is None else
             ("la evidencia no se mueve" if casos[13]["resultado"] == "pasa"
              else "la evidencia cambia al resolver")),
    }
    for _n, (_esp, _obs) in _d.items():
        if _n in casos:
            casos[_n]["esperado"], casos[_n]["observado"] = _esp, _obs

    return {"casos": casos, "contraste": contraste, "hallazgos": hallazgos,
            "tabla_contraste": [a_fila(e, hechos, reportadas) for e in esperados],
            "modo_lectura": modo_lectura}


def a_fila(esperado, hechos, reportadas):
    reportada = next((r for r in reportadas if r["campo"] == esperado["campo"]), None)
    return {
        "Campo": esperado["campo"],
        "Valor A": f"{esperado['valores'][0]} ({esperado['documentos'][0]})",
        "Valor B": f"{esperado['valores'][1]} ({esperado['documentos'][1]})",
        "Derivada por el evaluador": "sí",
        "Emitida por el módulo": "sí" if reportada else "no",
        "Severidad": reportada["severidad"] if reportada else "—",
        "Método": reportada["metodo"] if reportada else "—",
        "Revisada": ("sí" if reportada and reportada.get("resolucion") else "no"),
    }


def sujeto(contexto):
    d = contexto["datos"]
    return (f"el pedido {d['grupo']} — {len(d['documentos'])} documento(s), "
            f"{contexto['hechos_totales']} hecho(s) extraído(s)")
