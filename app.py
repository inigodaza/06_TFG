"""
Bloque de Evaluación y Calidad — TFG Íñigo Daza.

Esta capa sólo elige qué rama se ejecuta y pinta lo que devuelve. Toda la
evaluación vive en `nucleo/` y `modulos/`: la app es un selector.

Tres pantallas:
  · Evaluar un módulo — la rejilla de módulos y el flujo de tres pasos
  · Demo              — el recorrido completo, módulo a módulo
  · Esquema           — por dónde circula un dato y qué hace cada módulo
"""

import json
import tempfile
from datetime import date

import pandas as pd
import streamlit as st

# Las tres carpetas del proyecto, antes que nada.
#
# `import esquema` era la primera línea que tocaba `modulos`, así que cuando la
# subida a GitHub se dejaba una carpeta por el camino el traceback señalaba a
# `esquema.py` —un fichero que no tiene ninguna culpa— y no decía en ningún
# sitio la única palabra que importa: **falta una carpeta**.
#
# Importarlas aquí, a mano y una a una, cuesta cuatro líneas y convierte un
# `ModuleNotFoundError` en una frase que se puede leer y arreglar. Es la misma
# idea que la comprobación de piezas de más abajo, sólo que ésta tiene que ir
# antes: si la carpeta no está, no hay piezas que comprobar.
_CARPETAS = {
    "nucleo": "el núcleo común: lectura de PDF, contraste, veredicto",
    "modulos": "una rama por módulo evaluado",
    "demo": "el recorrido de demostración y los documentos de ejemplo",
}
_sin_subir = []
for _paquete, _para_que in _CARPETAS.items():
    try:
        __import__(_paquete)
    except ModuleNotFoundError:
        _sin_subir.append((_paquete, _para_que))

if _sin_subir:
    st.error("**Falta una carpeta entera del proyecto en el repositorio.** No es "
             "un error de código: la subida a GitHub se ha dejado carpetas por el "
             "camino, que es el fallo más frecuente de este despliegue.")
    for _paquete, _para_que in _sin_subir:
        st.markdown(f"- **`{_paquete}/`** — {_para_que}")
    st.info("Una carpeta sólo existe en GitHub si contiene ficheros, y el "
            "formulario web no sube carpetas si eliges los ficheros con el "
            "explorador: hay que **arrastrarlas**. La forma que no falla es "
            "GitHub Desktop, y está explicada paso a paso en `DESPLIEGUE.md`. "
            "Comprueba también que dentro de cada carpeta esté su `__init__.py`: "
            "sin él, la carpeta está pero el paquete no.")
    st.stop()

import esquema
import modulos
import ui
from demo import guion
from modulos import similitud, vigencia
from nucleo import VERSION
from nucleo import asesor, historial, llm, plantilla
from nucleo import bateria as B_NUCLEO
from nucleo import pdf as P
from nucleo import veredicto as V

st.set_page_config(page_title="Evaluación y Calidad — TFG", layout="wide",
                   page_icon="◍", initial_sidebar_state="expanded")
ui.inyectar_estilo()

VERSION_REQUERIDA = 12

# Comprobación de coherencia al arrancar.
#
# Existe porque el fallo más frecuente de este proyecto no es un error de lógica:
# es subir a GitHub la mitad de los ficheros. Cuando `app.py` es nuevo y `ui.py`
# es viejo, Python revienta con un AttributeError críptico en mitad de un flujo,
# y el traceback señala la línea que llama, no el fichero que falta.
#
# Cada pieza declara qué necesita de las demás. Si algo no está, la app lo dice
# con el nombre del fichero que hay que subir, y no se ejecuta a medias.
#
# El 29/08 esta comprobación dejó pasar exactamente el fallo que existe para
# evitar. `ui.tabla_documentos` seguía existiendo en el fichero viejo —el
# `hasattr` decía que sí— pero admitía tres argumentos y `app.py` le pasaba
# cuatro. La app arrancó tan contenta y reventó al abrir el módulo de Martín.
# Desde entonces una pieza puede pedir además un **parámetro**, con la sintaxis
# `funcion:parametro`: comprobar que algo existe no es comprobar que encaja.
PIEZAS = [
    ("ui.py", ui, ["VERSION_UI", "bloque_evolucion", "bloque_asesor",
                   "bloque_severidad",
                   "bloque_procedencia", "barra_bateria", "medidor",
                   "franja_sistema", "franja_cifras", "fila_medidores",
                   "diagnostico_modelos", "selector_modo_lectura",
                   "tabla_documentos:extraer"]),
    ("nucleo/bateria.py", B_NUCLEO, ["SEVERIDADES", "ORDEN_SEVERIDAD"]),
    ("nucleo/plantilla.py", plantilla, ["filas", "a_markdown", "severidad_de"]),
    ("nucleo/asesor.py", asesor, ["aconsejar", "verificar_anclaje"]),
    ("nucleo/historial.py", historial, ["comparar", "instantanea", "registrar"]),
    ("nucleo/llm.py", llm, ["conformar", "modelo_en_uso", "listar_modelos"]),
    ("modulos/similitud.py", similitud, ["cargar_contribuciones",
                                         "reproducir_ranking", "PESOS_DECLARADOS"]),
    ("modulos/vigencia.py", vigencia, ["conciliar_ids", "PRORROGAS",
                                       "SALIDA_IALERT_CRED", "SALIDA_IALERT_TODAS", "familia_de",
                                       "descartar_incoherentes", "FAMILIAS"]),
    ("nucleo/pdf.py", P, ["hay_ocr", "texto_ocr", "integridad",
                          "idiomas_ocr"]),
    ("nucleo/llm.py · anclaje", llm, ["anclar", "fragmento_presente"]),
]

def _falta(modulo, pieza):
    """
    ¿Le falta a este módulo la pieza que se le pide?

    `nombre` pregunta por existencia. `nombre:parametro` pregunta además por la
    firma: que la función admita ese argumento. Lo segundo es lo que distingue
    un fichero viejo que casualmente tiene el mismo nombre de función de un
    fichero al día.
    """
    nombre, _, parametro = pieza.partition(":")
    objeto = getattr(modulo, nombre, None)
    if objeto is None:
        return True
    if not parametro:
        return False
    try:
        import inspect
        return parametro not in inspect.signature(objeto).parameters
    except (TypeError, ValueError):
        return False


_faltan = []
for _fichero, _modulo, _piezas in PIEZAS:
    _ausentes = [x for x in _piezas if _falta(_modulo, x)]
    if _ausentes:
        _faltan.append((_fichero, _ausentes))

# El número propio de `ui.py`, que es el fichero que más cambia y el que más
# veces se ha quedado atrás al subirlo.
if getattr(ui, "VERSION_UI", 0) < 12:
    _faltan.append(("ui.py", [f"es la versión {getattr(ui, 'VERSION_UI', 'antigua')} "
                              f"y se necesita la 12"]))

if VERSION < VERSION_REQUERIDA or _faltan:
    st.error("**El repositorio está a medio subir.** Hay ficheros de versiones "
             "distintas conviviendo, y eso produce errores que parecen de código "
             "pero son de despliegue.")
    if VERSION < VERSION_REQUERIDA:
        st.markdown(f"- `nucleo/__init__.py` está en la versión **{VERSION}** y se "
                    f"necesita la **{VERSION_REQUERIDA}**")
    for _fichero, _ausentes in _faltan:
        st.markdown(f"- **`{_fichero}`** es de una versión anterior: le faltan "
                    f"`{'`, `'.join(_ausentes)}`")
    st.info("Sube el repositorio **completo**, no ficheros sueltos. En GitHub: "
            "borra las carpetas `nucleo/`, `modulos/` y `demo/` y vuelve a "
            "subirlas enteras, junto con `app.py`, `ui.py` y `esquema.py`.")
    st.stop()

