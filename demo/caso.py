"""
El caso, ejecutado: una incongruencia recorriendo los cuatro trabajos.

Qué cambia respecto a la versión anterior
------------------------------------------
Antes había dos pantallas. Una —«El hilo»— **contaba** el recorrido con un texto
escrito a mano: bonito de leer y muerto, porque decía lo mismo con datos que sin
ellos. Otra —«Demo»— ejecutaba las baterías módulo a módulo, pero cada módulo por
su lado, de modo que no se veía que fueran partes del mismo caso.

Esto es una sola cosa y se ejecuta: entran la orden de fabricación y el pedido de
cliente, y de ahí sale todo lo demás. Ninguna de las cuatro fases escribe un
resultado a mano; todas lo calculan o declaran que no pueden.

Las cuatro fases
-----------------
    OBSERVAR   `observar()`   ¿hay discrepancia, y la vio el módulo de Juan?
    GOBERNAR   `gobernar()`   ¿de quién es la decisión, según la matriz de Pablo?
    DECIDIR    `decidir()`    ¿quién validó, y conservó el módulo de Mencía la decisión?
    COMPROBAR  `comprobar()`  ¿el conjunto se sostiene, y qué queda abierto?

Aquí no se importa Streamlit a propósito. Todo lo que decide algo vive en este
fichero y se puede comprobar desde `pruebas.py` sin abrir la interfaz; `app.py`
sólo pinta lo que estas funciones devuelven. Si la lógica viviera dentro de la
pantalla, el recorrido de la demo sería lo único del sistema que nadie comprueba.
"""

import re

from nucleo import autoridad as AUT


def numero_de_pedido(contexto):
    """
    El número del pedido, sacado del nombre de la orden: `of42805.pdf` → 42805.

    Devuelve `None` cuando no hay ninguno reconocible, y entonces la pantalla
    dice «este pedido» en vez de inventarse una referencia. Pedirle a Mencía «la
    exportación del pedido EJEMPLO_orden_de_fabricacion» sería una petición que
    nadie puede atender.
    """
    m = re.search(r"(\d{4,})", str((contexto or {}).get("pedido") or ""))
    return m.group(1) if m else None

# ---------------------------------------------------------------------------
# La pieza que falta, escrita donde se ve
# ---------------------------------------------------------------------------
# De qué ámbito es cada CAMPO de un pedido. Pablo tiene rol → área. Mencía tiene
# contradicción → categoría. Esto de en medio no lo tiene nadie, así que mientras
# no lo escriba Pablo **no se elige una lectura: se enseñan las dos**.
#
# No es una cautela teórica. En el campo `cantidad` las dos lecturas dan
# responsables distintos, y por tanto veredictos distintos sobre si quien validó
# tenía autoridad. Ésa es exactamente la pregunta que ningún módulo puede
# contestar solo, y hoy el evaluador tampoco puede cerrarla: puede enseñar que
# está abierta, que ya es más de lo que hacía nadie.
LECTURAS_DE_CAMPO = {
    "cantidad": [
        ("produccion",
         "Mencía la etiqueta así en su exportación: una cantidad es cosa de planta"),
        ("comercial",
         "la matriz de Pablo pone «la gestión de clientes y pedidos de producción» "
         "bajo Admin. Comerciales, que es Área Comercial"),
    ],
    "fecha_entrega": [
        ("produccion",
         "coinciden los dos: Mencía la etiqueta como producción y la matriz de "
         "Pablo da a Dir. Producción «la operativa y las fechas de entrega»"),
    ],
    "precio": [
        ("financiera",
         "es un importe; la matriz da a Dir. Financiera «presupuestos, cuentas e "
         "informes económicos»"),
        ("comercial",
         "pero también es una condición de venta, y la matriz da a Dir. Comercial "
         "«las estrategias de venta, ofertas y cuentas de clientes»"),
    ],
}


# ---------------------------------------------------------------------------
# 1 · OBSERVAR
# ---------------------------------------------------------------------------

