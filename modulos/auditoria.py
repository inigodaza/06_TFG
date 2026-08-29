"""
Rama de evaluación del módulo de AUDITORÍA DE PEDIDOS — Juan Salas · GraphyCems.
Conexión C8 · Juan → Evaluación y Calidad. Es la primera conexión probada.

Qué hace el módulo evaluado: compara la orden de fabricación contra la
documentación de cliente y emite las incongruencias que encuentra.

Qué hace esta rama: lee los mismos PDF, calcula por su cuenta qué discrepancias
existen realmente, y contrasta la salida del módulo contra ese cálculo. La
unidad evaluada es el campo discrepante.

Migrado del `evaluador.py` de la primera versión. Cambios respecto a ella:
  · el contraste, la batería y el veredicto salen del núcleo, no se repiten aquí
  · `valores_correctos()` estaba definida dos veces; queda una
  · la comparación de valores usa `texto.mismo_valor()`, que distingue el 0 de la
    ausencia de valor y compara texto cuando el campo no es numérico
"""

import re

from nucleo import bateria as B
from nucleo import contraste as C
from nucleo import jueces as J
from nucleo import llm
from nucleo.texto import formato_normal, mismo_valor, numero, plano

# ===========================================================================
# Ficha de la rama
# ===========================================================================

# Severidad esperada cuando el campo difiere. "menor" recoge las diferencias con
# explicación industrial plausible: el gramaje de cartulina se redondea al
# formato comercial disponible, luego 240 frente a 250 no es necesariamente un error.
CAMPOS = {
    "cantidad":         ("Cantidad", "alta"),
    "paginas":          ("Páginas", "alta"),
    "isbn":             ("ISBN", "alta"),
    "formato":          ("Formato", "alta"),
    "gramaje_interior": ("Gramaje de interior", "menor"),
    "gramaje_cubierta": ("Gramaje de cubierta", "menor"),
}
ETIQUETAS = {k: v[0] for k, v in CAMPOS.items()}

CASOS = {
    1: "Detección de discrepancias de severidad alta",
    2: "Graduación de la severidad",
    3: "Ausencia de incidencias sin respaldo documental",
    4: "Completitud del recuento declarado",
    5: "Trazabilidad de la evidencia",
    6: "Dirección de la corrección",
    7: "Repetibilidad del veredicto",
    8: "Cobertura de campos del módulo",
    9: "Distinción entre ausencia de incidencias e imposibilidad de comprobar",
}

ASPECTOS = {
    1: ("Hay discrepancias existentes que no se detectan correctamente",
        "Revisar la extracción de los campos afectados: el evaluador los localiza en "
        "ambos documentos, luego la información estaba disponible."),
    2: ("La severidad asignada no corresponde a la esperada",
        "Fijar la clasificación de severidad por regla explícita en lugar de "
        "delegarla al modelo generativo."),
    3: ("Se emiten incidencias sin respaldo documental o con valores erróneos",
        "Exigir que toda incidencia cite los dos valores en conflicto tal como "
        "figuran en los documentos, y verificar la cita antes de emitirla."),
    4: ("El recuento declarado no coincide con las incidencias emitidas",
        "Derivar el recuento de la lista de incidencias en lugar de calcularlo "
        "por separado."),
    5: ("Hay incidencias que no citan sus documentos de origen",
        "Hacer obligatoria la referencia a ambos documentos en cada incidencia: sin "
        "ella, la validación humana recibe una afirmación que no puede verificar."),
    6: ("La dirección de la corrección no es la esperada",
        "Declarar explícitamente que el documento de cliente es la fuente de verdad "
        "y la orden de fabricación el documento a corregir."),
    7: ("El determinismo del veredicto no está demostrado",
        "Ejecutar la auditoría dos veces sobre el mismo pedido sin modificar los "
        "documentos y comparar campos y severidad, no la redacción."),
    8: ("La cobertura de campos del módulo no está acotada",
        "Auditar un pedido con una discrepancia introducida en un campo distinto de "
        "cantidad y gramaje, y declarar qué campos entran en la comparación."),
    9: ("No consta distinción entre ausencia de incidencias e imposibilidad de comprobar",
        "Diferenciar ambas situaciones en la salida: una salida vacía por documento "
        "ilegible llegaría a validación humana como señal de pedido correcto."),
}

# Alcance de cada caso. Casi todos se juzgan sobre los datos de la ejecución que
# se está evaluando. El 9 no: es una propiedad del módulo —o distingue las dos
# situaciones o no las distingue— y se comprueba una vez, con evidencia aportada
# aparte, no deduciéndola de la respuesta pegada.
ALCANCE = {n: "ejecucion" for n in CASOS}
ALCANCE[9] = "modulo"

# Severidad por consecuencia aguas abajo, declarada antes de ejecutar. En este
# módulo el destinatario es producción: lo crítico es lo que llega a máquina sin
# que nadie lo haya visto.
SEVERIDAD = {
    1: "critica",   # una discrepancia real no detectada se fabrica tal cual
    2: "alta",      # si la severidad no discrimina, hay que revisarlo todo a mano
    3: "critica",   # afirmar que no hay incidencias sin haber comprobado
    4: "media",     # el recuento descuadra pero las incidencias están
    5: "alta",      # sin trazabilidad hay que volver a los PDF para corregir
    6: "alta",      # corregir en la dirección equivocada propaga el error
    7: "alta",      # sin repetibilidad ninguna medición anterior se sostiene
    8: "media",     # campos fuera de cobertura: se sabe que no se miran
    9: "critica",   # un pedido sin auditar leído como pedido conforme
}

