# Bloque de Evaluación y Calidad — TFG Íñigo Daza

Sistema que verifica automáticamente si la salida de un módulo es correcta y emite
una valoración de su calidad.

El principio no cambia respecto a la primera versión: **el evaluador no se fía de
lo que reporta el módulo**. Lee los documentos de origen, calcula por su cuenta
cuál es el resultado correcto, y sólo entonces contrasta.

Lo que sí cambia es la forma. Antes había un evaluador para un módulo. Ahora hay
un núcleo común y una rama por módulo.

## Estructura

```
app.py                 selector de módulo, demo y esquema — nada más
ui.py                  estilo, componentes y bloques de resultado
esquema.py             el diagrama del sistema, generado desde el registro
nucleo/
  pdf.py               lectura de PDF: capa de texto, OCR de escaneos e
                       integridad (páginas del fichero vs. las que el
                       documento declara en su pie)
  texto.py             normalización de valores y de fechas
  contraste.py         contraste genérico → exhaustividad y precisión
  bateria.py           casos, resumen y tasa sobre lo verificado
  veredicto.py         EvaluationResult y exportación
  llm.py               las ranuras del modelo: caché, temperatura 0, estabilidad
  jueces.py            panel de jueces para lo cualitativo, con acuerdo medido
  informe.py           redacción del informe, con control de cifras
  asesor.py            el plan de mejora: cruza fallos y criterios, y ancla
                       cada recomendación a un caso
  historial.py         el ciclo de mejora: qué cambió entre dos evaluaciones
modulos/
  auditoria.py         Juan Salas · GraphyCems      · C8 · operativo
  vigencia.py          Martín de Lucas · RALSA      · C1 · operativo · probado
  similitud.py         Álvaro Subias · Kelvion      · C7 · operativo
  contradicciones.py   Mencía Viñuelas · GraphyCems · C6 · operativo
  gobernanza.py        Pablo Morillas · MAIO Legal  ·    · declarado, sin batería
demo/
  guion.py             recorrido completo, módulo a módulo
  datos/<modulo>/      documentos de cada paso
pruebas.py             comprobación del evaluador desde la línea de órdenes
medir.py               mide el evaluador contra el conjunto de referencia:
                       aciertos, omisiones, errores e invenciones por campo
referencia/            el conjunto etiquetado a mano y cómo rellenarlo
ALCANCE.md             hasta dónde llega el trabajo y hasta dónde no
ACUERDO_C7_SIMILITUD.md  el acuerdo de conexión con Álvaro, revisado el 27/08
DESPLIEGUE.md          cómo subirlo a Streamlit Cloud sin dejarse ficheros
```

**Añadir un módulo** es escribir un fichero en `modulos/` y una línea en
`modulos/__init__.py`. La rejilla de tarjetas, el esquema y el recorrido de la
demo se construyen solos a partir del registro.

Están los **cinco** módulos del proyecto, no sólo aquellos con los que he
avanzado. Es la misma disciplina de la batería aplicada al propio sistema: un
módulo que no aparece en el mapa se lee como un módulo que no existe. `operativo`
separa la rama que puede evaluar de la que sólo está declarada, y una rama puede
estar declarada incluso sin batería — la de Pablo lo está.

## Las tres pantallas

**Evaluar un módulo** — una tarjeta por módulo con su función, el estado de la
conexión y si es evaluable hoy. Al abrir una, el flujo de tres pasos.

**Demo** — el recorrido completo. Un paso que no puede ejecutarse se enseña con
el motivo: el recorrido cuenta el estado real, no el previsto.

**Esquema del sistema** — de qué documentos parte cada módulo, qué hace, y cómo
su salida entra en el evaluador. Sustituye a la tabla de conexiones: una tabla no
explica por dónde circula un dato. El estado de la conexión va en el color, en el
trazo y en la palabra — el color acompaña, nunca carga solo con el significado.

## Qué es común y qué es específico

| | Dónde vive |
|---|---|
| Calcular la verdad de campo de forma independiente | rama |
| Contrastar y obtener exhaustividad y precisión | núcleo |
| Ejecutar la batería y separar pendiente de fallido | núcleo |
| El veredicto, con aspectos anclados a casos | núcleo |
| Cómo se extraen los campos de los documentos | rama |
| Qué campos son comparables | rama |
| Los casos propios de esa batería | rama |

