"""
Componente de IA: la ranura de lectura del evaluador.

Por qué existe
--------------
Los extractores deterministas están escritos contra los documentos concretos que
entregó cada compañero. Eso los hace auditables —siempre devuelven lo mismo y
puedo explicar por qué— pero los ata a la forma exacta de esos documentos.

Generalizar es un problema de **lectura**, no de **juicio**. Por eso el modelo
ocupa ranuras contadas, cada una con su función declarada, y ninguna más:

    extraer_con_llm()      documento  -> campos          (verdad de campo)
    interpretar_con_llm()  respuesta  -> incidencias     (salida del módulo)
    consultar()            evidencia  -> voto            (panel de jueces)
    redactar()             veredicto  -> prosa           (informe)

Las dos primeras **leen**. La tercera **opina, y sólo sobre lo que ninguna regla
puede medir** —si una salida es accionable, si una justificación se sostiene—, y
aun así no puntúa sola: puntúa cuando un panel de jueces independientes coincide,
y donde discrepa se declara la discrepancia en vez de resolverla a la fuerza. La
cuarta no decide nada: recibe el veredicto ya calculado y lo redacta.

Ninguna de las cuatro toca el núcleo. El cálculo de la verdad de campo, el
contraste, las dos métricas y el veredicto siguen siendo deterministas. Si el
juicio dependiera de un modelo generativo, el evaluador heredaría el mismo
problema que le está señalando a los módulos que evalúa, y el caso de
repetibilidad dejaría de significar nada.

Cómo está domado
----------------
Un modelo dentro de un evaluador es una fuente de gasto y de varianza. Las dos
están acotadas a propósito:

  · **Caché por contenido.** La clave es el hash de (modelo, prompt, esquema,
    texto). El mismo documento se lee **una sola vez**, y las siguientes salen de
    memoria o de disco. Importa más de lo que parece: Streamlit reejecuta el
    script entero cada vez que se toca un widget, así que sin caché mover una
    barra relanzaría todas las extracciones.
  · **Temperatura 0 y versión anclada.** El modelo no se elige «el último»: se
    fija, porque un cambio de versión cambia el veredicto.
  · **Razonamiento desactivado.** Los Flash piensan por defecto; aquí no hace
    falta y cuesta tokens.
  · **Contador de llamadas** a la vista, para que el gasto se vea en vez de
    suponerse.
  · **Medida de estabilidad.** `medir_estabilidad()` ejecuta la misma extracción
    K veces y dice qué campos bailan. Si bailan, la verdad de campo no es
    reproducible y hay que decirlo en el veredicto.

Este módulo **no importa Streamlit** a propósito: así `pruebas.py` puede
ejercitarlo desde la línea de órdenes, y la evaluación sigue siendo comprobable
fuera de la app.
"""

import hashlib
import json
import os
import re
import time
from datetime import date
from pathlib import Path

PROVEEDOR = "gemini"

# Versión anclada. No es «el último modelo»: es este. Cambiarlo puede cambiar el
# veredicto, así que es una decisión, no un valor por defecto.
MODELO = "gemini-3.6-flash"

