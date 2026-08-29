"""
Panel de jueces: lo cualitativo, medido.

El problema
-----------
Hay criterios que ninguna regla captura. Una regla puede comprobar que el módulo
de Martín clasificó bien los seis contratos; no puede comprobar si el aviso que
emite sirve para algo, si afirma con la misma rotundidad lo que sabe y lo que no,
o si llama a la misma cosa de dos maneras distintas. Eso lo juzga alguien
leyendo. Y si lo juzga alguien leyendo, entra opinión.

La opinión no es el problema. El problema sería **esconderla**: dar un veredicto
cualitativo con la misma cara de dato duro que el resto del sistema.

La solución
-----------
No se pregunta a un juez. Se pregunta a varios, cada uno con una lente declarada,
y **sólo puntúa aquello en lo que coinciden**. Donde discrepan, el criterio no se
resuelve: se declara la discrepancia y sale como caso pendiente de arbitraje
humano, con la misma disciplina con la que un caso sin datos sale como pendiente.

El acuerdo entre jueces no es un detalle interno, es un resultado que se publica:

  · **acuerdo por criterio** — cuántos jueces están en la mayoría
  · **kappa de Fleiss** — acuerdo del panel entero corregido por azar. Sin la
    corrección, tres jueces que dijeran «cumple» a todo parecerían de acuerdo
    cuando en realidad no estarían discriminando nada.

Un kappa bajo no invalida el sistema: dice que ese criterio está mal formulado o
que el caso es de verdad ambiguo. Las dos cosas son información.

Por qué el panel es repetible
-----------------------------
Podría haber sacado la diversidad de la temperatura: subirla y dejar que cada
llamada saliera distinta. Habría sido un error. El evaluador penaliza a los
módulos que no repiten resultado, así que no puede tener dentro un componente que
no repite el suyo.

Aquí la diversidad viene de la **lente**, no del azar. Cada juez es una
instrucción distinta ejecutada a temperatura 0: individualmente determinista,
colectivamente diverso. El panel entero, con la caché por contenido, da el mismo
resultado las veces que se ejecute.
"""

from . import llm

# ---------------------------------------------------------------------------
# Las lentes
# ---------------------------------------------------------------------------
# Tres puntos de vista que en una revisión real estarían en la sala: quien tiene
# que usar la salida, quien tiene que dar fe de ella, y quien se limita a lo que
# el criterio dice sin extrapolar. No son «tres opiniones»: son tres formas de
# leer que fallan por sitios distintos, que es lo que hace que su coincidencia
# signifique algo.

PERSPECTIVAS = {
    "destinatario": (
        "Destinatario",
        "Eres quien recibe esta salida y tiene que actuar con ella, sin acceso a "
        "los documentos de origen ni al código del módulo. Juzgas si lo que lees "
        "te permite hacer tu trabajo: si sabes qué pasa, con qué elemento y qué "
        "tienes que hacer a continuación. No te importa la elegancia; te importa "
        "poder actuar sin volver a preguntar."),
    "auditor": (
        "Auditor",
        "Eres un auditor externo. Buscas afirmaciones que la salida no sostiene: "
        "cosas dadas por ciertas sin respaldo, seguridad mayor de la que los datos "
        "permiten, silencios que se leen como conformidad. Tu sesgo es la "
        "desconfianza: ante la duda, el criterio no se cumple."),
    "literal": (
        "Literal",
        "Te ciñes exactamente a lo que pregunta el criterio, ni un milímetro más. "
        "No extrapolas, no juzgas nada que el criterio no mencione y no penalizas "
        "defectos reales que caigan fuera de la pregunta. Si el criterio se cumple "
        "en sus términos, se cumple, aunque la salida tenga otros problemas."),
}

ORDEN_PERSPECTIVAS = ["destinatario", "auditor", "literal"]

VEREDICTOS = ("cumple", "no_cumple", "no_valorable")

TEXTO = {"cumple": "Cumple", "no_cumple": "No cumple",
         "no_valorable": "No valorable", "discrepancia": "Discrepancia"}
COLOR = {"cumple": "#0ca30c", "no_cumple": "#d03b3b",
         "no_valorable": "#898781", "discrepancia": "#52514e"}
GLIFO = {"cumple": "✔", "no_cumple": "✖", "no_valorable": "○", "discrepancia": "≠"}

ESQUEMA_VOTO = {
    "type": "object",
    "required": ["veredicto", "justificacion"],
    "properties": {
        "veredicto": {"enum": list(VEREDICTOS)},
        "justificacion": {"type": "string"},
        "cita": {"type": ["string", "null"]},
    },
}

