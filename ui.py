"""
Capa de presentación: estilo, componentes y bloques de resultado.

Aquí no hay ninguna decisión de evaluación. Sólo se pinta lo que devuelve el
núcleo. Si algo de esta capa influyera en el veredicto, el veredicto dejaría de
ser reproducible fuera de la app y `pruebas.py` no podría comprobarlo.

Los colores no son decorativos. Los tres estados de un caso —superado, fallido,
pendiente— y los tres de una conexión —probada, documentada, sin documentar— son
información, y por eso van siempre con su glifo y su palabra al lado: el color
acompaña, nunca carga solo con el significado.
"""

import html

import pandas as pd
import streamlit as st

# Versión de ESTE fichero, aparte de la del paquete.
#
# La comprobación de arranque miraba sólo `nucleo/__init__.py`, y por eso dejó
# pasar el fallo del 29/08: `app.py` era nuevo, `ui.py` era viejo, y como el
# viejo también tenía todas las funciones por nombre, la comprobación dio el
# visto bueno. Lo que había cambiado era la **firma** de una de ellas, no su
# existencia. Un número por fichero detecta lo que un `hasattr` no ve.
VERSION_UI = 12

from nucleo import bateria as B  # noqa: F401  (lo usa app.py)
from nucleo import asesor as AS
from nucleo import historial as H
from nucleo import informe as INF
from nucleo import jueces as J
from nucleo import plantilla as PL
from nucleo import llm
from nucleo import veredicto as V

# ===========================================================================
# Estilo
# ===========================================================================

ESTILO = """
<style>
:root{
  --superficie:#fcfcfb; --plano:#f4f4f1; --tinta:#0b0b0b; --tinta-2:#52514e;
  --tinta-3:#898781; --linea:#e1e0d9; --borde:rgba(11,11,11,.10);
  --acento:#2a78d6; --acento-suave:#eaf2fd;
  --bien:#006300; --bien-marca:#0ca30c; --bien-fondo:#e8f5e8;
  --mal:#d03b3b; --mal-fondo:#fceceb;
  --espera:#52514e; --espera-fondo:#f0efec;
}

.stApp { background: var(--superficie); }
.block-container { padding-top: 3.4rem; max-width: 1180px; }

h1, h2, h3 { letter-spacing: -.015em; }
h1 { font-weight: 650 !important; }

/* --- Cabecera de sección ------------------------------------------------ */
.eyebrow{
  font-size:.72rem; font-weight:650; letter-spacing:.09em; text-transform:uppercase;
  color:var(--acento); margin-bottom:.35rem;
}
.hero{ border-bottom:1px solid var(--linea); padding-bottom:1rem; margin-bottom:1.4rem; }
.hero h1{ margin:0 0 .3rem 0; font-size:1.85rem; }
.hero .meta{ color:var(--tinta-2); font-size:.92rem; }

/* --- Medidores de arco -------------------------------------------------- */
.medidores{ display:flex; gap:.7rem; flex-wrap:wrap; margin:.2rem 0 1rem 0; }
.medidor{
  flex:1 1 165px; background:#fff; border:1px solid var(--borde); border-radius:14px;
  padding:.85rem .7rem .7rem .7rem; text-align:center;
}
.medidor svg{ display:block; margin:0 auto; }
.medidor .m-et{
  font-size:.72rem; font-weight:650; letter-spacing:.06em; text-transform:uppercase;
  color:var(--tinta-2); margin-top:.35rem;
}
.medidor .m-n{ font-size:.74rem; color:var(--tinta-3); line-height:1.35; margin-top:.2rem; }
.m-cifra{ font-size:1.5rem; font-weight:680; letter-spacing:-.02em; }
.m-sub{ font-size:.72rem; font-weight:600; fill:var(--tinta-3); }

/* --- Barra apilada de la batería ---------------------------------------- */
.barra-envoltura{
  background:#fff; border:1px solid var(--borde); border-radius:14px;
  padding:.9rem 1rem 1rem 1rem; margin:.2rem 0 1rem 0;
}
.barra{
  display:flex; height:26px; border-radius:8px; overflow:hidden;
  border:1px solid var(--borde); background:var(--plano);
}
.barra .seg{
  display:flex; align-items:center; justify-content:center; color:#fff;
  font-size:.74rem; font-weight:650; min-width:0; transition:flex-basis .3s ease;
}
.barra .seg span{ padding:0 .3rem; white-space:nowrap; overflow:hidden; }
.leyenda{ display:flex; gap:1.1rem; flex-wrap:wrap; margin-top:.6rem; }
.leyenda .it{ display:flex; align-items:center; gap:.4rem; font-size:.79rem;
  color:var(--tinta-2); }
.leyenda .sw{ width:11px; height:11px; border-radius:3px; flex:none; }
.barra-pie{ font-size:.79rem; color:var(--tinta-3); margin-top:.55rem; line-height:1.5; }

/* --- Franja de estado del sistema --------------------------------------- */
.franja{
  background:linear-gradient(180deg,#fff 0%, var(--plano) 100%);
  border:1px solid var(--borde); border-radius:16px;
  padding:1rem 1.15rem; margin:0 0 1.3rem 0;
}
.franja-cifras{ display:flex; gap:1.9rem; flex-wrap:wrap; margin-bottom:.9rem; }
.franja-cifras .f-b{ min-width:88px; }
.franja-cifras .f-v{ font-size:1.55rem; font-weight:680; letter-spacing:-.02em;
  line-height:1.1; }
.franja-cifras .f-e{ font-size:.73rem; font-weight:600; letter-spacing:.05em;
  text-transform:uppercase; color:var(--tinta-3); }
.cadena{ display:flex; align-items:stretch; gap:0; flex-wrap:wrap; }
.cadena .esl{
  flex:1 1 0; min-width:118px; background:#fff; border:1px solid var(--borde);
  border-top:3px solid var(--tinta-3); border-radius:10px; padding:.5rem .6rem;
  margin-right:.4rem;
}
.cadena .esl:last-child{ margin-right:0; }
.cadena .e-n{ font-size:.82rem; font-weight:650; line-height:1.25; }
.cadena .e-q{ font-size:.72rem; color:var(--tinta-3); margin-top:.15rem; }
.cadena .e-s{ font-size:.71rem; font-weight:600; margin-top:.35rem; }

/* --- Desglose esperado / observado -------------------------------------- */
.desglose{ display:flex; gap:.9rem; flex-wrap:wrap; margin-top:.45rem; }
.desglose > div{ flex:1 1 240px; font-size:.81rem; color:var(--tinta-2);
  background:var(--plano); border-radius:8px; padding:.35rem .55rem; line-height:1.4; }
.desglose span{ display:block; font-size:.68rem; font-weight:700; letter-spacing:.06em;
  text-transform:uppercase; color:var(--tinta-3); margin-bottom:.1rem; }
.sev{ margin-top:.35rem; font-size:.7rem; font-weight:700; letter-spacing:.05em;
  text-transform:uppercase; text-align:center; border:1px solid; border-radius:6px;
  padding:.1rem .35rem; }

/* --- Pastillas ---------------------------------------------------------- */
.pastilla{
  display:inline-flex; align-items:center; gap:.38rem; padding:.16rem .58rem;
  border-radius:999px; font-size:.76rem; font-weight:600; line-height:1.5;
  border:1px solid var(--borde); white-space:nowrap;
}
.pastilla .punto{ font-size:.62rem; line-height:1; }
.p-bien{ background:var(--bien-fondo); color:var(--bien); border-color:#bfe0bf; }
.p-mal{ background:var(--mal-fondo); color:var(--mal); border-color:#f2c9c7; }
.p-espera{ background:var(--espera-fondo); color:var(--espera); }
.p-acento{ background:var(--acento-suave); color:#1c5cab; border-color:#c6ddf8; }
.p-neutro{ background:var(--plano); color:var(--tinta-2); }

/* --- Tarjetas de módulo ------------------------------------------------- */
div[data-testid="stVerticalBlockBorderWrapper"]{
  border-radius:14px !important; border:1px solid var(--borde) !important;
  background:#fff; transition:box-shadow .15s ease, transform .15s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover{
  box-shadow:0 6px 20px rgba(11,11,11,.07); transform:translateY(-1px);
}
.tarjeta-nombre{ font-size:1.02rem; font-weight:650; margin:.1rem 0 .1rem 0; }
.tarjeta-quien{ color:var(--tinta-2); font-size:.83rem; margin-bottom:.55rem; }
.tarjeta-funcion{ color:var(--tinta-2); font-size:.86rem; line-height:1.45;
                  min-height:3.7rem; }
.tarjeta-pie{ color:var(--tinta-3); font-size:.76rem; border-top:1px solid var(--linea);
              padding-top:.5rem; margin-top:.55rem; }

/* --- Botones ------------------------------------------------------------ */
div.stButton > button{ border-radius:9px; font-weight:600; border:1px solid var(--borde); }
div.stButton > button[kind="primary"]{ border:none; box-shadow:0 1px 2px rgba(11,11,11,.14); }
div.stButton > button:disabled{ color:var(--tinta-3); }

/* --- KPI ---------------------------------------------------------------- */
.kpis{ display:flex; gap:.7rem; flex-wrap:wrap; margin:.2rem 0 1rem 0; }
.kpi{ flex:1 1 150px; background:#fff; border:1px solid var(--borde);
      border-radius:12px; padding:.75rem .9rem; }
.kpi .k-et{ font-size:.74rem; color:var(--tinta-2); font-weight:600;
            text-transform:uppercase; letter-spacing:.05em; }
.kpi .k-v{ font-size:1.75rem; font-weight:650; line-height:1.25; margin-top:.15rem; }
.kpi .k-n{ font-size:.76rem; color:var(--tinta-3); }
.kpi--acento{ border-color:#c6ddf8; background:linear-gradient(180deg,#f7fbff,#fff); }
.kpi--acento .k-v{ color:#1c5cab; }

/* --- Casos -------------------------------------------------------------- */
.caso{ display:flex; gap:.8rem; align-items:flex-start; padding:.7rem .9rem;
       border:1px solid var(--borde); border-left-width:4px; border-radius:10px;
       background:#fff; margin-bottom:.45rem; }
.caso--pasa{ border-left-color:var(--bien-marca); }
.caso--no_pasa{ border-left-color:var(--mal); }
.caso--pendiente{ border-left-color:var(--tinta-3); }
.caso--no_aplica{ border-left-color:var(--linea); background:#fbfbfa; }
.caso .requiere{ color:var(--tinta-3); font-size:.8rem; margin-top:.3rem;
                 font-style:italic; }
.caso .n{ font-variant-numeric:tabular-nums; color:var(--tinta-3); font-weight:650;
          font-size:.86rem; min-width:1.4rem; padding-top:.12rem; }
.caso .cuerpo{ flex:1; }
.caso .titulo{ font-weight:600; font-size:.94rem; margin-bottom:.15rem; }
.caso .obs{ color:var(--tinta-2); font-size:.85rem; line-height:1.5; }
.caso .origen{ color:var(--tinta-3); font-size:.74rem; font-weight:500;
               margin-left:.45rem; }

/* --- Avisos ------------------------------------------------------------- */
.nota{ background:var(--plano); border-left:3px solid var(--tinta-3);
       padding:.6rem .85rem; border-radius:0 8px 8px 0; color:var(--tinta-2);
       font-size:.87rem; line-height:1.5; margin:.4rem 0 .9rem 0; }
.nota--acento{ background:var(--acento-suave); border-left-color:var(--acento);
               color:#1c5cab; }

/* --- Esquema ------------------------------------------------------------ */
.esquema{ width:100%; background:#fff; border:1px solid var(--borde);
          border-radius:14px; padding:.5rem; overflow-x:auto; }
</style>
"""