def secreto(clave, defecto=None):
    """
    `st.secrets` no devuelve None cuando falta el fichero de secretos: levanta
    excepción y se lleva por delante la app entera. En local, sin
    `secrets.toml`, eso significa que no arranca. Aquí la ausencia de clave es
    una situación normal —el sistema funciona en determinista— así que no puede
    ser un error fatal.
    """
    try:
        return st.secrets.get(clave, defecto)
    except Exception:
        return defecto


# La clave vive en Settings → Secrets de la app, nunca en el repositorio. Si no
# está, no pasa nada: el sistema entero funciona en modo determinista y lo dice.
llm.configurar(api_key=secreto("GEMINI_API_KEY"), modelo=secreto("GEMINI_MODELO"))

if not P.hay_pdftotext():
    st.error("No se encuentra `pdftotext`. En Streamlit Cloud, añade un fichero "
             "`packages.txt` con la línea `poppler-utils` y vuelve a desplegar.")
    st.stop()

# El OCR no para la app —hay ramas que no leen documentos— pero sí condiciona por
# completo la de Martín: sus trece documentos reales son fotocopias y ninguno
# tiene capa de texto. Sin OCR, el veredicto correcto sobre todos ellos es «no se
# ha podido comprobar», que es honesto y no sirve para nada. Se avisa arriba y
# con el nombre del paquete que falta, porque el mensaje que sale abajo —«sin
# capa de texto extraíble»— describe el síntoma y no la causa.
SIN_OCR = not P.hay_ocr()
if SIN_OCR:
    st.warning(
        "**No hay OCR en este despliegue, y sin él los documentos escaneados no "
        "se pueden leer.** Los trece documentos reales de Martín son fotocopias "
        "sin capa de texto: sobre ellos el evaluador sólo podrá decir «no se ha "
        "podido comprobar».\n\n"
        "· **En Streamlit Cloud** — `packages.txt` tiene que contener "
        "`poppler-utils`, `tesseract-ocr` y `tesseract-ocr-spa`. Los paquetes de "
        "sistema **sólo se instalan al reconstruir el contenedor**: después de "
        "subirlo hay que ir a *Manage app → Reboot app*, no basta con que se "
        "vuelva a desplegar el código.\n"
        "· **En local** — `sudo apt install tesseract-ocr tesseract-ocr-spa "
        "poppler-utils`.")
elif "spa" not in P.idiomas_ocr():
    st.warning("El OCR está disponible pero **sin el idioma español** "
               "(`tesseract-ocr-spa`). Funcionará en inglés: reconoce las cifras "
               "y las fechas, pero come tildes y eñes, y eso hace fallar citas "
               "que son buenas.")


# ===========================================================================
# Navegación
# ===========================================================================

PANTALLAS = ["Evaluar un módulo", "Demo", "Esquema del sistema"]

with st.sidebar:
    st.markdown('<div class="eyebrow">TFG · Íñigo Daza</div>'
                '<div style="font-size:1.15rem;font-weight:650;line-height:1.25;'
                'margin-bottom:1rem">Evaluación y Calidad</div>',
                unsafe_allow_html=True)
    pantalla = st.radio("Pantalla", PANTALLAS, label_visibility="collapsed")
    st.markdown("---")
    operativas = len(modulos.operativas())
    st.markdown(
        f'<div style="font-size:.8rem;color:#52514e;line-height:1.7">'
        f'<b>{operativas}</b> de <b>{len(modulos.RAMAS)}</b> módulos evaluables<br>'
        f'<b>{len(modulos.con_bateria())}</b> con batería diseñada<br>'
        f'<span style="color:#898781">núcleo v{VERSION}</span></div>',
        unsafe_allow_html=True)
    st.markdown("---")
    _ocr_ok = P.hay_ocr()
    _idiomas = P.idiomas_ocr()
    st.markdown(
        f'<div style="font-size:.8rem;color:#52514e;line-height:1.7">'
        f'<b>Lectura de documentos</b><br>'
        f'{"✓" if P.hay_pdftotext() else "✗"} pdftotext'
        f'<br>{"✓" if _ocr_ok else "✗"} OCR (tesseract)'
        f'<br>{"✓" if "spa" in _idiomas else "✗"} idioma español'
        f'</div>', unsafe_allow_html=True)
    if not _ocr_ok:
        st.caption("Sin OCR no se leen escaneos. Sube el `.ocr.txt` junto al PDF, "
                   "o instala `tesseract-ocr` y reinicia la app.")
    st.markdown("---")
    ui.panel_ia()
    ui.diagnostico_modelos()


# ===========================================================================
# Pantalla: esquema del sistema
# ===========================================================================

def pantalla_esquema():
    st.markdown('<div class="hero"><div class="eyebrow">Arquitectura</div>'
                '<h1>Esquema del sistema</h1>'
                '<div class="meta">Qué hace cada módulo y por dónde circula un dato '
                'hasta el veredicto</div></div>', unsafe_allow_html=True)
    ui.franja_sistema(modulos.fichas(), modulos.ESTADOS_CONEXION)
    st.markdown(f'<div class="esquema">{esquema.dibujar()}</div>',
                unsafe_allow_html=True)
    ui.nota("El dibujo se genera desde el registro de módulos: si mañana añado una "
            "rama, aparece aquí sola. <b>Probada</b> significa que un dato real ha "
            "recorrido el sistema de extremo a extremo, no que yo haya mirado los "
            "datos a mano — y quien la prueba es siempre quien la consume, no quien "
            "la produce.", acento=True)


# ===========================================================================
# Pantalla: demo
# ===========================================================================

ICONO = {"ejecutado": ("p-bien", "✓", "Ejecutado"),
         "a_medias": ("p-acento", "◐", "A medias"),
         "no_operativo": ("p-espera", "◌", "No operativo")}


