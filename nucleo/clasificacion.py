"""
De qué tipo es cada documento, y quién lo ha decidido.

Por qué existe
--------------
Cada rama trae su `clasificar()`, que busca frases literales: «orden de
fabricacion», «quantity:», «please find herewith our prices». Funciona con los
documentos con los que se escribió y **con ninguno más**. Un pedido del mismo
cliente redactado de otra forma sale «No identificado», y a partir de ahí el
documento no entra en la evaluación aunque se haya leído perfectamente. Íñigo lo
vio metiendo dos órdenes nuevas en el módulo de Juan: el sistema las leía y no
sabía qué eran.

Enumerar frases es perseguir documentos. Pero sustituir la regla por el modelo
sería peor: el clasificador determinista es reproducible, gratis e inspeccionable,
y donde acierta no hay ninguna razón para preguntarle a nadie.

La regla, entonces, es la misma que gobierna todo lo demás en este sistema:

    **La regla decide donde llega. El modelo entra sólo donde la regla se rinde,
    y lo que aporta queda marcado como suyo.**

Cada documento sale de aquí con cuatro cosas: el tipo, **por qué vía** se ha
decidido, con cuánta confianza, y la cita que lo sostiene. Un veredicto que
dependa de un tipo puesto por el modelo tiene que poder decirlo.
"""

from nucleo import llm

# Los tipos que significan «no lo sé», y que por tanto abren la puerta al modelo.
SIN_DECIDIR = ("desconocido", "sin_texto", None, "")

VIAS = {
    "regla": "Identificado por la regla de la rama",
    "modelo": "Identificado por el modelo, con cita verificada",
    "ninguna": "Sin identificar",
}


def anotar_tipos(docs, clasificar, tipos, modo="determinista",
                 permiso=None):
    """
    Escribe en cada documento `tipo`, `tipo_via`, `tipo_confianza` y `tipo_cita`.

    Devuelve (docs, avisos). Los avisos recogen lo que el modelo ha aportado y lo
    que no ha podido decidir, para que aparezca en pantalla en vez de colarse en
    el veredicto sin que nadie lo vea.

    No lanza: si la lectura asistida falla, el documento se queda sin identificar
    —que es lo que ya le pasaba antes— y se dice por qué.
    """
    avisos = []
    for d in docs:
        texto = d.get("texto") or ""
        legible = d.get("legible", d.get("capa"))
        tipo = clasificar(texto) if legible else "sin_texto"
        d["tipo"] = tipo
        d["tipo_via"] = "regla" if tipo not in SIN_DECIDIR else "ninguna"
        d["tipo_confianza"] = 1.0 if tipo not in SIN_DECIDIR else 0.0
        d["tipo_cita"] = None

        if tipo not in SIN_DECIDIR or not legible or modo == "determinista":
            continue

        try:
            propuesto, confianza, por_que = llm.clasificar_con_llm(
                texto, tipos, permiso=permiso)
        except llm.Vetada as e:
            # No es un fallo: es una decisión declarada. Se dice una
            # sola vez y se sigue en determinista.
            if not any("cerrada" in a for a in avisos):
                avisos.append(f"La lectura asistida está cerrada en esta "
                              f"rama, así que los documentos que la regla "
                              f"no reconoce se quedan sin identificar. {e}")
            continue
        except llm.NoDisponible as e:
            avisos.append(f"{d['nombre']}: la regla no lo reconoce y la lectura "
                          f"asistida no está disponible. {e}")
            continue
        except Exception as e:                      # noqa: BLE001
            avisos.append(f"{d['nombre']}: la regla no lo reconoce y el intento "
                          f"asistido ha fallado ({e}).")
            continue

        if not propuesto:
            avisos.append(f"{d['nombre']}: sigue sin identificar — {por_que}.")
            continue

        # Las mismas dos garantías, comprobadas aquí otra vez.
        #
        # Ya las aplica `llm.clasificar_con_llm`, y aun así se repiten. No es
        # desconfianza del código de al lado: es que quien acepta el valor es
        # esta función, y una garantía que depende de que otro la haya
        # comprobado deja de ser una garantía en cuanto alguien añade un segundo
        # camino de entrada. Lo destapó una prueba con un modelo simulado que
        # devolvía una cita inventada: pasó entera, porque el guardia estaba en
        # la puerta por la que esa prueba no entraba.
        if propuesto not in tipos:
            avisos.append(f"{d['nombre']}: el modelo propone un tipo que no "
                          f"existe en esta rama ({propuesto}). No se acepta.")
            continue
        if confianza < llm.CONFIANZA_MINIMA_TIPO:
            avisos.append(
                f"{d['nombre']}: el modelo propone «{tipos[propuesto]}» con "
                f"confianza {confianza:.2f}, por debajo del mínimo de "
                f"{llm.CONFIANZA_MINIMA_TIPO}. Se queda sin identificar: aquí "
                f"equivocarse cuesta más que abstenerse, porque un documento mal "
                f"clasificado entra en una comparación que no le corresponde y el "
                f"fallo aparece disfrazado de discrepancia del módulo.")
            continue
        anclada = bool(por_que) and llm.fragmento_presente(por_que, texto)[0]
        if not anclada:
            avisos.append(
                f"{d['nombre']}: el modelo propone «{tipos[propuesto]}» pero la "
                f"cita que da no aparece en el documento. No se acepta un tipo "
                f"que no se puede anclar al texto.")
            continue

        d["tipo"] = propuesto
        d["tipo_via"] = "modelo"
        d["tipo_confianza"] = confianza
        d["tipo_cita"] = por_que
        avisos.append(
            f"**{d['nombre']}** lo ha identificado el modelo como "
            f"«{tipos.get(propuesto, propuesto)}» (confianza {confianza:.2f}), "
            f"porque la regla de la rama no lo reconocía. Lo sostiene esta cita "
            f"del propio documento: «{str(por_que)[:180]}». "
            f"El tipo puesto por el modelo se declara en el veredicto.")
    return docs, avisos


def tipo_de(doc, clasificar):
    """
    El tipo ya anotado, o el que dé la regla si nadie ha pasado por aquí.

    Existe para que las ramas puedan leer `tipo_de(d, clasificar)` sin tener que
    saber si la anotación se ha hecho. Una rama no debería comportarse distinto
    según por dónde la hayan llamado.
    """
    if doc.get("tipo"):
        return doc["tipo"]
    legible = doc.get("legible", doc.get("capa"))
    return clasificar(doc.get("texto") or "") if legible else "sin_texto"


def resumen(docs):
    """Cuántos ha decidido cada quién. Para poder enseñarlo sin recalcular."""
    return {
        "por_regla": sum(1 for d in docs if d.get("tipo_via") == "regla"),
        "por_modelo": sum(1 for d in docs if d.get("tipo_via") == "modelo"),
        "sin_identificar": sum(1 for d in docs if d.get("tipo_via") == "ninguna"),
    }
