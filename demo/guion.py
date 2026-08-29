"""
Guion de la demo: el recorrido completo del sistema, módulo a módulo.

Es lo que pidió Fabián como producto final —una demo básica que recorra todos
los módulos— y está pensado para poder enseñarse sin subir nada a mano: los
documentos viven en `demo/datos/<módulo>/` y la respuesta del módulo, cuando la
tengo, va escrita en el propio paso.

Un paso que no puede ejecutarse no se maquilla: se enseña con el motivo. El
recorrido cuenta el estado real del sistema, incluidas las conexiones que
todavía no están probadas, y eso es exactamente lo que hay que poder defender.

No importa `streamlit`: `pruebas.py` ejecuta este mismo guion desde la línea de
órdenes, y así el veredicto que sale en la demo es comprobable fuera de la app.
"""

from pathlib import Path

import modulos
from modulos import auditoria, contradicciones, similitud, vigencia
from nucleo import pdf as P
from nucleo import veredicto as V

RAIZ = Path(__file__).resolve().parent / "datos"


PASOS = [
    {
        "id": "auditoria",
        "titulo": "Auditoría de pedidos · Juan Salas",
        "relato": (
            "El módulo compara la orden de fabricación contra los documentos de "
            "cliente del pedido 42805. El evaluador lee los mismos PDF, calcula por "
            "su cuenta qué discrepancias existen y contrasta. Es la única conexión "
            "probada de extremo a extremo."
        ),
        "respuesta": auditoria.EJEMPLO,
        "nota_datos": ("Los PDF del pedido no se versionan en el repositorio por ser "
                       "documentación de cliente. Colócalos en demo/datos/auditoria/ "
                       "para que el paso se ejecute."),
    },
    {
        "id": "vigencia",
        "titulo": "Vigencia documental · Martín de Lucas",
        "relato": (
            "Un contrato de arrendamiento real de RALSA, de ocho páginas escaneadas "
            "sin capa de texto, y la ficha que IAlert emite para él. El evaluador "
            "reconoce el documento por su cuenta, deduce de las cláusulas qué le "
            "corresponde y sólo entonces contrasta. Coinciden en el estado y en las "
            "fechas; se separan en tres cosas que no se ven mirando la fecha de "
            "vencimiento: la naturaleza de la prórroga, la fecha en la que hay que "
            "moverse, y que al documento le faltan dos páginas."
        ),
        "documentos": ["CONTRATO_ARRENDAMIENTO_CRED.pdf"],
        "respuesta": vigencia.SALIDA_IALERT_CRED,
        "nota_datos": ("Falta el contrato en demo/datos/vigencia/. Los seis contratos "
                       "sintéticos siguen disponibles en la pantalla de evaluación: "
                       "sirven para ejercitar la batería, pero de ellos no hay salida "
                       "del módulo con la que contrastar."),
    },
    {
        "id": "similitud",
        "titulo": "Similitud de proyectos · Álvaro Subias",
        "relato": (
            "Aquí no hay documentos que leer: el módulo entrega JSON. El evaluador "
            "recalcula la puntuación desde las señales y el peso declarados, rehace "
            "el orden, y decide por su cuenta qué proyectos son equivalentes al "
            "pedido mirando los parámetros que el propio módulo publica. Se enseña "
            "el caso reñido, que es el que el autor señala como más interesante: dos "
            "proyectos que no son equivalentes adelantan a uno que sí lo es."
        ),
        "fichero": "caso3_syn0052_distractores.json",
        "respuesta": None,
        "nota_datos": ("Falta el JSON de la consulta en demo/datos/similitud/."),
    },
    {
        "id": "contradicciones",
        "titulo": "Contradicciones y validación humana · Mencía Viñuelas",
        "relato": (
            "El contraste más limpio del sistema: la exportación trae en el mismo "
            "fichero los hechos extraídos de cada documento y las contradicciones "
            "que el módulo declara. El evaluador ignora la tabla de contradicciones "
            "y la recalcula desde los hechos. Aparece el fallo del caso 7, que no se "
            "ve mirando la contradicción sino los hechos: después de que una persona "
            "valide una de las dos fechas, la descartada sigue marcada como activa."
        ),
        "fichero": "export_PED1004.json",
        "respuesta": None,
        "nota_datos": ("Falta la exportación en demo/datos/contradicciones/."),
    },
    {
        "id": "gobernanza",
        "titulo": "Ontología y grafo organizativo · Pablo Morillas",
        "relato": ("Declarado y vacío: sin batería, sin datos y sin conexión "
                   "documentada con mi bloque. Aparece en el recorrido porque forma "
                   "parte del proyecto — omitirlo lo haría desaparecer del mapa, y el "
                   "mapa es justo lo que el recorrido tiene que contar."),
        "respuesta": None,
        "nota_datos": None,
    },
]