def pantalla_demo():
    st.markdown('<div class="hero"><div class="eyebrow">Recorrido completo</div>'
                '<h1>Demo</h1><div class="meta">El sistema módulo a módulo. Un paso '
                'que no puede ejecutarse se enseña con el motivo: el recorrido cuenta '
                'el estado real del proyecto, no el previsto.</div></div>',
                unsafe_allow_html=True)

    fecha = st.date_input("Fecha de evaluación", value=date.today(),
                          help="La vigencia depende de cuándo se pregunta. Fijarla "
                               "aquí hace el recorrido reproducible.")

    # Se ejecuta todo primero para poder encabezar el recorrido con su resultado.
    # Una demo que empieza por el paso 1 obliga a llegar al final para saber cómo
    # acaba; ésta dice desde arriba qué ha encontrado y qué le falta.
    recorrido = [(paso,) + guion.ejecutar_paso(paso, fecha) for paso in guion.PASOS]
    ejecutados = [(p, d) for p, e, d in recorrido if e == "ejecutado"]
    bloqueados = [(p, d) for p, e, d in recorrido if e == "a_medias"]
    sin_bateria = [(p, d) for p, e, d in recorrido if e == "no_operativo"]

    fallos = []
    for paso, datos in ejecutados:
        ficha = datos["ficha"]
        for n, caso in sorted(datos["ev"]["casos"].items()):
            if caso["resultado"] == "no_pasa":
                fallos.append({"modulo": ficha["nombre"], "caso": n,
                               "titulo": ficha["casos"][n],
                               "severidad": plantilla.severidad_de(ficha, n),
                               "esperado": caso.get("esperado"),
                               "observado": caso.get("observado")})

    ui.franja_cifras([
        (f"{len(ejecutados)}/{len(recorrido)}", "pasos ejecutados"),
        (len(bloqueados), "bloqueados por datos ajenos"),
        (sum(len(d["ev"]["casos"]) for _, d in ejecutados), "casos ejercitados hoy"),
        (len(fallos), "fallos con evidencia"),
    ])

    ui.nota("<b>Dónde termina el sistema.</b> El evaluador recibe la salida de un "
            "módulo, calcula por su cuenta cuál debería haber sido y contrasta. "
            "<b>La salida se le entrega</b> —pegada o subida— porque ninguno de los "
            "cinco módulos publica un punto de acceso al que conectarse. Construir "
            "ese puente exigiría que cada compañero publicara y mantuviera un "
            "contrato técnico, y sobre prototipos que cambian cada semana dejaría de "
            "poder distinguirse si falla el módulo o falla el puente.")

    if fallos:
        st.subheader("Qué ha encontrado este recorrido")
        st.caption("Fallos con evidencia directa, encontrados hoy por las baterías "
                   "que sí han podido ejecutarse. No son opiniones sobre el código "
                   "ajeno: cada uno tiene un esperado y un observado detrás.")
        for f in fallos:
            sev = f["severidad"]
            color = (B_NUCLEO.SEVERIDADES[sev][2]
                     if sev in B_NUCLEO.SEVERIDADES else "#898781")
            with st.container(border=True):
                st.markdown(
                    f'<div style="border-left:4px solid {color};padding-left:.75rem">'
                    f'<b>{f["modulo"]} · caso {f["caso"]}</b> — {f["titulo"]}<br>'
                    f'<span style="font-size:.78rem;color:{color};font-weight:700;'
                    f'text-transform:uppercase;letter-spacing:.05em">'
                    f'{B_NUCLEO.SEVERIDADES[sev][0] if sev in B_NUCLEO.SEVERIDADES else "—"}'
                    f'</span></div>', unsafe_allow_html=True)
                if f["esperado"] and f["observado"]:
                    a, b = st.columns(2)
                    a.markdown(f"<span style='font-size:.7rem;font-weight:700;"
                               f"letter-spacing:.06em;color:#898781'>ESPERADO</span>"
                               f"<br>{f['esperado']}", unsafe_allow_html=True)
                    b.markdown(f"<span style='font-size:.7rem;font-weight:700;"
                               f"letter-spacing:.06em;color:#898781'>OBSERVADO</span>"
                               f"<br>{f['observado']}", unsafe_allow_html=True)

    st.subheader("El recorrido, paso a paso")

    for paso, estado, datos in recorrido:
        clase, glifo, palabra = ICONO[estado]
        with st.expander(paso["titulo"], expanded=(estado == "ejecutado")):
            st.markdown(ui.pastilla(palabra, clase, glifo), unsafe_allow_html=True)
            st.write(paso["relato"])

            if estado == "no_operativo":
                ui.nota(datos["motivo"])
                n = len(datos["ficha"]["casos"])
                st.caption(f"Batería diseñada: {n} casos. Diseñada no es ejecutada."
                           if n else "Sin batería diseñada todavía.")
                continue

            if estado == "a_medias":
                ui.nota(datos["motivo"], acento=True)
                # Un paso bloqueado no es un hueco: es media evaluación hecha. Se
                # enseña lo que ya está calculado para que se vea qué falta
                # exactamente y de quién depende.
                if datos.get("esperados"):
                    st.markdown("**Lo que ya está calculado: la verdad de campo**")
                    st.caption("Esta mitad no depende de nadie. El evaluador ha leído "
                               "los documentos y ha deducido qué estado corresponde a "
                               "cada uno. Lo que falta es la otra mitad del "
                               "contraste: la salida del módulo.")
                    st.dataframe(pd.DataFrame([{
                        "Documento": e["id_documento"],
                        "Vence": e["fecha_caducidad"].strftime("%d/%m/%Y")
                                 if e["fecha_caducidad"] else "—",
                        "Estado que sostienen los documentos":
                            vigencia.ESTADOS[e["estado"]],
                        "Por qué": e["motivo"],
                    } for e in datos["esperados"]]), use_container_width=True,
                        hide_index=True)
                n = len(datos["ficha"]["casos"])
                st.caption(f"Batería diseñada y lista: {n} casos. En cuanto llegue la "
                           f"salida, este paso se ejecuta sin tocar una línea de "
                           f"código.")
                continue

            ficha, ev, er = datos["ficha"], datos["ev"], datos["er"]
            c = ev["contraste"]
            ui.fila_medidores([
                ui.medidor("Exhaustividad", c["exhaustividad"],
                           "de lo que había que resolver"),
                ui.medidor("Precisión", c["precision"],
                           "de lo emitido se sostiene"),
            ])
            ui.barra_bateria(B_NUCLEO.resumen(ev["casos"]))
            st.write(er["valoracion"])

    if bloqueados or sin_bateria:
        st.subheader("Qué falta, y de quién depende")
        st.caption("Ninguno de estos puntos es un defecto del evaluador ni de los "
                   "módulos: son datos que el banco de pruebas todavía no tiene. La "
                   "lista la calcula el propio sistema.")
        filas = []
        for paso, datos in bloqueados:
            filas.append({"Paso": datos["ficha"]["nombre"],
                          "Responsable": datos["ficha"]["responsable"],
                          "Qué falta": datos.get("motivo", "")})
        for paso, datos in sin_bateria:
            filas.append({"Paso": datos["ficha"]["nombre"],
                          "Responsable": datos["ficha"]["responsable"],
                          "Qué falta": datos.get("motivo", "")})
        for paso, datos in ejecutados:
            for q in datos["er"].get("requisitos", []):
                filas.append({"Paso": datos["ficha"]["nombre"],
                              "Responsable": datos["ficha"]["responsable"],
                              "Qué falta": f"caso {q['caso']} — {q['requiere']}"})
        st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)


# ===========================================================================
# Pantalla: evaluar un módulo
# ===========================================================================

def rejilla_modulos():
    st.markdown('<div class="hero"><div class="eyebrow">Bloque de Evaluación y '
                'Calidad</div><h1>Elige el módulo que quieres auditar</h1>'
                '<div class="meta">Están los cinco módulos del proyecto, no sólo '
                'aquellos con los que he avanzado. Todos emiten el mismo objeto, con '
                'las mismas dos métricas y la misma regla de anclaje: lo comparable '
                'no son los módulos, es el veredicto.</div></div>',
                unsafe_allow_html=True)

    # Aquí iba una franja con el recuento del proyecto —módulos evaluables, casos
    # diseñados, conexiones probadas— y una tira con los cinco módulos y su
    # estado de conexión.
    #
    # Se ha quitado por dos motivos. El primero es que **repetía las tarjetas que
    # vienen justo debajo**: los mismos cinco módulos, dos veces, una de ellas sin
    # poder pulsarse. El segundo es de fondo: esas cifras cuentan cómo va el
    # trabajo, no la calidad de ningún módulo, y esta pantalla sirve para elegir
    # qué auditar. Un marcador del propio avance encabezando una herramienta de
    # calidad se lee raro, y además cambia cada semana.
    #
    # Las cifras no se pierden: viven en «Esquema del sistema», que es la pantalla
    # que sí existe para contar el estado real del conjunto.
    fichas = modulos.fichas()
    for inicio in range(0, len(fichas), 3):
        cols = st.columns(3, gap="medium")
        for ficha, col in zip(fichas[inicio:inicio + 3], cols):
            if ui.tarjeta_modulo(ficha, col):
                st.session_state.modulo = ficha["id"]
                st.rerun()
        # Rellena la última fila para que las tarjetas no se estiren
        for col in cols[len(fichas[inicio:inicio + 3]):]:
            col.empty()


def pantalla_no_operativa(ficha):
    ui.cabecera(ficha)
    ui.nota(ficha.get("pendiente", "Rama no operativa todavía."))
    if ficha["casos"]:
        st.markdown("**Batería diseñada**")
        st.dataframe(pd.DataFrame([{"#": n, "Caso": t}
                                   for n, t in ficha["casos"].items()]),
                     use_container_width=True, hide_index=True)
        st.caption("Los casos están diseñados y no ejecutados. Se enseñan porque el "
                   "estado de diseño y el de ejecución son cosas distintas y conviene "
                   "que se vea cuál es cuál.")
    else:
        st.markdown("**Batería**")
        st.caption("No hay ninguna. Escribir casos sin haber visto una salida real "
                   "sería exactamente el error que le mido a los demás: dar por hecho "
                   "algo que no se ha comprobado.")
    if ficha.get("siguiente_paso"):
        st.markdown("**Siguiente paso**")
        st.write(ficha["siguiente_paso"])