# Un juez vota **todos** los criterios en una sola llamada.
#
# La versión anterior hacía una llamada por criterio y por juez: con cuatro
# criterios eran doce peticiones, y el nivel gratuito del proveedor da cinco por
# minuto. No fallaba por un error de código, fallaba por aritmética.
#
# Lo que importa metodológicamente es que **los jueces sean independientes entre
# sí** —que ninguno vea lo que votó otro—, y eso se mantiene intacto: siguen
# siendo tres llamadas separadas, con tres instrucciones distintas. Lo que se
# pierde es la independencia entre criterios *dentro* de un mismo juez, que es un
# precio menor y conviene declararlo en vez de disimularlo.
ESQUEMA_PANEL = {
    "type": "object",
    "required": ["votos"],
    "properties": {
        "votos": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["criterio", "veredicto", "justificacion"],
                "properties": {
                    "criterio": {"type": "string"},
                    "veredicto": {"enum": list(VEREDICTOS)},
                    "justificacion": {"type": "string"},
                    "cita": {"type": ["string", "null"]},
                },
            },
        },
    },
}

INSTRUCCION_COMUN = (
    "Estás evaluando la salida de un módulo de software dentro de un sistema de "
    "control de calidad. Te dan una lista de criterios y la evidencia sobre la que "
    "juzgarlos. Devuelves un voto por criterio, en el campo `votos`, usando como "
    "`criterio` el identificador exacto que se te da.\n\n"
    "Reglas que no puedes saltarte:\n"
    "· Juzgas cada criterio POR SEPARADO y sólo por lo que ese criterio pregunta. "
    "Que la salida falle en uno no predispone a que falle en otro.\n"
    "· Te apoyas sólo en la evidencia que se te entrega. No supones lo que el "
    "módulo hace por dentro ni lo que probablemente quiso decir.\n"
    "· Si la evidencia no contiene lo necesario para juzgar el criterio, el "
    "veredicto es `no_valorable`. No es una salida cómoda: es la respuesta "
    "correcta cuando no hay con qué decidir, y usarla mal es tan grave como "
    "equivocarse de veredicto.\n"
    "· `justificacion`: una o dos frases, en español, diciendo por qué. Sin "
    "elogios y sin fórmulas de cortesía.\n"
    "· `cita`: el fragmento literal de la evidencia en el que te apoyas, o null "
    "si no hay ninguno. No lo reescribas ni lo resumas."
)


def criterio(id_, titulo, pregunta, porque_importa, requiere=None):
    """
    Un criterio cualitativo de una rama.

    `pregunta`       lo que se le plantea al juez, redactado para que se pueda
                     contestar sí o no con la evidencia delante
    `porque_importa` por qué merece estar en la batería. Va al informe: un
                     criterio que no se puede justificar no debería puntuar
    `requiere`       qué haría falta si el panel discrepa. Por defecto, arbitraje
    """
    return {"id": id_, "titulo": titulo, "pregunta": pregunta,
            "porque_importa": porque_importa,
            "requiere": requiere or ("Arbitraje humano: el panel no ha alcanzado "
                                     "acuerdo sobre este criterio.")}


# ---------------------------------------------------------------------------
# La votación
# ---------------------------------------------------------------------------

def _prompt(perspectiva):
    nombre, lente = PERSPECTIVAS[perspectiva]
    return f"{INSTRUCCION_COMUN}\n\n--- Tu punto de vista: {nombre} ---\n{lente}"


def _evidencia_texto(criterios, evidencia):
    """Todos los criterios y la evidencia, en una sola pieza de texto."""
    bloques = ["CRITERIOS A JUZGAR", ""]
    for c in criterios:
        bloques += [f"[{c['id']}] {c['titulo']}", f"    {c['pregunta']}", ""]
    bloques += ["EVIDENCIA", evidencia]
    return "\n".join(bloques)


def _voto_no_valorable(perspectiva, motivo):
    return {"perspectiva": perspectiva, "veredicto": "no_valorable",
            "justificacion": motivo, "cita": None}


def votar_todos(criterios, evidencia, perspectiva, sin_cache=False):
    """
    Un juez, todos los criterios, **una sola llamada**.

    Devuelve un diccionario {id_criterio: voto}. Un criterio que el juez no
    conteste sale como «no valorable» y se dice por qué: rellenar el hueco con una
    suposición sería inventar un voto que nadie emitió.
    """
    bruto = llm.consultar(_prompt(perspectiva), _evidencia_texto(criterios, evidencia),
                          ESQUEMA_PANEL, sin_cache)
    emitidos = {}
    for v in (bruto or {}).get("votos") or []:
        if not isinstance(v, dict):
            continue
        ident = str(v.get("criterio", "")).strip()
        veredicto = v.get("veredicto")
        if veredicto not in VEREDICTOS:
            emitidos[ident] = _voto_no_valorable(
                perspectiva, f"Voto no reconocido ({veredicto!r}); se cuenta como "
                             f"no valorable.")
            continue
        emitidos[ident] = {"perspectiva": perspectiva, "veredicto": veredicto,
                           "justificacion": (v.get("justificacion") or "").strip(),
                           "cita": (v.get("cita") or None)}

    return {c["id"]: emitidos.get(c["id"]) or _voto_no_valorable(
        perspectiva, "El juez no se ha pronunciado sobre este criterio.")
        for c in criterios}


