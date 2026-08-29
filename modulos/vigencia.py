"""
Rama de evaluación del módulo de VIGENCIA DOCUMENTAL — Martín de Lucas · RALSA.
Módulo evaluado: IAlert. Conexión C1 · Martín → Evaluación y Calidad.

Qué hace el módulo evaluado: clasifica documentos jurídicos por su estado de
vigencia y avisa de los vencimientos con antelación configurable.

Qué hace esta rama: lee los mismos documentos por su cuenta, deduce de sus
cláusulas qué estado y qué fechas corresponden, y sólo entonces contrasta la
salida del módulo contra ese cálculo. La unidad evaluada es el documento; el
resto —contraste, métricas, batería y veredicto— es el núcleo común.

La batería son las ocho preguntas de la prueba inicial, en su mismo orden, más
dos casos transversales que aplico a todos los módulos (cobertura y
repetibilidad) y dos que salieron de la primera salida real, el 28/08 (la
naturaleza de la prórroga y la fecha crítica de aviso). Doce en total, y cada uno
lleva anotado de dónde viene.

Cómo se lee un documento, que es lo que cambió al llegar el corpus real
----------------------------------------------------------------------
Los trece documentos de RALSA son fotocopias: ninguno tiene capa de texto. El
evaluador los reconoce por OCR y **declara la vía**, porque comparar su lectura
contra la del módulo no es lo mismo que comparar contra el documento.

Sobre ese texto, las reglas leen lo que pueden y el modelo rellena lo que no
—modo asistido—, con tres candados que no usan modelo: la cita tiene que estar en
el documento, la aritmética de las fechas tiene que cuadrar, y ante dos fechas
candidatas para el mismo campo no se elige, se declara la ambigüedad.

Y hay una distinción que sostiene todo lo demás: **no saber leer un documento no
es lo mismo que contradecir al módulo**. Cuando el evaluador no encuentra la
cláusula de duración se abstiene — ese documento sale del contraste y sus casos
quedan pendientes, en lugar de contar como fallo de Martín.

Tres correcciones ajenas están cableadas a propósito:

  1. Un documento sin fecha de caducidad no se declara vigente por defecto. La
     pregunta 8 lo pedía como «indefinido»; su corrección lo afina: título
     consumado si el documento agota su objeto, y vigencia no determinada en
     cualquier otro caso. Nunca vigencia indefinida.
  2. La pregunta 5 decía «tomar como bueno el documento vigente». Su corrección:
     hay que verificar la relación de versionado o sustitución, no quedarse
     simplemente con el que no ha caducado. El caso 5 exige que el módulo declare
     la sustitución, no que acierte por descarte.
  3. De Íñigo, al etiquetar a mano los documentos reales (28/08): lo que separa
     `titulo_consumado` de `no_clasificado` no es tener o no fecha —en los dos
     casos falta— sino **si el documento tiene que tenerla**. Un anexo que cambia
     el día de facturación se agota al firmarse; uno que subroga a una parte o
     financia unas obras deja obligaciones vivas mientras viva el contrato. De
     ahí sale `requiere_fecha_caducidad`, y de ahí que se retirase el estado
     `depende_de_otro` que me había inventado: el vocabulario de esta rama es el
     de la prueba inicial, no uno propio.

Vocabulario del módulo evaluado, observado en su interfaz: los estados que emite
son «Vigente» y «Obsoleto», con la validez formal en un eje aparte y la urgencia
en otro, y agrupa las versiones de un mismo inmueble en una «cadena documental»
formada por la dirección normalizada. La traducción a los estados canónicos está
en SINONIMOS; la cadena documental se calcula aquí igual que él la calcula.
"""

import csv
import io
import json
import re
from datetime import date, timedelta

from nucleo import bateria as B
from nucleo import contraste as C
from nucleo import jueces as J
from nucleo import llm
from nucleo.texto import (anios_de, buscar_fecha, duracion_dias, fecha_de,
                          fecha_unica, numero_en_letra, plano,
                          restar_duracion, sumar_anios)

# ===========================================================================
# Ficha de la rama
# ===========================================================================

ESTADOS = {
    "vigente": "Vigente",
    "caducado": "Caducado",
    "obsoleto": "Obsoleto",
    "titulo_consumado": "Título consumado",
    "no_clasificado": "Vigencia no determinada",
    "no_aplica_vigencia": "Sin vigencia que determinar",
}

# Ventana por defecto de la pregunta 2. Configurable en la interfaz.
VENTANA_DIAS = 30

CASOS = {
    1: "Estado del documento en la fecha real de consulta",
    2: "Documentos que vencen dentro de la ventana consultada",
    3: "Exactitud de la fecha de caducidad devuelta",
    4: "Incoherencia entre fecha de emisión y fecha de caducidad",
    5: "Relación de versionado dentro de la cadena documental",
    6: "Criterio fijo y declarado cuando el documento vence el mismo día",
    7: "Aviso con antelación configurable",
    8: "Documento sin fecha de caducidad: vigencia no determinada",
    9: "Cobertura del conjunto entregado",
    10: "Repetibilidad del veredicto",
    11: "Naturaleza de la prórroga declarada",
    12: "Fecha crítica de aviso derivada del plazo de preaviso",
}

# La integridad del escaneo estuvo un rato como caso 13 y se retiró el 28/08.
#
# El motivo es de alcance, no de dificultad: el módulo de Martín clasifica
# **vigencia documental**, y la vigencia se decide con la cláusula de duración.
# Que al escaneo le falten dos páginas es un problema de quien digitalizó el
# expediente, no del clasificador — mientras la cláusula esté, el estado que
# emite es correcto. Suspenderle por eso sería medirle por un trabajo que no es
# el suyo.
#
# Se conserva como **hallazgo**: informa y no puntúa. Sigue mereciendo la pena
# decirlo —un documento incompleto declarado «apto como referencia» es un riesgo
# aguas abajo— pero es información para quien gestiona el archivo, no una nota
# para el módulo.

# De qué pregunta de la prueba inicial viene cada caso. Los dos últimos son míos,
# transversales a todos los módulos, y se declaran como tales.
ORIGEN = {1: "pregunta 1", 2: "pregunta 2", 3: "pregunta 3", 4: "pregunta 4",
          5: "pregunta 5", 6: "pregunta 6", 7: "pregunta 7", 8: "pregunta 8",
          9: "criterio transversal", 10: "criterio transversal",
          11: "salida real 28/08", 12: "salida real 28/08"}

ASPECTOS = {
    1: ("Hay documentos cuyo estado no se resuelve correctamente en la fecha de consulta",
        "Revisar la extracción de la cláusula de duración: el evaluador localiza la "
        "fecha de vencimiento en el propio documento, luego la información estaba "
        "disponible. El estado debe emitirse junto con la fecha de caducidad usada "
        "como referencia, para que sea verificable."),
    2: ("La ventana de vencimientos no devuelve exactamente los documentos del rango",
        "Acotar la consulta por los dos extremos: excluir los ya vencidos y los que "
        "vencen más allá del plazo. Un listado que incluye vencidos convierte el "
        "aviso en ruido."),
    3: ("La fecha de caducidad devuelta no coincide con la que consta en el documento",
        "Devolver la fecha en formato estándar junto al identificador del documento, "
        "y extraerla de la cláusula de duración en lugar de derivarla."),
    4: ("No se señala la incoherencia entre fecha de emisión y fecha de caducidad",
        "Emitir un aviso de inconsistencia con ambas fechas a la vista para revisión "
        "manual, en lugar de tomar por buena la fecha de caducidad."),
    5: ("La relación de versionado no se declara",
        "Devolver la fecha de la versión vigente junto con la referencia a la versión "
        "sustituida. Quedarse con la no caducada sin declarar la sustitución acierta "
        "por descarte: si las dos estuvieran vigentes, o las dos caducadas, el "
        "criterio no serviría."),
    6: ("El vencimiento en el mismo día no sigue un criterio fijo y declarado",
        "Fijar la regla de negocio —por ejemplo vigente hasta las 23:59 del día de "
        "caducidad— aplicarla igual a todos los documentos y declarar en la salida "
        "que se trata de un caso límite."),
    7: ("Las alertas no se generan en los umbrales definidos",
        "Emitir cada alerta con el documento, la fecha de caducidad y la antelación "
        "aplicada, y permitir configurar el plazo."),
    8: ("Se declara vigente, o con fecha, un documento sin caducidad determinable",
        "Un documento sin plazo no es vigente por defecto: título consumado si agota "
        "su objeto, y vigencia no determinada / requiere revisión en cualquier otro "
        "caso, salvo evidencia explícita de vigencia indefinida."),
    9: ("Hay documentos entregados que no reciben estado",
        "Emitir un registro por cada documento recibido, incluidos los que no puedan "
        "clasificarse: un documento que desaparece en silencio se lee aguas abajo "
        "como un documento sin problemas."),
    10: ("El determinismo del veredicto no está demostrado",
         "Ejecutar la clasificación dos veces sobre el mismo conjunto sin modificar "
         "los documentos y comparar estados, no la redacción."),
    11: ("La prórroga se declara tácita cuando la cláusula la exige expresa",
         "No son matices del mismo campo: son comportamientos opuestos al llegar "
         "el vencimiento. Con prórroga tácita el contrato se renueva solo salvo "
         "que alguien avise; con prórroga expresa se extingue salvo que las partes "
         "acuerden lo contrario. Quien lea «prórroga tácita ✓» no hará nada y el "
         "contrato caducará. Conviene leer el verbo de la cláusula —«se prorrogará "
         "automáticamente» frente a «las partes podrán convenir… mediante acuerdo "
         "expreso»— y, cuando no sea concluyente, dejar el campo sin marcar en "
         "lugar de elegir un valor por defecto."),
    12: ("La fecha crítica de aviso no se emite, teniendo el plazo para calcularla",
         "Con fecha de vencimiento y plazo de preaviso, la fecha crítica es una "
         "resta. Es además el único dato accionable de la ficha: el vencimiento "
         "dice cuándo acaba, la fecha crítica dice cuándo hay que moverse. Ojo a "
         "la unidad: tres meses antes del 15/01/2030 es el 15/10/2029, no el "
         "17/10/2029 que sale de restar noventa días."),
}

ALCANCE = {n: "ejecucion" for n in CASOS}

# Severidad declarada al diseñar cada caso, antes de ejecutarlo: mide qué ocurre
# aguas abajo si el fallo pasa desapercibido, no cuánto molesta. Las críticas son
# las tres que producen silencio — un documento que se da por bueno sin serlo y
# que nadie vuelve a mirar.
SEVERIDAD = {
    1: "critica",   # un vencido dado por vigente no genera ninguna alarma después
    2: "alta",      # el aviso llega mal, pero llega: se revisa a mano
    3: "alta",      # la fecha viaja aguas abajo y contamina lo que se calcule con ella
    4: "media",     # es un aviso sobre la calidad del dato, no sobre la vigencia
    5: "critica",   # tomar por bueno el documento sustituido no deja rastro
    6: "media",     # afecta a un día concreto y el criterio es declarable
    7: "alta",      # sin preaviso el vencimiento se descubre cuando ya ocurrió
    8: "critica",   # declarar vigente lo que no se sabe es la tranquilidad falsa
    9: "critica",   # un documento que desaparece se lee como documento sin problemas
    10: "alta",     # sin repetibilidad ninguna medición anterior se sostiene
    11: "critica",  # invierte lo que pasa al vencer: renovar solo o extinguirse
    12: "alta",     # el aviso existe pero sin fecha no dispara nada
}


# ---------------------------------------------------------------------------
# Criterios cualitativos: lo que la batería no alcanza
# ---------------------------------------------------------------------------
# La batería comprueba si el estado asignado es el correcto. Eso deja fuera todo
# lo que decide si la salida sirve: si se entiende, si distingue lo que sabe de lo
# que supone, si llama igual a la misma cosa. Son preguntas que no tienen regla,
# y por eso van al panel de jueces, que puntúa sólo donde coincide.

CUALITATIVOS = [
    J.criterio(
        "accionable",
        "El aviso permite actuar sin abrir el contrato",
        "¿Puede el destinatario saber, leyendo únicamente esta salida, qué "
        "documento concreto requiere acción y en qué plazo, sin tener que abrir el "
        "contrato original?",
        "El módulo existe para que alguien renueve a tiempo. Una clasificación "
        "correcta que obliga a abrir el documento para saber qué hacer no ahorra "
        "el trabajo que venía a ahorrar."),
    J.criterio(
        "justifica",
        "El estado viene justificado, no sólo afirmado",
        "¿La salida indica en qué se basa para asignar el estado —una fecha, una "
        "cláusula, un plazo—, o se limita a afirmar el estado sin decir de dónde "
        "sale?",
        "Aguas abajo, Mencía tiene que poder contrastar estados. Un estado sin "
        "razón declarada no se puede contrastar: hay que creerlo o rehacerlo."),
    J.criterio(
        "prudencia",
        "Distingue lo que sabe de lo que no puede saber",
        "Cuando un documento no contiene la información necesaria para determinar "
        "su vigencia, ¿la salida transmite esa incertidumbre, o afirma un estado "
        "con la misma rotundidad que en los documentos completos?",
        "Es el fallo más caro de este módulo. Un documento del que no se puede "
        "decir nada presentado como «vigente» produce una tranquilidad falsa, y "
        "nadie vuelve a mirarlo."),
    J.criterio(
        "vocabulario",
        "Usa un vocabulario consistente",
        "¿Emplea siempre el mismo término para el mismo estado a lo largo de toda "
        "la salida, o alterna sinónimos —vigente, válido, en vigor, activo— para "
        "referirse a la misma situación?",
        "El consumidor de esta salida es otro módulo, no una persona. Dos "
        "palabras para un estado son dos estados para quien parsea."),
]


# ---------------------------------------------------------------------------
# Salida real del módulo, 28/08/2026
# ---------------------------------------------------------------------------
# La ficha que IAlert emite para el contrato de arrendamiento de la estación de
# servicio de Calatorao, copiada de su pantalla tal cual. Es la primera salida
# real de este módulo que entra en el sistema: hasta ahora la batería estaba
# cerrada y sin nada con lo que contrastar.
#
# Se guarda aquí, y no en un fichero suelto, por el mismo motivo que la respuesta
# de Juan: el recorrido de la demo tiene que poder ejecutarse sin que nadie pegue
# nada a mano, y una evaluación que sólo existe si alguien recuerda pegar el
# texto correcto no es reproducible.
SALIDA_IALERT_CRED = """\
CONTRATO ARRENDAMIENTO CRED
Vigente
Actualización anual de la renta por IPC (140 días)
El documento se puede usar como referencia válida.
Este documento es un contrato de arrendamiento de industria de una estación de servicio destinado a la venta de carburantes, ubicado en CR A-2, 280,1 (Calatorao).
Validez formal

Campo | Valor
Archivo | C:\\Users\\marti\\Documents\\TFG\\Modelo0.1\\Frontend..\\datos\\ARRENDAMIENTO CRED.pdf
Ciudad | Calatorao
Dirección | —
Tipo de documento | Contrato de arrendamiento de industria de estación de servicio
Familia documental | Contratos y relaciones mercantiles
Cadena documental | —
Fecha de firma | 2015-12-10
Fecha de inicio | 2016-01-15
Plazo | 14 años
Fecha de vencimiento | 2030-01-15
Prórroga tácita | ✓
Preaviso (días) | 90
Fecha crítica de alerta | —
Arrendador | SERVIARAGÓN, S.A.
Arrendatario | CAMPSA ESTACIONES DE SERVICIO, S.A.
Fecha de subida | 2026-08-26 15:56
Subido por | —
Última modificación | 2026-08-26 15:56
Número de páginas | 8
"""