def subir_documentos(ficha, clave, carpeta_demo=None):
    """
    Paso 1: de qué documentos parte la evaluación.

    **Elegir de los que ya están manda sobre subirlos**, y el orden no es
    cosmético. Subir un PDF encadena tres cosas que fallan por separado: que el
    despliegue tenga OCR instalado, que el reconocimiento aguante en memoria, y
    que el nombre del fichero case con el de su texto. Con el corpus de Martín
    —trece fotocopias sin una letra de texto— cualquiera de las tres deja el
    módulo inservible, y las tres han fallado ya al menos una vez.

    Los documentos que viajan en el repositorio llevan su lectura hecha al lado.
    Elegirlos de una lista no depende de nada: ni de tesseract, ni de la memoria
    de la máquina, ni de cómo se llame el fichero. Subir sigue estando, para
    documentos nuevos, pero deja de ser el camino obligatorio.
    """
    st.subheader("1 · Documentos")
    st.caption(ficha["entrada"])

    disponibles = guion.documentos_de(carpeta_demo) if carpeta_demo else []
    por_nombre = {d["id"]: d for d in disponibles}
    docs = []

    if disponibles:
        listos = sum(1 for d in disponibles if d.get("legible"))
        st.markdown("**Documentos ya cargados en el sistema**")
        st.caption(f"{len(disponibles)} documentos con su lectura hecha "
                   f"({listos} legibles). Elegirlos de aquí no necesita OCR ni "
                   f"esperar: el texto ya está reconocido y viaja con el "
                   f"repositorio.")
        elegidos = st.multiselect(
            "Elige los documentos que quieres evaluar",
            options=sorted(por_nombre),
            default=st.session_state.get(f"sel_docs_{clave}") or [],
            key=f"sel_docs_{clave}",
            format_func=lambda n: n.replace("_", " "))
        c1, c2 = st.columns(2)
        if c1.button("Seleccionar todos", key=f"todos_{clave}",
                     use_container_width=True):
            st.session_state[f"sel_docs_{clave}"] = sorted(por_nombre)
            st.rerun()
        if c2.button("Quitar la selección", key=f"ninguno_{clave}",
                     use_container_width=True):
            st.session_state[f"sel_docs_{clave}"] = []
            st.rerun()
        docs = [por_nombre[n] for n in elegidos]

    with st.expander("…o subir documentos nuevos", expanded=not disponibles):
        st.caption(
            "Para documentos que el sistema todavía no conoce. Si son escaneos "
            "hace falta OCR instalado, o subir el `.ocr.txt` junto al PDF.")
        subidos = st.file_uploader(
            "Documentos en PDF (y, si los tienes, sus `.ocr.txt`)",
            type=["pdf", "txt"], accept_multiple_files=True, key=f"up_{clave}")
        ocr = st.checkbox(
            "Reconocer el texto de los escaneos (OCR)", value=P.hay_ocr(),
            disabled=not P.hay_ocr(), key=f"ocr_{clave}",
            help="Un escaneo tarda cerca de un minuto por documento."
                 if P.hay_ocr() else
                 "No hay OCR en este despliegue: sube el `.ocr.txt` junto al PDF.")
        if subidos:
            firmas = tuple((f.name, hash(f.getvalue())) for f in subidos)
            memo = st.session_state.setdefault("_docs_leidos", {})
            llave = (clave, firmas, bool(ocr))
            if llave not in memo:
                with st.spinner("Leyendo los documentos…"):
                    with tempfile.TemporaryDirectory() as tmp:
                        memo.clear()
                        memo[llave] = P.leer_subidos(subidos, tmp, ocr=ocr)
            nuevos = memo[llave]
            huerfanos = [d for d in nuevos if d.get("huerfano")]
            if huerfanos:
                st.warning(
                    "**Estos textos reconocidos no se han emparejado con ningún "
                    "PDF:** " + ", ".join(d["nombre"] for d in huerfanos)
                    + ". El emparejamiento ignora mayúsculas, espacios, guiones y "
                      "tildes; si aun así no casa, los nombres son distintos.")
            docs = docs + [d for d in nuevos if not d.get("huerfano")]

    if not docs:
        st.info("Elige al menos un documento de la lista, o sube uno nuevo.")
        st.stop()

    # Qué se ha podido leer y por qué vía. Va después de elegir y antes de
    # evaluar, porque condiciona todo lo que viene detrás.
    escaneos = [d for d in docs if d.get("via") == "ocr"]
    ilegibles = [d for d in docs if not d.get("legible")]
    if escaneos:
        ui.nota(f"<b>{len(escaneos)} de {len(docs)} documento(s) son escaneos sin "
                f"capa de texto</b> y se leen por OCR. El veredicto lo declara: "
                f"lo que se compara es una lectura del evaluador contra una "
                f"lectura del módulo, así que una discrepancia sobre una fecha no "
                f"demuestra por sí sola que el módulo se equivoque.", acento=True)
    if ilegibles:
        st.error("**Sin texto ni con OCR:** "
                 + ", ".join(d["nombre"] for d in ilegibles)
                 + ". Estos documentos no producen «sin incidencias»: producen "
                   "«no se ha podido comprobar».")
        for d in ilegibles:
            for f in (d.get("fallos_lectura") or []):
                st.caption(f"· {d['nombre']}: {f}")
    for d in docs:
        integ = d.get("integridad") or {}
        if integ.get("completo") is False:
            st.warning(f"**{d['nombre']}** está incompleto: su pie declara "
                       f"{integ['paginas_declaradas']} páginas y el fichero tiene "
                       f"{integ['paginas_fichero']} (faltan "
                       f"{', '.join(str(n) for n in integ['faltantes'])}). No "
                       f"puntúa contra el módulo; se registra como hallazgo.")
    return docs


def evaluar_pulsado(clave, etiqueta="Evaluar la salida del módulo"):
    """
    El botón de evaluar, con memoria.

    Streamlit reejecuta el script entero en cada interacción y un `st.button`
    sólo devuelve True en la ejecución en la que se pulsa. Sin recordar que ya se
    evaluó, cualquier botón posterior —convocar al panel, redactar el informe—
    haría desaparecer el resultado al pulsarlo. Se anota en el estado de sesión y
    se limpia lo que dependía de la evaluación anterior.
    """
    if st.button(etiqueta, type="primary", key=f"btn_eval_{clave}"):
        st.session_state[f"evaluado_{clave}"] = True
        st.session_state.pop(f"panel_{clave}", None)
        st.session_state.pop(f"informe_{clave}", None)
        st.session_state.pop(f"asesor_{clave}", None)
    return bool(st.session_state.get(f"evaluado_{clave}"))


