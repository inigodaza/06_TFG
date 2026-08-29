# Conjunto de referencia — cómo rellenarlo

Íñigo Daza · 28/08/2026

## Para qué sirve

Sin esto, lo único que puedo escribir en la memoria es *«el evaluador lee 7 de 13
documentos»*. Con esto puedo escribir *«acierta X, falla Y y se abstiene Z»*, que
es una afirmación medible y la única que se sostiene delante de un tribunal.

Y sirve para algo más: **es lo que impide que el sistema mejore sólo en
apariencia.** Cada vez que toco la lectura, la medición se rehace sola. Si un
cambio sube la cobertura a costa de leer mal, se ve en el acto — hoy ya me pasó
una vez, con un contrato vigente hasta 2029 leído como caducado en 2019.

## Qué hay que hacer

Abre `conjunto_de_referencia.csv` en Excel. Trece filas, una por documento. Las
columnas ya vienen **rellenas con lo que el evaluador cree hoy**: tu trabajo no
es escribir de cero, es **corregir lo que esté mal y completar lo que falte**.

Con **6 u 8 documentos bien etiquetados vale**. Elige los que mejor conozcas y
deja el resto en blanco: una fila a medias es peor que una fila vacía, porque se
mide contra ella.

### Las columnas que tienes que tocar

| Columna | Qué poner |
|---|---|
| `familia_correcta` | `principal` si el documento fija su propia vigencia · `modificativo` si modifica a otro (anexo, prórroga, subrogación, rescate) · `accesorio` si no tiene vigencia que determinar (una aportación económica, un acta) |
| `fecha_firma` | La fecha en que se firma, en formato `AAAA-MM-DD` |
| `fecha_inicio` | Cuándo empieza a contar el plazo. **Ojo: no siempre es la firma.** Alguno cuenta «desde la inscripción en el Registro», que es otra fecha |
| `plazo_anios` | Los años pactados, en número |
| `fecha_vencimiento` | Cuándo termina. Si el documento no la escribe y sale de sumar el plazo al inicio, pon el resultado |
| `prorroga` | `tacita` (se renueva sola salvo aviso) · `expresa` (hace falta acuerdo) · `renunciada` · `no_consta` |
| `preaviso` | Días de antelación para avisar. Si la cláusula dice «tres meses», pon `90` y anótalo en `notas` |
| `estado_correcto` | A fecha **28/08/2026**: `vigente`, `caducado`, `obsoleto`, `titulo_consumado`, `no_clasificado` o `no_aplica_vigencia` |

### La columna más importante, y la que más se olvida

**`no_consta_en_el_documento`** — escribe aquí los nombres de los campos que el
documento **de verdad no dice**, separados por comas. Por ejemplo:
`fecha_inicio, preaviso`.

Es la que más valor tiene de todas. Sin ella no puedo distinguir dos cosas que se
parecen y no lo son:

- el evaluador **no supo leer** un dato que estaba → **error**
- el evaluador **se abstuvo** de un dato que no estaba → **acierto**

Un evaluador que se calla cuando no hay nada que decir está haciéndolo bien, y
esta columna es lo único que lo demuestra.

### Ayudas

- `pista_duracion` y `pista_firma` traen el trozo del documento donde está la
  respuesta, ya reconocido. Para la mayoría no te hará falta abrir el PDF.
- El texto viene de un OCR y tiene erratas (`cuatroúe abril` por `cuatro de
  abril`). Si la pista está ilegible, abre el PDF: manda el papel.
- Si dudas entre dos valores, **déjalo en blanco y escríbelo en `notas`**. Una
  duda tuya anotada vale más que un valor inventado, y en la memoria se cita.

## Cuando lo tengas

Devuélveme el CSV. Con él se ejecuta `python medir.py`, que compara el conjunto
contra lo que produce el sistema y saca la tabla de aciertos, fallos y
abstenciones por campo. Esa tabla va a la memoria tal cual.
