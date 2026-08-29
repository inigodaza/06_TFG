"""
La plantilla común de evaluación.

Es el artefacto que pidió Fabián el 24/08: entradas, resultado esperado, resultado
observado, severidad y pasa/no pasa. Una sola forma para todos los módulos.

Por qué es una capa aparte y no un campo más del veredicto
-----------------------------------------------------------
El `EvaluationResult` cuenta **por qué** un módulo obtiene su nota: explica, razona
y ancla cada aspecto a su caso. La plantilla no explica: **compara**. Pone lo que
tenía que salir al lado de lo que salió y deja que se vea la diferencia sin leer
prosa.

Son dos necesidades distintas y por eso son dos salidas distintas. Quien evalúa
necesita el razonamiento; quien tiene que corregir el módulo necesita la tabla. La
misma evaluación alimenta las dos, así que no pueden discrepar: las dos se generan
del mismo objeto `ev`.

Qué hace la plantilla que el veredicto no hacía
------------------------------------------------
Obliga a separar `esperado` de `observado`. Antes los dos iban fundidos en el texto
de la observación, y eso permitía escribir cosas como «el estado no coincide» sin
decir cuál era cada uno. Con dos columnas ya no se puede: o se rellenan o sale
escrito «no desglosado», que es una deuda visible.

Y añade la severidad, declarada en la ficha de cada rama **antes** de ejecutar.
Un fallo que se propaga aguas abajo sin dejar rastro no es lo mismo que uno que
obliga a rehacer trabajo a mano, y hasta ahora los dos pesaban igual.
"""

from .bateria import ORDEN_SEVERIDAD, SEVERIDADES, TEXTO

# Las columnas, en el orden en que las pidió Fabián. El orden importa: se lee de
# izquierda a derecha como la historia de una comprobación —qué le di, qué esperaba,
# qué salió, cuánto importa, veredicto—.
COLUMNAS = ["#", "Caso", "Entradas", "Resultado esperado", "Resultado observado",
            "Severidad", "Pasa / No pasa"]

SIN_DESGLOSAR = "— no desglosado —"


def severidad_de(ficha, n):
    """
    La severidad declarada para ese caso. Si la rama no la declara, se dice: una
    severidad inventada por defecto sería peor que ninguna, porque parecería una
    decisión cuando sería un hueco.
    """
    return (ficha.get("severidad") or {}).get(n)


def entradas_de(ev, n, por_defecto=""):
    """
    Qué se le dio al módulo para ejercitar ese caso.

    Casi siempre es la entrada común de la ejecución —los seis contratos, el JSON
    de la consulta—. Un caso de alcance «módulo» puede declarar la suya propia,
    porque no se juzga con la salida pegada sino con evidencia aportada aparte.
    """
    caso = ev["casos"][n]
    if caso.get("evidencia"):
        return f"Evidencia declarada: {caso['evidencia']}"
    return por_defecto


def filas(ficha, ev, entradas=""):
    """La plantilla en bruto: una fila por caso, lista para tabla o CSV."""
    fuera = []
    for n, caso in sorted(ev["casos"].items()):
        sev = severidad_de(ficha, n)
        fuera.append({
            "#": n,
            "Caso": ficha["casos"].get(n, ""),
            "Entradas": entradas_de(ev, n, entradas),
            "Resultado esperado": caso.get("esperado") or SIN_DESGLOSAR,
            "Resultado observado": caso.get("observado") or SIN_DESGLOSAR,
            "Severidad": SEVERIDADES[sev][0] if sev in SEVERIDADES else "—",
            "Pasa / No pasa": TEXTO[caso["resultado"]],
        })
    return fuera


def fallos_por_severidad(ficha, ev):
    """
    Los casos fallidos agrupados por severidad, de más grave a menos.

    Sólo entran los `no_pasa`. Un pendiente o un no aplicable no tienen severidad
    porque no hay fallo que graduar: el caso no se ha llegado a ejercitar, y
    asignarle un riesgo sería contarlo como si hubiera salido mal.
    """
    grupos = {s: [] for s in ORDEN_SEVERIDAD}
    sin_declarar = []
    for n, caso in sorted(ev["casos"].items()):
        if caso["resultado"] != "no_pasa":
            continue
        sev = severidad_de(ficha, n)
        destino = grupos[sev] if sev in grupos else sin_declarar
        destino.append({"caso": n, "titulo": ficha["casos"].get(n, ""),
                        "esperado": caso.get("esperado"),
                        "observado": caso.get("observado"),
                        "detalle": caso["observacion"]})
    return {"grupos": grupos, "sin_declarar": sin_declarar,
            "peor": next((s for s in ORDEN_SEVERIDAD if grupos[s]), None)}


