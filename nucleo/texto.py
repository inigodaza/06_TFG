"""
Normalización y comparación de valores. Es la capa que decide cuándo dos formas
distintas de escribir lo mismo son el mismo dato.
"""

import re
import unicodedata
from datetime import date

# ---------------------------------------------------------------------------
# Números
# ---------------------------------------------------------------------------

def numero(s):
    """'30.000' -> 30000 · '3,000' -> 3000 · '240gsm' -> 240 · None si no hay cifra."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return int(s)
    s = re.sub(r"[^\d.,]", "", str(s)).replace(".", "").replace(",", "")
    return int(s) if s.isdigit() else None


def formato_normal(v):
    """'297 x 210' y '210x297' son el mismo formato: se ordenan para comparar."""
    n = re.findall(r"\d+", str(v or ""))
    return "x".join(sorted(n, key=int)) if n else None


def plano(s):
    """Minúsculas, sin tildes y sin espacios de más: para comparar texto libre."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def mismo_valor(citado, real):
    """
    ¿El valor que cita el módulo es el que figura en los documentos?

    Se compara como número cuando ambos lo son y como texto normalizado en
    cualquier otro caso. No citar un valor no es citarlo mal: si el módulo no
    lo declara, no se le penaliza aquí (eso lo mira el caso de trazabilidad).
    """
    if citado is None or (isinstance(citado, str) and not citado.strip()):
        return True
    a, b = numero(citado), numero(real)
    if a is not None and b is not None:      # `is not None`, no `or`:
        return a == b                        # el 0 es un valor válido
    return plano(citado) == plano(real)


# ---------------------------------------------------------------------------
# Fechas
# ---------------------------------------------------------------------------

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
         "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
         "noviembre": 11, "diciembre": 12}

FECHA_LARGA = r"(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóú]+)\s+de\s+(\d{4})"
FECHA_CORTA = r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})"
# ISO primero: IAlert emite 2026-08-18, que leído como día/mes/año daría 2001.
FECHA_ISO = r"(\d{4})-(\d{1,2})-(\d{1,2})"

ORDINALES = {"un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
             "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
             "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
             "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
             "veinte": 20, "veinticinco": 25, "treinta": 30}


# ---------------------------------------------------------------------------
# Números y fechas escritos con letra
# ---------------------------------------------------------------------------
# Las escrituras notariales antiguas no escriben cifras: escriben «veinticinco
# años» y «mil novecientos noventa y cinco». Los contratos sintéticos con los que
# se diseñó la batería sí las escribían, así que esto no hacía falta hasta que
# entró el primer documento de verdad. Es el mismo aprendizaje que el plazo en
# letra: un banco de pruebas fabricado enseña la forma del fabricante.

UNIDADES = {"cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3,
            "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
            "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14,
            "quince": 15, "dieciseis": 16, "diecisiete": 17, "dieciocho": 18,
            "diecinueve": 19, "veinte": 20, "veintiun": 21, "veintiuno": 21,
            "veintidos": 22, "veintitres": 23, "veinticuatro": 24,
            "veinticinco": 25, "veintiseis": 26, "veintisiete": 27,
            "veintiocho": 28, "veintinueve": 29}
DECENAS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60,
           "setenta": 70, "ochenta": 80, "noventa": 90}
CENTENAS = {"cien": 100, "ciento": 100, "doscientos": 200, "trescientos": 300,
            "cuatrocientos": 400, "quinientos": 500, "seiscientos": 600,
            "setecientos": 700, "ochocientos": 800, "novecientos": 900}

PALABRAS_NUMERO = set(UNIDADES) | set(DECENAS) | set(CENTENAS) | {"mil", "y"}