# ---------------------------------------------------------------------------
# Salidas reales de IAlert — transcritas de la pantalla de Martín (28-29/08/2026)
# ---------------------------------------------------------------------------
# Las fichas que IAlert emite para los documentos de RALSA, copiadas de los
# vídeos que grabó Íñigo de su pantalla. Están aquí, y no en un fichero suelto,
# por el mismo motivo que la respuesta de Juan: una evaluación que sólo existe si
# alguien recuerda pegar el texto correcto no es reproducible, y la demo tiene que
# poder ejecutarse sin que nadie pegue nada.
#
# Lo que no se veía en el vídeo **no se ha rellenado**. Un campo ausente en esta
# transcripción significa «no lo he podido leer», no «el módulo no lo emite», y
# el evaluador lo tratará como lo que es: un dato que falta, no un fallo de
# Martín. Inventar aquí un valor plausible sería exactamente el fallo que este
# sistema existe para detectar, cometido en la propia fuente de la evaluación.
SALIDAS_IALERT = {
    '20160119_ANEXO': """\
20160119 ANEXO
Vigente
Vencimiento del documento (1240 días)
El documento se puede usar como referencia válida.
Validez formal
Archivo | C:\\Users\\marti\\Documents\\TFG\\Modelo0.1\\Frontend..\\datos\\20160119 ANEXO.pdf
Ciudad | Zaragoza
Dirección | CR A-2 281,6 CALATORAO
Tipo de documento | Contrato de arrendamiento de local comercial (anexo)
Familia documental | Contratos y relaciones mercantiles
Cadena documental | cr a 2 281 6 calatorao zaragoza
Fecha de firma | 2016-01-19
Fecha de inicio | 2016-01-19
Plazo | 14 años
Fecha de vencimiento | 2030-01-19
""",

    '20190115_SUBROGACION_A_REPSOL_COMERCIALLOS_OLIVOS': """\
20190115 SUBROGACION A REPSOL COMERCIAL-LOS OLIVOS
No clasificado (revisar)
Falta la fecha de vencimiento; revisa el documento y complétala manualmente.
Validez formal
Archivo | C:\\Users\\marti\\Documents\\TFG\\Modelo0.1\\Frontend..\\datos\\SUBROGACION A REPSOL COMERCIAL-LOS OLIVOS.pdf
Ciudad | Zaragoza
Dirección | —
Tipo de documento | Addendum de contrato de arrendamiento de estación de servicio
Familia documental | Contratos y relaciones mercantiles
Cadena documental | —
Fecha de firma | 2019-01-15
Fecha de inicio | 2019-01-15
Plazo | —
Fecha de vencimiento | —
Preaviso (días) | —
Fecha crítica de alerta | —
Arrendador | SERVIARAGON, S.A.
Arrendatario | REPSOL COMERCIAL DE PRODUCTOS PETROLIFEROS, S.A.
Número de páginas | 4
""",

    '20190208_APORTACION_REPSOL_A_REFORMA_TIENDA_008': """\
20190208 APORTACION REPSOL A REFORMA TIENDA 008
No clasificado (revisar)
No se ha podido determinar con seguridad la vigencia de este documento; revísalo manualmente.
Validez formal
Archivo | C:\\Users\\marti\\Documents\\TFG\\Modelo0.1\\Frontend..\\datos\\APORTACION REPSOL A REFORMA TIENDA 008.pdf
Ciudad | Madrid
Dirección | CR-A2, 280,1
Tipo de documento | Anexo al contrato de arrendamiento industrial
Familia documental | Contratos y relaciones mercantiles
Cadena documental | cr a2 280 1 madrid
Fecha de firma | 2019-02-08
Fecha de inicio | 2019-02-08
Plazo | —
Fecha de vencimiento | —
Preaviso (días) | —
Fecha crítica de alerta | —
Arrendador | REPSOL COMERCIAL, S.A.
Arrendatario | SERVI GON, S.A.
Número de páginas | 4
""",

    '20200522_APORTACION_REPSOL_A_REFORMA_EESS': """\
20200522 APORTACION REPSOL A REFORMA EESS
Archivo | C:\\Users\\marti\\Documents\\TFG\\Modelo0.1\\Frontend..\\datos\\APORTACION REPSOL A REFORMA EESS.pdf
Ciudad | Calatorao
Dirección | CR-A2, nº 12933
Tipo de documento | Anexo al contrato de arrendamiento industrial
Familia documental | Contratos y relaciones mercantiles
Cadena documental | cr a2 no 12933 calatorao
Fecha de firma | 2020-05-22
Fecha de inicio | 2020-05-22
Plazo | —
Fecha de vencimiento | 2021-12-31
Preaviso (días) | —
Fecha crítica de alerta | —
Arrendador | REPSOL COMERCIAL DE PRODUCTOS PETROLÍFEROS, S.A.
Arrendatario | SERVIARAGON S.A.
""",

    'DERECHOS_SUPERFICIE': """\
DERECHOS SUPERFICIE
Obsoleto
El documento se puede desechar o conservar como fuente histórica.
Validez formal
Archivo | C:\\Users\\marti\\Documents\\TFG\\Modelo0.1\\Frontend..\\datos\\DERECHOS SUPERFICIE.pdf
Ciudad | Calatorao
Dirección | Autovía de Aragón, M.DCHA., Ctra. N-II Km. 280.100
Tipo de documento | Contrato de derecho de superficie y cesión de derechos de construcción
Familia documental | Contratos y relaciones mercantiles
Cadena documental | autovia de aragon m dcha ctra n ii km 280 100 calatorao
Fecha de firma | 1995-04-04
Fecha de inicio | 1995-04-04
Plazo | 25 años
Fecha de vencimiento | 2020-04-04
Preaviso (días) | —
Fecha crítica de alerta | —
Número de páginas | 20
""",

}

# Todas juntas, que es como se pega una tanda en la interfaz.
SALIDA_IALERT_TODAS = "\n\n".join(SALIDAS_IALERT.values())


def evidencia_panel(respuesta_cruda, limite=6000):
    """
    Lo que ven los jueces: la salida del módulo tal cual la emitió.

    No se les da la verdad de campo ni el resultado de la batería a propósito.
    Están juzgando si la salida se sostiene por sí sola, que es exactamente la
    situación de quien la recibe.
    """
    texto = (respuesta_cruda or "").strip()
    if len(texto) > limite:
        texto = texto[:limite] + "\n[...salida recortada por longitud...]"
    return texto or "(el módulo no ha emitido salida)"


FICHA = {
    "id": "vigencia",
    "nombre": "Vigencia documental",
    "responsable": "Martín de Lucas",
    "empresa": "RALSA",
    "modulo_evaluado": "IAlert",
    "conexion": "C1 · Martín → Evaluación y Calidad",
    "estado_conexion": "documentada",
    "funcion": ("Clasifica documentos jurídicos por su estado de vigencia y "
                "avisa de los vencimientos con antelación configurable."),
    "verifica": "Íñigo Daza",
    "operativo": True,
    # Los seis contratos son ficticios y lo declaran ellos mismos, así que se
    # pueden mandar a un nivel gratuito sin comprometer nada de nadie.
    "ia_permitida": True,
    "panel_permitido": True,
    "cualitativos": CUALITATIVOS,
    "unidad": ("documento", "los estados de vigencia"),
    "entrada": "Los documentos jurídicos en PDF que se le dieron al módulo.",
    "entrada_respuesta": (
        "Pega la salida de IAlert tal como la emite. Se acepta JSON, CSV, la **ficha "
        "de documento con su tabla «Campo / Valor»** —lo que sale al copiar la "
        "pantalla—, las fichas resumidas y las líneas de «Próximos eventos». El "
        "intérprete reconoce las cinco formas y separa los estados de los eventos."
    ),
    "casos": CASOS,
    "aspectos": ASPECTOS,
    "alcance": ALCANCE,
    "severidad": SEVERIDAD,
    "origen_casos": ORIGEN,
    "esquema_campos": {
        "type": "object",
        "properties": {
            "fecha_emision": {"type": ["string", "null"], "format": "date"},
            "fecha_inicio": {"type": ["string", "null"], "format": "date"},
            "fecha_caducidad": {"type": ["string", "null"], "format": "date"},
            "anios_pactados": {"type": ["integer", "null"]},
            "prorroga_renunciada": {"type": "boolean"},
            "objeto_consumado": {"type": "boolean"},
            "documento_incompleto": {"type": "boolean"},
            "direccion_objeto": {"type": ["string", "null"]},
            "cita_duracion": {"type": ["string", "null"]},
            "prorroga_tipo": {"enum": ["tacita", "expresa", "renunciada",
                                        "no_consta"]},
            "cita_prorroga_tipo": {"type": ["string", "null"]},
            "preaviso_dias": {"type": ["integer", "null"]},
            # Una cita por campo afirmado. No es documentación: es la condición
            # para que el valor entre. Lo que no se pueda anclar en el texto se
            # descarta, aunque sea correcto.
            "familia": {"enum": ["principal", "modificativo", "accesorio"]},
            "requiere_fecha_caducidad": {"type": "boolean"},
            "duracion_escalonada": {"type": "boolean"},
            "duracion_maxima_anios": {"type": ["integer", "null"]},
            "citas": {"type": "object",
                      "description": "fragmento literal del documento que "
                                     "sostiene cada campo, por nombre de campo"},
        },
    },
    "esquema_salida": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "tipo": {"enum": ["estado", "evento"]},
                "id_documento": {"type": "string"},
                "estado": {"enum": list(ESTADOS)},
                "fecha_emision": {"type": ["string", "null"]},
                "fecha_caducidad": {"type": ["string", "null"]},
                "sustituye_a": {"type": ["string", "null"]},
                "evento": {"type": ["string", "null"]},
                "fecha_evento": {"type": ["string", "null"]},
                "preaviso_dias": {"type": ["integer", "null"]},
                "cita": {"type": ["string", "null"]},
            },
            "required": ["id_documento"],
        },
    },
}

FICHA["prompt_extraccion"] = (
    "Eres un extractor de campos, no un clasificador. Lee el documento jurídico y "
    "devuelve únicamente el objeto JSON que pide el esquema.\n"
    "Reglas:\n"
    "· No deduzcas el estado de vigencia. Sólo extraes fechas y hechos.\n"
    "· `fecha_caducidad` es la fecha en que el documento deja de producir efectos "
    "según sus propias cláusulas. Si el documento no la fija, devuelve null: no la "
    "calcules ni la supongas.\n"
    "· `objeto_consumado` es verdadero sólo si el documento declara su objeto "
    "agotado y sin obligaciones ni plazos pendientes.\n"
    "· `direccion_objeto` es la dirección del inmueble sobre el que versa.\n"
    "· `cita_duracion` es el fragmento literal que sostiene la duración. Literal: "
    "si no puedes copiarlo, devuelve null.\n"
    "· `citas` lleva, por cada campo que rellenes con un hecho del documento, el "
    "fragmento literal que lo sostiene, copiado del texto que te doy. No lo "
    "parafrasees ni lo corrijas más allá de erratas evidentes del "
    "reconocimiento: ese fragmento se busca después en el documento y, si no "
    "aparece, el campo se descarta aunque el valor fuese correcto. Un campo sin "
    "cita es un campo perdido, así que no rellenes lo que no puedas citar.\n"
    "· `anios_pactados` sale de la cláusula de DURACIÓN del documento, no de "
    "cualquier plazo que aparezca. Un contrato puede fijar plazos para otras "
    "cosas —edificar, avisar, pagar— y ésos no son la duración.\n"
    "· `prorroga_tipo`: «tacita» si el documento se renueva solo salvo denuncia; "
    "«expresa» si hace falta acuerdo de las partes para prorrogarlo; "
    "«renunciada» si renuncia a la tácita reconducción; «no_consta» si la "
    "cláusula no es concluyente. No elijas por defecto: «no_consta» es una "
    "respuesta correcta y frecuente.\n"
    "· `familia`: «principal» si el documento fija su propia vigencia (un "
    "contrato, una escritura); «modificativo» si modifica a otro anterior (un "
    "anexo, una adenda, una prórroga, una subrogación, un rescate); «accesorio» "
    "si documenta un acto sin vigencia propia. Míralo en el ENCABEZAMIENTO: un "
    "contrato que lleva anexos cosidos detrás sigue siendo un contrato.\n"
    "· `requiere_fecha_caducidad`: **la pregunta más importante de todas cuando "
    "el documento no fija vencimiento.** Verdadero si este documento *debería* "
    "tener uno —crea o modifica una relación que dura en el tiempo, o deja "
    "obligaciones que viven mientras viva el contrato al que acompaña: una "
    "subrogación, una aportación que se amortiza durante el plazo, una cesión—. "
    "Falso si no tiene por qué tenerlo porque su objeto se agota al otorgarse: un "
    "anexo que cambia el día de facturación, un acta de entrega, un recibo. En "
    "los dos casos falta la fecha; lo que cambia es si se la echa de menos.\n"
    "· `duracion_escalonada` y `duracion_maxima_anios`: verdadero cuando el plazo "
    "no es uno solo sino una escalera de prórrogas —«un año, prorrogable por "
    "periodos anuales hasta diez, y después cinco más hasta un máximo de "
    "quince»—. En ese caso `anios_pactados` es el **primer** periodo y "
    "`duracion_maxima_anios` el tope. Es una forma de duración que no se reduce a "
    "inicio más plazo, y tratarla como si lo fuera da por caducado un contrato "
    "que sigue vivo.\n"
    "\n"
    "El texto puede venir de un OCR de un documento mecanografiado antiguo y "
    "tener erratas de reconocimiento («cuatroúe abril» por «cuatro de abril»). "
    "Corrige la errata sólo cuando el texto vecino la haga inequívoca; si el dato "
    "está perdido, devuelve null. Inventar una fecha plausible es el peor "
    "resultado posible: este sistema existe para detectar exactamente eso."
)

FICHA["prompt_interpretacion"] = (
    "Convierte la salida del módulo de vigencia documental en la lista JSON del "
    "esquema. Separa los registros de estado —una ficha por documento— de los "
    "eventos de vencimiento o preaviso. No juzgues si el estado es correcto: sólo "
    "traduces lo que el módulo dice. Si el módulo no declara un dato, devuelve "
    "null; no lo infieras del documento."
)

COLUMNAS = [
    ("id_documento", "Documento", "texto", None),
    ("estado", "Estado declarado", "opcion", list(ESTADOS.values())),
    ("fecha_caducidad", "Fecha de vencimiento citada", "texto", None),
    ("sustituye_a", "Versión que sustituye", "texto", None),
    ("cita", "Cita la cláusula", "bool", None),
]


# ===========================================================================
# 1. Clasificación del documento
# ===========================================================================

def clasificar(texto, cabecera=1400):
    """
    De qué trata el documento. Eje distinto del de `familia_de`, que dice qué
    papel juega: un anexo (familia) puede ser de un arrendamiento (tipo).

    **Se lee del encabezamiento y de lo más específico a lo más general**, y
    ninguna de las dos cosas es un detalle. Sobre los trece documentos reales la
    versión anterior llamaba «contrato de arrendamiento» a once —incluidas dos
    aportaciones económicas y una subrogación— porque preguntaba por la palabra
    «arrendamiento» en el documento entero, y todos la mencionan: son anexos DE
    un arrendamiento. Una etiqueta que acierta el 85 % de las veces por decir
    siempre lo mismo no clasifica nada, sólo lo parece.
    """
    completo = plano(texto)
    if not completo.strip():
        return "sin_texto"
    cab = plano((texto or "")[:cabecera])

    # Lo específico primero, y en la cabecera: es donde el documento se nombra.
    for clave, marcas in (
            ("superficie", ("derecho de superficie", "facultas aedificandi")),
            ("aportacion", ("aportacion economica", "aportacion de repsol",
                            "aportara la cantidad", "reforma integral")),
            ("subrogacion", ("subrogacion", "addendum")),
            ("requerimiento", ("requerimiento",)),
            ("arrendamiento", ("contrato de arrendamiento", "arrendamiento de "
                               "industria", "cesion de uso", "alquiler"))):
        if any(m in cab for m in marcas):
            return clave

    # Fuera de la cabecera sólo se acepta lo inequívoco.
    if "derecho de superficie" in completo:
        return "superficie"
    if "arrendamiento" in completo:
        return "arrendamiento"
    return "otro"


TIPOS = {"arrendamiento": "Contrato de arrendamiento",
         "superficie": "Derecho de superficie",
         "subrogacion": "Subrogación o addendum",
         "aportacion": "Documento de aportación económica",
         "requerimiento": "Requerimiento administrativo",
         "otro": "Otro documento", "sin_texto": "Sin capa de texto"}


# ===========================================================================
# 2. Extracción determinista de campos
# ===========================================================================

# «En Zaragoza, a cuatro de abril de…». El ancla de principio de línea se cayó
# con el primer escaneo real: el OCR deja basura delante («o En Zaragoza, a…»),
# así que se ancla a la palabra y no al margen.
P_EMISION = r"\bEn\s+[A-ZÁÉÍÓÚ][a-záéíóúñ]{2,20}(?:\s+[a-záéíóúñ]{2,20})?,\s*a\b"
# Las tres formas de fijar cuándo empieza a contar el plazo, y las cuatro de
# fijar cuándo termina, escritas por FORMA VERBAL y no por frase.
#
# La versión anterior enumeraba frases literales —«finalizando, en consecuencia,
# el»— y sobre trece documentos reales acertó una. No porque las frases fueran
# pocas, sino porque estaban congeladas: «finaliza el» no reconocía «finalizará
# el», y una coma de más o de menos rompía la coincidencia. Enumerar frases es
# perseguir documentos; enumerar la raíz del verbo y dejar libre la terminación
# cubre las conjugaciones que aún no he visto, que son las que importan.
P_INICIO = (r"(?:fecha\s+de\s+inicio[^.\n]{0,30}?ser[áa]|"
            r"comenzar[áa]?\s+a\s+(?:contarse|surtir\s+efectos?)|"
            r"comenzando\s+a\s+contarse|comenzando|"
            r"(?:a\s+)?contar(?:se)?\s+desde|"
            r"con\s+(?:inicio|efectos?)|"
            r"entrar[áa]?\s+en\s+vigor|surtir[áa]?\s+efectos?|"
            r"\binicio\b|desde\s+el\s+d[íi]a)"
            r"(?:\s+(?:el|desde|a\s+partir\s+de|d[íi]a|,))*")
P_FIN = (r"(?:finaliz(?:a|ar[áa]|ando|aci[óo]n)|termin(?:a|ar[áa]|ando|aci[óo]n)|"
         r"siendo\s+su\s+t[ée]rmino|\bt[ée]rmino\b|"
         r"expir(?:a|ar[áa]|aci[óo]n)|caduc(?:a|ar[áa]|idad)|"
         r"venc(?:e|er[áa]|imiento)|extingu(?:e|ir[áa])|"
         r"v[áa]lido\s+hasta|hasta)"
         # El conector es obligatorio, y no es un detalle de sintaxis.
         #
         # Sin él, «la obra finalizada con fecha 5 de febrero de 2020» pasaba por
         # una fecha de vencimiento del contrato. Es el error que más miedo da de
         # los tres tipos que hay: no es no leer, es leer un dato correcto de la
         # cláusula equivocada, y sale con la misma cara de verificado que uno
         # bueno. Lo que termina «el 31 de octubre» es un plazo; lo que termina
         # «con fecha 5 de febrero» es una obra.
         r"(?:\s*,?\s*en\s+consecuencia\s*,?)?\s*(?:el|hasta)\s+(?:d[íi]a\s+)?")

P_RENUNCIA = (r"renuncia\s+(expresa\s+)?a\s+la\s+t[áa]cita\s+reconducci[óo]n|"
              r"sin\s+pr[óo]rroga\s+t[áa]cita|no\s+pr[óo]rroga\s+autom[áa]tica|"
              r"sin\s+pr[óo]rroga\s+autom[áa]tica|NO\s+pr[óo]rroga")
P_CONSUMADO = (r"agotad[oa]\s+el\s+objeto|sin\s+obligaciones\s+(econ[óo]micas\s+)?"
               r"ni\s+plazos\s+pendientes|[íi]ntegramente\s+abonad[ao]")
