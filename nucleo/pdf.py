"""
Lectura de documentos. Común a todas las ramas: cualquier módulo que reciba
PDF entra por aquí.

Dos cosas que esta capa hace y conviene tener presentes:

**Lee por dos vías y declara cuál usó.** Los documentos reales de Martín salen de
una fotocopiadora: son imágenes, no tienen capa de texto, y `pdftotext` devuelve
cero bytes. Hasta el 28/08 eso significaba «no legible» y toda su batería quedaba
pendiente — el evaluador no podía decir nada de un módulo que sí leía esos
documentos. Ahora, cuando no hay capa de texto, se reconoce el texto con OCR.

Pero la vía se declara siempre (`via`), porque no son equivalentes:

  · `capa_texto` — el texto es el que el PDF contiene. Lo que diga es el documento.
  · `ocr`        — el texto es una **lectura** del documento, con error posible.
                   Una discrepancia con el módulo evaluado no demuestra por sí
                   sola que el módulo se equivoque: puede haberse equivocado el
                   evaluador. Por eso el veredicto la arrastra.
  · `ninguna`    — ni capa ni OCR disponible. No es «sin incidencias».

**Cuenta las páginas dos veces.** Las que tiene el PDF y las que el propio
documento dice tener en su pie («Página 3 de 10»). Cuando no coinciden, el
escaneo está incompleto — y un documento al que le faltan páginas no puede
declararse apto como referencia, porque lo que falta puede ser precisamente la
cláusula que decide.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from nucleo.texto import juntar_guiones

# Idioma del OCR. Los documentos del proyecto son españoles; si el paquete no
# está instalado se cae a inglés, que reconoce peor las tildes pero sigue
# extrayendo fechas y cifras, que es lo que sostiene la verdad de campo.
IDIOMA_OCR = "spa"
RESOLUCION_OCR = 300


def hay_pdftotext():
    """`pdftotext` viene de poppler-utils. Sin él no se puede leer ningún PDF."""
    return shutil.which("pdftotext") is not None


def hay_ocr():
    """OCR = tesseract + pdftoppm. Sin él, un escaneo sigue siendo ilegible."""
    return (shutil.which("tesseract") is not None
            and shutil.which("pdftoppm") is not None)


def idiomas_ocr():
    if not shutil.which("tesseract"):
        return []
    r = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True)
    return [l.strip() for l in r.stdout.splitlines()[1:] if l.strip()]


def texto_pdf(ruta):
    """Texto del PDF preservando la disposición en columnas."""
    r = subprocess.run(["pdftotext", "-layout", str(ruta), "-"],
                       capture_output=True, text=True)
    return r.stdout


def tiene_capa_texto(ruta):
    """
    False si el PDF es un escaneo sin texto extraíble.

    Importa para el veredicto: un documento ilegible no produce «sin incidencias»,
    produce «no se ha podido comprobar». Son dos cosas distintas y ninguna rama
    puede confundirlas.
    """
    r = subprocess.run(["pdffonts", str(ruta)], capture_output=True, text=True)
    if len(r.stdout.strip().splitlines()) > 2:
        return True
    # Un PDF puede declarar fuentes y aun así no dar texto útil. Lo que decide es
    # si sale algo legible, no si hay tipografías declaradas.
    return len(re.sub(r"\s", "", texto_pdf(ruta))) >= 40


def paginas_pdf(ruta):
    """Número de páginas que tiene el fichero."""
    r = subprocess.run(["pdfinfo", str(ruta)], capture_output=True, text=True)
    m = re.search(r"^Pages:\s*(\d+)", r.stdout, re.MULTILINE)
    return int(m.group(1)) if m else None


def texto_ocr(ruta, idioma=IDIOMA_OCR, paginas=None, diagnostico=None):
    """
    Reconocimiento óptico, **página a página**. Devuelve el texto concatenado.

    Se rasteriza con `pdftoppm`, que respeta la rotación declarada de la página:
    los escaneos de bandeja salen girados 270º y un OCR sobre la imagen sin girar
    no reconoce nada.

    Y se hace de una en una, no el documento entero de golpe. La primera versión
    rasterizaba las nueve páginas del contrato de Zurita a la vez —unos 70 MB de
    imagen en memoria— y en Streamlit Cloud, con un gigabyte para todo, el
    proceso moría sin decir nada. El resultado era un documento «sin capa de
    texto extraíble»: el síntoma de un escaneo ilegible, cuando lo que había era
    un evaluador sin memoria. Página a página, el pico baja a una sola imagen.

    `diagnostico` es una lista donde se anotan los fallos. Un OCR que se cae en
    silencio es peor que uno que no existe, porque el veredicto que sale después
    parece un veredicto.
    """
    fallos = diagnostico if diagnostico is not None else []
    if not hay_ocr():
        fallos.append("no hay tesseract o pdftoppm en este equipo")
        return ""
    if idioma not in idiomas_ocr():
        fallos.append(f"falta el idioma «{idioma}»; se usa inglés")
        idioma = "eng"

    total = paginas or paginas_pdf(ruta) or 1
    trozos = []
    for n in range(1, total + 1):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "pg"
            r = subprocess.run(
                ["pdftoppm", "-r", str(RESOLUCION_OCR), "-gray",
                 "-f", str(n), "-l", str(n), str(ruta), str(base)],
                capture_output=True)
            imgs = sorted(Path(tmp).glob("pg-*"))
            if r.returncode != 0 or not imgs:
                fallos.append(f"página {n}: no se ha podido rasterizar"
                              + (f" ({r.stderr.decode()[:80]})" if r.stderr else ""))
                continue
            t = subprocess.run(
                ["tesseract", str(imgs[0]), "stdout", "-l", idioma, "--psm", "6"],
                capture_output=True, text=True)
            if t.returncode != 0:
                fallos.append(f"página {n}: el reconocimiento ha fallado"
                              + (f" ({t.stderr[:80]})" if t.stderr else ""))
                continue
            trozos.append(t.stdout)

    if not trozos:
        fallos.append("ninguna página ha producido texto")
    # Los escaneos de máquina de escribir parten palabras al final de línea
    # («no-\nventa»), y una fecha o un plazo partido por la mitad no lo encuentra
    # ningún patrón. Se repara aquí, en la lectura, para que todas las ramas
    # reciban el texto ya cosido.
    return juntar_guiones("\n".join(trozos))


def pathlib_stem(nombre):
    return Path(str(nombre or "")).stem


def _clave(nombre):
    """
    Nombre de fichero reducido a lo que no cambia al pasar por un correo, un zip
    o un navegador: sólo letras y números.

    «20190115 SUBROGACION A REPSOL COMERCIAL-LOS OLIVOS.pdf» y
    «20190115_SUBROGACION_A_REPSOL_COMERCIALLOS_OLIVOS.ocr.txt» son el mismo
    documento, y comparando las cadenas tal cual no lo parecen: espacios frente a
    guiones bajos, y un guion que uno de los dos se ha comido por el camino.
    """
    import unicodedata
    n = unicodedata.normalize("NFKD", str(nombre or "").lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", n)


P_PIE = r"P[áa]gina\s+(\d{1,3})\s+de\s+(\d{1,3})"


def integridad(texto, paginas_fichero):
    """
    ¿Está el documento completo?

    Muchos contratos numeran sus páginas en el pie: «Página 3 de 10». Ese número
    es del documento, no del fichero, así que sirve de testigo independiente. Si
    el PDF tiene menos páginas de las que el documento declara, faltan hojas — y
    el módulo que lo clasifica no tiene forma de saber qué decían.

    Devuelve también **cuáles** faltan, porque no es lo mismo perder la portada
    que perder la cláusula de resolución.
    """
    vistas = sorted({int(a) for a, _ in re.findall(P_PIE, texto or "")})
    totales = sorted({int(b) for _, b in re.findall(P_PIE, texto or "")})
    declaradas = max(totales) if totales else None

    faltantes = []
    if declaradas and vistas:
        faltantes = [n for n in range(1, declaradas + 1) if n not in vistas]

    completo = None
    if declaradas is not None and paginas_fichero is not None:
        completo = (paginas_fichero >= declaradas) and not faltantes

    return {"paginas_fichero": paginas_fichero, "paginas_declaradas": declaradas,
            "paginas_vistas": vistas, "faltantes": faltantes, "completo": completo}


# Lecturas ya reconocidas que viajan con el repositorio.
#
# Reconocer un escaneo cuesta un minuto y exige tesseract instalado, y ninguna de
# las dos cosas está garantizada donde se despliega esto: en Streamlit Cloud los
# paquetes de sistema sólo entran al reconstruir el contenedor. Sin esta caché, un
# despliegue sin OCR no puede evaluar el módulo de Martín en absoluto — sus trece
# documentos son fotocopias— aunque el texto esté reconocido desde hace días.
#
# Lo que se guarda es la lectura, no el veredicto: el evaluador sigue calculando
# todo lo demás, y la vía se declara `ocr` con la misma reserva de siempre. Basta
# borrar el `.ocr.txt` para que se rehaga.
CACHES = [Path(__file__).resolve().parent.parent / "demo" / "datos" / "vigencia"]


def _huella(ruta, trozo=1 << 20):
    """
    Identidad del fichero, independiente de cómo se llame.

    Se lee entero en bloques para no cargar en memoria un PDF de varios megas
    —ZURITA son 3,7— y se devuelve el resumen. Dos ficheros con la misma huella
    son el mismo fichero; dos copias del mismo documento reguardadas por
    programas distintos no lo son, y eso está bien: en la duda se reconoce.
    """
    import hashlib
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(trozo), b""):
            h.update(bloque)
    return h.hexdigest()


def _cache_de(ruta):
    """
    El texto ya reconocido de este documento, venga de donde venga.

    Busca primero al lado del PDF y después en las carpetas del repositorio, y
    **compara los nombres por lo que no cambia al pasar por un correo o un
    navegador**: sólo letras y números. «20190115 SUBROGACION A REPSOL
    COMERCIAL-LOS OLIVOS.pdf» y «20190115_SUBROGACION_A_REPSOL_COMERCIALLOS_
    OLIVOS.ocr.txt» son el mismo documento, y comparando las cadenas tal cual no
    lo parecían: por eso un documento salía «sin capa de texto» teniendo su
    lectura en la carpeta de al lado.
    """
    propia = ruta.with_suffix(".ocr.txt")
    if propia.is_file():
        return propia
    clave = _clave(ruta.stem)
    if not clave:
        return None

    exactos, parciales = [], []
    for carpeta in CACHES:
        if not carpeta.is_dir():
            continue
        for cand in carpeta.glob("*.ocr.txt"):
            k = _clave(cand.name[:-len(".ocr.txt")])
            if k == clave:
                exactos.append(cand)
            elif len(clave) > 8 and (k in clave or clave in k):
                parciales.append(cand)
    if exactos:
        return exactos[0]

    # El parcial sólo vale si es **único**. «DERECHOS SUPERFICIE» está contenido
    # en «RESCATE DERECHOS SUPERFICIE», así que con la regla de «el primero que
    # encaje» el rescate se leía con el texto de la escritura original: un
    # veredicto sobre un documento sacado de otro, y sin que nada lo delatara.
    # Ante dos candidatos no se elige — la misma regla que ya gobierna las fechas.
    if len(parciales) != 1:
        return None

    # Y aunque sea único, el nombre no basta.
    #
    # Un parcial acepta cualquier nombre que contenga al de la caché: si mañana
    # llega un «20160119 ANEXO MODIFICADO», que es otro documento, la regla del
    # nombre le daría el texto del viejo. El evaluador emitiría un veredicto
    # sobre un documento **leyendo otro**, con todos sus campos anclados a citas
    # que existen —en el documento equivocado—, y ni el anclaje ni la aritmética
    # lo detectarían: son coherentes entre sí, sólo que con la fuente cambiada.
    # Es el fallo más grave que puede cometer un evaluador, porque no se nota.
    #
    # Contar páginas no lo cierra: los dos anexos de 2016 tienen una. Lo que sí
    # lo cierra es comparar el fichero entero. Y encaja con lo que el parcial
    # existe para resolver —un documento que ha cambiado de nombre al pasar por
    # un correo o un zip—, porque **renombrar no cambia los bytes**. Si el PDF
    # es el mismo fichero, se aprovecha el texto; si no lo es, se reconoce de
    # verdad aunque tarde. Ante la duda, trabajar de más.
    candidata = parciales[0]
    origen = Path(str(candidata)[:-len(".ocr.txt")] + ".pdf")
    if not origen.is_file():
        return None                       # no se puede corroborar: se reconoce
    try:
        if _huella(origen) != _huella(ruta):
            return None
    except OSError:
        return None
    return candidata


def leer(ruta, ocr=True):
    """
    Devuelve el registro de documento que consumen todas las ramas.

    `capa` se mantiene con su significado de siempre —¿había texto sin OCR?— para
    no cambiar lo que ya dependía de ella, y `legible` es lo nuevo: si el
    evaluador ha conseguido texto por la vía que sea.
    """
    ruta = Path(ruta)
    capa = tiene_capa_texto(ruta)
    via, texto = "capa_texto", ""

    # Reconocer ocho páginas cuesta cerca de un minuto, y la demo ejecuta todos
    # los pasos al abrirse. Cuando junto al PDF hay un `.ocr.txt`, se usa: es el
    # mismo texto que produciría el OCR, guardado la primera vez. Se declara como
    # OCR igualmente —la reserva sobre la lectura no desaparece por estar en
    # caché— y basta borrar el fichero para rehacerlo.
    cache = _cache_de(ruta) if not capa else None
    if cache is not None:
        texto = cache.read_text(encoding="utf-8")
        if len(re.sub(r"\s", "", texto)) >= 40:
            paginas = paginas_pdf(ruta)
            return {"nombre": ruta.name, "id": ruta.stem, "capa": False,
                    "via": "ocr", "legible": True, "texto": texto,
                    "paginas": paginas, "integridad": integridad(texto, paginas)}

    fallos = []
    if capa:
        texto = texto_pdf(ruta)
    elif ocr and hay_ocr():
        texto, via = texto_ocr(ruta, diagnostico=fallos), "ocr"
        if len(re.sub(r"\s", "", texto)) < 40:
            texto, via = "", "ninguna"
            fallos.append("el reconocimiento no ha devuelto texto legible")
    else:
        via = "ninguna"
        fallos.append("el OCR está desactivado o no disponible")

    paginas = paginas_pdf(ruta)
    return {"nombre": ruta.name,
            "id": ruta.stem,
            "capa": capa,
            "via": via,
            "legible": bool(texto.strip()),
            "texto": texto,
            "paginas": paginas,
            "fallos_lectura": fallos,
            "integridad": integridad(texto, paginas)}


def leer_subidos(ficheros, carpeta, ocr=True):
    """
    Vuelca los ficheros que llegan por el `st.file_uploader` a disco y los lee.
    `carpeta` es un directorio temporal creado por quien llama.

    Acepta **texto reconocido aparte**: si junto a `X.pdf` se sube un `X.ocr.txt`,
    se usa como lectura del documento en vez de reconocerlo otra vez.

    Existe porque el OCR depende de un paquete del sistema y hay despliegues
    donde no está —Streamlit Cloud sólo instala `packages.txt` al reconstruir el
    contenedor, y hasta entonces todo escaneo sale «ilegible»—. Sin esta puerta,
    una máquina sin tesseract no puede evaluar el módulo de Martín en absoluto,
    aunque el texto ya esté reconocido en otro sitio. La procedencia se declara
    igual: sigue siendo `ocr`, con la misma reserva sobre la lectura.
    """
    sueltos, aparte = [], {}
    for f in ficheros:
        nombre = getattr(f, "name", "")
        if nombre.lower().endswith((".ocr.txt", ".txt")):
            clave = _clave(re.sub(r"\.ocr\.txt$|\.txt$", "", nombre,
                                  flags=re.IGNORECASE))
            try:
                aparte[clave] = (nombre, f.getvalue().decode("utf-8", "replace"))
            except Exception:
                pass
        else:
            sueltos.append(f)

    # Un solo PDF y un solo texto sin emparejar: se emparejan. No hay ambigüedad
    # posible y ahorra tener que renombrar ficheros para que el evaluador
    # funcione, que es una tarea que no debería existir.
    if len(sueltos) == 1 and len(aparte) == 1:
        aparte = {_clave(pathlib_stem(sueltos[0].name)): list(aparte.values())[0]}

    docs, usados = [], set()
    for f in sueltos:
        ruta = Path(carpeta) / f.name
        ruta.write_bytes(f.getbuffer())
        clave = _clave(ruta.stem)
        par = aparte.get(clave)
        # Si el nombre no casa exacto, vale un único candidato que lo contenga —
        # y sólo uno: emparejar el texto de un documento con otro sería peor que
        # no emparejar nada, porque el veredicto saldría del documento equivocado.
        if par is None:
            cands = [k for k in aparte if k and (k in clave or clave in k)]
            if len(cands) == 1:
                par = aparte[cands[0]]
                clave = cands[0]
        if par and len(re.sub(r"\s", "", par[1])) >= 40:
            ruta.with_suffix(".ocr.txt").write_text(par[1], encoding="utf-8")
            usados.add(clave)
        docs.append(leer(ruta, ocr=ocr))

    # Un .txt que no encuentra su PDF se ignoraba en silencio, y el documento
    # salía «sin capa de texto» sin decir que su texto venía en la maleta.
    for clave, (nombre, _t) in aparte.items():
        if clave not in usados:
            docs.append({"nombre": nombre, "id": nombre, "capa": False,
                         "via": "ninguna", "legible": False, "texto": "",
                         "paginas": None, "integridad": {}, "huerfano": True,
                         "fallos_lectura": [
                             "este texto reconocido no corresponde al nombre de "
                             "ningún PDF de los subidos; renómbralo para que "
                             "coincida con el del documento"]})
    return docs