def numero_en_letra(cadena):
    """
    'veinticinco' -> 25 · 'mil novecientos noventa y cinco' -> 1995.

    Suma por tramos, que es como se construye el número en castellano. No
    pretende cubrir el idioma entero: cubre años y plazos, que es lo que aparece
    en un contrato.
    """
    palabras = [p for p in re.split(r"[\s,.\-]+", plano(cadena)) if p]
    if not palabras or not any(p in PALABRAS_NUMERO - {"y"} for p in palabras):
        return None
    total, tramo, visto = 0, 0, False
    for p in palabras:
        if p == "y":
            continue
        if p in UNIDADES:
            tramo += UNIDADES[p]
        elif p in DECENAS:
            tramo += DECENAS[p]
        elif p in CENTENAS:
            tramo += CENTENAS[p]
        elif p == "mil":
            total += (tramo or 1) * 1000
            tramo = 0
        else:
            break                      # una palabra que no es número cierra el número
        visto = True
    return (total + tramo) if visto else None


# «a cuatro de abril de mil novecientos noventa y cinco»
# El año puede ocupar hasta cinco palabras —«dos mil veinticinco», «mil
# novecientos noventa y cinco»—. Se capturan generosamente y `numero_en_letra`
# corta solo en cuanto aparece una palabra que no es número.
_DIA = r"[a-záéíóúñ]+(?:\s+y\s+[a-záéíóúñ]+)?"
_ANIO = r"[a-záéíóúñ]+(?:\s+(?:y\s+)?[a-záéíóúñ]+){0,4}"
FECHA_LETRA = rf"({_DIA})\s+de\s+([a-záéíóúñ]+)\s+de[l]?\s+({_ANIO})"


def juntar_guiones(texto):
    """
    Repara los cortes de palabra al final de línea: «no-\\nventa» -> «noventa».

    Los escaneos de máquina de escribir parten palabras constantemente, y una
    fecha o un plazo partido por la mitad no lo encuentra ningún patrón. Se
    aplica antes de extraer nada; no cambia el texto que se cita como evidencia.
    """
    if not texto:
        return ""
    return re.sub(r"([a-záéíóúñ])[-—]\s*\n\s*([a-záéíóúñ])", r"\1\2", texto,
                  flags=re.IGNORECASE)


def fecha_de(cadena):
    """Convierte '1 de julio de 2023' o '01/07/2023' en un date. None si no es una fecha."""
    if not cadena:
        return None
    m = re.search(FECHA_LARGA, str(cadena))
    if m:
        mes = MESES.get(plano(m.group(2)))
        if mes:
            try:
                return date(int(m.group(3)), mes, int(m.group(1)))
            except ValueError:
                return None
    m = re.search(FECHA_ISO, str(cadena))
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(FECHA_CORTA, str(cadena))
    if m:
        d, mes, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
        a = a + 2000 if a < 100 else a
        try:
            return date(a, mes, d)
        except ValueError:
            return None
    # Mixta: el día con letra y el año con cifra —«el día uno de enero de 2020»—.
    # Es frecuentísima en los contratos y no la cubre ninguna de las anteriores:
    # `FECHA_LARGA` exige el día en cifra y `FECHA_LETRA` el año en letra.
    m = re.search(rf"({_DIA})\s+de\s+([a-záéíóúñ]+)\s+de[l]?\s+(\d{{4}})",
                  plano(cadena))
    if m:
        dia, mes = numero_en_letra(m.group(1)), MESES.get(plano(m.group(2)))
        if dia and mes and 1 <= dia <= 31:
            try:
                return date(int(m.group(3)), mes, dia)
            except ValueError:
                return None

    # Última, porque es la más costosa y la más fácil de confundir con prosa.
    m = re.search(FECHA_LETRA, plano(cadena))
    if m:
        dia = numero_en_letra(m.group(1))
        mes = MESES.get(plano(m.group(2)))
        anio = numero_en_letra(m.group(3))
        if dia and mes and anio and 1 <= dia <= 31 and 1900 <= anio <= 2100:
            try:
                return date(anio, mes, dia)
            except ValueError:
                return None
    return None


