"""
Registro de ramas. Añadir un módulo al sistema es escribir su fichero y una línea
aquí: la interfaz se construye sola a partir de este registro.

Están los cinco módulos del proyecto, no sólo aquellos con los que he avanzado.
`operativo` distingue la rama que puede evaluar hoy de la que sólo está declarada,
y una rama puede estar declarada incluso sin batería. Es la misma disciplina de la
batería aplicada al propio sistema: lo diseñado no se cuenta como ejecutado, ni
siquiera cuando lo diseñado es mío. Un módulo que no aparece en el mapa se lee como
un módulo que no existe.
"""

from . import auditoria, contradicciones, gobernanza, similitud, vigencia

# El orden es el de la cadena de valor, no el de mi avance: de los documentos de
# un pedido hacia la gobernanza del conjunto.
RAMAS = [auditoria, vigencia, similitud, contradicciones, gobernanza]

REGISTRO = {r.FICHA["id"]: r for r in RAMAS}


def fichas():
    return [r.FICHA for r in RAMAS]


def rama(id_modulo):
    return REGISTRO.get(id_modulo)


def operativas():
    return [r for r in RAMAS if r.FICHA.get("operativo")]


def con_bateria():
    return [r for r in RAMAS if r.FICHA.get("casos")]


# Estados de conexión, tal como los fijó Fabián. «Probada» significa que un dato
# real ha recorrido el sistema de extremo a extremo, no que yo haya mirado los
# datos a mano. Quién verifica es siempre el consumidor: ese fue el malentendido
# de la semana del 18 de agosto — los productores ya habían entregado y daban su
# parte por hecha, pero nadie tenía asignado probar.
ESTADOS_CONEXION = {
    "probada": ("Probada", "#0ca30c", "Un dato real ha recorrido el sistema de "
                                      "extremo a extremo."),
    "documentada": ("Documentada", "#2a78d6", "El acuerdo está escrito y los datos "
                                              "recibidos; falta recorrerla."),
    "sin documentar": ("Sin documentar", "#898781", "No hay acuerdo escrito todavía."),
}
