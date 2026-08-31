"""
Comprobación del evaluador desde la línea de órdenes: `python pruebas.py`.

No prueba los módulos de mis compañeros. Prueba el evaluador: que la verdad de
campo que calcula sobre documentos conocidos es la que corresponde, y que
reacciona como debe cuando la salida del módulo se altera a propósito.

Es la respuesta a la frase de Fabián: un validador que sólo aprueba no está
demostrado; hay que comprobar que también rechaza.
"""

import json as json_mod
import pathlib
import sys
from datetime import date

from demo import guion
from modulos import vigencia
from nucleo import veredicto as V
from nucleo import VERSION as VERSION_NUCLEO

FECHA = date(2026, 8, 19)

# Estado que corresponde a cada documento de prueba de Martín en la fecha de
# evaluación, deducido de sus cláusulas a mano y por escrito antes de ejecutar
# nada. Si el evaluador no coincide con esta tabla, el fallo es del evaluador.
ESPERADO = {
    "PRUEBA_1": ("vigente", "arrendamiento de 15 años que vence el 01/03/2039"),
    "PRUEBA_2": ("caducado", "venció el 16/08/2026, tres días antes, y renuncia "
                             "expresamente a la prórroga tácita"),
    "PRUEBA_3": ("caducado", "venció el 31/12/2023 con renuncia a la tácita "
                             "reconducción"),
    "PRUEBA_4": ("titulo_consumado", "aportación económica ya abonada y obra "
                                     "recepcionada: no hay plazo que vencer"),
    "PRUEBA_5": ("no_clasificado", "plantilla sin cumplimentar: no hay fecha de "
                                   "firma ni duración"),
    "PRUEBA_6": ("caducado", "venció el 01/07/2026 con renuncia expresa a la tácita "
                             "reconducción"),
}

fallos = []


def comprobar(condicion, titulo, detalle=""):
    print(f"  {'OK  ' if condicion else 'FALLA'}  {titulo}"
          + (f"  — {detalle}" if detalle and not condicion else ""))
    if not condicion:
        fallos.append(titulo)


def alterar(registros, ident, **cambios):
    """
    Cambia un registro **por identificador**, no por posición.

    Estaba por posición hasta que la carpeta de vigencia dejó de contener sólo
    los seis contratos sintéticos: al añadir el contrato real de Martín, que
    ordena antes, `alterada[1]` pasó a apuntar a otro documento y tres
    comprobaciones empezaron a fallar sin que nada de lo que medían hubiera
    cambiado. Un banco de pruebas frágil al orden de un `glob` mide el `glob`.
    """
    salida = []
    for r in registros:
        salida.append(dict(r, **cambios) if r["id_documento"] == ident else dict(r))
    assert any(r["id_documento"] == ident for r in registros), ident
    return salida


def perfecta_de(esperados):
    return [{"tipo": "estado", "id_documento": e["id_documento"], "estado": e["estado"],
             "fecha_caducidad": e["fecha_caducidad"].strftime("%d/%m/%Y")
                                if e["fecha_caducidad"] else None,
             "sustituye_a": e["sustituido_por"], "cita": True} for e in esperados]


# ---------------------------------------------------------------------------
print("\n1 · Verdad de campo sobre los seis documentos de Martín")
docs = guion.documentos_de("vigencia")
if not docs:
    print("  No hay documentos en demo/datos/vigencia/. Nada que comprobar.")
    sys.exit(1)

esperados, ctx = vigencia.verdad_de_campo(docs, FECHA)
por_id = {e["id_documento"]: e for e in esperados}

for ident, (estado, razon) in ESPERADO.items():
    e = por_id.get(ident)
    comprobar(e is not None and e["estado"] == estado, f"{ident} → {estado}",
              f"el evaluador dice {e['estado'] if e else 'nada'}; se esperaba {estado} "
              f"porque es un {razon}")

con_cadena = [e for e in esperados if e["cadena"]]
comprobar(len(con_cadena) >= 5,
          "Se extrae la cadena documental (dirección normalizada) de los contratos",
          "; ".join(f"{e['id_documento']}: {e['cadena']}" for e in esperados))

# ---------------------------------------------------------------------------
print("\n2 · Reacción ante una salida perfecta")
perfecta = perfecta_de(esperados)
ev = vigencia.evaluar(esperados, perfecta, FECHA, contexto=ctx)
c = ev["contraste"]
comprobar(c["exhaustividad"] == 100.0, "Exhaustividad 100 %", str(c["exhaustividad"]))
comprobar(c["precision"] == 100.0, "Precisión 100 %", str(c["precision"]))
comprobar(ev["casos"][1]["resultado"] == "pasa", "Caso 1 superado",
          ev["casos"][1]["observacion"])
comprobar(ev["casos"][3]["resultado"] == "pasa", "Caso 3 superado (fechas exactas)",
          ev["casos"][3]["observacion"])
comprobar(ev["casos"][8]["resultado"] == "pasa",
          "Caso 8 superado (nada declarado vigente sin plazo)",
          ev["casos"][8]["observacion"])
comprobar(ev["casos"][9]["resultado"] == "pasa", "Caso 9 superado (cobertura)")

# ---------------------------------------------------------------------------
print("\n3 · Reacción cuando la salida se altera a propósito")

alterada = alterar(perfecta, "PRUEBA_2", estado="vigente")   # PRUEBA_2 sí caducó
ev2 = vigencia.evaluar(esperados, alterada, FECHA, contexto=ctx)
comprobar(ev2["contraste"]["exhaustividad"] < 100,
          "Declarar vigente un contrato vencido baja la exhaustividad",
          str(ev2["contraste"]["exhaustividad"]))
comprobar(ev2["casos"][1]["resultado"] == "no_pasa", "El caso 1 deja de superarse")

sin_plazo = [dict(r) for r in perfecta]
for r in sin_plazo:
    if r["id_documento"] == "PRUEBA_5":
        r["estado"] = "vigente"                        # vigencia indefinida por defecto
ev3 = vigencia.evaluar(esperados, sin_plazo, FECHA, contexto=ctx)
comprobar(ev3["casos"][8]["resultado"] == "no_pasa",
          "Declarar vigente un documento sin plazo no pasa el caso 8",
          ev3["casos"][8]["observacion"])

inventada_fecha = [dict(r) for r in perfecta]
for r in inventada_fecha:
    if r["id_documento"] == "PRUEBA_4":
        r["fecha_caducidad"] = "31/12/2030"            # fecha que no consta
ev3b = vigencia.evaluar(esperados, inventada_fecha, FECHA, contexto=ctx)
comprobar(ev3b["casos"][8]["resultado"] == "no_pasa",
          "Inventar una fecha de caducidad no pasa el caso 8",
          ev3b["casos"][8]["observacion"])

mala_fecha = alterar(perfecta, "PRUEBA_1", fecha_caducidad="01/03/2038")
ev3c = vigencia.evaluar(esperados, mala_fecha, FECHA, contexto=ctx)
comprobar(ev3c["casos"][3]["resultado"] == "no_pasa",
          "Devolver una fecha de caducidad equivocada no pasa el caso 3")
comprobar(ev3c["contraste"]["exhaustividad"] < 100,
          "Y además no cuenta como acierto, aunque el estado sea correcto")

inventada = perfecta + [{"tipo": "estado", "id_documento": "PRUEBA_9",
                         "estado": "vigente", "fecha_caducidad": None, "cita": True}]
ev5 = vigencia.evaluar(esperados, inventada, FECHA, contexto=ctx)
comprobar(ev5["contraste"]["precision"] < 100,
          "Un documento que no se entregó baja la precisión",
          str(ev5["contraste"]["precision"]))

incompleta = [r for r in perfecta if r["id_documento"] != "PRUEBA_3"]
ev6 = vigencia.evaluar(esperados, incompleta, FECHA, contexto=ctx)
comprobar(ev6["casos"][9]["resultado"] == "no_pasa",
          "Dejar un documento sin clasificar no pasa el caso de cobertura")

ev8 = vigencia.evaluar(esperados, perfecta, FECHA, repeticion=alterada, contexto=ctx)
comprobar(ev8["casos"][10]["resultado"] == "no_pasa",
          "Dos ejecuciones que no coinciden no pasan el caso de repetibilidad")
ev9 = vigencia.evaluar(esperados, perfecta, FECHA, repeticion=perfecta, contexto=ctx)
comprobar(ev9["casos"][10]["resultado"] == "pasa",
          "Dos ejecuciones idénticas sí lo pasan")

# El caso 5 dejó de ser «no aplica» el 29/08, y no porque cambiara el banco: al
# normalizar el identificador de carretera —«CR A-2», «CR-A2» y «CR A2» eran tres
# huellas distintas para la misma estación— el contrato de Calatorao y su anexo
# de 2019 cayeron por fin en la misma cadena documental. El caso que Fabián
# corrigió expresamente, y que llevaba desde el principio sin poderse ejercitar,
# ya tiene dos versiones del mismo inmueble que contrastar.
_cadenas = {}
for _e in esperados:
    if _e["cadena"]:
        _cadenas.setdefault(_e["cadena"], []).append(_e["id_documento"])
_con_varias = {k: v for k, v in _cadenas.items() if len(v) > 1}
comprobar(bool(_con_varias),
          "El caso 5 es ejercitable: hay dos documentos del mismo inmueble en la "
          "misma cadena documental",
          "; ".join(f"{k}: {', '.join(v)}" for k, v in _con_varias.items())[:150])
comprobar(ev["casos"][5]["resultado"] in ("pasa", "no_pasa"),
          "…y por tanto el caso 5 se juzga en vez de declararse no aplicable",
          ev["casos"][5]["resultado"])

# ---------------------------------------------------------------------------
print("\n4 · Pendiente y no aplicable son cosas distintas")
# Pendiente: el caso aplica a estos datos y falta algo que puedo conseguir sin
# cambiar de conjunto.
for n, titulo in ((2, "ventana de vencimientos, falta pegar la consulta"),
                  (7, "aviso anticipado, faltan las alertas"),
                  (10, "repetibilidad, falta la segunda ejecución")):
    comprobar(ev["casos"][n]["resultado"] == "pendiente",
              f"Caso {n} pendiente ({titulo})", ev["casos"][n]["observacion"])

# No aplica: el conjunto no contiene la situación que el caso mide.
for n, titulo in ((4, "no hay ningún documento con las fechas invertidas"),
                  (6, "ningún documento vence en la fecha de consulta")):
    comprobar(ev["casos"][n]["resultado"] == "no_aplica",
              f"Caso {n} no aplica ({titulo})", ev["casos"][n]["observacion"])

# El 5 sale de esta lista: ya no es un caso sin ejercitar que declare qué le
# falta, es un caso que se juzga.
comprobar(all(ev["casos"][n].get("requiere")
              for n in (2, 4, 6, 7, 10)),
          "Todo caso pendiente o no aplicable declara qué haría falta",
          str({n: ev["casos"][n].get("requiere") for n in (2, 4, 6, 7, 10)}))
comprobar("16/08/2026" in (ev["casos"][6]["requiere"] or ""),
          "El caso 6 dice qué fecha de consulta lo ejercitaría",
          str(ev["casos"][6]["requiere"]))

from nucleo.bateria import requisitos as _req
_pend = [n for n, c in ev["casos"].items()
         if c["resultado"] in ("pendiente", "no_aplica") and c.get("requiere")]
comprobar(len(_req(ev["casos"])) == len(_pend),
          "La lista de requisitos recoge todos los casos sin ejercitar, y sólo esos",
          f"{len(_req(ev['casos']))} requisitos para {len(_pend)} casos")

# ---------------------------------------------------------------------------
print("\n5 · El caso límite, ejercitado moviendo la fecha de consulta")
LIMITE = date(2026, 8, 16)                    # PRUEBA_2 vence exactamente ese día
esp_l, ctx_l = vigencia.verdad_de_campo(docs, LIMITE)
comprobar({e["id_documento"]: e["estado"] for e in esp_l}["PRUEBA_2"] == "vigente",
          "El criterio fijado —vigente el día en que vence— se aplica",
          str({e["id_documento"]: e["estado"] for e in esp_l}))
ev_l = vigencia.evaluar(esp_l, perfecta_de(esp_l), LIMITE, contexto=ctx_l)
comprobar(ev_l["casos"][6]["resultado"] == "pasa",
          "Con un documento que vence ese día, el caso 6 se ejecuta",
          ev_l["casos"][6]["observacion"])
mezcla = perfecta_de(esp_l)
comprobar(ev_l["casos"][2]["resultado"] == "pendiente",
          "El caso 2 sigue pendiente mientras no se peguen los eventos")

# ---------------------------------------------------------------------------
print("\n6 · Lectura de la salida de IAlert en sus cuatro formas")

json_texto = ('[{"id_documento": "PRUEBA_1", "estado": "vigente", '
              '"fecha_caducidad": "01/03/2039", "cita": "Cláusula segunda"}]')
csv_texto = ("id_documento;estado;fecha_caducidad\n"
             "PRUEBA_1;vigente;01/03/2039\nPRUEBA_2;caducado;16/08/2026")

# Ficha de la pantalla de Documentos, tal como aparece en la interfaz
fichas = """Prueba_12
Vigente   Vencimiento del documento (1 día)
El documento se puede usar como referencia válida.
Este documento es un requerimiento de aportación de documentación de la Agencia Estatal de Administración Tributaria para el ejercicio 2025.
Archivo   C:\\Users\\marti\\Documents\\TFG\\Modelo0.1\\Frontend..\\datos
Ciudad    Zaragoza
Dirección Avenida de Madrid, nº 118, bajo

1997 CTO ALQUILER BULL MCCABES
Obsoleto
El documento se puede desechar o conservar como fuente histórica.
Validez formal
Ciudad    Zaragoza
Dirección Calle Cádiz"""

# Panel «Próximos eventos»
eventos_texto = (
    "CRITICO Vencimiento del documento — 2026-08-18 (1 día) — Zaragoza · Prueba_12\n"
    "PROXIMO Fecha límite para avisar de no renovación — 2026-08-31 (14 días) — "
    "preaviso legal: 30 días — Zaragoza · Prueba_7\n"
    "PROXIMO Vencimiento del documento — 2026-09-30 (44 días) — Zaragoza · Prueba_7")

leidos, _ = vigencia.interpretar(json_texto)
comprobar(len(leidos) == 1 and leidos[0]["estado"] == "vigente",
          "Salida en JSON interpretada", str(leidos))

leidos, _ = vigencia.interpretar(csv_texto)
comprobar(len(leidos) == 2 and leidos[1]["estado"] == "caducado",
          "Salida en CSV interpretada", str(leidos))

leidos, avisos = vigencia.interpretar(fichas)
estados = {r["id_documento"]: r["estado"] for r in leidos if r["tipo"] == "estado"}
comprobar(estados.get("PRUEBA_12") == "vigente",
          "Ficha de IAlert: Prueba_12 se lee como vigente", str(estados))
comprobar(estados.get("1997_CTO_ALQUILER_BULL_MCCABES") == "obsoleto",
          "Ficha de IAlert: el contrato de 1997 se lee como obsoleto", str(estados))
comprobar(not any(v == "vigente" for k, v in estados.items()
                  if "1997" in k),
          "«Validez formal» no se confunde con el estado de vigencia", str(estados))

leidos, avisos = vigencia.interpretar(eventos_texto)
eventos = [r for r in leidos if r["tipo"] == "evento"]
comprobar(len(eventos) == 3, "Panel de eventos: se leen las tres líneas",
          str(eventos))