def buscar_fecha(texto, patron, ventana=80):
    """
    Primera fecha que aparece a continuación de `patron`, dentro de la misma frase.

    Devuelve (fecha, cita) — la cita es el fragmento literal que la sostiene, para
    que el veredicto pueda anclarse a algo verificable en el documento.
    """
    # MULTILINE porque varios patrones anclan en `^` para exigir que la fórmula
    # abra línea —«En Madrid, a 10 de diciembre de 2015»— y sin él ese ancla sólo
    # casaba con el principio del fichero: en un PDF real nunca es la primera
    # línea, así que la fecha de firma se perdía siempre.
    for m in re.finditer(patron, texto, re.IGNORECASE | re.MULTILINE):
        cola = texto[m.end(): m.end() + ventana]
        cola = re.split(r"(?<=\d{4})\s*[.;]", cola)[0]
        f = fecha_de(cola)
        if f:
            inicio = max(0, m.start() - 10)
            cita = re.sub(r"\s+", " ", texto[inicio: m.end() + 60]).strip()
            return f, cita
    return None, None


def fechas_candidatas(texto, patron, ventana=80):
    """
    TODAS las fechas que el patrón encuentra, no sólo la primera.

    `buscar_fecha` devuelve la primera y se calla las demás, y eso es un problema
    de fondo cuando el documento es una renovación: el contrato de 2019 dice
    primero «se amplió el plazo hasta el 31 de octubre de 2019» —contando lo que
    pasó antes— y después «finalizará el 31 de octubre de 2029», que es lo que
    pacta. Quedarse con la primera da 2019 y un veredicto de «caducado» sobre un
    contrato vigente: un dato correcto leído de la cláusula equivocada, con la
    misma cara de verificado que uno bueno.

    Devuelve [(fecha, cita), …] en orden de aparición, sin repetir fecha.
    """
    salida, vistas = [], set()
    for m in re.finditer(patron, texto, re.IGNORECASE | re.MULTILINE):
        cola = texto[m.end(): m.end() + ventana]
        cola = re.split(r"(?<=\d{4})\s*[.;]", cola)[0]
        f = fecha_de(cola)
        if f and f not in vistas:
            vistas.add(f)
            ini = max(0, m.start() - 60)
            salida.append((f, re.sub(r"\s+", " ",
                                     texto[ini: m.end() + 60]).strip()))
    return salida


def fecha_unica(texto, patron, ventana=80):
    """
    La fecha que el patrón encuentra, **sólo si encuentra una**.

    Devuelve (fecha, cita, aviso). Si hay varias candidatas distintas, devuelve
    fecha a None y un aviso que las nombra: el evaluador se abstiene en vez de
    elegir. Es la misma regla que gobierna todo lo demás — no afirmar lo que no
    se puede sostener — aplicada al sitio donde más barato sale equivocarse.

    Elegir la primera sería acertar la mayoría de las veces, y ese «la mayoría»
    es justo lo que un evaluador no puede permitirse: quien lea el veredicto no
    tiene forma de saber cuál de las veces le ha tocado.
    """
    cands = fechas_candidatas(texto, patron, ventana)
    if not cands:
        return None, None, None
    if len(cands) == 1:
        return cands[0][0], cands[0][1], None
    fechas = ", ".join(f.strftime("%d/%m/%Y") for f, _ in cands[:4])
    return None, cands[0][1], (f"el documento ofrece {len(cands)} fechas para el "
                               f"mismo campo ({fechas}) y ninguna regla decide "
                               f"cuál pacta y cuál narra")