def flujo_vigencia(rama):
    ficha = rama.FICHA
    ui.cabecera(ficha)
    modo = ui.selector_modo_lectura(ficha, "vigencia")

    docs = subir_documentos(ficha, "vigencia", carpeta_demo="vigencia")
    ui.tabla_documentos(docs, rama.TIPOS, rama.clasificar, rama.extraer)

    c1, c2 = st.columns(2)
    fecha = c1.date_input(
        "Fecha de consulta", value=date.today(),
        help="Un estado de vigencia sin fecha de consulta no es verificable: el "
             "mismo documento está vigente antes de su vencimiento y caducado "
             "después. Queda escrita en el veredicto.")
    ventana = c2.number_input(
        "Ventana de vencimientos (días)", min_value=1, max_value=365,
        value=rama.VENTANA_DIAS,
        help="La pregunta 2 de la prueba inicial: qué documentos vencen en los "
             "próximos N días, sin incluir los ya vencidos ni los posteriores.")

    try:
        esperados, ctx = rama.verdad_de_campo(docs, fecha, modo)
    except llm.NoDisponible as e:
        # No se degrada en silencio: se dice qué ha pasado y con qué se ha leído.
        st.error(f"La lectura asistida ha fallado y se ha vuelto al modo "
                 f"determinista. {e}")
        modo = "determinista"
        esperados, ctx = rama.verdad_de_campo(docs, fecha, modo)

    with st.expander("Verdad de campo calculada por el evaluador", expanded=False):
        st.dataframe(pd.DataFrame([{
            "Documento": e["id_documento"],
            "Cadena documental": e["cadena"] or "—",
            "Emisión": e["fecha_emision"].strftime("%d/%m/%Y") if e["fecha_emision"] else "—",
            "Vencimiento": e["fecha_caducidad"].strftime("%d/%m/%Y") if e["fecha_caducidad"] else "—",
            "Estado": rama.ESTADOS[e["estado"]], "Por qué": e["motivo"],
        } for e in esperados]), use_container_width=True, hide_index=True)
        cadenas = {k: v for k, v in ctx["cadenas"].items() if len(v) > 1}
        if cadenas:
            st.caption("Cadenas documentales con más de una versión: "
                       + "; ".join(f"«{k}» → " + ", ".join(x["id_documento"] for x in v)
                                   for k, v in cadenas.items()))
        st.caption("Ningún dato de esta tabla procede del módulo evaluado. Un "
                   "documento sin fecha de vencimiento no se declara vigente: la "
                   "ausencia de plazo no es vigencia indefinida.")

    ui.bloque_procedencia(ctx.get("procedencias"), modo)

    if modo != "determinista" and llm.esta_disponible():
        with st.expander("¿Es estable la lectura del modelo?", expanded=False):
            st.caption("El evaluador se aplica a sí mismo el caso que exige a los "
                       "demás. Lee el mismo documento varias veces saltándose la "
                       "caché y enseña qué campos cambian. Si la lectura baila, la "
                       "verdad de campo no es reproducible, y entonces el veredicto "
                       "que salga de ella tampoco: hay que declararlo. Cuesta una "
                       "llamada por repetición, así que no se hace solo.")
            c1, c2 = st.columns([2, 1])
            cual = c1.selectbox("Documento", [d["nombre"] for d in docs],
                                key="est_doc")
            k = c2.number_input("Repeticiones", 2, 5, 3, key="est_k")
            if st.button(f"Medir estabilidad · {int(k)} llamadas", key="est_btn"):
                doc = next(d for d in docs if d["nombre"] == cual)
                try:
                    r = llm.medir_estabilidad(doc["texto"], ficha["esquema_campos"],
                                              ficha["prompt_extraccion"], int(k))
                except llm.NoDisponible as e:
                    st.error(str(e))
                else:
                    if r["estable"]:
                        st.success(f"Estable: {r['ejecuciones']} lecturas de "
                                   f"{cual} devuelven los mismos {r['campos']} "
                                   f"campos.")
                    else:
                        st.warning(f"{len(r['inestables'])} de {r['campos']} campos "
                                   f"cambian entre lecturas.")
                        st.dataframe(pd.DataFrame([
                            {"Campo": c, "Valores distintos": " · ".join(v)}
                            for c, v in r["inestables"].items()]),
                            use_container_width=True, hide_index=True)

    st.subheader("2 · Salida del módulo")
    st.caption(ficha["entrada_respuesta"])
    c_pega, c_ej = st.columns([3, 1])
    with c_ej:
        st.caption("Salidas reales de IAlert ya transcritas:")
        if st.button("Cargar todas", use_container_width=True,
                     help="Las fichas que IAlert emite para los documentos de "
                          "RALSA, transcritas de la pantalla de Martín. Lo que no "
                          "se veía en el vídeo no se ha rellenado."):
            st.session_state["resp_vigencia"] = (
                rama.SALIDA_IALERT_CRED + "\n\n" + rama.SALIDA_IALERT_TODAS)
        if st.button("Sólo el contrato CRED", use_container_width=True):
            st.session_state["resp_vigencia"] = rama.SALIDA_IALERT_CRED
    respuesta = c_pega.text_area(
        "Salida del módulo de vigencia", height=220, key="resp_vigencia",
        label_visibility="collapsed",
        placeholder="Copia la ficha del documento entera desde la pantalla de "
                    "IAlert —el estado, la alerta y la tabla de campos— y pégala "
                    "aquí. Da igual si al copiar la tabla queda con el nombre del "
                    "campo y su valor en líneas separadas: se reconoce igual. "
                    "También se acepta JSON o CSV.")
    reportados, avisos = rama.interpretar(respuesta, modo)
    for a in avisos:
        st.warning(a)
    eventos = [r for r in reportados if r.get("tipo") == "evento"]
    reportados = [r for r in reportados if r.get("tipo", "estado") == "estado"]

    st.markdown("**Interpretación de la salida**")
    if reportados:
        st.caption("Revisa que coincide con lo que dice el módulo. Puedes corregir "
                   "cualquier celda antes de evaluar.")
        reportados = ui.editor(reportados, rama, "rev_vigencia")
    elif respuesta.strip():
        # No basta con decir que no se ha reconocido: hay que decir qué se ha
        # visto. Si no, la única salida es probar formatos hasta que uno cuele.
        diag = rama.diagnosticar(respuesta)
        st.error(f"**No se ha reconocido ningún documento.** De las "
                 f"{diag['lineas']} líneas pegadas, {len(diag['reconocidas'])} "
                 f"corresponden a campos que el evaluador conoce.")
        with st.expander("Qué ha leído el evaluador", expanded=True):
            if diag["reconocidas"]:
                st.markdown("**Campos reconocidos:** "
                            + ", ".join(f"`{l[:40]}`" for l in diag["reconocidas"][:12]))
            if diag["sueltas"]:
                st.markdown("**Líneas que no encajan con ningún campo:**")
                st.code("\n".join(diag["sueltas"]), language=None)
            st.caption("Etiquetas que el intérprete reconoce: "
                       + ", ".join(diag["conocidas"]) + ". Si IAlert las llama de "
                       "otra manera, dímelo y se añaden — o rellena la tabla de "
                       "abajo a mano, que también vale.")
        st.caption("Mientras tanto puedes introducir el estado a mano:")
        reportados = ui.editor([], rama, "rev_vigencia_manual")
    else:
        st.info("Sin respuesta introducida. Si continúas, se evaluará como ausencia "
                "total de clasificación.")

    if eventos:
        st.markdown("**Eventos y alertas reconocidos**")
        st.caption("Un evento no es un estado: alimenta el caso de la ventana de "
                   "vencimientos y el del aviso anticipado, no el de clasificación.")
        st.dataframe(pd.DataFrame([{
            "Documento": e["id_documento"], "Evento": e["evento"] or "—",
            "Fecha": e["fecha_evento"] or "—",
            "Días": e["dias"] if e["dias"] is not None else "—",
            "Preaviso declarado": e["preaviso_dias"] or "—"} for e in eventos]),
            use_container_width=True, hide_index=True)

    with st.expander("Segunda ejecución · repetibilidad (opcional)"):
        st.caption("Vuelve a pasar los mismos documentos por el módulo sin cambiar "
                   "nada y pega aquí la nueva salida. La redacción puede variar, el "
                   "estado asignado no debería.")
        respuesta_2 = st.text_area("Segunda ejecución", height=110,
                                   key="resp2_vigencia", label_visibility="collapsed")
    repeticion = None
    if respuesta_2.strip():
        repeticion, avisos_2 = rama.interpretar(respuesta_2, modo)
        for a in avisos_2:
            st.warning(f"Segunda ejecución: {a}")

    st.subheader("3 · Evaluación")
    if not evaluar_pulsado("vigencia"):
        st.stop()

    ev = rama.evaluar(esperados, reportados + eventos, fecha, repeticion, modo,
                      ventana_dias=int(ventana), contexto=ctx)
    er = V.evaluation_result(ficha, ev, rama.sujeto(esperados), fecha)

    # Cuando el evaluador se abstiene, decir qué lo cerraría. Un «pendiente» que
    # no explica cómo dejar de estarlo es un callejón.
    if ev.get("abstenidos") and modo == "determinista":
        st.warning(
            f"**El evaluador se abstiene sobre "
            f"{len(ev['abstenidos'])} documento(s)** — no ha sabido leerles la "
            f"cláusula de duración, así que no entran en el contraste y sus casos "
            f"quedan pendientes en lugar de contar como fallo del módulo. Esto pasa "
            f"con los escaneos antiguos: el reconocimiento devuelve texto con "
            f"erratas y ninguna regla saca de ahí una fecha. **El modo asistido lo "
            f"cierra**: el modelo lee los mismos campos sobre el mismo texto —no "
            f"decide el estado, eso lo sigue haciendo la regla— y cada valor queda "
            f"marcado con su procedencia. Se cambia arriba, en «cómo lee el "
            f"evaluador».")
    elif ev.get("abstenidos"):
        # Dos causas muy distintas bajo la misma palabra. Confundirlas manda a
        # buscar el problema donde no está: una se arregla instalando un paquete
        # y la otra leyendo el documento a mano.
        _ilegibles = [e for e in ev["abstenidos"] if not e.get("legible")]
        _sin_clausula = [e for e in ev["abstenidos"] if e.get("legible")]
        if _ilegibles:
            st.error(
                f"**{len(_ilegibles)} documento(s) no se han podido leer**: "
                + ", ".join(e["id_documento"] for e in _ilegibles)
                + ". No es que el modelo no los entienda — es que no ha llegado a "
                  "ver ningún texto. Son escaneos y el OCR no está disponible en "
                  "este despliegue"
                + (" (ver el aviso del principio de la página)." if SIN_OCR
                   else ", o el reconocimiento no ha devuelto nada legible.")
                + " El modo asistido no arregla esto: el modelo lee texto, no "
                  "imágenes.")
        if _sin_clausula:
            st.warning(
                f"**{len(_sin_clausula)} documento(s) se han leído pero no se "
                f"les ha encontrado la cláusula de duración**: "
                + ", ".join(e["id_documento"] for e in _sin_clausula)
                + ". Ni las reglas ni el modelo la sostienen con una cita del "
                  "texto. Mira la tabla de procedencia: si hay descartes por "
                  "anclaje, el modelo sí propuso un valor y el evaluador no se lo "
                  "ha aceptado. Confírmalo a mano o déjalo como no evaluable.")

    ui.bloque_contraste(ficha, ev)
    ui.bloque_hallazgos(ev)
    df = ui.bloque_casos(ficha, ev)
    ui.bloque_requisitos(ficha, er)
    ui.bloque_severidad(ficha, ev)
    ui.bloque_veredicto(er)
    ui.bloque_evolucion(ficha, er, ev, "vigencia")
    panel = ui.bloque_asesor(ficha, er, ev, rama.evidencia_panel(respuesta),
                             "vigencia", "vigencia")
    ui.bloque_informe(ficha, er, ev, panel, "vigencia", "vigencia")
    ui.exportar(ficha, er, ev, df, "vigencia", panel,
                f"{len(docs)} documento(s) en PDF + salida pegada de IAlert")