comprobar(any(e["preaviso_dias"] == 30 for e in eventos),
          "Se reconoce el preaviso legal de 30 días", str(eventos))
comprobar(all(e["fecha_evento"] for e in eventos),
          "Cada evento lleva su fecha", str(eventos))
from nucleo.texto import fecha_de as _f
comprobar(_f("2026-08-18") == date(2026, 8, 18),
          "Las fechas ISO de IAlert no se confunden con día/mes/año",
          str(_f("2026-08-18")))
mezclado, _ = vigencia.interpretar(fichas + "\n" + eventos_texto)
comprobar(len([r for r in mezclado if r["tipo"] == "estado"]) == 2,
          "Pegar fichas y eventos juntos no genera estados fantasma",
          str([(r["tipo"], r["id_documento"]) for r in mezclado]))
comprobar(any("PRUEBA_7" == e["id_documento"] for e in eventos),
          "El documento del evento se identifica por el sufijo tras el punto medio",
          str([e["id_documento"] for e in eventos]))

# ---------------------------------------------------------------------------
print("\n7 · La tasa se calcula sólo sobre lo verificado")
er = V.evaluation_result(vigencia.FICHA, ev, vigencia.sujeto(esperados), FECHA)
r = er["resumen"]
comprobar(r["tasa"] == round(100 * r["pasa"] / r["con_evidencia"], 1),
          "La tasa excluye los casos pendientes",
          f"{r['pasa']}/{r['con_evidencia']} → {r['tasa']}")
comprobar(r["pendiente"] > 0 and r["no_aplica"] > 0
          and r["total"] == len(vigencia.CASOS),
          f"Los {len(vigencia.CASOS)} casos están declarados; pendientes y no "
          f"aplicables van aparte",
          str(r))
comprobar(r["cobertura"] == round(100 * r["con_evidencia"] / r["total"], 1),
          "La cobertura dice qué parte de la batería se ha ejercitado",
          f"{r['con_evidencia']}/{r['total']} → {r['cobertura']}")

# ---------------------------------------------------------------------------
print("\n8 · La rama de auditoría reproduce la tabla de prueba de éxito del 42805")
from modulos import auditoria as A

REALES = [
    {"campo": "cantidad", "etiqueta": "Cantidad", "valor_cliente": 3000,
     "valor_orden": 30000, "severidad_esperada": "alta"},
    {"campo": "gramaje_cubierta", "etiqueta": "Gramaje de cubierta",
     "valor_cliente": 240, "valor_orden": 250, "severidad_esperada": "menor"},
]
CTX = {"orden": {"cantidad": 30000, "cantidad_logistica": 3000,
                 "cantidad_impresion": 3000},
       "cliente": {"cantidad": 3000}, "pedido": "of42805",
       "comparables": ["cantidad"], "procedencia": {}}

inc, _ = A.interpretar(A.EJEMPLO)
comprobar(len(inc) == 2, "Se interpretan las dos incidencias del 42805", str(inc))

ev_a = A.evaluar(REALES, inc, CTX, texto_respuesta=A.EJEMPLO, repeticion=inc)
ca = ev_a["contraste"]
comprobar(ca["exhaustividad"] == 100.0 and ca["precision"] == 100.0,
          "Exhaustividad y precisión al 100 % con la respuesta real",
          f"{ca['exhaustividad']} / {ca['precision']}")
comprobar(ev_a["casos"][9]["resultado"] == "pasa",
          "El caso 9 se supera con la evidencia del tablero de GraphyFlow",
          ev_a["casos"][9]["observacion"])
comprobar(bool(ev_a["casos"][9].get("evidencia")),
          "…y el veredicto declara de dónde sale ese juicio")
comprobar(ev_a["casos"][8]["resultado"] == "no_aplica",
          "El caso 8 no aplica: el 42805 no discrepa en ningún otro campo")
comprobar(any("no viaja en la salida" in h["titulo"] for h in ev_a["hallazgos"]),
          "Se registra que el estado de auditabilidad no cruza la conexión",
          str([h["titulo"] for h in ev_a["hallazgos"]]))

quito = [i for i in inc if i["campo"] != "cantidad"]
comprobar(A.evaluar(REALES, quito, CTX)["contraste"]["exhaustividad"] == 50.0,
          "Quitar una discrepancia baja la exhaustividad al 50 %")
falsa = inc + [{"campo": "paginas", "valor_cliente": "224", "valor_orden": "300",
                "severidad": "alta", "cita_documentos": True, "corregir": "orden",
                "interna": False}]
comprobar(A.evaluar(REALES, falsa, CTX)["contraste"]["precision"] == 66.7,
          "Añadir una que no existía baja la precisión al 66,7 %")
comprobar(A.evaluar(REALES, [], CTX)["contraste"]["exhaustividad"] == 0.0,
          "No reportar nada deja la exhaustividad en 0 %")

# ---------------------------------------------------------------------------
print("\n9 · La rama de similitud sobre las cuatro consultas de Álvaro")
import json as _json
from pathlib import Path as _Path
from modulos import similitud as SM

CARPETA = _Path("demo/datos/similitud")
ESPERADO_SIM = {
    # fichero                                (equivalentes, exhaustividad, precisión)
    "caso1_syn0047_acierto.json":            (4, 100.0, 100.0),
    "caso2_syn0041_fallo_conocido.json":     (5, 80.0, 80.0),
    "caso3_syn0052_distractores.json":       (2, 50.0, 50.0),
}
for nombre, (n_eq, exh, pre) in ESPERADO_SIM.items():
    ruta = CARPETA / nombre
    if not ruta.is_file():
        comprobar(False, f"Falta {nombre}")
        continue
    datos, avisos = SM.interpretar(ruta.read_text(encoding="utf-8"))
    comprobar(datos is not None and not avisos,
              f"{nombre}: se lee y cumple el acuerdo de 7 campos", str(avisos))
    esp, ctx = SM.verdad_de_campo(datos)
    ev = SM.evaluar(esp, ctx)
    c = ev["contraste"]
    comprobar(len(esp) == n_eq and c["exhaustividad"] == exh and c["precision"] == pre,
              f"{nombre}: {n_eq} equivalentes, exhaustividad {exh} %, precisión {pre} %",
              f"{len(esp)} / {c['exhaustividad']} / {c['precision']}")
    comprobar(all(x["cuadra"] for x in SM.recalcular_puntuaciones(datos)),
              f"{nombre}: las puntuaciones se reproducen con la fórmula")
    comprobar(ev["casos"][5]["resultado"] == "pasa",
              f"{nombre}: resultados y descartados particionan el corpus")

# El fallo que anuncia Álvaro tiene que aparecer donde él dice
d2, _ = SM.interpretar((CARPETA / "caso2_syn0041_fallo_conocido.json").read_text("utf-8"))
e2, x2 = SM.verdad_de_campo(d2)
ev2 = SM.evaluar(e2, x2)
comprobar("SYN-0045" in ev2["casos"][4]["observacion"],
          "El caso 2 señala SYN-0045 fuera de cabeza, como anuncia Álvaro",
          ev2["casos"][4]["observacion"][:160])
comprobar(ev2["casos"][4]["resultado"] == "no_pasa",
          "…y por eso el caso 4 no se supera")

d3, _ = SM.interpretar((CARPETA / "caso3_syn0052_distractores.json").read_text("utf-8"))
e3, x3 = SM.verdad_de_campo(d3)
ev3 = SM.evaluar(e3, x3)
comprobar(all(x in ev3["casos"][4]["observacion"] for x in ("SYN-0092", "SYN-0090")),
          "El caso 3 nombra los dos no equivalentes que adelantan al hermano",
          ev3["casos"][4]["observacion"][:260])
comprobar(len(ev3["adelantamientos"]) == 2,
          "…y los cuenta como adelantamientos, no sólo como colados en cabeza",
          str(ev3["adelantamientos"]))

# Lista vacía
d4, _ = SM.interpretar((CARPETA / "caso4_lista_vacia.json").read_text("utf-8"))
e4, x4 = SM.verdad_de_campo(d4)
ev4 = SM.evaluar(e4, x4)
comprobar(ev4["casos"][8]["resultado"] == "pasa",
          "El caso de lista vacía supera el caso del aviso",
          ev4["casos"][8]["observacion"][:140])
comprobar(ev4["casos"][4]["resultado"] == "no_aplica",
          "…y el caso del ranking no aplica, porque no hay ranking")

# El umbral se deriva del conjunto, no se elige
for nombre, esperado_eq in (("caso1_syn0047_acierto.json", 4),
                            ("caso2_syn0041_fallo_conocido.json", 5),
                            ("caso3_syn0052_distractores.json", 2)):
    dd, _ = SM.interpretar((CARPETA / nombre).read_text("utf-8"))
    ee, cc = SM.verdad_de_campo(dd)                       # sin umbral impuesto
    comprobar(cc["umbral"]["automatico"] and len(ee) == esperado_eq,
              f"{nombre}: el umbral se lee del salto del conjunto ({cc['tolerancia']:.1%})",
              f"{cc['umbral']}, {len(ee)} equivalentes")

# Y el veredicto no depende de él: hay una meseta ancha con el mismo resultado
d3b, _ = SM.interpretar((CARPETA / "caso3_syn0052_distractores.json").read_text("utf-8"))
meseta = []
for _pct in range(6, 31, 2):
    _e, _c = SM.verdad_de_campo(d3b, _pct / 100)
    meseta.append(SM.evaluar(_e, _c)["contraste"]["exhaustividad"])
comprobar(len(set(meseta)) == 1,
          "El veredicto del caso 3 aguanta del 6 % al 30 %: no lo sostiene el umbral",
          str(meseta))

# Un conjunto sin separación se declara como tal
import copy as _copy
plano_ = _copy.deepcopy(d3b)
for _i, _r in enumerate(plano_["resultados"]):     # desviaciones en continuo
    for _p in _r["parametros_justificativos"]:
        if isinstance(_p["valor_pedido"], (int, float)) and \
                not isinstance(_p["valor_pedido"], bool):
            _p["valor_candidata"] = _p["valor_pedido"] * (1 + 0.02 * (_i + 1))
_e, _c = SM.verdad_de_campo(plano_)
comprobar(not _c["umbral"]["automatico"],
          "Si las desviaciones forman un continuo, no se inventa una frontera",
          str(_c["umbral"]))
comprobar(any("no separa por sí solo" in h["titulo"]
              for h in SM.evaluar(_e, _c)["hallazgos"]),
          "…y se registra como hallazgo, porque el corte lo pone el evaluador")

# El margen del umbral se mide y se declara
peor, mejor = x3["margen"]
comprobar(peor is not None and mejor is not None and mejor > 2 * peor,
          "El umbral de equivalencia tiene holgura: los dos grupos se separan",
          f"peor equivalente {peor}, mejor no equivalente {mejor}")

comprobar(any("semántica se calcula y no se usa" in h["titulo"]
              for h in ev3["hallazgos"]),
          "Se registra que el peso semántico está a 0")
comprobar(ev3["casos"][9]["resultado"] == "no_aplica",
          "`extra_no_pactado` está pero viene vacío: no puede comprobarse",
          ev3["casos"][9]["observacion"][:140])

# Y reacciona si la salida se altera
import copy
alterada = copy.deepcopy(d3)
alterada["resultados"][0]["puntuacion"] = 0.5      # rompe la aritmética y el orden
eva = SM.evaluar(*SM.verdad_de_campo(alterada)[::-1][::-1])
comprobar(eva["casos"][1]["resultado"] == "no_pasa",
          "Tocar una puntuación rompe el caso de la aritmética")
comprobar(eva["casos"][2]["resultado"] == "no_pasa",
          "…y también el del orden")

partida = copy.deepcopy(d3)
partida["descartados"].append({"id_proyecto": partida["resultados"][0]["id_proyecto"],
                               "parametro": "presion_diseno", "valor_pedido": 1,
                               "valor_candidata": 2})
evp = SM.evaluar(*SM.verdad_de_campo(partida)[::-1][::-1])
comprobar(evp["casos"][5]["resultado"] == "no_pasa",
          "Un proyecto en las dos listas rompe la partición del corpus")

# ---------------------------------------------------------------------------
print("\n10 · El componente de IA: cerrado, acotado y sin degradar en silencio")
from nucleo import llm as L

L.configurar(api_key="")            # como si no hubiera clave
L._CLAVE = None
comprobar(not L.esta_disponible(), "Sin clave, el componente se declara no disponible")
comprobar("Secrets" in (L.por_que_no() or ""),
          "…y dice dónde ponerla", str(L.por_que_no()))

try:
    # Con un hueco de verdad que rellenar: si no lo hubiera, el rescate ni se
    # intenta y no haría falta clave.
    L.resolver("asistido", {"a": None}, "texto", {"properties": {"a": {}}}, "prompt")
    comprobar(False, "Pedir el rescate sin clave tiene que fallar, no caer a reglas")
except L.NoDisponible:
    comprobar(True, "Pedir el rescate sin clave levanta NoDisponible, no degrada solo")

campos, proc = L.resolver("determinista", {"a": 1, "b": None}, "t", {}, "p")
comprobar(campos == {"a": 1, "b": None} and proc == {"a": "regla", "b": "regla"},
          "El modo determinista no toca el modelo y marca la procedencia")

mezcla, proc = L.combinar({"a": 1, "b": None}, {"a": 99, "b": 7, "c": 3})
comprobar(mezcla == {"a": 1, "b": 7, "c": 3} and proc["a"] == "regla"
          and proc["b"] == "modelo",
          "En modo asistido mandan las reglas y el modelo sólo rellena huecos",
          f"{mezcla} / {proc}")

# El esquema de la rama se traduce al dialecto del proveedor sin que la rama lo sepa
from modulos import vigencia as _V
g = L._esquema_gemini(_V.FICHA["esquema_campos"])
comprobar(g["properties"]["fecha_emision"] == {"type": "string", "format": "date",
                                               "nullable": True},
          "Los tipos opcionales de la rama se traducen a `nullable`",
          str(g["properties"]["fecha_emision"]))
comprobar(g["properties"]["prorroga_renunciada"] == {"type": "boolean"},
          "…y los que no son opcionales se quedan igual")

# La caché evita repetir la misma lectura
L._CACHE.clear()
h1 = L._huella("p", "documento", {"x": 1})
h2 = L._huella("p", "documento", {"x": 1})
h3 = L._huella("p", "OTRO documento", {"x": 1})
comprobar(h1 == h2 and h1 != h3,
          "La huella de caché depende del contenido, no del momento")
L._a_cache(h1, {"leido": True})
comprobar(L._de_cache(h1) == {"leido": True}, "Lo cacheado se recupera")
L.vaciar_cache()
comprobar(L._de_cache(h1) is None, "…y se puede vaciar")

# La frontera de tipos: lo que devuelve el modelo no entra crudo en las reglas.
# Esto es la regresión del fallo del 22/08/2026: el modelo devolvía la fecha como
# cadena («2026-08-16»), nadie la convertía, y la regla
# `fecha_evaluacion <= campos["fecha_caducidad"]` tumbaba la aplicación entera con
# un TypeError a cinco llamadas de distancia del sitio donde estaba el problema.
_ESQ_V = vigencia.FICHA["esquema_campos"]
_crudo = {"fecha_emision": "2024-03-01", "fecha_caducidad": "2026-08-16",
          "fecha_inicio": None, "anios_pactados": "15",
          "prorroga_renunciada": "true", "objeto_consumado": False,
          "documento_incompleto": False, "direccion_objeto": "Calle del Coso 12",
          "campo_inventado": "algo", "cita_duracion": "quince años"}