# Evidencia que no sale de la salida pegada y que el evaluador aporta y declara.
# Cuando un caso se juzga así, el veredicto dice de dónde viene el juicio: si no,
# el resultado no sería verificable por nadie más.
EVIDENCIAS = {
    9: {
        "pregunta": ("¿El módulo distingue un pedido sin incidencias de un pedido "
                     "que no ha podido auditarse?"),
        "como_comprobarlo": ("Abrir el tablero de GraphyFlow y mirar los filtros de "
                             "estado de auditoría."),
        "constatado": True,
        "origen": ("Tablero de GraphyFlow: fila de filtros de estado. Confirmado por "
                   "Juan el 19/08/2026, con el pedido que subió a la carpeta de "
                   "auditoría del Drive."),
        "nota": ("El tablero expone cinco estados filtrables: auditados OK, con "
                 "incongruencias, sin auditar, sin orden de fabricación y sin "
                 "documento de origen. Los dos últimos separan la imposibilidad de "
                 "comprobar de la ausencia de incidencias, que es exactamente lo "
                 "que el caso exige."),
    },
}


# ---------------------------------------------------------------------------
# Criterios cualitativos: diseñados, no ejecutables aquí
# ---------------------------------------------------------------------------
# Están escritos y se enseñan, pero el panel no puede ejecutarse en esta rama: los
# jueces tendrían que leer la salida, y la salida cita documentación real de un
# cliente de GraphyCems. Es la misma disciplina que el resto del sistema —lo
# diseñado no se cuenta como ejecutado— aplicada a un límite que no es técnico
# sino de datos. Enseñar el criterio cerrado dice más que ocultarlo: dice qué se
# podría medir y por qué hoy no se mide.

CUALITATIVOS = [
    J.criterio(
        "ausencia_vs_imposibilidad",
        "Distingue no haber encontrado nada de no haber podido mirar",
        "Cuando el módulo no reporta incongruencias, ¿queda claro si es porque ha "
        "comprobado y no las hay, o porque no ha podido comprobar —falta la orden, "
        "falta el documento de origen, el PDF venía escaneado—?",
        "Es el punto que Juan resolvió en el tablero pero que no viaja en la "
        "salida. Un pedido sin auditar leído como pedido conforme es un fallo que "
        "no deja rastro."),
    J.criterio(
        "severidad",
        "La severidad asignada es proporcionada",
        "¿La severidad que el módulo asigna a cada incongruencia guarda proporción "
        "con su consecuencia real en fabricación, o trata igual una diferencia "
        "trivial y una que obliga a parar la tirada?",
        "Una severidad que no discrimina obliga a revisarlo todo a mano, y "
        "entonces el módulo no ha ahorrado nada."),
    J.criterio(
        "accionable",
        "La incongruencia se puede corregir con lo que dice",
        "¿Indica el campo concreto, el valor de cada fuente y dónde está el "
        "desacuerdo, de forma que se pueda corregir sin volver a los PDF?",
        "El destinatario de esta salida trabaja con el pedido delante y sin tiempo. "
        "Una incongruencia enunciada en abstracto se traduce en abrir los PDF."),
]


def evidencia_panel(respuesta_cruda, limite=6000):
    """Existe por simetría con el resto de ramas; hoy no se llama: el panel está vetado."""
    texto = (respuesta_cruda or "").strip()
    return (texto[:limite] if texto else "(el módulo no ha emitido salida)")


FICHA = {
    "id": "auditoria",
    "nombre": "Auditoría de pedidos",
    "responsable": "Juan Salas",
    "empresa": "GraphyCems",
    "conexion": "C8 · Juan → Evaluación y Calidad",
    "estado_conexion": "probada",
    "funcion": ("Compara la orden de fabricación contra los documentos de "
                "cliente del pedido y emite las incongruencias que encuentra."),
    "verifica": "Íñigo Daza",
    "operativo": True,
    # Los PDF del 42805 son documentación real de un cliente de GraphyCems:
    # editorial, ISBN, tirada y precios. El nivel gratuito de Gemini entrena con
    # lo que se le manda, y esa no es una decisión que me corresponda tomar a mí.
    "ia_permitida": False,
    "motivo_ia": ("Los documentos de este módulo son datos reales de un cliente de "
                  "GraphyCems. El nivel gratuito del proveedor usa el contenido para "
                  "mejorar sus modelos, así que el modo IA queda cerrado aquí hasta "
                  "que haya nivel de pago —que no entrena— y el visto bueno de Juan."),
    "panel_permitido": False,
    "motivo_panel": ("Los jueces tendrían que leer la salida del módulo, y esa "
                     "salida cita editorial, ISBN, tirada y precios de un cliente "
                     "real. Los tres criterios quedan diseñados y sin ejecutar: "
                     "no se cuentan como superados ni como fallidos."),
    "cualitativos": CUALITATIVOS,
    "unidad": ("campo", "las discrepancias"),
    "entrada": "La orden de fabricación y la documentación de cliente del pedido, en PDF.",
    "entrada_respuesta": ("Pega la respuesta tal como aparece en la interfaz de "
                          "GraphyCems, con sus encabezados de severidad."),
    "casos": CASOS,
    "aspectos": ASPECTOS,
    "alcance": ALCANCE,
    "severidad": SEVERIDAD,
    "evidencias": EVIDENCIAS,
    "esquema_campos": {
        "type": "object",
        "properties": {k: {"type": ["string", "integer", "null"]} for k in CAMPOS},
    },
    "esquema_salida": {
        "type": "array",
        "items": {"type": "object", "properties": {
            "campo": {"enum": list(CAMPOS)},
            "valor_cliente": {"type": ["string", "null"]},
            "valor_orden": {"type": ["string", "null"]},
            "severidad": {"enum": ["alta", "menor"]},
            "cita_documentos": {"type": "boolean"},
            "corregir": {"enum": ["orden", "cliente", None]},
        }, "required": ["campo"]},
    },
    "prompt_extraccion": (
        "Extrae de este documento de imprenta los campos del esquema. Devuelve el "
        "valor tal como figura, sin convertir unidades ni redondear. Si un campo no "
        "aparece, devuelve null: no lo deduzcas de otro."
    ),
    "prompt_interpretacion": (
        "Convierte la respuesta de un módulo de auditoría de pedidos en la lista JSON "
        "del esquema. No juzgues si la incidencia es correcta: sólo traduces lo que "
        "el módulo dice, incluidos los valores que cita aunque sean erróneos."
    ),
}