# Un ancla que apunta a un modelo retirado deja de ser un ancla y pasa a ser una
# avería: el 22/08/2026 el proveedor dejó de servir `gemini-2.5-flash` a claves
# nuevas y toda la vía asistida se cayó con un 404. La respuesta no es dejar de
# anclar —eso volvería el veredicto irreproducible— sino tener un plan de retirada
# escrito, en orden, y **decir en voz alta** cuál se ha usado. Un cambio de modelo
# puede cambiar el veredicto, así que no puede ocurrir en silencio.
MODELOS_ALTERNATIVOS = ["gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]

# Qué modelo se está usando de verdad, y por qué, si no es el anclado.
MODELO_EFECTIVO = None
AVISO_MODELO = None

# Caché en disco, para que reiniciar la app no vuelva a gastar. Va ignorado por
# git: son lecturas de documentos, no código.
CARPETA_CACHE = Path(".cache_llm")

# Ya no son «modos de evaluación» alternativos: son el mismo camino con o sin
# rescate. Cuando había un modo `ia` puro, el sistema ofrecía dos vías paralelas
# que hacían lo mismo y competían entre sí — y una de las dos no era reproducible.
# Un evaluador no puede tener dos verdades de campo distintas según qué botón se
# pulse: tiene una, calculada por reglas, y una ayuda para los huecos.
MODOS = {
    "determinista": "Sólo reglas. Auditable y repetible; cubre la forma en que "
                    "el módulo redacta hoy.",
    "asistido":     "Las reglas mandan. El modelo se llama únicamente para los "
                    "campos que las reglas no han encontrado, y cada valor queda "
                    "marcado con su procedencia.",
}

# El nivel gratuito del proveedor da 5 peticiones por minuto y por modelo. No es
# un detalle de configuración: es la restricción que decide cómo se diseña todo lo
# que llama al modelo. Un panel que lance doce peticiones de golpe no falla por un
# error de código, falla por aritmética.
LIMITE_POR_MINUTO = 5
REINTENTOS_POR_CUOTA = 2

ESTADISTICAS = {"llamadas": 0, "cache": 0, "errores": 0, "esperas": 0,
                "segundos_esperando": 0.0}

# Marcas de tiempo de las últimas llamadas, para no pasarse del ritmo.
_RITMO = []

_CLAVE = None
_CACHE = {}


class NoDisponible(RuntimeError):
    """El modo pedido necesita el componente de IA y no se puede usar."""


# ===========================================================================
# Configuración
# ===========================================================================

def configurar(api_key=None, modelo=None, carpeta_cache=None):
    """
    La llama la interfaz con lo que haya en `st.secrets`. Si no se pasa clave,
    se busca en el entorno, para poder usarlo desde la línea de órdenes.
    """
    global _CLAVE, MODELO, CARPETA_CACHE, MODELO_EFECTIVO, AVISO_MODELO
    _CLAVE = api_key or os.environ.get("GEMINI_API_KEY") or _CLAVE
    if modelo:
        # Un modelo fijado desde los secretos manda sobre el anclado en el código:
        # así se puede cambiar sin volver a desplegar cuando el proveedor retira
        # una versión.
        MODELO = modelo
        MODELO_EFECTIVO, AVISO_MODELO = None, None
    if carpeta_cache:
        CARPETA_CACHE = Path(carpeta_cache)
    return esta_disponible()


def modelo_en_uso():
    """El que se está usando de verdad, que no siempre es el anclado."""
    return MODELO_EFECTIVO or MODELO


def listar_modelos():
    """
    Qué modelos alcanza esta clave. Sirve para diagnosticar un 404 sin tener que
    adivinar: cuesta una llamada de catálogo, no de generación.
    """
    if not esta_disponible():
        raise NoDisponible(por_que_no())
    from google import genai
    try:
        cliente = genai.Client(api_key=_CLAVE)
        nombres = []
        for m in cliente.models.list():
            nombre = getattr(m, "name", "") or ""
            acciones = getattr(m, "supported_actions", None) or []
            if not acciones or "generateContent" in acciones:
                nombres.append(nombre.replace("models/", ""))
        return sorted(set(nombres))
    except Exception as e:
        raise NoDisponible(f"No se ha podido leer el catálogo de modelos: "
                           f"{type(e).__name__}: {e}") from e


def esta_disponible():
    """Hay clave y hay cliente. Nada más: no se comprueba llamando, eso cuesta."""
    if not _CLAVE:
        return False
    try:
        import google.genai  # noqa: F401
    except ImportError:
        return False
    return True


def por_que_no():
    if not _CLAVE:
        return ("No hay clave. Añade `GEMINI_API_KEY` en Settings → Secrets de la "
                "app, o en `.streamlit/secrets.toml` si trabajas en local.")
    try:
        import google.genai  # noqa: F401
    except ImportError:
        return ("Falta la librería. Añade `google-genai` a `requirements.txt` y "
                "vuelve a desplegar.")
    return None


def estado():
    """Lo que la interfaz enseña en el lateral."""
    return {"proveedor": PROVEEDOR, "modelo": modelo_en_uso(),
            "modelo_anclado": MODELO, "aviso_modelo": AVISO_MODELO,
            "disponible": esta_disponible(), "motivo": por_que_no(),
            **ESTADISTICAS}


# ===========================================================================
# Esquemas
# ===========================================================================

def _esquema_gemini(esquema):
    """
    Traduce el esquema JSON de la rama al dialecto que acepta el modelo.

    El único punto delicado son los tipos opcionales: las ramas escriben
    `["string", "null"]`, que aquí se convierte en un tipo con `nullable`.
    Se hace en una función aparte para que el esquema de la rama no tenga que
    conocer al proveedor.
    """
    if not isinstance(esquema, dict):
        return esquema
    fuera = {}
    for k, v in esquema.items():
        if k == "type" and isinstance(v, list):
            tipos = [t for t in v if t != "null"]
            fuera["type"] = tipos[0] if tipos else "string"
            if "null" in v:
                fuera["nullable"] = True
        elif isinstance(v, dict):
            fuera[k] = _esquema_gemini(v)
        elif isinstance(v, list):
            fuera[k] = [_esquema_gemini(x) if isinstance(x, dict) else x for x in v]
        else:
            fuera[k] = v
    return fuera


# ===========================================================================
# Caché
# ===========================================================================

def _huella(prompt, texto, esquema):
    # El modelo entra en la clave: una lectura hecha con otro modelo es otra
    # lectura, y reutilizarla en silencio sería mentir sobre cómo se ha leído.
    crudo = json.dumps([modelo_en_uso(), prompt, esquema, texto], sort_keys=True,
                       ensure_ascii=False, default=str)
    return hashlib.sha256(crudo.encode("utf-8")).hexdigest()[:32]


def en_cache(prompt, texto, esquema):
    """
    ¿Esta llamada saldría gratis? La interfaz lo pregunta antes de ofrecer un
    botón que gasta, para poder decir si va a costar llamadas o no.
    """
    return _de_cache(_huella(prompt, texto, esquema)) is not None


def _de_cache(huella):
    if huella in _CACHE:
        return _CACHE[huella]
    fichero = CARPETA_CACHE / f"{huella}.json"
    if fichero.is_file():
        try:
            valor = json.loads(fichero.read_text(encoding="utf-8"))
            _CACHE[huella] = valor
            return valor
        except (OSError, json.JSONDecodeError):
            return None
    return None


def _a_cache(huella, valor):
    _CACHE[huella] = valor
    try:
        CARPETA_CACHE.mkdir(exist_ok=True)
        (CARPETA_CACHE / f"{huella}.json").write_text(
            json.dumps(valor, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass          # sin disco, la caché en memoria sigue valiendo


def vaciar_cache():
    _CACHE.clear()
    try:
        for f in CARPETA_CACHE.glob("*.json"):
            f.unlink()
    except OSError:
        pass


# ===========================================================================
# La llamada
# ===========================================================================

def _es_cuota(e):
    """
    ¿Es «has gastado tu cuota» y no otra cosa?

    Importa distinguirlo: un 429 se arregla **esperando**, un 404 cambiando de
    modelo y un fallo de red reintentando sin más. Tratarlos igual haría que una
    cuota agotada disparase el plan de retirada y acabáramos evaluando con otro
    modelo por una espera de treinta segundos.
    """
    t = f"{type(e).__name__}: {e}".upper()
    return "RESOURCE_EXHAUSTED" in t or "429" in t


def _espera_sugerida(e, por_defecto=20.0):
    """El proveedor dice cuánto hay que esperar. Hacerle caso es más barato que adivinar."""
    m = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s", str(e))
    if m:
        return min(float(m.group(1)) + 1.0, 65.0)
    return por_defecto


def _esperar_turno():
    """
    Limitador de ritmo. Antes de cada llamada mira cuántas van en los últimos
    sesenta segundos y, si toca, espera.

    Es preferible esperar a fallar: el error de cuota deja la evaluación a medias
    y obliga a repetirla entera, mientras que la espera sólo la hace más lenta. Y
    la espera se cuenta y se enseña, para que se vea que el sistema está frenando
    a propósito y no colgado.
    """
    ahora = time.monotonic()
    _RITMO[:] = [t for t in _RITMO if ahora - t < 60]
    if len(_RITMO) >= LIMITE_POR_MINUTO:
        espera = 60 - (ahora - _RITMO[0]) + 0.5
        if espera > 0:
            ESTADISTICAS["esperas"] += 1
            ESTADISTICAS["segundos_esperando"] += espera
            time.sleep(espera)
        _RITMO[:] = [t for t in _RITMO if time.monotonic() - t < 60]
    _RITMO.append(time.monotonic())


def _modelo_retirado(e):
    """
    ¿Este error es «ese modelo ya no existe» y no otra cosa?

    Se distingue a propósito de un fallo de red o de cuota: un 404 de modelo se
    arregla cambiando de modelo, y los demás no. Confundirlos haría que un corte
    de red disparara el plan de retirada y acabáramos evaluando con otro modelo
    sin motivo.
    """
    t = f"{type(e).__name__}: {e}".upper()
    return "NOT_FOUND" in t or "404" in t


def _escalones(esquema, prompt, json_forzado=True):
    """
    De más exigente a menos. Cada escalón renuncia a una garantía y lo dice.

    No es tolerancia a fallos por costumbre: los proveedores cambian qué opciones
    aceptan de una versión a la siguiente —el razonamiento configurable, el
    esquema estricto— y una opción retirada no debería tumbar la evaluación
    entera. Lo que sí es innegociable es la temperatura 0.
    """
    from google.genai import types

    base = {"temperature": 0, "system_instruction": prompt}
    if json_forzado:
        base["response_mime_type"] = "application/json"
    esq = {"response_json_schema": _esquema_gemini(esquema)} if esquema else {}

    sin_razonar = {}
    for constructor in (lambda: {"thinking_config": types.ThinkingConfig(thinking_budget=0)},
                        lambda: {"thinking_config": types.ThinkingConfig(thinking_level="low")}):
        try:
            sin_razonar = constructor()
            break
        except Exception:
            continue

    if esq:
        yield "esquema estricto, sin razonamiento", {**base, **esq, **sin_razonar}
        yield "esquema estricto", {**base, **esq}
    yield "sin esquema, sin razonamiento", {**base, **sin_razonar}
    yield "sin esquema", base


def _intentar(cliente, types, modelo, texto, config):
    """
    Una llamada, respetando el ritmo y reintentando si el proveedor dice que hay
    que esperar. Un 429 no es un error del sistema: es el proveedor pidiendo
    paciencia, y merece paciencia antes que un mensaje de fallo.
    """
    ultimo = None
    for intento in range(REINTENTOS_POR_CUOTA + 1):
        _esperar_turno()
        try:
            return cliente.models.generate_content(
                model=modelo, contents=texto,
                config=types.GenerateContentConfig(**config))
        except Exception as e:
            ultimo = e
            if not _es_cuota(e) or intento == REINTENTOS_POR_CUOTA:
                raise
            espera = _espera_sugerida(e)
            ESTADISTICAS["esperas"] += 1
            ESTADISTICAS["segundos_esperando"] += espera
            time.sleep(espera)
    raise ultimo


def _generar(prompt, texto, esquema, json_forzado=True):
    """
    Habla con el proveedor bajando por dos escaleras: la de opciones y la de
    modelos. La primera se recorre entera antes de tocar la segunda, porque
    cambiar de opción no cambia el veredicto y cambiar de modelo sí.
    """
    global MODELO_EFECTIVO, AVISO_MODELO
    from google import genai
    from google.genai import types

    cliente = genai.Client(api_key=_CLAVE)
    candidatos = [modelo_en_uso()] + [m for m in MODELOS_ALTERNATIVOS
                                      if m != modelo_en_uso()]
    ultimo = None

    for i, nombre in enumerate(candidatos):
        retirado = False
        for _etiqueta, config in _escalones(esquema, prompt, json_forzado):
            try:
                respuesta = _intentar(cliente, types, nombre, texto, config)
                if i > 0 and MODELO_EFECTIVO != nombre:
                    MODELO_EFECTIVO = nombre
                    AVISO_MODELO = (
                        f"El modelo anclado ({MODELO}) ya no está disponible para "
                        f"esta clave, así que la evaluación se ha hecho con "
                        f"{nombre}. Un cambio de modelo puede cambiar la lectura y, "
                        f"con ella, el veredicto: los resultados obtenidos antes y "
                        f"después de este cambio no son directamente comparables. "
                        f"Fija `GEMINI_MODELO` en los secretos para anclarlo de "
                        f"nuevo a propósito.")
                return respuesta
            except Exception as e:
                ultimo = e
                if _modelo_retirado(e):
                    # No tiene sentido seguir bajando escalones: el problema no son
                    # las opciones, es que ese modelo no existe para esta clave.
                    retirado = True
                    break
        if not retirado and i == 0 and len(candidatos) > 1:
            # Ha fallado por algo que no es el modelo. Probar otro modelo no
            # arreglaría nada y gastaría cuota.
            break

    ESTADISTICAS["errores"] += 1
    detalle = f"{type(ultimo).__name__}: {ultimo}" if ultimo else "sin detalle"
    if ultimo is not None and _es_cuota(ultimo):
        raise NoDisponible(
            f"Cuota agotada en el nivel gratuito ({LIMITE_POR_MINUTO} peticiones "
            f"por minuto). El sistema ya espera entre llamadas y reintenta, pero "
            f"esta vez no ha bastado. Espera un minuto y vuelve a pedirlo: lo que "
            f"ya se calculó está en caché y no se repite. Detalle: {detalle}")
    if ultimo is not None and _modelo_retirado(ultimo):
        raise NoDisponible(
            f"Ninguno de los modelos previstos está disponible para esta clave "
            f"(probados: {', '.join(candidatos)}). Mira qué modelos alcanza tu "
            f"clave y fija el que quieras en `GEMINI_MODELO`. Detalle: {detalle}")
    raise NoDisponible(f"La llamada al modelo ha fallado: {detalle}")


def _llamar(prompt, texto, esquema, sin_cache=False):
    """
    Única función de todo el sistema que habla con un modelo.

    Devuelve un objeto que valida contra `esquema`. Temperatura 0, razonamiento
    desactivado y salida forzada a JSON: lo que se quiere de aquí es una lectura,
    no una redacción.
    """
    if not esta_disponible():
        raise NoDisponible(por_que_no())

    huella = _huella(prompt, texto, esquema)
    if not sin_cache:
        guardado = _de_cache(huella)
        if guardado is not None:
            ESTADISTICAS["cache"] += 1
            return guardado

    try:
        respuesta = _generar(prompt, texto, esquema)
        salida = json.loads(respuesta.text)
    except NoDisponible:
        raise
    except json.JSONDecodeError as e:
        ESTADISTICAS["errores"] += 1
        raise NoDisponible(f"El modelo no ha devuelto JSON válido: {e}") from e

    ESTADISTICAS["llamadas"] += 1
    _a_cache(huella, salida)
    return salida


def _llamar_texto(prompt, texto, sin_cache=False):
    """
    Igual que `_llamar`, pero la salida es prosa en vez de JSON.

    Existe por una sola razón: el redactor del informe. Ahí no se está leyendo
    nada ni decidiendo nada —el veredicto ya está calculado— y lo que se pide al
    modelo es que lo cuente. Mantenerlo aparte deja claro que ninguna de las dos
    funciones puede colarse en el sitio de la otra.
    """
    if not esta_disponible():
        raise NoDisponible(por_que_no())

    huella = _huella(prompt, texto, "texto/1")
    if not sin_cache:
        guardado = _de_cache(huella)
        if guardado is not None:
            ESTADISTICAS["cache"] += 1
            return guardado

    # Misma escalera de modelos y opciones que la lectura, pero sin forzar JSON:
    # aquí lo que se espera es prosa. `esquema=None` quita el escalón del esquema.
    respuesta = _generar(prompt, texto, None, json_forzado=False)
    salida = (respuesta.text or "").strip()

    if not salida:
        ESTADISTICAS["errores"] += 1
        raise NoDisponible("El modelo ha devuelto una respuesta vacía.")

    ESTADISTICAS["llamadas"] += 1
    _a_cache(huella, salida)
    return salida


def consultar(prompt, texto, esquema, sin_cache=False):
    """
    Entrada pública para quien necesita una respuesta estructurada que no es una
    lectura de documento: hoy, el panel de jueces.
    """
    return _llamar(prompt, texto, esquema, sin_cache)


def redactar(prompt, texto, sin_cache=False):
    """Entrada pública para prosa. Hoy, el informe."""
    return _llamar_texto(prompt, texto, sin_cache)


def extraer_con_llm(texto_documento, esquema_campos, prompt, sin_cache=False):
    """Documento -> campos. Misma salida que el extractor determinista de la rama."""
    return _llamar(prompt, texto_documento, esquema_campos, sin_cache)


def interpretar_con_llm(texto_respuesta, esquema_salida, prompt, sin_cache=False):
    """Respuesta del módulo -> incidencias. Misma salida que `interpretar()`."""
    return _llamar(prompt, texto_respuesta, esquema_salida, sin_cache)


# ===========================================================================
# Estabilidad: el evaluador se mide a sí mismo
# ===========================================================================

def medir_estabilidad(texto, esquema, prompt, k=3):
    """
    Ejecuta la misma extracción K veces saltándose la caché y dice qué campos
    cambian de una a otra.

    Es la comprobación que el evaluador se aplica a sí mismo. Si la lectura no es
    estable, la verdad de campo no es reproducible, y entonces el veredicto que
    salga de ella tampoco lo es: hay que declararlo antes de que lo descubra otro.
    """
    lecturas = []
    for _ in range(max(2, k)):
        lecturas.append(_llamar(prompt, texto, esquema, sin_cache=True))

    claves = sorted({c for l in lecturas if isinstance(l, dict) for c in l})
    inestables = {}
    for c in claves:
        valores = [json.dumps(l.get(c), ensure_ascii=False, sort_keys=True,
                              default=str) for l in lecturas]
        if len(set(valores)) > 1:
            inestables[c] = sorted(set(valores))

    return {"ejecuciones": len(lecturas), "campos": len(claves),
            "inestables": inestables, "estable": not inestables,
            "lecturas": lecturas}


# ===========================================================================
# Entrada única que usan las ramas
# ===========================================================================

def conformar(campos, esquema):
    """
    Convierte lo que devuelve el modelo a los tipos que esperan las reglas.

    Es la frontera, y hasta ahora faltaba. Un extractor determinista devuelve un
    `date`; el modelo devuelve `"2026-08-16"`, que es una cadena. Mientras el
    valor sólo se enseñaba no pasaba nada, pero en cuanto una regla lo compara
    —`fecha_evaluacion <= campos["fecha_caducidad"]`— revienta con un TypeError, y
    revienta lejos del sitio donde se produjo el problema.

    La conversión la dirige el **esquema que ya declara cada rama**: ahí está
    escrito qué campo es una fecha, cuál un entero y cuál un booleano. No hacía
    falta información nueva, sólo usarla.

    Devuelve (campos, rechazados). Se rechaza —y se dice— cuando:

      · el modelo inventa un campo que no está en el esquema de la rama
      · devuelve algo que no se puede convertir al tipo declarado

    Un campo rechazado se queda en None, nunca con el valor crudo: un valor con el
    tipo equivocado circulando por el núcleo es peor que un hueco, porque el hueco
    se ve y el otro no.
    """
    from .texto import fecha_de, numero

    props = (esquema or {}).get("properties") or {}
    fuera, rechazados = {}, {}

    for clave, valor in (campos or {}).items():
        declarado = props.get(clave)
        if declarado is None:
            rechazados[clave] = "campo que no está en el esquema de la rama"
            continue
        if valor is None:
            fuera[clave] = None
            continue

        tipos = declarado.get("type")
        tipos = [tipos] if isinstance(tipos, str) else list(tipos or [])
        tipos = [t for t in tipos if t != "null"]
        formato = declarado.get("format", "")

        try:
            if formato == "date" or clave.startswith("fecha_"):
                convertido = valor if isinstance(valor, date) else fecha_de(valor)
                if convertido is None:
                    rechazados[clave] = f"no es una fecha reconocible ({valor!r})"
                    fuera[clave] = None
                    continue
            elif "integer" in tipos:
                convertido = valor if isinstance(valor, int) and not isinstance(valor, bool) \
                    else numero(valor)
                if convertido is None:
                    rechazados[clave] = f"no es un entero ({valor!r})"
                    fuera[clave] = None
                    continue
            elif "number" in tipos:
                convertido = float(valor)
            elif "boolean" in tipos:
                if isinstance(valor, bool):
                    convertido = valor
                else:
                    t = str(valor).strip().lower()
                    if t in ("true", "sí", "si", "1", "verdadero"):
                        convertido = True
                    elif t in ("false", "no", "0", "falso"):
                        convertido = False
                    else:
                        rechazados[clave] = f"no es un booleano ({valor!r})"
                        fuera[clave] = None
                        continue
            elif "array" in tipos:
                convertido = list(valor) if isinstance(valor, (list, tuple)) else [valor]
            elif "object" in tipos:
                if not isinstance(valor, dict):
                    rechazados[clave] = f"no es un objeto ({valor!r})"
                    fuera[clave] = None
                    continue
                convertido = valor
            else:
                convertido = str(valor)
        except (TypeError, ValueError) as e:
            rechazados[clave] = f"no se ha podido convertir ({valor!r}: {e})"
            fuera[clave] = None
            continue

        fuera[clave] = convertido

    return fuera, rechazados


def combinar(deterministas, del_modelo, campos_permitidos=None):
    """
    Modo asistido: manda lo determinista y el modelo sólo rellena huecos.

    Devuelve (campos, procedencia). La procedencia se enseña en la interfaz para
    que se vea qué dato viene de una regla y cuál de un modelo: sin eso, el
    evaluador dejaría de ser auditable justo donde más falta hace.
    """
    campos = dict(deterministas)
    procedencia = {k: "regla" for k in campos}
    for k, v in (del_modelo or {}).items():
        if campos_permitidos is not None and k not in campos_permitidos:
            continue
        if campos.get(k) is None and v is not None:
            campos[k] = v
            procedencia[k] = "modelo"
    return campos, procedencia


def resolver(modo, deterministas, texto, esquema, prompt, campos_permitidos=None):
    """
    Punto único de entrada. Devuelve (campos, procedencia).

    No degrada en silencio: si el modo pedido necesita el modelo y el modelo no
    está, levanta `NoDisponible` para que la interfaz lo diga. Un evaluador que
    se cae a reglas sin avisar estaría mintiendo sobre cómo ha leído.

    Y no hay un modo «sólo modelo». Lo hubo, y era un error de diseño: ponía dos
    caminos a competir por el mismo trabajo, uno de ellos no reproducible, y
    convertía al modelo en alternativa de las reglas en vez de en apoyo. La verdad
    de campo la calculan las reglas; el modelo rellena los huecos que dejan.
    """
    if modo == "determinista":
        return dict(deterministas), {k: "regla" for k in deterministas}

    # Si las reglas lo han encontrado todo, no se llama al modelo. El rescate sólo
    # tiene sentido cuando hay algo que rescatar, y no gastar es parte del diseño.
    # Va **antes** de comprobar si el modelo está disponible: un documento que las
    # reglas leen enteras no debería exigir clave para evaluarse.
    huecos = [k for k, v in deterministas.items() if v is None]
    if campos_permitidos is not None:
        huecos = [k for k in huecos if k in campos_permitidos]
    if not huecos:
        return dict(deterministas), {k: "regla" for k in deterministas}

    if not esta_disponible():
        raise NoDisponible(por_que_no())

    # Nada de lo que devuelve el modelo entra en el núcleo sin pasar por aquí.
    del_modelo, rechazados = conformar(extraer_con_llm(texto, esquema, prompt),
                                       esquema)
    marcas = {k: f"modelo (descartado: {m})" for k, m in rechazados.items()}
    campos, procedencia = combinar(deterministas, del_modelo, campos_permitidos)
    return campos, {**procedencia, **marcas}


# ===========================================================================
# 9. Anclaje literal: cómo se comprueba lo que dice el modelo
# ===========================================================================
# El modo asistido pasa de rescate ocasional a vía principal en cuanto el corpus
# son escaneos, y eso cambia lo que está en juego. Mientras el modelo rellenaba
# un hueco suelto, un error suyo era una molestia. Cuando la verdad de campo sale
# de él, un error suyo **acusa a un compañero de un fallo que no ha cometido** — y
# la autoridad de todo este bloque se apoya en que eso no pase.
#
# La respuesta no es confiar más ni menos: es no tener que confiar. Cada valor
# que el modelo aporta debe venir con el fragmento literal del documento que lo
# sostiene, y ese fragmento se busca en el texto. Si no está, el valor se
# descarta. La comprobación no usa modelo: es una búsqueda de texto, la hace
# cualquiera y sale igual las mil veces.
#
# Es el mismo candado que ya gobierna al asesor —toda recomendación cita un caso
# o se descarta entera— aplicado a la lectura.

def _solo_letras(s):
    """Texto reducido a lo que sobrevive a un OCR: letras y números, sin más."""
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def fragmento_presente(cita, texto, minimo=0.75):
    """
    ¿Está esa cita en el documento?

    No exige coincidencia exacta y no es por generosidad: sobre un OCR, el modelo
    corrige erratas al citar —escribe «cuatro de abril» donde el reconocimiento
    puso «cuatroúe abril»— y una comparación literal descartaría citas buenas.

    Pero tampoco basta con que las palabras estén *en alguna parte*. Ésa fue la
    primera versión y colaba lo peor: «a 10 de diciembre de 2017» daba por buena
    una fecha inventada porque el «2017» aparecía en otra cláusula, a diez folios
    de distancia. Un documento largo contiene casi cualquier palabra suelta.

    Así que se busca una **ventana** del texto donde las palabras de la cita
    aparezcan juntas, y se exige que ahí estén todos sus números. Es lo que
    distingue «este fragmento está en el documento» de «estas palabras existen en
    el idioma».

    Devuelve (presente, proporción encontrada en la mejor ventana).
    """
    from nucleo.texto import UNIDADES, DECENAS, CENTENAS
    NUMERICAS = set(UNIDADES) | set(DECENAS) | set(CENTENAS) | {"mil"}

    t_texto = _solo_letras(texto).split()
    t_cita = _solo_letras(cita).split()
    if not t_cita or not t_texto:
        return False, 0.0

    utiles = [p for p in t_cita if len(p) >= 4 or p.isdigit() or p in NUMERICAS]
    numeros = [p for p in t_cita if p.isdigit() or p in NUMERICAS]
    if not utiles:
        return False, 0.0

    # Ventana generosa —tres veces la cita— porque el OCR intercala basura entre
    # palabras: números de página, rayas de la máquina de escribir, marcas de
    # margen. Lo que importa es la vecindad, no la contigüidad exacta.
    ancho = max(20, len(t_cita) * 3)
    objetivo = set(utiles)
    mejor = 0.0
    for ini in range(0, max(1, len(t_texto) - 1), max(1, ancho // 3)):
        ventana = set(t_texto[ini: ini + ancho])
        if any(n not in ventana for n in numeros):
            continue
        prop = len(objetivo & ventana) / len(objetivo)
        mejor = max(mejor, prop)
        if mejor >= 0.999:
            break
    return mejor >= minimo, round(mejor, 2)


def anclar(campos, procedencia, citas, texto, exigen_cita):
    """
    Descarta los valores del modelo cuya cita no esté en el documento.

    `citas` es {campo: fragmento literal}. `exigen_cita` son los campos a los que
    se les exige: los que afirman un hecho del documento. No se le exige cita a
    lo que es derivado ni a lo que el modelo se limita a clasificar.

    Devuelve (campos, procedencia, descartes). Los descartes se declaran: un
    valor que se cae en silencio deja al veredicto sin explicación.
    """
    campos, procedencia = dict(campos), dict(procedencia)
    descartes = {}
    for campo in exigen_cita:
        if procedencia.get(campo) != "modelo" or campos.get(campo) is None:
            continue
        cita = (citas or {}).get(campo)
        if not cita:
            descartes[campo] = "el modelo no aporta el fragmento que lo sostiene"
        else:
            ok, prop = fragmento_presente(cita, texto)
            if not ok:
                descartes[campo] = (f"la cita no aparece en el documento "
                                    f"(coincide el {int(prop*100)} % de sus "
                                    f"palabras): «{str(cita)[:90]}»")
        if campo in descartes:
            campos[campo] = None
            procedencia[campo] = f"modelo (descartado: {descartes[campo][:60]})"
    return campos, procedencia, descartes