_conf, _rech = L.conformar(_crudo, _ESQ_V)

comprobar(_conf["fecha_caducidad"] == date(2026, 8, 16),
          "Una fecha en ISO devuelta por el modelo llega a las reglas como date",
          repr(_conf["fecha_caducidad"]))
comprobar(_conf["anios_pactados"] == 15 and isinstance(_conf["anios_pactados"], int),
          "Un entero devuelto como cadena llega como entero")
comprobar(_conf["prorroga_renunciada"] is True,
          "«true» llega como booleano, no como cadena no vacía")
comprobar("campo_inventado" in _rech and "campo_inventado" not in _conf,
          "Un campo que el modelo se inventa no entra en el núcleo")

_mala, _r2 = L.conformar({"fecha_caducidad": "no consta"}, _ESQ_V)
comprobar(_mala["fecha_caducidad"] is None and "fecha_caducidad" in _r2,
          "Una fecha que no es una fecha se queda en None y se declara descartada, "
          "no se cuela con el tipo equivocado")

_base = vigencia._campos_vacios()
comprobar(vigencia.estado_esperado({**_base, **_conf}, FECHA)[0] == "caducado",
          "Con los campos ya conformados, la regla decide sin reventar")
comprobar(vigencia.estado_esperado(
    {**_base, "fecha_caducidad": "2026-08-16", "prorroga_renunciada": True},
    FECHA)[0] == "caducado",
    "Y si aun así llega una cadena, la regla la contiene en vez de tumbar la app")

# La procedencia llega marcada, incluidos los descartes
_c3, _p3 = L.combinar({"fecha_caducidad": None, "anios_pactados": 15},
                      {"fecha_caducidad": date(2026, 8, 16)})
comprobar(_p3["anios_pactados"] == "regla" and _p3["fecha_caducidad"] == "modelo",
          "Cada valor sale etiquetado con quién lo puso")

# El plan de retirada de modelo: se dispara con un 404 y sólo con un 404
comprobar(L._modelo_retirado(RuntimeError(
    "ClientError: 404 NOT_FOUND. {'error': {'code': 404, 'message': "
    "'This model models/gemini-2.5-flash is no longer available to new users.'}}")),
    "Un 404 de modelo retirado se reconoce como tal")
comprobar(not L._modelo_retirado(RuntimeError("ConnectionError: timed out")),
          "Un corte de red NO se confunde con un modelo retirado: cambiar de "
          "modelo no arreglaría un problema de red")
comprobar(not L._modelo_retirado(RuntimeError("ClientError: 429 RESOURCE_EXHAUSTED")),
          "…ni una cuota agotada")

comprobar(L.MODELO not in ("gemini-2.5-flash", "gemini-2.0-flash"),
          "El modelo anclado no es uno de los que el proveedor ya ha retirado",
          L.MODELO)
comprobar(L.MODELO not in L.MODELOS_ALTERNATIVOS,
          "El plan de retirada no repite el modelo anclado")
comprobar(L.modelo_en_uso() == L.MODELO,
          "Sin sustituciones, el modelo en uso es el anclado")

# Una lectura hecha con otro modelo es otra lectura: no puede compartir caché
_h_anclado = L._huella("p", "documento", {"x": 1})
L.MODELO_EFECTIVO = "otro-modelo"
comprobar(L._huella("p", "documento", {"x": 1}) != _h_anclado,
          "La huella de caché cambia con el modelo: una lectura de otro modelo no "
          "se reutiliza en silencio")
_est = L.estado()
L.MODELO_EFECTIVO = None
comprobar(_est["modelo"] == "otro-modelo" and _est["modelo_anclado"] == L.MODELO,
          "El estado enseña el modelo en uso y el anclado por separado")

# La escalera completa, con un proveedor simulado: no gasta una sola llamada real
class _Resp:
    def __init__(self, t):
        self.text = t


class _ModelosFalsos:
    """Acepta un único modelo y, si se le pide, rechaza el esquema estricto."""

    def __init__(self, ok, rechaza_esquema=False):
        self.ok, self.rechaza, self.log = ok, rechaza_esquema, []

    def generate_content(self, model, contents, config):
        self.log.append((model, "esquema" if getattr(config, "response_json_schema", None)
                         else "plano"))
        if model != self.ok:
            raise RuntimeError("ClientError: 404 NOT_FOUND. This model is no longer "
                               "available to new users.")
        if self.rechaza and getattr(config, "response_json_schema", None):
            raise RuntimeError("ClientError: 400 INVALID_ARGUMENT bad schema")
        return _Resp('{"ok": true}')


from google import genai as _genai
_cliente_real, _clave_real = _genai.Client, L._CLAVE
_FALSOS = {"actual": None}
_genai.Client = lambda api_key=None: type("C", (), {"models": _FALSOS["actual"]})()
_rpm_real, _reint_real = L.LIMITE_POR_MINUTO, L.REINTENTOS_POR_CUOTA
L.LIMITE_POR_MINUTO, L.REINTENTOS_POR_CUOTA = 10 ** 6, 0
L._CLAVE = "clave-de-prueba"
_ESQ = {"type": "object", "properties": {"ok": {"type": "boolean"}}}


def _con_falso(falso, fn):
    _FALSOS["actual"] = falso
    L.MODELO_EFECTIVO = L.AVISO_MODELO = None
    return fn()


_f = _ModelosFalsos(L.MODELO)
_r = _con_falso(_f, lambda: L._llamar("p", "doc-a", _ESQ, sin_cache=True))
comprobar(_r == {"ok": True} and len(_f.log) == 1 and L.AVISO_MODELO is None,
          "Con el modelo anclado disponible se llama una vez y no hay aviso",
          str(_f.log))

_f = _ModelosFalsos(L.MODELOS_ALTERNATIVOS[0])
_r = _con_falso(_f, lambda: L._llamar("p", "doc-b", _ESQ, sin_cache=True))
comprobar(_r == {"ok": True} and L.modelo_en_uso() == L.MODELOS_ALTERNATIVOS[0],
          "Si el modelo anclado está retirado, se pasa al siguiente del plan",
          L.modelo_en_uso())
comprobar(L.AVISO_MODELO and "no son directamente comparables" in L.AVISO_MODELO,
          "…y el aviso dice que los veredictos de antes y después no son comparables")

_f = _ModelosFalsos(L.MODELO, rechaza_esquema=True)
_r = _con_falso(_f, lambda: L._llamar("p", "doc-c", _ESQ, sin_cache=True))
comprobar(_r == {"ok": True} and L.AVISO_MODELO is None
          and all(m == L.MODELO for m, _ in _f.log),
          "Si el proveedor rechaza el esquema se baja de escalón sin cambiar de "
          "modelo: una opción retirada no altera el veredicto y un modelo sí",
          str(_f.log))

_f = _ModelosFalsos("un-modelo-que-no-existe")
try:
    _con_falso(_f, lambda: L._llamar("p", "doc-d", _ESQ, sin_cache=True))
    comprobar(False, "Sin ningún modelo disponible, la llamada tiene que fallar")
except L.NoDisponible as _e:
    comprobar("probados:" in str(_e),
              "Sin ningún modelo disponible, el error nombra todos los intentados")

_f = _ModelosFalsos(L.MODELO)
_r = _con_falso(_f, lambda: L._llamar_texto("p", "doc-e", sin_cache=True))
comprobar(_f.log and all(t == "plano" for _, t in _f.log),
          "El redactor del informe no pide esquema: se le pide prosa")

_genai.Client, L._CLAVE = _cliente_real, _clave_real
L.LIMITE_POR_MINUTO, L.REINTENTOS_POR_CUOTA = _rpm_real, _reint_real
L.MODELO_EFECTIVO = L.AVISO_MODELO = None
L.vaciar_cache()

# Las ramas que manejan datos ajenos tienen la IA cerrada por escrito
import modulos as _M
for _id, _permitida in (("auditoria", False), ("vigencia", True), ("similitud", False)):
    _f = _M.rama(_id).FICHA
    comprobar(_f.get("ia_permitida") is _permitida,
              f"{_id}: ia_permitida = {_permitida}")
    if not _permitida:
        comprobar(bool(_f.get("motivo_ia")),
                  f"{_id}: y el veto lleva su motivo escrito")

# ---------------------------------------------------------------------------
print("\n10a · El intérprete no puede perder registros")
# Regresión de un fallo grave encontrado el 24/08/2026: con una salida de una línea
# por documento —la forma más natural de pegarla— el lector de fichas se comía uno
# de cada dos registros Y le asignaba al superviviente el estado del siguiente.
# El evaluador no habría dicho «no lo he leído»: habría dicho que el módulo se
# equivoca. Un evaluador que lee mal la salida no evalúa, inventa.
_una_linea = "\n".join([
    "PRUEBA_1 · Vigente · vence 01/03/2039",
    "PRUEBA_2 · Caducado · venció 16/08/2026",
    "PRUEBA_3 · Obsoleto",
    "PRUEBA_4 · Vigente",
    "PRUEBA_5 · Vigente",
    "PRUEBA_6 · Obsoleto"])
_r, _ = vigencia.interpretar(_una_linea)
comprobar(len(_r) == 6, "Seis líneas, seis registros: no se pierde ninguno",
          f"leídos {len(_r)}")
comprobar([x["id_documento"] for x in _r] ==
          [f"PRUEBA_{i}" for i in range(1, 7)],
          "…y cada registro conserva su identificador")
comprobar([x["estado"] for x in _r] ==
          ["vigente", "caducado", "obsoleto", "vigente", "vigente", "obsoleto"],
          "…y su estado, sin heredar el del siguiente",
          str([x["estado"] for x in _r]))

_fichas = ("PRUEBA_1\nEstado: Vigente\nVencimiento: 01/03/2039\n"
           "Evidencia: Cláusula Segunda\n\n"
           "PRUEBA_3\nEstado: Obsoleto\nSustituye a PRUEBA_2\nVencimiento: 31/12/2023\n")
_rf, _ = vigencia.interpretar(_fichas)
comprobar(len(_rf) == 2, "Las fichas de varias líneas siguen agrupándose bien",
          f"leídas {len(_rf)}")
comprobar(any(x["id_documento"] == "PRUEBA_3" and x["sustituye_a"] == "PRUEBA_2"
              for x in _rf),
          "«Sustituye a PRUEBA_2» es una referencia dentro de la ficha, no una "
          "ficha nueva")

# ---------------------------------------------------------------------------
print("\n10b · Contradicciones y validación humana · PED1004")
from modulos import contradicciones as CT

# Verdad de campo escrita a mano antes de ejecutar nada, leyendo la exportación:
# dos hechos activos de `fecha_entrega` —25/08/2026 en la confirmación y
# 12/08/2026 en el pedido— dan UNA contradicción. El módulo la emite, la resuelve
# validando el hecho A, y deja los DOS hechos con is_active = 1.
ESPERADO_PED1004 = {
    "contradicciones": 1,
    "resultados": {1: "pasa", 2: "no_aplica", 3: "pendiente", 4: "pasa",
                   5: "pasa", 6: "pasa", 7: "no_pasa", 8: "no_aplica",
                   9: "no_aplica", 10: "pendiente"},
    "tasa": 80.0, "cobertura": 50.0,
}

_ruta = guion.RAIZ / "contradicciones" / "export_PED1004.json"
if not _ruta.is_file():
    comprobar(False, "Falta demo/datos/contradicciones/export_PED1004.json")
else:
    _datos, _av = CT.interpretar(_ruta.read_text(encoding="utf-8"))
    comprobar(_datos is not None and not _av,
              "La exportación de Mencía se interpreta sin avisos", str(_av))
    _esp, _c = CT.verdad_de_campo(_datos)
    comprobar(len(_esp) == ESPERADO_PED1004["contradicciones"],
              "El evaluador deriva 1 contradicción de los hechos, sin mirar la "
              "tabla de contradicciones del módulo", f"derivadas {len(_esp)}")
    comprobar(_esp and _esp[0]["hechos"] == {24, 25} and
              _esp[0]["campo"] == "fecha_entrega",
              "…y señala los dos hechos correctos del campo fecha_entrega")

    _evc = CT.evaluar(_esp, _c)
    for _n, _r in ESPERADO_PED1004["resultados"].items():
        comprobar(_evc["casos"][_n]["resultado"] == _r,
                  f"PED1004 · caso {_n} → {_r}",
                  _evc["casos"][_n]["resultado"])
    _rc = CT.B.resumen(_evc["casos"])
    comprobar(_rc["tasa"] == ESPERADO_PED1004["tasa"] and
              _rc["cobertura"] == ESPERADO_PED1004["cobertura"],
              "Tasa 80% sobre 5 casos verificados y cobertura 50%", str(_rc))
    comprobar(_evc["contraste"]["exhaustividad"] == 100.0 and
              _evc["contraste"]["precision"] == 100.0,
              "Exhaustividad y precisión al 100%: la única contradicción real es "
              "la única emitida")

    # El fallo del caso 7 tiene que ser el del hecho perdedor, no otro
    comprobar("is_active = 1" in _evc["casos"][7]["observacion"]
              and "12/08/2026" in _evc["casos"][7]["observacion"],
              "El caso 7 falla por el hecho descartado que sigue activo, y lo cita")

    # Y el evaluador tiene que rechazar una exportación alterada a propósito
    import json as _json
    _crudo = _json.loads(_ruta.read_text(encoding="utf-8"))
    _crudo["contradictions"][0]["fact_b_id"] = 99
    _d2, _ = CT.interpretar(_json.dumps(_crudo))
    _e2, _c2 = CT.verdad_de_campo(_d2)
    _ev2 = CT.evaluar(_e2, _c2)
    comprobar(_ev2["casos"][1]["resultado"] == "no_pasa",
              "Si la contradicción apunta a un hecho que no está en conflicto, "
              "el caso 1 falla", _ev2["casos"][1]["resultado"])

    _crudo = _json.loads(_ruta.read_text(encoding="utf-8"))
    _crudo["contradiction_resolutions"][0]["resolved_value"] = "01/01/2027"
    _d3, _ = CT.interpretar(_json.dumps(_crudo))
    _e3, _c3 = CT.verdad_de_campo(_d3)
    _ev3 = CT.evaluar(_e3, _c3)
    comprobar(_ev3["casos"][6]["resultado"] == "no_pasa",
              "Si el valor resuelto no coincide con el hecho que dice validar, "
              "el caso 6 falla", _ev3["casos"][6]["resultado"])

    _crudo = _json.loads(_ruta.read_text(encoding="utf-8"))
    for _h in _crudo["extracted_facts"]:
        if _h["id"] == 25:
            _h["is_active"] = 0
    _d4, _ = CT.interpretar(_json.dumps(_crudo))
    _e4, _c4 = CT.verdad_de_campo(_d4)
    _ev4 = CT.evaluar(_e4, _c4)
    comprobar(_ev4["casos"][7]["resultado"] == "pasa",
              "Y si el hecho descartado se marca inactivo, el caso 7 pasa: el "
              "evaluador reacciona a la corrección, no sólo al fallo",
              _ev4["casos"][7]["resultado"])

# ---------------------------------------------------------------------------
print("\n11 · Panel de jueces")
from nucleo import jueces as JU

# Panel simulado: se sustituye la única función que habla con el modelo. Todo lo
# demás —la regla de unanimidad, el recuento, kappa— se ejecuta de verdad. Así la
# lógica del panel queda comprobada sin gastar una sola llamada.
_GUION = {}


