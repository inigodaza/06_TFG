"""
Quién puede validar qué. La ontología de Pablo, convertida en algo comprobable.

Por qué existe
--------------
El módulo de Mencía no se limita a registrar quién resolvió una contradicción:
distingue entre **proponer** y **validar**. Cuando alguien sin autoridad
suficiente resuelve, su decisión queda como propuesta y la pantalla dice
«pendiente de validación por quien tiene autoridad sobre *Producción*».

Esa frase da por supuesto un mapa —qué rol manda sobre qué ámbito— que **no vive
en su módulo**. Vive en el de Pablo, que hasta ahora era una lámina. Este fichero
lo convierte en dato, y con eso aparece el primer caso del sistema que **no se
puede comprobar mirando un solo módulo**:

    ¿Quien validó esta contradicción tenía autoridad sobre su categoría,
    según el organigrama que declara la organización?

Ni Mencía puede contestarlo sola —no tiene el organigrama— ni Pablo puede
contestarlo solo —no tiene las validaciones—. El evaluador tiene los dos.

Una nota sobre la procedencia
------------------------------
La matriz llegó como una página HTML **entregada por el propio Pablo**, y este
JSON es su transcripción literal: los ocho roles, sus niveles, sus áreas y el
texto de «manda_sobre» están copiados sin reinterpretar. Por eso se declara
confirmada en la cabecera del fichero, y por eso los casos que se apoyan en ella
pueden fallarle a alguien: hay una parte que responde de lo que dice.

Lo que sigue sin confirmar es otra cosa, y conviene no confundirlas. La matriz va
de **rol a área**. El módulo de Mencía va de **contradicción a categoría**. La
pieza del medio —de qué área es cada **campo** de un pedido— no está en ninguno
de los dos, y `AREA_DE_CATEGORIA`, aquí abajo, es la suposición del evaluador
mientras Pablo no la escriba. Ahí sí: un acuerdo que firma una sola parte no es
un acuerdo.
"""

import json
import unicodedata
from pathlib import Path

RUTA = Path(__file__).resolve().parent.parent / "referencia" / "ontologia_autoridad.json"

# Las categorías que emite el módulo de Mencía y el área de la que son.
#
# Se declara a mano y a la vista porque es **el punto exacto donde los dos
# módulos tienen que estar de acuerdo**. Mencía etiqueta cada contradicción con
# una categoría; Pablo reparte el mando por áreas. Si esta tabla hiciera falta
# adivinarla, el desacuerdo entre ambos quedaría escondido dentro de una
# heurística en vez de a la vista.
AREA_DE_CATEGORIA = {
    "produccion": "Área de Producción",
    "comercial": "Área Comercial",
    "financiera": "Área Financiera",
    "financiero": "Área Financiera",
}

# ¿La ha escrito alguna de las dos partes, o la he deducido yo?
#
# Hoy la he deducido yo, y hay un desacuerdo vivo que lo demuestra: Mencía marca
# `cantidad_pedida` como **producción**, mientras que la matriz de Pablo pone los
# «pedidos de producción» bajo Admin. Comerciales, que es **Área Comercial**. Con
# la misma validación delante, una lectura y otra dan veredictos distintos.
#
# Por eso esta bandera existe y por eso está a False: mientras el reparto de
# ámbitos sea mío, el cruce de autoridad se declara pero **no le falla a nadie**.
# Acusar a Mencía de validar sin autoridad apoyándome en un mapa que me he
# inventado yo sería exactamente el error que este sistema le reprocha a los
# módulos que evalúa.
#
# Se pone a True cuando Pablo entregue el mapa campo/categoría → ámbito.
CATEGORIAS_CONFIRMADAS = False


def categorias_confirmadas():
    """¿El reparto categoría → área lo ha firmado alguien que no sea yo?"""
    return CATEGORIAS_CONFIRMADAS


def _plano(s):
    s = unicodedata.normalize("NFKD", str(s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.split())


def cargar(ruta=None):
    """La ontología tal como la declara Pablo. `None` si no está."""
    ruta = Path(ruta or RUTA)
    if not ruta.is_file():
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))


def confirmada(onto=None):
    """
    ¿La ha confirmado Pablo, o la ha deducido el evaluador de su lámina?

    Importa para el veredicto: un caso que se apoya en un mapa que su autor no ha
    validado no puede declararse superado sin decirlo.
    """
    onto = onto or cargar()
    if not onto:
        return False
    return not str(onto.get("formato_original", "")).upper().count("PENDIENTE")


def area_de(categoria):
    """El área a la que pertenece una categoría de contradicción."""
    return AREA_DE_CATEGORIA.get(_plano(categoria))