def anios_de(texto):
    """
    Los años de duración que pacta el documento, buscados **de la cláusula más
    específica a la más general**.

    El orden es la regla, y por eso está escrito de una vez y no repartido. La
    versión anterior probaba primero el patrón genérico «plazo de N años», y en
    la escritura de derecho de superficie de 1995 eso devolvía 5 —el plazo del
    artículo 16 del Reglamento Hipotecario para edificar, que vive en otra
    cláusula— en lugar de los 25 de la duración del derecho. Un número correcto
    leído de la cláusula equivocada es peor que no leer ninguno: parece
    verificado, y arrastra la fecha de vencimiento con él.
    """
    def _n(bruto):
        bruto = (bruto or "").strip()
        if re.fullmatch(r"\d{1,2}", bruto):
            return int(bruto)
        n = numero_en_letra(bruto)
        return n if n and 1 <= n <= 99 else None

    CLAUSULA = (r"(?:plazo\s+de\s+(?:vigencia|duraci[óo]n)|"
                r"duraci[óo]n\s+(?:del?\s+)?(?:presente\s+)?[a-záéíóúñ\s]{0,40}?)")
    intentos = [
        # 1 · La cláusula de duración, con el número en letra o en cifra.
        rf"{CLAUSULA}[^.]{{0,180}}?(?:ser[áa]|es)\s+de\s+"
        r"([A-Za-zÁÉÍÓÚáéíóúñ\s]{3,30}?|\d{1,2})\s*a[ñn]os",
        rf"{CLAUSULA}[^.]{{0,180}}?(?:de\s+)?(\d{{1,2}})\s*a[ñn]os",
        # 2 · La forma «TRES (3) AÑOS», típica de los contratos mecanografiados.
        r"\((\d{1,2})\)\s*A[ÑN]OS?",
        # 3 · «duración de tres años» y «plazo inicial de CATORCE AÑOS».
        r"duraci[óo]n\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñ]+)\s*(?:\(\d+\))?\s*a[ñn]os?",
        r"plazo\s+(?:inicial\s+|de\s+duraci[óo]n\s+)?de\s+"
        r"([A-Za-zÁÉÍÓÚáéíóúñ]+|\d{1,2})\s*(?:\(\d+\))?\s*a[ñn]os?",
    ]
    for patron in intentos:
        m = re.search(patron, texto, re.IGNORECASE)
        if m:
            n = _n(m.group(1))
            if n:
                return n
    return None


# Un plazo de aviso puede venir en días, meses o años, y en cifra o en letra:
# «90 días», «3 meses», «un año», «tres (3) meses». Todo se reduce a días para
# poder compararlo con lo que el módulo publica, que son días.
DIAS_POR = {"dia": 1, "dias": 1, "mes": 30, "meses": 30, "ano": 365, "anos": 365}


def duracion_dias(cadena):
    """
    '90 días' -> (90, 'dias', 90) · '3 meses' -> (3, 'meses', 90) ·
    'un año' -> (1, 'anos', 365). None si no hay duración reconocible.

    Devuelve también la unidad original porque la equivalencia importa: tres meses
    NO son noventa días cuando se restan de una fecha concreta, y el evaluador
    tiene que poder decir cuál de las dos cuentas hizo el módulo.
    """
    if not cadena:
        return None
    t = plano(cadena)
    m = re.search(r"(\d{1,4}|[a-záéíóú]+)\s*\(?\s*(\d{1,4})?\s*\)?\s*"
                  r"(d[ií]as?|meses|mes|a[ñn]os?)\b", t)
    if not m:
        return None
    bruto = m.group(2) or m.group(1)
    n = int(bruto) if str(bruto).isdigit() else ORDINALES.get(plano(bruto))
    if n is None:
        return None
    unidad = plano(m.group(3)).replace("ñ", "n").replace("í", "i")
    unidad = {"dia": "dias", "mes": "meses", "ano": "anos"}.get(unidad, unidad)
    return (n, unidad, n * DIAS_POR.get(unidad, 1))


def restar_duracion(f, n, unidad):
    """
    Fecha `n` unidades antes de `f`. Los meses se restan como meses de calendario,
    no como bloques de treinta días: es la diferencia entre el 15/10/2029 y el
    17/10/2029, y la fecha crítica de un contrato no admite dos días de holgura.
    """
    if f is None or n is None:
        return None
    if unidad == "dias":
        from datetime import timedelta
        return f - timedelta(days=n)
    if unidad == "anos":
        return sumar_anios(f, -n)
    if unidad == "meses":
        total = f.year * 12 + (f.month - 1) - n
        anio, mes = divmod(total, 12)
        mes += 1
        dia = f.day
        while dia > 28:
            try:
                return date(anio, mes, dia)
            except ValueError:
                dia -= 1
        return date(anio, mes, dia)
    return None


def sumar_anios(f, n):
    """Misma fecha n años después. El 29 de febrero cae al 28."""
    if f is None or n is None:
        return None
    try:
        return f.replace(year=f.year + n)
    except ValueError:
        return f.replace(year=f.year + n, day=28)