def _consulta_falsa(prompt, texto, esquema, sin_cache=False):
    """Un juez contesta todos los criterios de una vez, como en el sistema real."""
    for nombre, lente in JU.PERSPECTIVAS.values():
        if lente in prompt:
            return {"votos": [{"criterio": ident, "veredicto": votos[nombre],
                               "justificacion": f"por {nombre}", "cita": None}
                              for ident, votos in _GUION.items()]}
    raise AssertionError("perspectiva no prevista en el guion de prueba")


_consulta_real = L.consultar
L.consultar = _consulta_falsa

C_UNANIME = JU.criterio("u", "Criterio unánime", "¿?", "porque sí")
C_PARTIDO = JU.criterio("p", "Criterio partido", "¿?", "porque sí")
C_MALO = JU.criterio("m", "Criterio incumplido", "¿?", "porque sí")

_GUION = {
    "u": {"Destinatario": "cumple", "Auditor": "cumple", "Literal": "cumple"},
    "p": {"Destinatario": "cumple", "Auditor": "no_cumple", "Literal": "cumple"},
    "m": {"Destinatario": "no_cumple", "Auditor": "no_cumple", "Literal": "no_cumple"},
}
panel = JU.evaluar_panel([C_UNANIME, C_PARTIDO, C_MALO], "evidencia cualquiera")

comprobar(panel["criterios"][0]["veredicto"] == "cumple",
          "Con unanimidad, el criterio puntúa")
comprobar(panel["criterios"][1]["veredicto"] == "discrepancia",
          "Dos contra uno NO resuelve el criterio: se declara la discrepancia",
          panel["criterios"][1]["veredicto"])
comprobar(panel["criterios"][1]["acuerdo"] == 0.67,
          "…y el acuerdo del criterio queda registrado", panel["criterios"][1]["acuerdo"])
comprobar(panel["puntuables"] == 2 and panel["cumple"] == 1 and panel["tasa"] == 50.0,
          "La tasa cualitativa se calcula sólo sobre los criterios con acuerdo",
          f"{panel['puntuables']} / {panel['tasa']}")
comprobar(len(panel["requisitos"]) == 1,
          "Un criterio en discrepancia genera requisito de arbitraje")

# Kappa: un panel que contesta lo mismo a todo tiene acuerdo perfecto y no
# discrimina nada. Eso lo tiene que delatar la corrección por azar.
_GUION = {t: {"Destinatario": "cumple", "Auditor": "cumple", "Literal": "cumple"}
          for t in ("u", "p", "m")}
plano_ = JU.evaluar_panel([C_UNANIME, C_PARTIDO, C_MALO], "otra evidencia")
comprobar(plano_["fleiss"]["kappa"] is None and "no está definida" in
          plano_["fleiss"]["motivo"],
          "Un panel que vota igual a todo no produce un kappa de 1 engañoso",
          str(plano_["fleiss"]))
comprobar(plano_["acuerdo_medio"] == 1.0,
          "…aunque su acuerdo bruto sea perfecto, y se enseñan los dos")

# Un voto que no encaja en las tres categorías no se interpreta
L.consultar = lambda p, t, e, sin_cache=False: {
    "votos": [{"criterio": "u", "veredicto": "quizá", "justificacion": ""}]}
raro = JU.evaluar_panel([C_UNANIME], "x")["criterios"][0]
comprobar(raro["veredicto"] == "no_valorable",
          "Un voto fuera de las tres categorías cuenta como no valorable, no se adivina")

# Y un juez que se salta un criterio no genera un voto inventado
L.consultar = lambda p, t, e, sin_cache=False: {"votos": []}
mudo = JU.evaluar_panel([C_UNANIME], "x")["criterios"][0]
comprobar(mudo["veredicto"] == "no_valorable"
          and "no se ha pronunciado" in mudo["votos"][0]["justificacion"],
          "Un criterio que el juez no contesta sale como no valorable, con su motivo")

L.consultar = _consulta_real

# ---------------------------------------------------------------------------
print("\n12 · Informe: el control de cifras")
from nucleo import informe as INF

_docs = guion.documentos_de("vigencia")
_esp, _ctx = vigencia.verdad_de_campo(_docs, FECHA)
_ev = vigencia.evaluar(_esp, perfecta_de(_esp), FECHA, None, "determinista",
                       contexto=_ctx)
_er = V.evaluation_result(vigencia.FICHA, _ev, vigencia.sujeto(_esp), FECHA)
_p = INF.payload(vigencia.FICHA, _er, _ev)
_permitidas = INF.cifras_permitidas(_p)

v_ok = INF.verificar_cifras(
    f"El módulo supera {_p['metricas']['superados']} casos y la cobertura es "
    f"{_p['metricas']['cobertura_bateria_pct']}%.", _permitidas)
comprobar(v_ok["ok"], "Las cifras que salen de los resultados pasan el control",
          str(v_ok))

v_mal = INF.verificar_cifras("La precisión alcanza el 93,7% este trimestre.",
                             _permitidas)
comprobar(not v_mal["ok"] and "93.7" in v_mal["intrusas"],
          "Una cifra inventada se detecta aunque el texto suene impecable",
          str(v_mal))

v_lista = INF.verificar_cifras("1. Primer punto\n2. Segundo punto\n### 3. Tercero",
                               set())
comprobar(v_lista["ok"],
          "La numeración de listas y encabezados no se confunde con datos")

v_form = INF.verificar_cifras("Cobertura del 100 %.", {"100"})
comprobar(v_form["ok"], "100, 100.0 y 100,0 se reconocen como el mismo número")

# El informe se genera sin modelo y no miente sobre su origen
sin_ia = INF.generar(vigencia.FICHA, _er, _ev, usar_modelo=False)
comprobar(sin_ia["origen"] == "plantilla" and "plantilla determinista" in sin_ia["texto"],
          "Sin modelo el informe se genera igual y declara que es de plantilla")
for seccion in ("Qué se ha evaluado", "Resultado", "Qué conviene revisar",
                "Qué necesito de ti"):
    comprobar(seccion in sin_ia["texto"], f"El informe lleva la sección «{seccion}»")

# Lo que viaja al redactor está recortado según el permiso de datos de la rama
from modulos import auditoria as _A
comprobar(INF.payload(_A.FICHA, _er, _ev, incluir_observaciones=False)["casos"][0]
          .get("observacion") is None,
          "En una rama con los datos vetados, las observaciones no viajan al redactor")
comprobar("observacion" in INF.payload(vigencia.FICHA, _er, _ev)["casos"][0],
          "…y en una rama con datos ficticios sí viajan")

# Las tres ramas declaran por escrito si el panel puede ejecutarse
for _id, _permitido in (("auditoria", False), ("vigencia", True), ("similitud", True),
                        ("contradicciones", True)):
    _f = _M.rama(_id).FICHA
    comprobar(_f.get("panel_permitido") is _permitido,
              f"{_id}: panel_permitido = {_permitido}")
    comprobar(bool(_f.get("cualitativos")),
              f"{_id}: tiene criterios cualitativos escritos")
    if not _permitido:
        comprobar(bool(_f.get("motivo_panel")),
                  f"{_id}: y el panel cerrado lleva su motivo escrito")

# ---------------------------------------------------------------------------
print("\n13 · Plantilla común de evaluación")
from nucleo import plantilla as PL
from nucleo.bateria import ORDEN_SEVERIDAD, SEVERIDADES

# Fabián, 24/08: entradas, resultado esperado, resultado observado, severidad y
# pasa/no pasa. Una sola forma para todos los módulos.
comprobar(PL.COLUMNAS == ["#", "Caso", "Entradas", "Resultado esperado",
                          "Resultado observado", "Severidad", "Pasa / No pasa"],
          "La plantilla lleva las cinco columnas acordadas, en su orden")

# Toda rama operativa declara severidad para todos sus casos, y sólo con valores
# del vocabulario: una severidad inventada sobre la marcha no clasifica nada.
for _id in ("auditoria", "vigencia", "similitud", "contradicciones"):
    _f = _M.rama(_id).FICHA
    _sev = _f.get("severidad") or {}
    _malos = [n for n in _f["casos"] if _sev.get(n) not in SEVERIDADES]
    comprobar(not _malos, f"{_id}: los {len(_f['casos'])} casos llevan severidad "
                          f"declarada y válida", str(_malos))

# La plantilla de los módulos priorizados tiene que salir completa, sin huecos
_ru = guion.RAIZ / "contradicciones" / "export_PED1004.json"
_dc, _ = CT.interpretar(_ru.read_text(encoding="utf-8"))
_ec, _cc = CT.verdad_de_campo(_dc)
_evc2 = CT.evaluar(_ec, _cc)
for _nombre, _fi, _evx in (("vigencia", vigencia.FICHA, _ev),
                           ("contradicciones", CT.FICHA, _evc2)):
    _cob = PL.cobertura_severidad(_fi, _evx)
    comprobar(_cob["completa"],
              f"{_nombre}: plantilla completa — severidad y desglose en todos los casos",
              str(_cob))
    _filas = PL.filas(_fi, _evx, "entradas de prueba")
    comprobar(all(set(f) == set(PL.COLUMNAS) for f in _filas),
              f"{_nombre}: todas las filas llevan exactamente las columnas acordadas")
    comprobar(all(f["Resultado esperado"] != PL.SIN_DESGLOSAR for f in _filas),
              f"{_nombre}: ninguna fila queda sin desglosar")

# La severidad clasifica riesgo, no resultado: sólo se agrupa lo que falla
_sev_ct = PL.fallos_por_severidad(CT.FICHA, _evc2)
_agrupados = [x["caso"] for g in _sev_ct["grupos"].values() for x in g]
comprobar(_agrupados == [7],
          "Sólo entran en el listado por severidad los casos que fallan de verdad; "
          "un pendiente o un no aplicable no tienen fallo que graduar", str(_agrupados))
comprobar(_sev_ct["peor"] == "alta",
          "…y la peor severidad presente se identifica", str(_sev_ct["peor"]))

# El caso 7 de Mencía es el ejemplo que pide Fabián: esperado y observado a la vista
_c7 = _evc2["casos"][7]
comprobar("descartado" in (_c7["esperado"] or "")
          and "is_active = 1" in (_c7["observado"] or ""),
          "El fallo de Mencía se lee en la plantilla sin abrir la observación",
          f"{_c7['esperado']} || {_c7['observado']}")

# El documento generado lleva la tabla y los fallos graduados
_md = PL.a_markdown(CT.FICHA, V.evaluation_result(CT.FICHA, _evc2, CT.sujeto(_cc)),
                    _evc2, "exportación JSON del pedido")
for _t in ("| # | Caso | Entradas |", "## Fallos por severidad", "### Alta",
           "Resultado esperado", "Severidad declarada en"):
    comprobar(_t in _md, f"La plantilla en Markdown contiene «{_t}»")

# Y el desglose no cambia ningún veredicto: es presentación, no juicio
_evc3 = CT.evaluar(_ec, _cc)
comprobar(all(_evc2["casos"][n]["resultado"] == _evc3["casos"][n]["resultado"]
              for n in _evc2["casos"]),
          "Desglosar esperado y observado no altera ningún resultado")

# ---------------------------------------------------------------------------
print("\n14 · Asesor de mejora · el candado del anclaje")
from nucleo import asesor as AS

# El asesor es el único sitio donde el modelo produce criterio, así que es el que
# más control necesita. La regla: toda recomendación tiene que apoyarse en un caso
# que exista y que el módulo NO supere.
_recs = [
    {"titulo": "Sostenida por un caso fallido", "casos": [7],
     "que_cambiar": "x", "como_comprobarlo": "y"},
    {"titulo": "Cita un caso que no existe", "casos": [99],
     "que_cambiar": "x", "como_comprobarlo": "y"},
    {"titulo": "Sólo cita casos superados", "casos": [1, 5],
     "que_cambiar": "x", "como_comprobarlo": "y"},
    {"titulo": "No cita ninguno", "casos": [],
     "que_cambiar": "x", "como_comprobarlo": "y"},
    {"titulo": "Mezcla superado y fallido", "casos": [1, 7],
     "que_cambiar": "x", "como_comprobarlo": "y"},
]
_val, _desc = AS.verificar_anclaje(_recs, _evc2)
_titulos = [r["titulo"] for r in _val]
comprobar(_titulos == ["Sostenida por un caso fallido", "Mezcla superado y fallido"],
          "Sólo sobreviven las recomendaciones ancladas a un caso fallido real",
          str(_titulos))
comprobar(len(_desc) == 3 and all(d.get("motivo") for d in _desc),
          "Las descartadas se cuentan y llevan su motivo escrito")
comprobar(next(r for r in _val if r["titulo"] == "Mezcla superado y fallido")["casos"]
          == [7],
          "De una recomendación mixta sólo se conservan los casos que la sostienen")

# La prioridad la fija la severidad declarada, no el modelo
_orden = AS.ordenar([{"titulo": "media", "casos": [4]},
                     {"titulo": "critica", "casos": [1]},
                     {"titulo": "alta", "casos": [7]}], CT.FICHA)
comprobar([r["titulo"] for r in _orden] == ["critica", "alta", "media"],
          "El orden de las recomendaciones lo pone la severidad, no el modelo",
          str([r["titulo"] for r in _orden]))

# Lo que viaja al asesor: hechos calculados, y nunca los casos que ya se superan
_pl = AS.payload(CT.FICHA, V.evaluation_result(CT.FICHA, _evc2, CT.sujeto(_cc)), _evc2)
comprobar(all(c["resultado"] != "pasa" for c in _pl["casos_no_superados"]),
          "Al asesor sólo le llegan los casos que no se superan")
comprobar(7 in [c["numero"] for c in _pl["casos_no_superados"]],
          "…y el caso 7 de Mencía, que es el fallo real, está entre ellos")
comprobar(all(c.get("severidad") for c in _pl["casos_no_superados"]),
          "Cada caso viaja con su severidad declarada")

# Sin modelo, el asesor sigue dando plan: las correcciones ya escritas, ordenadas
_sin = AS.aconsejar(CT.FICHA, V.evaluation_result(CT.FICHA, _evc2, CT.sujeto(_cc)),
                    _evc2, usar_modelo=False)
comprobar(_sin["origen"] == "plantilla" and _sin["recomendaciones"],
          "Sin modelo el asesor sigue emitiendo plan y declara que es de plantilla")
comprobar(all(r["casos"] for r in _sin["recomendaciones"]),
          "…y también ahí toda recomendación va anclada a un caso")

# Un módulo sin fallos no recibe consejo inventado
_perf = CT.evaluar(_ec, _cc)
for _c in _perf["casos"].values():
    _c["resultado"] = "pasa"
_nada = AS.aconsejar(CT.FICHA,
                     V.evaluation_result(CT.FICHA, _perf, CT.sujeto(_cc)), _perf,
                     usar_modelo=False)
comprobar(_nada["origen"] == "ninguno" and not _nada["recomendaciones"],
          "Si no falla nada, el asesor no inventa recomendaciones")

# La ranura de lectura ya no es un camino paralelo: no hay modo «sólo modelo»
comprobar("ia" not in L.MODOS and set(L.MODOS) == {"determinista", "asistido"},
          "La lectura por IA deja de ser un modo alternativo: sólo hay reglas, con "
          "o sin rescate", str(list(L.MODOS)))