TONO_CASO = {"pasa": ("p-bien", "✓", "Superado"),
             "no_pasa": ("p-mal", "✕", "Fallido"),
             "pendiente": ("p-espera", "◌", "Pendiente"),
             "no_aplica": ("p-neutro", "–", "No aplica")}

TONO_CONEXION = {"probada": ("p-bien", "●"),
                 "documentada": ("p-acento", "●"),
                 "sin documentar": ("p-neutro", "○")}

TONO_CRITERIO = {"cumple": ("p-bien", "✔", "Cumple"),
                 "no_cumple": ("p-mal", "✖", "No cumple"),
                 "discrepancia": ("p-espera", "≠", "Discrepancia"),
                 "no_valorable": ("p-neutro", "○", "No valorable")}


def inyectar_estilo():
    st.markdown(ESTILO, unsafe_allow_html=True)


def _e(x):
    return html.escape(str(x))


def pastilla(texto, clase="p-neutro", glifo="●"):
    return (f'<span class="pastilla {clase}"><span class="punto">{glifo}</span>'
            f'{_e(texto)}</span>')


def nota(texto, acento=False):
    st.markdown(f'<div class="nota{" nota--acento" if acento else ""}">{texto}</div>',
                unsafe_allow_html=True)


def kpi(etiqueta, valor, nota_pie="", acento=False):
    return (f'<div class="kpi{" kpi--acento" if acento else ""}">'
            f'<div class="k-et">{_e(etiqueta)}</div>'
            f'<div class="k-v">{_e(valor)}</div>'
            f'<div class="k-n">{_e(nota_pie)}</div></div>')


def fila_kpis(items):
    st.markdown('<div class="kpis">' + "".join(items) + '</div>',
                unsafe_allow_html=True)


# ===========================================================================
# Piezas visuales: medidores y barra apilada
# ===========================================================================
# Un porcentaje escrito hay que leerlo; un arco se ve. Pero el arco nunca va
# solo: lleva la cifra dentro y la explicación debajo, porque quien lea esto
# tiene que poder citarlo, no sólo mirarlo.

def medidor(etiqueta, porcentaje, pie="", color=None, sufijo="%"):
    """Arco de 270° con la cifra dentro. `porcentaje` None se dibuja vacío."""
    r, cx, cy = 46, 60, 58
    vacio = porcentaje is None
    p = 0 if vacio else max(0.0, min(100.0, float(porcentaje)))
    if color is None:
        color = ("#0ca30c" if p >= 90 else "#2a78d6" if p >= 70
                 else "#d9822b" if p >= 50 else "#d03b3b")
    # 270° de recorrido, empezando abajo-izquierda: el hueco de abajo evita que
    # el arco parezca un anillo cerrado y ya completo.
    largo = 2 * 3.14159265 * r * 0.75
    avance = largo * p / 100
    return (
        f'<div class="medidor">'
        f'<svg viewBox="0 0 120 116" width="120" height="116" role="img" '
        f'aria-label="{_e(etiqueta)}: {"sin dato" if vacio else f"{p:g}%"}">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#eceae4" '
        f'stroke-width="11" stroke-linecap="round" '
        f'stroke-dasharray="{largo:.1f} 999" transform="rotate(135 {cx} {cy})"/>'
        + (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
           f'stroke-width="11" stroke-linecap="round" '
           f'stroke-dasharray="{avance:.1f} 999" transform="rotate(135 {cx} {cy})"/>'
           if not vacio else "")
        + f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" class="m-cifra" '
          f'fill="{"#898781" if vacio else "#0b0b0b"}">'
          f'{"—" if vacio else f"{p:g}{sufijo}"}</text>'
        + f'</svg>'
        f'<div class="m-et">{_e(etiqueta)}</div>'
        + (f'<div class="m-n">{_e(pie)}</div>' if pie else "")
        + '</div>')


def fila_medidores(items):
    st.markdown('<div class="medidores">' + "".join(items) + '</div>',
                unsafe_allow_html=True)


