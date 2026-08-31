"""
¿Y si el documento nuevo viene peor escaneado?

`prueba_ocr_real.py` responde a «¿sabe reconocer?» usando los PDF de Martín tal
como están. Pero un documento que llegue mañana no vendrá igual: lo habrá
escaneado otra persona, con otra máquina, quizá torcido, quizá a menos
resolución, quizá guardado en JPEG por un móvil.

Este script coge un documento que el sistema lee bien y lo **estropea a
propósito** de cinco formas distintas, cada una imitando un defecto real de
escaneo. Después mide qué campos sobreviven. La pregunta no es si el texto sale
idéntico —no saldrá—, sino si **los campos que deciden el veredicto** siguen
saliendo, y si cuando no salen el sistema calla en vez de inventárselos.

Un evaluador que ante un escaneo malo devuelve fechas plausibles es peor que uno
que no lee nada: el primero acusa a un compañero, el segundo se declara incapaz.

    python3 prueba_robustez_ocr.py [documento.pdf ...]
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter

from nucleo import pdf as P
from modulos import vigencia as V

CORPUS = Path("demo/datos/vigencia")
CAMPOS = [("fecha_emision", "firma"), ("fecha_inicio", "inicio"),
          ("anios_pactados", "plazo"), ("fecha_caducidad", "vencim."),
          ("prorroga_tipo", "prórroga"), ("antelacion", "preaviso"),
          ("familia", "familia"), ("direccion_objeto", "cadena")]

# Cada avería imita algo que pasa de verdad, no un ruido cualquiera.
AVERIAS = [
    ("original a 300 ppp", dict()),
    ("escaneado a 150 ppp", dict(ppp=150)),
    ("torcido 0,8°", dict(giro=0.8)),
    ("torcido 2°", dict(giro=2.0)),
    ("desenfocado", dict(desenfoque=1.2)),
    ("guardado en JPEG (móvil)", dict(jpeg=30)),
    ("150 ppp + torcido 1,5°", dict(ppp=150, giro=1.5)),
]


def paginas_como_imagen(pdf, carpeta, ppp=300):
    subprocess.run(["pdftoppm", "-r", str(ppp), "-gray", "-png",
                    str(pdf), str(carpeta / "p")],
                   check=True, capture_output=True)
    return sorted(carpeta.glob("p*.png"))


def estropear(img, giro=0.0, desenfoque=0.0, jpeg=0):
    if giro:
        img = img.rotate(giro, resample=Image.BICUBIC, expand=True,
                         fillcolor=255)
    if desenfoque:
        img = img.filter(ImageFilter.GaussianBlur(desenfoque))
    if jpeg:
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "x.jpg"
            img.convert("L").save(f, "JPEG", quality=jpeg)
            img = Image.open(f).copy()
    return img


def reconocer(img, carpeta, i):
    f = carpeta / f"q{i}.png"
    img.save(f)
    r = subprocess.run(["tesseract", str(f), "stdout", "-l", "spa"],
                       capture_output=True, text=True)
    return r.stdout or ""


def campos_de(texto):
    c = V.extraer(texto) or {}
    return {k for k, _ in CAMPOS
            if c.get(k) not in (None, "", "no_consta", {}, [])}, c


def probar(pdf):
    print(f"\n{'=' * 86}\n{pdf.stem}\n{'=' * 86}")
    base_texto = P.leer(pdf)["texto"]
    base_campos, _ = campos_de(base_texto)
    print(f"Lectura buena: {len(base_campos)}/8 campos "
          f"→ {', '.join(n for k, n in CAMPOS if k in base_campos)}\n")

    print(f"{'cómo llega el documento':30}{'car':>8}{'campos':>9}"
          f"{'pierde':>26}{'INVENTA':>10}")
    print("-" * 86)
    resultados = []
    for nombre, av in AVERIAS:
        with tempfile.TemporaryDirectory() as t:
            carpeta = Path(t)
            pags = paginas_como_imagen(pdf, carpeta, av.get("ppp", 300))
            trozos = []
            for i, f in enumerate(pags):
                img = estropear(Image.open(f), av.get("giro", 0.0),
                                av.get("desenfoque", 0.0), av.get("jpeg", 0))
                trozos.append(reconocer(img, carpeta, i))
            texto = "\n".join(trozos)
        campos, _ = campos_de(texto)
        pierde = sorted(n for k, n in CAMPOS if k in base_campos - campos)
        inventa = sorted(n for k, n in CAMPOS if k in campos - base_campos)
        resultados.append((nombre, campos, pierde, inventa))
        print(f"{nombre:30}{len(re.sub(r'[^A-Za-z0-9]', '', texto)):>8}"
              f"{len(campos):>7}/8{', '.join(pierde) or '—':>26}"
              f"{', '.join(inventa) or '—':>10}")
    return base_campos, resultados


def main(nombres):
    pdfs = [CORPUS / n if not Path(n).is_file() else Path(n) for n in nombres]
    todo = []
    for p in pdfs:
        if not p.is_file():
            print(f"No está: {p}")
            continue
        todo.append((p.stem, *probar(p)))

    print(f"\n{'=' * 86}\nQué aguanta y qué no\n{'=' * 86}")
    for nombre, base, res in todo:
        for averia, campos, pierde, inventa in res:
            marca = "·" if not pierde and not inventa else (
                "!" if inventa else "-")
            print(f" {marca} {nombre[:26]:28}{averia:30}"
                  f"{len(campos)}/{len(base)} campos"
                  + (f"  INVENTA {inventa}" if inventa else ""))
    inventados = sum(1 for _n, _b, res in todo for _a, _c, _p, inv in res if inv)
    print(f"\n  Veces que un escaneo peor le hace INVENTARSE un campo: "
          f"{inventados}")
    print("  (es la cifra que importa: perder un campo es una limitación "
          "declarada;\n   inventarlo es una acusación falsa a quien escribió el "
          "módulo)")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:] or ["20160119_ANEXO.pdf",
                            "2019_CTO_ALQUILER_RENOVACION_BULL_MCCABES.pdf"]
    sys.exit(main(args))