# Y el rescate no gasta si las reglas lo han encontrado todo
_llamadas_antes = dict(L.ESTADISTICAS)
_completos = {"a": 1, "b": 2}
_c_out, _p_out = L.resolver("asistido", _completos, "texto", {"properties": {}}, "p")
comprobar(_c_out == _completos and set(_p_out.values()) == {"regla"},
          "Sin huecos que rellenar, el rescate devuelve lo determinista")
comprobar(L.ESTADISTICAS["llamadas"] == _llamadas_antes["llamadas"],
          "…y no gasta ninguna llamada")

# ---------------------------------------------------------------------------
print("\n15 · Ciclo de mejora · el evaluador con memoria")
from nucleo import historial as H

_er_ct = V.evaluation_result(CT.FICHA, _evc2, CT.sujeto(_cc))
_snap1 = H.instantanea(CT.FICHA, _er_ct, _evc2, "antes de corregir")
comprobar(_snap1["casos"]["7"] == "no_pasa" and _snap1["metricas"]["tasa"] == 80.0,
          "La instantánea guarda el estado de cada caso y las métricas")
comprobar("documento" not in json_mod.dumps(_snap1).lower()
          or "Pedido_PED1004" not in json_mod.dumps(_snap1),
          "…y no arrastra los datos del compañero, sólo el veredicto")

# La corrección de Mencía: marcar el hecho descartado como inactivo
_crudo_ok = json_mod.loads(_ru.read_text(encoding="utf-8"))
for _h in _crudo_ok["extracted_facts"]:
    if _h["id"] == 25:
        _h["is_active"] = 0
_d_ok, _ = CT.interpretar(json_mod.dumps(_crudo_ok))
_e_ok, _c_ok = CT.verdad_de_campo(_d_ok)
_ev_ok = CT.evaluar(_e_ok, _c_ok)
_snap2 = H.instantanea(CT.FICHA,
                       V.evaluation_result(CT.FICHA, _ev_ok, CT.sujeto(_c_ok)),
                       _ev_ok, "tras la corrección")

_comp = H.comparar(_snap1, _snap2, CT.FICHA)
comprobar(any(m["caso"] == 7 and m["cambio"] == "corregido"
              for m in _comp["mejoras"]),
          "El sistema detecta que el caso 7 pasó de fallido a superado",
          str(_comp["mejoras"]))
comprobar(not _comp["regresiones"], "…y que no hubo ninguna regresión")
comprobar("tasa" in _comp["deltas"] and _comp["deltas"]["tasa"]["delta"] > 0,
          "…y que la tasa sube, con el antes y el después",
          str(_comp.get("deltas")))

comprobar(_ev_ok["contraste"]["precision"] == 100.0
          and _ev_ok["contraste"]["exhaustividad"] == 100.0,
          "Corregir el fallo NO castiga al módulo: la contradicción resuelta sigue "
          "contando, así que la precisión no se hunde",
          f"exh {_ev_ok['contraste']['exhaustividad']} / "
          f"prec {_ev_ok['contraste']['precision']}")

_texto = H.texto_evolucion(_comp)
comprobar("caso 7" in _texto and "corregido" in _texto,
          "La frase que demuestra la mejora se genera sola", _texto[:110])

# Una regresión pesa distinto que una mejora, y no se disimula
_comp_reg = H.comparar(_snap2, _snap1, CT.FICHA)
comprobar(any(r["caso"] == 7 and r["cambio"] == "regresión"
              for r in _comp_reg["regresiones"]),
          "Si un caso retrocede se marca como regresión, no como cambio neutro")
comprobar("REGRESIÓN" in H.texto_evolucion(_comp_reg),
          "…y la regresión se dice en voz alta, no se suaviza")

# Dos evaluaciones idénticas no inventan progreso
comprobar(H.comparar(_snap1, _snap1, CT.FICHA)["sin_cambios"],
          "Dos evaluaciones iguales no producen ninguna mejora ficticia")
comprobar(H.comparar(None, _snap1, CT.FICHA) is None,
          "Sin evaluación anterior no hay comparación que inventar")

# ---------------------------------------------------------------------------
print("\n16 · Coherencia del despliegue")
# El fallo más frecuente de este proyecto no es de lógica: es subir a GitHub la
# mitad de los ficheros. Un `app.py` nuevo con un `ui.py` viejo revienta con un
# AttributeError que señala la línea que llama, no el fichero que falta.
import importlib, re as _re

_fuente_app = pathlib.Path("app.py").read_text(encoding="utf-8")
_m = _re.search(r"PIEZAS = \[(.*?)\n\]", _fuente_app, _re.S)
comprobar(_m is not None, "app.py declara qué piezas necesita de los demás ficheros")

_declaradas = set(_re.findall(r'"(\w+)"', _m.group(1))) if _m else set()
_usadas = set(_re.findall(r"\bui\.(\w+)\(", _fuente_app))
_faltan_decl = sorted(_usadas - _declaradas - {"inyectar_estilo", "pastilla", "nota",
                                               "kpi", "fila_kpis", "cabecera",
                                               "tarjeta_modulo", "panel_ia",
                                               "tabla_documentos", "editor",
                                               "bloque_contraste", "bloque_hallazgos",
                                               "bloque_casos", "bloque_requisitos",
                                               "bloque_veredicto", "bloque_evidencia",
                                               "bloque_informe", "exportar",
                                               "fila_medidores"})
comprobar(not _faltan_decl,
          "Las funciones nuevas de ui.py que usa app.py están en la comprobación "
          "de arranque", str(_faltan_decl))

import ui as _uimod
for _f, _mod in (("ui.py", _uimod), ("nucleo/plantilla.py", PL),
                 ("nucleo/asesor.py", AS), ("nucleo/historial.py", H)):
    _piezas = [x for x in _declaradas if hasattr(_mod, x)]
    comprobar(bool(_piezas), f"{_f} expone las piezas que la app espera")

comprobar(VERSION_NUCLEO >= 6,
          "La versión del núcleo sube cuando cambia la forma de las piezas",
          str(VERSION_NUCLEO))

# ---------------------------------------------------------------------------
print("\n17 · Ritmo y cuota del nivel gratuito")
# El nivel gratuito da 5 peticiones por minuto y por modelo. No es un detalle de
# configuración: es la restricción que decide cómo se diseña todo lo que llama al
# modelo. El panel fallaba por aritmética, no por un error de código.

comprobar(L._es_cuota(RuntimeError("ClientError: 429 RESOURCE_EXHAUSTED")),
          "Un 429 se reconoce como cuota agotada")
comprobar(not L._es_cuota(RuntimeError("404 NOT_FOUND no longer available")),
          "Y no se confunde con un modelo retirado: uno se arregla esperando y el "
          "otro cambiando de modelo")
comprobar(L._espera_sugerida(RuntimeError("{'retryDelay': '32s'}")) == 33.0,
          "Se hace caso a la espera que sugiere el proveedor, no se adivina")
comprobar(L._espera_sugerida(RuntimeError("sin dato")) == 20.0,
          "…y si no la dice, se usa una por defecto")
comprobar(L._espera_sugerida(RuntimeError("{'retryDelay': '9999s'}")) <= 65.0,
          "La espera está acotada: nadie se queda colgado diez minutos")

# El limitador cuenta llamadas en ventana de 60 s. Se comprueba la contabilidad,
# sin dormir de verdad.
_rpm_guardado = L.LIMITE_POR_MINUTO
L.LIMITE_POR_MINUTO = 3
L._RITMO.clear()
for _ in range(3):
    L._esperar_turno()
comprobar(len(L._RITMO) == 3, "El limitador lleva la cuenta de las llamadas recientes")
L._RITMO.clear()
L.LIMITE_POR_MINUTO = _rpm_guardado

# El panel: una llamada por juez, no una por juez y criterio
_cs = [JU.criterio(str(i), f"Criterio {i}", "¿?", "porque sí") for i in range(4)]
L.consultar = lambda p, t, e, sin_cache=False: {"votos": []}
_coste = JU.coste(_cs, "evidencia")
comprobar(_coste["total"] == len(JU.ORDEN_PERSPECTIVAS),
          f"Con {len(_cs)} criterios el panel cuesta {len(JU.ORDEN_PERSPECTIVAS)} "
          f"llamadas, no {len(_cs) * len(JU.ORDEN_PERSPECTIVAS)}",
          str(_coste))
comprobar(_coste["total"] <= L.LIMITE_POR_MINUTO,
          "…y cabe dentro del límite del nivel gratuito sin esperar")
L.consultar = _consulta_real

# ---------------------------------------------------------------------------
print("\n18 · Álvaro · ¿se puede rehacer la ordenación desde fuera?")
# Historia de este bloque, que conviene no borrar.
#
# La primera versión del caso 11 preguntaba si la puntuación seguía a la
# desviación en los `parametros_justificativos`. Encontró inversiones reales y se
# las pasé a Álvaro. Su respuesta (27/08) fue que el diagnóstico era correcto pero
# la conclusión no: esos ocho parámetros son los filtros de la Capa 1, seis valen
# cero y los otros dos suman menos del 10 %; quien decide son siete categóricos
# secundarios que no se publican. Es decir, **mi caso marcaba como incoherentes
# salidas que eran correctas**.
#
# Así que el caso 11 cambió de pregunta. Ya no supone qué parámetro debería pesar
# más —esa suposición era el error— sino que rehace la cuenta que Álvaro declara:
# suma de contribuciones, normalización min-max dentro del grupo, y comparación
# contra lo emitido. Lo que antes era el caso es ahora un hallazgo de
# trazabilidad, que informa y no puntúa.
#
# Estas comprobaciones existen para que ese cambio no se pueda deshacer sin darse
# cuenta: la número 3 es literalmente «no vuelvas a marcar esto como fallo».
from modulos import similitud as SIM

_ruta_contrib = guion.RAIZ / "similitud" / "contribuciones_peso_semantico_0.csv"
_contrib = (SIM.cargar_contribuciones(_ruta_contrib.read_text(encoding="utf-8"))
            if _ruta_contrib.is_file() else None)
comprobar(_contrib is not None and set(_contrib) == {"SYN-0041", "SYN-0052"},
          "La tabla de contribuciones de Álvaro se lee y cubre los dos grupos",
          str(sorted(_contrib or [])))
comprobar(_contrib is not None
          and sum(len(v) for v in _contrib.values()) == 17,
          "…con las 17 candidatas supervivientes",
          str(sum(len(v) for v in (_contrib or {}).values())))

_esperado_rep = {
    "caso1_syn0047_acierto.json": ("pendiente", "la tabla no cubre el grupo "
                                                "SYN-0047: no se puede rehacer, "
                                                "pero tampoco se acusa"),
    "caso2_syn0041_fallo_conocido.json": ("pasa", "las 10 puntuaciones se rehacen "
                                                  "desde las contribuciones"),
    "caso3_syn0052_distractores.json": ("pasa", "las 7 se rehacen, incluidas las "
                                                "que antes marcaba como inversión"),
    "caso4_lista_vacia.json": ("pendiente", "sin resultados no hay escala min-max "
                                            "que rehacer"),
}

for _fich, (_esp, _razon) in _esperado_rep.items():
    _ruta = guion.RAIZ / "similitud" / _fich
    if not _ruta.is_file():
        comprobar(False, f"Falta {_fich}")
        continue
    _d, _ = SIM.interpretar(_ruta.read_text(encoding="utf-8"))
    _e, _c = SIM.verdad_de_campo(_d, contribuciones=_contrib)
    _evs = SIM.evaluar(_e, _c)
    comprobar(_evs["casos"][11]["resultado"] == _esp,
              f"{_fich[:26]} · caso 11 → {_esp} ({_razon})",
              _evs["casos"][11]["resultado"])

# El corazón del caso: la reproducción es exacta dentro del redondeo de la tabla.
_d3, _ = SIM.interpretar((guion.RAIZ / "similitud" /
                          "caso3_syn0052_distractores.json").read_text(encoding="utf-8"))
_rep = SIM.reproducir_ranking(_d3, _contrib)
comprobar(_rep["exigible"] and _rep["n"] == 7 and not _rep["discrepancias"],
          "Las 7 puntuaciones de SYN-0052 se rehacen sumando contribuciones",
          f"n={_rep['n']} discrepancias={len(_rep['discrepancias'])}")
comprobar(_rep["peor_delta"] <= SIM.TOL_REPRODUCCION,
          "…con una diferencia máxima dentro del redondeo de la tabla",
          f"{_rep['peor_delta']}")
comprobar(_rep["orden_coincide"],
          "…y el orden rehecho es exactamente el publicado",
          " > ".join(_rep["orden_rehecho"][:3]))

# Sin tabla el caso queda PENDIENTE, nunca falla. Un evaluador que acusa sin poder
# demostrarlo es justo lo que este sistema le reprocha a los módulos que evalúa.
_sin = SIM.reproducir_ranking(_d3, None)
comprobar(not _sin["exigible"] and "tabla" in _sin["motivo"],
          "Sin la tabla el caso queda pendiente y declara qué le falta",
          _sin["motivo"])

# Y si la puntuación NO se dedujera de las contribuciones, el caso lo cazaría:
# el caso discrimina, no está puesto para salir verde.
_trucado = _json.loads(_json.dumps(_d3))
_trucado["resultados"][1]["puntuacion"] = 0.95   # SYN-0092, que emite 0,6458
_rept = SIM.reproducir_ranking(_trucado, _contrib)
comprobar(_rept["exigible"] and _rept["discrepancias"],
          "Una puntuación manipulada rompe la reproducción: el caso discrimina",
          str(len(_rept["discrepancias"])))

# El diagnóstico viejo sigue calculándose, pero ya no acusa: es un hallazgo.
_e3, _c3 = SIM.verdad_de_campo(_d3, contribuciones=_contrib)
_ev3 = SIM.evaluar(_e3, _c3)
comprobar(any("no explica la posición" in h["titulo"] for h in _ev3["hallazgos"]),
          "La correlación negativa se conserva como hallazgo de trazabilidad, "
          "no como caso fallado",
          "; ".join(h["titulo"][:40] for h in _ev3["hallazgos"]))
comprobar(_ev3["casos"][11]["resultado"] == "pasa",
          "…y el caso 11 pasa: `parametros_justificativos` es informativo y el "
          "evaluador ya no lo trata como si explicara el ranking")

_cal = SIM.revisar_calibracion(_d3)
comprobar(_cal["rho"] is not None and _cal["rho"] < 0,
          "La correlación se sigue midiendo y sigue siendo negativa: el dato no se "
          "borra, se reinterpreta", str(_cal["rho"]))

# Y la consulta se explica en cristiano antes de enseñar ningún veredicto
_rc = SIM.resumen_consulta(_d3)
comprobar(_rc["pedido"].startswith("SYN-0052") and "distractores" in _rc["nota"],
          "El resumen de la consulta separa el pedido de la nota de Álvaro",
          f"{_rc['pedido']} || {_rc['nota'][:40]}")
comprobar(_rc["corpus"] == _rc["resultados"] + _rc["descartados"],
          "…y dice cuántas candidatas se evaluaron en total")

