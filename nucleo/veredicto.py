"""
EvaluationResult: el objeto que emiten todas las ramas.

Es lo que hace que el sistema no sea una suma de validadores independientes.
Da igual que se esté evaluando una auditoría de pedidos o una clasificación de
vigencia documental: el producto final tiene la misma forma, las mismas dos
métricas y la misma regla de anclaje —cada aspecto a mejorar cita el caso de la
batería que lo evidencia—. Lo comparable no son los módulos, es el veredicto.
"""

from datetime import date

from .bateria import ETIQUETA_CASO, requisitos, resumen


def evaluation_result(ficha, ev, sujeto, fecha=None):
    """
    ficha  : metadatos de la rama (nombre, responsable, conexión, casos, aspectos)
    ev     : lo que devuelve `evaluar()` de la rama
    sujeto : qué se ha evaluado — el pedido 42805, el conjunto de seis documentos…
    """
    casos, c = ev["casos"], ev["contraste"]
    r = resumen(casos)
    uni, unis = ficha.get("unidad", ("unidad", "unidades"))

    if r["con_evidencia"] == 0:
        val = ("No es posible emitir valoración: ninguno de los casos diseñados ha "
               "podido ejecutarse con los documentos aportados.")
    else:
        val = (f"Sobre {sujeto}, el módulo supera {r['pasa']} de los "
               f"{r['con_evidencia']} casos verificados ({r['tasa']}%). ")
        if c["exhaustividad"] is not None:
            val += (f"Resuelve correctamente el {c['exhaustividad']}% de {unis} que "
                    f"el evaluador determina de forma independiente a partir de los "
                    f"documentos")
            val += (f", y el {c['precision']}% de lo que emite se sostiene "
                    f"documentalmente. " if c["precision"] is not None else ". ")
        val += ("La evaluación se apoya en salidas reales del módulo contrastadas "
                "contra los documentos de origen, no en casos construidos por el "
                "evaluador. ")
        if r["no_pasa"]:
            val += (f"Se ha identificado un fallo con evidencia directa. "
                    if r["no_pasa"] == 1 else
                    f"Se han identificado {r['no_pasa']} fallos con evidencia directa. ")
        if r["pendiente"]:
            val += (f"{'Queda un caso' if r['pendiente'] == 1 else 'Quedan ' + str(r['pendiente']) + ' casos'} "
                    f"pendiente{'' if r['pendiente'] == 1 else 's'} de un dato de esta "
                    f"misma ejecución, cuyo resultado no se presume en ningún sentido. ")
        if r["no_aplica"]:
            val += (f"Otro{'' if r['no_aplica'] == 1 else 's'} {r['no_aplica']} "
                    f"caso{'' if r['no_aplica'] == 1 else 's'} mide"
                    f"{'n' if r['no_aplica'] != 1 else ''} situaciones que este "
                    f"conjunto no contiene, así que no se ejercita"
                    f"{'n' if r['no_aplica'] != 1 else ''}: eso no dice nada del "
                    f"módulo, dice qué le falta al banco de pruebas. ")
        val += (f"La batería queda ejercitada al {r['cobertura']}%. "
                if r["cobertura"] is not None else "")
        n_h = len(ev.get("hallazgos", []))
        if n_h:
            val += (f"Con independencia de la batería, se "
                    f"{'registra' if n_h == 1 else 'registran'} {n_h} "
                    f"hallazgo{'' if n_h == 1 else 's'} de cobertura: comprobaciones "
                    f"que el módulo no contempla y para las que el evaluador "
                    f"demuestra que había algo que encontrar.")

    # Un caso no aplicable no genera aspecto a mejorar: no hay nada que el módulo
    # haya hecho mal. Genera un requisito de datos, que va aparte.
    prioridad = {"no_pasa": 0, "pendiente": 1, "no_aplica": 2, "pasa": 3}
    aspectos = []
    for n, caso in sorted(casos.items(), key=lambda kv: (prioridad[kv[1]["resultado"]], kv[0])):
        if caso["resultado"] in ("pasa", "no_aplica") or n not in ficha["aspectos"]:
            continue
        titulo, correccion = ficha["aspectos"][n]
        aspectos.append({"titulo": titulo, "caso": n, "nombre_caso": ficha["casos"][n],
                         "estado": caso["resultado"], "detalle": caso["observacion"],
                         "correccion": correccion})

    return {"modulo": ficha["nombre"], "responsable": ficha["responsable"],
            "empresa": ficha.get("empresa", ""), "conexion": ficha.get("conexion", ""),
            "sujeto": sujeto, "fecha": (fecha or date.today()).strftime("%d/%m/%Y"),
            "modo_lectura": ev.get("modo_lectura", "determinista"),
            "resumen": r, "valoracion": val, "aspectos": aspectos,
            "requisitos": requisitos(casos)}