No es una suma de validadores independientes porque **todas las ramas emiten el
mismo objeto, con las mismas dos métricas y la misma regla de anclaje**. Lo
comparable no son los módulos, es el veredicto.

## Dónde entra el modelo, y dónde no

El modelo no trabaja **en paralelo** al núcleo determinista: trabaja **detrás**.

Esto es la corrección de un error de diseño. Durante un tiempo hubo un «modo IA»
que competía con las reglas por el mismo trabajo, un panel cualitativo colgado al
lado y un redactor que reformulaba lo ya escrito. Ninguno consumía el veredicto
para producir algo que las reglas no pudieran producir. Un evaluador no puede
tener dos verdades de campo según qué botón se pulse.

Hoy la cadena es una sola:

```
reglas → verdad de campo → contraste → batería → veredicto
                                                     ↓
                                     panel de jueces ─┤
                                                     ↓
                                                  ASESOR → plan de mejora
                                                     ↓
                                                 HISTORIAL → qué cambió
```

**Rescate, no vía alternativa.** El modelo se llama únicamente para los campos
que las reglas no han encontrado. Si las reglas lo encuentran todo, ni se llama.
Cada valor que aporta queda marcado con su procedencia, y pasa por una frontera
de tipos antes de tocar el núcleo.

**El panel de jueces no puntúa solo.** Hay criterios que ninguna regla alcanza
—si un aviso es accionable, si la salida distingue lo que sabe de lo que no puede
saber—. Los juzgan tres jueces con lentes declaradas, a temperatura 0, y sólo
cuenta lo que los tres coinciden; donde discrepan se declara la discrepancia y se
publica la **κ de Fleiss**. Su conclusión no vive en una tabla aparte: **entra en
el asesor**.

**El asesor es el único sitio donde el modelo produce criterio.** Recibe el
veredicto ya calculado y hace lo que las reglas no saben: agrupar varios fallos
bajo una causa común, cruzar un fallo duro con un criterio cualitativo que apunta
al mismo sitio, y ordenar por severidad. Tres candados: sólo ve hechos
calculados, nunca documentos; **toda recomendación tiene que citar un caso
fallido o pendiente** —si no lo cita, se descarta entera y el descarte se
cuenta—; y hay versión sin modelo.

**El historial compara ejecuciones.** Guarda una instantánea por evaluación y la
compara con la anterior, así que el sistema puede decir *«el caso 7 fallaba el 22
y hoy pasa; tasa 80 % → 100 %»*. Separa mejoras de regresiones a propósito: un
evaluador que sólo celebrase los avances sería complaciente. El mecanismo está
probado; el ciclo entero con la corrección de un compañero está pendiente de la
reexportación de Mencía, y `ALCANCE.md` §7 lo declara en esos términos.

### Permisos por rama, y por qué son dos

Leer y juzgar exponen cosas distintas, así que se autorizan por separado:

| Rama | `ia_permitida` (leer) | `panel_permitido` (juzgar) |
|---|---|---|
| Auditoría · Juan | ✖ documentación real de cliente | ✖ los jueces leerían esa salida |
| Vigencia · Martín | ✔ contratos ficticios | ✔ |
| Similitud · Álvaro | ✖ no hay lectura que generalizar | ✔ identificadores sintéticos |
| Contradicciones · Mencía | ✖ exportación ya estructurada | ✔ sin datos identificables de cliente |

Los criterios de una rama con el panel cerrado **se escriben y se enseñan igual**,
marcados como diseñados y sin ejecutar.

## Comprobar el evaluador

```
python pruebas.py
```

No prueba los módulos de mis compañeros: prueba el evaluador. Comprueba que la
verdad de campo sobre los seis documentos de Martín es la que corresponde, y que
el sistema **reacciona cuando la salida se altera a propósito** — un contrato
vencido declarado vigente baja la exhaustividad, un documento inventado baja la
precisión, dos ejecuciones distintas no pasan repetibilidad. Un validador que
sólo aprueba no está demostrado.

## Despliegue

Streamlit Community Cloud. `packages.txt` con `poppler-utils` es imprescindible:
sin él no hay `pdftotext` y la app no arranca.

Al subir a GitHub, **Add file → Upload files**, nunca el lápiz.