# Un documento «sin cumplimentar» es una PLANTILLA: tiene huecos donde deberían
# ir los datos. Se reconoce por los subrayados y los puntos suspensivos que se
# dejan para rellenar a mano.
#
# El patrón tenía además `\.{6,}` —seis puntos seguidos— y sobre el corpus real
# eso marcaba como plantillas dos documentos perfectamente cumplimentados: los
# puntos de relleno de una tabla, «Nombre..........: SERVIARAGÓN, S.A.». Es un
# resto de los contratos sintéticos, donde los huecos eran literales y las tablas
# no existían; en un escaneo de verdad, un renglón de puntos es maquetación.
#
# Y se exige **más de uno**: una plantilla tiene huecos por todas partes, no uno
# suelto. Un solo hueco en un documento firmado es una errata, no una plantilla.
P_INCOMPLETO = r"_{3,}|…{3,}"
MINIMO_HUECOS = 2

# Preaviso de no renovación: es lo que dispara el evento que IAlert llama
# «Fecha límite para avisar de no renovación».
P_PREAVISO = r"preaviso[^.]{0,60}?(\d{1,3})\s*d[íi]as|(\d{1,3})\s*d[íi]as\s+de\s+antelaci[óo]n"

# --- Naturaleza de la prórroga -------------------------------------------
#
# Tres situaciones que la salida del módulo colapsa en una casilla de sí/no, y
# que aguas abajo significan cosas opuestas:
#
#   · TÁCITA     — se renueva sola salvo que alguien avise. Hay que avisar.
#   · EXPRESA    — se extingue salvo que las partes acuerden prorrogarla.
#                  No hacer nada es dejarla morir.
#   · RENUNCIADA — se descarta la reconducción explícitamente.
#
# El discriminante es el verbo, no la palabra «prórroga»: «se prorrogará
# automáticamente» frente a «las partes podrán convenir… mediante acuerdo
# expreso». Los dos textos contienen «prórroga».
P_PRORROGA_TACITA = (r"se\s+prorrogar[áa]\s+(autom[áa]ticamente|t[áa]citamente)|"
                     r"pr[óo]rroga\s+(autom[áa]tica|t[áa]cita)|"
                     r"t[áa]cita\s+reconducci[óo]n|"
                     r"se\s+entender[áa]\s+prorrogado")
P_PRORROGA_EXPRESA = (r"podr[áa]n\s+convenir[^.]{0,120}?pr[óo]rroga|"
                      r"pr[óo]rroga[^.]{0,120}?(acuerdo\s+expreso|mutuo\s+acuerdo|"
                      r"acuerdo\s+de\s+ambas\s+partes|convenio\s+expreso)|"
                      r"(acuerdo\s+expreso|mutuo\s+acuerdo)[^.]{0,120}?pr[óo]rroga")

PRORROGAS = {"tacita": "Tácita (se renueva sola)",
             "expresa": "Expresa (requiere acuerdo)",
             "renunciada": "Renunciada expresamente",
             "no_consta": "No consta"}

# La antelación con la que hay que moverse antes del vencimiento. Puede venir en
# días, meses o años, y en cifra o en letra. `duracion_dias` lo reduce a las tres
# cosas que hacen falta: cuánto, de qué, y su equivalencia en días.
P_ANTELACION = (r"(?:con\s+una?\s+)?antelaci[óo]n\s+de\s+([^,.;]{1,40})|"
                r"preaviso\s+de\s+(?:al\s+menos\s+)?([^,.;]{1,40})")


def _cita(texto, patron, largo=160):
    m = re.search(patron, texto, re.IGNORECASE)
    if not m:
        return None
    ini = max(0, m.start() - 40)
    return re.sub(r"\s+", " ", texto[ini: m.end() + largo]).strip()


VIAS = (r"(?:calle|c/|avenida|avda|plaza|paseo|ronda|camino|carretera|ctra|"
        r"cr|autov[íi]a|via)")

# Las direcciones de carretera —«CR A-2, 280,1 (CALATORAO)»— no tienen vía con
# nombre ni número de portal: tienen identificador de carretera y punto
# kilométrico, y la población entre paréntesis. El patrón general no las coge, y
# son la mitad del corpus real de Martín: sus documentos son estaciones de
# servicio, no locales de calle.
P_CARRETERA = (r"\b(cr|ctra|carretera|autov[íi]a)[\s.\-]*"
               r"([a-z]{0,2}-?\s?\d{1,3})\s*,?\s*"
               r"(\d{1,4}(?:[.,]\d)?)\s*"
               r"(?:\(\s*([a-záéíóúñ\s]{3,30}?)\s*\)|([a-záéíóúñ]{3,30}))")


def cadena_documental(texto):
    """
    La huella del inmueble sobre el que versa el documento: vía, número y ciudad,
    normalizados. Es lo mismo que IAlert llama «cadena documental», y es lo que
    permite saber que dos documentos son dos versiones de la misma relación.
    """
    # Los saltos de línea del PDF parten la dirección por la mitad —«Calle del\nCoso»—
    # y `.` no los cruza. Se aplana el texto antes de buscar.
    llano = re.sub(r"\s+", " ", texto or "")
    m = re.search(r"(?:sit[oa]\s+en|situad[oa]\s+en|OBJETO\.?\s*(?:Local[^,]{0,40})?\s*"
                  r"(?:sit[oa]\s+)?en|finca\s+sita\s+en)\s+(.{0,140})",
                  llano, re.IGNORECASE)
    if not m:
        return None
    frag = plano(m.group(1))

    # Carretera y punto kilométrico primero: es una forma distinta de dirección,
    # no un caso particular de la de calle.
    mc2 = re.search(P_CARRETERA, frag)
    if mc2:
        poblacion = (mc2.group(4) or mc2.group(5) or "").strip()
        # El identificador de la carretera se escribe de tres maneras en el mismo
        # expediente —«CR A-2», «CR-A2», «CR A2»— y la cadena documental sirve
        # para saber que dos documentos hablan del mismo inmueble. Si «a-2» y
        # «a2» no son la misma huella, el contrato y su anexo caen en cadenas
        # distintas y la relación de versionado no se detecta jamás. Se quitan
        # los separadores de dentro del identificador; el punto kilométrico
        # también, que aparece como «280,1» y como «280.1».
        carretera = re.sub(r"[\s\-.]", "", f"{mc2.group(1)}{mc2.group(2)}")
        pk = re.sub(r"[.,]", ",", mc2.group(3))
        return re.sub(r"\s+", " ", f"{carretera} pk {pk} {poblacion}").strip()

    ciudad = None
    mc = re.match(r"([a-z\s]{3,25}?)\s*,", frag)
    if mc:
        ciudad = mc.group(1).strip()

    mv = re.search(rf"{VIAS}\b[\s.]*([a-z0-9\-\s]{{2,40}}?)(?=\s*,|\s+n[uú]?m?[ºo°.]|$)",
                   frag)
    via = None
    if mv:
        via = re.sub(r"\s+", " ", (re.search(VIAS, frag).group(0) + " "
                                   + mv.group(1)).strip())

    mn = re.search(r"n[uú]?m?[ºo°.]{0,2}\s*(\d{1,4})|p\.?k\.?\s*(\d{1,4})", frag)
    num = (mn.group(1) or mn.group(2)) if mn else None

    partes = [p for p in (via, f"num {num}" if num else None, ciudad) if p]
    return " ".join(partes) if via else None


# ===========================================================================
# 1 bis. Familia documental: qué se le puede exigir a cada documento
# ===========================================================================
# El cambio de fondo que trajo el corpus real de RALSA, y el que no se arregla
# con ningún patrón.
#
# La batería estaba escrita como si todo documento fijara su propia vigencia. De
# los trece documentos reales, **seis no la fijan**: dos anexos, una prórroga,
# una subrogación y dos aportaciones económicas a obras. Exigirles una fecha de
# vencimiento y anotar «vigencia no determinada» cuando no aparece no es
# evaluarlos: es hacerles una pregunta que no les corresponde, y produce un
# suspenso que no significa nada.
#
# Tres familias, y cada una admite una pregunta distinta:
#
#   · PRINCIPAL    — fija su propia vigencia (contrato, escritura de derecho de
#                    superficie). Se le exige plazo y vencimiento.
#   · MODIFICATIVO — modifica a otro (anexo, prórroga, renovación, subrogación,
#                    novación, rescate). Su vigencia **es la del documento que
#                    modifica**, así que no se le puede exigir sola: se declara
#                    qué documento haría falta. Eso es un requisito de datos, no
#                    un fallo del módulo.
#   · ACCESORIO    — no tiene vigencia que determinar (aportación económica,
#                    acta, factura, requerimiento cumplido). El caso no aplica.
#
# La familia se deduce del texto, no del nombre del fichero. Un fichero llamado
# «ANEXO.pdf» que contenga un contrato completo es un contrato; y al revés.
# Clasificar por el nombre sería creerse la etiqueta en vez de leer el documento,
# que es justo lo que este sistema le reprocha a los módulos que evalúa.

FAMILIAS = {
    "principal": "Fija su propia vigencia",
    "modificativo": "Modifica a otro documento",
    "accesorio": "Sin vigencia propia que determinar",
}

# Un documento modificativo se anuncia con un ACTO ejercido SOBRE OTRO
# INSTRUMENTO: «addendum al contrato», «prórroga de contrato de arrendamiento»,
# «rescate de derecho de superficie». No es una lista de palabras sueltas —
# «subrogación» a secas es una cláusula corriente dentro de un contrato — sino
# una construcción: acto + preposición + documento. Eso es lo que generaliza a
# los actos que todavía no he visto.
ACTO_SOBRE_OTRO = (r"addend(?:um|a)|adenda|anexo|pr[óo]rroga|renovaci[óo]n|"
                   r"subrogaci[óo]n|novaci[óo]n|rescate|resoluci[óo]n|cesi[óo]n|"
                   r"modificaci[óo]n|ampliaci[óo]n")
DOCUMENTO_ALUDIDO = (r"contrato|escritura|arrendamiento|derecho|p[óo]liza|"
                     r"convenio|acuerdo")
P_MODIFICATIVO = (rf"\b(?:{ACTO_SOBRE_OTRO})\s+(?:de|del|al|a\s+la)\s+"
                  rf"(?:[a-záéíóúñ]+\s+){{0,2}}(?:{DOCUMENTO_ALUDIDO})|"

                  r"no\s+obstante\s+lo\s+(?:establecido|dispuesto)\s+en\s+la\s+"
                  r"cl[áa]usula")
# Autodescripción: sólo se llama así a sí mismo el documento que lo es.
#
# El juego de actos es más corto que el del título, y no por prudencia genérica:
# «resolución» y «cesión» son sustantivos corrientes dentro de un contrato —«la
# presente Resolución cabe recurso de alzada», en un anejo administrativo de la
# escritura de derecho de superficie— y con ellos dentro, una escritura principal
# se clasificaba como modificativa por una frase de la última página. Los actos
# que quedan sólo aparecen cuando el documento se está nombrando a sí mismo.
ACTO_AUTODESCRITO = (r"addend(?:um|a)|adenda|anexo|pr[óo]rroga|renovaci[óo]n|"
                     r"novaci[óo]n|subrogaci[óo]n")
P_AUTODESCRIPCION = (rf"\b(?:el|la)\s+presente\s+(?:{ACTO_AUTODESCRITO})\b|"
                     rf"\botorgar\s+(?:el|la)\s+presente\s+(?:{ACTO_AUTODESCRITO})\b")