def cobertura_severidad(ficha, ev):
    """
    Cuántos casos llevan severidad declarada. Es la comprobación de que la
    plantilla está completa y no medio rellena: una columna con la mitad de los
    valores a «—» no es una plantilla, es una intención.
    """
    total = len(ev["casos"])
    declarados = sum(1 for n in ev["casos"] if severidad_de(ficha, n) in SEVERIDADES)
    desglosados = sum(1 for c in ev["casos"].values()
                      if c.get("esperado") and c.get("observado"))
    return {"total": total, "severidad": declarados, "desglose": desglosados,
            "completa": declarados == total and desglosados == total}


def a_markdown(ficha, er, ev, entradas=""):
    """La plantilla como documento, para adjuntar al correo del compañero."""
    f = filas(ficha, ev, entradas)
    r = er["resumen"]
    sev = fallos_por_severidad(ficha, ev)

    L = [f"# Plantilla de evaluación · {ficha['nombre']}", "",
         f"**Módulo evaluado:** {ficha['nombre']}"
         + (f" ({ficha['modulo_evaluado']})" if ficha.get("modulo_evaluado") else ""),
         f"**Responsable:** {er['responsable']}"
         + (f" · {er['empresa']}" if er.get("empresa") else ""),
         f"**Conexión:** {er.get('conexion', '')}",
         f"**Evaluado:** {er['sujeto']}",
         f"**Fecha:** {er['fecha']}",
         f"**Lectura de los documentos:** {er.get('modo_lectura', 'determinista')}",
         "",
         f"**Entradas de la evaluación:** {entradas or 'las declaradas en cada caso'}",
         "", "## Resultado por caso", "",
         "| " + " | ".join(COLUMNAS) + " |",
         "|" + "---|" * len(COLUMNAS)]

    for fila in f:
        L.append("| " + " | ".join(
            str(fila[c]).replace("|", "/").replace("\n", " ") for c in COLUMNAS) + " |")

    L += ["",
          f"**Superados:** {r['pasa']} de {r['con_evidencia']} casos verificados "
          f"({r['tasa']}%)  ",
          f"**Cobertura de la batería:** {r['cobertura']}% "
          f"({r['con_evidencia']} de {r['total']} casos ejercitados)  ",
          f"**Exhaustividad:** {ev['contraste']['exhaustividad']}%  ·  "
          f"**Precisión:** {ev['contraste']['precision']}%", ""]

    if any(sev["grupos"][s] for s in ORDEN_SEVERIDAD) or sev["sin_declarar"]:
        L += ["## Fallos por severidad", "",
              "*La severidad se declara al diseñar el caso, antes de ejecutarlo, y "
              "mide qué ocurre aguas abajo si el fallo pasa desapercibido — no "
              "cuánto molesta.*", ""]
        for s in ORDEN_SEVERIDAD:
            if not sev["grupos"][s]:
                continue
            nombre, criterio, _ = SEVERIDADES[s]
            L += [f"### {nombre}", "", f"*{criterio}*", ""]
            for x in sev["grupos"][s]:
                L.append(f"- **Caso {x['caso']} · {x['titulo']}**")
                if x["esperado"] and x["observado"]:
                    L.append(f"  - Esperado: {x['esperado']}")
                    L.append(f"  - Observado: {x['observado']}")
                L.append(f"  - {x['detalle']}")
            L.append("")
        if sev["sin_declarar"]:
            L += ["### Sin severidad declarada", "",
                  "*Estos casos fallan y su rama todavía no ha declarado qué pasa "
                  "aguas abajo si el fallo no se ve. Es una deuda del evaluador, no "
                  "del módulo.*", ""]
            for x in sev["sin_declarar"]:
                L.append(f"- Caso {x['caso']} · {x['titulo']}")
            L.append("")

    if er.get("requisitos"):
        L += ["## Qué falta para ejercitar la batería completa", "",
              "*No son defectos del módulo: son datos que el banco de pruebas "
              "todavía no tiene.*", "",
              "| # | Estado | Qué haría falta |", "|---|---|---|"]
        for q in er["requisitos"]:
            L.append(f"| {q['caso']} | {TEXTO[q['estado']]} | {q['requiere']} |")
        L.append("")

    cob = cobertura_severidad(ficha, ev)
    L += ["---", "",
          f"*Plantilla común del bloque de Evaluación y Calidad. Severidad "
          f"declarada en {cob['severidad']} de {cob['total']} casos; esperado y "
          f"observado desglosados en {cob['desglose']} de {cob['total']}.*"]
    return "\n".join(L)