def quien_manda_sobre(categoria, onto=None):
    """
    Los roles con autoridad sobre esa categoría, del más cercano al más alto.

    Devuelve [] si la categoría no se reconoce — que no es lo mismo que «nadie
    manda»: es que no se sabe, y el caso que lo use tiene que declararlo.
    """
    onto = onto or cargar()
    if not onto:
        return []
    area = area_de(categoria)
    if not area:
        return []
    propios = [r for r in onto["roles"]
               if _plano(r["area"]) == _plano(area) and r["nivel"] <= 2]
    # Y por encima, quien tenga autoridad global declarada.
    globales = [r for r in onto["roles"]
                if r["nivel"] == 1 and "global" in _plano(r["tipo_de_autoridad"])]
    return sorted(propios + globales, key=lambda r: r["nivel"], reverse=True)


def rol_de(nombre, onto=None):
    """
    El rol de la ontología que corresponde a un nombre escrito a mano.

    `resolved_by` es texto libre en la exportación de Mencía —«Director de
    Producción», «Administrativo Comercial»— y en la ontología los nombres son
    «Dir. Producción», «Admin. Comerciales». No coinciden como cadenas, así que
    se comparan por las palabras que llevan carga: el área y el escalón.
    """
    onto = onto or cargar()
    if not onto or not nombre:
        return None
    t = _plano(nombre)

    # Primero por el nombre, tolerando plural y puntuación: «Encargado de Turno»
    # y «Encargados de Turno» son el mismo rol, y compararlos por la cadena
    # entera no lo parece. Va antes que la heurística porque cuando el nombre
    # coincide no hay nada que deducir.
    def raiz(x):
        return {p.rstrip("s.") for p in _plano(x).split()
                if p not in ("de", "del", "la", "el", "y", "/")}

    r_busca = raiz(t)
    for r in onto["roles"]:
        if raiz(r["rol"]) == r_busca:
            return r
    for r in onto["roles"]:
        comun = raiz(r["rol"]) & r_busca
        if comun and comun == raiz(r["rol"]):
            return r

    def escalon(x):
        # El CEO se mira primero: su nombre en la ontología es «CEO / Dirección
        # General», que también contiene «direccion», y comprobando ese antes se
        # le clasificaba como un director de área cualquiera.
        if "ceo" in x:
            return "ceo"
        if any(p in x for p in ("director", "dir.", "dir ", "direccion")):
            return "direccion"
        if any(p in x for p in ("administrativo", "admin", "encargado")):
            return "subordinado"
        return None

    def area(x):
        for clave, palabra in (("produccion", "produccion"),
                               ("comercial", "comercial"),
                               ("financ", "financiera")):
            if clave in x:
                return palabra
        return None

    e_busca, a_busca = escalon(t), area(t)
    mejor = None
    for r in onto["roles"]:
        rt = _plano(r["rol"])
        e_rol, a_rol = escalon(rt), area(rt)
        if e_busca == "ceo" and e_rol == "ceo":
            return r
        if a_busca and a_rol == a_busca and e_busca and e_rol == e_busca:
            return r
        if a_busca and a_rol == a_busca and mejor is None:
            mejor = r
    return mejor


def tiene_autoridad(nombre_rol, categoria, onto=None):
    """
    ¿Podía esta persona validar una contradicción de esa categoría?

    Devuelve (veredicto, motivo). El veredicto es True, False o **None cuando no
    se puede saber** — porque el rol no se reconoce en la ontología o porque la
    categoría no encaja en ningún área. No saberlo no es que no la tuviera, y
    tratarlos igual convertiría un hueco del evaluador en un fallo del módulo.
    """
    onto = onto or cargar()
    if not onto:
        return None, "no hay ontología de autoridad cargada"
    if not categoria:
        return None, "la contradicción no declara categoría"

    manda = quien_manda_sobre(categoria, onto)
    if not manda:
        return None, (f"la categoría «{categoria}» no corresponde a ningún área "
                      f"de la ontología")

    rol = rol_de(nombre_rol, onto)
    if not rol:
        return None, (f"«{nombre_rol}» no se reconoce como un rol del "
                      f"organigrama")

    if any(r["rol"] == rol["rol"] for r in manda):
        return True, (f"{rol['rol']} tiene autoridad sobre "
                      f"{area_de(categoria)}")
    return False, (f"{rol['rol']} (nivel {rol['nivel']}, {rol['area']}) no manda "
                   f"sobre {area_de(categoria)}; ahí manda "
                   f"{', '.join(r['rol'] for r in manda)}")


def resumen():
    """Para poder enseñarlo en pantalla sin volver a leer el fichero."""
    onto = cargar()
    if not onto:
        return {"disponible": False}
    return {
        "disponible": True,
        "confirmada": confirmada(onto),
        "fuente": onto.get("fuente"),
        "roles": len(onto["roles"]),
        "areas": sorted({r["area"] for r in onto["roles"]}),
    }
