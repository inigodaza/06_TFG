"""
Contraste: el corazón del núcleo.

El evaluador no se fía de lo que reporta el módulo. Cada rama calcula por su
cuenta, leyendo los documentos, qué debería haber salido —los `esperados`—, y
sólo entonces se contrasta contra lo que el módulo emitió —los `reportados`—.

De ahí salen las dos magnitudes del veredicto, idénticas en todas las ramas:

  exhaustividad : de lo que había que resolver, cuánto resolvió correctamente
  precisión     : de lo que emitió, cuánto se sostiene documentalmente

Señalar la unidad correcta no basta. Si lo emitido cita valores que contradicen
los documentos, no computa como acierto y además resta precisión: un aviso con
los datos equivocados no es información utilizable aguas abajo.
"""


def contrastar(esperados, reportados, clave, comparar):
    """
    esperados  : lista de dicts calculada por la rama a partir de los documentos
    reportados : lista de dicts con lo que emitió el módulo, ya interpretado
    clave(x)   : identidad de la unidad evaluada — el campo en la auditoría de
                 pedidos, el identificador de documento en vigencia documental
    comparar(esperado, reportado) -> (bool, str)
                 ¿se sostiene lo reportado? y, si no, por qué. El motivo se
                 arrastra hasta el veredicto para que el fallo quede anclado.

    Devuelve el mismo diccionario sea cual sea la rama.
    """
    esp_por_clave = {clave(e): e for e in esperados}

    # Primera aparición de cada clave; las siguientes son repetición y no aportan.
    primera, repetidas = {}, set()
    for pos, r in enumerate(reportados):
        k = clave(r)
        if k in primera:
            repetidas.add(pos)
        else:
            primera[k] = pos

    detectadas, con_error, omitidas, motivos = [], [], [], []
    for e in esperados:
        pos = primera.get(clave(e))
        if pos is None:
            omitidas.append(e)
            continue
        ok, motivo = comparar(e, reportados[pos])
        if ok:
            detectadas.append(e)
        else:
            con_error.append(e)
            motivos.append({"clave": clave(e), "motivo": motivo,
                            "esperado": e, "reportado": reportados[pos]})

    falsas_pos = [pos for pos, r in enumerate(reportados)
                  if pos not in repetidas and clave(r) not in esp_por_clave]
    falsas = [reportados[p] for p in falsas_pos]
    duplicadas = [reportados[p] for p in sorted(repetidas)]

    n = len(reportados)
    # Se sostiene lo que ni es falso, ni contradice los documentos, ni repite
    # algo ya emitido.
    sostenidas = n - len(falsas) - len(con_error) - len(duplicadas)

    return {
        "detectadas": detectadas,
        "con_error": con_error,
        "omitidas": omitidas,
        "falsas": falsas,
        "duplicadas": duplicadas,
        "motivos": motivos,
        "n_esperados": len(esperados),
        "n_reportados": n,
        "exhaustividad": (round(100 * len(detectadas) / len(esperados), 1)
                          if esperados else None),
        "precision": round(100 * sostenidas / n, 1) if n else None,
    }


ETIQUETAS_ESTADO = {"si": "Sí", "error": "Con valores erróneos", "no": "No"}


def estado_de(unidad, contraste, etiquetas=None):
    """Etiqueta legible del resultado de una unidad esperada, para las tablas."""
    e = {**ETIQUETAS_ESTADO, **(etiquetas or {})}
    if unidad in contraste["detectadas"]:
        return e["si"]
    if unidad in contraste["con_error"]:
        return e["error"]
    return e["no"]