def flujo_auditoria(rama):
    ficha = rama.FICHA
    ui.cabecera(ficha)
    modo = ui.selector_modo_lectura(ficha, "auditoria")

    docs = subir_documentos(ficha, "auditoria", carpeta_demo="auditoria")
    ui.tabla_documentos(docs, rama.TIPOS, rama.clasificar)

    try:
        esperados, contexto = rama.verdad_de_campo(docs, modo)
    except ValueError as e:
        st.error(str(e))
        st.stop()
    except llm.NoDisponible as e:
        st.error(f"La lectura asistida ha fallado y se ha vuelto al modo "
                 f"determinista. {e}")
        modo = "determinista"
        esperados, contexto = rama.verdad_de_campo(docs, modo)

    with st.expander("Campos extraídos de los documentos", expanded=False):
        st.dataframe(pd.DataFrame([{
            "Campo": etiqueta,
            "Documentación de cliente": contexto["cliente"].get(k, "—"),
            "Orden de fabricación": contexto["orden"].get(k, "—"),
        } for k, etiqueta in rama.ETIQUETAS.items()]), use_container_width=True,
            hide_index=True)
        respaldos = {k: v for k, v in contexto["orden"].items()
                     if k in ("cantidad_logistica", "cantidad_impresion")}
        if respaldos:
            st.caption("Valores de respaldo hallados dentro de la propia orden: "
                       + " · ".join(f"{k.replace('cantidad_', '')}: {v}"
                                    for k, v in respaldos.items()))

    st.subheader("2 · Respuesta del módulo")
    st.caption(ficha["entrada_respuesta"])
    if "resp_auditoria" not in st.session_state:
        st.session_state.resp_auditoria = ""
    b1, b2 = st.columns([1, 3])
    if b1.button("Pegar la respuesta del 42805", use_container_width=True):
        st.session_state.resp_auditoria = rama.EJEMPLO
    b2.caption("Atajo para la demostración: carga la respuesta que el módulo emitió "
               "sobre el pedido 42805.")
    respuesta = st.text_area("Respuesta del módulo", key="resp_auditoria", height=220,
                             label_visibility="collapsed")

    reportados, avisos = rama.interpretar(respuesta, modo)
    for a in avisos:
        st.warning(a)

    st.markdown("**Interpretación de la respuesta**")
    if reportados:
        st.caption("Revisa que coincide con lo que dice el módulo. Puedes corregir "
                   "cualquier celda antes de evaluar.")
        reportados = ui.editor(reportados, rama, "rev_auditoria")
    elif respuesta.strip():
        st.info("No se ha reconocido ninguna incidencia. Si el módulo efectivamente "
                "no reportó nada, continúa: el evaluador comprobará si esa ausencia "
                "era correcta.")
    else:
        st.info("Sin respuesta introducida. Si continúas, se evaluará como ausencia "
                "de incidencias.")

    with st.expander("Segunda ejecución · repetibilidad (opcional)"):
        respuesta_2 = st.text_area("Segunda ejecución", height=110,
                                   key="resp2_auditoria", label_visibility="collapsed")
    repeticion = None
    if respuesta_2.strip():
        repeticion, avisos_2 = rama.interpretar(respuesta_2, modo)
        for a in avisos_2:
            st.warning(f"Segunda ejecución: {a}")

    evidencias = ui.bloque_evidencia(rama, "auditoria")

    st.subheader("3 · Evaluación")
    if not evaluar_pulsado("auditoria"):
        st.stop()

    ev = rama.evaluar(esperados, reportados, contexto, respuesta, repeticion, modo,
                      evidencias=evidencias)
    er = V.evaluation_result(ficha, ev, rama.sujeto(contexto))
    ui.bloque_contraste(ficha, ev)
    ui.bloque_hallazgos(ev)
    df = ui.bloque_casos(ficha, ev)
    ui.bloque_requisitos(ficha, er)
    ui.bloque_severidad(ficha, ev)
    ui.bloque_veredicto(er)
    ui.bloque_evolucion(ficha, er, ev, "auditoria")
    panel = ui.bloque_asesor(ficha, er, ev, rama.evidencia_panel(respuesta),
                             "auditoria", contexto["pedido"])
    ui.bloque_informe(ficha, er, ev, panel, "auditoria", contexto["pedido"])
    ui.exportar(ficha, er, ev, df, contexto["pedido"], panel,
                f"orden de fabricación y documentos de cliente del pedido "
                f"{contexto['pedido']}, en PDF")