# ---------------------------------------------------------------------------
print("\n19 · Martín · el primer documento real, y lo que trajo consigo")
# Hasta el 28/08 la batería de Martín estaba cerrada y sin ejercitar: no había
# salida del módulo con la que contrastar. El primer documento real cambió tres
# cosas de golpe, y las tres están aquí para que no se deshagan sin darse cuenta:
#
#   1. Es una fotocopia. Cero bytes de texto. La rama entera dependía de que los
#      PDF tuvieran capa de texto, así que sin OCR el veredicto habría sido
#      «no se ha podido comprobar» sobre todo el corpus de RALSA.
#   2. El plazo va escrito con letra —«CATORCE AÑOS»— y el vencimiento no está
#      escrito en ninguna parte: se deriva. Los contratos sintéticos siempre lo
#      traían en cifra y con fecha final explícita. Una batería que sólo ve
#      documentos fabricados aprende la forma del fabricante.
#   3. Le faltan dos páginas, y eso se sabe sin ninguna fuente externa: el propio
#      pie dice «Página N de 10» y el fichero tiene 8.
from nucleo import pdf as PDFN
from nucleo.texto import duracion_dias, restar_duracion

# --- Integridad: el documento como testigo de sí mismo
_pie = "\n".join(f"cláusula ... ARR_DIR_2014 Página {n} de 10" for n in
                 [1, 2, 3, 4, 5, 6, 9, 10])
_int = PDFN.integridad(_pie, 8)
comprobar(_int["paginas_declaradas"] == 10 and _int["paginas_fichero"] == 8,
          "Se cuentan las páginas dos veces: las del fichero y las que el "
          "documento dice tener", str(_int))
comprobar(_int["faltantes"] == [7, 8] and _int["completo"] is False,
          "…y se dice cuáles faltan, no sólo cuántas: no es lo mismo perder la "
          "portada que la cláusula de resolución", str(_int["faltantes"]))
comprobar(PDFN.integridad("\n".join(f"Página {n} de 3" for n in (1, 2, 3)),
                          3)["completo"] is True,
          "Un documento completo se declara completo")
comprobar(PDFN.integridad("un documento sin pie numerado", 4)["completo"] is None,
          "Sin numeración en el pie no se afirma nada: no hay testigo interno")

# --- Unidades: tres meses no son noventa días
comprobar(duracion_dias("3 meses")[:2] == (3, "meses"),
          "«3 meses» se lee como meses, no como 90 días sueltos")
comprobar(duracion_dias("un año")[:2] == (1, "anos"),
          "…y «un año» escrito con letra también")
_v = date(2030, 1, 15)
comprobar(restar_duracion(_v, 3, "meses") == date(2029, 10, 15),
          "Tres meses antes del 15/01/2030 es el 15/10/2029",
          str(restar_duracion(_v, 3, "meses")))
comprobar(restar_duracion(_v, 90, "dias") == date(2029, 10, 17),
          "…y noventa días antes es el 17/10/2029: dos días de diferencia que en "
          "una fecha crítica no son redondeo", str(restar_duracion(_v, 90, "dias")))

# --- Prórroga: el discriminante es el verbo, no la palabra «prórroga»
_expresa = ("Vencido dicho plazo, las partes podrán convenir una o más prórrogas "
            "del mismo, mediante acuerdo expreso entre ambas partes, conseguido "
            "con una antelación de 3 meses a la fecha de extinción.")
_tacita = ("Llegado el vencimiento, el contrato se prorrogará automáticamente por "
           "periodos anuales salvo denuncia con 60 días de antelación.")
comprobar(vigencia.extraer(_expresa)["prorroga_tipo"] == "expresa",
          "«podrán convenir… mediante acuerdo expreso» se lee como prórroga expresa",
          vigencia.extraer(_expresa)["prorroga_tipo"])
comprobar(vigencia.extraer(_tacita)["prorroga_tipo"] == "tacita",
          "«se prorrogará automáticamente» se lee como prórroga tácita",
          vigencia.extraer(_tacita)["prorroga_tipo"])
comprobar(vigencia.extraer("un contrato que no dice nada de prórrogas"
                           )["prorroga_tipo"] == "no_consta",
          "Y cuando la cláusula no es concluyente no se elige: no consta")
comprobar(vigencia.extraer(_expresa + " " + _tacita)["prorroga_tipo"] == "no_consta",
          "Con las dos formas en el mismo texto tampoco se adivina — adivinar aquí "
          "es el fallo que este caso mide en el módulo evaluado")

# --- El plazo escrito con letra y el vencimiento derivado
_dur = ("La duración del presente Contrato se concierta por un plazo inicial de "
        "CATORCE AÑOS a contar desde el día 15 de enero de 2016, fecha prevista "
        "en el presente contrato para la cesión de la explotación.")
_c = vigencia.extraer(_dur)
comprobar(_c["anios_pactados"] == 14,
          "«plazo inicial de CATORCE AÑOS» se lee como 14", str(_c["anios_pactados"]))
comprobar(_c["fecha_caducidad"] == date(2030, 1, 15) and _c["caducidad_derivada"],
          "…y el vencimiento se deriva del inicio más el plazo, marcado como "
          "derivado y no como leído", str(_c["fecha_caducidad"]))

# --- Conciliación de identificadores: estricta a propósito
_esp2 = [{"id_documento": "CONTRATO_ARRENDAMIENTO_CRED"},
         {"id_documento": "OTRO_CONTRATO"}]
_rep2, _ren2 = vigencia.conciliar_ids(_esp2, [{"id_documento": "ARRENDAMIENTO_CRED"}])
comprobar(_rep2[0]["id_documento"] == "CONTRATO_ARRENDAMIENTO_CRED" and len(_ren2) == 1,
          "El documento que el módulo nombra por su ruta local se empareja con el "
          "mío cuando hay un único candidato", str(_ren2))
_amb = [{"id_documento": "CONTRATO_A_2024"}, {"id_documento": "CONTRATO_A_2025"}]
_rep3, _ren3 = vigencia.conciliar_ids(_amb, [{"id_documento": "CONTRATO_A"}])
comprobar(not _ren3 and _rep3[0]["id_documento"] == "CONTRATO_A",
          "Con dos candidatos no se elige: emparejar mal mueve un veredicto de un "
          "documento a otro sin que se note")

# --- La salida real de IAlert, leída de su propia ficha
_regs, _av = vigencia.interpretar(vigencia.SALIDA_IALERT_CRED)
_est = [r for r in _regs if r["tipo"] == "estado"]
_evt = [r for r in _regs if r["tipo"] == "evento"]
comprobar(len(_est) == 1 and _est[0]["estado"] == "vigente",
          "La ficha de campos de IAlert se lee: un estado, «vigente»",
          str([(r["tipo"], r.get("estado")) for r in _regs]))
comprobar(_est[0]["prorroga_tacita"] is True and _est[0]["preaviso_dias"] == 90
          and _est[0]["fecha_critica"] is None and _est[0]["paginas"] == 8,
          "…con los campos que deciden los casos nuevos: prórroga, preaviso, fecha "
          "crítica y páginas",
          str({k: _est[0].get(k) for k in
               ("prorroga_tacita", "preaviso_dias", "fecha_critica", "paginas")}))
comprobar(len(_evt) == 1 and _evt[0]["dias"] == 140,
          "La alerta de la cabecera viaja como evento, no como estado",
          str([(e.get("evento"), e.get("dias")) for e in _evt]))

# --- La ficha se pega de seis formas distintas y las seis tienen que valer.
# El modo de fallo real de este intérprete no es equivocarse: es no reconocer
# nada y mandar a rellenar la tabla a mano, que es el trabajo que el sistema
# venía a ahorrar. Al copiar una tabla del navegador, el nombre del campo y su
# valor caen en líneas separadas — la forma más natural de pegarla era justo la
# única que no funcionaba.
_BASE = {
    "Archivo": "C:\\Users\\marti\\Documents\\datos\\ARRENDAMIENTO CRED.pdf",
    "Ciudad": "Calatorao", "Dirección": "—", "Fecha de firma": "2015-12-10",
    "Fecha de inicio": "2016-01-15", "Plazo": "14 años",
    "Fecha de vencimiento": "2030-01-15", "Prórroga tácita": "✓",
    "Preaviso (días)": "90", "Fecha crítica de alerta": "—",
    "Número de páginas": "8"}
_CAB = ("CONTRATO ARRENDAMIENTO CRED\nVigente\n"
        "Actualización anual de la renta por IPC (140 días)\n"
        "El documento se puede usar como referencia válida.\n")

_FORMAS = {
    "líneas alternas": _CAB + "Valor\n" + "\n".join(f"{k}\n{v}"
                                                    for k, v in _BASE.items()),
    "líneas alternas con blancos": _CAB + "\n\n".join(f"{k}\n\n{v}"
                                                      for k, v in _BASE.items()),
    "tabulador": _CAB + "\n".join(f"{k}\t{v}" for k, v in _BASE.items()),
    "barra vertical": _CAB + "\n".join(f"{k} | {v}" for k, v in _BASE.items()),
    "dos puntos": _CAB + "\n".join(f"{k}: {v}" for k, v in _BASE.items()),
    "espacios": _CAB + "\n".join(f"{k}    {v}" for k, v in _BASE.items()),
}
for _nombre, _txt in _FORMAS.items():
    _r, _ = vigencia.interpretar(_txt)
    _e = [x for x in _r if x["tipo"] == "estado"]
    comprobar(len(_e) == 1 and _e[0]["estado"] == "vigente"
              and _e[0]["fecha_caducidad"] == "15/01/2030"
              and _e[0]["prorroga_tacita"] is True and _e[0]["preaviso_dias"] == 90
              and _e[0]["fecha_critica"] is None and _e[0]["paginas"] == 8,
              f"La ficha pegada «{_nombre}» se lee igual y entera",
              str([(x["tipo"], x.get("estado")) for x in _r]))

# Dos fichas pegadas seguidas son dos documentos, no uno con los campos del
# primero: si se fundieran, el evaluador acusaría a Martín de dejarse sin
# clasificar documentos que sí clasificó.
_dos = (_CAB + "\n".join(f"{k} | {v}" for k, v in _BASE.items()) + "\n\n"
        + "CESION USO NORTE\nObsoleto\n"
        + "\n".join(f"{k} | {v}" for k, v in
                    dict(_BASE, **{"Archivo": "C:\\Users\\marti\\CESION USO NORTE.pdf",
                                   "Fecha de vencimiento": "2024-03-01",
                                   "Prórroga tácita": "✗",
                                   "Número de páginas": "5"}).items()))
_r2 = [x for x in vigencia.interpretar(_dos)[0] if x["tipo"] == "estado"]
comprobar([(x["id_documento"], x["estado"], x["paginas"]) for x in _r2]
          == [("ARRENDAMIENTO_CRED", "vigente", 8),
              ("CESION_USO_NORTE", "obsoleto", 5)],
          "Dos fichas pegadas seguidas son dos documentos, con sus campos propios",
          str([(x["id_documento"], x["estado"], x["paginas"]) for x in _r2]))

# Y cuando de verdad no se reconoce nada, se dice qué se ha visto.
_diag = vigencia.diagnosticar("cualquier cosa que no es una ficha\notra línea suelta")
comprobar(_diag["lineas"] == 2 and not _diag["reconocidas"] and _diag["sueltas"],
          "Si no se reconoce nada, el diagnóstico enseña las líneas que sobran en "
          "vez de mandar a adivinar el formato", str(_diag["sueltas"]))

# --- El paso de la demo, de extremo a extremo
_paso_v = next(p for p in guion.PASOS if p["id"] == "vigencia")
_e_v, _d_v = guion.ejecutar_paso(_paso_v, date(2026, 8, 28))
comprobar(_e_v == "ejecutado",
          "El paso de Martín se ejecuta: hay documento real y salida real",
          str(_e_v))
if _e_v == "ejecutado":
    _cv = _d_v["ev"]["casos"]
    comprobar(_cv[1]["resultado"] == "pasa" and _cv[3]["resultado"] == "pasa",
              "Coinciden en lo que sí acierta: el estado y la fecha de vencimiento",
              f"1→{_cv[1]['resultado']} 3→{_cv[3]['resultado']}")
    comprobar(_cv[11]["resultado"] == "no_pasa"
              and "expresa" in _cv[11]["observacion"],
              "Caso 11 · el módulo marca prórroga tácita y la cláusula la exige "
              "expresa — son comportamientos opuestos al vencer",
              _cv[11]["observacion"][:90])
    comprobar(_cv[12]["resultado"] == "no_pasa"
              and "15/10/2029" in _cv[12]["observacion"],
              "Caso 12 · la fecha crítica no se emite, teniendo los dos sumandos "
              "para calcularla", _cv[12]["observacion"][:90])
    # La integridad del escaneo se retiró como caso el 28/08 y quedó como
    # hallazgo: el módulo clasifica vigencia, y la vigencia la decide la cláusula
    # de duración, no que al escaneo le falten hojas. Sigue informando.
    comprobar(13 not in _cv,
              "La integridad del escaneo ya no puntúa: no es el trabajo de este "
              "módulo", str(sorted(_cv)))
    _h_int = [h for h in _d_v["ev"]["hallazgos"] if "incompletos" in h["titulo"]]
    comprobar(_h_int and "faltan la(s) 7, 8" in _h_int[0]["detalle"],
              "…pero se conserva como hallazgo, con las páginas que faltan",
              _h_int[0]["detalle"][:100] if _h_int else "sin hallazgo")
    comprobar(any("OCR" in h["titulo"] for h in _d_v["ev"]["hallazgos"]),
              "La vía de lectura se declara: lo comparado es una lectura contra "
              "otra lectura, y el veredicto lo dice")
    comprobar(all(_cv[n]["resultado"] != "no_pasa" for n in (1, 2, 3, 9)),
              "El evaluador no acusa de lo que el módulo hace bien: un banco que "
              "sólo suspende no discrimina")

# ---------------------------------------------------------------------------
print("\n20 · El segundo documento real: una escritura de 1995")
# La escritura de derecho de superficie enseñó el límite del lector determinista.
# El OCR de una máquina de escribir de hace treinta años devuelve «cuatroúe
# abril» y pierde el año entero; ninguna regla saca una fecha de ahí. Lo que este
# bloque fija no es que el evaluador lo lea —no puede— sino que **no acuse por no
# saber leer**, que es la única forma de equivocarse que le quita autoridad.
from nucleo.texto import numero_en_letra as _nl
from nucleo.texto import fecha_de as _fecha_de
from nucleo.texto import anios_de as _anios_de

comprobar(_nl("veinticinco") == 25 and _nl("mil novecientos noventa y cinco") == 1995
          and _nl("dos mil quince") == 2015,
          "Los números escritos con letra se leen: las escrituras notariales no "
          "usan cifras", f"{_nl('veinticinco')}/{_nl('mil novecientos noventa y cinco')}")
comprobar(_fecha_de("a cuatro de abril de mil novecientos noventa y cinco")
          == date(1995, 4, 4),
          "…y las fechas con ellos")
comprobar(vigencia.clasificar("derecho de superficie y facultas aedificandi")
          == "superficie",
          "El corpus real de RALSA no son sólo arrendamientos")

# La cláusula correcta, no la primera que aparezca.
_escritura = ("Sexta. El plazo de vigencia del referido derecho de superficie será "
              "de veinticinco años, contados desde la inscripción de esta escritura "
              "en el Registro de la Propiedad. Séptima. Repsol deberá hacer uso de "
              "la facultas aedificandi dentro del plazo de cinco años que a tal "
              "efecto establece el artículo 16 del Reglamento Hipotecario.")
comprobar(_anios_de(_escritura) == 25,
          "El plazo sale de la cláusula de duración, no del primer «plazo de N "
          "años» del documento — leer 5 en vez de 25 parecería verificado",
          str(_anios_de(_escritura)))