def coste(criterios, evidencia, perspectivas=None):
    """
    Cuántas llamadas costaría el panel ahora mismo, descontando lo que ya está
    en caché. La interfaz lo enseña antes de ofrecer el botón: el gasto se ve
    antes de gastarlo, no después.
    """
    perspectivas = perspectivas or ORDEN_PERSPECTIVAS
    texto = _evidencia_texto(criterios, evidencia)
    total = len(perspectivas)
    nuevas = sum(1 for p in perspectivas
                 if not llm.en_cache(_prompt(p), texto, ESQUEMA_PANEL))
    return {"total": total, "nuevas": nuevas, "en_cache": total - nuevas,
            "criterios": len(criterios)}


def evaluar_criterio(crit, votos, unanimidad=True):
    """
    Un criterio ante el panel entero, con los votos ya emitidos.

    La regla de decisión es deliberadamente severa: **hace falta unanimidad para
    puntuar**. Con mayoría simple bastaría un juez discrepante para que el
    resultado dependiera de con qué lente se mire, y eso es exactamente lo que el
    sistema le reprocha a un módulo que no repite. Cuando no hay unanimidad no se
    inventa un veredicto intermedio: se declara `discrepancia`, que en la batería
    se comporta como un pendiente —ni a favor ni en contra del módulo— y arrastra
    un requisito de arbitraje.
    """
    emitidos = [v["veredicto"] for v in votos]

    cuenta = {v: emitidos.count(v) for v in VEREDICTOS}
    mayoritario = max(VEREDICTOS, key=lambda v: (cuenta[v], v == "no_cumple"))
    en_mayoria = cuenta[mayoritario]
    acuerdo = en_mayoria / len(votos) if votos else 0.0
    unanime = en_mayoria == len(votos)

    if unanime:
        veredicto = mayoritario
    elif not unanimidad and acuerdo > 0.5:
        veredicto = mayoritario
    else:
        veredicto = "discrepancia"

    # La justificación que se enseña es la del primer juez del bando que decide,
    # no una síntesis: sintetizar las tres sería volver a opinar por encima de
    # ellas, que es justo lo que este diseño evita.
    portavoz = next((v for v in votos if v["veredicto"] == mayoritario), None)

    return {**crit, "votos": votos, "cuenta": cuenta, "acuerdo": round(acuerdo, 2),
            "unanime": unanime, "veredicto": veredicto,
            "justificacion": portavoz["justificacion"] if portavoz else "",
            "cita": portavoz["cita"] if portavoz else None,
            "discrepan": sorted({v["veredicto"] for v in votos}) if not unanime else []}


# ---------------------------------------------------------------------------
# Acuerdo del panel: kappa de Fleiss
# ---------------------------------------------------------------------------

def kappa_fleiss(criterios_evaluados):
    """
    Acuerdo del panel corregido por azar.

    Sin corregir, un panel que contestara «cumple» a todo daría 100% de acuerdo y
    no habría discriminado nada. Kappa descuenta el acuerdo que saldría solo por
    la distribución de las respuestas, así que un panel que no discrimina se
    delata: su kappa cae a cero aunque su acuerdo bruto sea perfecto.

    Devuelve None cuando no está definida —menos de dos criterios, o todos los
    jueces en una única categoría—, y en ese caso se dice, en vez de enseñar un 1
    que no significaría nada.
    """
    filas = [c["cuenta"] for c in criterios_evaluados]
    N = len(filas)
    if N < 2:
        return {"kappa": None, "motivo": "Hacen falta al menos dos criterios "
                                         "para calcularla.", "n_criterios": N}
    n = sum(filas[0].values())
    if n < 2 or any(sum(f.values()) != n for f in filas):
        return {"kappa": None, "motivo": "El panel no ha votado todos los criterios "
                                         "con el mismo número de jueces.",
                "n_criterios": N}

    P = [(sum(v * v for v in f.values()) - n) / (n * (n - 1)) for f in filas]
    P_barra = sum(P) / N
    p = {v: sum(f[v] for f in filas) / (N * n) for v in VEREDICTOS}
    P_e = sum(x * x for x in p.values())

    if abs(1 - P_e) < 1e-12:
        return {"kappa": None, "n_criterios": N, "acuerdo_bruto": round(P_barra, 3),
                "motivo": ("Todos los jueces han emitido la misma categoría en todos "
                           "los criterios. El acuerdo es total, pero kappa no está "
                           "definida: no hay variabilidad que corregir.")}

    k = (P_barra - P_e) / (1 - P_e)
    return {"kappa": round(k, 3), "acuerdo_bruto": round(P_barra, 3),
            "esperado_por_azar": round(P_e, 3), "n_criterios": N, "n_jueces": n,
            "lectura": _leer_kappa(k), "motivo": None}