# Obligaciones que sólo tienen sentido mientras el contrato viva. Si el documento
# las contiene, su vigencia está atada a un plazo aunque él no escriba ninguno.
def a_int(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


# La escalera de prórrogas y su tope.
P_ESCALONADA = (r"prorrog[áa]ndose\s+por\s+(?:plazos|periodos|per[íi]odos)\s+"
                r"(?:anuales\s+)?sucesivos|"
                r"por\s+(?:plazos|periodos|per[íi]odos)\s+sucesivos|"
                r"volverse\s+a\s+prorrogar|"
                r"prórrogas\s+sucesivas\s+hasta")
P_TOPE = (r"(?:duraci[óo]n\s+m[áa]xima|m[áa]ximo|hasta\s+(?:que\s+)?alcance"
          r"(?:\s+una\s+duraci[óo]n)?)\s+(?:de\s+)?"
          r"([A-Za-zÁÉÍÓÚáéíóúñ]+|\d{1,2})\s*(?:\(\d+\))?\s*a[ñn]os")

P_ATA_AL_PLAZO = (r"una\s+vez\s+extinguid[oa]\s+el\s+contrato|"
                  r"durante\s+(?:toda\s+)?la\s+vigencia|"
                  r"hasta\s+(?:la\s+)?(?:finalizaci[óo]n|extinci[óo]n|"
                  r"terminaci[óo]n)\s+del\s+contrato|"
                  r"con\s+anterioridad\s+al\s+plazo\s+de\s+duraci[óo]n|"
                  r"resoluci[óo]n\s+anticipada|"
                  r"se\s+subroga|subrogaci[óo]n\s+en|"
                  r"prorrata|pro\s+rata\s+temporis|"
                  r"amortizaci[óo]n\s+(?:pendiente|del\s+saldo)")

P_ACCESORIO = (r"aportaci[óo]n\s+econ[óo]mica|aportar[áa]\s+la\s+cantidad|"
               r"comprende\s+las\s+siguientes\s+mejoras|"
               r"reforma\s+integral|acta\s+de\s+(?:entrega|recepci[óo]n)|"
               r"factura\s+n[úu]m|requerimiento\s+administrativo")


# Cuánto texto mira `familia_de`. Un documento jurídico declara qué es en su
# encabezamiento, y de ahí no se mueve.
CABECERA = 1400


def familia_de(texto, cabecera=CABECERA):
    """
    (familia, cita). La cita es el fragmento que la sostiene: una clasificación
    que cambia lo que se le exige a un documento no puede ser una corazonada.

    **Sólo mira el encabezamiento**, y ésa es la parte que costó entender. Con el
    documento entero, el contrato de arrendamiento de Calatorao salía clasificado
    como anexo —porque lleva cinco anexos cosidos detrás— y el de 1997 también,
    porque su cláusula duodécima se titula «SUBROGACIÓN». Los dos son contratos
    completos que *contienen* esas cosas, no documentos que *son* esas cosas.
    Un documento jurídico dice en su primera página qué es; lo que venga después
    son sus partes, no su naturaleza.
    """
    cab = (texto or "")[:cabecera]
    if re.search(P_MODIFICATIVO, cab, re.IGNORECASE):
        return "modificativo", _cita(cab, P_MODIFICATIVO)
    if re.search(P_ACCESORIO, cab, re.IGNORECASE):
        return "accesorio", _cita(cab, P_ACCESORIO)
    # Fuera del encabezamiento sólo vale la autodescripción —«el presente
    # anexo»—, porque es la única forma en que un documento habla de sí mismo y
    # no de una de sus partes. El de renovación de 2019 abre con la fórmula
    # notarial y no se nombra hasta la segunda página.
    if re.search(P_AUTODESCRIPCION, texto or "", re.IGNORECASE):
        return "modificativo", _cita(texto, P_AUTODESCRIPCION)
    return "principal", None



def extraer(texto):
    """Campos del documento. Ningún estado se decide aquí: sólo se leen hechos."""
    c = {}
    # `fecha_unica` en vez de `buscar_fecha` para el inicio y el fin: si el
    # documento ofrece varias fechas para el mismo campo, no se elige la primera
    # —se declara la ambigüedad y el evaluador se abstiene—. La fecha de firma se
    # queda con la primera a propósito: la fórmula de otorgamiento abre el
    # documento y las posteriores son de los anexos que cita.
    c["fecha_emision"], c["cita_emision"] = buscar_fecha(texto, P_EMISION)
    c["fecha_inicio"], c["cita_inicio"], av_ini = fecha_unica(texto, P_INICIO)
    c["fecha_caducidad"], c["cita_duracion"], av_fin = fecha_unica(texto, P_FIN)
    c["ambiguedades"] = [a for a in (av_ini and f"fecha de inicio: {av_ini}",
                                     av_fin and f"vencimiento: {av_fin}") if a]
    c["anios_pactados"] = anios_de(texto)
    c["prorroga_renunciada"] = bool(re.search(P_RENUNCIA, texto, re.IGNORECASE))
    c["cita_prorroga"] = _cita(texto, P_RENUNCIA)
    c["objeto_consumado"] = bool(re.search(P_CONSUMADO, texto, re.IGNORECASE))
    c["cita_consumado"] = _cita(texto, P_CONSUMADO)
    c["documento_incompleto"] = (
        len(re.findall(P_INCOMPLETO, texto or "")) >= MINIMO_HUECOS)
    c["direccion_objeto"] = cadena_documental(texto)
    m = re.search(P_PREAVISO, texto, re.IGNORECASE)
    c["preaviso_dias"] = int(m.group(1) or m.group(2)) if m else None
    c["familia"], c["cita_familia"] = familia_de(texto)
    # ¿Este documento TIENE QUE tener fecha de caducidad?
    #
    # Es la pregunta que separa los dos estados de la pregunta 8, y la formuló
    # Íñigo con los documentos delante: «título consumado es cuando el documento
    # no tiene que tener fecha de caducidad; no clasificado es cuando sí tiene
    # que tenerla». En los dos casos falta la fecha — lo que cambia es si se la
    # echa de menos.
    #
    # Un anexo que cambia la facturación se agota al firmarse: nadie espera que
    # caduque. Uno que subroga a una parte, o que financia unas obras cuyo coste
    # se devuelve «una vez extinguido el contrato», crea una obligación que vive
    # mientras viva el contrato: ahí la ausencia de fecha es un hueco, no una
    # propiedad.
    #
    # La regla lo aproxima buscando obligaciones atadas al plazo. Es una
    # aproximación honesta y se declara como tal: el modelo la lee mejor, y el
    # caso 8 arrastra la cita que la sostiene.
    # Duración en escalera: «UN AÑO, prorrogándose por plazos anuales sucesivos
    # hasta alcanzar DIEZ AÑOS, para volverse a prorrogar por CINCO AÑOS hasta un
    # máximo de QUINCE». El plazo pactado es el primer periodo, pero el contrato
    # vive hasta el tope. Tratarlo como inicio + plazo da por caducado en 2021 un
    # contrato que sigue vigente en 2026 — que es lo que hacía el evaluador con el
    # contrato de Zurita antes de que Íñigo lo etiquetara a mano.
    c["duracion_escalonada"] = bool(re.search(P_ESCALONADA, texto, re.IGNORECASE))
    c["duracion_maxima_anios"] = None
    if c["duracion_escalonada"]:
        topes = [n for n in (numero_en_letra(m.group(1)) or a_int(m.group(1))
                             for m in re.finditer(P_TOPE, texto, re.IGNORECASE))
                 if n and 1 <= n <= 99]
        c["duracion_maxima_anios"] = max(topes) if topes else None
    c["cita_escalonada"] = _cita(texto, P_ESCALONADA)

    c["ata_al_plazo"] = bool(re.search(P_ATA_AL_PLAZO, texto, re.IGNORECASE))
    c["cita_ata_al_plazo"] = _cita(texto, P_ATA_AL_PLAZO)
    c["requiere_fecha_caducidad"] = (
        not c["objeto_consumado"]
        and (c["familia"] == "principal" or c["ata_al_plazo"]))

    # --- Vencimiento derivado del plazo --------------------------------
    # Muchos contratos no escriben la fecha final: escriben el inicio y el plazo.
    # Derivarla es aritmética, no interpretación, y se marca como derivada para
    # que el veredicto pueda decir de dónde salió.
    c["caducidad_derivada"] = False
    if c["fecha_caducidad"] is None and c["fecha_inicio"] and c["anios_pactados"]:
        c["fecha_caducidad"] = sumar_anios(c["fecha_inicio"], c["anios_pactados"])
        c["caducidad_derivada"] = True
        c["cita_duracion"] = c["cita_duracion"] or _cita(
            texto, r"plazo\s+(?:inicial\s+)?de\s+[A-Za-zÁÉÍÓÚáéíóú\d]+\s*a[ñn]os?")

    # --- Naturaleza de la prórroga --------------------------------------
    renunciada = c["prorroga_renunciada"]
    tacita = bool(re.search(P_PRORROGA_TACITA, texto, re.IGNORECASE))
    expresa = bool(re.search(P_PRORROGA_EXPRESA, texto, re.IGNORECASE))
    # La renuncia manda sobre todo lo demás; y si el texto contiene las dos
    # formas, no se elige: se declara que no consta, porque adivinar aquí es
    # exactamente el fallo que este caso mide en el módulo evaluado.
    if renunciada:
        c["prorroga_tipo"] = "renunciada"
    elif expresa and not tacita:
        c["prorroga_tipo"] = "expresa"
    elif tacita and not expresa:
        c["prorroga_tipo"] = "tacita"
    else:
        c["prorroga_tipo"] = "no_consta"
    c["cita_prorroga_tipo"] = (_cita(texto, P_PRORROGA_EXPRESA)
                               if c["prorroga_tipo"] == "expresa" else
                               _cita(texto, P_PRORROGA_TACITA)
                               if c["prorroga_tipo"] == "tacita" else
                               c["cita_prorroga"])

    # --- Antelación y fecha crítica --------------------------------------
    antelaciones = []
    for m in re.finditer(P_ANTELACION, texto, re.IGNORECASE):
        d = duracion_dias(m.group(1) or m.group(2))
        if d:
            antelaciones.append({"cantidad": d[0], "unidad": d[1], "dias": d[2],
                                 "cita": _cita(texto, re.escape(m.group(0)[:40]))})
    # Vale la más próxima al vencimiento: es la que primero obliga a actuar.
    antelaciones.sort(key=lambda x: x["dias"])
    c["antelaciones"] = antelaciones
    c["antelacion"] = antelaciones[0] if antelaciones else None
    c["fecha_critica"] = (restar_duracion(c["fecha_caducidad"],
                                          c["antelacion"]["cantidad"],
                                          c["antelacion"]["unidad"])
                          if c["antelacion"] and c["fecha_caducidad"] else None)
    return c


def _campos_vacios():
    return {"fecha_emision": None, "cita_emision": None, "fecha_inicio": None,
            "cita_inicio": None, "fecha_caducidad": None, "cita_duracion": None,
            "anios_pactados": None, "prorroga_renunciada": False,
            "cita_prorroga": None, "objeto_consumado": False,
            "cita_consumado": None, "documento_incompleto": False,
            "direccion_objeto": None, "preaviso_dias": None,
            "requiere_fecha_caducidad": True, "caducidad_derivada": False,
            "ambiguedades": [], "familia": "principal", "cita_familia": None,
            "ata_al_plazo": False, "cita_ata_al_plazo": None,
            "duracion_escalonada": False, "duracion_maxima_anios": None,
            "cita_escalonada": None,
            "prorroga_tipo": "no_consta", "cita_prorroga_tipo": None,
            "antelaciones": [], "antelacion": None, "fecha_critica": None}


# ===========================================================================
# 3. Verdad de campo
# ===========================================================================

# Lo único que se le pide al modelo: hechos que están escritos en el documento.
# Ni el estado, ni nada derivado — la fecha de vencimiento que sale de sumar el
# plazo al inicio la calcula la regla, siempre, aunque los dos sumandos los haya
# leído el modelo. Es la frontera entre leer y decidir, y es la que sostiene que
# esto siga siendo una evaluación y no una segunda opinión.
CAMPOS_DEL_MODELO = ["fecha_emision", "fecha_inicio", "fecha_caducidad",
                     "anios_pactados", "direccion_objeto", "cita_duracion",
                     "prorroga_tipo", "cita_prorroga_tipo", "preaviso_dias",
                     "familia", "requiere_fecha_caducidad",
                     "duracion_escalonada", "duracion_maxima_anios"]


# Campos a los que se les exige cita: los que afirman un hecho escrito. A
# `prorroga_tipo` también, porque es una lectura de la cláusula y no una
# clasificación libre.
CAMPOS_CON_CITA = ["fecha_emision", "fecha_inicio", "fecha_caducidad",
                   "anios_pactados", "prorroga_tipo", "preaviso_dias",
                   "requiere_fecha_caducidad", "duracion_maxima_anios"]


def descartar_incoherentes(campos, procedencia):
    """
    Comprobaciones de aritmética sobre lo que el modelo ha aportado.

    No usan modelo, no cuestan nada y cazan justo el error que más daño hace: la
    fecha verosímil pero falsa. Son tres, y las tres son del documento consigo
    mismo, no contra ninguna fuente externa:

      · La firma no puede ser posterior al inicio.
      · El inicio no puede ser posterior al vencimiento.
      · Si están el inicio, el plazo y el vencimiento, tienen que cuadrar.

    Cuando algo no cuadra se descarta **el valor que puso el modelo**, no el que
    puso la regla: entre una lectura reproducible y una que no lo es, la duda
    beneficia a la reproducible. Si los dos vienen del modelo, se caen los dos —
    no hay forma de saber cuál miente.
    """
    campos, procedencia = dict(campos), dict(procedencia)
    incoh = {}

    def _cae(campos_en_conflicto, motivo):
        delmodelo = [c for c in campos_en_conflicto
                     if str(procedencia.get(c, "")).startswith("modelo")]
        for c in (delmodelo or []):
            campos[c] = None
            procedencia[c] = f"modelo (descartado: {motivo[:60]})"
            incoh[c] = motivo

    f, i, v = (campos.get("fecha_emision"), campos.get("fecha_inicio"),
               campos.get("fecha_caducidad"))
    if f and i and f > i:
        _cae(["fecha_emision", "fecha_inicio"],
             f"la firma ({f:%d/%m/%Y}) sería posterior al inicio ({i:%d/%m/%Y})")
    if i and v and i > v:
        _cae(["fecha_inicio", "fecha_caducidad"],
             f"el inicio ({i:%d/%m/%Y}) sería posterior al vencimiento "
             f"({v:%d/%m/%Y})")
    n = campos.get("anios_pactados")
    if i and v and n and sumar_anios(i, n) != v:
        _cae(["fecha_inicio", "fecha_caducidad", "anios_pactados"],
             f"inicio {i:%d/%m/%Y} más {n} años daría "
             f"{sumar_anios(i, n):%d/%m/%Y}, no {v:%d/%m/%Y}")
    return campos, procedencia, incoh


def _rederivar(campos, previo, texto):
    """
    Rehace lo derivado después de que el modelo haya rellenado huecos.

    Si el modelo aporta el inicio y el plazo, el vencimiento tiene que salir de
    sumarlos —marcado como derivado— y la fecha crítica de restarle la antelación.
    Sin esto, un documento rescatado por el modelo se quedaría con los derivados
    a nulo y el evaluador seguiría abstiéndose sobre un documento que ya sabe
    leer.
    """
    campos = dict(campos)
    campos.setdefault("caducidad_derivada", False)
    if campos.get("prorroga_tipo") in (None, ""):
        campos["prorroga_tipo"] = "no_consta"

    if campos.get("fecha_caducidad") is None and campos.get("fecha_inicio") \
            and campos.get("anios_pactados"):
        campos["fecha_caducidad"] = sumar_anios(campos["fecha_inicio"],
                                                campos["anios_pactados"])
        campos["caducidad_derivada"] = True

    if not campos.get("antelacion") and campos.get("preaviso_dias"):
        campos["antelacion"] = {"cantidad": campos["preaviso_dias"],
                                "unidad": "dias", "dias": campos["preaviso_dias"],
                                "cita": campos.get("cita_prorroga_tipo")}
    ant = campos.get("antelacion")
    campos["fecha_critica"] = (restar_duracion(campos.get("fecha_caducidad"),
                                               ant["cantidad"], ant["unidad"])
                               if ant and campos.get("fecha_caducidad") else None)
    for clave in ("antelaciones", "documento_incompleto", "objeto_consumado",
                  "prorroga_renunciada", "requiere_fecha_caducidad"):
        campos.setdefault(clave, previo.get(clave))
    return campos


def _asegurar_fechas(campos):
    """
    Cinturón, además del tirante.

    La conversión de tipos se hace en la frontera —`llm.conformar()`—, que es su
    sitio. Esto sólo garantiza que un valor con el tipo equivocado no tumbe la
    aplicación entera en mitad de una demo: si llega aquí una cadena donde debería
    haber un `date`, algo falló antes, pero el fallo se contiene en vez de
    propagarse hasta un `TypeError` a diez llamadas de distancia.
    """
    campos = dict(campos)
    for clave in ("fecha_caducidad", "fecha_emision", "fecha_inicio"):
        valor = campos.get(clave)
        if valor is not None and not isinstance(valor, date):
            campos[clave] = fecha_de(valor)
    return campos


def estado_esperado(campos, fecha_evaluacion):
    """
    Regla de decisión, en este orden. El orden es la regla: cambiarlo cambia el
    resultado, así que queda escrito y no repartido por el código. La sustitución
    dentro de una cadena documental se aplica después, en `_aplicar_cadenas()`.
    """
    campos = _asegurar_fechas(campos)

    if campos["documento_incompleto"] and campos["fecha_caducidad"] is None \
            and campos["fecha_emision"] is None:
        return ("no_clasificado",
                "El documento está sin cumplimentar: no hay fecha de firma ni plazo "
                "que permitan situarlo en el tiempo.")

    # El orden importa y por eso está junto: lo que el documento **afirma** de sí
    # mismo manda sobre lo que su familia permite preguntarle. Una aportación
    # económica que declara su objeto agotado es un título consumado, no un
    # documento «sin vigencia que determinar»: la primera lectura dice que se
    # cumplió, la segunda sólo que no había plazo. Invertir el orden hacía
    # desaparecer la corrección de Fabián sobre la pregunta 8.
    if campos["objeto_consumado"]:
        return ("titulo_consumado",
                "El documento declara su objeto agotado y sin plazos pendientes, "
                "luego no tiene vencimiento que comprobar.")

    # Familia antes que nada: determina qué pregunta admite el documento.
    familia = campos.get("familia", "principal")
    # Duración en escalera: el vencimiento del primer periodo no es el final del
    # contrato. Mientras no se sepa el tope, declarar «caducado» sería afirmar el
    # final de algo que sigue prorrogándose solo — y ése es el fallo más caro de
    # este módulo, porque nadie vuelve a mirar un documento dado por muerto.
    if campos.get("duracion_escalonada"):
        tope = campos.get("duracion_maxima_anios")
        base = campos.get("fecha_inicio") or campos.get("fecha_emision")
        final = sumar_anios(base, tope) if base and tope else None
        if final and fecha_evaluacion > final:
            return ("caducado",
                    f"El contrato se prorroga en escalones hasta un máximo de "
                    f"{tope} años, que se cumplieron el "
                    f"{final.strftime('%d/%m/%Y')}.")
        if final:
            return ("vigente",
                    f"Se prorroga en escalones hasta un máximo de {tope} años, "
                    f"es decir hasta el {final.strftime('%d/%m/%Y')}.")
        return ("no_clasificado",
                "El contrato se prorroga por periodos sucesivos y no se ha podido "
                "leer hasta qué tope. El vencimiento del primer periodo no es el "
                "final del contrato, así que no puede afirmarse que haya caducado.")

    if familia == "accesorio" and campos["fecha_caducidad"] is None:
        return ("no_aplica_vigencia",
                "El documento no fija vigencia porque no tiene ninguna que fijar: "
                "documenta una aportación o un acto ya cumplido, no una relación "
                "con plazo. Preguntarle cuándo caduca es preguntarle algo que no "
                "le corresponde.")

    if campos["fecha_caducidad"] is None:
        # La pregunta 8, con la corrección de Fabián: falta la fecha en los dos
        # casos, y lo que decide es si se la echa de menos.
        if not campos.get("requiere_fecha_caducidad", True):
            return ("titulo_consumado",
                    "El documento no fija vencimiento y tampoco tiene por qué "
                    "fijarlo: agota su objeto al otorgarse y no deja obligaciones "
                    "atadas a un plazo. No es que falte la fecha — es que no la "
                    "hay que buscar.")
        return ("no_clasificado",
                "No hay fecha de vencimiento determinable, y este documento sí "
                "debería tener una: "
                + ("crea obligaciones que viven mientras viva el contrato. "
                   if campos.get("ata_al_plazo") else "fija una relación con plazo. ")
                + "La ausencia de fecha es un hueco, no una propiedad, y la "
                  "ausencia de plazo no equivale a vigencia indefinida.")

    if familia == "modificativo" and campos["fecha_caducidad"] is None \
            and campos["anios_pactados"] is None:
        # Estado `no_clasificado`, no uno propio. Lo tuvo un rato —
        # `depende_de_otro`— y se retiró: el vocabulario de esta rama es el de la
        # prueba inicial y el de la corrección de Fabián a la pregunta 8, y ahí
        # sólo hay dos salidas cuando falta la fecha. Que el documento dependa de
        # otro es el MOTIVO, no un estado distinto, y viaja en el motivo y en el
        # requisito de datos. Inventar vocabulario propio habría hecho que el
        # evaluador midiera a Martín contra una regla que nadie acordó.
        return ("no_clasificado",
                "El documento modifica a otro —lo dice en su encabezamiento— y no "
                "fija fechas propias, así que su vigencia es la del documento que "
                "modifica. No se puede determinar sin él, y eso no es un defecto "
                "del documento ni del módulo: es que falta la otra mitad.")


    if fecha_evaluacion <= campos["fecha_caducidad"]:
        # Criterio del caso límite, fijado y aplicado igual a todos: el documento
        # sigue vigente el día en que vence, hasta las 23:59.
        return ("vigente",
                f"Vence el {campos['fecha_caducidad'].strftime('%d/%m/%Y')}, "
                f"que no es anterior a la fecha de consulta.")

    # Vencido. Lo que decide si eso es «caducado» o «no se puede afirmar» es la
    # naturaleza de la prórroga, y son tres situaciones, no dos:
    #
    #   · renunciada → caducado. Lo dice el documento.
    #   · expresa    → caducado también, y ésta es la que faltaba. Si prorrogar
    #                  exige acuerdo de las partes, la ausencia de acuerdo no
    #                  prolonga nada: el documento se extinguió al vencer. La
    #                  escritura de derecho de superficie de 1995 es justo eso, y
    #                  la regla anterior la dejaba en «no clasificado» mientras el
    #                  módulo de Martín la daba por obsoleta — con razón.
    #   · tácita o no consta → no se puede afirmar sin comprobar si se prorrogó.
    tipo = campos.get("prorroga_tipo", "no_consta")
    if campos["prorroga_renunciada"] or tipo == "renunciada":
        return ("caducado",
                f"El plazo venció el {campos['fecha_caducidad'].strftime('%d/%m/%Y')} "
                f"y el documento renuncia expresamente a la prórroga tácita.")

    if tipo == "expresa":
        return ("caducado",
                f"El plazo venció el {campos['fecha_caducidad'].strftime('%d/%m/%Y')} "
                f"y la prórroga exige acuerdo expreso de las partes: sin ese "
                f"acuerdo el documento no se prolonga solo.")

    return ("no_clasificado",
            f"El plazo venció el {campos['fecha_caducidad'].strftime('%d/%m/%Y')}, "
            f"pero el documento no renuncia a la tácita reconducción ni exige "
            f"acuerdo expreso para prorrogar: no puede afirmarse que haya dejado "
            f"de producir efectos sin comprobar si se prorrogó.")


def _aplicar_cadenas(esperados):
    """
    Dentro de una cadena documental, el documento cuyo plazo ha terminado y que va
    seguido de otro posterior sobre el mismo inmueble no está simplemente
    caducado: está *sustituido*. Es la distinción que pide la pregunta 5, y la
    razón por la que quedarse con el que no ha caducado no basta como criterio.
    """
    cadenas = {}
    for e in esperados:
        k = e["campos"]["direccion_objeto"]
        if k:
            cadenas.setdefault(k, []).append(e)

    for k, grupo in cadenas.items():
        # Sin fecha no hay orden, y sin orden no hay «sustituido por». Un
        # documento cuya fecha no se ha sabido leer se ordenaba como el más
        # antiguo de todos —`date.min`— y salía declarado obsoleto: el evaluador
        # acusaba al módulo de no haber visto una sustitución que se acababa de
        # inventar él con un dato que no tenía.
        fechados = [e for e in grupo
                    if e["campos"]["fecha_inicio"] or e["campos"]["fecha_emision"]]
        if len(fechados) < 2:
            continue
        grupo = fechados
        def orden(x):
            c = x["campos"]
            return c["fecha_inicio"] or c["fecha_emision"]
        grupo.sort(key=orden)
        ultimo = grupo[-1]
        for e in grupo[:-1]:
            if e["estado"] in ("caducado", "no_clasificado"):
                e["estado"] = "obsoleto"
                e["sustituido_por"] = ultimo["id_documento"]
                e["motivo"] = (f"Sustituido por {ultimo['id_documento']}, posterior "
                               f"sobre el mismo inmueble ({k}). No es sólo que su "
                               f"plazo haya terminado: hay una versión que lo "
                               f"reemplaza.")
    return cadenas


def verdad_de_campo(docs, fecha_evaluacion=None, modo="determinista"):
    fecha_evaluacion = fecha_evaluacion or date.today()
    esperados, procedencias = [], {}
    for d in docs:
        # `legible` en vez de `capa`: desde el 28/08 la lectura puede venir por
        # OCR. Un escaneo ya no es automáticamente ilegible, pero la vía viaja
        # con el registro para que el veredicto la declare.
        legible = d.get("legible", d.get("capa"))
        campos = extraer(d["texto"]) if legible else _campos_vacios()
        if modo != "determinista":
            # Sólo se le pide al modelo lo que tiene sentido que lea de un
            # documento, y sólo donde la regla no ha llegado. `prorroga_tipo`
            # entra como hueco cuando la regla dice «no consta»: no consta es la
            # ausencia de lectura, no un valor leído.
            previo = dict(campos)
            if campos.get("prorroga_tipo") == "no_consta":
                campos["prorroga_tipo"] = None
            campos, proc = llm.resolver(modo, campos, d["texto"],
                                        FICHA["esquema_campos"],
                                        FICHA["prompt_extraccion"],
                                        campos_permitidos=CAMPOS_DEL_MODELO)
            campos = _asegurar_fechas(campos)
            # Nada que aporte el modelo entra sin que su cita esté en el
            # documento, y nada entra si contradice a lo que ya se sabe.
            campos, proc, desc = llm.anclar(campos, proc, campos.get("citas"),
                                            d["texto"], CAMPOS_CON_CITA)
            campos, proc, incoh = descartar_incoherentes(campos, proc)
            campos = _rederivar(campos, previo, d["texto"])
            campos["descartes_modelo"] = {**desc, **incoh}
            procedencias[d["id"]] = proc
        # ¿Se abstiene el evaluador sobre este documento?
        #
        # Distinción que costó un documento entender. Hay dos motivos muy
        # distintos para no poder decir el estado:
        #
        #   · El documento no fija plazo. Es un hecho del documento, y entonces
        #     «vigencia no determinada» es un veredicto: si el módulo lo declara
        #     vigente, se equivoca y hay que decirlo.
        #   · El evaluador no ha sabido leer el plazo. Es un límite MÍO. En una
        #     escritura de 1995 mecanografiada, el OCR devuelve «cuatroúe abril»
        #     y pierde el año entero; ninguna regla saca de ahí una fecha.
        #
        # Tratarlos igual convierte mi ceguera en su fallo. El módulo de Martín
        # clasificó bien la escritura de derecho de superficie y mi lector no
        # supo leerla: acusarle habría sido exactamente lo que este sistema le
        # reprocha a los módulos que evalúa. Cuando el texto viene de un OCR y no
        # sale el plazo, el evaluador **se abstiene**: ese documento no entra en
        # el contraste y sus casos quedan pendientes, declarando qué falta.
        abstiene = False
        if not legible:
            estado, motivo = ("no_clasificado",
                              "El PDF no tiene capa de texto y tampoco ha podido "
                              "reconocerse por OCR: no es que no pueda "
                              "clasificarse, es que no ha podido leerse.")
            abstiene = True
        else:
            estado, motivo = estado_esperado(campos, fecha_evaluacion)
            # Abstenerse es decir «no he sabido leerlo», y eso sólo cabe cuando
            # de verdad no se ha leído la cláusula de duración. Un anexo cuya
            # vigencia es la del contrato que modifica NO es una abstención: el
            # evaluador ha leído bastante para saber qué clase de documento es y
            # está emitiendo un veredicto sobre él. Confundir las dos cosas
            # borraba del contraste media docena de documentos correctamente
            # clasificados, y hacía parecer ciego a un evaluador que veía.
            # No hay vencimiento derivable. Da igual que se haya leído el plazo:
            # sin saber desde cuándo cuenta, el evaluador no puede decir si está
            # vigente. La escritura de derecho de superficie es justo eso —25
            # años leídos, fecha de inicio perdida en el OCR— y sin esta línea el
            # evaluador declaraba «vigencia no determinada» como veredicto y
            # marcaba en falso el «Obsoleto» de Martín, que era correcto.
            sin_vencimiento = campos.get("fecha_caducidad") is None
            if (d.get("via") == "ocr" and estado == "no_clasificado"
                    and not campos.get("objeto_consumado")
                    and campos.get("familia") == "principal"
                    and sin_vencimiento):
                abstiene = True
                falta = [n for n, v in (("la fecha de firma", campos["fecha_emision"]),
                                        ("la fecha de inicio", campos["fecha_inicio"]),
                                        ("el plazo", campos["anios_pactados"]))
                         if not v]
                motivo = ("El evaluador no ha sabido leer "
                          + (", ".join(falta) or "la cláusula de duración")
                          + " en el texto reconocido por OCR, así que no puede "
                            "afirmar qué estado corresponde. No es que el documento "
                            "no lo diga: es que esta lectura no lo ha encontrado.")
        esperados.append({
            "id_documento": _normalizar_id(d["id"]), "nombre": d["nombre"],
            "tipo": clasificar(d["texto"]) if legible else "sin_texto",
            "cadena": campos["direccion_objeto"], "legible": legible,
            "via": d.get("via", "capa_texto" if d.get("capa") else "ninguna"),
            "integridad": d.get("integridad") or {},
            "campos": campos, "estado": estado, "motivo": motivo,
            "abstiene": abstiene, "sustituido_por": None,
            "fecha_caducidad": campos["fecha_caducidad"],
            "fecha_emision": campos["fecha_emision"],
        })
    cadenas = _aplicar_cadenas(esperados)
    return esperados, {"procedencias": procedencias, "cadenas": cadenas}


def vencimientos_en(esperados, fecha_evaluacion, dias=VENTANA_DIAS):
    """Pregunta 2: ni los ya vencidos ni los que vencen más allá del plazo."""
    limite = fecha_evaluacion + timedelta(days=dias)
    return [e for e in esperados if e["fecha_caducidad"]
            and fecha_evaluacion <= e["fecha_caducidad"] <= limite]


def incoherencias_de_fechas(esperados):
    """
    Pregunta 4: emisión posterior a caducidad. Y, de propina, el mismo contraste
    interno que en la auditoría de pedidos: la duración pactada tiene que cuadrar
    con la fecha de finalización que el propio documento declara. Se admite un día
    de holgura porque es habitual cerrar tres años el 31 de diciembre en lugar del
    1 de enero.
    """
    invertidas, descuadres = [], []
    for e in esperados:
        c = e["campos"]
        if c["fecha_emision"] and c["fecha_caducidad"] \
                and c["fecha_emision"] > c["fecha_caducidad"]:
            invertidas.append({"Documento": e["id_documento"],
                               "Emisión": c["fecha_emision"].strftime("%d/%m/%Y"),
                               "Caducidad": c["fecha_caducidad"].strftime("%d/%m/%Y")})
        calc = sumar_anios(c["fecha_inicio"], c["anios_pactados"])
        if calc and c["fecha_caducidad"] and abs((calc - c["fecha_caducidad"]).days) > 1:
            descuadres.append({"Documento": e["id_documento"],
                               "Inicio": c["fecha_inicio"].strftime("%d/%m/%Y"),
                               "Años pactados": c["anios_pactados"],
                               "Vencimiento que resulta": calc.strftime("%d/%m/%Y"),
                               "Vencimiento declarado":
                                   c["fecha_caducidad"].strftime("%d/%m/%Y")})
    return invertidas, descuadres


# ===========================================================================
# 4. Interpretación de la salida del módulo
# ===========================================================================
# Determinista. Reconoce las cuatro formas en que puede llegar la salida de
# IAlert: JSON, CSV, las fichas de la pantalla de Documentos y las líneas del
# panel «Próximos eventos». Separa los registros de estado de los eventos,
# porque responden a preguntas distintas de la batería.

SINONIMOS = [
    ("obsoleto", r"\bobsolet[oa]\b|\bsustituid[oa]\b|\bsuperad[oa]\b|"
                 r"\breemplazad[oa]\b|fuente\s+hist[óo]rica"),
    ("titulo_consumado", r"t[íi]tulo\s+consumado|objeto\s+(ya\s+)?consumado|"
                         r"\bconsumad[oa]\b|\bagotad[oa]\b"),
    ("no_clasificado", r"no\s+determinad[ao]|vigencia\s+no\s+determinada|"
                       r"requiere\s+revisi[óo]n|no\s+clasificad[oa]|sin\s+clasificar|"
                       r"indeterminad[oa]|sin\s+fecha|\bindefinid[oa]\b|desconocid[oa]"),
    ("caducado", r"\bcaducad[oa]\b|\bvencid[oa]\b|\bexpirad[oa]\b|no\s+vigente|"
                 r"fuera\s+de\s+vigor|\bextinguid[oa]\b"),
    ("vigente", r"\bvigente\b|\ben\s+vigor\b|\bactiv[oa]\b"),
]

# Etiquetas que IAlert usa y que no son un estado de vigencia: la validez formal
# y la urgencia van en ejes distintos y no deben leerse como estado.
NO_ES_ESTADO = r"validez\s+formal|\bcr[íi]tico\b|\bpr[óo]ximo\b|\burgencia\b"

P_ID = (r"(?:PRUEBA[\s_\-]?\d+|DOC[\s_\-]?\d+|"
        r"\d{4}\s+[A-ZÁÉÍÓÚ][A-ZÁÉÍÓÚ0-9\s\-]{5,60}|[\w\-]+\.pdf)")
# Palabras que, delante de un identificador, indican que se está citando otro
# documento en vez de abriendo su ficha.
MENCION_DE_OTRO = (r"(sustituye|sustituid[oa]|reemplaza|reemplazad[oa]|anula|"
                   r"deroga|version|referencia|respecto|frente|sobre|vease|ver)"
                   r"\s+(a|de|por|al)?\s*$")

P_EVENTO = r"(vencimiento\s+del\s+documento|fecha\s+l[íi]mite\s+para\s+avisar[^—\-·]*|"
P_EVENTO += r"caducidad|renovaci[óo]n)"


def _estado_de(texto):
    t = plano(texto)
    for estado, patron in SINONIMOS:      # el orden importa: lo específico primero
        if re.search(patron, t):
            return estado
    return None


def _normalizar_id(s):
    s = re.sub(r"\.pdf$", "", str(s or "").strip(), flags=re.IGNORECASE)
    return re.sub(r"[\s\-]+", "_", s).upper()


def _registro(id_doc, estado, fecha=None, cita=False, crudo="", **extra):
    r = {"tipo": "estado", "id_documento": _normalizar_id(id_doc), "estado": estado,
         "fecha_caducidad": fecha, "fecha_emision": None, "sustituye_a": None,
         "evento": None, "fecha_evento": None, "preaviso_dias": None,
         "dias": None, "cita": bool(cita), "texto": crudo}
    r.update(extra)
    return r


def _desde_json(texto):
    datos = json.loads(texto)
    if isinstance(datos, dict):
        for k in ("documentos", "resultados", "items", "salida", "eventos"):
            if isinstance(datos.get(k), list):
                datos = datos[k]
                break
        else:
            datos = [datos]
    out = []
    for d in datos:
        if not isinstance(d, dict):
            continue
        ident = next((d[k] for k in ("id_documento", "id", "documento", "fichero",
                                     "nombre", "archivo") if d.get(k)), None)
        if not ident:
            continue
        bruto = d.get("estado") or d.get("vigencia") or d.get("status")
        estado = bruto if bruto in ESTADOS else _estado_de(str(bruto))
        fecha = (d.get("fecha_caducidad") or d.get("fecha_vencimiento")
                 or d.get("caducidad") or d.get("vencimiento"))
        cita = bool(d.get("cita") or d.get("clausula") or d.get("evidencia")
                    or d.get("fragmento"))
        evento = d.get("evento") or d.get("tipo_evento")
        out.append(_registro(
            ident, estado, fecha, cita, json.dumps(d, ensure_ascii=False),
            tipo="evento" if evento else "estado",
            evento=evento, fecha_evento=d.get("fecha_evento") or d.get("fecha"),
            preaviso_dias=d.get("preaviso_dias") or d.get("preaviso"),
            dias=d.get("dias"), sustituye_a=d.get("sustituye_a") or d.get("sustituye"),
            fecha_emision=d.get("fecha_emision")))
    return out


CABECERAS = {
    "id": r"^(id|id[_\s]?documento|documento|doc|fichero|archivo|nombre)$",
    "estado": r"^(estado|estado[_\s]?vigencia|vigencia|status|resultado)$",
    "fecha": r"^(fecha[_\s]?(de[_\s]?)?(caducidad|vencimiento)|caducidad|vencimiento|"
             r"vence|valido[_\s]?hasta)$",
    "cita": r"^(cita|clausula|evidencia|fragmento|referencia)$",
    "sustituye": r"^(sustituye|sustituye[_\s]?a|version[_\s]?sustituida|reemplaza)$",
}


def _desde_tabla(texto):
    muestra = texto[:2000]
    delim = max(";,\t", key=lambda d: muestra.count(d))
    if muestra.count(delim) == 0:
        return []
    filas = list(csv.DictReader(io.StringIO(texto), delimiter=delim))
    if not filas:
        return []
    cabeceras = [k for k in filas[0].keys() if k is not None]
    # Una tabla tiene al menos dos columnas y cabeceras cortas. Si no, esto es
    # prosa con comas dentro y hay que dejarlo pasar al lector de fichas.
    if len(cabeceras) < 2 or any(len(k.strip()) > 40 for k in cabeceras):
        return []

    def columna(nombre):
        for k in cabeceras:
            if re.match(CABECERAS[nombre], plano(k).replace(" ", "_")):
                return k
        return None

    col_id, col_estado = columna("id"), columna("estado")
    if not col_id or not col_estado:
        return []
    col_fecha, col_cita, col_sust = columna("fecha"), columna("cita"), columna("sustituye")

    out = []
    for f in filas:
        ident = (f.get(col_id) or "").strip()
        if not ident:
            continue
        bruto = (f.get(col_estado) or "").strip()
        out.append(_registro(ident, bruto if bruto in ESTADOS else _estado_de(bruto),
                             f.get(col_fecha) if col_fecha else None,
                             f.get(col_cita) if col_cita else None, str(f),
                             sustituye_a=f.get(col_sust) if col_sust else None))
    return out


def _desde_eventos(texto):
    """
    Líneas del panel «Próximos eventos» de IAlert. Forma observada:

        CRITICO Vencimiento del documento — 2026-08-18 (1 día) — Zaragoza · Prueba_12
        PROXIMO Fecha límite para avisar de no renovación — 2026-08-31 (14 días)
                — preaviso legal: 30 días — Zaragoza · Prueba_7

    Un evento no es un estado: responde a las preguntas 2 y 7, no a la 1.
    """
    out = []
    for linea in texto.splitlines():
        l = linea.strip()
        if not re.search(r"CR[ÍI]TICO|PR[ÓO]XIMO|VENCID[OA]", l, re.IGNORECASE):
            continue
        m_id = re.search(r"·\s*([\w\-. ]+?)\s*$", l) or re.search(P_ID, l, re.IGNORECASE)
        if not m_id:
            continue
        ident = m_id.group(1) if m_id.lastindex else m_id.group(0)
        m_ev = re.search(P_EVENTO, l, re.IGNORECASE)
        m_f = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})", l)
        m_d = re.search(r"\((-?\d{1,5})\s*d[íi]as?\)", l)
        m_p = re.search(r"preaviso[^:]{0,20}:\s*(\d{1,3})\s*d[íi]as", l, re.IGNORECASE)
        out.append(_registro(
            ident, None, None, True, l, tipo="evento",
            evento=(m_ev.group(1).strip().lower() if m_ev else "evento"),
            fecha_evento=m_f.group(1) if m_f else None,
            dias=int(m_d.group(1)) if m_d else None,
            preaviso_dias=int(m_p.group(1)) if m_p else None))
    return out