def barra_bateria(r):
    """
    Los cuatro desenlaces de la batería en una sola barra proporcional.

    Es la pieza que más rápido cuenta el estado de una evaluación, y la que más
    cuidado necesita: superado, fallido, pendiente y no aplicable no se pueden
    fundir en un «porcentaje de éxito». Por eso los cuatro tramos van con su
    número dentro, su palabra en la leyenda y las dos tasas explicadas debajo.
    """
    tramos = [("pasa", "Superados", "#0ca30c"),
              ("no_pasa", "Fallidos", "#d03b3b"),
              ("pendiente", "Pendientes", "#8a8880"),
              ("no_aplica", "No aplicables", "#cfcdc6")]
    total = max(1, r["total"])

    segmentos = ""
    for clave, _, color in tramos:
        n = r[clave]
        if not n:
            continue
        ancho = 100 * n / total
        segmentos += (f'<div class="seg" style="flex:0 0 {ancho:.2f}%;'
                      f'background:{color};'
                      f'{"color:#4a4843;" if clave == "no_aplica" else ""}">'
                      f'<span>{n}</span></div>')

    leyenda = "".join(
        f'<div class="it"><span class="sw" style="background:{color}"></span>'
        f'{etiqueta} · {r[clave]}</div>' for clave, etiqueta, color in tramos)

    pie = (f'<b>Tasa de acierto {r["tasa"]}%</b> — superados entre los '
           f'{r["con_evidencia"]} casos con evidencia; mide el módulo. '
           if r["tasa"] is not None else "Sin casos con evidencia. ")
    pie += (f'<b>Cobertura {r["cobertura"]}%</b> — casos con evidencia entre los '
            f'{r["total"]} diseñados; mide el banco de pruebas del evaluador, no el '
            f'módulo.' if r["cobertura"] is not None else "")

    st.markdown(f'<div class="barra-envoltura"><div class="barra">{segmentos}</div>'
                f'<div class="leyenda">{leyenda}</div>'
                f'<div class="barra-pie">{pie}</div></div>',
                unsafe_allow_html=True)


# ===========================================================================
# Cabeceras y tarjetas
# ===========================================================================

def cabecera(ficha):
    clase, glifo = TONO_CONEXION.get(ficha["estado_conexion"], ("p-neutro", "○"))
    pastillas = pastilla(f"Conexión {ficha['estado_conexion']}", clase, glifo)
    if ficha.get("modulo_evaluado"):
        pastillas += " " + pastilla(ficha["modulo_evaluado"], "p-neutro", "▣")
    pastillas += " " + pastilla(f"{len(ficha['casos'])} casos", "p-neutro", "≡")
    st.markdown(
        f'<div class="hero"><div class="eyebrow">Módulo evaluado</div>'
        f'<h1>{_e(ficha["nombre"])}</h1>'
        f'<div class="meta">{_e(ficha["responsable"])}'
        + (f' · {_e(ficha["empresa"])}' if ficha.get("empresa") else "")
        + f' · {_e(ficha["conexion"])}</div>'
        f'<div style="margin-top:.6rem">{pastillas}</div></div>',
        unsafe_allow_html=True)


def franja_cifras(items):
    """
    Una banda de cifras grandes con su etiqueta. Es la misma pieza que encabeza la
    rejilla de módulos, sin la cadena de eslabones: sirve para que un recorrido
    empiece por su resultado en vez de por su primer paso.
    """
    cuerpo = "".join(
        f'<div class="f-b"><div class="f-v">{_e(v)}</div>'
        f'<div class="f-e">{_e(et)}</div></div>' for v, et in items)
    st.markdown(f'<div class="franja"><div class="franja-cifras" '
                f'style="margin-bottom:0">{cuerpo}</div></div>',
                unsafe_allow_html=True)


def franja_sistema(fichas, estados_conexion):
    """
    El estado del sistema entero, arriba del todo y de un vistazo.

    Enseña la cadena de valor tal cual está —no como debería estar— porque el
    dato que importa aquí no es cuántos módulos hay, es cuántas conexiones han
    llegado a probarse. Una conexión documentada y una probada se parecen mucho
    sobre el papel y no se parecen en nada en la práctica.
    """
    con_bateria = [f for f in fichas if f.get("casos")]
    operativos = [f for f in fichas if f.get("operativo")]
    casos = sum(len(f.get("casos") or {}) for f in fichas)
    cualitativos = sum(len(f.get("cualitativos") or []) for f in fichas)
    probadas = sum(1 for f in fichas if f.get("estado_conexion") == "probada")

    cifras = "".join(
        f'<div class="f-b"><div class="f-v">{v}</div><div class="f-e">{e}</div></div>'
        for v, e in [(f"{len(operativos)}/{len(fichas)}", "módulos evaluables"),
                     (casos, "casos diseñados"),
                     (cualitativos, "criterios cualitativos"),
                     (f"{probadas}/{len(fichas)}", "conexiones probadas")])

    eslabones = ""
    for f in fichas:
        estado = f.get("estado_conexion", "sin documentar")
        etiqueta, color, _ = estados_conexion.get(estado, ("—", "#898781", ""))
        _, glifo = TONO_CONEXION.get(estado, ("p-neutro", "○"))
        eslabones += (
            f'<div class="esl" style="border-top-color:{color}">'
            f'<div class="e-n">{_e(f["nombre"])}</div>'
            f'<div class="e-q">{_e(f["responsable"])}</div>'
            f'<div class="e-s" style="color:{color}">{glifo} {_e(etiqueta)}</div>'
            f'</div>')

    st.markdown(f'<div class="franja"><div class="franja-cifras">{cifras}</div>'
                f'<div class="cadena">{eslabones}</div></div>',
                unsafe_allow_html=True)


def tarjeta_modulo(ficha, columna):
    """Tarjeta de un módulo. Devuelve True si se ha pulsado su botón."""
    clase, glifo = TONO_CONEXION.get(ficha["estado_conexion"], ("p-neutro", "○"))
    with columna:
        with st.container(border=True):
            estado = (pastilla("Evaluable", "p-bien", "✓") if ficha["operativo"]
                      else pastilla("No operativo", "p-espera", "◌"))
            st.markdown(
                f'<div style="margin-bottom:.5rem">{estado} '
                f'{pastilla(ficha["estado_conexion"].capitalize(), clase, glifo)}</div>'
                f'<div class="tarjeta-nombre">{_e(ficha["nombre"])}</div>'
                f'<div class="tarjeta-quien">{_e(ficha["responsable"])}'
                + (f' · {_e(ficha["empresa"])}' if ficha.get("empresa") else "")
                + f'</div><div class="tarjeta-funcion">{_e(ficha["funcion"])}</div>'
                f'<div class="tarjeta-pie">'
                + (f'{len(ficha["casos"])} casos en la batería'
                   if ficha["casos"] else "Sin batería diseñada")
                + '</div>', unsafe_allow_html=True)
            return st.button(
                "Abrir" if ficha["operativo"] else "Ver estado",
                key=f"card_{ficha['id']}", use_container_width=True,
                type="primary" if ficha["operativo"] else "secondary")


# ===========================================================================
# Piezas del flujo de evaluación
# ===========================================================================

def selector_modo_lectura(ficha, clave):
    """
    El conmutador de la vía de lectura.

    Los modos que necesitan el modelo se enseñan siempre, aunque estén cerrados:
    lo que falta tiene que verse. Y una rama puede tener la IA vetada por una
    razón que no es técnica —los datos que maneja— así que el veto se enseña con
    su motivo, no escondiendo la opción.
    """
    est = llm.estado()
    permitida = ficha.get("ia_permitida", False)

    with st.expander("Vía de lectura de los documentos", expanded=False):
        for modo, explicacion in llm.MODOS.items():
            libre = modo == "determinista" or (est["disponible"] and permitida)
            st.markdown(f"**{modo}**{'' if libre else '  ·  no disponible aquí'} — "
                        f"{explicacion}")

        if not permitida:
            nota(f"<b>Modo IA cerrado en este módulo.</b> "
                 f"{_e(ficha.get('motivo_ia', 'Sin motivo declarado.'))}")
        elif not est["disponible"]:
            nota(f"<b>El componente de IA no está conectado.</b> {_e(est['motivo'])}")
        else:
            nota(f"<b>Conectado a {_e(est['proveedor'])} · modelo "
                 f"<code>{_e(est['modelo'])}</code>.</b> Temperatura 0, versión "
                 f"anclada y caché por contenido: el mismo documento se lee una vez "
                 f"y las siguientes salen de memoria. El juicio sigue siendo "
                 f"determinista — el modelo sólo lee.", acento=True)
            if est.get("aviso_modelo"):
                st.warning(est["aviso_modelo"])

        opciones = (list(llm.MODOS) if (est["disponible"] and permitida)
                    else ["determinista"])
        return st.radio("Modo", opciones, horizontal=True, key=f"modo_{clave}",
                        label_visibility="collapsed")