def a_markdown(ficha, er, ev, panel=None):
    r, c = er["resumen"], ev["contraste"]
    uni, unis = ficha.get("unidad", ("unidad", "unidades"))

    L = ["# EvaluationResult", "",
         f"## {er['modulo']} — {er['responsable']}"
         + (f" · {er['empresa']}" if er["empresa"] else ""), "",
         f"**Conexión evaluada:** {er['conexion']}",
         f"**Evaluado:** {er['sujeto']}",
         f"**Fecha:** {er['fecha']}",
         f"**Lectura de los documentos:** {er['modo_lectura']}",
         "**Origen de los datos:** salida real del módulo, contrastada contra los "
         "documentos de origen", "",
         "| | |", "|---|---|",
         f"| Casos diseñados | {r['total']} |",
         f"| Casos con evidencia | {r['con_evidencia']} |",
         f"| Superados | {r['pasa']} |",
         f"| Fallidos | {r['no_pasa']} |",
         f"| Pendientes de un dato de esta ejecución | {r['pendiente']} |",
         f"| No aplicables a este conjunto | {r['no_aplica']} |",
         f"| Cobertura de la batería | {r['cobertura']}% |",
         f"| Exhaustividad | {c['exhaustividad']}% |",
         f"| Precisión | {c['precision']}% |", "",
         f"*Exhaustividad: de {unis} que el evaluador determina por su cuenta, "
         f"cuántos resolvió correctamente el módulo. Precisión: de lo que el módulo "
         f"emitió, cuánto se sostiene documentalmente. Lo que señala la unidad "
         f"correcta pero cita valores erróneos no computa en ninguna de las dos.*", "",
         "## Valoración", "", er["valoracion"], ""]

    if ev.get("tabla_contraste"):
        cols = list(ev["tabla_contraste"][0].keys())
        L += ["## Contraste independiente", "",
              "| " + " | ".join(cols) + " |",
              "|" + "---|" * len(cols)]
        for fila in ev["tabla_contraste"]:
            L.append("| " + " | ".join(str(fila[k]) for k in cols) + " |")
        L.append("")

    if ev.get("hallazgos"):
        L += ["## Hallazgos de cobertura", "",
              "*Comprobaciones que el módulo no realiza y que el evaluador sí. No "
              "puntúan en la batería: no realizar una comprobación no equivale a "
              "realizarla mal.*", ""]
        for h in ev["hallazgos"]:
            L += [f"### {h['titulo']}", "", h["detalle"], "",
                  f"**Por qué importa:** {h['porque_importa']}", ""]
            if h.get("tabla"):
                cols = list(h["tabla"][0].keys())
                L += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
                for fila in h["tabla"]:
                    L.append("| " + " | ".join(str(fila[k]) for k in cols) + " |")
                L.append("")

    L += ["## Resultado caso a caso", "",
          "| # | Caso | Resultado | Observación |", "|---|---|---|---|"]
    for n, caso in sorted(ev["casos"].items()):
        L.append(f"| {n} | {ficha['casos'][n]} | {caso['resultado'].replace('_', ' ')} | "
                 f"{caso['observacion']} |")
    L.append("")

    if panel and panel.get("criterios"):
        from .jueces import TEXTO as T_CRIT
        from .jueces import texto_panel
        L += ["## Criterios cualitativos", "",
              "*Lo que ninguna regla puede comprobar, sometido a un panel de jueces "
              "independientes. Se puntúa sólo donde el panel coincide; donde "
              "discrepa, la discrepancia se declara en vez de resolverse. Estos "
              "criterios no alteran las métricas deterministas de arriba.*", "",
              texto_panel(panel), "",
              "| Criterio | Veredicto | Acuerdo | Justificación |",
              "|---|---|---|---|"]
        for c in panel["criterios"]:
            just = (c["justificacion"] or "—").replace("|", "/").replace("\n", " ")
            L.append(f"| {c['titulo']} | {T_CRIT[c['veredicto']]} | "
                     f"{int(c['acuerdo'] * 100)}% | {just} |")
        L.append("")
        if panel.get("requisitos"):
            L += ["**Pendiente de arbitraje**", ""]
            for q in panel["requisitos"]:
                L.append(f"- {q['criterio']}: {q['requiere']}")
            L.append("")

    if er.get("requisitos"):
        L += ["## Qué falta para ejercitar la batería completa", "",
              "*Ninguno de estos puntos es un defecto del módulo: son datos que el "
              "banco de pruebas todavía no tiene.*", "",
              "| # | Estado | Qué haría falta |", "|---|---|---|"]
        for q in er["requisitos"]:
            L.append(f"| {q['caso']} | {q['estado'].replace('_', ' ')} | "
                     f"{q['requiere']} |")
        L.append("")

    if er["aspectos"]:
        L += ["## Aspectos a mejorar", ""]
        for i, a in enumerate(er["aspectos"], 1):
            L += [f"### {i}. {a['titulo']}",
                  f"*Caso {a['caso']} · {a['nombre_caso']} · {ETIQUETA_CASO[a['estado']]}*",
                  "", a["detalle"], "",
                  f"**Corrección propuesta:** {a['correccion']}", ""]

    L += ["---", "",
          "*Cada aspecto a mejorar queda anclado al caso de la batería que lo "
          "evidencia. Un caso **pendiente** está diseñado y no ejecutado por falta "
          "de un dato de esta misma ejecución; uno **no aplicable** mide una "
          "situación que este conjunto no contiene. Ninguno de los dos computa a "
          "favor ni en contra del módulo evaluado.*"]
    return "\n".join(L)
