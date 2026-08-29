"""
Ejecución de una batería y recuento de resultados.

Un caso tiene cuatro desenlaces, no dos, y la diferencia entre los dos últimos
importa:

  pasa       — se ha comprobado y el módulo lo cumple
  no_pasa    — se ha comprobado y el módulo no lo cumple
  pendiente  — el caso aplica a estos datos, pero falta algo que puedo conseguir
               sin cambiar de caso: una segunda ejecución, la consulta de
               vencimientos, la pantalla de alertas
  no_aplica  — el caso mide una situación que este conjunto de datos no contiene.
               No se puede ejercitar aquí por construcción, y no dice nada del
               módulo: dice algo de mi banco de pruebas

La distinción no es cosmética. «Pendiente» es un deber mío sobre estos mismos
datos; «no aplica» es un dato que hay que pedir. Contar cualquiera de los dos
como superado inflaría el resultado, y contarlos como fallidos penalizaría al
módulo por una situación que no se le ha puesto delante.

De ahí salen dos porcentajes distintos:

  tasa de acierto  = superados / verificados     — cómo de bien lo hace el módulo
  cobertura        = verificados / diseñados     — cuánto de mi batería he podido
                                                   ejercitar con los datos que tengo

Un caso `no_aplica` o `pendiente` lleva escrito en `requiere` qué haría falta
para ejercitarlo. Esa lista es exactamente lo que hay que pedirle al compañero.
"""

TEXTO = {"pasa": "Pasa", "no_pasa": "No pasa", "pendiente": "Pendiente",
         "no_aplica": "No aplica"}
COLOR = {"pasa": "#0ca30c", "no_pasa": "#d03b3b", "pendiente": "#52514e",
         "no_aplica": "#898781"}
ETIQUETA_CASO = {"no_pasa": "caso fallido", "pendiente": "caso pendiente",
                 "no_aplica": "caso no aplicable a estos datos",
                 "pasa": "caso superado"}

# Un caso puede juzgarse sobre los datos de esta ejecución o ser una propiedad
# del módulo, que se comprueba una vez y vale para todos sus pedidos.
ALCANCES = {"ejecucion": "sobre los datos de esta ejecución",
            "modulo": "propiedad del módulo, verificada aparte"}


# ---------------------------------------------------------------------------
# Severidad
# ---------------------------------------------------------------------------
# La severidad no mide cuánto molesta el fallo: mide **qué pasa aguas abajo si
# nadie lo ve**. Por eso el criterio es la propagación, no la incomodidad.
#
# Y va declarada en la ficha de la rama, junto al caso, **antes de saber si el
# módulo lo pasa**. Si se asignara al ver el resultado, la severidad dejaría de
# clasificar el riesgo y pasaría a justificar la nota.

SEVERIDADES = {
    "critica": (
        "Crítica",
        "El fallo se propaga aguas abajo sin dejar rastro. Quien recibe la salida "
        "no tiene forma de saber que hay un problema, así que lo da por bueno.",
        "#b3261e"),
    "alta": (
        "Alta",
        "El fallo es visible para quien recibe la salida, pero le obliga a rehacer "
        "a mano el trabajo que el módulo venía a ahorrarle.",
        "#d9822b"),
    "media": (
        "Media",
        "Degrada la utilidad de la salida sin invalidarla: se puede seguir "
        "trabajando con ella, peor.",
        "#8a8880"),
}

ORDEN_SEVERIDAD = ["critica", "alta", "media"]


def caso(ok, detalle, omitir=False, no_aplica=False, requiere=None, evidencia=None,
         esperado=None, observado=None):
    """
    `omitir`     -> pendiente: el caso aplica pero falta un dato de esta ejecución
    `no_aplica`  -> el conjunto no contiene la situación que el caso mide
    `requiere`   -> qué haría falta para ejercitarlo
    `evidencia`  -> de dónde sale el juicio cuando no sale de la salida pegada
    `esperado`   -> qué tenía que haber salido, según la verdad de campo
    `observado`  -> qué salió de verdad, según la salida del módulo

    `esperado` y `observado` desglosan lo que antes iba fundido en `detalle`. El
    texto largo sigue existiendo porque explica **por qué**; estos dos campos
    existen porque una plantilla de evaluación tiene que poder poner las dos cosas
    en dos columnas y dejar que se comparen de un vistazo, sin leer prosa.

    Se dejan opcionales a propósito. Un caso que no los rellene sale con «no
    desglosado» en la plantilla, que es honesto; rellenarlos con un resumen
    automático de la observación sería inventar una comparación que nadie ha hecho.
    """
    if no_aplica:
        resultado = "no_aplica"
    elif omitir:
        resultado = "pendiente"
    else:
        resultado = "pasa" if ok else "no_pasa"
    return {"resultado": resultado, "observacion": detalle,
            "requiere": requiere, "evidencia": evidencia,
            "esperado": esperado, "observado": observado}


def resumen(casos):
    cuenta = {k: sum(1 for c in casos.values() if c["resultado"] == k)
              for k in ("pasa", "no_pasa", "pendiente", "no_aplica")}
    con_evidencia = cuenta["pasa"] + cuenta["no_pasa"]
    total = len(casos)
    return {
        "total": total,
        "con_evidencia": con_evidencia,
        "pasa": cuenta["pasa"], "no_pasa": cuenta["no_pasa"],
        "pendiente": cuenta["pendiente"], "no_aplica": cuenta["no_aplica"],
        # Sólo sobre lo verificado: pendientes y no aplicables quedan fuera y se
        # declaran.
        "tasa": round(100 * cuenta["pasa"] / con_evidencia, 1) if con_evidencia else None,
        # Cuánto de la batería diseñada ha podido ejercitarse con estos datos.
        "cobertura": round(100 * con_evidencia / total, 1) if total else None,
    }


def requisitos(casos):
    """Qué datos harían falta para ejercitar lo que hoy no se puede juzgar."""
    out = []
    for n, c in sorted(casos.items()):
        if c["resultado"] in ("pendiente", "no_aplica") and c.get("requiere"):
            out.append({"caso": n, "estado": c["resultado"], "requiere": c["requiere"]})
    return out


def hallazgo(titulo, detalle, porque_importa, tabla=None):
    """
    Hallazgo de cobertura: una comprobación que el módulo no realiza y el
    evaluador sí. No puntúa —no hacer algo no equivale a hacerlo mal— pero se
    informa, porque el evaluador demuestra que había algo que encontrar.
    """
    return {"titulo": titulo, "detalle": detalle,
            "porque_importa": porque_importa, "tabla": tabla or []}