def panel_ia():
    """Estado y gasto del componente de IA, para el lateral."""
    est = llm.estado()
    if est["disponible"]:
        cuerpo = (f'<b style="color:#006300">IA conectada</b><br>'
                  f'<code>{_e(est["modelo"])}</code><br>'
                  f'{est["llamadas"]} llamada(s) · {est["cache"]} de caché'
                  + (f' · {est["esperas"]} espera(s)' if est.get("esperas") else "")
                  + (f' · <span style="color:#d03b3b">{est["errores"]} error(es)'
                     f'</span>' if est["errores"] else "")
                  + f'<br><span style="color:#898781">límite gratuito: '
                    f'{llm.LIMITE_POR_MINUTO}/min</span>')
        if est.get("aviso_modelo"):
            cuerpo += (f'<br><span style="color:#d03b3b">modelo sustituido — '
                       f'anclado: <code>{_e(est["modelo_anclado"])}</code></span>')
    else:
        cuerpo = '<b>IA no conectada</b><br>evaluación en modo determinista'
    st.markdown(f'<div style="font-size:.8rem;color:#52514e;line-height:1.7">'
                f'{cuerpo}</div>', unsafe_allow_html=True)


def diagnostico_modelos():
    """
    Qué modelos alcanza la clave. Va en el lateral, plegado, porque sólo hace
    falta cuando algo falla — y cuando falla, adivinar el nombre del modelo es
    exactamente lo que no hay que hacer.
    """
    if not llm.esta_disponible():
        return
    with st.expander("Modelos disponibles"):
        st.caption("Cuesta una llamada de catálogo, no de generación. Fija el que "
                   "quieras en `GEMINI_MODELO` dentro de Secrets para anclarlo sin "
                   "volver a desplegar.")
        if st.button("Consultar al proveedor", key="btn_modelos",
                     use_container_width=True):
            try:
                st.session_state["modelos"] = llm.listar_modelos()
            except llm.NoDisponible as e:
                st.error(str(e))
        for m in st.session_state.get("modelos", []):
            st.markdown(f"- `{m}`" + ("  ← en uso" if m == llm.modelo_en_uso() else ""))


VIAS_LECTURA = {
    "capa_texto": ("Texto del PDF", "p-bien", "▤"),
    "ocr": ("Reconocido por OCR", "p-acento", "◍"),
    "ninguna": ("No se ha podido leer", "p-mal", "✕"),
}


def tabla_documentos(docs, tipos, clasificar, extraer=None):
    """
    Qué ha podido leer el evaluador de cada documento, y por qué vía.

    Es la pantalla que faltaba, y faltaba en el peor sitio: sin ella, un aviso de
    «sin capa de texto» convivía con un hallazgo que citaba el pie de página del
    mismo documento —dos afirmaciones incompatibles sobre la misma hoja— y no
    había forma de saber cuál creerse. La causa era que este panel miraba `capa`,
    que sólo dice si el PDF traía texto, en vez de `legible`, que dice si el
    evaluador ha conseguido leerlo. Desde que hay OCR no son lo mismo.

    Enseña tres cosas por documento: **por dónde** ha entrado el texto, **cuánto**
    ha salido, y **qué campos** se han podido extraer. Y deja ver el texto
    reconocido tal cual, porque cuando una fecha no cuadra lo primero que hay que
    poder mirar es qué leyó exactamente la máquina.
    """
    def _tipo_de(d):
        legible = d.get("legible", d.get("capa"))
        return tipos.get(clasificar(d["texto"]) if legible else "sin_texto", "—")

    # Sin extractor de campos —la rama de auditoría no tiene ninguno— este panel
    # sólo puede decir por dónde ha entrado cada documento, y para eso una tabla
    # basta. Cuando sí lo hay, la tabla sobra: repetiría fila a fila las mismas
    # tres cifras que ya encabezan el bloque de cada documento, y lo que Íñigo
    # pidió es ver **lo que se ha sacado de ese documento**, no un resumen de
    # todos junto a él.
    if extraer is None:
        filas = []
        for d in docs:
            legible = d.get("legible", d.get("capa"))
            via = d.get("via", "capa_texto" if d.get("capa") else "ninguna")
            etiqueta, _, glifo = VIAS_LECTURA.get(via, VIAS_LECTURA["ninguna"])
            integ = d.get("integridad") or {}
            filas.append({
                "Documento": d["nombre"],
                "Lectura": f"{glifo} {etiqueta}",
                "Texto leído": (f"{len(d.get('texto') or ''):,} caracteres"
                                .replace(",", ".") if legible else "—"),
                "Páginas": (f"{integ.get('paginas_fichero') or '—'}"
                            + (f" de {integ['paginas_declaradas']}"
                               if integ.get("paginas_declaradas") else "")),
                "Identificado como": _tipo_de(d),
            })
        st.dataframe(pd.DataFrame(filas), use_container_width=True,
                     hide_index=True)

    leidos = [d for d in docs if d.get("legible", d.get("capa"))]
    porocr = [d for d in leidos if d.get("via") == "ocr"]
    ilegibles = [d for d in docs if not d.get("legible", d.get("capa"))]

    fila_kpis([
        kpi("Documentos leídos", f"{len(leidos)}/{len(docs)}",
            "con texto que el evaluador puede usar"),
        kpi("Por OCR", len(porocr), "escaneos sin capa de texto",
            acento=bool(porocr)),
        kpi("Sin leer", len(ilegibles), "no producen «sin incidencias»"),
    ])

    if ilegibles:
        st.error("**No se ha podido leer:** "
                 + ", ".join(d["nombre"] for d in ilegibles)
                 + ". Un documento escaneado que no se lee no produce «sin "
                   "incidencias»: produce «no se ha podido comprobar», y el "
                   "veredicto las separa.")
        for d in ilegibles:
            for f in (d.get("fallos_lectura") or []):
                st.caption(f"· {d['nombre']}: {f}")

    if not leidos or extraer is None:
        return

    CAMPOS_LEIDOS = [("fecha_emision", "Fecha de firma"),
                     ("fecha_inicio", "Fecha de inicio"),
                     ("anios_pactados", "Plazo (años)"),
                     ("fecha_caducidad", "Fecha de vencimiento"),
                     ("prorroga_tipo", "Prórroga"),
                     ("antelacion", "Preaviso"),
                     ("familia", "Familia documental"),
                     ("direccion_objeto", "Cadena documental")]

    st.markdown("**Qué ha sacado el evaluador de cada documento**")
    st.caption("Un bloque por documento, con lo que ha podido leer de él y lo que "
               "no. Un «no lo ha encontrado» **no acusa al módulo de nada**: es un "
               "límite de esta lectura, y el veredicto lo declara como tal en vez "
               "de contarlo contra quien escribió el módulo.")

    for d in leidos:
        via = d.get("via", "capa_texto")
        etiqueta, _tono, glifo = VIAS_LECTURA.get(via, VIAS_LECTURA["ninguna"])
        integ = d.get("integridad") or {}
        campos = {}
        if extraer is not None:
            try:
                campos = extraer(d["texto"])
            except Exception:
                campos = {}

        filas, encontrados = [], 0
        for clave, titulo in CAMPOS_LEIDOS:
            v = campos.get(clave)
            if clave == "antelacion" and isinstance(v, dict):
                v = f"{v['cantidad']} {v['unidad']} ({v['dias']} días)"
            vacio = v in (None, "", "no_consta", {}, [])
            encontrados += not vacio
            filas.append({"Campo": titulo,
                          "Lo que ha leído el evaluador":
                              "— no lo ha encontrado —" if vacio else str(v)})

        cabecera = (f"{d['nombre']}  ·  {encontrados} de {len(CAMPOS_LEIDOS)} "
                    f"campos leídos")
        with st.expander(cabecera, expanded=len(leidos) <= 3):
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"**Lectura**  \n{glifo} {etiqueta}")
            c2.markdown(f"**Texto**  \n"
                        f"{len(d.get('texto') or ''):,}".replace(",", ".")
                        + " caracteres")
            c3.markdown("**Páginas**  \n"
                        + f"{integ.get('paginas_fichero') or '—'}"
                        + (f" de {integ['paginas_declaradas']}"
                           if integ.get("paginas_declaradas") else ""))
            c4.markdown(f"**Identificado como**  \n{_tipo_de(d)}")

            st.dataframe(pd.DataFrame(filas), use_container_width=True,
                         hide_index=True)

            if campos.get("ambiguedades"):
                st.warning("**No se ha elegido entre varios valores posibles:** "
                           + " · ".join(campos["ambiguedades"])
                           + ". Ante dos candidatos el evaluador se abstiene: "
                             "acertar la mayoría de las veces no sirve cuando "
                             "quien lee el veredicto no sabe cuál de las veces le "
                             "ha tocado.")

            for clave, titulo in (("cita_duracion", "duración"),
                                  ("cita_prorroga_tipo", "prórroga"),
                                  ("cita_emision", "fecha de firma")):
                if campos.get(clave):
                    st.caption(f"Cláusula de {titulo}: «"
                               + str(campos[clave])[:260].strip() + "…»")

            if via == "ocr":
                st.caption("Leído por OCR: lo que se compara con el módulo es una "
                           "lectura contra otra lectura, y el veredicto lo dice.")

            st.markdown("**Texto reconocido**")
            st.text_area("Texto reconocido", (d.get("texto") or "")[:20000],
                         height=220, key=f"txt_{d['nombre']}",
                         label_visibility="collapsed")
            if len(d.get("texto") or "") > 20000:
                st.caption(f"Se muestran los primeros 20.000 de "
                           f"{len(d['texto']):,} caracteres.".replace(",", "."))


