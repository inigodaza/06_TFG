# Exportaciones de ejemplo para el módulo de evaluación de calidad

JSON generados con `src/exportar_resultado.py` (construcción del export) y
`src/generar_ejemplos_exportacion.py` (los 4 casos de este directorio), a
partir del corpus sintético ya indexado (`data/tabla_fichas.json` +
`data/vectores.npz`). Nada de esto es un dato real de cliente — todos los
proyectos son `SYN-####` de `datos_sinteticos/corpus/`.

Para regenerarlos:

```
python -m src.generar_ejemplos_exportacion
```

## Estructura del JSON

Cada archivo tiene 7 campos pactados con el módulo de evaluación de
calidad: `id_consulta`, `fecha_hora`, `pedido_consultado`, `resultados`
(con `posicion`, `id_proyecto`, `puntuacion`, `senales` y
`parametros_justificativos` por resultado), `descartados` (con
`id_proyecto`, `parametro`, `valor_pedido` y `valor_candidata`),
`esquema_version` y `peso_semantico`. `id_proyecto` es siempre el nombre
del documento de origen (p. ej. `"SYN-0048.md"`), nunca el UUID interno
del proyecto.

Si ningún candidato sobrevive al filtro de la Capa 1, `resultados` es una
lista vacía y el campo `aviso_lista_vacia` (siempre presente, `null`
cuando sí hay resultados) explica qué parámetro dejó fuera a todos.

**Añadido propuesto, fuera del acuerdo de 7 campos**: cada resultado
lleva también `extra_no_pactado.parametros_no_verificados` — los
parámetros duros que exigía el pedido pero que la candidata no tenía
valor para comprobar (sobrevivió por benevolencia, no por verificación
completa). Se propone como información de fiabilidad para el evaluador de
calidad, pero **no forma parte del acuerdo original**: va deliberadamente
anidado aparte de los campos pactados para que un consumidor que solo
espere esos 7 campos pueda ignorarlo sin problema.

## Los 4 casos

1. **`caso1_syn0047_acierto.json`** — caso limpio. Pedido = ficha de
   `SYN-0047.md` (familia de 5: 47/48/49/50/51). Los 4 hermanos ocupan las
   posiciones 1-4 del ranking; las posiciones 5-9 son los 5 distractores
   de este grupo (`evaluacion/distractores.md`), todos por detrás.
2. **`caso2_syn0041_fallo_conocido.json`** — fallo conocido. Pedido =
   ficha de `SYN-0041.md` (familia de 6, único grupo de los 8 de
   `evaluacion/informe_capa2.md` con recall@5 < 1). `SYN-0045.md` es un
   hermano real (sus `parametros_justificativos` coinciden con el pedido)
   pero queda en la posición 7, fuera del top-5, por su tamaño físico
   atípico dentro de la familia — un distractor (`SYN-0079.md`) ocupa la
   posición 4 en su lugar.
3. **`caso3_syn0052_distractores.json`** — distractores compitiendo.
   Pedido = ficha de `SYN-0052.md` (familia de 3: aerocondensador_vapor,
   con 5 distractores `SYN-0088`..`SYN-0092`). Elegido porque aquí la
   competencia es más reñida que en los otros grupos: dos distractores
   (`SYN-0092.md`, `SYN-0090.md`) quedan en las posiciones 2 y 3, por
   delante del hermano real `SYN-0053.md` (posición 4).
4. **`caso4_lista_vacia.json`** — comportamiento ante error. Pedido
   sintético de formulario (`presion_diseno=60` barg, sin documento de
   origen, por eso el identificador de consulta no lleva referencia) muy
   por fuera de la banda de las 97 fichas indexadas (rango real del
   corpus, ~2-20 barg). Las 97 candidatas se descartan, todas por el mismo
   parámetro: `resultados` queda vacío y `aviso_lista_vacia` lo dice
   explícitamente (`"El parámetro que excluyó a todas fue
   'presion_diseno' (97/97)"`).