def flujo_similitud(rama):
    ficha = rama.FICHA
    ui.cabecera(ficha)

    st.subheader("1 · Consulta exportada")
    ui.nota("<b>Aquí no se suben documentos, y no es un olvido.</b> El módulo de "
            "Álvaro no lee PDF: recibe un pedido, busca en un histórico de "
            "proyectos ya indexado y devuelve un ranking de los más parecidos. Lo "
            "único que existe es esa exportación en JSON, que es <b>a la vez el dato "
            "de origen y la salida a evaluar</b>.<br><br>"
            "Por eso el evaluador no contrasta contra una fuente externa: "
            "<b>rehace la aritmética</b> —recalcula la puntuación desde las señales "
            "y el peso declarados, y el orden desde las puntuaciones—, <b>decide por "
            "su cuenta qué proyectos son equivalentes al pedido</b> con los "
            "parámetros que el propio módulo publica, y <b>rehace la ordenación "
            "entera desde los pesos que Álvaro declara</b>.")

    ejemplos = sorted((guion.RAIZ / "similitud").glob("caso*.json")) \
        if (guion.RAIZ / "similitud").is_dir() else []
    texto = None
    if ejemplos:
        # Etiquetas legibles: el nombre del fichero no dice de qué va cada consulta.
        etiquetas = {"— subir un fichero —": None}
        for f in ejemplos:
            try:
                r = rama.resumen_consulta(json.loads(f.read_text(encoding="utf-8")))
                et = f"{r['pedido']} — {r['nota'].split(' · ')[0] if r['nota'] else 'sin nota'}"
            except Exception:
                et = f.name
            etiquetas[et] = f
        elegido = st.selectbox("Consulta", list(etiquetas), key="sel_similitud")
        if etiquetas[elegido] is not None:
            texto = etiquetas[elegido].read_text(encoding="utf-8")
    if texto is None:
        subido = st.file_uploader("Exportación en JSON", type="json",
                                  key="up_similitud")
        if subido:
            texto = subido.getvalue().decode("utf-8")
    if texto is None:
        st.info("Esperando la exportación de una consulta.")
        st.stop()

    datos, avisos = rama.interpretar(texto)
    for a in avisos:
        st.warning(a)
    if datos is None:
        st.stop()

    # Qué es esta consulta, antes de enseñar ningún veredicto sobre ella. El nombre
    # del fichero no dice nada a quien no lo escribió.
    rc = rama.resumen_consulta(datos)
    st.markdown(f"**Pedido consultado:** {rc['pedido']}")
    if rc["nota"]:
        st.caption(f"Álvaro anota sobre este caso: {rc['nota']}")
    ui.fila_kpis([
        ui.kpi("Corpus evaluado", rc["corpus"], "proyectos del histórico"),
        ui.kpi("Pasan el filtro", rc["resultados"],
               f"{rc['descartados']} descartados en la Capa 1"),
        ui.kpi("Equivalentes", rc["equivalentes"],
               "que determina el evaluador por su cuenta", acento=True),
        ui.kpi("Peso semántico", rc["peso_semantico"],
               "0 = la puntuación es sólo paramétrica"),
    ])
    if rc["lista_vacia"]:
        ui.nota("Esta consulta <b>no devuelve ningún resultado</b>: el filtro de la "
                "Capa 1 excluyó a todas las candidatas. Lo que se evalúa aquí es si "
                "el módulo lo explica bien, no si acierta el ranking.", acento=True)
    elif rc["equivalentes"]:
        ui.nota(f"El evaluador considera equivalentes al pedido a "
                f"<b>{', '.join(rc['ids_equivalentes'])}</b> — coinciden en todos los "
                f"parámetros categóricos y no se desvían más del "
                f"{rc['tolerancia']:.1%} en ninguno de los numéricos. Ésa es la "
                f"verdad de campo: lo que se comprueba es si el módulo los pone "
                f"arriba.", acento=True)

    # El umbral no se elige: se lee del propio conjunto buscando el salto entre las
    # candidatas parecidas y las que no lo son. La barra existe para lo contrario de
    # lo que parece — no para ajustar hasta que salga bien, sino para comprobar si el
    # veredicto aguanta cuando se mueve.
    # Tabla de contribución por parámetro. Sin ella el caso 11 queda pendiente —no
    # falla— porque la ordenación no se puede rehacer desde la salida sola. Que
    # haya que pedirla aparte es justamente el hallazgo de trazabilidad.
    contrib = None
    ruta_csv = guion.RAIZ / "similitud" / "contribuciones_peso_semantico_0.csv"
    with st.expander("Tabla de contribución por parámetro · reproducir la "
                     "ordenación", expanded=False):
        st.caption("Una fila por candidata y parámetro, con lo que cada uno aporta "
                   "al bruto. Es lo único que permite rehacer una puntuación sin "
                   "tener el corpus delante. Álvaro la aportó el 27/08 para los "
                   "grupos SYN-0041 y SYN-0052.")
        usar = st.checkbox("Usar la tabla aportada por Álvaro (27/08)",
                           value=ruta_csv.is_file(), key="chk_contrib_similitud",
                           disabled=not ruta_csv.is_file())
        subido_csv = st.file_uploader("O aportar otra tabla (CSV)", type="csv",
                                      key="up_contrib_similitud")
        crudo = None
        if subido_csv:
            crudo = subido_csv.getvalue().decode("utf-8")
        elif usar and ruta_csv.is_file():
            crudo = ruta_csv.read_text(encoding="utf-8")
        if crudo:
            try:
                contrib = rama.cargar_contribuciones(crudo)
                st.success("Tabla cargada: "
                           + ", ".join(f"{g} ({len(c)} candidatas)"
                                       for g, c in contrib.items()))
            except Exception as e:
                contrib = None
                st.error(f"No se pudo leer la tabla: {e}")

    esperados, ctx = rama.verdad_de_campo(datos, contribuciones=contrib)
    diag = ctx["umbral"]

    if diag.get("automatico"):
        ui.nota(f"<b>Umbral de equivalencia {ctx['tolerancia']:.1%}, derivado del "
                f"propio conjunto.</b> {diag['motivo'].capitalize()}.", acento=True)
    else:
        ui.nota(f"<b>Umbral de respaldo {ctx['tolerancia']:.1%}.</b> "
                f"{diag['motivo'].capitalize()} — aquí la frontera la pone el "
                f"evaluador, no los datos, y eso hace discutible el caso del ranking.")

    with st.expander("Análisis de sensibilidad · ¿aguanta el veredicto si muevo el "
                     "umbral?", expanded=False):
        st.caption("Un umbral derivado sólo vale si el resultado no depende de él. "
                   "Esta tabla recorre el rango entero y enseña dónde cambia la "
                   "respuesta. Si el veredicto es el mismo en toda la banda del "
                   "salto, el corte no está sostenido con pinzas.")
        filas = []
        for pct in range(2, 31, 2):
            e_i, c_i = rama.verdad_de_campo(datos, pct / 100, contrib)
            ev_i = rama.evaluar(e_i, c_i)
            ct = ev_i["contraste"]
            filas.append({"Umbral": f"{pct} %", "Equivalentes": len(e_i),
                          "Exhaustividad": f"{ct['exhaustividad']}%"
                                           if ct["exhaustividad"] is not None else "—",
                          "Precisión": f"{ct['precision']}%"
                                       if ct["precision"] is not None else "—",
                          "Caso del ranking":
                              ui.B.TEXTO[ev_i["casos"][4]["resultado"]],
                          "": "◀ derivado" if abs(pct / 100 - ctx["tolerancia"]) < 0.01
                              else ""})
        st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

        manual = st.checkbox("Fijar el umbral a mano", value=False, key="man_similitud")
        if manual:
            pct = st.slider("Umbral", 1, 30, int(round(ctx["tolerancia"] * 100)), 1,
                            format="%d %%", key="umb_similitud")
            esperados, ctx = rama.verdad_de_campo(datos, pct / 100, contrib)
            st.warning(f"Umbral impuesto a mano: {pct} %. El veredicto lo declarará "
                       f"como tal.")

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**Consulta**  \n{ctx['consulta']}")
    c2.markdown(f"**Peso semántico**  \n{ctx['peso']}")
    c3.markdown(f"**Candidatas**  \n{ctx['n_resultados']} en el ranking · "
                f"{ctx['n_descartados']} descartadas")
    st.caption(f"Pedido: {datos.get('pedido_consultado', '—')}")

    with st.expander("Verdad de campo calculada por el evaluador", expanded=False):
        st.dataframe(pd.DataFrame([{
            "Posición": p["posicion"], "Proyecto": p["id_proyecto"],
            "Desviación máxima": f"{p['desviacion']:.1%}",
            "Categóricos que no coinciden":
                ", ".join(p["categoricos_distintos"]) or "—",
            "Equivalente al pedido": "Sí" if p["equivalente"] else "No",
        } for p in ctx["perfiles"]]), use_container_width=True, hide_index=True)
        peor, mejor = ctx["margen"]
        if peor is not None and mejor is not None:
            st.caption(f"Margen del conjunto: el equivalente que más se desvía está "
                       f"al {peor:.1%} y el no equivalente que menos, al {mejor:.1%}. "
                       f"Cuanto mayor sea el hueco, menos discutible es el umbral.")

    st.subheader("2 · Segunda ejecución · repetibilidad (opcional)")
    with st.expander("Aportar una segunda exportación de la misma consulta"):
        subido2 = st.file_uploader("Segunda exportación", type="json",
                                   key="up2_similitud")
    repeticion = None
    if subido2:
        repeticion, avisos2 = rama.interpretar(subido2.getvalue().decode("utf-8"))
        for a in avisos2:
            st.warning(f"Segunda ejecución: {a}")

    st.subheader("3 · Evaluación")
    if not evaluar_pulsado("similitud"):
        st.stop()

    ev = rama.evaluar(esperados, ctx, repeticion)
    er = V.evaluation_result(ficha, ev, rama.sujeto(ctx))
    ui.bloque_contraste(ficha, ev)
    ui.bloque_hallazgos(ev)
    df = ui.bloque_casos(ficha, ev)
    ui.bloque_requisitos(ficha, er)
    ui.bloque_severidad(ficha, ev)
    ui.bloque_veredicto(er)
    nombre = ctx["consulta"] or "similitud"
    ui.bloque_evolucion(ficha, er, ev, "similitud")
    panel = ui.bloque_asesor(ficha, er, ev, rama.evidencia_panel(datos),
                             "similitud", nombre)
    ui.bloque_informe(ficha, er, ev, panel, "similitud", nombre)
    ui.exportar(ficha, er, ev, df, nombre, panel,
                "exportación JSON de la consulta")


