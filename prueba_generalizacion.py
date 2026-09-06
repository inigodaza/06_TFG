"""
¿Aguantan las cuatro ramas una entrada que nadie ha visto antes?

Por qué existe
--------------
`pruebas.py` comprueba que el evaluador hace lo que dice sobre las entradas
conocidas. Eso no responde a la pregunta que se hizo Íñigo metiendo dos órdenes
nuevas en el módulo de Juan: **¿y cuando le llega algo distinto?**

Un evaluador puede fallar ahí de tres formas, y sólo una es aceptable:

  1. **Se rompe.** Inaceptable: una excepción en pantalla no es un veredicto.
  2. **Acusa al compañero de su propia ceguera.** El peor de los tres, porque el
     resultado parece un hallazgo. Es el fallo que este bloque entero existe para
     no cometer.
  3. **Declara que no puede.** Correcto. «No se ha podido comprobar» no es «sin
     incidencias», y decirlo es hacer el trabajo, no rehuirlo.

Este guion mete por cada rama entradas que el sistema no ha visto —documentos con
otra redacción, exportaciones incompletas, ficheros corruptos, salidas vacías— y
comprueba las tres cosas.

    python3 prueba_generalizacion.py
"""

import json
import sys
import traceback
from datetime import date

import modulos
from nucleo import clasificacion as CLAS
from nucleo import llm

FECHA = date(2026, 9, 1)
fallos = []
ok = 0


def comprobar(cierto, titulo, detalle=""):
    global ok
    if cierto:
        ok += 1
        print(f"  OK    {titulo}")
    else:
        fallos.append(titulo)
        print(f"  FALLA {titulo}" + (f"  — {detalle}" if detalle else ""))


def sin_romperse(titulo, fn, *a, **k):
    """Ejecuta y comprueba que no lanza. Devuelve (ok, resultado o excepción)."""
    try:
        r = fn(*a, **k)
        comprobar(True, titulo)
        return True, r
    except Exception as e:                              # noqa: BLE001
        comprobar(False, titulo, f"{type(e).__name__}: {e}")
        traceback.print_exc(limit=2)
        return False, e


# ===========================================================================
print("\n1 · Juan · documentos con otra redacción")
# ===========================================================================
from modulos import auditoria as AUD

NUEVOS = [
    ("O.F. Nº 42463\nTirada: 5.000 ejemplares\nEncuadernación: rústica\n"
     "Formato: 210 x 297\nGramaje interior 90", "orden"),
    ("PURCHASE ORDER\nWe hereby order 5000 copies\nExtent: 128 pp\n"
     "Binding: cased\nDelivery date: 3 October", "pedido_cliente"),
    ("QUOTATION\nRef: 9780717195473\nUnit price: 1.85\nValid until 31 December",
     "presupuesto"),
    ("Plano de montaje de la máquina 4. Esquema eléctrico, revisión B.",
     "desconocido"),
]
for texto, esperado in NUEVOS:
    comprobar(AUD.clasificar(texto) == esperado,
              f"Se identifica «{texto.splitlines()[0][:38]}» como {esperado}",
              AUD.clasificar(texto))

# Una orden nueva más un pedido nuevo: el contraste tiene que poder ejecutarse.
docs_nuevos = [
    {"nombre": "of_nueva.pdf", "legible": True, "capa": True, "texto": NUEVOS[0][0]},
    {"nombre": "pedido_nuevo.pdf", "legible": True, "capa": True,
     "texto": NUEVOS[1][0]},
]
bien, r = sin_romperse("Una orden y un pedido que el sistema no ha visto nunca "
                       "producen un contraste sin romper nada",
                       AUD.verdad_de_campo, docs_nuevos)
if bien:
    esperados, ctx = r
    comprobar(True, f"…y salen {len(esperados)} discrepancia(s) derivadas de los "
                    f"documentos")

# Y lo que falta se dice con los documentos delante.
try:
    AUD.verdad_de_campo([docs_nuevos[0]])
    comprobar(False, "Una orden sola no puede producir un caso")
except ValueError as e:
    comprobar("of_nueva.pdf" in str(e),
              "Con una orden sola, el mensaje nombra lo que sí se ha leído")


# ===========================================================================
print("\n2 · Martín · documentos con formas de fecha nuevas")
# ===========================================================================
from modulos import vigencia as VIG