def _leer_kappa(k):
    """Escala de Landis y Koch, la habitual para acuerdo entre observadores."""
    if k < 0:
        return "peor que el azar"
    if k < 0.21:
        return "leve"
    if k < 0.41:
        return "aceptable"
    if k < 0.61:
        return "moderado"
    if k < 0.81:
        return "sustancial"
    return "casi perfecto"


# ---------------------------------------------------------------------------
# El panel entero
# ---------------------------------------------------------------------------

def evaluar_panel(criterios, evidencia, perspectivas=None, unanimidad=True):
    """
    Devuelve el mismo tipo de objeto que una batería determinista: recuentos, una
    tasa y una lista de lo que queda sin resolver. Así el bloque cualitativo se
    lee con la misma gramática que el resto del sistema, sin mezclarse con él.
    """
    perspectivas = perspectivas or ORDEN_PERSPECTIVAS

    # Una llamada por juez, no una por juez y criterio. Los jueces siguen sin
    # verse entre sí, que es la independencia que importa.
    por_juez = {p: votar_todos(criterios, evidencia, p) for p in perspectivas}

    evaluados = [
        evaluar_criterio(c, [por_juez[p][c["id"]] for p in perspectivas], unanimidad)
        for c in criterios]

    cuenta = {v: sum(1 for c in evaluados if c["veredicto"] == v)
              for v in ("cumple", "no_cumple", "discrepancia", "no_valorable")}
    puntuables = cuenta["cumple"] + cuenta["no_cumple"]

    return {
        "criterios": evaluados,
        "perspectivas": [PERSPECTIVAS[p][0] for p in perspectivas],
        "n_jueces": len(perspectivas),
        "total": len(evaluados),
        **cuenta,
        "puntuables": puntuables,
        "tasa": round(100 * cuenta["cumple"] / puntuables, 1) if puntuables else None,
        "acuerdo_medio": (round(sum(c["acuerdo"] for c in evaluados) / len(evaluados), 2)
                          if evaluados else None),
        "fleiss": kappa_fleiss(evaluados),
        "requisitos": [{"criterio": c["titulo"], "requiere": c["requiere"]}
                       for c in evaluados if c["veredicto"] == "discrepancia"],
        "regla": ("unanimidad" if unanimidad else "mayoría simple"),
    }


def texto_panel(panel):
    """Resumen en prosa, para el informe y para el Markdown exportado."""
    if not panel or not panel.get("criterios"):
        return ""
    f = panel.get("fleiss") or {}
    t = (f"Un panel de {panel['n_jueces']} jueces independientes "
         f"({', '.join(panel['perspectivas'])}) ha revisado "
         f"{panel['total']} criterios cualitativos. ")
    if panel["puntuables"]:
        t += (f"El panel ha alcanzado {panel['regla']} en {panel['puntuables']} de "
              f"ellos, y ahí el módulo cumple {panel['cumple']} "
              f"({panel['tasa']}%). ")
    if panel["discrepancia"]:
        t += (f"En {panel['discrepancia']} "
              f"criterio{'' if panel['discrepancia'] == 1 else 's'} los jueces no "
              f"coinciden: no se resuelve por mayoría, queda declarado y requiere "
              f"arbitraje. ")
    if panel["no_valorable"]:
        t += (f"Otro{'s' if panel['no_valorable'] != 1 else ''} "
              f"{panel['no_valorable']} no son valorables con la evidencia "
              f"aportada. ")
    if f.get("kappa") is not None:
        t += (f"El acuerdo entre jueces, corregido por azar, es κ = "
              f"{f['kappa']} ({f['lectura']}). ")
    elif f.get("motivo"):
        t += f["motivo"] + " "
    t += ("Estos criterios se informan aparte y no alteran las métricas "
          "deterministas: miden lo que ninguna regla puede medir, con un método "
          "que declara su propio margen de desacuerdo.")
    return t