def _desde_fichas(texto):
    """
    Fichas de la pantalla de Documentos: el identificador abre la ficha y el
    estado, el vencimiento y la evidencia vienen en las líneas siguientes.
    """
    lineas = [l.strip() for l in texto.splitlines()]
    bloques, actual = [], None
    for l in lineas:
        # La fila «Archivo» de la ficha lleva una ruta con el nombre del PDF dentro.
        # Es contenido de la ficha abierta, no la cabecera de una nueva.
        if re.search(r"^archivo\b|[A-Za-z]:\\|/Users/|\\datos", l, re.IGNORECASE):
            if actual:
                actual["lineas"].append(l)
            continue
        # Un identificador AL PRINCIPIO de la línea abre ficha nueva siempre. Uno
        # que aparece en medio sólo la abre si la ficha en curso ya tiene cuerpo,
        # porque dentro de una ficha se citan otros documentos («sustituye a
        # PRUEBA_3») y eso no es una ficha nueva.
        #
        # La condición de antes exigía cuerpo en los dos casos, y con una salida de
        # una línea por documento —la forma más natural de pegarla— se comía uno de
        # cada dos registros y además les asignaba el estado del siguiente. Un
        # evaluador que lee mal la salida del módulo no evalúa: inventa.
        al_inicio = re.match(rf"^\s*({P_ID})\b", l, re.IGNORECASE)
        en_medio = re.search(P_ID, l, re.IGNORECASE) if len(l) < 90 else None
        m = al_inicio or en_medio
        # «Sustituye a PRUEBA_3» nombra otro documento desde dentro de una ficha:
        # es una referencia, no la cabecera de una ficha nueva. Partir ahí crearía
        # un documento fantasma con el estado del anterior.
        mencion = bool(m) and not al_inicio and bool(
            re.search(MENCION_DE_OTRO, plano(l[:m.start()])))
        nuevo = (actual is None or bool(al_inicio)
                 or (len(actual["lineas"]) > 1 and not mencion))
        if m and nuevo:
            if actual:
                bloques.append(actual)
            actual = {"id": m.group(1) if m.lastindex else m.group(0), "lineas": [l]}
        elif actual and l:
            actual["lineas"].append(l)
    if actual:
        bloques.append(actual)

    out = []
    for b in bloques:
        cuerpo = " ".join(b["lineas"])
        limpio = re.sub(NO_ES_ESTADO, " ", cuerpo, flags=re.IGNORECASE)
        estado = _estado_de(limpio)
        # Todas las menciones, no sólo la primera: la ficha dice «Vencimiento del
        # documento (4577 días)» antes de decir la fecha, y quedarse en la primera
        # coincidencia daría por hecho que el módulo no la declara.
        fecha = None
        for m in re.finditer(r"(?:vence|vencimiento|caducidad|v[áa]lido\s+hasta|"
                             r"hasta\s+el)\b[^.]{0,45}", cuerpo, re.IGNORECASE):
            f = fecha_de(m.group(0))
            if f:
                fecha = f.strftime("%d/%m/%Y")
                break
        m_d = re.search(r"\((-?\d{1,5})\s*d[íi]as?\)", cuerpo)
        m_s = re.search(r"sustituye\s+a\s+([\w\-.]+)|reemplaza\s+a\s+([\w\-.]+)",
                        cuerpo, re.IGNORECASE)
        cita = bool(re.search(r"cl[áa]usula|estipulaci[óo]n|«|art[íi]culo|"
                              r"cadena\s+documental", cuerpo, re.IGNORECASE))
        out.append(_registro(b["id"], estado, fecha, cita, cuerpo,
                             dias=int(m_d.group(1)) if m_d else None,
                             sustituye_a=(m_s.group(1) or m_s.group(2)) if m_s else None))
    return out