def editor(registros, rama, clave):
    """
    Enseña lo que el intérprete ha entendido y deja corregirlo antes de puntuar.
    Las columnas salen de `rama.COLUMNAS`, así que la interfaz no sabe nada del
    módulo concreto que está mostrando.
    """
    if not registros:
        return []
    base = pd.DataFrame([rama.a_fila(r) for r in registros])
    config = {}
    for _, etiqueta, tipo, opciones in rama.COLUMNAS:
        if etiqueta not in base.columns:
            continue
        if tipo == "opcion":
            config[etiqueta] = st.column_config.SelectboxColumn(options=opciones)
        elif tipo == "bool":
            config[etiqueta] = st.column_config.CheckboxColumn()
    editadas = st.data_editor(base, num_rows="dynamic", use_container_width=True,
                              hide_index=True, key=clave, column_config=config)
    salida = []
    for _, f in editadas.iterrows():
        try:
            r = rama.de_fila(f)
        except Exception:
            continue
        if r.get("campo") or r.get("id_documento"):
            salida.append(r)
    return salida


def bloque_procedencia(procedencias, modo):
    """
    Qué dato lo ha puesto una regla y cuál un modelo — y cuál ha rechazado el
    evaluador.

    Sin esto, el modo asistido sería una caja negra justo donde más falta hace
    verla: un veredicto que se apoya en una fecha leída por un modelo tiene que
    poder decir que esa fecha la leyó un modelo. Y cuando el modelo devuelve algo
    que no encaja con el esquema de la rama —un campo inventado, una fecha que no
    es una fecha— el valor no entra: se descarta y se enseña descartado.
    """
    if modo == "determinista" or not procedencias:
        return

    filas, descartes = [], []
    for documento, campos in sorted(procedencias.items()):
        for campo, origen in sorted(campos.items()):
            if origen.startswith("modelo (descartado"):
                descartes.append({"Documento": documento, "Campo": campo,
                                  "Motivo del descarte": origen.split(": ", 1)[-1]
                                                              .rstrip(")")})
            else:
                filas.append({"Documento": documento, "Campo": campo,
                              "Lo ha puesto": origen})

    with st.expander(f"Procedencia de cada dato · lectura en modo {modo}",
                     expanded=bool(descartes)):
        st.caption("Un veredicto que se apoya en un dato leído por un modelo tiene "
                   "que poder decirlo. La regla manda siempre que encuentra el "
                   "valor; el modelo sólo rellena huecos.")
        del_modelo = sum(1 for f in filas if f["Lo ha puesto"] == "modelo")
        fila_kpis([
            kpi("Datos por regla", sum(1 for f in filas if f["Lo ha puesto"] == "regla"),
                "deterministas y reproducibles"),
            kpi("Datos por modelo", del_modelo, "leídos por el modelo",
                acento=bool(del_modelo)),
            kpi("Descartados", len(descartes), "no han superado un control"),
        ])
        if descartes:
            # Tres controles distintos, y conviene no confundirlos al leerlos: el
            # primero mira la forma del dato, el segundo si el documento lo dice y
            # el tercero si el documento se contradice. Sólo el segundo y el
            # tercero hablan de si el valor es CIERTO.
            CONTROLES = [
                ("no aparece en el documento", "Anclaje",
                 "el fragmento que el modelo cita para sostener el valor no está "
                 "en el texto. El valor no entra aunque fuese correcto: lo que "
                 "no se puede comprobar no se puede afirmar."),
                ("daría", "Aritmética",
                 "el valor no cuadra con los otros datos del propio documento."),
                ("posterior", "Aritmética",
                 "el valor no cuadra con los otros datos del propio documento."),
            ]
            for f in descartes:
                m = f["Motivo del descarte"]
                f["Control"] = next((n for clave, n, _ in CONTROLES if clave in m),
                                    "Esquema")
            st.warning(
                "**Valores que el modelo propuso y el evaluador no ha aceptado.** "
                "No es un fallo del módulo evaluado ni cuenta contra él: es el "
                "evaluador negándose a sostener un dato que no puede comprobar. "
                "Un valor sin respaldo circulando por el núcleo es peor que un "
                "hueco, porque el hueco se ve y el otro no.")
            st.dataframe(pd.DataFrame(descartes)[
                ["Documento", "Campo", "Control", "Motivo del descarte"]],
                use_container_width=True, hide_index=True)
            st.caption("**Esquema** — el valor no tenía la forma declarada. "
                       "**Anclaje** — la cita que lo sostenía no está en el "
                       "documento. **Aritmética** — contradice a los demás datos "
                       "del mismo documento.")
        if filas:
            st.dataframe(pd.DataFrame(filas), use_container_width=True,
                         hide_index=True)


def bloque_contraste(ficha, ev):
    c = ev["contraste"]
    uni, unis = ficha["unidad"]
    st.subheader("Contraste independiente")
    st.caption("El evaluador calcula el resultado correcto leyendo los documentos. "
               "Las cifras siguientes no proceden del módulo evaluado.")

    fila_medidores([
        medidor("Exhaustividad", c["exhaustividad"],
                f"de {unis} que el evaluador determina por su cuenta"),
        medidor("Precisión", c["precision"],
                "de lo emitido se sostiene documentalmente"),
    ])
    fila_kpis([
        kpi("Calculado por el evaluador", c["n_esperados"], "de forma independiente"),
        kpi("Emitido por el módulo", c["n_reportados"], "registros interpretados"),
    ])

    if ev.get("tabla_contraste"):
        st.dataframe(pd.DataFrame(ev["tabla_contraste"]),
                     use_container_width=True, hide_index=True)
        st.caption("Señalar la unidad correcta no basta: si lo emitido cita valores "
                   "que contradicen los documentos, no cuenta como acierto.")

    if c["omitidas"]:
        st.error("No reportado por el módulo: " + _listar(c["omitidas"]))
    if c["con_error"]:
        st.error("Reportado con valores que contradicen los documentos: "
                 + "; ".join(f"{_nombre(m['esperado'])} {m['motivo']}"
                             for m in c["motivos"]))
    if c["falsas"]:
        st.error("Emitido sin respaldo documental: " + _listar(c["falsas"]))
    if c["duplicadas"]:
        st.warning("Emitido más de una vez: " + _listar(c["duplicadas"]))


def _nombre(x):
    return x.get("etiqueta") or x.get("id_documento") or x.get("campo") or "—"


def _listar(xs):
    return ", ".join(_nombre(x) for x in xs)


def bloque_hallazgos(ev):
    if not ev.get("hallazgos"):
        return
    st.subheader("Hallazgos de cobertura")
    st.caption("No puntúan en la batería. O son comprobaciones que el módulo no "
               "realiza —y no hacer algo no equivale a hacerlo mal— o son "
               "observaciones sobre el dato que viaja aguas abajo.")
    for h in ev["hallazgos"]:
        with st.expander(h["titulo"], expanded=True):
            st.write(h["detalle"])
            st.markdown(f"**Por qué importa:** {h['porque_importa']}")
            if h.get("tabla"):
                st.dataframe(pd.DataFrame(h["tabla"]), use_container_width=True,
                             hide_index=True)