COLUMNAS = [
    ("campo", "Campo", "opcion", list(ETIQUETAS.values())),
    ("valor_cliente", "Valor según cliente", "texto", None),
    ("valor_orden", "Valor según orden", "texto", None),
    ("severidad", "Severidad", "opcion", ["Alta", "Menor"]),
    ("cita_documentos", "Cita ambos documentos", "bool", None),
    ("corregir", "Documento a corregir", "opcion",
     ["Orden de fabricación", "Pedido de cliente", "No lo declara"]),
]


# ===========================================================================
# 1. Clasificación de los documentos
# ===========================================================================

def clasificar(texto):
    """Identifica de qué tipo es un documento por su contenido, no por su nombre."""
    t = plano(texto)
    if "orden de fabricacion" in t:
        return "orden"
    if "quantity:" in t or "cover material:" in t:
        return "pedido_cliente"
    if "please find herewith our prices" in t or re.search(r"\bcps\.\s*=", t):
        return "presupuesto"
    if not t.strip():
        return "sin_texto"
    return "desconocido"


TIPOS = {"orden": "Orden de fabricación", "pedido_cliente": "Pedido de cliente",
         "presupuesto": "Presupuesto", "desconocido": "No identificado",
         "sin_texto": "Sin capa de texto"}


# ===========================================================================
# 2. Extracción de campos
# ===========================================================================

def campos_orden(texto):
    """
    Campos de la orden de fabricación.

    Además del valor de cabecera se recogen los valores de respaldo que aparecen
    en otras secciones del mismo documento (logística, tabla de impresión). Son
    los que permiten detectar que el documento se contradice a sí mismo.
    """
    c = {}
    m = re.search(r"Cantidad:\s*\n?.*?\n\s*\S.*?\s{2,}([\d.,]+)\s+(\d+)\s*$",
                  texto, re.MULTILINE)
    if m:
        c["cantidad"] = numero(m.group(1))
        c["paginas"] = numero(m.group(2))

    pos = texto.find("LOG")
    if pos != -1:
        m = re.search(r"Cantidad:\s*([\d.,]+)", texto[pos:])
        if m:
            c["cantidad_logistica"] = numero(m.group(1))

    m = re.search(r"Interiores\s+\d+\s+\d+\s+\S+\s+\S+\s+\d+\s+([\d.,]+)\s+([\d.,]+)", texto)
    if m:
        c["cantidad_impresion"] = numero(m.group(1))

    for destino, clave in (("Interiores", "gramaje_interior"),
                           ("Cubiertas", "gramaje_cubierta")):
        m = re.search(rf"^\s*\S.*?\s{{2,}}[\d ]+x[\d ]+\s+([\d.,]+)\s+{destino}\s",
                      texto, re.MULTILINE)
        if m:
            c[clave] = numero(m.group(1))

    m = re.search(r"^(\d{13})\s+(\d+\s*x\s*\d+)", texto, re.MULTILINE)
    if m:
        c["isbn"] = m.group(1)
        c["formato"] = formato_normal(m.group(2))
    return c