# Etiquetas de la tabla «Campo / Valor» de la ficha de IAlert, tal como salen en
# pantalla. Se normalizan sin tildes para que un copiado imperfecto no rompa la
# lectura.
ETIQUETAS_FICHA = {
    "archivo": "archivo", "ciudad": "ciudad", "direccion": "direccion",
    "tipo de documento": "tipo_documento",
    "familia documental": "familia", "cadena documental": "cadena",
    "fecha de firma": "fecha_emision", "fecha de inicio": "fecha_inicio",
    "plazo": "plazo", "fecha de vencimiento": "fecha_caducidad",
    "prorroga tacita": "prorroga_tacita", "preaviso (dias)": "preaviso_dias",
    "preaviso dias": "preaviso_dias",
    "fecha critica de alerta": "fecha_critica",
    "arrendador": "arrendador", "arrendatario": "arrendatario",
    "fecha de subida": "fecha_subida", "subido por": "subido_por",
    "ultima modificacion": "modificado", "numero de paginas": "paginas",
}

VACIO_FICHA = {"", "—", "-", "–", "n/a", "na", "null", "none", "sin datos"}


def _valor_ficha(v):
    """«✓» -> True · «—» -> None · «8» -> '8'. El resto, tal cual."""
    t = (v or "").strip()
    if plano(t) in VACIO_FICHA:
        return None
    if t in ("✓", "✔", "Sí", "Si", "sí", "si", "True"):
        return True
    if t in ("✗", "✘", "No", "no", "False"):
        return False
    return t


def _desde_ficha_campos(texto):
    """
    La ficha de documento de IAlert: la cabecera con el estado y la alerta, y
    debajo una tabla de dos columnas «Campo | Valor».

    Es la forma en que la salida se puede copiar de la pantalla sin que Martín
    tenga que exportar nada, y por eso existe: pedirle un formato nuevo a seis
    días de la entrega habría sido pedirle que cambiase su módulo para que yo
    pudiera evaluarlo, que es justo al revés de como debe funcionar esto.
    """
    lineas = [l.rstrip() for l in (texto or "").splitlines()]
    pares, cortes = [], []          # (clave, valor, nº de línea) y dónde parte cada ficha

    def _etiqueta(l):
        return ETIQUETAS_FICHA.get(plano(l).rstrip(":").strip())

    i = 0
    while i < len(lineas):
        l = lineas[i]
        # Forma 1 — etiqueta y valor en la misma línea: «Campo | Valor»,
        # «Campo: Valor», «Campo<tab>Valor», «Campo<2+ espacios>Valor».
        m = re.match(r"^\s*([A-Za-zÁÉÍÓÚÑáéíóúñ()\s]{3,32}?)\s*(?:\||\t|\s{2,}|:)\s*"
                     r"(\S.*?)\s*$", l)
        if m and _etiqueta(m.group(1)):
            pares.append((_etiqueta(m.group(1)), _valor_ficha(m.group(2)), i))
            i += 1
            continue

        # Forma 2 — etiqueta sola en su línea y el valor en la siguiente. Es como
        # queda al copiar una tabla del navegador, que es lo que uno hace, y por
        # no contemplarla el intérprete no reconocía nada y mandaba a rellenar la
        # tabla a mano: el evaluador se volvía el trabajo que venía a ahorrar.
        clave = _etiqueta(l)
        if clave:
            j = i + 1
            while j < len(lineas) and not lineas[j].strip():
                j += 1
            # Si lo siguiente es otra etiqueta, el valor está vacío en la ficha.
            # Consumirlo tomaría la etiqueta por valor y desplazaría la tabla
            # entera una fila.
            if j < len(lineas) and not _etiqueta(lineas[j]):
                pares.append((clave, _valor_ficha(lineas[j]), i))
                i = j + 1
                continue
            pares.append((clave, None, i))
        i += 1

    if len(pares) < 3:
        return []

    # Varias fichas pegadas seguidas: cuando una etiqueta ya vista vuelve a
    # aparecer, empieza otro documento. Sin esto, pegar diez fichas de golpe
    # produciría un solo documento con los campos de la primera — y el evaluador
    # diría que a Martín le faltan nueve, que sería mentira mía.
    bloques, actual, vistas = [], [], set()
    for clave, valor, nlinea in pares:
        if clave in vistas:
            bloques.append((actual, vistas))
            actual, vistas = [], set()
        actual.append((clave, valor, nlinea))
        vistas.add(clave)
    if actual:
        bloques.append((actual, vistas))

    salida = []
    for bloque, _ in bloques:
        if len(bloque) < 3:
            continue
        desde = bloque[0][2]
        hasta = bloque[-1][2] + 2
        # La cabecera de la primera ficha —estado y alerta— va por encima de su
        # primera etiqueta; la de las siguientes, entre la última etiqueta de la
        # anterior y la primera de ésta.
        arranque = 0 if bloque is bloques[0][0] else max(0, desde - 8)
        salida += _ficha_de(dict((c, v) for c, v, _ in bloque),
                            "\n".join(lineas[arranque:hasta]))
    return salida


def _ficha_de(campos, cuerpo):
    """Un registro de estado (y sus eventos) a partir de los campos ya leídos."""
    lineas = cuerpo.splitlines()

    # El identificador: el nombre del PDF de la fila «Archivo», o la cabecera.
    id_doc = None
    if isinstance(campos.get("archivo"), str):
        id_doc = re.sub(r"\.pdf$", "", campos["archivo"].split("\\")[-1].split("/")[-1],
                        flags=re.IGNORECASE)
    if not id_doc:
        for l in lineas[:4]:
            if l.strip() and not re.search(r"\||:", l):
                id_doc = l.strip()
                break
    id_doc = (id_doc or "documento").strip()

    cuerpo = "\n".join(lineas)
    estado = _estado_de(re.sub(NO_ES_ESTADO, " ", cuerpo, flags=re.IGNORECASE))

    fecha = None
    if isinstance(campos.get("fecha_caducidad"), str):
        f = fecha_de(campos["fecha_caducidad"])
        fecha = f.strftime("%d/%m/%Y") if f else campos["fecha_caducidad"]

    # La alerta de la cabecera —«Actualización anual de la renta por IPC (140
    # días)»— es un evento, no un estado: viaja aparte y no puntúa como estado.
    eventos = []
    for m in re.finditer(r"^(.{4,90}?)\s*\((-?\d{1,5})\s*d[íi]as?\)\s*$",
                         cuerpo, re.MULTILINE):
        eventos.append(_registro(id_doc, None, None, False, m.group(0),
                                 tipo="evento", evento=m.group(1).strip(),
                                 dias=int(m.group(2))))

    preaviso = campos.get("preaviso_dias")
    reg = _registro(
        id_doc, estado, fecha,
        cita=bool(campos.get("cadena") or campos.get("plazo")),
        crudo=cuerpo,
        fecha_emision=campos.get("fecha_emision"),
        preaviso_dias=int(preaviso) if str(preaviso or "").isdigit() else None,
        prorroga_tacita=campos.get("prorroga_tacita"),
        fecha_critica=campos.get("fecha_critica"),
        paginas=int(campos["paginas"]) if str(campos.get("paginas") or "").isdigit()
                else None,
        direccion=campos.get("direccion"),
        ciudad=campos.get("ciudad"),
        plazo=campos.get("plazo"),
        campos_ficha=campos)
    return [reg] + eventos


def diagnosticar(texto):
    """
    Qué ha reconocido el intérprete y qué no, línea a línea.

    Existe porque el modo de fallo real no es que el intérprete se equivoque: es
    que no reconozca nada y diga «introduce los estados a mano», que es
    exactamente el trabajo que el sistema venía a ahorrar. Un mensaje de error
    que no dice qué le pasa obliga a adivinar, y aquí adivinar es probar formatos
    hasta que uno cuele.
    """
    lineas = [l.rstrip() for l in (texto or "").splitlines() if l.strip()]
    reconocidas, sueltas = [], []
    for l in lineas:
        m = re.match(r"^\s*([A-Za-zÁÉÍÓÚÑáéíóúñ()\s]{3,32}?)\s*(?:\||\t|\s{2,}|:)\s*"
                     r"(\S.*?)\s*$", l)
        etiqueta = (ETIQUETAS_FICHA.get(plano(m.group(1)).rstrip(":").strip())
                    if m else None) or ETIQUETAS_FICHA.get(plano(l).rstrip(":").strip())
        (reconocidas if etiqueta else sueltas).append(l)
    return {"lineas": len(lineas), "reconocidas": reconocidas, "sueltas": sueltas[:12],
            "conocidas": sorted({plano(k) for k in ETIQUETAS_FICHA})}


def interpretar(texto, modo="determinista"):
    """
    Devuelve (registros, avisos). Los registros llevan `tipo`: «estado» o
    «evento». Los avisos recogen lo que no ha podido interpretarse, para que
    quede a la vista y pueda corregirse a mano antes de puntuar: el módulo no
    debe salir penalizado por un fallo de lectura mío.
    """
    texto = (texto or "").strip()
    if not texto:
        return [], []

    if modo not in ("determinista", None):
        crudo = llm.interpretar_con_llm(texto, FICHA["esquema_salida"],
                                        FICHA["prompt_interpretacion"])
        return [_registro(d.get("id_documento"), d.get("estado"),
                          d.get("fecha_caducidad"), d.get("cita"), json.dumps(d),
                          tipo=d.get("tipo", "estado"), evento=d.get("evento"),
                          fecha_evento=d.get("fecha_evento"),
                          preaviso_dias=d.get("preaviso_dias"),
                          sustituye_a=d.get("sustituye_a")) for d in crudo], []

    avisos = []
    eventos = _desde_eventos(texto)
    # Las líneas de evento ya están leídas: si se dejan, los lectores de estado
    # las tomarían por fichas y emitirían un registro fantasma por cada alerta.
    sin_eventos = "\n".join(l for l in texto.splitlines()
                            if not re.search(r"CR[ÍI]TICO|PR[ÓO]XIMO|VENCID[OA]S?\b",
                                             l, re.IGNORECASE))
    # La ficha de campos va antes que los lectores genéricos: su tabla «Campo |
    # Valor» también casaría con el lector de tabla, y ahí se perderían la
    # prórroga, el preaviso y la fecha crítica, que son justo los campos nuevos.
    estados = []
    for lector, nombre in ((_desde_json, "JSON"),
                           (_desde_ficha_campos, "ficha de campos de IAlert"),
                           (_desde_tabla, "tabla"),
                           (_desde_fichas, "fichas de la interfaz")):
        try:
            leidos = lector(sin_eventos)
            estados = [r for r in leidos if r["tipo"] == "estado"]
            eventos += [r for r in leidos
                        if r["tipo"] == "evento" and lector is _desde_ficha_campos]
        except Exception:
            estados = []
        if estados:
            if nombre != "JSON":
                avisos.append(f"Salida leída como {nombre}. Comprueba la tabla antes "
                              f"de evaluar.")
            break

    if eventos:
        avisos.append(f"Se han reconocido {len(eventos)} evento(s) de vencimiento o "
                      f"preaviso. Los eventos no puntúan como estado: alimentan los "
                      f"casos de la ventana de vencimientos y del aviso anticipado.")

    registros = estados + eventos
    if not registros:
        return [], ["No se ha reconocido ningún documento en la respuesta. "
                    "Introduce los estados a mano en la tabla."]

    for r in estados:
        if r["estado"] is None:
            avisos.append(f"No se ha identificado el estado declarado para "
                          f"{r['id_documento']}; corrígelo en la tabla.")
        if re.search(r"\bindefinid[oa]\b", r.get("texto") or "", re.IGNORECASE):
            avisos.append(f"{r['id_documento']} se declara «indefinido». Se cuenta "
                          f"como vigencia no determinada, pero la etiqueta se lee "
                          f"como vigencia sin plazo: conviene precisarla.")
    return registros, avisos


# ===========================================================================
# 5. Contraste y batería
# ===========================================================================

# IAlert emite dos estados: «Vigente» y «Obsoleto». Mi vocabulario tiene cinco, y
# distingue el documento que **venció** del que fue **sustituido** por una versión
# posterior. Son cosas distintas aguas abajo —una obliga a renovar, la otra a
# mirar la versión nueva— pero exigirle a un módulo de dos estados que acierte una
# distinción de cinco sería medirle contra un vocabulario que no es el suyo.
#
# Así que «Obsoleto» se acepta para las dos: lo que afirma —«ya no vigente»— es
# correcto en ambos casos. Lo que no se puede afirmar es *por qué*, y eso queda
# como hallazgo y como criterio del panel, no como suspenso.
EQUIVALENTES = {("caducado", "obsoleto"), ("obsoleto", "caducado")}


def _comparar(esperado, reportado):
    if (reportado["estado"] != esperado["estado"]
            and (esperado["estado"], reportado["estado"]) not in EQUIVALENTES):
        return False, (f"declara «{ESTADOS.get(reportado['estado'], reportado['estado'])}» "
                       f"y los documentos sostienen «{ESTADOS[esperado['estado']]}»: "
                       f"{esperado['motivo']}")
    citada = fecha_de(reportado.get("fecha_caducidad"))
    real = esperado["fecha_caducidad"]
    if citada and real and citada != real:
        return False, (f"cita como vencimiento el {citada.strftime('%d/%m/%Y')} "
                       f"y el documento fija el {real.strftime('%d/%m/%Y')}")
    return True, ""


ETIQUETAS_TABLA = {"error": "Estado incorrecto", "no": "Sin clasificar"}


def _lista(xs, vacio="ninguno"):
    xs = [str(x) for x in xs if x]
    return ", ".join(xs) if xs else vacio