def bloque_casos(ficha, ev):
    st.subheader("Resultado caso a caso")
    r = B.resumen(ev["casos"])
    barra_bateria(r)

    origen = ficha.get("origen_casos", {})
    filas = []
    for n, caso in sorted(ev["casos"].items()):
        clase, glifo, palabra = TONO_CASO[caso["resultado"]]
        marca = (f'<span class="origen">· {_e(origen[n])}</span>'
                 if n in origen else "")
        pie = ""
        if caso.get("requiere"):
            pie = (f'<div class="requiere">Para ejercitarlo hace falta: '
                   f'{_e(caso["requiere"])}</div>')
        elif caso.get("evidencia"):
            pie = (f'<div class="requiere">Evidencia: {_e(caso["evidencia"])}</div>')

        # Esperado y observado, uno al lado del otro. La observación explica el
        # porqué; esto deja ver la comparación sin leerla.
        desglose = ""
        if caso.get("esperado") and caso.get("observado"):
            desglose = (f'<div class="desglose">'
                        f'<div><span>Esperado</span>{_e(caso["esperado"])}</div>'
                        f'<div><span>Observado</span>{_e(caso["observado"])}</div>'
                        f'</div>')

        # La severidad sólo se enseña donde significa algo: en un fallo. Un caso
        # pendiente o no aplicable no tiene fallo que graduar, y pintarle un riesgo
        # lo haría parecer un problema del módulo.
        sev = PL.severidad_de(ficha, n)
        marca_sev = ""
        if caso["resultado"] == "no_pasa" and sev in B.SEVERIDADES:
            nombre, _, color = B.SEVERIDADES[sev]
            marca_sev = (f'<div class="sev" style="color:{color};'
                         f'border-color:{color}33">{_e(nombre)}</div>')

        filas.append(
            f'<div class="caso caso--{caso["resultado"]}">'
            f'<div class="n">{n}</div><div class="cuerpo">'
            f'<div class="titulo">{_e(ficha["casos"][n])}{marca}</div>'
            f'<div class="obs">{_e(caso["observacion"])}</div>{desglose}{pie}</div>'
            f'<div>{pastilla(palabra, clase, glifo)}{marca_sev}</div></div>')
    st.markdown("".join(filas), unsafe_allow_html=True)

    st.caption("**Pendiente** es un caso que aplica a estos datos y al que le falta "
               "algo que puedo conseguir sin cambiar de pedido. **No aplica** es un "
               "caso que mide una situación que este conjunto no contiene: no dice "
               "nada del módulo, dice qué le falta al banco de pruebas. Ninguno de "
               "los dos entra en la tasa de acierto.")

    return pd.DataFrame(PL.filas(ficha, ev))


def bloque_evidencia(rama, clave):
    """
    Los casos de alcance «módulo» no se deducen de la salida pegada: o el módulo
    tiene esa propiedad o no la tiene, y eso vale para todos sus pedidos. Se
    declaran aquí, y el veredicto dice de dónde sale el juicio — si no, el
    resultado no sería verificable por nadie más.
    """
    evidencias = dict(getattr(rama, "EVIDENCIAS", {}) or {})
    if not evidencias:
        return {}
    with st.expander("Evidencia sobre el módulo · casos que no se leen de la salida",
                     expanded=False):
        st.caption("Estos casos no dependen del pedido concreto que estés evaluando. "
                   "Se comprueban una vez sobre el módulo y el resultado vale para "
                   "todos sus pedidos.")
        salida = {}
        for n, e in sorted(evidencias.items()):
            st.markdown(f"**Caso {n} · {rama.FICHA['casos'][n]}**")
            st.caption(e["pregunta"] + "  ·  Cómo comprobarlo: " + e["como_comprobarlo"])
            constatado = st.checkbox("Constatado", value=e.get("constatado", False),
                                     key=f"ev_{clave}_{n}")
            nota_txt = st.text_area("Qué se ha observado", value=e.get("nota", ""),
                                    key=f"evn_{clave}_{n}", height=90)
            origen = st.text_input("De dónde sale esta evidencia",
                                   value=e.get("origen", ""), key=f"evo_{clave}_{n}")
            salida[n] = {**e, "constatado": constatado, "nota": nota_txt,
                         "origen": origen}
        return salida


def bloque_requisitos(ficha, er):
    """Lo que hay que pedir para poder ejercitar la batería entera."""
    if not er.get("requisitos"):
        return
    st.subheader("Qué falta para ejercitar la batería completa")
    st.caption("Ninguno de estos puntos es un defecto del módulo: son datos que el "
               "banco de pruebas todavía no tiene. Esta lista es la que hay que "
               "mandarle al compañero.")
    st.dataframe(pd.DataFrame([{
        "Caso": q["caso"], "Título": ficha["casos"].get(q["caso"], ""),
        "Estado": B.TEXTO[q["estado"]], "Qué haría falta": q["requiere"],
    } for q in er["requisitos"]]), use_container_width=True, hide_index=True)


def bloque_veredicto(er):
    st.subheader("EvaluationResult")
    st.write(er["valoracion"])
    if er["aspectos"]:
        st.markdown("**Aspectos a mejorar**")
        for i, a in enumerate(er["aspectos"], 1):
            etq = B.ETIQUETA_CASO[a["estado"]]
            with st.expander(f"{i}.  {a['titulo']}   ·   caso {a['caso']} ({etq})"):
                st.write(a["detalle"])
                st.markdown(f"**Corrección propuesta:** {a['correccion']}")
    else:
        st.success("No se han emitido aspectos a mejorar.")


# ===========================================================================
# Panel de jueces
# ===========================================================================

def _tabla_criterios(panel):
    filas = []
    for c in panel["criterios"]:
        _, glifo, palabra = TONO_CRITERIO[c["veredicto"]]
        filas.append({
            "Criterio": c["titulo"],
            "Veredicto": f"{glifo} {palabra}",
            "Acuerdo": f"{int(c['acuerdo'] * 100)}%",
            **{p: f"{J.GLIFO[v['veredicto']]} {J.TEXTO[v['veredicto']]}"
               for p, v in zip(panel["perspectivas"], c["votos"])},
        })
    return pd.DataFrame(filas)


def _panel_criterios(ficha, evidencia, clave):
    """
    Los criterios que ninguna regla alcanza, sometidos a un panel de jueces.

    Se enseña siempre, incluso cuando no puede ejecutarse: un criterio diseñado y
    cerrado dice qué se podría medir y por qué hoy no se mide. Lo que nunca se
    hace es inventar un resultado para rellenar el hueco.
    """
    criterios = ficha.get("cualitativos") or []
    if not criterios:
        return None

    st.markdown("**Criterios cualitativos · panel de jueces**")
    st.caption("Lo que ninguna regla puede comprobar: si la salida es accionable, "
               "si justifica lo que afirma, si distingue lo que sabe de lo que "
               "supone. Tres jueces independientes con lentes declaradas, "
               "temperatura 0 y unanimidad obligatoria para puntuar. Estos "
               "criterios se informan aparte y no alteran las métricas "
               "deterministas.")

    permitido = ficha.get("panel_permitido", False)
    est = llm.estado()

    if not permitido:
        nota(f"<b>Panel cerrado en este módulo.</b> "
             f"{_e(ficha.get('motivo_panel', 'Sin motivo declarado.'))}")
    elif not est["disponible"]:
        nota(f"<b>El componente de IA no está conectado.</b> {_e(est['motivo'])} "
             f"Los criterios quedan diseñados y sin ejecutar.")

    with st.expander(f"Los {len(criterios)} criterios y por qué están en la batería"):
        for c in criterios:
            st.markdown(f"**{c['titulo']}**  \n{c['pregunta']}")
            st.caption(f"Por qué importa: {c['porque_importa']}")

    if not (permitido and est["disponible"]):
        return None

    guardado = st.session_state.get(f"panel_{clave}")
    if guardado is None:
        c = J.coste(criterios, evidencia)
        st.caption(f"Coste: **{c['nuevas']} llamada(s)** — un juez, una llamada, "
                   f"con los {len(criterios)} criterios de golpe. "
                   + (f"{c['en_cache']} sale(n) de caché. " if c["en_cache"] else "")
                   + f"El nivel gratuito da {llm.LIMITE_POR_MINUTO} peticiones por "
                     f"minuto, así que el sistema espera entre llamadas si hace "
                     f"falta: puede tardar unos segundos.")
        if not st.button("Convocar al panel", key=f"btn_panel_{clave}"):
            return None
        with st.spinner("Los jueces están leyendo la salida… "
                "(el sistema espera entre llamadas para no agotar la cuota)"):
            try:
                guardado = J.evaluar_panel(criterios, evidencia)
            except llm.NoDisponible as e:
                st.error(f"El panel no ha podido ejecutarse: {e}")
                return None
        st.session_state[f"panel_{clave}"] = guardado

    panel = guardado
    f = panel.get("fleiss") or {}
    fila_kpis([
        kpi("Criterios con acuerdo", f"{panel['puntuables']}/{panel['total']}",
            f"regla: {panel['regla']}"),
        kpi("Cumple", panel["cumple"],
            f"{panel['tasa']}% de los que puntúan" if panel["tasa"] is not None
            else "sin criterios puntuables", acento=True),
        kpi("En discrepancia", panel["discrepancia"], "requieren arbitraje"),
        kpi("κ de Fleiss",
            f["kappa"] if f.get("kappa") is not None else "—",
            f.get("lectura", "no definida")),
    ])

    st.dataframe(_tabla_criterios(panel), use_container_width=True, hide_index=True)

    for c in panel["criterios"]:
        _, glifo, palabra = TONO_CRITERIO[c["veredicto"]]
        with st.expander(f"{glifo}  {c['titulo']}   ·   {palabra}"
                         f"   ·   acuerdo {int(c['acuerdo'] * 100)}%"):
            st.write(c["justificacion"] or "—")
            if c["cita"]:
                st.markdown("**Se apoya en:**")
                st.code(c["cita"], language=None)
            if c["veredicto"] == "discrepancia":
                st.warning(f"El panel no coincide ({', '.join(c['discrepan'])}). "
                           f"El criterio no se resuelve por mayoría: queda "
                           f"declarado. {c['requiere']}")
            st.caption(f"Por qué importa: {c['porque_importa']}")
            st.markdown("**Voto por voto**")
            for p, v in zip(panel["perspectivas"], c["votos"]):
                st.markdown(f"- *{p}* → **{J.TEXTO[v['veredicto']]}** — "
                            f"{v['justificacion'] or '—'}")

    if f.get("kappa") is not None:
        nota(f"<b>κ = {f['kappa']}</b> ({_e(f['lectura'])}). El acuerdo bruto es "
             f"{int(f['acuerdo_bruto'] * 100)}%, pero {int(f['esperado_por_azar'] * 100)}% "
             f"saldría solo por cómo se reparten los votos; kappa descuenta esa "
             f"parte. Un panel que dijera «cumple» a todo tendría acuerdo perfecto "
             f"y κ = 0: no estaría discriminando nada.", acento=True)
    elif f.get("motivo"):
        nota(_e(f["motivo"]))

    return panel


