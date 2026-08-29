"""
Rama de evaluación del módulo de ONTOLOGÍA Y GRAFO ORGANIZATIVO
— Pablo Morillas · MAIO Legal.

DECLARADA Y VACÍA. No hay batería, ni datos, ni conexión documentada conmigo.
Está aquí precisamente por eso: el sistema tiene que enseñar los cinco módulos
del proyecto, no sólo aquellos con los que he avanzado. Un módulo que no aparece
en el mapa se lee como un módulo que no existe, y el de Pablo existe.

Es el mismo criterio que aplico a las baterías, aplicado al propio sistema:
  · no operativo   — no puede evaluar
  · sin batería    — ni siquiera está diseñada
Ninguna de las dos cosas se disimula.

Qué hace el módulo evaluado, hasta donde sé: modela las entidades de la
organización —sociedades, inmuebles, personas, documentos— y las relaciones
entre ellas en un grafo, con la capa de permisos encima. Es el módulo que da
vocabulario común al resto: si dos módulos llaman de forma distinta a la misma
entidad, es aquí donde se resuelve.

Qué haría falta para abrir esta rama, por orden:

  1. Saber qué emite: ¿un grafo consultable, un fichero de ontología, una API?
  2. Una salida real sobre entidades que yo pueda verificar por mi cuenta —
     las mismas sociedades y direcciones que ya aparecen en los documentos de
     Martín servirían, y de paso probaría la conexión entre los dos.
  3. Documentar la conexión con mi bloque, que hoy no existe.

Mientras tanto no invento casos. Una batería escrita sin haber visto una salida
sería exactamente el error que le estoy midiendo a los demás: dar por hecho algo
que no se ha comprobado.
"""

CASOS = {}
ASPECTOS = {}

FICHA = {
    "id": "gobernanza",
    "nombre": "Ontología y grafo organizativo",
    "responsable": "Pablo Morillas",
    "empresa": "MAIO Legal",
    "conexion": "Pablo → Evaluación y Calidad · sin documentar",
    "estado_conexion": "sin documentar",
    "verifica": "Íñigo Daza",
    "operativo": False,
    "unidad": ("entidad", "las entidades del grafo"),
    "funcion": ("Modela entidades, relaciones y permisos de la organización en un "
                "grafo, y da vocabulario común al resto de módulos."),
    "entrada": "Por determinar: depende de en qué formato exponga el grafo.",
    "entrada_respuesta": "Por determinar.",
    "casos": CASOS,
    "aspectos": ASPECTOS,
    "pendiente": (
        "Sin batería diseñada y sin datos. No he avanzado con este módulo y no hay "
        "conexión documentada con mi bloque. Aparece en el sistema porque forma "
        "parte del proyecto: omitirlo lo haría desaparecer del mapa."
    ),
    "siguiente_paso": (
        "Saber qué emite el módulo y conseguir una salida real que yo pueda "
        "verificar por mi cuenta. Las sociedades y direcciones de los contratos de "
        "Martín servirían de banco de pruebas y probarían de paso la conexión "
        "entre los dos módulos."
    ),
}