# Prórroga expresa + vencido = caducado. Antes quedaba en «no clasificado» y el
# módulo de Martín, que decía «Obsoleto», parecía equivocarse. Se equivocaba la
# regla.
_venc = vigencia.extraer(
    "El plazo de duración será de veinticinco años desde el 4 de abril de 1995. "
    "En caso de que al término del plazo las partes podrán convenir una prórroga "
    "mediante acuerdo expreso.")
_venc = dict(_venc, fecha_caducidad=date(2020, 4, 4), prorroga_tipo="expresa")
comprobar(vigencia.estado_esperado(_venc, date(2026, 8, 28))[0] == "caducado",
          "Vencido y con prórroga por acuerdo expreso es caducado: no acordar nada "
          "no prolonga nada", vigencia.estado_esperado(_venc, date(2026, 8, 28))[0])
_venc2 = dict(_venc, prorroga_tipo="no_consta")
comprobar(vigencia.estado_esperado(_venc2, date(2026, 8, 28))[0] == "no_clasificado",
          "…pero si la cláusula no es concluyente sigue sin poder afirmarse")

# «Obsoleto» de IAlert vale para caducado y para sustituido: dos estados no
# pueden acertar una distinción de cinco.
comprobar(("caducado", "obsoleto") in vigencia.EQUIVALENTES,
          "«Obsoleto» se acepta para un documento vencido: exigirle a un módulo de "
          "dos estados el vocabulario de cinco sería medirle contra otra regla")

# Y lo esencial: abstenerse en vez de acusar.
_doc_ciego = {"nombre": "ESCRITURA.pdf", "id": "ESCRITURA", "capa": False,
              "via": "ocr", "legible": True, "paginas": 20, "integridad": {},
              "texto": "escritura ilegible sin cláusula de duración reconocible"}
_e_c, _ctx_c = vigencia.verdad_de_campo([_doc_ciego], date(2026, 8, 28))
comprobar(_e_c[0]["abstiene"] is True,
          "Sobre un escaneo cuya cláusula no se ha sabido leer, el evaluador se "
          "abstiene", _e_c[0]["motivo"][:80])
_ev_c = vigencia.evaluar(_e_c, [{"tipo": "estado", "id_documento": "ESCRITURA",
                                 "estado": "obsoleto", "fecha_caducidad": None,
                                 "cita": True}], date(2026, 8, 28), contexto=_ctx_c)
comprobar(_ev_c["casos"][1]["resultado"] == "pendiente",
          "…y el caso 1 queda pendiente, no fallado: mi ceguera no es su fallo",
          _ev_c["casos"][1]["resultado"])
comprobar(_ev_c["contraste"]["precision"] in (None, 100.0),
          "…y la precisión no baja por un documento que yo no he sabido leer",
          str(_ev_c["contraste"]["precision"]))
comprobar(any("abstiene" in h["titulo"] for h in _ev_c["hallazgos"]),
          "La abstención se declara como hallazgo, con qué haría falta para cerrarla")

# Un documento legible SIN plazo sigue siendo un veredicto, no una abstención:
# ahí «vigencia no determinada» lo dice el documento, no mi lector.
_doc_sin = {"nombre": "SIN.pdf", "id": "SIN", "capa": True, "via": "capa_texto",
            "legible": True, "paginas": 2, "integridad": {},
            "texto": "Acuerdo marco sin plazo de duración pactado entre las partes."}
_e_s, _ = vigencia.verdad_de_campo([_doc_sin], date(2026, 8, 28))
comprobar(not _e_s[0]["abstiene"] and _e_s[0]["estado"] == "no_clasificado",
          "Un documento legible sin plazo no es una abstención: es un veredicto")

# ---------------------------------------------------------------------------
print("\n21 · El corpus real completo: trece escaneos de RALSA")
# Trece documentos, ni uno con capa de texto. El lector determinista leía UNO.
# Lo que sigue fija los cuatro cambios que lo subieron a siete, y sobre todo el
# que impide que subir de siete a nueve se pague con un veredicto equivocado.

# 1 · La ambigüedad se declara, no se resuelve a la primera.
from nucleo.texto import fecha_unica, fechas_candidatas
_renov = ("se amplió el plazo de duración del contrato hasta el 31 de octubre de "
          "2019. Se amplía la duración por diez años, por lo que el mismo "
          "finalizará el 31 de octubre de 2029.")
_cands = fechas_candidatas(_renov, vigencia.P_FIN)
comprobar(len(_cands) == 2,
          "En una renovación hay dos fechas de fin: la que narra y la que pacta",
          str([f.isoformat() for f, _ in _cands]))
_f, _cita, _av = fecha_unica(_renov, vigencia.P_FIN)
comprobar(_f is None and _av and "2 fechas" in _av,
          "Con dos candidatas no se elige la primera: se declara la ambigüedad. "
          "Elegir habría dado «caducado» sobre un contrato vigente hasta 2029",
          str(_av)[:80])
_uno = "El contrato finalizará el 31 de octubre de 2029."
comprobar(fecha_unica(_uno, vigencia.P_FIN)[0] == date(2029, 10, 31),
          "…y con una sola candidata se lee sin más")

# 2 · La familia decide qué se le puede exigir al documento.
comprobar(vigencia.familia_de("ADDENDUM AL CONTRATO DE ARRENDAMIENTO SUSCRITO EL "
                              "10 DE DICIEMBRE DE 2015 ENTRE …")[0] == "modificativo",
          "«Addendum al contrato» es un documento que modifica a otro")
comprobar(vigencia.familia_de("NOTIFICACION DE PRORROGA DE CONTRATO DE "
                              "ARRENDAMIENTO DEL LOCAL …")[0] == "modificativo",
          "…y «prórroga de contrato» también: el patrón es acto + documento, no "
          "una lista de palabras")
comprobar(vigencia.familia_de("CONTRATO DE ARRENDAMIENTO. REUNIDOS … CLAUSULAS. "
                              "DECIMOSEGUNDO.- SUBROGACION. Se autoriza la "
                              "subrogación del arrendatario.")[0] == "principal",
          "Un contrato con una cláusula de subrogación sigue siendo un contrato: "
          "la familia se lee del encabezamiento, no de sus partes")
comprobar(vigencia.familia_de("ESCRITURA. El plazo de vigencia del derecho de "
                              "superficie será de veinticinco años. Contra la "
                              "presente Resolución cabe recurso de alzada.")[0]
          == "principal",
          "…y «la presente Resolución» de un anejo administrativo no convierte "
          "una escritura en un documento modificativo")

_mod = vigencia.extraer("ANEXO AL CONTRATO DE ARRENDAMIENTO SUSCRITO ENTRE LAS "
                        "PARTES. Las partes acuerdan modificar la renta.")
# El vocabulario es el de la prueba inicial y el de la corrección de Fabián a la
# pregunta 8: cuando falta la fecha sólo hay dos salidas, y lo que decide es si el
# documento TIENE QUE tener una. Que dependa de otro es el motivo, no un estado
# aparte — tuvo uno propio (`depende_de_otro`) y se retiró el 28/08, porque
# inventar vocabulario habría medido a Martín contra una regla que nadie acordó.
_mod_ata = vigencia.extraer(
    "ANEXO AL CONTRATO DE ARRENDAMIENTO. REPSOL COMERCIAL aporta la cantidad "
    "necesaria para amortizar la reforma; si el contrato se resolviera con "
    "anterioridad al plazo de duración pactado, se facturará una vez extinguido "
    "el contrato.")
_e_ata, _m_ata = vigencia.estado_esperado(_mod_ata, date(2026, 8, 28))
comprobar(_e_ata == "no_clasificado" and "debería tener una" in _m_ata,
          "Un anexo que ata obligaciones al plazo del contrato SÍ debería tener "
          "vencimiento: falta la fecha y se echa de menos", f"{_e_ata} · {_m_ata[:60]}")

_mod_suelto = vigencia.extraer(
    "ANEXO AL CONTRATO DE ARRENDAMIENTO. Las partes acuerdan que la facturación "
    "mensual se emita el día cinco de cada mes.")
_e_su, _m_su = vigencia.estado_esperado(_mod_suelto, date(2026, 8, 28))
comprobar(_e_su == "titulo_consumado" and "no la hay que buscar" in _m_su,
          "…y uno que sólo cambia la facturación se agota al firmarse: no es que "
          "le falte la fecha, es que no la tiene que tener",
          f"{_e_su} · {_m_su[:60]}")
_mod_con = vigencia.extraer("ANEXO AL CONTRATO. No obstante lo establecido en la "
                            "cláusula SEGUNDA, la fecha de inicio del mismo será "
                            "el 19 de enero de 2016, finalizando en consecuencia "
                            "el 19 de enero de 2030.")
comprobar(vigencia.estado_esperado(_mod_con, date(2026, 8, 28))[0] == "vigente",
          "…pero un anexo que SÍ trae sus fechas se juzga como cualquier otro")

# 3 · Lo que el documento afirma manda sobre lo que su familia permite preguntar.
_cons = vigencia.extraer("Aportación económica de REPSOL a la reforma. La "
                         "aportación ha sido íntegramente abonada y la obra "
                         "finalizada, quedando agotado el objeto.")
comprobar(vigencia.estado_esperado(_cons, date(2026, 8, 28))[0] == "titulo_consumado",
          "Una aportación que declara agotado su objeto es título consumado, no "
          "«sin vigencia que determinar»", vigencia.estado_esperado(_cons, date(2026,8,28))[0])

# 4 · El conjunto, medido de una vez.
_corpus = pathlib.Path("/home/claude/martin/corpus")
if _corpus.is_dir():
    from nucleo import pdf as _P
    _docs = [_P.leer(x) for x in sorted(_corpus.glob("*.pdf"))]
    _esp, _ = vigencia.verdad_de_campo(_docs, date(2026, 8, 28))
    _con = [e for e in _esp if not e["abstiene"]]
    comprobar(len(_esp) == 13 and len(_con) >= 7,
              f"Sobre los 13 escaneos reales de RALSA se emite veredicto en "
              f"{len(_con)}; el resto se declara abstención, no fallo del módulo",
              f"{len(_con)}/{len(_esp)}")
    comprobar(all(d["via"] == "ocr" for d in _docs),
              "Ninguno de los trece trae capa de texto: el OCR no es un extra, es "
              "la única puerta")
else:
    print("  ·  (corpus de RALSA no disponible en este equipo; bloque omitido)")

# ---------------------------------------------------------------------------
print("\n22 · Anclaje: cómo se comprueba lo que dice el modelo")
# El modo asistido pasa de rescate ocasional a vía principal en cuanto el corpus
# son escaneos, y eso cambia lo que está en juego: si la verdad de campo sale de
# un modelo, un error suyo acusa a un compañero de un fallo que no ha cometido.
# La respuesta no es confiar más ni menos, es no tener que confiar — cada valor
# viene con el fragmento que lo sostiene y el fragmento se busca en el documento.
# La comprobación no usa modelo: es búsqueda de texto y sale igual las mil veces.
_texto_doc = (
    "SEGUNDA: DURACION. La duración del presente Contrato de Arrendamiento de "
    "Industria se concierta por un plazo inicial de CATORCE AÑOS a contar desde "
    "el día 15 de enero de 2016. En Madrid, a 10 de Diciembre de 2015. "
    "Vencido dicho plazo, las partes podrán convenir una o más prórrogas del "
    "mismo, mediante acuerdo expreso entre ambas partes, conseguido con una "
    "antelación de 3 meses. El derecho de tanteo podrá ejercitarse en el plazo "
    "de 60 días naturales. ARR_DIR_2014 Página 6 de 10.")

for _cita, _debe in [
        ("plazo inicial de CATORCE AÑOS a contar desde el día 15 de enero de 2016", True),
        ("En Madrid, a 10 de Diciembre de 2015", True),
        ("las partes podrán convenir una o más prórrogas mediante acuerdo expreso", True),
        # Inventadas: cambian el dato y conservan la prosa, que es exactamente
        # como se equivoca un modelo cuando se equivoca.
        ("En Madrid, a 10 de Diciembre de 2017", False),
        ("plazo inicial de VEINTE AÑOS a contar desde el día 15 de enero de 2016", False),
        ("conseguido con una antelación de 6 meses", False),
        ("el contrato se prorrogará automáticamente por periodos anuales", False)]:
    _ok, _p = L.fragmento_presente(_cita, _texto_doc)
    comprobar(_ok is _debe,
              f"{'Se acepta' if _debe else 'Se rechaza'}: «{_cita[:52]}…»",
              f"presente={_ok} proporción={_p}")

comprobar(not L.fragmento_presente("a 10 de Diciembre de 2017", _texto_doc)[0],
          "Una fecha falsa no cuela porque su año aparezca en otra cláusula: se "
          "exige que las palabras estén JUNTAS, no que existan en el documento")

_c, _pr, _desc = L.anclar(
    {"fecha_emision": date(2015, 12, 10), "anios_pactados": 20},
    {"fecha_emision": "modelo", "anios_pactados": "modelo"},
    {"fecha_emision": "En Madrid, a 10 de Diciembre de 2015",
     "anios_pactados": "plazo inicial de VEINTE AÑOS"},
    _texto_doc, ["fecha_emision", "anios_pactados"])
comprobar(_c["fecha_emision"] == date(2015, 12, 10) and _c["anios_pactados"] is None,
          "El valor con cita buena entra; el de cita inventada se cae, aunque "
          "venga en la misma respuesta", str(_c))
comprobar("anios_pactados" in _desc and "descartado" in _pr["anios_pactados"],
          "…y el descarte se declara con su motivo: un valor que desaparece en "
          "silencio deja al veredicto sin explicación", str(_desc)[:90])

_c2, _pr2, _inc = vigencia.descartar_incoherentes(
    {"fecha_emision": date(2015, 12, 10), "fecha_inicio": date(2016, 1, 15),
     "fecha_caducidad": date(2028, 1, 15), "anios_pactados": 14},
    {"fecha_emision": "regla", "fecha_inicio": "regla",
     "fecha_caducidad": "modelo", "anios_pactados": "regla"})
comprobar(_c2["fecha_caducidad"] is None and _inc,
          "Aritmética contra el propio documento: 2016 más 14 años no da 2028, "
          "así que cae el vencimiento — y cae el del modelo, no el de la regla",
          str(_inc)[:100])
_c3, _pr3, _inc3 = vigencia.descartar_incoherentes(
    {"fecha_emision": date(2020, 1, 1), "fecha_inicio": date(2016, 1, 1),
     "fecha_caducidad": None, "anios_pactados": None},
    {"fecha_emision": "modelo", "fecha_inicio": "regla"})
comprobar(_c3["fecha_emision"] is None,
          "Una firma posterior al inicio es imposible: se descarta la del modelo")
_c4, _pr4, _inc4 = vigencia.descartar_incoherentes(
    {"fecha_emision": date(2015, 12, 10), "fecha_inicio": date(2016, 1, 15),
     "fecha_caducidad": date(2030, 1, 15), "anios_pactados": 14},
    {k: "modelo" for k in ("fecha_emision", "fecha_inicio", "fecha_caducidad",
                           "anios_pactados")})
comprobar(not _inc4 and _c4["fecha_caducidad"] == date(2030, 1, 15),
          "Y lo que cuadra no se toca: la comprobación descarta, no sospecha")

