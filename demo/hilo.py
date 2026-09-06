"""
El hilo: una sola incongruencia recorriendo tres módulos.

Por qué existe
--------------
La demo por módulos enseña cinco cosas seguidas y cada una se entiende sola. Lo
que no enseña es **el sistema**: que los cinco trabajos son partes de un mismo
recorrido y que el fallo de uno se convierte en el trabajo del siguiente.

Este hilo sigue **un solo hecho** —una cantidad que no cuadra en el pedido 42805
de GraphyCems— desde que aparece hasta que alguien decide y esa decisión queda
registrada. Y es el mismo recorrido que dibuja el diagrama de flujo del equipo:

    1-3  OBSERVAR    Juan detecta que el pedido y la orden no dicen lo mismo
    4-5  GOBERNAR    la ontología de Pablo dice de quién es la autoridad
    5-6  DECIDIR     Mencía recoge la validación y conserva el estado vigente
      7  COMPROBAR   este bloque juzga si lo anterior es correcto y reproducible

La regla del pie de ese diagrama es literalmente la tesis de este TFG:

    «Ninguna discrepancia se convierte en verdad sin evidencia, autoridad y
     evaluación.»

Qué se puede enseñar hoy y qué no
----------------------------------
Los tres primeros pasos tienen datos reales y se ejecutan. El cuarto —la
exportación de Mencía **para este pedido**— todavía no existe: la que hay es del
PED1004, otro pedido. Así que el hilo llega hasta donde llegan los datos y **dice
dónde se corta**, que es lo que hace este sistema con todo lo demás.

Un hilo que fingiera el último paso sería una demo más bonita y una demostración
peor: lo que se está demostrando es precisamente que el sistema distingue lo
comprobado de lo supuesto.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent / "datos"

# El hecho que recorre el hilo. Sale de la auditoría real del pedido 42805 y no
# lo ha inventado nadie: lo dedujo el evaluador leyendo los dos documentos.
HECHO = {
    "pedido": "42805",
    "campo": "cantidad",
    "titulo": "Beliefs in Our World 2nd Edition Skills Book",
    "isbn": "9780717195473",
    "valor_cliente": 3000,
    "valor_orden": 30000,
    "documento_cliente": "Beliefs in Our World … 9780717195473.pdf",
    "documento_orden": "of42805.pdf",
}

PASOS = [
    {
        "n": 1,
        "fase": "OBSERVAR",
        "modulo": "auditoria",
        "responsable": "Juan Salas",
        "titulo": "Aparece la discrepancia",
        "que_pasa": (
            "El pedido del cliente pide **3.000 ejemplares** y la orden de "
            "fabricación dice **30.000**. Un cero de más en una tirada son 27.000 "
            "libros que nadie ha pedido."),
        "quien_lo_dice": "El módulo de Juan la emite como INCONGRUENCIA.",
        "que_hace_el_evaluador": (
            "No se fía: abre los dos PDF, extrae la cantidad de cada uno por su "
            "cuenta y comprueba que la discrepancia existe y es la que él dice. "
            "**Ésta es la verdad de campo del hilo entero**, y la calcula aquí — "
            "los módulos siguientes no tendrán que aportarla."),
        "estado": "ejecutable",
        "requiere": None,
    },
    {
        "n": 2,
        "fase": "GOBERNAR",
        "modulo": "gobernanza",
        "responsable": "Pablo Morillas",
        "titulo": "¿De quién es esta decisión?",
        "que_pasa": (
            "Alguien tiene que decidir cuál de los dos números vale. La "
            "organización no es plana: hay tres áreas y tres niveles, y cada "
            "ámbito tiene un dueño."),
        "quien_lo_dice": (
            "La matriz de autoridad de Pablo: quién manda sobre Producción, "
            "sobre Comercial y sobre Finanzas."),
        "que_hace_el_evaluador": (
            "La convierte en dato y la usa para poder preguntar después una cosa "
            "que **ningún módulo puede contestar solo**: ¿validó quien tenía "
            "autoridad? Mencía sabe quién validó; Pablo sabe quién podía. Sólo el "
            "evaluador tiene los dos delante."),
        "estado": "ejecutable",
        "requiere": ("el mapa campo → ámbito. La matriz de autoridad la entregó "
                     "Pablo y va de rol a área; el módulo de Mencía va de "
                     "contradicción a categoría; de qué área es cada campo de un "
                     "pedido no lo dice ninguno de los dos, y sin ese paso el "
                     "cruce se declara pero no puede fallarle a nadie"),
    },
    {
        "n": 3,
        "fase": "DECIDIR",
        "modulo": "contradicciones",
        "responsable": "Mencía Viñuelas",
        "titulo": "Alguien decide, y la decisión se guarda",
        "que_pasa": (
            "La discrepancia llega a su módulo como contradicción. Quien no tiene "
            "autoridad suficiente **propone**; quien la tiene **valida**. A partir "
            "de ahí, cualquier pregunta sobre ese pedido recibe el valor decidido "
            "y no vuelve a mostrar el conflicto."),
        "quien_lo_dice": (
            "Su exportación: los hechos, las contradicciones y las resoluciones."),
        "que_hace_el_evaluador": (
            "Recalcula las contradicciones desde los hechos —ignorando su tabla— y "
            "después compara **dos exportaciones**, antes y después de resolver. "
            "Ahí se ven tres cosas que una sola foto no enseña: lo que cambió, lo "
            "que no debía cambiar y lo que se perdió."),
        "estado": "parcial",
        "requiere": ("la exportación de Mencía para el pedido 42805, antes y "
                     "después de resolver. Hoy sólo existe la del PED1004, que es "
                     "otro pedido: sirve para probar el mecanismo, no para cerrar "
                     "este hilo"),
    },
    {
        "n": 4,
        "fase": "COMPROBAR",
        "modulo": "evaluacion",
        "responsable": "Íñigo Daza",
        "titulo": "¿Es correcto y reproducible?",
        "que_pasa": (
            "Los tres pasos anteriores han producido un dato, una autoridad y una "
            "decisión. Falta la pregunta que da sentido a los tres."),
        "quien_lo_dice": "Este bloque.",
        "que_hace_el_evaluador": (
            "Emite un veredicto por módulo con dos métricas comparables, gradúa "
            "cada fallo por lo que provoca aguas abajo, y **declara lo que no ha "
            "podido comprobar** en vez de callarlo. Un caso pendiente no es un "
            "aprobado ni un suspenso: es una pregunta que sigue abierta y dice qué "
            "hace falta para cerrarla."),
        "estado": "ejecutable",
        "requiere": None,
    },
]

REGLA = ("Ninguna discrepancia se convierte en verdad sin evidencia, autoridad "
         "y evaluación.")


def estado_de_los_datos():
    """
    Qué hay y qué falta para poder recorrer el hilo entero, sin adornos.

    Se calcula mirando el disco, no escribiéndolo a mano: un guion que afirma
    tener datos que no están es la primera cosa que este sistema le reprocha a
    los módulos que evalúa.
    """
    auditoria = sorted((RAIZ / "auditoria").glob("*.pdf")) if (RAIZ / "auditoria").is_dir() else []
    contra = sorted((RAIZ / "contradicciones").glob("*.json")) if (RAIZ / "contradicciones").is_dir() else []
    onto = (Path(__file__).resolve().parent.parent / "referencia"
            / "ontologia_autoridad.json")
    del_pedido = [f for f in contra if HECHO["pedido"] in f.name]
    return {
        "documentos_del_pedido": [f.name for f in auditoria],
        "hay_documentos": bool(auditoria),
        "ontologia": onto.is_file(),
        "exportaciones": [f.name for f in contra],
        "exportacion_del_pedido": [f.name for f in del_pedido],
        "hilo_completo": bool(auditoria) and onto.is_file() and len(del_pedido) >= 2,
    }