def campos_cliente(texto):
    """
    Campos de la documentación de cliente. Cubre los dos formatos observados: la
    carta de pedido y el presupuesto, que expresan los mismos datos de forma
    distinta.
    """
    c = {}
    directos = {
        "cantidad":         r"Quantity:\s*([\d.,]+)\s*copies",
        "paginas":          r"Extent:\s*([\d.,]+)\s*pp",
        "gramaje_cubierta": r"Cover Material:\s*([\d.,]+)\s*gsm",
        "gramaje_interior": r"Text Paper:\s*([\d.,]+)\s*gsm",
    }
    for clave, patron in directos.items():
        m = re.search(patron, texto, re.IGNORECASE)
        if m:
            c[clave] = numero(m.group(1))

    m = re.search(r"RE:\s*(\d{13})", texto)
    if m:
        c["isbn"] = m.group(1)
    m = re.search(r"Trimmed Size:\s*([\d\sx]+)mm", texto, re.IGNORECASE)
    if m:
        c["formato"] = formato_normal(m.group(1))

    # --- Presupuesto: los mismos datos con otra redacción
    respaldo = {
        "cantidad":         r"([\d.,]+)\s*cps\.\s*=",
        "paginas":          r"Extent\s+([\d.,]+)\s*pp",
        "gramaje_cubierta": r"Cover:.*?([\d.,]+)\s*gsm",
        "gramaje_interior": r"Inside:.*?([\d.,]+)\s*gsm",
    }
    for clave, patron in respaldo.items():
        if clave not in c:
            m = re.search(patron, texto, re.IGNORECASE)
            if m:
                c[clave] = numero(m.group(1))
    if "isbn" not in c:
        m = re.search(r"Ref:\s*(\d{13})", texto)
        if m:
            c["isbn"] = m.group(1)
    if "formato" not in c:
        m = re.search(r"TPS\s+([\d\sx]+)mm", texto, re.IGNORECASE)
        if m:
            c["formato"] = formato_normal(m.group(1))
    return c


def verdad_de_campo(docs, modo="determinista"):
    """
    Discrepancias reales entre la orden y la documentación de cliente, calculadas
    leyendo los documentos. Devuelve (esperados, contexto).
    """
    orden_doc = next((d for d in docs if clasificar(d["texto"]) == "orden"), None)
    cliente_docs = [d for d in docs
                    if clasificar(d["texto"]) in ("pedido_cliente", "presupuesto")]
    if not orden_doc:
        raise ValueError("Falta la orden de fabricación: es el documento que se audita.")
    if not cliente_docs:
        raise ValueError("Falta documentación de cliente: sin ella no hay contra qué "
                         "contrastar.")

    orden = campos_orden(orden_doc["texto"])
    cliente = {}
    for d in cliente_docs:                       # los datos pueden venir repartidos
        for k, v in campos_cliente(d["texto"]).items():
            cliente.setdefault(k, v)

    procedencia = {}
    if modo != "determinista":
        orden, p1 = llm.resolver(modo, orden, orden_doc["texto"],
                                 FICHA["esquema_campos"], FICHA["prompt_extraccion"])
        cliente, p2 = llm.resolver(modo, cliente, "\n".join(d["texto"] for d in cliente_docs),
                                   FICHA["esquema_campos"], FICHA["prompt_extraccion"])
        procedencia = {"orden": p1, "cliente": p2}

    esperados = []
    for clave, (etiqueta, severidad) in CAMPOS.items():
        a, b = cliente.get(clave), orden.get(clave)
        if a is None or b is None:
            continue
        if str(a) != str(b):
            esperados.append({"campo": clave, "etiqueta": etiqueta,
                              "valor_cliente": a, "valor_orden": b,
                              "severidad_esperada": severidad})

    contexto = {"orden": orden, "cliente": cliente,
                "pedido": orden_doc["id"], "procedencia": procedencia,
                "comparables": [k for k in CAMPOS
                                if orden.get(k) is not None and cliente.get(k) is not None]}
    return esperados, contexto


def incoherencias_internas(orden):
    """
    Contradicciones de la orden consigo misma. Un valor de cabecera que no
    concuerda con el cálculo productivo del propio documento delata un error de
    transcripción sin necesidad de consultar ninguna otra fuente.
    """
    out = []
    cab = orden.get("cantidad")
    for clave, donde in (("cantidad_logistica", "bloque de logística"),
                         ("cantidad_impresion", "tabla de impresión")):
        v = orden.get(clave)
        if cab is not None and v is not None and cab != v:
            out.append({"Campo": "Cantidad", "Valor en cabecera": cab,
                        "Valor de respaldo": v, "Procedencia del respaldo": donde})
    return out


# ===========================================================================
# 3. Interpretación de la respuesta del módulo
# ===========================================================================
# Intérprete determinista: reconoce la forma en que el módulo redacta hoy sus
# incidencias. Para formulaciones arbitrarias, `nucleo/llm.py` ocupa este hueco
# sin tocar nada más: lo que se juzga son las incidencias ya interpretadas.

PISTAS_CAMPO = [
    ("gramaje_cubierta", r"gramaje\s+de\s+(la\s+)?cubierta|cubierta.{0,30}gramaje|gramaje.{0,20}cubierta"),
    ("gramaje_interior", r"gramaje\s+de\s+(l\s*)?interior|papel\s+de\s+interior|interior.{0,20}gramaje"),
    ("cantidad",         r"\bunidades\b|\bcantidad\b|\btirada\b|\bejemplares\b|\bcopias\b"),
    ("paginas",          r"\bp[áa]ginas\b|\bpp\b|\bextent\b"),
    ("isbn",             r"\bisbn\b"),
    ("formato",          r"\bformato\b|\btama[ñn]o\b|\bmedidas\b"),
]

SIN_INCIDENCIAS = (r"no\s+se\s+han?\s+(encontrado|detectado)|sin\s+incongruencias|"
                   r"ninguna\s+incidencia|todo\s+(es\s+)?correcto|"
                   r"no\s+hay\s+(incongruencias|discrepancias)")


def _campo_de(texto):
    t = plano(texto)
    for campo, patron in PISTAS_CAMPO:       # el orden importa: lo específico primero
        if re.search(patron, t):
            return campo
    return None