# ===========================================================================
# Informe redactado
# ===========================================================================

def bloque_evolucion(ficha, er, ev, clave):
    """
    Qué ha cambiado desde la última evaluación registrada.

    Es la mitad que faltaba para poder decir que la evaluación produce aprendizaje
    y no sólo medida. Un fallo detectado demuestra que el evaluador discrimina; un
    fallo detectado, comunicado y **después corregido**, con el cambio medido por
    el mismo banco que lo encontró, demuestra que ha servido para algo.
    """
    hist = H.leer(ficha["id"])
    anterior = hist[-1] if hist else None
    comp = H.comparar(anterior, H.instantanea(ficha, er, ev), ficha)

    st.subheader("Evolución")
    if comp and (comp["mejoras"] or comp["regresiones"]):
        for m in comp["mejoras"]:
            st.success(f"**Caso {m['caso']} · {_e(m['titulo'])}** — "
                       f"{H.TEXTO_CAMBIO[m['cambio']]}")
        for r in comp["regresiones"]:
            st.error(f"**Caso {r['caso']} · {_e(r['titulo'])}** — "
                     f"{H.TEXTO_CAMBIO[r['cambio']]}")
        if comp["deltas"]:
            fila_kpis([kpi(k.capitalize(),
                           f"{d['antes']} → {d['ahora']}",
                           f"{'+' if d['delta'] > 0 else ''}{d['delta']}",
                           acento=d["delta"] > 0)
                       for k, d in sorted(comp["deltas"].items())])
    st.caption(H.texto_evolucion(comp, ficha["nombre"]))

    c1, c2 = st.columns([2, 1])
    nota_txt = c1.text_input("Nota de esta evaluación (opcional)",
                             key=f"nota_{clave}",
                             placeholder="p.ej. tras la corrección del is_active")
    if c2.button("Registrar esta evaluación", key=f"btn_hist_{clave}",
                 use_container_width=True):
        H.registrar(ficha, er, ev, nota_txt)
        st.rerun()
    st.caption("Registrar es afirmar que esta evaluación cuenta. Se hace a mano a "
               "propósito: si el historial se llenara de pruebas a medias, el "
               "antes/después dejaría de significar nada.")

    if hist:
        with st.expander(f"Historial completo · {len(hist)} evaluación(es) registradas"):
            st.dataframe(pd.DataFrame([{
                "Fecha": x["fecha"], "Evaluado": x["sujeto"],
                "Tasa": f"{x['metricas']['tasa']}%",
                "Cobertura": f"{x['metricas']['cobertura']}%",
                "Exhaustividad": f"{x['metricas']['exhaustividad']}%",
                "Precisión": f"{x['metricas']['precision']}%",
                "Nota": x.get("nota", "")} for x in hist]),
                use_container_width=True, hide_index=True)
            st.download_button("Descargar el historial (Markdown)",
                               H.a_markdown(ficha, hist).encode("utf-8"),
                               file_name=f"historial_{ficha['id']}.md",
                               mime="text/markdown", key=f"dl_hist_{clave}",
                               use_container_width=True)
    return comp


def bloque_asesor(ficha, er, ev, evidencia, clave, nombre):
    """
    El último eslabón: qué hacer con lo que la evaluación ha encontrado.

    Aquí se juntan las dos mitades. Los fallos deterministas dicen qué está mal
    con evidencia dura; el panel de jueces dice si la salida falla en algo que
    ninguna regla mide. El asesor recibe las dos cosas y produce lo único que no
    sale de ninguna de ellas por separado: un diagnóstico y un orden.

    El panel ya no tiene bloque propio. Su resultado entra aquí porque ésa es su
    función: alimentar el consejo, no vivir en una tabla al lado.
    """
    st.subheader("Qué mejorar")
    st.caption("El veredicto ya está calculado. Esto no lo cambia: lo interpreta. "
               "Agrupa por causa, cruza lo que miden las reglas con lo que sólo "
               "puede juzgarse leyendo, y ordena por lo que más daño hace aguas "
               "abajo. Cada recomendación va anclada al caso que la sostiene.")

    r = B.resumen(ev["casos"])
    if not (r["no_pasa"] or r["pendiente"]):
        st.success("Todos los casos con evidencia se superan. No hay nada que "
                   "recomendar sobre esta ejecución: lo que queda es ampliar el "
                   "banco de pruebas.")
        return None

    # 1 — lo cualitativo, si la rama lo permite y hay IA
    panel = _panel_criterios(ficha, evidencia, clave)

    # 2 — el consejo
    guardado = st.session_state.get(f"asesor_{clave}")
    if guardado is None:
        est = llm.estado()
        if est["disponible"]:
            c = AS.coste(ficha, er, ev, panel)
            st.caption("Coste: 1 llamada." if c["nuevas"] else
                       "Coste: 0 llamadas, este consejo ya está en caché.")
        if not st.button("Pedir el plan de mejora", key=f"btn_asesor_{clave}",
                         type="primary"):
            return panel
        with st.spinner("Cruzando fallos y criterios…"):
            guardado = AS.aconsejar(ficha, er, ev, panel)
        st.session_state[f"asesor_{clave}"] = guardado

    res = guardado
    if res.get("aviso"):
        st.warning(res["aviso"])

    if res["origen"] == "modelo":
        nota("<b>Recomendaciones sobre el veredicto ya calculado.</b> El modelo no "
             "ve los documentos: sólo casos, severidades y hallazgos. Y cada "
             "recomendación tiene que citar un caso fallido o pendiente — si no lo "
             "cita, se descarta entera en vez de corregirla.", acento=True)

    if res.get("diagnostico"):
        st.markdown(f"**{_e(res['diagnostico'])}**")

    for i, rec in enumerate(res["recomendaciones"], 1):
        sevs = [PL.severidad_de(ficha, n) for n in rec.get("casos") or []]
        peor = next((x for x in B.ORDEN_SEVERIDAD if x in sevs), None)
        color = B.SEVERIDADES[peor][2] if peor in B.SEVERIDADES else "#898781"
        with st.container(border=True):
            st.markdown(
                f'<div style="border-left:4px solid {color};padding-left:.75rem">'
                f'<b>{i}. {_e(rec["titulo"])}</b><br>'
                f'<span style="font-size:.78rem;color:#898781">'
                f'casos {", ".join(str(c) for c in rec["casos"])}'
                + (f' · criterios: {_e(", ".join(rec["criterios"]))}'
                   if rec.get("criterios") else "")
                + (f' · severidad {_e(B.SEVERIDADES[peor][0].lower())}'
                   if peor in B.SEVERIDADES else "")
                + '</span></div>', unsafe_allow_html=True)
            if rec.get("por_que_primero"):
                st.caption(rec["por_que_primero"])
            st.markdown(f"**Qué cambiar:** {_e(rec['que_cambiar'])}")
            st.markdown(f"**Cómo comprobar que quedó arreglado:** "
                        f"{_e(rec['como_comprobarlo'])}")

    if res.get("descartadas"):
        with st.expander(f"{len(res['descartadas'])} recomendación(es) descartadas "
                         f"por no anclarse a ningún caso"):
            st.caption("Un consejo sin evidencia que lo sostenga es justo el tipo de "
                       "afirmación que este sistema le reprocha a los módulos que "
                       "evalúa. No se corrigen: se descartan y se cuentan.")
            for d in res["descartadas"]:
                st.markdown(f"- **{_e(d.get('titulo', '—'))}** — {_e(d['motivo'])}")

    st.download_button("Descargar el plan de mejora (Markdown)",
                       AS.a_markdown(ficha, er, res).encode("utf-8"),
                       file_name=f"plan_mejora_{nombre}.md", mime="text/markdown",
                       key=f"dl_asesor_{clave}", use_container_width=True)
    return panel


