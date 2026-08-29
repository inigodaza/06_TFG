"""
Esquema del sistema, dibujado en SVG a partir del registro de módulos.

Sustituye a la antigua tabla de conexiones. Una tabla con seis filas no explica
qué hace cada módulo ni por dónde circula un dato; este esquema sí, y además se
mantiene solo: si mañana añado una rama a `modulos/`, aparece aquí sin tocar
nada.

Lo que cuenta el dibujo, de izquierda a derecha: de qué documentos parte cada
módulo, qué hace cada uno, y cómo su salida entra en el bloque de Evaluación y
Calidad, que la contrasta contra los mismos documentos de origen.

El estado de la conexión va en el color **y** en el trazo **y** en la palabra:
continuo para probada, continuo fino para documentada, discontinuo para sin
documentar. El color acompaña, no carga solo con el significado.
"""

import html

import modulos

ANCHO = 1120
X_ENTRADA, W_ENTRADA = 24, 210
X_MOD, W_MOD = 298, 430
X_EVAL, W_EVAL = 790, 306
Y0 = 104
ALTO_CAJA, HUECO = 84, 14

TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_3 = "#898781"
BORDE = "rgba(11,11,11,.12)"
LINEA = "#e1e0d9"
ACENTO = "#2a78d6"

TRAZO = {
    "probada": {"color": "#0ca30c", "ancho": 2.4, "guion": "none"},
    "documentada": {"color": "#2a78d6", "ancho": 1.8, "guion": "none"},
    "sin documentar": {"color": "#898781", "ancho": 1.6, "guion": "6 5"},
}

ENTRADAS = [
    "Documentos del pedido",
    "Contratos y escrituras",
    "Histórico de proyectos",
    "Hechos extraídos y su revisión",
    "Entidades de la organización",
]

PASOS_EVALUADOR = [
    ("Extracción", "campos de cada documento"),
    ("Verdad de campo", "qué debería haber salido, calculado sin mirar al módulo"),
    ("Contraste", "exhaustividad y precisión"),
    ("Batería", "casos superados, fallidos y pendientes"),
    ("Panel de jueces", "lo cualitativo, sólo donde coinciden"),
    ("Informe", "redactado y con las cifras verificadas"),
]


def _e(t):
    return html.escape(str(t))


def _lineas(texto, ancho):
    """Parte un texto en líneas de como mucho `ancho` caracteres, por palabras."""
    palabras, filas, actual = str(texto).split(), [], ""
    for p in palabras:
        if len(actual) + len(p) + 1 > ancho:
            filas.append(actual)
            actual = p
        else:
            actual = f"{actual} {p}".strip()
    if actual:
        filas.append(actual)
    return filas


def _texto(x, y, texto, tam=12, color=TINTA_2, peso=400, ancho=None, interlinea=15):
    if ancho is None:
        return (f'<text x="{x}" y="{y}" font-size="{tam}" fill="{color}" '
                f'font-weight="{peso}">{_e(texto)}</text>')
    partes = _lineas(texto, ancho)
    tspans = "".join(f'<tspan x="{x}" dy="{0 if i == 0 else interlinea}">{_e(l)}</tspan>'
                     for i, l in enumerate(partes))
    return (f'<text x="{x}" y="{y}" font-size="{tam}" fill="{color}" '
            f'font-weight="{peso}">{tspans}</text>')


def _caja(x, y, w, h, relleno="#ffffff", borde=BORDE, radio=11, guion=None, ancho=1):
    d = f' stroke-dasharray="{guion}"' if guion else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radio}" '
            f'fill="{relleno}" stroke="{borde}" stroke-width="{ancho}"{d}/>')


def _columna(x, w, titulo):
    return _texto(x, 74, titulo.upper(), tam=11, color=ACENTO, peso=700)