def _severidad_de(cabecera, cuerpo):
    t = plano(cabecera + " " + cuerpo)
    if re.search(r"a\s+revisar|revisar:|posible|podr[íi]a\s+ser|no\s+necesariamente", t):
        return "menor"
    if re.search(r"incongruencia|discrepancia|error|incoherencia", t):
        return "alta"
    return None


def _bloques(texto):
    """
    Parte la respuesta en incidencias. Reconoce dos formas: encabezados de
    severidad seguidos de párrafos, y listas de párrafos sin encabezado.
    """
    bloques, cabecera, actual = [], "", []

    def cerrar():
        cuerpo = " ".join(x.strip() for x in actual if x.strip())
        if len(cuerpo) > 25:                     # descarta restos de interfaz
            bloques.append((cabecera, cuerpo))

    for linea in texto.splitlines():
        desnuda = linea.strip()
        if re.match(r"^\s*(INCONGRUENCIA|A\s+REVISAR|INCOHERENCIA|AVISO|ERROR)S?\b",
                    desnuda, re.IGNORECASE):
            cerrar()
            cabecera, actual = desnuda, []
            continue
        if not desnuda:                          # línea en blanco separa incidencias
            if actual:
                cerrar()
                actual = []
            continue
        actual.append(desnuda)
    cerrar()
    return bloques


def recuento_declarado(texto):
    """Suma los recuentos que el módulo declara en sus encabezados: «INCONGRUENCIA (1)»."""
    n = [int(m) for m in re.findall(
        r"(?:INCONGRUENCIA|A\s+REVISAR|INCOHERENCIA|AVISO|ERROR)S?\s*\((\d+)\)",
        texto or "", re.IGNORECASE)]
    return sum(n) if n else None


def interpretar(texto, modo="determinista"):
    """Devuelve (incidencias, avisos)."""
    texto = (texto or "").strip()
    if not texto:
        return [], []
    if re.search(SIN_INCIDENCIAS, texto, re.IGNORECASE) and len(texto) < 200:
        return [], []

    if modo not in ("determinista", None):
        return llm.interpretar_con_llm(texto, FICHA["esquema_salida"],
                                       FICHA["prompt_interpretacion"]), []

    incidencias, avisos = [], []
    for cabecera, cuerpo in _bloques(texto):
        campo = _campo_de(cuerpo)
        if not campo:
            avisos.append(f"No se ha identificado el campo en: «{cuerpo[:80]}…»")
            continue

        # El módulo redacta "el cliente indica X, pero la orden indica Y".
        # La conjunción separa el valor de origen del valor discrepante.
        partes = re.split(r"\bpero\b|\bmientras que\b|\bfrente a\b", cuerpo, maxsplit=1)
        izq, der = (partes[0], partes[1]) if len(partes) == 2 else (cuerpo, "")

        v_izq, v_der = _primer_numero(izq), _primer_numero(der)

        menciona_orden = lambda s: bool(re.search(
            r"orden\s+de\s+fabricaci[óo]n|\bof\d*\.pdf|\bOF\b", s, re.IGNORECASE))
        if menciona_orden(der) or not menciona_orden(izq):
            valor_cliente, valor_orden, corregir = v_izq, v_der, "orden"
        else:
            valor_cliente, valor_orden, corregir = v_der, v_izq, "cliente"

        ficheros = {f.strip().lower() for f in re.findall(r"[\w\s\-–—()]+?\.pdf", cuerpo)}
        severidad = _severidad_de(cabecera, cuerpo)
        if severidad is None:
            severidad = "alta"
            avisos.append(f"Severidad no declarada en la incidencia de "
                          f"{ETIQUETAS.get(campo, campo)}; se asume alta.")

        # Incoherencia interna: ambos valores atribuidos al mismo documento. En ese
        # caso la dirección de la corrección no aplica: no hay dos documentos entre
        # los que elegir cuál es la fuente de verdad.
        interna = bool(re.search(r"cabecera|log[íi]stica|internamente|"
                                 r"el propio documento|dentro del mismo", cuerpo,
                                 re.IGNORECASE))
        if interna:
            corregir = None

        incidencias.append({"campo": campo, "valor_cliente": valor_cliente,
                            "valor_orden": valor_orden, "severidad": severidad,
                            "cita_documentos": len(ficheros) >= 2,
                            "corregir": corregir, "interna": interna, "texto": cuerpo})
    return incidencias, avisos


def _primer_numero(fragmento):
    # Se descartan los números pegados a un nombre de fichero (el ISBN del título)
    limpio = re.sub(r"\S+\.pdf", " ", fragmento, flags=re.IGNORECASE)
    m = re.search(r"(?:indica|es|de|señala|pone|figura|consta)\s+([\d.,]+)", limpio)
    if not m:
        m = re.search(r"\b([\d.,]{2,})\b", limpio)
    if not m:
        return None
    return m.group(1).rstrip(".,;:")             # la puntuación no es parte del valor


# ===========================================================================
# 4. Contraste y batería
# ===========================================================================

def _comparar(esperado, reportado):
    """
    ¿Se sostiene documentalmente la incidencia? Señalar el campo correcto no
    basta: si cita valores que contradicen los documentos, no computa como
    detección y además resta precisión.
    """
    problemas = []
    if not mismo_valor(reportado.get("valor_cliente"), esperado["valor_cliente"]):
        problemas.append(f"atribuye al cliente {reportado['valor_cliente']} "
                         f"y el documento dice {esperado['valor_cliente']}")
    if not mismo_valor(reportado.get("valor_orden"), esperado["valor_orden"]):
        problemas.append(f"atribuye a la orden {reportado['valor_orden']} "
                         f"y el documento dice {esperado['valor_orden']}")
    return (not problemas), "; ".join(problemas)