def _desglosar(casos, esperados, estados, eventos, contraste, por_id,
               fecha_evaluacion, ventana_dias, contexto, repeticion):
    """
    Rellena `esperado` y `observado` de cada caso para la plantilla común.

    Va aparte y al final a propósito. No decide nada —los diez casos ya están
    resueltos cuando esto se ejecuta— y sólo separa en dos columnas lo que el
    texto de la observación ya contaba fundido. Si esta función desapareciera, el
    veredicto sería exactamente el mismo; lo único que se perdería es poder leer
    la comparación sin leer la prosa.
    """
    def _e(clave):
        return [x for x in esperados if x.get(clave)]

    def _estado_obs(ident):
        r = por_id.get(ident) or {}
        return ESTADOS.get(r.get("estado"), r.get("estado") or "sin registro")

    dentro = vencimientos_en(esperados, fecha_evaluacion, ventana_dias)
    anunciados = sorted({r["id_documento"] for r in eventos
                         if r.get("evento") and "vencimiento" in (r["evento"] or "")})
    con_fecha = _e("fecha_caducidad")
    invertidas, _ = incoherencias_de_fechas(esperados)
    cadenas = {k: v for k, v in (contexto.get("cadenas") or {}).items() if len(v) > 1}
    sustituidos = [e for v in cadenas.values() for e in v if e["sustituido_por"]]
    hoy_mismo = [e for e in esperados if e["fecha_caducidad"] == fecha_evaluacion]
    sin_plazo = [e for e in esperados if e["fecha_caducidad"] is None and e["legible"]]

    NO_EJERCITADO = "— el conjunto no contiene esta situación —"
    SIN_DATO = "— no aportado en esta ejecución —"

    d = {}

    d[1] = (_lista([f"{e['id_documento']}: {ESTADOS[e['estado']]}" for e in esperados]),
            _lista([f"{e['id_documento']}: {_estado_obs(e['id_documento'])}"
                    for e in esperados]))

    d[2] = (f"vencen dentro de {ventana_dias} días: "
            + _lista([e["id_documento"] for e in dentro]),
            ("anuncia: " + _lista(anunciados)) if eventos else SIN_DATO)

    d[3] = (_lista([f"{e['id_documento']}: {e['fecha_caducidad']:%d/%m/%Y}"
                    for e in con_fecha]),
            _lista([f"{e['id_documento']}: "
                    f"{(por_id.get(e['id_documento']) or {}).get('fecha_caducidad') or '—'}"
                    for e in con_fecha]) if con_fecha else SIN_DATO)

    d[4] = (("señalar como no determinables: "
             + _lista([i["Documento"] for i in invertidas])) if invertidas
            else "ningún documento con las fechas invertidas",
            _lista([f"{i['Documento']}: {_estado_obs(i['Documento'])}"
                    for i in invertidas]) if invertidas else NO_EJERCITADO)

    d[5] = (("declarar sustituidos: "
             + _lista([f"{e['id_documento']} ← {e['sustituido_por']}"
                       for e in sustituidos])) if sustituidos
            else "ninguna cadena con dos versiones",
            _lista([f"{e['id_documento']}: {_estado_obs(e['id_documento'])}"
                    for e in sustituidos]) if sustituidos else NO_EJERCITADO)

    declarados = sorted({_estado_obs(e["id_documento"]) for e in hoy_mismo})
    d[6] = (("un único estado para: "
             + _lista([e["id_documento"] for e in hoy_mismo])) if hoy_mismo
            else "ningún documento vence en la fecha de consulta",
            _lista(declarados) if hoy_mismo else NO_EJERCITADO)

    d[7] = ("cada alerta con su fecha y la antelación aplicada",
            (f"{len(eventos)} alerta(s), "
             f"{sum(1 for r in eventos if r.get('preaviso_dias'))} con antelación "
             f"declarada") if eventos else SIN_DATO)

    d[8] = ((_lista([e["id_documento"] for e in sin_plazo])
             + ": vigencia no determinada, sin fecha") if sin_plazo
            else "todos los documentos fijan plazo",
            _lista([f"{e['id_documento']}: {_estado_obs(e['id_documento'])}"
                    + (f", vence {(por_id.get(e['id_documento']) or {}).get('fecha_caducidad')}"
                       if (por_id.get(e['id_documento']) or {}).get("fecha_caducidad")
                       else "")
                    for e in sin_plazo]) if sin_plazo else NO_EJERCITADO)

    d[9] = (f"{len(esperados)} registro(s), uno por documento entregado",
            f"{len(estados)} registro(s) emitido(s)"
            + (f"; sin registro: "
               + _lista([e["id_documento"] for e in contraste["omitidas"]])
               if contraste["omitidas"] else "")
            + (f"; sin documento que los respalde: "
               + _lista([r["id_documento"] for r in contraste["falsas"]])
               if contraste["falsas"] else ""))

    d[10] = ("los mismos estados en dos ejecuciones seguidas",
             ("coinciden" if casos[10]["resultado"] == "pasa" else "difieren")
             if repeticion is not None else SIN_DATO)

    _pr = [(e, por_id[e["id_documento"]]) for e in esperados
           if e["id_documento"] in por_id
           and e["campos"].get("prorroga_tipo") in ("tacita", "expresa", "renunciada")
           and por_id[e["id_documento"]].get("prorroga_tacita") is not None]
    d[11] = ("la naturaleza de la prórroga que fija la cláusula: "
             + _lista(sorted({PRORROGAS[e["campos"]["prorroga_tipo"]] for e, _ in _pr}))
             if _pr else "una cláusula de prórroga concluyente",
             _lista([f"{e['id_documento']}: el módulo marca prórroga tácita "
                     f"{'sí' if r['prorroga_tacita'] else 'no'}" for e, r in _pr])
             if _pr else NO_EJERCITADO)

    _fc = [(e, por_id[e["id_documento"]]) for e in esperados
           if e["id_documento"] in por_id and e["campos"].get("fecha_critica")]
    d[12] = (_lista([f"{e['id_documento']}: "
                     f"{e['campos']['fecha_critica'].strftime('%d/%m/%Y')}"
                     for e, _ in _fc]) if _fc else
             "un documento con plazo de preaviso del que derivar la fecha crítica",
             _lista([f"{e['id_documento']}: {r.get('fecha_critica') or 'sin emitir'}"
                     for e, r in _fc]) if _fc else NO_EJERCITADO)

    for n, (esp, obs) in d.items():
        if n in casos:
            casos[n]["esperado"], casos[n]["observado"] = esp, obs


def conciliar_ids(esperados, reportados):
    """
    El módulo nombra los documentos por el fichero que tiene él en su disco
    —«ARRENDAMIENTO CRED.pdf»— y yo tengo el mismo contrato guardado como
    «CONTRATO ARRENDAMIENTO CRED.pdf». Sin conciliar, el contraste no empareja
    nada: el evaluador diría que el módulo se inventó un documento y se dejó otro
    sin clasificar, y las dos acusaciones serían mías.

    Regla estricta a propósito: sólo se renombra cuando **un único** documento
    esperado contiene al reportado o al revés. Con dos candidatos no se elige, se
    deja sin emparejar y que se corrija a mano. Emparejar mal es peor que no
    emparejar: mueve un veredicto de un documento a otro sin que se note.

    Devuelve (reportados, renombres) — los renombres se declaran siempre.
    """
    ids_esperados = {e["id_documento"] for e in esperados}
    # La comparación es por letras y números, sin guiones ni espacios: el módulo
    # nombra «SUBROGACION A REPSOL COMERCIAL-LOS OLIVOS» y el fichero se llama
    # «...COMERCIALLOS OLIVOS». Comparando las cadenas tal cual no casaban, y el
    # evaluador daba por no clasificado un documento que el módulo sí clasificó.
    desnudo = {i: re.sub(r"[^a-z0-9]", "", i.lower()) for i in ids_esperados}
    renombres = []
    salida = []
    for r in reportados:
        rid = r.get("id_documento")
        if rid in ids_esperados or not rid:
            salida.append(r)
            continue
        nrid = re.sub(r"[^a-z0-9]", "", str(rid).lower())
        candidatos = [i for i, d in desnudo.items() if nrid in d or d in nrid]
        if len(candidatos) == 1:
            r = dict(r, id_documento=candidatos[0])
            renombres.append((rid, candidatos[0]))
        salida.append(r)
    return salida, renombres