def observar(esperados, reportados):
    """
    ¿Qué discrepancias hay de verdad, y cuáles vio el módulo de Juan?

    `esperados` lo ha calculado el evaluador leyendo los PDF; `reportados` es lo
    que dice el módulo. Aquí no se puntúa nada —de eso ya se encarga la batería
    de la rama— sino que se emparejan las dos listas para poder enseñar, campo a
    campo, quién dice qué.
    """
    por_campo = {r.get("campo"): r for r in (reportados or []) if r.get("campo")}
    vistas, no_vistas = [], []
    for e in esperados or []:
        r = por_campo.get(e["campo"])
        (vistas if r else no_vistas).append({**e, "reportada": r})

    campos_reales = {e["campo"] for e in esperados or []}
    inventadas = [r for c, r in por_campo.items() if c not in campos_reales]

    # La discrepancia que conduce el recorrido es la más grave de las que
    # existen de verdad. Si el módulo no vio ninguna, el hilo sigue igual: lo
    # que se sigue es el hecho, no el acierto del módulo.
    orden = {"critica": 0, "alta": 1, "media": 2}
    candidatas = sorted(esperados or [],
                        key=lambda e: orden.get(e.get("severidad_esperada"), 9))
    principal = candidatas[0] if candidatas else None

    return {
        "discrepancias": esperados or [],
        "vistas": vistas,
        "no_vistas": no_vistas,
        "inventadas": inventadas,
        "principal": principal,
        "hay_caso": bool(principal),
    }


# ---------------------------------------------------------------------------
# 2 · GOBERNAR
# ---------------------------------------------------------------------------

def gobernar(discrepancia, onto=None):
    """
    ¿De quién es esta decisión?

    Devuelve una lectura por cada ámbito al que se podría atribuir el campo, con
    los roles que mandan sobre cada uno. Si las lecturas no coinciden, se declara
    el desacuerdo en vez de escoger: escoger en silencio convertiría una
    suposición del evaluador en un veredicto sobre el trabajo de otro.
    """
    onto = onto if onto is not None else AUT.cargar()
    if not discrepancia:
        return {"disponible": False,
                "motivo": "No hay ninguna discrepancia sobre la que decidir."}
    if not onto:
        return {"disponible": False,
                "motivo": "No hay matriz de autoridad cargada.",
                "requiere": "la matriz de Pablo en "
                            "`referencia/ontologia_autoridad.json`"}

    campo = discrepancia["campo"]
    crudas = LECTURAS_DE_CAMPO.get(campo)
    if not crudas:
        return {"disponible": False, "campo": campo,
                "motivo": f"Nadie ha declarado de qué ámbito es «{campo}».",
                "requiere": "el mapa campo → ámbito, escrito por Pablo"}

    lecturas = []
    for categoria, por_que in crudas:
        manda = AUT.quien_manda_sobre(categoria, onto)
        lecturas.append({
            "categoria": categoria,
            "area": AUT.area_de(categoria),
            "por_que": por_que,
            "manda": [r["rol"] for r in manda],
        })

    responsables = {tuple(l["manda"]) for l in lecturas}
    return {
        "disponible": True,
        "campo": campo,
        "etiqueta": discrepancia.get("etiqueta", campo),
        "lecturas": lecturas,
        "acuerdo": len(responsables) == 1,
        "confirmada": AUT.confirmada(onto),
        "categorias_confirmadas": AUT.categorias_confirmadas(),
        "requiere": (None if len(responsables) == 1 else
                     "el mapa campo → ámbito, escrito por Pablo: las dos "
                     "lecturas dan responsables distintos y el veredicto de "
                     "autoridad depende entera de cuál valga"),
    }


# ---------------------------------------------------------------------------
# 3 · DECIDIR
# ---------------------------------------------------------------------------

