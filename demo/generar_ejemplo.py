"""
Genera el par de documentos sintéticos con el que la pantalla del caso arranca
sin depender de nada.

Por qué existe
--------------
Los documentos del pedido 42805 son documentación de cliente y no se versionan,
así que en un despliegue limpio la pantalla «Seguir un caso» no tenía con qué
arrancar: pedía documentos y ahí se quedaba. Una demo que sólo funciona en el
portátil de quien la escribió no es una demo.

Esto fabrica dos PDF **inventados de principio a fin** —editorial, título e ISBN
no existen— con la misma estructura que los reales y una discrepancia deliberada
de un cero en la cantidad. Sirven para ver el recorrido entero funcionando; para
la demostración de verdad se suben los documentos reales, que dan el mismo
resultado por el mismo camino.

Van marcados en la primera línea de cada página. Un documento sintético que se
pudiera confundir con uno de cliente sería un problema, no una comodidad.

    python demo/generar_ejemplo.py
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

DESTINO = Path(__file__).resolve().parent / "datos" / "ejemplo"

AVISO = "DOCUMENTO SINTETICO DE PRUEBA - editorial, titulo e ISBN inventados"

ORDEN = f"""{AVISO}

ORDEN DE FABRICACION                          O.F. Nº 90001

Cliente: Editorial Ficticia del Norte S.L.
Formato: 170 x 240

9780000000017 170 x 240

Cantidad:                                     Paginas:
  Manual de Encuadernacion Imaginaria           30.000 288

Interiores 4 4 offset blanco 288  30.000  30.000
  Papel offset ahuesado    170x240   90   Interiores  1/1
  Carton estucado brillo   170x240   250  Cubiertas  4/0

Encuadernacion: rustica fresada
Impresion: offset

LOGISTICA
Cantidad: 30.000
Destino: almacen central
"""

CLIENTE = f"""{AVISO}

PURCHASE ORDER

We hereby order the following title:

RE: 9780000000017

Title: Manual de Encuadernacion Imaginaria
Quantity: 3,000 copies
Extent: 288 pp
Trimmed Size: 170 x 240mm
Text Paper: 90 gsm
Cover Material: 240 gsm
Binding: limp

Delivery date: 30/11/2026
Delivery address: Editorial Ficticia del Norte S.L.
"""


def escribir(ruta, texto):
    """Un PDF con capa de texto: nada de imagenes, para que no dependa del OCR."""
    c = canvas.Canvas(str(ruta), pagesize=A4)
    c.setFont("Courier", 9)
    y = A4[1] - 50
    for linea in texto.splitlines():
        c.drawString(45, y, linea)
        y -= 12
        if y < 50:
            c.showPage()
            c.setFont("Courier", 9)
            y = A4[1] - 50
    c.save()


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    escribir(DESTINO / "EJEMPLO_orden_de_fabricacion.pdf", ORDEN)
    escribir(DESTINO / "EJEMPLO_pedido_de_cliente.pdf", CLIENTE)
    (DESTINO / "LEEME.md").write_text(
        "# Documentos de ejemplo\n\n"
        "Inventados de principio a fin: la editorial, el título y el ISBN no "
        "existen. Los genera `demo/generar_ejemplo.py` y sirven para que la "
        "pantalla «Seguir un caso» se pueda recorrer entera en cualquier "
        "despliegue, sin depender de documentación de cliente.\n\n"
        "Llevan una discrepancia deliberada —3.000 ejemplares pedidos contra "
        "30.000 en la orden— que es la misma forma de error que el caso real "
        "del pedido 42805.\n\n"
        "Para la demostración de verdad se suben los documentos reales. Éstos "
        "no los sustituyen: enseñan que el recorrido funciona.\n",
        encoding="utf-8")
    print(f"Escritos en {DESTINO}")


if __name__ == "__main__":
    main()