def documentos_de(id_modulo, solo=None):
    """
    PDF disponibles para ese paso de la demo, ya leídos.

    `solo` acota a unos ficheros concretos. Existe porque la carpeta de vigencia
    guarda dos cosas distintas: los seis contratos sintéticos, que sirven para
    probar la batería, y el contrato real de Martín, que es el único del que hay
    salida del módulo. El recorrido enseña el que se puede contrastar; los otros
    siguen disponibles en la pantalla de evaluación.
    """
    carpeta = RAIZ / id_modulo
    if not carpeta.is_dir():
        return []
    rutas = sorted(carpeta.glob("*.pdf"))
    if solo:
        quiere = {s.lower() for s in solo}
        rutas = [r for r in rutas if r.name.lower() in quiere]
    return [P.leer(r) for r in rutas]


def ejecutar_paso(paso, fecha_evaluacion=None):
    """
    Devuelve (estado, datos). `estado` es 'ejecutado', 'a_medias' o 'no_operativo',
    y el motivo viaja dentro de `datos` para que la interfaz lo enseñe tal cual.
    """
    rama = modulos.rama(paso["id"])
    ficha = rama.FICHA

    if not ficha.get("operativo"):
        return "no_operativo", {"ficha": ficha,
                                "motivo": ficha.get("pendiente", "Rama no operativa.")}

    if paso["id"] == "contradicciones":
        ruta = RAIZ / "contradicciones" / paso["fichero"]
        if not ruta.is_file():
            return "a_medias", {"ficha": ficha, "motivo": paso.get("nota_datos")}
        datos, avisos = contradicciones.interpretar(ruta.read_text(encoding="utf-8"))
        if datos is None:
            return "a_medias", {"ficha": ficha, "motivo": "; ".join(avisos)}
        esperados, ctx = contradicciones.verdad_de_campo(datos)
        ev = contradicciones.evaluar(esperados, ctx)
        er = V.evaluation_result(ficha, ev, contradicciones.sujeto(ctx))
        return "ejecutado", {"ficha": ficha, "ev": ev, "er": er, "avisos": avisos}

    docs = documentos_de(paso["id"], paso.get("documentos"))
    if not docs and paso["id"] != "similitud":
        return "a_medias", {"ficha": ficha,
                            "motivo": paso.get("nota_datos")
                                      or "No hay documentos para este paso."}

    if paso["id"] == "similitud":
        ruta = RAIZ / "similitud" / paso["fichero"]
        if not ruta.is_file():
            return "a_medias", {"ficha": ficha, "motivo": paso.get("nota_datos")}
        datos, avisos = similitud.interpretar(ruta.read_text(encoding="utf-8"))
        if datos is None:
            return "a_medias", {"ficha": ficha, "motivo": "; ".join(avisos)}
        # La tabla de contribuciones que Álvaro aportó el 27/08. Sin ella el caso
        # 11 no puede rehacer la ordenación y queda pendiente, que es lo correcto.
        _csv = RAIZ / "similitud" / "contribuciones_peso_semantico_0.csv"
        _contrib = None
        if _csv.is_file():
            try:
                _contrib = similitud.cargar_contribuciones(
                    _csv.read_text(encoding="utf-8"))
            except Exception:
                _contrib = None
        esperados, ctx = similitud.verdad_de_campo(datos, contribuciones=_contrib)
        ev = similitud.evaluar(esperados, ctx)
        er = V.evaluation_result(ficha, ev, similitud.sujeto(ctx))
        return "ejecutado", {"ficha": ficha, "ev": ev, "er": er, "avisos": avisos}

    if paso["id"] == "vigencia":
        esperados, ctx = vigencia.verdad_de_campo(docs, fecha_evaluacion)
        if not paso.get("respuesta"):
            return "a_medias", {"ficha": ficha, "esperados": esperados,
                                "motivo": paso.get("nota_datos")}
        reportados, avisos = vigencia.interpretar(paso["respuesta"])
        ev = vigencia.evaluar(esperados, reportados, fecha_evaluacion, contexto=ctx)
        er = V.evaluation_result(ficha, ev, vigencia.sujeto(esperados))
        return "ejecutado", {"ficha": ficha, "ev": ev, "er": er, "avisos": avisos}

    esperados, contexto = auditoria.verdad_de_campo(docs)
    reportados, avisos = auditoria.interpretar(paso["respuesta"])
    ev = auditoria.evaluar(esperados, reportados, contexto,
                           texto_respuesta=paso["respuesta"])
    er = V.evaluation_result(ficha, ev, auditoria.sujeto(contexto))
    return "ejecutado", {"ficha": ficha, "ev": ev, "er": er, "avisos": avisos}