def decidir(gobierno, datos_antes=None, datos_despues=None, pedido=None):
    """
    ¿Quién validó la discrepancia, y tenía autoridad para hacerlo?

    Necesita la exportación de Mencía **para este pedido**. Sin ella el paso no
    se inventa: queda pendiente y dice qué le falta. Con ella, cruza quién
    resolvió contra cada una de las lecturas de la fase anterior — y si las
    lecturas discrepaban, el cruce hereda el desacuerdo, que es justamente lo que
    hay que enseñar.
    """
    estado = datos_despues or datos_antes
    if not estado:
        cual = f"el pedido {pedido}" if pedido else "este pedido"
        return {"disponible": False,
                "motivo": "No hay exportación del módulo de validación.",
                "requiere": (f"la exportación de Mencía para {cual}, antes y "
                             f"después de resolver la contradicción")}

    resueltas = [c for c in (estado.get("contradicciones") or [])
                 if c.get("resolucion")]
    if not resueltas:
        return {"disponible": True, "resueltas": [], "veredictos": [],
                "motivo": "La exportación no trae ninguna contradicción resuelta, "
                          "así que no hay ninguna validación cuya autoridad "
                          "comprobar.",
                "requiere": "una exportación posterior a la validación"}

    lecturas = (gobierno or {}).get("lecturas") or []
    veredictos = []
    for c in resueltas:
        quien = (c["resolucion"] or {}).get("revisor")
        por_lectura = []
        for l in lecturas:
            podia, motivo = AUT.tiene_autoridad(quien, l["categoria"])
            por_lectura.append({"categoria": l["categoria"], "area": l["area"],
                                "podia": podia, "motivo": motivo})
        respuestas = {p["podia"] for p in por_lectura}
        veredictos.append({
            "campo": c.get("campo"),
            "revisor": quien,
            "por_lectura": por_lectura,
            # `None` no es «no tenía autoridad»: es «no se puede saber».
            "concluyente": len(respuestas) == 1 and None not in respuestas,
            "podia": por_lectura[0]["podia"] if len(respuestas) == 1 else None,
        })

    ambiguos = [v for v in veredictos if not v["concluyente"]]
    return {
        "disponible": True,
        "resueltas": resueltas,
        "veredictos": veredictos,
        "hay_comparacion": bool(datos_antes and datos_despues),
        "requiere": (None if not ambiguos else
                     "el mapa campo → ámbito: con una lectura la validación es "
                     "válida y con la otra no, y el evaluador no puede elegir "
                     "por Pablo"),
    }


# ---------------------------------------------------------------------------
# 4 · COMPROBAR
# ---------------------------------------------------------------------------

def comprobar(observacion, gobierno, decision):
    """
    Qué se ha podido establecer con estos datos y qué sigue abierto.

    Devuelve el estado de cada fase —`ejecutada`, `parcial` o `pendiente`— y la
    lista de lo que falta, con su dueño. La lista no se escribe: se recoge de lo
    que cada fase ha declarado que le falta, que es la única manera de que no se
    quede obsoleta en cuanto lleguen los datos.
    """
    fases = [
        {"fase": "OBSERVAR", "responsable": "Juan Salas",
         "estado": "ejecutada" if observacion.get("hay_caso") else "pendiente",
         "requiere": (None if observacion.get("hay_caso") else
                      "documentos en los que exista alguna discrepancia")},
        {"fase": "GOBERNAR", "responsable": "Pablo Morillas",
         "estado": ("ejecutada" if gobierno.get("acuerdo")
                    else "parcial" if gobierno.get("disponible") else "pendiente"),
         "requiere": gobierno.get("requiere") or gobierno.get("motivo")
                     if not gobierno.get("acuerdo") else None},
        {"fase": "DECIDIR", "responsable": "Mencía Viñuelas",
         "estado": ("ejecutada" if decision.get("disponible")
                    and not decision.get("requiere") else
                    "parcial" if decision.get("disponible") else "pendiente"),
         "requiere": decision.get("requiere") or decision.get("motivo")
                     if decision.get("requiere") or not decision.get("disponible")
                     else None},
        {"fase": "COMPROBAR", "responsable": "Íñigo Daza",
         "estado": "ejecutada", "requiere": None},
    ]
    pendientes = [f for f in fases if f["estado"] != "ejecutada"]
    return {
        "fases": fases,
        "pendientes": pendientes,
        "completo": not pendientes,
        # El hilo se recorre entero sólo si ninguna fase se queda a medias. Que
        # esto se calcule —en vez de escribirse— es lo que impide que la pantalla
        # afirme un recorrido que los datos no sostienen.
        "recorrido": sum(1 for f in fases if f["estado"] == "ejecutada"),
        "total": len(fases),
    }


REGLA = ("Ninguna discrepancia se convierte en verdad sin evidencia, autoridad "
         "y evaluación.")
