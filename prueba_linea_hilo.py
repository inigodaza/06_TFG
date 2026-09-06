"""
Mirar la línea del hilo de verdad, no imaginársela.

El validador comprueba colores; no comprueba que una etiqueta se solape con
otra, que un bloque se salga de su caja o que la espina caiga desalineada
respecto a los puntos. Eso sólo se ve mirando, así que este guion genera la
página suelta y la abre en un navegador para dejar una captura.

    python prueba_linea_hilo.py            → escribe /tmp/linea_hilo.html
    python prueba_linea_hilo.py --captura  → además guarda linea_hilo.png
"""

import sys
from pathlib import Path

import ui
from demo import caso

SALIDA = Path("/tmp/linea_hilo.html")


def _fases():
    """
    Las cuatro fases con los datos que hay hoy: la discrepancia real, la matriz
    de Pablo cargada y ninguna exportación de Mencía. No se escriben a mano — se
    calculan, igual que en la pantalla, para que lo que se mira aquí sea lo mismo
    que verá quien abra la aplicación.
    """
    esperados = [{"campo": "cantidad", "etiqueta": "Cantidad",
                  "valor_cliente": "3000", "valor_orden": "30000",
                  "severidad_esperada": "critica"}]
    obs = caso.observar(esperados, [{"campo": "cantidad"}])
    gob = caso.gobernar(obs["principal"])
    dec = caso.decidir(gob, None, None, pedido="42805")
    return caso.comprobar(obs, gob, dec)["fases"]


def _capturar():
    """Recoge lo que `linea_del_hilo` le pasaría a Streamlit, sin Streamlit."""
    trozos = []
    original = ui.st.markdown
    ui.st.markdown = lambda cuerpo, **kw: trozos.append(cuerpo)
    try:
        ui.linea_del_hilo(_fases(), caso.REGLA)
    finally:
        ui.st.markdown = original
    return "".join(trozos)


def main():
    cuerpo = _capturar()

    # Comprobaciones que sí se pueden automatizar antes de mirar nada.
    fallos = []
    if cuerpo.count('class="hilo-paso') != len(_fases()):
        fallos.append("no hay un bloque por paso")
    if "hilo-paso--corte" not in cuerpo:
        fallos.append("ningún tramo sale discontinuo, y el hilo está incompleto")
    abiertas = [p for p in _fases() if p["estado"] != "ejecutada"]
    if not abiertas:
        fallos.append("ninguna fase queda abierta, y hoy deberían quedar dos")
    for p in abiertas:
        if p["requiere"] not in cuerpo.replace("<b>", "**").replace("</b>", "**"):
            fallos.append(f"la fase {p['fase']} no dice qué le falta")
    if "<script" in cuerpo.lower():
        fallos.append("se ha colado un script en el marcado")

    SALIDA.write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<title>La línea del hilo</title>"
        + ui.ESTILO
        + "<style>body{background:var(--superficie);margin:0;"
          "font-family:system-ui,-apple-system,'Segoe UI',sans-serif;}"
          ".block-container{max-width:1180px;margin:0 auto;padding:2.4rem 2rem;}"
          "</style>"
        + f"<div class='block-container'>{cuerpo}</div>",
        encoding="utf-8")

    print(f"Escrito {SALIDA}")
    for f in fallos:
        print(f"  FALLA  {f}")
    if not fallos:
        print("  OK     un bloque por paso, el corte se ve y dice qué le falta")

    if "--captura" in sys.argv:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            n = p.chromium.launch()
            pg = n.new_page(viewport={"width": 1240, "height": 1500})
            pg.goto(SALIDA.as_uri())
            pg.wait_for_timeout(300)
            pg.screenshot(path="linea_hilo.png", full_page=True)
            n.close()
        print("Escrito linea_hilo.png")

    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