def evaluar(esperados, incidencias, contexto, texto_respuesta=None, repeticion=None,
            modo_lectura="determinista", evidencias=None):
    contraste = C.contrastar(esperados, incidencias,
                             clave=lambda x: x["campo"], comparar=_comparar)
    motivos = {m["clave"]: m["motivo"] for m in contraste["motivos"]}
    esperada = {d["campo"]: d["severidad_esperada"] for d in esperados}
    sev = [{"campo": i["campo"], "etiqueta": ETIQUETAS.get(i["campo"], i["campo"]),
            "asignada": i.get("severidad"), "esperada": esperada[i["campo"]],
            "correcta": i.get("severidad") == esperada[i["campo"]]}
           for i in incidencias if i.get("campo") in esperada]
    casos = {}

    # 1 — discrepancias de severidad alta
    duras = [d for d in esperados if d["severidad_esperada"] == "alta"]
    det = [d for d in contraste["detectadas"] if d["severidad_esperada"] == "alta"]
    omit = [d["etiqueta"] for d in contraste["omitidas"] if d["severidad_esperada"] == "alta"]
    err = [d["etiqueta"] for d in contraste["con_error"] if d["severidad_esperada"] == "alta"]
    casos[1] = B.caso(bool(duras) and len(det) == len(duras),
                      f"{len(det)} de {len(duras)} detectadas correctamente."
                      + (f" Omitidas: {', '.join(omit)}." if omit else "")
                      + (f" Señaladas con valores que contradicen los documentos: "
                         f"{', '.join(err)}." if err else ""),
                      omitir=not duras)

    # 2 — graduación de severidad
    malas = [s for s in sev if not s["correcta"]]
    casos[2] = B.caso(bool(sev) and not malas,
                      "; ".join(f"{s['etiqueta']}: {s['asignada'] or 'sin declarar'}"
                                + ("" if s["correcta"] else f" (esperada {s['esperada']})")
                                for s in sev) or "Sin severidades comparables.",
                      omitir=not sev)

    # 3 — precisión: ni incidencias inventadas ni valores erróneos
    problemas = []
    if contraste["falsas"]:
        problemas.append("sin respaldo documental: "
                         + ", ".join(ETIQUETAS.get(i.get("campo"), str(i.get("campo")))
                                     for i in contraste["falsas"]))
    if contraste["con_error"]:
        problemas.append("con valores que no coinciden con los documentos: "
                         + "; ".join(f"{d['etiqueta']} {motivos.get(d['campo'], '')}"
                                     for d in contraste["con_error"]))
    if contraste["duplicadas"]:
        problemas.append("repetidas: " + ", ".join(
            ETIQUETAS.get(i.get("campo"), str(i.get("campo")))
            for i in contraste["duplicadas"]))
    casos[3] = B.caso(not problemas,
                      f"Precisión {contraste['precision']}%. "
                      + ("Incidencias " + "; ".join(problemas) + "." if problemas
                         else "Todas las incidencias se sostienen en los documentos."),
                      omitir=not incidencias)

    # 4 — completitud del recuento declarado
    declarado = recuento_declarado(texto_respuesta) if texto_respuesta else None
    casos[4] = B.caso(declarado == len(incidencias),
                      f"El módulo declara {declarado} incidencia(s) y emite "
                      f"{len(incidencias)}." if declarado is not None else
                      "La respuesta no declara ningún recuento en sus encabezados.",
                      omitir=declarado is None,
                      requiere=("una respuesta del módulo que declare el recuento en "
                                "sus encabezados, del tipo «INCONGRUENCIA (1)»")
                               if declarado is None else None)

    # 5 — trazabilidad
    sin_fuente = [ETIQUETAS.get(i.get("campo"), str(i.get("campo")))
                  for i in incidencias if not i.get("cita_documentos")]
    casos[5] = B.caso(not sin_fuente,
                      f"{len(incidencias) - len(sin_fuente)} de {len(incidencias)} "
                      f"incidencias citan sus dos documentos."
                      + (f" Sin respaldo: {', '.join(sin_fuente)}." if sin_fuente else ""),
                      omitir=not incidencias)

    # 6 — dirección de la corrección
    # El documento de cliente es fuente de verdad por definición; la orden de
    # fabricación es la transcripción, y por tanto el documento a corregir.
    declaradas = [i for i in incidencias if i.get("corregir")]
    mal_dirigidas = [ETIQUETAS.get(i["campo"], i["campo"]) for i in declaradas
                     if i["corregir"] != "orden"]
    casos[6] = B.caso(not mal_dirigidas,
                      "La corrección apunta a la orden de fabricación en todas las "
                      "incidencias." if not mal_dirigidas else
                      f"La corrección no apunta a la orden de fabricación en: "
                      f"{', '.join(mal_dirigidas)}.",
                      omitir=not declaradas)

    # 7 — repetibilidad
    if repeticion is None:
        casos[7] = B.caso(False, "No se ha aportado una segunda ejecución.",
                          omitir=True,
                          requiere=("una segunda ejecución del módulo sobre este "
                                    "mismo pedido, sin modificar los documentos"))
    else:
        firma = lambda l: sorted((i["campo"], i["severidad"]) for i in l)
        f1, f2 = firma(incidencias), firma(repeticion)
        if f1 == f2:
            detalle = (f"Las dos ejecuciones coinciden en los {len(f1)} campo(s) "
                       f"señalado(s) y en su severidad.")
        else:
            solo1 = [ETIQUETAS.get(c, c) for c, s in f1 if (c, s) not in f2]
            solo2 = [ETIQUETAS.get(c, c) for c, s in f2 if (c, s) not in f1]
            detalle = "El veredicto varía entre ejecuciones."
            if solo1:
                detalle += f" Sólo en la primera: {', '.join(solo1)}."
            if solo2:
                detalle += f" Sólo en la segunda: {', '.join(solo2)}."
        casos[7] = B.caso(f1 == f2, detalle)

    # 8 — cobertura de campos del módulo
    probados = {"cantidad", "gramaje_cubierta"}
    otros = [d for d in esperados if d["campo"] not in probados]
    det_otros = [d for d in contraste["detectadas"] if d["campo"] not in probados]
    casos[8] = B.caso(bool(otros) and len(det_otros) == len(otros),
                      (f"Discrepancias en campos no probados: "
                       f"{', '.join(d['etiqueta'] for d in otros)}. Detectadas "
                       f"{len(det_otros)} de {len(otros)}." if otros else
                       f"Campos comparados sin discrepancia: "
                       f"{', '.join(ETIQUETAS[k] for k in contexto['comparables'])}. "
                       f"Este pedido no pone a prueba ningún campo fuera de cantidad "
                       f"y gramaje de cubierta."),
                      no_aplica=not otros,
                      requiere=("un pedido con una discrepancia en un campo distinto "
                                "de cantidad y gramaje de cubierta — páginas, ISBN o "
                                "formato") if not otros else None)

    # 9 — ausencia frente a imposibilidad de comprobar          [alcance: módulo]
    # No se deduce de la respuesta pegada: o el módulo separa las dos situaciones en
    # su modelo de estados o no las separa, y eso vale para todos sus pedidos. Se
    # juzga con evidencia aportada, y el veredicto declara cuál.
    e9 = (evidencias or {}).get(9) or EVIDENCIAS[9]
    if e9.get("constatado"):
        casos[9] = B.caso(True, e9["nota"], evidencia=e9["origen"])
    else:
        casos[9] = B.caso(False, "No consta que el módulo separe la ausencia de "
                                 "incidencias de la imposibilidad de auditar.",
                          omitir=True, requiere=e9["como_comprobarlo"])

    hallazgos = []
    internas = incoherencias_internas(contexto["orden"])
    if internas:
        hallazgos.append(B.hallazgo(
            "La orden de fabricación se contradice a sí misma",
            "El evaluador detecta " + str(len(internas)) + " incoherencia(s) interna(s): "
            + "; ".join(f"la cabecera indica {i['Valor en cabecera']} frente a "
                        f"{i['Valor de respaldo']} en el {i['Procedencia del respaldo']}"
                        for i in internas)
            + ". El módulo contrasta la orden únicamente contra los documentos de "
              "cliente, luego no puede detectarlo.",
            "El contraste externo revela que dos documentos no coinciden; el contraste "
            "interno revela cuál de los dos valores es el correcto, porque el cálculo "
            "productivo de la propia orden ya está hecho sobre él. Además seguiría "
            "funcionando aunque faltase el documento de cliente.",
            internas))

    if e9.get("constatado"):
        hallazgos.append(B.hallazgo(
            "El estado de auditabilidad no viaja en la salida",
            "El módulo distingue en su tablero los pedidos que no ha podido auditar "
            "—sin orden de fabricación, sin documento de origen— de los auditados sin "
            "incidencias. Pero esa distinción vive en la pantalla: la respuesta que se "
            "consume aguas abajo son las incidencias, y un pedido inauditable produce "
            "la misma lista vacía que un pedido correcto.",
            "La conexión con validación humana transporta incidencias. Si el estado no "
            "viaja con ellas, quien revisa recibe silencio y lo lee como conformidad, "
            "que es justo lo que el caso 9 quiere evitar. La comprobación está hecha; "
            "lo que falta es que el dato cruce la conexión."))

    por_campo = {i["campo"]: i for i in incidencias}
    tabla = [{"Campo": d["etiqueta"], "Cliente": d["valor_cliente"],
              "Orden de fabricación": d["valor_orden"],
              "Severidad esperada": d["severidad_esperada"].capitalize(),
              "Severidad declarada":
                  (por_campo.get(d["campo"], {}).get("severidad") or "—").capitalize(),
              "Detectada por el módulo": C.estado_de(d, contraste)} for d in esperados]

    # --- Desglose esperado / observado para la plantilla común -------------
    def _l(xs, vacio="ninguno"):
        xs = [str(x) for x in xs if x]
        return ", ".join(xs) if xs else vacio

    NADA = "— el conjunto no contiene esta situación —"
    FALTA = "— no aportado en esta ejecución —"

    _duras = [d for d in esperados if d["severidad_esperada"] == "alta"]
    _det_duras = [d for d in contraste["detectadas"]
                  if d["severidad_esperada"] == "alta"]
    _mal_sev = [x for x in sev if not x["correcta"]]
    _sin_fuente = [ETIQUETAS.get(i.get("campo"), str(i.get("campo")))
                   for i in incidencias if not i.get("cita_documentos")]
    _probados = {"cantidad", "gramaje_cubierta"}
    _otros = [d for d in esperados if d["campo"] not in _probados]
    _det_otros = [d for d in contraste["detectadas"] if d["campo"] not in _probados]
    _decl = recuento_declarado(texto_respuesta) if texto_respuesta else None

    _d = {
        1: (_l([f"{d['etiqueta']}: {d['valor_cliente']} vs {d['valor_orden']}"
                for d in _duras]) if _duras else "ninguna discrepancia de severidad alta",
            f"detecta {len(_det_duras)} de {len(_duras)}"
            + ("; omite: " + _l([d["etiqueta"] for d in contraste["omitidas"]
                                 if d["severidad_esperada"] == "alta"])
               if any(d["severidad_esperada"] == "alta"
                      for d in contraste["omitidas"]) else "")
            if _duras else NADA),
        2: (_l([f"{x['etiqueta']}: {x['esperada']}" for x in sev])
            if sev else "sin incidencias que graduar",
            _l([f"{x['etiqueta']}: {x['asignada'] or '—'}" for x in sev])
            if sev else NADA),
        3: (f"toda incidencia emitida respaldada por los documentos "
            f"(precisión 100%)",
            f"precisión {contraste['precision']}% sobre "
            f"{len(incidencias)} incidencia(s)" if incidencias else FALTA),
        4: ("el recuento declarado coincide con las incidencias emitidas",
            f"declara {_decl}, emite {len(incidencias)}" if _decl is not None
            else FALTA),
        5: ("cada incidencia cita el documento del que sale",
            (f"sin fuente: " + _l(_sin_fuente)) if _sin_fuente
            else f"las {len(incidencias)} citan documento"
            if incidencias else FALTA),
        6: ("la corrección apunta del valor de la orden al del cliente",
            f"{len(contraste['detectadas'])} incidencia(s) con dirección "
            f"comprobable" if contraste["detectadas"] else FALTA),
        7: ("las mismas incidencias y severidades en dos ejecuciones",
            ("coinciden" if casos[7]["resultado"] == "pasa" else "difieren")
            if repeticion is not None else FALTA),
        8: (_l([d["etiqueta"] for d in _otros],
               "ninguna discrepancia fuera de los campos ya probados"),
            f"detecta {len(_det_otros)} de {len(_otros)}" if _otros else NADA),
        9: ("distinguir «sin incidencias» de «no se ha podido comprobar»",
            (casos[9].get("evidencia") or "sin evidencia aportada")),
    }
    for _n, (_esp, _obs) in _d.items():
        if _n in casos:
            casos[_n]["esperado"], casos[_n]["observado"] = _esp, _obs

    return {"esperados": esperados, "reportados": incidencias, "contraste": contraste,
            "severidades": sev, "casos": casos, "hallazgos": hallazgos,
            "tabla_contraste": tabla, "contexto": contexto,
            "modo_lectura": modo_lectura}