def flujo_contradicciones(rama):
    ficha = rama.FICHA
    ui.cabecera(ficha)

    st.subheader("1 · Exportación del pedido")
    st.caption(ficha["entrada"])
    ui.nota("Aquí el contraste es el más limpio del sistema: la exportación trae "
            "en el mismo fichero <b>los hechos extraídos de cada documento</b> y "
            "<b>las contradicciones que el módulo declara</b>. El evaluador "
            "<b>ignora la tabla de contradicciones y la recalcula desde los "
            "hechos</b> —dos hechos activos del mismo campo con valores distintos "
            "son una contradicción, la haya visto el módulo o no— y sólo entonces "
            "compara. No hay lectura de por medio que pueda introducir error.")

    carpeta = guion.RAIZ / "contradicciones"
    ejemplos = sorted(carpeta.glob("*.json")) if carpeta.is_dir() else []
    texto = None
    if ejemplos:
        nombres = ["— subir un fichero —"] + [f.name for f in ejemplos]
        elegido = st.selectbox("Exportación", nombres, key="sel_contradicciones")
        if elegido != nombres[0]:
            texto = next(f for f in ejemplos
                         if f.name == elegido).read_text(encoding="utf-8")
    if texto is None:
        subido = st.file_uploader("Exportación en JSON", type="json",
                                  key="up_contradicciones")
        if subido:
            texto = subido.getvalue().decode("utf-8")
    if texto is None:
        st.info("Esperando la exportación de un pedido.")
        st.stop()

    datos, avisos = rama.interpretar(texto)
    for a in avisos:
        st.warning(a)
    if datos is None:
        st.stop()

    esperados, ctx = rama.verdad_de_campo(datos)

    st.markdown("**Hechos extraídos y su estado**")
    st.caption("El estado de cada hecho es lo que decide el caso 7: después de una "
               "validación humana, el valor descartado debería distinguirse del "
               "confirmado.")
    st.dataframe(pd.DataFrame([{
        "#": h["id"], "Documento": h["documento"], "Campo": h["campo"],
        "Etiqueta en el documento": h["etiqueta"], "Valor": h["valor"],
        "Activo": "sí" if h["activo"] else "no"} for h in datos["hechos"]]),
        use_container_width=True, hide_index=True)

    ui.fila_kpis([
        ui.kpi("Hechos activos", ctx["hechos_activos"],
               f"de {ctx['hechos_totales']} extraídos"),
        ui.kpi("Contradicciones derivadas", len(esperados),
               "recalculadas desde los hechos", acento=True),
        ui.kpi("Contradicciones emitidas", len(datos["contradicciones"]),
               "declaradas por el módulo"),
        ui.kpi("Revisiones humanas",
               sum(1 for c in datos["contradicciones"] if c.get("resolucion")),
               "con rastro registrado"),
    ])

    st.subheader("2 · Segunda ejecución · repetibilidad (opcional)")
    st.caption("Vuelve a exportar el mismo pedido sin cambiar nada. El módulo emite "
               "una huella por contradicción, así que la comparación es inmediata.")
    subido2 = st.file_uploader("Segunda exportación", type="json",
                               key="up2_contradicciones", label_visibility="collapsed")
    repeticion = None
    if subido2:
        repeticion, avisos2 = rama.interpretar(subido2.getvalue().decode("utf-8"))
        for a in avisos2:
            st.warning(f"Segunda exportación: {a}")

    st.subheader("3 · Evaluación")
    if not evaluar_pulsado("contradicciones"):
        st.stop()

    ev = rama.evaluar(esperados, ctx, repeticion)
    er = V.evaluation_result(ficha, ev, rama.sujeto(ctx))
    ui.bloque_contraste(ficha, ev)
    ui.bloque_hallazgos(ev)
    df = ui.bloque_casos(ficha, ev)
    ui.bloque_requisitos(ficha, er)
    ui.bloque_severidad(ficha, ev)
    ui.bloque_veredicto(er)
    nombre = datos["grupo"] or "contradicciones"
    ui.bloque_evolucion(ficha, er, ev, "contradicciones")
    panel = ui.bloque_asesor(ficha, er, ev, rama.evidencia_panel(datos),
                             "contradicciones", nombre)
    ui.bloque_informe(ficha, er, ev, panel, "contradicciones", nombre)
    ui.exportar(ficha, er, ev, df, nombre, panel,
                "exportación JSON del pedido")


FLUJOS = {"auditoria": flujo_auditoria, "vigencia": flujo_vigencia,
          "similitud": flujo_similitud,
          "contradicciones": flujo_contradicciones}


def pantalla_evaluar():
    id_modulo = st.session_state.get("modulo")
    if not id_modulo:
        rejilla_modulos()
        return

    if st.button("← Todos los módulos"):
        st.session_state.modulo = None
        st.rerun()

    rama = modulos.rama(id_modulo)
    if not rama.FICHA["operativo"]:
        pantalla_no_operativa(rama.FICHA)
        return
    FLUJOS[id_modulo](rama)


if pantalla == "Esquema del sistema":
    pantalla_esquema()
elif pantalla == "Demo":
    pantalla_demo()
else:
    pantalla_evaluar()