# ---------------------------------------------------------------------------
print("\n23 · Duración en escalera, y el prompt puesto al día")
# El contrato de Zurita lo enseñó, y lo enseñó el etiquetado a mano: «UN AÑO,
# prorrogándose por plazos anuales sucesivos hasta DIEZ, para volverse a
# prorrogar por CINCO hasta un máximo de QUINCE». El plazo pactado es el primer
# periodo; el contrato vive hasta el tope. Tratarlo como inicio + plazo daba por
# caducado en 2021 un contrato vigente en 2026 — el fallo más caro de este
# módulo, porque nadie vuelve a mirar un documento dado por muerto.
_esc = vigencia.extraer(
    "SEGUNDA. DURACIÓN. El plazo de vigencia del presente contrato comenzará a "
    "contarse desde el día uno de enero de 2020, siendo la duración del mismo de "
    "UN AÑO, prorrogándose por plazos anuales sucesivos hasta que alcance una "
    "duración de DIEZ AÑOS (10), para volverse a prorrogar por un periodo de "
    "CINCO AÑOS (5), hasta que alcance una duración máxima de QUINCE AÑOS (15).")
comprobar(_esc["duracion_escalonada"],
          "Se reconoce que la duración es una escalera de prórrogas y no un plazo")
comprobar(_esc["duracion_maxima_anios"] == 15,
          "…y se lee el tope, que es lo que de verdad marca el final",
          str(_esc["duracion_maxima_anios"]))
_e_esc, _m_esc = vigencia.estado_esperado(
    dict(_esc, fecha_inicio=date(2020, 1, 1)), date(2026, 8, 28))
comprobar(_e_esc == "vigente" and "15 años" in _m_esc,
          "Con el tope leído, el contrato está vigente en 2026 aunque el primer "
          "periodo venciera en 2021", f"{_e_esc} · {_m_esc[:70]}")
_e_fin, _ = vigencia.estado_esperado(
    dict(_esc, fecha_inicio=date(2000, 1, 1)), date(2026, 8, 28))
comprobar(_e_fin == "caducado",
          "…y caducado cuando el tope sí se ha cumplido: la regla discrimina")
_sin_tope = dict(_esc, duracion_maxima_anios=None, fecha_inicio=date(2020, 1, 1))
_e_st, _m_st = vigencia.estado_esperado(_sin_tope, date(2026, 8, 28))
comprobar(_e_st == "no_clasificado" and "no puede afirmarse que haya caducado" in _m_st,
          "Sin tope no se afirma nada: declarar caducado un contrato que se "
          "prorroga solo es el error que este caso existe para no cometer",
          f"{_e_st} · {_m_st[-60:]}")

# El prompt y el esquema tienen que llevar los campos que decide el sistema. Si
# el código aprende una distinción y el prompt no, el modelo no puede aportarla:
# la lectura se queda en la versión de ayer sin que nadie lo note.
_ESQ = set(vigencia.FICHA["esquema_campos"]["properties"])
for _c in ("familia", "requiere_fecha_caducidad", "duracion_escalonada",
           "duracion_maxima_anios", "citas"):
    comprobar(_c in _ESQ, f"El esquema del modelo declara «{_c}»")
    if _c != "citas":
        comprobar(_c in vigencia.CAMPOS_DEL_MODELO,
                  f"…y se le pide al modelo cuando la regla no llega: «{_c}»")
_P = vigencia.FICHA["prompt_extraccion"]
for _t, _q in [("ENCABEZAMIENTO", "que la familia se lee del encabezamiento"),
               ("se la echa de menos", "la regla de la pregunta 8 tal como la "
                                       "formuló Íñigo"),
               ("escalera de prórrogas", "que hay duraciones en escalera"),
               ("no se reduce a", "que una escalera no es inicio más plazo")]:
    comprobar(_t in _P, f"El prompt explica {_q}")

# ---------------------------------------------------------------------------
print("\n24 · La comprobación de despliegue mira las firmas, no sólo los nombres")
# Existe por un fallo real: `app.py` era nuevo, `ui.py` era viejo, y el aviso de
# «repositorio a medio subir» no saltó porque el `ui.py` viejo también tenía una
# función llamada `tabla_documentos`. Lo que había cambiado era su firma. La app
# arrancó sin quejarse y reventó con un TypeError al abrir el módulo de Martín —
# justo el error que ese aviso existe para que Íñigo no vea nunca.
import inspect as _insp
import types as _tipos
import ui as _ui
from nucleo import VERSION as _V_NUCLEO


def _falta_pieza(modulo, pieza):
    nombre, _, parametro = pieza.partition(":")
    objeto = getattr(modulo, nombre, None)
    if objeto is None:
        return True
    if not parametro:
        return False
    try:
        return parametro not in _insp.signature(objeto).parameters
    except (TypeError, ValueError):
        return False


_viejo = _tipos.SimpleNamespace(tabla_documentos=lambda docs, tipos, clasificar: None)
comprobar(_falta_pieza(_viejo, "tabla_documentos:extraer"),
          "Un `ui.py` de ayer se detecta por la firma que le falta")
comprobar(not _falta_pieza(_viejo, "tabla_documentos"),
          "…y no por el nombre, que el viejo también tiene: por eso no bastaba")
comprobar(not _falta_pieza(_ui, "tabla_documentos:extraer"),
          "El `ui.py` de hoy sí admite el extractor de campos")
comprobar(getattr(_ui, "VERSION_UI", 0) == _V_NUCLEO,
          "`ui.py` y `nucleo/` declaran la misma versión",
          f"ui {getattr(_ui, 'VERSION_UI', '—')} · nucleo {_V_NUCLEO}")

# Cada documento tiene su bloque, y el bloque enseña los ocho campos. La tabla
# de todos juntos sólo sobrevive donde no hay extractor —la rama de Juan—,
# porque allí es lo único que se puede enseñar.
_fuente_tabla = _insp.getsource(_ui.tabla_documentos)
comprobar("if extraer is None:" in _fuente_tabla,
          "La tabla resumen queda reservada a las ramas sin extractor de campos")
comprobar("no lo ha encontrado" in _fuente_tabla,
          "Un campo que no se ha leído se enseña como hueco, no se esconde")

# Y una carpeta que no se ha subido tiene que decirse con esa palabra. El
# traceback de Streamlit señalaba `esquema.py`, que es sólo el primer fichero que
# toca `modulos`: acusaba a un inocente y no nombraba la causa.
_fuente_app = pathlib.Path("app.py").read_text(encoding="utf-8")
_i_guarda = _fuente_app.find("_CARPETAS = {")
comprobar(0 < _i_guarda < _fuente_app.find("\nimport esquema"),
          "La comprobación de carpetas va ANTES del primer import que las usa")
for _c in ("nucleo", "modulos", "demo"):
    comprobar(f'"{_c}":' in _fuente_app[_i_guarda:_i_guarda + 600],
              f"Se comprueba que la carpeta `{_c}/` está subida")
comprobar("Falta una carpeta entera" in _fuente_app,
          "…y si no está, se dice con esas palabras y no con un ModuleNotFoundError")

# ---------------------------------------------------------------------------
print("\n25 · La caché de OCR identifica el fichero, no su nombre")
# El texto reconocido se guarda junto al PDF y se busca por nombre, porque un
# documento cambia de nombre al pasar por un correo o un zip. Pero el nombre es
# una etiqueta: si «20160119 ANEXO MODIFICADO» —otro documento— se lleva el texto
# del anexo de 2016, el evaluador emite un veredicto **leyendo otro documento**,
# con sus campos anclados a citas que existen en el sitio equivocado. Ni el
# anclaje ni la aritmética lo ven: son coherentes entre sí. Por eso una
# coincidencia parcial de nombre se corrobora comparando el fichero entero.
import shutil as _sh
import tempfile as _tmpf
from nucleo import pdf as _P

_CORPUS = pathlib.Path("demo/datos/vigencia")
if (_CORPUS / "20160119_ANEXO.pdf").is_file():
    with _tmpf.TemporaryDirectory() as _td:
        def _cache_para(fuente, nombre):
            d = pathlib.Path(_td) / f"{nombre}.pdf"
            _sh.copy(_CORPUS / fuente, d)
            return _P._cache_de(d)

        comprobar(_cache_para("202002_CTO_ALQUILER_ZURITA.pdf",
                              "copia de 202002 CTO ALQUILER ZURITA") is not None,
                  "El mismo fichero renombrado sigue aprovechando su lectura: "
                  "renombrar no cambia los bytes")
        comprobar(_cache_para("20160128_ANEXO.pdf",
                              "20160119_ANEXO_MODIFICADO") is None,
                  "Pero OTRO documento con nombre parecido no hereda el texto "
                  "del primero: se reconoce de verdad aunque tarde")
        comprobar(_cache_para("DERECHOS_SUPERFICIE.pdf",
                              "RESCATE_DERECHOS_SUPERFICIE_2") is None,
                  "…ni siquiera en el par que ya provocó este fallo una vez")
        comprobar(_cache_para("202002_CTO_ALQUILER_ZURITA.pdf",
                              "documento_que_nadie_ha_visto") is None,
                  "Un nombre sin parecido alguno no busca similitudes: escanea")

    _con_cache = sum(1 for p in _CORPUS.glob("*.pdf") if _P._cache_de(p))
    comprobar(_con_cache == 13,
              "Y los 13 escaneos del corpus siguen encontrando su lectura",
              str(_con_cache))
    _h = _P._huella(_CORPUS / "20160119_ANEXO.pdf")
    comprobar(_h == _P._huella(_CORPUS / "20160119_ANEXO.pdf") and len(_h) == 64,
              "La huella del fichero es estable y no depende del nombre")

# ---------------------------------------------------------------------------
print("\n26 · Las cuatro formas de escribir una fecha, y la cláusula de al lado")
# Íñigo lo vio mirando documento por documento: «la mayoría no reconoce las
# fechas de inicio ni de final». Tenía razón, y no era un fallo: eran tres formas
# de escribir una fecha que ningún patrón cubría. Las tres salen de documentos
# reales, no de casos inventados.
import re as _rex
from nucleo.texto import CORTE_CLAUSULA as _CC
from nucleo.texto import fecha_de as _fd
from nucleo.texto import fecha_unica as _fu

for _t, _esp, _por in [
    # el punto de millar, que escriben casi todas las escrituras
    ("31 de octubre de 2.017", date(2017, 10, 31), "el año lleva punto de millar"),
    ("uno de enero de 2.020", date(2020, 1, 1), "día en letra y año con punto"),
    # la cuarta combinación: día en cifra, año en letra
    ("26 de Enero de dos mil treinta", date(2030, 1, 26),
     "día en cifra y año en letra"),
    ("27 de Enero de dos mil dieciséis", date(2016, 1, 27),
     "…y la misma forma en el inicio"),
    # las que ya funcionaban, para que no se rompan
    ("a 22 de Mayo de 2020", date(2020, 5, 22), "la forma corriente"),
    ("cuatro de abril de mil novecientos noventa y cinco", date(1995, 4, 4),
     "todo en letra, como las escrituras antiguas"),
]:
    comprobar(_fd(_t) == _esp, f"Se lee «{_t}»: {_por}", str(_fd(_t)))

comprobar(_fd("31 de octubre de 20109") is None,
          "Un año imposible es un año mal reconocido: no se afirma nada. El OCR "
          "leyó 20109 y el evaluador venía afirmando 2010",
          str(_fd("31 de octubre de 20109")))

# La fecha de la cláusula de al lado no es la de ésta.
_BULL = ("El presente contrato tendrá una duración de 20 años, y comenzará, "
         "a-surir efecto desde el día 1 de noviembre del presente año, siendo su "
         "término sFañá 31 de octubre de 2.017.")
comprobar(_fu(_BULL, vigencia.P_INICIO, corte=_CC)[0] is None,
          "Un inicio sin año no se rellena con la fecha del término: el "
          "evaluador afirmaba que el contrato empezó el día en que acababa",
          str(_fu(_BULL, vigencia.P_INICIO, corte=_CC)[0]))
_GRA = ("El arriendo tendrá una duración de QUINCE AÑOS que principiarán a "
        "contarse desde el día 27 de Enero de dos mil dieciséis, por lo cual, el "
        "arriendo terminará el 26 de Enero de dos mil treinta.")
comprobar(_fu(_GRA, vigencia.P_INICIO, corte=_CC)[0] == date(2016, 1, 27)
          and _fu(_GRA, vigencia.P_FIN, corte=_CC)[0] == date(2030, 1, 26),
          "…y cuando cada cláusula tiene su fecha, se leen las dos")

# El preaviso, con la cantidad delante — que es como se dice en castellano.
for _t, _dias in [("con DOS MESES de antelación como mínimo", 60),
                  ("remitido con 3 meses de antelación a la propia", 90),
                  ("con una antelación mínima de 3 meses", 90),
                  ("un preaviso de 2 meses de tiempo", 60),
                  ("avisará con quince días de antelación", 15)]:
    _v = [duracion_dias(m.group(1) or m.group(2) or m.group(3))
          for m in _rex.finditer(vigencia.P_ANTELACION, _t, _rex.IGNORECASE)]
    _v = [x[2] for x in _v if x]
    comprobar(_dias in _v, f"Preaviso en «{_t[:44]}» → {_dias} días", str(_v))

# La prórroga, con las fórmulas del Código Civil y con el «no» delante.
for _t, _esp in [
    ("el contrato podrá ser prorrogado por la tácita, art. 1566", "tacita"),
    ("podrá prorrogarse de año en año, sucesivamente", "tacita"),
    ("prorrogándose por plazos anuales sucesivos", "tacita"),
    ("RENUNCIA DE LA TÁCITA RECONDUCCIÓN. el presente contrato no se "
     "prorrogará automáticamente", "renunciada"),
    ("las partes renuncian expresamente a la tácita reconducción", "renunciada"),
]:
    _ren = bool(_rex.search(vigencia.P_RENUNCIA, _t, _rex.IGNORECASE))
    _tac = bool(_rex.search(vigencia.P_PRORROGA_TACITA, _t, _rex.IGNORECASE))
    _exp = bool(_rex.search(vigencia.P_PRORROGA_EXPRESA, _t, _rex.IGNORECASE))
    _r = ("renunciada" if _ren else "expresa" if _exp and not _tac
          else "tacita" if _tac and not _exp else "no_consta")
    comprobar(_r == _esp, f"«{_t[:50]}» → {_esp}", _r)

# Y la escalera: tope leído pese al ruido del OCR, y sin fecha inventada.
_ESC2 = vigencia.extraer(
    "comenzará a contarse desde el día uno de enero de 2.020, siendo la "
    "duración del mismo de UN AÑO, prorrogándose por plazos anuales sucesivos "
    "hasta que alcance una duración de DIEZ AÑOS (10), para volverse a "
    "prorrogar por un periodo de CINCO AÑOS (5), hasta que alcance una "
    "duración máxima de | QUINCE AÑOS (15), fecha en que queda extinguido.")
comprobar(_ESC2["duracion_maxima_anios"] == 15,
          "El tope se lee aunque el OCR meta una barra suelta antes del número",
          str(_ESC2["duracion_maxima_anios"]))
comprobar(_ESC2["fecha_caducidad"] is None,
          "Una escalera no tiene UNA fecha de vencimiento, así que no se deriva "
          "ninguna: sumar el escalón al inicio daba una fecha que el documento "
          "no pacta",
          str(_ESC2["fecha_caducidad"]))
comprobar(any("escalera" in a for a in (_ESC2.get("ambiguedades") or [])),
          "…y se dice por qué está vacía, en vez de dejar el hueco mudo")

# ---------------------------------------------------------------------------
print("\n" + ("Todo correcto." if not fallos
              else f"{len(fallos)} comprobación(es) fallida(s):\n  - "
                   + "\n  - ".join(fallos)))
sys.exit(1 if fallos else 0)