# --- Traducción a la tabla corregible de la interfaz -----------------------

_INV_CAMPO = {v: k for k, v in ETIQUETAS.items()}
_CORREGIR = {"orden": "Orden de fabricación", "cliente": "Pedido de cliente",
             None: "No lo declara"}
_INV_CORREGIR = {"Orden de fabricación": "orden", "Pedido de cliente": "cliente",
                 "No lo declara": None}


def a_fila(i):
    return {"Campo": ETIQUETAS.get(i["campo"], i["campo"]),
            "Valor según cliente": i.get("valor_cliente") or "",
            "Valor según orden": i.get("valor_orden") or "",
            "Severidad": "Alta" if i.get("severidad") == "alta" else "Menor",
            "Cita ambos documentos": bool(i.get("cita_documentos")),
            "Documento a corregir": _CORREGIR.get(i.get("corregir"), "No lo declara")}


def de_fila(f):
    return {"campo": _INV_CAMPO.get(str(f["Campo"])),
            "valor_cliente": str(f["Valor según cliente"]).strip() or None,
            "valor_orden": str(f["Valor según orden"]).strip() or None,
            "severidad": "alta" if str(f["Severidad"]) == "Alta" else "menor",
            "cita_documentos": bool(f["Cita ambos documentos"]),
            "corregir": _INV_CORREGIR.get(str(f["Documento a corregir"])),
            "interna": False, "texto": ""}


def sujeto(contexto):
    return f"el pedido {contexto['pedido']}"


# Respuesta real del módulo sobre el pedido 42805, para la demo.
EJEMPLO = """INCONGRUENCIA (1)
El pedido del cliente (Beliefs in Our World 2nd Edition Skills Book 9780717195473.pdf) indica 3.000 unidades, pero la orden de fabricación (of42805.pdf) indica 30.000.
of42805.pdf   Beliefs in Our World 2nd Edition Skills Book 9780717195473.pdf

A REVISAR (1)
El gramaje de cubierta en el pedido del cliente (Beliefs in Our World 2nd Edition Skills Book 9780717195473.pdf) es 240g, pero la orden de fabricación (of42805.pdf) indica 250g. A revisar: podría ser el redondeo estándar de GraphyCems, no necesariamente un error.
of42805.pdf   Beliefs in Our World 2nd Edition Skills Book 9780717195473.pdf"""