def dibujar():
    fichas = modulos.fichas()
    n = len(fichas)
    alto_bloque = n * ALTO_CAJA + (n - 1) * HUECO
    # La columna del evaluador crece con sus pasos, así que el panel es el más
    # alto de los dos: si no, añadir un paso al núcleo desbordaría el dibujo.
    alto_panel = max(alto_bloque,
                     42 + len(PASOS_EVALUADOR) * 76 + 70 + 62)
    alto = Y0 + alto_panel + 96

    p = [f'<svg viewBox="0 0 {ANCHO} {alto}" width="100%" '
         f'xmlns="http://www.w3.org/2000/svg" role="img" '
         f'aria-label="Esquema del sistema de evaluación" '
         f'font-family="system-ui, -apple-system, Segoe UI, sans-serif">']

    # Marcadores de flecha, uno por estado
    p.append("<defs>")
    for estado, t in TRAZO.items():
        ident = estado.replace(" ", "-")
        p.append(f'<marker id="f-{ident}" viewBox="0 0 10 10" refX="9" refY="5" '
                 f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
                 f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{t["color"]}"/></marker>')
    p.append(f'<marker id="f-neutro" viewBox="0 0 10 10" refX="9" refY="5" '
             f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
             f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{TINTA_3}"/></marker>')
    p.append("</defs>")

    p.append(f'<text x="24" y="34" font-size="17" font-weight="650" fill="{TINTA}">'
             f'Cómo circula un dato por el sistema</text>')
    p.append(_texto(24, 54, "Cada módulo del equipo produce una salida; el bloque de "
                            "Evaluación y Calidad la contrasta contra los mismos "
                            "documentos de origen.", tam=12.5, color=TINTA_2))

    # --- Columna 1: origen de los datos
    p.append(_columna(X_ENTRADA, W_ENTRADA, "Origen de los datos"))
    p.append(_caja(X_ENTRADA, Y0, W_ENTRADA, alto_bloque, relleno="#f9f9f7"))
    y = Y0 + 34
    for e in ENTRADAS:
        p.append(f'<circle cx="{X_ENTRADA + 18}" cy="{y - 4}" r="3" fill="{TINTA_3}"/>')
        p.append(_texto(X_ENTRADA + 30, y, e, tam=12.5, color=TINTA_2, ancho=22))
        y += 30 + 15 * (len(_lineas(e, 22)) - 1)
    p.append(_texto(X_ENTRADA + 16, Y0 + alto_bloque - 18,
                    "Los mismos que lee el evaluador", tam=11, color=TINTA_3, ancho=26))

    # Raíl de entrada
    rail = X_MOD - 30
    p.append(f'<path d="M {X_ENTRADA + W_ENTRADA} {Y0 + alto_bloque / 2} '
             f'H {rail}" stroke="{TINTA_3}" stroke-width="1.4" fill="none"/>')
    p.append(f'<path d="M {rail} {Y0 + ALTO_CAJA / 2} V {Y0 + alto_bloque - ALTO_CAJA / 2}" '
             f'stroke="{TINTA_3}" stroke-width="1.4" fill="none"/>')

    # --- Columna 2: módulos del equipo
    p.append(_columna(X_MOD, W_MOD, "Módulos del equipo"))
    for i, f in enumerate(fichas):
        y = Y0 + i * (ALTO_CAJA + HUECO)
        cy = y + ALTO_CAJA / 2
        t = TRAZO.get(f["estado_conexion"], TRAZO["sin documentar"])
        ident = f["estado_conexion"].replace(" ", "-")
        sin_avance = not f["casos"]

        p.append(f'<path d="M {rail} {cy} H {X_MOD - 6}" stroke="{TINTA_3}" '
                 f'stroke-width="1.4" fill="none" marker-end="url(#f-neutro)"/>')
        p.append(_caja(X_MOD, y, W_MOD, ALTO_CAJA,
                       relleno="#ffffff" if not sin_avance else "#fbfbfa",
                       guion="5 4" if sin_avance else None))
        p.append(f'<rect x="{X_MOD}" y="{y}" width="4" height="{ALTO_CAJA}" '
                 f'rx="2" fill="{t["color"]}"/>')
        p.append(_texto(X_MOD + 18, y + 26, f["nombre"], tam=13.5, color=TINTA, peso=650))
        p.append(_texto(X_MOD + 18, y + 44, f'{f["responsable"]} · {f.get("empresa", "")}',
                        tam=11.5, color=TINTA_3))
        p.append(_texto(X_MOD + 18, y + 62, f["funcion"], tam=11.5, color=TINTA_2,
                        ancho=62, interlinea=14))

        # Salida hacia el evaluador
        p.append(f'<path d="M {X_MOD + W_MOD} {cy} H {X_EVAL - 6}" '
                 f'stroke="{t["color"]}" stroke-width="{t["ancho"]}" fill="none" '
                 f'stroke-dasharray="{t["guion"]}" marker-end="url(#f-{ident})"/>')

    # --- Columna 3: el evaluador
    p.append(_columna(X_EVAL, W_EVAL, "Bloque de Evaluación y Calidad"))
    # El panel abarca toda la columna de módulos: las cinco salidas entran en el
    # mismo sitio, y ése es justo el argumento del esquema.
    y_panel = Y0
    p.append(_caja(X_EVAL, y_panel, W_EVAL, alto_panel, relleno="#f7fbff",
                   borde="#c6ddf8"))
    p.append(_texto(X_EVAL + 18, y_panel + 26, "Núcleo común, idéntico para toda rama",
                    tam=12, color="#1c5cab", peso=650))

    y = y_panel + 42
    for i, (titulo, detalle) in enumerate(PASOS_EVALUADOR):
        h = 60
        p.append(_caja(X_EVAL + 16, y, W_EVAL - 32, h, relleno="#ffffff",
                       borde="#c6ddf8", radio=9))
        p.append(f'<circle cx="{X_EVAL + 34}" cy="{y + 30}" r="10" fill="#eaf2fd"/>')
        p.append(f'<text x="{X_EVAL + 34}" y="{y + 34}" font-size="11" '
                 f'font-weight="700" fill="#1c5cab" text-anchor="middle">{i + 1}</text>')
        p.append(_texto(X_EVAL + 52, y + 25, titulo, tam=12.5, color=TINTA, peso=650))
        p.append(_texto(X_EVAL + 52, y + 41, detalle, tam=11, color=TINTA_2, ancho=40,
                        interlinea=12))
        if i < len(PASOS_EVALUADOR) - 1:
            p.append(f'<path d="M {X_EVAL + W_EVAL / 2} {y + h} v 14" '
                     f'stroke="{ACENTO}" stroke-width="1.6" fill="none" '
                     f'marker-end="url(#f-documentada)"/>')
        y += h + 16

    p.append(_caja(X_EVAL + 16, y, W_EVAL - 32, 70, relleno="#eaf2fd", borde="#9dc6f3",
                   radio=9))
    p.append(_texto(X_EVAL + 30, y + 26, "EvaluationResult", tam=13, color="#1c5cab",
                    peso=700))
    p.append(_texto(X_EVAL + 30, y + 44, "Valoración y aspectos a mejorar, cada uno "
                                         "anclado al caso que lo evidencia",
                    tam=10.5, color="#1c5cab", ancho=44, interlinea=12))

    # Pie del panel: lo que separa el núcleo de la rama
    yp = Y0 + alto_panel - 52
    p.append(_texto(X_EVAL + 16, yp + 4, "Cada rama sólo aporta cómo se extraen los "
                                         "campos de sus documentos y qué casos forman "
                                         "su batería. El resto es común.",
                    tam=10.5, color="#52514e", ancho=46, interlinea=13))

    # --- Leyenda
    yl = Y0 + alto_panel + 44
    p.append(_texto(24, yl - 14, "ESTADO DE LA CONEXIÓN CON MI BLOQUE", tam=10.5,
                    color=TINTA_3, peso=700))
    x = 24
    for estado, (etiqueta, _color, glosa) in modulos.ESTADOS_CONEXION.items():
        t = TRAZO[estado]
        p.append(f'<path d="M {x} {yl + 10} h 34" stroke="{t["color"]}" '
                 f'stroke-width="{t["ancho"]}" stroke-dasharray="{t["guion"]}"/>')
        p.append(_texto(x + 42, yl + 14, etiqueta, tam=12, color=TINTA, peso=650))
        p.append(_texto(x + 42, yl + 29, glosa, tam=10.5, color=TINTA_3, ancho=40,
                        interlinea=12))
        x += 360

    p.append("</svg>")
    return "".join(p)