def evaluar(esperados, reportados, fecha_evaluacion=None, repeticion=None,
            modo_lectura="determinista", ventana_dias=VENTANA_DIAS, contexto=None):
    fecha_evaluacion = fecha_evaluacion or date.today()
    contexto = contexto or {}
    reportados, renombres = conciliar_ids(esperados, reportados)
    estados = [r for r in reportados if r.get("tipo", "estado") == "estado"]
    eventos = [r for r in reportados if r.get("tipo") == "evento"]

    # Los documentos sobre los que el evaluador se abstiene salen del contraste
    # entero, y también de la lista de reportados: si se quedaran, el módulo
    # aparecería clasificando un documento que «no existe» y la precisión bajaría
    # por un límite de mi lectura, no por un fallo suyo.
    abstenidos = [e for e in esperados if e.get("abstiene")]
    ids_abst = {e["id_documento"] for e in abstenidos}
    esperados_firmes = [e for e in esperados if not e.get("abstiene")]
    estados_firmes = [r for r in estados if r["id_documento"] not in ids_abst]
    esperados, estados_todos = esperados_firmes, estados
    estados = estados_firmes

    contraste = C.contrastar(esperados, estados,
                             clave=lambda x: x["id_documento"], comparar=_comparar)
    por_id = {r["id_documento"]: r for r in estados}
    motivos = {m["clave"]: m["motivo"] for m in contraste["motivos"]}
    casos = {}

    # 1 — estado en la fecha real de consulta                        [pregunta 1]
    mal = [f"en {e['id_documento']} {motivos[e['id_documento']]}"
           for e in contraste["con_error"]]
    sin_referencia = [r["id_documento"] for r in estados
                      if not r.get("fecha_caducidad")
                      and (por_id.get(r["id_documento"]) and
                           next((e for e in esperados
                                 if e["id_documento"] == r["id_documento"]
                                 and e["fecha_caducidad"]), None))]
    casos[1] = B.caso(
        bool(esperados) and not mal and not contraste["omitidas"],
        f"{len(contraste['detectadas'])} de {len(esperados)} documentos con el estado "
        f"correcto en la fecha de consulta "
        f"({fecha_evaluacion.strftime('%d/%m/%Y')})."
        + (f" El módulo {'; '.join(mal)}." if mal else "")
        + (f" Sin estado declarado: "
           f"{', '.join(e['id_documento'] for e in contraste['omitidas'])}."
           if contraste["omitidas"] else "")
        + (f" Emiten estado sin la fecha de caducidad de referencia: "
           f"{', '.join(sin_referencia)}." if sin_referencia else ""),
        omitir=not esperados)

    # 2 — ventana de vencimientos                                    [pregunta 2]
    dentro = vencimientos_en(esperados, fecha_evaluacion, ventana_dias)
    anunciados = {r["id_documento"] for r in eventos
                  if r.get("evento") and "vencimiento" in (r["evento"] or "")}
    if not eventos:
        casos[2] = B.caso(False,
                          f"No se ha pegado ninguna consulta de vencimientos. El "
                          f"evaluador determina que dentro de {ventana_dias} días "
                          f"vence: "
                          + (", ".join(f"{e['id_documento']} "
                                       f"({e['fecha_caducidad'].strftime('%d/%m/%Y')})"
                                       for e in dentro) or "ninguno"),
                          omitir=True,
                          requiere=("la consulta de vencimientos del módulo: el panel "
                                    "«Próximos eventos» o la pantalla de Alertas"))
    else:
        esperada = {e["id_documento"] for e in dentro}
        sobran = anunciados - esperada
        faltan = esperada - anunciados
        casos[2] = B.caso(
            not sobran and not faltan,
            f"En una ventana de {ventana_dias} días vencen {len(esperada)} "
            f"documento(s) y el módulo anuncia {len(anunciados)}."
            + (f" Anunciados fuera del rango: {', '.join(sorted(sobran))}."
               if sobran else "")
            + (f" Dentro del rango y no anunciados: {', '.join(sorted(faltan))}."
               if faltan else ""))

    # 3 — exactitud de la fecha de caducidad                         [pregunta 3]
    con_fecha = [e for e in esperados if e["fecha_caducidad"]]
    citadas = [(e, fecha_de((por_id.get(e["id_documento"]) or {}).get("fecha_caducidad")))
               for e in con_fecha]
    citadas = [(e, f) for e, f in citadas if f]
    erroneas = [f"{e['id_documento']} devuelve {f.strftime('%d/%m/%Y')} y el documento "
                f"fija {e['fecha_caducidad'].strftime('%d/%m/%Y')}"
                for e, f in citadas if f != e["fecha_caducidad"]]
    casos[3] = B.caso(
        bool(citadas) and not erroneas,
        (f"{len(citadas)} de {len(con_fecha)} documentos con vencimiento determinable "
         f"reciben una fecha del módulo. "
         + ("Todas coinciden con la cláusula de duración."
            if not erroneas else "Discrepan: " + "; ".join(erroneas) + ".")
         if citadas else
         "El módulo no devuelve ninguna fecha de caducidad que contrastar."),
        omitir=not citadas,
        requiere=("que la salida del módulo incluya la fecha de caducidad junto al "
                  "estado de cada documento") if not citadas else None)

    # 4 — incoherencia entre emisión y caducidad                     [pregunta 4]
    invertidas, descuadres = incoherencias_de_fechas(esperados)
    if not invertidas:
        casos[4] = B.caso(False,
                          "Ningún documento del conjunto tiene la fecha de emisión "
                          "posterior a la de caducidad, así que la incoherencia que "
                          "el caso mide no está presente.",
                          no_aplica=True,
                          requiere=("un documento cuya fecha de emisión sea posterior "
                                    "a su fecha de caducidad"))
    else:
        ids = [i["Documento"] for i in invertidas]
        avisados = [i for i in ids
                    if (por_id.get(i) or {}).get("estado") == "no_clasificado"]
        casos[4] = B.caso(
            len(avisados) == len(ids),
            f"Documentos con las fechas invertidas: {', '.join(ids)}. "
            f"El módulo los señala en {len(avisados)} de {len(ids)} casos; en el "
            f"resto toma la fecha de caducidad por buena.")

    # 5 — versionado dentro de la cadena documental                  [pregunta 5]
    cadenas = {k: v for k, v in (contexto.get("cadenas") or {}).items() if len(v) > 1}
    if not cadenas:
        casos[5] = B.caso(
            False,
            "Ningún par de documentos del conjunto comparte inmueble, luego no hay "
            "ninguna cadena documental con dos versiones que verificar.",
            no_aplica=True,
            requiere=("dos versiones del mismo inmueble — un contrato y su "
                      "renovación. El módulo las agrupa por dirección normalizada, "
                      "así que basta con que compartan la calle y el número"))
    else:
        fallos = []
        for k, grupo in cadenas.items():
            sustituidos = [e for e in grupo if e["sustituido_por"]]
            for e in sustituidos:
                r = por_id.get(e["id_documento"]) or {}
                declara = (r.get("estado") == "obsoleto"
                           or _normalizar_id(r.get("sustituye_a"))
                           == e["sustituido_por"])
                if not declara:
                    fallos.append(f"{e['id_documento']} (cadena «{k}») no se declara "
                                  f"sustituido por {e['sustituido_por']}")
        casos[5] = B.caso(
            not fallos,
            f"Cadenas documentales con más de una versión: "
            + "; ".join(f"«{k}»: {', '.join(e['id_documento'] for e in v)}"
                        for k, v in cadenas.items())
            + (". La sustitución se declara en todas." if not fallos
               else ". " + "; ".join(fallos) + "."))

    # 6 — vencimiento el mismo día                                   [pregunta 6]
    hoy_mismo = [e for e in esperados if e["fecha_caducidad"] == fecha_evaluacion]
    if not hoy_mismo:
        # Ordenadas por cercanía a la fecha de consulta: la sugerencia útil es la
        # que está a un par de días, no la de hace tres años.
        sugerencias = sorted({e["fecha_caducidad"] for e in esperados
                              if e["fecha_caducidad"]},
                             key=lambda f: abs((f - fecha_evaluacion).days))
        casos[6] = B.caso(
            False,
            "Ningún documento vence exactamente en la fecha de consulta, así que el "
            "caso límite no se ejercita.",
            no_aplica=True,
            requiere=("fijar la fecha de consulta en "
                      + (" o ".join(f.strftime("%d/%m/%Y") for f in sugerencias[:2])
                         or "la fecha de vencimiento de alguno de los documentos")
                      + ", que es cuando vence alguno de estos documentos"))
    else:
        # El criterio del evaluador está fijado y escrito: vigente el día en que
        # vence. Lo que se juzga no es que el módulo comparta el criterio, sino
        # que aplique uno solo y lo declare.
        declarados = {(por_id.get(e["id_documento"]) or {}).get("estado")
                      for e in hoy_mismo}
        declarados.discard(None)
        casos[6] = B.caso(
            len(declarados) == 1,
            f"Documentos que vencen el mismo día de la consulta: "
            f"{', '.join(e['id_documento'] for e in hoy_mismo)}. "
            + (f"El módulo les asigna un único estado "
               f"({ESTADOS.get(list(declarados)[0], '—')}), luego el criterio es "
               f"consistente." if len(declarados) == 1 else
               f"El módulo les asigna estados distintos "
               f"({', '.join(ESTADOS.get(d, str(d)) for d in declarados)}): el "
               f"criterio del caso límite no está fijado."))

    # 7 — aviso con antelación                                       [pregunta 7]
    con_preaviso = [r for r in eventos if r.get("preaviso_dias")]
    if not eventos:
        casos[7] = B.caso(False, "No se ha pegado ninguna alerta del módulo.",
                          omitir=True,
                          requiere=("la pantalla de alertas del módulo, con la "
                                    "antelación aplicada a cada una"))
    else:
        sin_datos = [r["id_documento"] for r in eventos
                     if not (r.get("fecha_evento") and r.get("dias") is not None)]
        casos[7] = B.caso(
            bool(con_preaviso) and not sin_datos,
            f"{len(eventos)} alerta(s) emitidas, {len(con_preaviso)} con la "
            f"antelación aplicada declarada."
            + (f" Sin fecha o sin antelación: {', '.join(sin_datos)}."
               if sin_datos else "")
            + ("" if con_preaviso else " Ninguna declara el plazo de preaviso "
                                       "aplicado, así que no puede comprobarse el "
                                       "umbral."))

    # 8 — documento sin fecha de caducidad                           [pregunta 8]
    sin_plazo = [e for e in esperados if e["fecha_caducidad"] is None and e["legible"]]
    indebidos = [e["id_documento"] for e in sin_plazo
                 if (por_id.get(e["id_documento"]) or {}).get("estado") == "vigente"]
    con_fecha_inventada = [e["id_documento"] for e in sin_plazo
                           if (por_id.get(e["id_documento"]) or {}).get("fecha_caducidad")]
    casos[8] = B.caso(
        bool(sin_plazo) and not indebidos and not con_fecha_inventada,
        (f"Documentos sin vencimiento determinable: "
         f"{', '.join(e['id_documento'] for e in sin_plazo)}."
         + (f" Declarados vigentes pese a ello: {', '.join(indebidos)}."
            if indebidos else "")
         + (f" Reciben una fecha de caducidad que no consta en el documento: "
            f"{', '.join(con_fecha_inventada)}." if con_fecha_inventada else "")
         + ("" if indebidos or con_fecha_inventada
            else " Ninguno se declara vigente ni recibe fecha inventada.")
         if sin_plazo else
         "Todos los documentos aportados fijan un plazo, así que la situación que el "
         "caso mide no está presente."),
        no_aplica=not sin_plazo,
        requiere=("un documento sin fecha de caducidad determinable")
                 if not sin_plazo else None)

    # 9 — cobertura del conjunto                             [criterio transversal]
    casos[9] = B.caso(
        bool(esperados) and not contraste["omitidas"] and not contraste["falsas"]
        and not contraste["duplicadas"],
        f"Se entregan {len(esperados)} documentos y el módulo emite {len(estados)} "
        f"registros de estado."
        + (f" Sin registro: "
           f"{', '.join(e['id_documento'] for e in contraste['omitidas'])}."
           if contraste["omitidas"] else "")
        + (f" Registros que no corresponden a ningún documento entregado: "
           f"{', '.join(r['id_documento'] for r in contraste['falsas'])}."
           if contraste["falsas"] else "")
        + (f" Repetidos: "
           f"{', '.join(r['id_documento'] for r in contraste['duplicadas'])}."
           if contraste["duplicadas"] else ""),
        omitir=not esperados)

    # 10 — repetibilidad                                     [criterio transversal]
    if repeticion is None:
        casos[10] = B.caso(False, "No se ha aportado una segunda ejecución.",
                           omitir=True,
                           requiere=("una segunda ejecución del módulo sobre este "
                                     "mismo conjunto, sin modificar los documentos"))
    else:
        # La segunda ejecución se filtra igual que la primera: si un documento
        # sale del contraste por abstención, tiene que salir de las dos o la
        # comparación de firmas dice que el módulo no es repetible cuando lo que
        # ha cambiado es a quién estoy mirando.
        rep_estados = [r for r in repeticion
                       if r.get("tipo", "estado") == "estado"
                       and r.get("id_documento") not in ids_abst]
        firma = lambda l: sorted((r["id_documento"], r["estado"]) for r in l)
        f1, f2 = firma(estados), firma(rep_estados)
        if f1 == f2:
            detalle = (f"Las dos ejecuciones coinciden en los {len(f1)} documento(s) "
                       f"y en el estado asignado a cada uno.")
        else:
            solo1 = [i for i in f1 if i not in f2]
            solo2 = [i for i in f2 if i not in f1]
            detalle = "El veredicto varía entre ejecuciones."
            if solo1:
                detalle += f" Sólo en la primera: {', '.join(f'{a} ({b})' for a, b in solo1)}."
            if solo2:
                detalle += f" Sólo en la segunda: {', '.join(f'{a} ({b})' for a, b in solo2)}."
        casos[10] = B.caso(f1 == f2, detalle)

    # 11 — naturaleza de la prórroga                          [salida real 28/08]
    #
    # El módulo publica una casilla «Prórroga tácita» de sí/no. El documento
    # distingue tres cosas, y las dos primeras son opuestas: con prórroga tácita
    # no hacer nada renueva el contrato; con prórroga expresa no hacer nada lo
    # extingue. Marcar la casilla equivocada no es un matiz, es invertir el
    # consejo que la ficha le da a quien la lee.
    #
    # Sólo se exige donde el evaluador puede sostenerlo con la cláusula literal:
    # si su propia lectura sale «no consta», el caso no acusa.
    comparables_pr = [
        (e, por_id[e["id_documento"]]) for e in esperados
        if e["id_documento"] in por_id
        and e["campos"].get("prorroga_tipo") in ("tacita", "expresa", "renunciada")
        and por_id[e["id_documento"]].get("prorroga_tacita") is not None]
    discrepan_pr = [
        (e, r) for e, r in comparables_pr
        if bool(r["prorroga_tacita"]) != (e["campos"]["prorroga_tipo"] == "tacita")]
    casos[11] = B.caso(
        bool(comparables_pr) and not discrepan_pr,
        (f"{len(comparables_pr)} documento(s) con prórroga declarada por las dos "
         f"partes y coincidencia en los {len(comparables_pr)}."
         if not discrepan_pr else
         "Discrepa: " + "; ".join(
             f"{e['id_documento']} — el módulo marca prórroga tácita "
             f"{'sí' if r['prorroga_tacita'] else 'no'} y la cláusula dice "
             f"{PRORROGAS[e['campos']['prorroga_tipo']].lower()}"
             + (f" («{(e['campos'].get('cita_prorroga_tipo') or '')[:200]}…»)"
                if e["campos"].get("cita_prorroga_tipo") else "")
             for e, r in discrepan_pr[:3]))
        if comparables_pr else
        "Ningún documento permite comparar la naturaleza de la prórroga: o el "
        "módulo no la declara, o la cláusula no es concluyente.",
        omitir=not comparables_pr,
        requiere=("un documento cuya cláusula de prórroga sea concluyente y cuya "
                  "ficha declare el campo de prórroga tácita"),
        evidencia=[{"documento": e["id_documento"],
                    "cláusula": (e["campos"].get("cita_prorroga_tipo") or "")[:300],
                    "lee el evaluador": PRORROGAS[e["campos"]["prorroga_tipo"]],
                    "declara el módulo": ("Tácita" if r["prorroga_tacita"]
                                          else "No tácita")}
                   for e, r in discrepan_pr[:4]] or None)

    # 12 — fecha crítica de aviso                             [salida real 28/08]
    #
    # Es el único campo accionable de la ficha: el vencimiento dice cuándo acaba,
    # la fecha crítica dice cuándo hay que moverse. Y es una resta, así que se
    # exige siempre que el módulo tenga los dos sumandos.
    exigibles_fc = [(e, por_id[e["id_documento"]]) for e in esperados
                    if e["id_documento"] in por_id
                    and e["campos"].get("fecha_critica")]
    sin_fc = [(e, r) for e, r in exigibles_fc if not r.get("fecha_critica")]
    mal_fc = []
    for e, r in exigibles_fc:
        f = fecha_de(r.get("fecha_critica")) if r.get("fecha_critica") else None
        if f and f != e["campos"]["fecha_critica"]:
            mal_fc.append((e, r, f))
    casos[12] = B.caso(
        bool(exigibles_fc) and not sin_fc and not mal_fc,
        (f"{len(exigibles_fc)} documento(s) con fecha crítica correcta."
         if not sin_fc and not mal_fc else
         ((f"Sin fecha crítica teniendo vencimiento y plazo de preaviso: "
           + "; ".join(
               f"{e['id_documento']} vence el "
               f"{e['campos']['fecha_caducidad'].strftime('%d/%m/%Y')} con "
               f"{e['campos']['antelacion']['cantidad']} "
               f"{e['campos']['antelacion']['unidad']} de antelación, luego la "
               f"fecha crítica es el "
               f"{e['campos']['fecha_critica'].strftime('%d/%m/%Y')}"
               for e, r in sin_fc[:3]) + ". ") if sin_fc else "")
         + ("Fecha crítica distinta de la que sale de la cláusula: " + "; ".join(
             f"{e['id_documento']} declara {f.strftime('%d/%m/%Y')} y la cláusula "
             f"da {e['campos']['fecha_critica'].strftime('%d/%m/%Y')}"
             for e, r, f in mal_fc[:3]) + "." if mal_fc else ""))
        if exigibles_fc else
        "Ningún documento fija un plazo de preaviso del que derivar la fecha crítica.",
        omitir=not exigibles_fc,
        requiere=("un documento con cláusula de preaviso y fecha de vencimiento, "
                  "que son los dos datos de los que sale la fecha crítica"))

    # Integridad del escaneo — hallazgo, ya no caso (ver la nota junto a CASOS).
    escaneos_incompletos = [e for e in esperados + abstenidos
                            if (e.get("integridad") or {}).get("completo") is False]

    _desglosar(casos, esperados, estados, eventos, contraste, por_id,
               fecha_evaluacion, ventana_dias, contexto, repeticion)

    # --- Hallazgos de cobertura
    hallazgos = []

    if abstenidos:
        hallazgos.append(B.hallazgo(
            "El evaluador se abstiene sobre "
            + (f"{len(abstenidos)} documento(s)" if len(abstenidos) > 1
               else "un documento") + ": no ha sabido leerlos",
            "; ".join(f"{e['id_documento']} — {e['motivo']}" for e in abstenidos[:3]),
            "No entran en el contraste ni cuentan como fallo del módulo. La "
            "extracción determinista es un conjunto de patrones sobre el texto, y "
            "sobre el OCR de una escritura mecanografiada de hace treinta años los "
            "patrones no llegan: el reconocimiento devuelve «cuatroúe abril» y "
            "pierde el año. Convertir esa ceguera en un suspenso sería exactamente "
            "lo que este sistema le reprocha a los módulos que evalúa. Para "
            "cerrarlos hay dos vías: **el modo asistido**, donde un modelo lee el "
            "texto reconocido y rellena los mismos campos —sin decidir el estado, "
            "que lo sigue decidiendo la regla— o confirmar los campos a mano.",
            [{"documento": e["id_documento"],
              "tipo": TIPOS.get(e["tipo"], e["tipo"]),
              "lo que declara el módulo":
                  ESTADOS.get((por_id.get(e["id_documento"]) or {}).get("estado"), "—"),
              "lo que ha podido leer el evaluador":
                  ", ".join(f"{k}={v}" for k, v in (
                      ("firma", e["campos"]["fecha_emision"]),
                      ("inicio", e["campos"]["fecha_inicio"]),
                      ("plazo", e["campos"]["anios_pactados"])) if v) or "nada"}
             for e in abstenidos[:6]]))

    difusos = [e for e in esperados
               if (por_id.get(e["id_documento"]) or {}).get("estado") == "obsoleto"
               and e["estado"] == "caducado"]
    if difusos:
        hallazgos.append(B.hallazgo(
            "«Obsoleto» tapa dos situaciones distintas",
            "En " + _lista([e["id_documento"] for e in difusos]) + " el módulo "
            "declara «Obsoleto» y lo que sostienen los documentos es que **venció "
            "el plazo**, no que exista una versión posterior que los sustituya. Se "
            "cuenta como acierto —lo que afirma es cierto— pero el estado no "
            "distingue las dos cosas.",
            "Aguas abajo son decisiones opuestas: un documento vencido obliga a "
            "renovarlo, uno sustituido obliga a ir a la versión nueva y no renovar "
            "nada. Con dos estados —«Vigente» y «Obsoleto»— la distinción no cabe, "
            "y es la misma que pide el caso 5. No es un fallo de clasificación: es "
            "una etiqueta que agrupa más de lo que el destinatario necesita "
            "separar. Basta con un motivo junto al estado; no hace falta cambiar "
            "el vocabulario.",
            [{"documento": e["id_documento"],
              "declara el módulo": "Obsoleto",
              "sostiene el documento": ESTADOS[e["estado"]],
              "por qué": e["motivo"][:160]} for e in difusos[:4]]))

    if escaneos_incompletos:
        hallazgos.append(B.hallazgo(
            "Hay escaneos incompletos, y el módulo no lo advierte",
            "; ".join(
                f"{e['id_documento']} — el pie del documento dice «Página N de "
                f"{e['integridad']['paginas_declaradas']}», el fichero tiene "
                f"{e['integridad']['paginas_fichero']} y faltan la(s) "
                f"{', '.join(str(n) for n in e['integridad']['faltantes'])}"
                for e in escaneos_incompletos[:3]),
            "No puntúa, y conviene decir por qué: el módulo clasifica **vigencia**, "
            "y la vigencia la decide la cláusula de duración. Mientras esa cláusula "
            "esté, el estado que emite es correcto aunque al escaneo le falten "
            "hojas — suspenderle por esto sería medirle por un trabajo que no es el "
            "suyo, y el que digitalizó el expediente no es él. Se registra porque "
            "el riesgo aguas abajo existe igual: «se puede usar como referencia "
            "válida» sobre un documento al que le falta una quinta parte del texto "
            "es una afirmación que nadie ha comprobado. La comprobación es barata "
            "—el propio pie numera las páginas— y el sitio natural para ponerla es "
            "quien digitaliza, no quien clasifica.",
            [{"documento": e["id_documento"],
              "páginas que declara el documento": e["integridad"]["paginas_declaradas"],
              "páginas del fichero": e["integridad"]["paginas_fichero"],
              "faltan": ", ".join(str(n) for n in e["integridad"]["faltantes"])}
             for e in escaneos_incompletos[:6]]))

    if renombres:
        hallazgos.append(B.hallazgo(
            "El módulo identifica los documentos por la ruta de un disco local",
            "La salida nombra cada documento por el fichero que tiene el módulo en "
            "su máquina —" + "; ".join(f"«{a}» frente a «{b}»" for a, b in renombres[:4])
            + "—. El evaluador ha emparejado "
            + ("el documento" if len(renombres) == 1 else f"los {len(renombres)} documentos")
            + " porque en cada caso había un único candidato posible, y lo declara "
              "aquí en vez de hacerlo en silencio.",
            "No es un fallo de clasificación, pero sí del contrato de la conexión: "
            "un identificador que depende de cómo se llame el fichero en el "
            "ordenador de quien lo subió no es estable. Basta con que el mismo "
            "contrato se guarde con otro nombre para que aguas abajo pase por otro "
            "documento. Conviene acordar un identificador propio del documento que "
            "viaje en la salida, y de paso quitar la ruta absoluta "
            "(`C:\\\\Users\\\\…`), que no aporta nada a quien la recibe.",
            [{"lo que dice el módulo": a, "documento al que corresponde": b}
             for a, b in renombres[:6]]))

    por_ocr = [e for e in esperados if e.get("via") == "ocr"]
    if por_ocr:
        hallazgos.append(B.hallazgo(
            "La verdad de campo de estos documentos sale de un OCR, no del PDF",
            f"{len(por_ocr)} de {len(esperados)} documento(s) no tienen capa de "
            f"texto: son fotocopias. El evaluador los ha reconocido por OCR para "
            f"poder decir algo de ellos — antes quedaban todos pendientes — pero "
            f"lo que compara es una lectura suya contra una lectura del módulo.",
            "Importa para leer los fallos de esta evaluación con la reserva "
            "correcta: una discrepancia sobre una fecha o una cifra no demuestra "
            "por sí sola que el módulo se equivoque, porque puede haberse "
            "equivocado el reconocimiento. Los casos que **no** dependen del OCR "
            "—que el módulo publique un campo, que la resta cuadre, que el número "
            "de páginas coincida— sí se sostienen enteros. Cuando la discrepancia "
            "es sobre una cláusula, el veredicto cita el fragmento literal "
            "reconocido para que se pueda contrastar contra el papel.",
            [{"documento": e["id_documento"], "vía": "OCR",
              "páginas": (e.get("integridad") or {}).get("paginas_fichero")}
             for e in por_ocr[:6]]))

    if descuadres:
        hallazgos.append(B.hallazgo(
            "Hay documentos que se contradicen a sí mismos",
            f"En {len(descuadres)} documento(s), la duración pactada no cuadra con la "
            f"fecha de finalización que el propio documento declara.",
            "El contraste externo dice que dos documentos no coinciden; el contraste "
            "interno dice cuál de los dos valores es el correcto, y sigue funcionando "
            "aunque no haya ningún otro documento con el que comparar.",
            descuadres))

    tabla = [{"Documento": e["id_documento"]
                          + ("  ·  el evaluador se abstiene" if e.get("abstiene") else ""),
              "Cadena documental": e["cadena"] or "—",
              "Vence": e["fecha_caducidad"].strftime("%d/%m/%Y")
                       if e["fecha_caducidad"] else "—",
              "Estado que sostienen los documentos": ESTADOS[e["estado"]],
              "Estado declarado por el módulo":
                  ESTADOS.get((por_id.get(e["id_documento"]) or {}).get("estado"), "—"),
              "Resuelto": ("abstención" if e.get("abstiene")
                           else C.estado_de(e, contraste, ETIQUETAS_TABLA))}
             for e in esperados + abstenidos]

    return {"esperados": esperados, "abstenidos": abstenidos,
            "reportados": estados, "eventos": eventos,
            "contraste": contraste, "casos": casos, "hallazgos": hallazgos,
            "tabla_contraste": tabla, "fecha_evaluacion": fecha_evaluacion,
            "ventana_dias": ventana_dias, "modo_lectura": modo_lectura}


# --- Traducción a la tabla corregible de la interfaz -----------------------
# La interfaz enseña lo que ha entendido y deja corregir celda a celda antes de
# puntuar: el módulo no debe salir penalizado por un fallo de lectura mío.

_INV_ESTADOS = {v: k for k, v in ESTADOS.items()}


def a_fila(r):
    return {"Documento": r["id_documento"],
            "Estado declarado": ESTADOS.get(r["estado"], "—"),
            "Fecha de vencimiento citada": r.get("fecha_caducidad") or "",
            "Versión que sustituye": r.get("sustituye_a") or "",
            "Cita la cláusula": bool(r.get("cita"))}


def de_fila(f):
    return {"tipo": "estado", "id_documento": _normalizar_id(f["Documento"]),
            "estado": _INV_ESTADOS.get(str(f["Estado declarado"])),
            "fecha_caducidad": str(f["Fecha de vencimiento citada"]).strip() or None,
            "sustituye_a": str(f["Versión que sustituye"]).strip() or None,
            "cita": bool(f["Cita la cláusula"]), "evento": None, "fecha_evento": None,
            "preaviso_dias": None, "dias": None, "fecha_emision": None, "texto": ""}


def sujeto(esperados):
    return (f"el conjunto de {len(esperados)} documento"
            f"{'s' if len(esperados) != 1 else ''} aportado"
            f"{'s' if len(esperados) != 1 else ''}")