def bloque_informe(ficha, er, ev, panel, clave, nombre):
    """
    El informe que se le manda al compañero.

    El veredicto ya está calculado: aquí sólo se redacta. Y lo redactado pasa por
    un control determinista de cifras antes de entregarse, porque el riesgo real
    de un texto generado no es que escriba mal, es que escriba un porcentaje que
    nadie calculó.
    """
    st.subheader("Informe para el responsable del módulo")
    st.caption("El veredicto ya está calculado; el modelo sólo lo redacta. Después "
               "se verifica automáticamente que toda cifra del texto exista en los "
               "resultados. Sin IA disponible el informe se genera igual, con "
               "plantilla determinista, y lo declara.")

    est = llm.estado()
    incluir = bool(ficha.get("ia_permitida", False))
    if est["disponible"] and not incluir:
        nota(f"<b>Redacción con detalle recortado.</b> Los documentos de este "
             f"módulo no pueden salir del sistema, así que al redactor sólo le "
             f"llegan métricas, títulos de caso y correcciones propuestas: las "
             f"observaciones que citan valores del documento se quedan fuera. El "
             f"detalle completo sigue estando en el EvaluationResult exportable.")

    guardado = st.session_state.get(f"informe_{clave}")
    if guardado is None:
        if est["disponible"]:
            c = INF.coste(ficha, er, ev, panel)
            st.caption("Coste: 1 llamada." if c["nuevas"] else
                       "Coste: 0 llamadas, este informe ya está en caché.")
        if not st.button("Redactar el informe", key=f"btn_informe_{clave}",
                         type="primary"):
            return
        with st.spinner("Redactando…"):
            guardado = INF.generar(ficha, er, ev, panel)
        st.session_state[f"informe_{clave}"] = guardado

    inf = guardado
    if inf.get("aviso"):
        st.warning(inf["aviso"])

    v = inf.get("verificacion")
    if v and not v["ok"]:
        st.error(f"Control de cifras: el texto contiene {len(v['intrusas'])} "
                 f"número(s) que no figuran en los resultados calculados "
                 f"({', '.join(v['intrusas'])}). El informe se entrega marcado; "
                 f"revísalos antes de enviarlo.")
    elif v:
        st.success(f"Control de cifras superado: las {v['cifras_en_texto']} cifras "
                   f"del texto figuran en los resultados calculados.")

    with st.container(border=True):
        st.markdown(inf["texto"])

    st.download_button("Descargar el informe (Markdown)",
                       inf["texto"].encode("utf-8"),
                       file_name=f"informe_{nombre}.md", mime="text/markdown",
                       key=f"dl_informe_{clave}", use_container_width=True)


def bloque_severidad(ficha, ev):
    """
    Los fallos ordenados por lo que provocan aguas abajo, no por número de caso.

    Dos fallos no pesan igual. Uno que se propaga sin dejar rastro y otro que
    obliga a rehacer trabajo a mano son problemas distintos, y una lista numerada
    los presenta como si fueran el mismo. La severidad va declarada en la ficha de
    la rama **antes** de ejecutar: si se asignara al ver el resultado, dejaría de
    clasificar el riesgo para justificar la nota.
    """
    sev = PL.fallos_por_severidad(ficha, ev)
    if not sev["peor"] and not sev["sin_declarar"]:
        return

    st.subheader("Fallos por severidad")
    st.caption("La severidad mide qué ocurre aguas abajo si el fallo pasa "
               "desapercibido, no cuánto molesta. Se declara al diseñar el caso, "
               "antes de saber si el módulo lo supera.")

    for clave in B.ORDEN_SEVERIDAD:
        grupo = sev["grupos"][clave]
        if not grupo:
            continue
        nombre, criterio, color = B.SEVERIDADES[clave]
        st.markdown(f'<div style="border-left:4px solid {color};padding-left:.8rem;'
                    f'margin:.7rem 0 .4rem 0"><b style="color:{color}">{_e(nombre)}'
                    f'</b><div style="font-size:.84rem;color:#52514e">'
                    f'{_e(criterio)}</div></div>', unsafe_allow_html=True)
        for x in grupo:
            with st.container(border=True):
                st.markdown(f"**Caso {x['caso']} · {_e(x['titulo'])}**")
                if x["esperado"] and x["observado"]:
                    a, b = st.columns(2)
                    a.markdown(f"<span style='font-size:.7rem;font-weight:700;"
                               f"letter-spacing:.06em;color:#898781'>ESPERADO</span>"
                               f"<br>{_e(x['esperado'])}", unsafe_allow_html=True)
                    b.markdown(f"<span style='font-size:.7rem;font-weight:700;"
                               f"letter-spacing:.06em;color:#898781'>OBSERVADO</span>"
                               f"<br>{_e(x['observado'])}", unsafe_allow_html=True)
                st.caption(x["detalle"])

    if sev["sin_declarar"]:
        st.warning("Estos casos fallan y la rama no ha declarado su severidad. Es "
                   "una deuda del evaluador, no del módulo: "
                   + ", ".join(f"caso {x['caso']}" for x in sev["sin_declarar"]))


def exportar(ficha, er, ev, df, nombre, panel=None, entradas=""):
    st.subheader("Exportar")
    cob = PL.cobertura_severidad(ficha, ev)
    st.caption(f"La plantilla común lleva las cinco columnas acordadas: entradas, "
               f"resultado esperado, resultado observado, severidad y pasa/no pasa. "
               f"Severidad declarada en {cob['severidad']} de {cob['total']} casos; "
               f"esperado y observado desglosados en {cob['desglose']} de "
               f"{cob['total']}.")
    p1, p2 = st.columns(2)
    p1.download_button("Plantilla de evaluación (Markdown)",
                       PL.a_markdown(ficha, er, ev, entradas).encode("utf-8"),
                       file_name=f"plantilla_{nombre}.md", mime="text/markdown",
                       use_container_width=True, type="primary")
    p2.download_button("Plantilla de evaluación (CSV)",
                       pd.DataFrame(PL.filas(ficha, ev, entradas))
                       .to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"plantilla_{nombre}.csv", mime="text/csv",
                       use_container_width=True)
    e1, e2 = st.columns(2)
    e1.download_button("EvaluationResult (Markdown)",
                       V.a_markdown(ficha, er, ev, panel).encode("utf-8"),
                       file_name=f"evaluationresult_{nombre}.md",
                       mime="text/markdown", use_container_width=True)
    e2.download_button("Resultado caso a caso (CSV)",
                       df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"casos_{nombre}.csv", mime="text/csv",
                       use_container_width=True)