REDACCIONES = [
    ("En Zaragoza, a 27 de Enero de dos mil dieciséis, por plazo de QUINCE AÑOS, "
     "terminando el 26 de Enero de dos mil treinta.", "fecha_emision",
     date(2016, 1, 27)),
    ("El plazo comenzará el uno de enero de 2.020 y la duración será de DIEZ "
     "AÑOS.", "fecha_inicio", date(2020, 1, 1)),
    ("Firmado el 3 de marzo de 2.018. El contrato finalizará el 3 de marzo de "
     "2.028.", "fecha_caducidad", date(2028, 3, 3)),
]
for texto, campo, esperado in REDACCIONES:
    c = VIG.extraer(texto)
    comprobar(c.get(campo) == esperado,
              f"Se lee {campo} de una redacción nueva", str(c.get(campo)))

# Un documento ilegible no produce «sin incidencias»: produce abstención.
doc_ilegible = {"nombre": "roto.pdf", "id": "roto", "legible": False,
                "capa": False, "via": "ninguna", "texto": "", "paginas": 2,
                "integridad": {}}
bien, r = sin_romperse("Un documento que no se ha podido leer no rompe la rama",
                       VIG.verdad_de_campo, [doc_ilegible], FECHA)
if bien:
    esperados, _ = r
    comprobar(esperados[0].get("abstiene") is True,
              "…y el evaluador se abstiene sobre él en vez de juzgarlo")
    comprobar("no ha podido leerse" in (esperados[0].get("motivo") or ""),
              "…diciendo que el problema es de lectura, no del módulo",
              str(esperados[0].get("motivo"))[:70])


# ===========================================================================
print("\n3 · Álvaro y Mencía · exportaciones distintas")
# ===========================================================================
from modulos import contradicciones as CON
from modulos import similitud as SIM

ENTRADAS = [("vacía", ""), ("no es JSON", "{{{"), ("lista", "[1,2]"),
            ("objeto vacío", "{}"),
            ("tablas con otro nombre", json.dumps({"cosas": []})),
            ("nulos donde iban listas",
             json.dumps({"document_group": None, "extracted_facts": None,
                         "contradictions": None}))]
for rama, fn in (("Mencía", CON.interpretar), ("Álvaro", SIM.interpretar)):
    for nombre, txt in ENTRADAS:
        bien, r = sin_romperse(f"{rama}: exportación {nombre}", fn, txt)
        if bien and txt.strip() in ("", "{{{", "[1,2]"):
            _d, _av = r
            comprobar(bool(_av), f"{rama}: …y se explica por qué no vale")

# El camino completo de Mencía sobre una exportación degenerada.
DEGENERADA = json.dumps({"document_group": [{"id": 1, "group_key": "X"}],
                         "extracted_facts": [{"id": 1}, {"id": 2}],
                         "contradictions": []})
datos, avisos = CON.interpretar(DEGENERADA)
esperados, ctx = CON.verdad_de_campo(datos)
ev = CON.evaluar(esperados, ctx, None)
comprobar(not any(c["resultado"] == "pasa" for c in ev["casos"].values()),
          "Ningún caso se da por superado sobre hechos vacíos")
comprobar(any("sin campo o sin valor" in a for a in avisos),
          "…y se dice que los hechos llegaron incompletos")


# ===========================================================================
print("\n4 · El veto de IA, por todos los caminos")
# ===========================================================================
fugas = []
_gen, _disp, _clave = llm._generar, llm.esta_disponible, llm._CLAVE
try:
    def espia(*a, **k):
        fugas.append(a)
        raise AssertionError("salida al proveedor")
    llm._generar = espia
    llm.esta_disponible = lambda: True
    llm._CLAVE = "de-mentira"

    for m in modulos.RAMAS:
        f = m.FICHA
        if f.get("ia_permitida"):
            continue
        antes = len(fugas)
        docs = [{"nombre": "x.pdf", "legible": True, "capa": True,
                 "texto": "Documento con datos de cliente que no debe salir. "
                          "Referencia interna y condiciones acordadas."}]
        CLAS.anotar_tipos(docs, getattr(m, "clasificar", lambda t: "desconocido"),
                          getattr(m, "TIPOS", {}), "asistido",
                          permiso=llm.permiso_de(f))
        comprobar(len(fugas) == antes,
                  f"{f['id']}: con la IA cerrada no sale nada hacia el proveedor "
                  f"ni pidiendo modo asistido")
finally:
    llm._generar, llm.esta_disponible, llm._CLAVE = _gen, _disp, _clave

comprobar(not fugas, "Ninguna rama vetada ha llegado al proveedor en toda la "
                     "prueba", f"{len(fugas)} salida(s)")


# ===========================================================================
print("\n" + ("Todas las ramas aguantan." if not fallos else
              f"{len(fallos)} comprobación(es) fallida(s):\n  - "
              + "\n  - ".join(fallos)))
print(f"{ok} comprobaciones en verde.")
sys.exit(1 if fallos else 0)
