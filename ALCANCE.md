# Alcance del bloque de Evaluación y Calidad

Íñigo Daza · cierre de iteración del 1 de septiembre de 2026
Respuesta al encargo de Fabián del 24/08/2026.

> «Tu aportación no es probarlo todo: es construir una evaluación que discrimine
> y produzca aprendizaje.»

Este documento fija **hasta dónde llega el trabajo y hasta dónde no**. Empieza por
la renuncia de mayor calado, que no es qué módulos se evalúan sino **dónde termina
el sistema**.

---

## 1 · Dónde termina el sistema

El evaluador recibe la salida de un módulo, calcula por su cuenta cuál debería
haber sido, contrasta y emite un veredicto.

**La salida se le entrega.** Alguien la consigue del módulo —la pega, sube el
fichero JSON o los PDF— y a partir de ahí el sistema hace todo lo demás sin
intervención: lee, deduce la verdad de campo, contrasta, ejecuta la batería,
gradúa por severidad, redacta el informe y guarda la instantánea.

Esa frase corta —*la salida se le entrega*— es la frontera del trabajo.

---

## 2 · Lo que queda fuera: el puente automático

**Se descartó construir un sistema que fuera directamente a los módulos de mis
compañeros a recoger su salida.** Ni conexión en vivo, ni consulta programada, ni
evaluación disparada cuando un módulo produce algo nuevo.

Era la idea inicial. Es inviable, y conviene decir por qué con precisión, porque
la razón no es falta de tiempo:

**No hay dónde enchufarse.** Ninguno de los cinco módulos publica un punto de
acceso. GraphyFlow es una interfaz web, IAlert es una interfaz web, Álvaro y
Mencía exportan JSON a mano. El puente no es código que dependa de mí: exige que
cada compañero publique un contrato técnico —endpoint, autenticación, formato
estable— **y lo mantenga**. Eso es una decisión de equipo y de calendario, no una
tarea de mi bloque.

**Sería un puente sobre prototipos en movimiento.** Los cinco módulos siguen
cambiando cada semana. Un puente construido contra una salida que se mueve se
rompe con ella, y entonces deja de poder distinguirse si falla el módulo o falla
el puente. **Para un evaluador ése es el peor fallo posible**: confundir un
problema propio con un defecto ajeno le quita autoridad a todo lo que emita.

**No mejora lo que hay que demostrar.** Lo que se está demostrando es que la
evaluación **discrimina** y **produce aprendizaje**. Los tres hallazgos del
apartado 6 se consiguieron con la salida entregada a mano. Automatizar el
transporte no habría hecho mejor ninguno de ellos: habría hecho más cómodo
obtenerlos.

Y coincide con la prioridad que fijó Fabián desde el principio: **el diseño de
baterías antes que la automatización**.

### Lo que esto significa en la práctica, dicho sin adornos

- La evaluación es **a petición**, no continua. Alguien decide evaluar.
- **No hay detección automática de regresiones.** Si un módulo empeora entre dos
  versiones, el sistema lo detecta —tiene memoria— pero sólo cuando se le vuelve a
  pedir.
- El registro en el historial es **manual**, a propósito: guardar es afirmar que
  esa evaluación cuenta.

Nada de esto invalida los veredictos. Lo que limita es la frecuencia con que se
obtienen.

### Lo que sí queda construido del lado del puente

Esto importa, porque no se ha renunciado a la mitad difícil:

- **El intérprete de cada rama.** Cada módulo declara su `interpretar()`, que
  acepta la misma salida en varias formas —JSON, CSV, fichas de la interfaz, texto
  pegado— y la normaliza. Ése es el adaptador, y es la parte que cuesta.
- **El esquema de salida declarado** por rama: qué campos se esperan y de qué tipo.
- **La frontera de tipos**, que convierte y rechaza lo que no encaja antes de que
  toque el núcleo.
- **El acuerdo de conexión escrito** para cada módulo, con su estado y quién
  verifica.

El día que un módulo publique un endpoint, lo único que hay que escribir es la
llamada. Todo lo que viene después ya está hecho y probado.

**Qué haría falta para cruzarlo, por orden:** que un módulo publique una salida
estable y versionada; que se acuerde cómo se autentica y cada cuánto se consulta;
y sólo entonces, escribir el transporte. El primer paso no es mío.

---

## 3 · Qué entra en esta iteración

Cuatro módulos con batería cerrada y ejecutada contra salida real del compañero.

| Módulo | Responsable | Conexión | Casos | Estado |
|---|---|---|---|---|
| Auditoría de pedidos | Juan Salas · GraphyCems | C8 · **probada** | 9 | Caso demostrado, se mantiene |
| Vigencia documental | Martín de Lucas · RALSA | C1 · **probada** | 12 | Cerrado y ejecutado sobre documentos y salidas reales |
| Similitud de proyectos | Álvaro Subias · Kelvion | C7 · documentada | 11 | Cerrado y ejecutado |
| Contradicciones y validación humana | Mencía Viñuelas · GraphyCems | C6 · documentada | 10 | Cerrado y ejecutado |

**42 casos diseñados. 13 criterios cualitativos.**

### Una desviación respecto del encargo, y por qué

Proponías cerrar Martín y Álvaro, y **pedir sin evaluar** a Mencía y Pablo. Mencía
entregó su exportación el 22/08 —el `export_PED1004.json` que la batería llevaba
pidiendo— y evaluarla costó una tarde, porque la plantilla común ya estaba hecha.

La mantengo dentro por una razón concreta: **es la que produce el resultado que
pides al final de tu mensaje**. Renunciar a ella habría sido tirar evidencia ya
conseguida.

---

## 4 · Qué más queda fuera

### Pablo Morillas · Ontología y grafo organizativo

**Sin batería diseñada.** No hay documentación, no hay salida y no hay acuerdo de
conexión escrito con mi bloque. Escribir casos sin haber visto una salida real
sería cometer exactamente el error que este sistema mide en los demás: dar por
hecho algo que no se ha comprobado.

Aparece declarado en el registro y en el esquema, con su estado real. Un módulo
que no aparece en el mapa se lee como un módulo que no existe.

### El banco de robustez ante la redacción

**Construido y retirado el 24/08.** Fabricaba contratos con los mismos hechos y
distinta redacción para medir si un módulo aguanta cuando cambia el notario
(*metamorphic testing*). Fuera por decisión de alcance: **este bloque evalúa lo
que los compañeros entregan**; fabricar documentos de prueba es otra cosa.

### Lo que el sistema declara que no puede comprobar

No son renuncias de alcance, son limitaciones declaradas, y van escritas en cada
evaluación:

- **Álvaro** — no tengo el corpus de 97 fichas, sólo la salida. No puedo saber si
  el filtro de Capa 1 excluyó un proyecto que sí era equivalente.
- **Juan** — el modo IA queda cerrado: sus documentos son datos reales de cliente
  de GraphyCems y el nivel gratuito del proveedor entrena con lo que se le manda.
  Sus tres criterios cualitativos quedan diseñados y sin ejecutar.
- **Mencía** — sin los PDF del PED1004 puedo refutar que la evidencia sea literal,
  pero no confirmarlo. Prueba negativa concluyente, positiva no.

---

## 5 · La plantilla común de evaluación

`nucleo/plantilla.py`. Una sola forma para los cuatro módulos, con las columnas
que pediste:

| # | Caso | Entradas | Resultado esperado | Resultado observado | Severidad | Pasa / No pasa |
|---|---|---|---|---|---|---|

Exportable en Markdown y CSV desde cualquier evaluación.

**Severidad** — declarada en la ficha de cada rama **antes de ejecutar el caso**.
Si se asignara al ver el resultado dejaría de clasificar el riesgo para justificar
la nota. Mide qué ocurre aguas abajo si el fallo pasa desapercibido, no cuánto
molesta:

- **Crítica** — se propaga sin dejar rastro; quien recibe la salida lo da por bueno
- **Alta** — es visible, pero obliga a rehacer a mano lo que el módulo iba a ahorrar
- **Media** — degrada la utilidad sin invalidar el resultado

42 de 42 casos con severidad declarada.

**Esperado y observado** van en columnas separadas. Antes iban fundidos en un
párrafo, y eso permitía escribir «el estado no coincide» sin decir cuál era cada
uno. Ahora o se rellenan o sale escrito «no desglosado», que es una deuda visible.

---

## 6 · Precisión, exhaustividad y los resultados que produjeron aprendizaje

El criterio pasa/no pasa se apoya en dos métricas independientes, calculadas
contra una verdad de campo que el evaluador deduce **por su cuenta**, sin mirar la
salida del módulo:

- **Exhaustividad** — de lo que había que detectar, cuánto detectó
- **Precisión** — de lo que emitió, cuánto se sostiene documentalmente

Detectar incidencias reales sin inventar incidencias inexistentes: son las dos
caras, y se miden por separado a propósito. Un módulo que avisa de todo tiene
exhaustividad perfecta y precisión pésima.

### Hallazgo 1 · Mencía, caso 7, severidad alta

| | |
|---|---|
| **Esperado** | `Pedido_PED1004.pdf` (12/08/2026) marcado como descartado |
| **Observado** | `Pedido_PED1004.pdf`: `is_active = 1` |

Después de que el Director de Producción validara la fecha del 25/08, **los dos
hechos siguen marcados como activos**. El valor descartado se conserva —que es lo
que había que pedir— pero no queda distinguible del confirmado.

Lo relevante metodológicamente: **el fallo no se ve mirando la contradicción, se
ve mirando los hechos**. El evaluador ignora la tabla de contradicciones del
módulo y la recalcula desde los hechos extraídos; por eso encuentra algo que la
propia salida presenta como correcto.

### Hallazgo 2 · Álvaro — el hallazgo que corrigió al evaluador

Éste es el más interesante de los tres, y no porque encontrara un fallo. Porque
**el ciclo se cerró en la dirección contraria a la prevista**.

**Lo que preguntó el evaluador.** Salió de una pregunta mía: *«su módulo valora el
porcentaje de similitud, ¿no deberíamos comprobar que eso esté bien?»*. Los diez
casos que había comprobaban que el ranking está bien **construido** —aritmética,
orden, normalización, partición—: todos pasarían aunque la puntuación fuese un
número al azar. El caso 11 preguntaba si el número *significaba* algo, contrastando
la puntuación contra la desviación en los `parametros_justificativos` que el
propio módulo publica.

| Consulta | ρ de Spearman | Pares invertidos |
|---|---|---|
| SYN-0047 (limpio) | −0,895 | 0 |
| SYN-0041 (fallo conocido) | −0,628 | 8 |
| SYN-0052 (distractores) | −0,847 | 2 |

- **SYN-0053** se desvía **4,1 %** y puntúa **0,243**; **SYN-0092** se desvía
  **44,3 %** y puntúa **0,646**.

**Lo que contestó Álvaro (27/08).** El diagnóstico era correcto y la conclusión
no. No es un bug: la puntuación reparte 50 % a once numéricos y 50 % a siete
categóricos blandos, con media simple dentro de cada mitad. Los ocho parámetros
que publica como justificativos son los filtros de la Capa 1 — **seis aportan
exactamente cero** porque todos los supervivientes los cumplen por construcción, y
los otros dos suman **menos del 10 %**. Quien decide son **siete categóricos
secundarios que no se publican**. SYN-0092 tiene peor componente numérico que
SYN-0053 (0,106 frente a 0,275) pero coincide en 6 de 7 specs secundarias frente
a 3 de 7.

> *«`parametros_justificativos` es informativo y no explica la posición en el
> ranking. Si evalúas coherencia asumiendo que sí la explica, vas a marcar como
> incoherentes salidas que son correctas.»*

**Lo que se corrigió, y dónde.** El fallo estaba en mi lado. El caso 11 cambió de
pregunta: ya no supone qué parámetro debería pesar más —esa suposición era el
error— sino que **rehace la ordenación entera** desde la tabla de contribución por
parámetro que Álvaro aportó. Resultado sobre las 17 candidatas supervivientes de
SYN-0041 y SYN-0052:

| | |
|---|---|
| **Esperado** | cada puntuación igual a la suma de contribuciones normalizada min-max, y el mismo orden |
| **Observado** | 17 de 17 reproducidas · diferencia máxima **0,0006** · orden idéntico |
| **Caso 11** | **pasa** |

Sin esa tabla el caso queda **pendiente**, no fallado: un evaluador que acusa sin
poder demostrarlo es justo lo que este sistema le reprocha a los módulos que
evalúa.

**Qué se conserva.** La correlación negativa se sigue midiendo, degradada a
**hallazgo de trazabilidad**: informa y no puntúa. Su consecuencia —que la salida
sola no permite auditar una posición— está escrita en
[`ACUERDO_C7_SIMILITUD.md`](ACUERDO_C7_SIMILITUD.md), junto con el reparto de
pesos, los tres comportamientos que Álvaro declara deliberados (lista vacía,
precedente antiguo, candidato marcado) y la deuda técnica del reparto 1/N, que él
asume y deja fuera del alcance de su TFG.

**Por qué está aquí.** El encargo pedía «al menos un resultado que haya permitido
corregir o mejorar otro módulo». Éste mejoró **dos**: el módulo de Álvaro gana una
advertencia escrita sin la que cualquier consumidor de C7 se equivocaría igual, y
el evaluador deja de producir falsos positivos sobre salidas correctas. Una
evaluación que sólo puede tener razón no evalúa nada; ésta se dejó corregir por el
módulo que estaba juzgando, y las comprobaciones del bloque 18 de `pruebas.py`
existen para que ese cambio no se pueda deshacer sin darse cuenta.

### Hallazgo 3 · Martín — tres fallos que no se ven mirando la fecha

Llegó el 28/08, el primer documento real de RALSA con la ficha que IAlert emite
para él: un contrato de arrendamiento de una estación de servicio, ocho páginas
**escaneadas sin capa de texto**. `pdftotext` devuelve cero bytes.

Eso obligó a cambiar la capa de lectura antes de poder evaluar nada — hasta ese
día la rama daba por ilegible cualquier fotocopia, y todo el corpus de Martín
habría quedado en «no se ha podido comprobar». Ahora el evaluador reconoce el
documento por OCR **y declara la vía**: lo que compara es una lectura suya contra
una lectura del módulo, y el veredicto lo dice para que los fallos se lean con la
reserva correcta.

Coinciden en lo importante: estado **vigente**, firma 10/12/2015, inicio
15/01/2016, plazo 14 años, vencimiento 15/01/2030, y la alerta de revisión de
renta por IPC a **140 días**, que cuadra al día. Se separan en tres cosas:

| # | Caso | Severidad | Esperado | Observado |
|---|---|---|---|---|
| 11 | Naturaleza de la prórroga | **crítica** | Expresa — *«las partes podrán convenir una o más prórrogas… mediante acuerdo expreso»* | `Prórroga tácita ✓` |
| 12 | Fecha crítica de aviso | alta | 15/10/2029 — tres meses antes del vencimiento | *(vacío)* |


Los tres merecen una frase:

- **La prórroga no es un matiz, es el comportamiento opuesto.** Con prórroga
  tácita, no hacer nada renueva el contrato; con prórroga expresa, no hacer nada
  lo extingue. Quien lea «tácita ✓» se quedará quieto y perderá la estación de
  servicio. El discriminante es el verbo de la cláusula, no la palabra
  «prórroga»: los dos textos la contienen.
- **La fecha crítica es el único campo accionable de la ficha** —el vencimiento
  dice cuándo acaba, la fecha crítica cuándo hay que moverse— y sale de una
  resta que el módulo ya tiene resuelta: publica el vencimiento y publica un
  preaviso de 90 días. Ojo a la unidad: la cláusula dice *tres meses*, que es el
  15/10/2029, no el 17/10/2029 que sale de restar noventa días.
- **Al documento le faltan las páginas 7 y 8**, y eso se sabe sin ninguna fuente
  externa: su propio pie dice «Página N de 10» y el fichero tiene 8. El módulo
  publica «Número de páginas: 8» —el dato del fichero— sin compararlo con el que
  el documento declara de sí mismo. Declararlo apto como referencia cuando falta
  una quinta parte del texto es el peor resultado posible, porque lo que falta
  puede ser la cláusula de resolución.

Y un cuarto, de contrato de conexión: **el módulo identifica los documentos por
la ruta de un disco local** (`C:\Users\marti\…\ARRENDAMIENTO CRED.pdf`). El
evaluador los concilió porque había un único candidato posible, y lo declara en
vez de hacerlo en silencio; pero un identificador que depende de cómo se llame
el fichero en el ordenador de quien lo subió no es estable.

**Resultado:** exhaustividad 100 %, precisión 100 % — acierta en todo lo que se
puede contrastar por identificador — con **tasa 50 %** sobre 8 casos verificados
y **cobertura 61,5 %**. Las dos cifras juntas dicen algo que ninguna dice sola:
el módulo no se equivoca en lo que hace, se deja sin hacer lo que da sentido a
hacerlo.

### Lo que enseñó el corpus completo de RALSA (28/08)

Martín entregó sus **trece documentos reales**. Medirlos de una vez cambió el
diagnóstico del sistema más que cualquiera de los hallazgos individuales:

| | |
|---|---|
| Documentos con capa de texto | **0 de 13** |
| Leídos por el lector determinista, al recibirlos | **1 de 13** |
| Leídos tras los cuatro cambios de abajo | **7 de 13** |

**Ninguno trae texto.** Los trece son fotocopias de un RICOH. El OCR dejó de ser
una mejora y pasó a ser la única puerta de entrada al corpus.

Los cuatro cambios que subieron de 1 a 7 son de diseño, no parches por documento
—esa distinción es lo que decidió cómo se hicieron—:

1. **La familia documental decide qué se le puede preguntar.** Seis de los trece
   no fijan vigencia propia: son anexos, adendas, prórrogas, subrogaciones y
   rescates. Exigirles fecha de vencimiento y anotar «vigencia no determinada»
   no los evalúa, les hace una pregunta que no les corresponde. Ahora se
   clasifican por su **encabezamiento** —un contrato que contiene anexos no es un
   anexo— y los modificativos declaran *«su vigencia es la del documento que
   modifica»*, con el principal como requisito de datos.
2. **Ante varias fechas candidatas, se declara la ambigüedad en vez de elegir la
   primera.** El contrato de renovación de 2019 cita el vencimiento anterior
   (31/10/2019) antes de pactar el nuevo (31/10/2029). Quedarse con la primera
   daba «caducado» sobre un contrato vigente. Es el cambio que más veredictos
   *quita* y el más importante: elegir habría acertado la mayoría de las veces, y
   «la mayoría» es justo lo que un evaluador no puede permitirse.
3. **Los patrones se escriben por forma verbal, no por frase.** «finaliza el» no
   reconocía «finalizará el». Enumerar frases es perseguir documentos; enumerar
   la raíz del verbo cubre las conjugaciones que aún no se han visto.
4. **Números y fechas escritos con letra**, que es como escriben las escrituras
   notariales: *veinticinco años*, *mil novecientos noventa y cinco*.

Y un límite que conviene declarar sin adornos: **sobre este corpus, el lector
determinista solo no llega**. Seis documentos siguen sin veredicto y no por falta
de patrones, sino porque el OCR de una máquina de escribir de 1995 devuelve
«cuatroúe abril» y pierde el año. Para ésos, el **modo asistido** deja de ser un
extra y pasa a ser la vía principal — con la misma frontera de siempre: el modelo
**lee**, la regla **decide**.

---

### Hallazgo 4 · Juan, caso 9

El evaluador señaló que no distinguía «sin incidencias» de «no se ha podido
comprobar». Juan respondió que sí lo distingue —el tablero de GraphyFlow tiene
cinco filtros de estado— y tenía razón. Al verificarlo apareció el hallazgo real:

> **El estado de auditabilidad no viaja en la salida.** La comprobación está
> hecha; lo que falta es que el dato cruce la conexión hacia Mencía.

Ahí el aprendizaje no fue corregir un fallo, sino **precisar dónde estaba**: no en
el módulo, sino en el contrato de la conexión.

---

## 7 · El bucle cerrado

Detectar el fallo era la mitad; la otra es poder enseñar que se corrigió. El
evaluador tiene memoria (`nucleo/historial.py`): guarda una instantánea por
evaluación y compara con la anterior.

> Entre el 22/08/2026 y el 30/08/2026, 1 caso mejora: **caso 7 corregido — fallaba
> y ahora se supera**. Métricas: tasa 80,0 → 100,0 (+20,0); fallidos 1 → 0.

Separa mejoras de regresiones a propósito: un evaluador que sólo celebrase los
avances sería complaciente.

**Y el ciclo destapó un fallo propio.** Al simular la corrección de Mencía apareció
que la verdad de campo derivaba las contradicciones sólo de los hechos *activos*:
si ella marcaba el descartado como inactivo —justo lo que el informe le pedía— el
evaluador dejaba de ver la contradicción y su precisión caía al 0 %. **Habría
castigado la corrección que él mismo pidió.** Corregido: una contradicción resuelta
existió, así que también cuentan los hechos desactivados por una revisión humana
registrada.

---

## 8 · El asesor de mejora

El modelo generativo no trabaja en paralelo al núcleo determinista, sino detrás.
`nucleo/asesor.py` recibe el veredicto ya calculado —fallos con severidad,
hallazgos, requisitos y los criterios del panel de jueces— y hace lo que las
reglas no saben: **agrupar varios síntomas bajo una causa común y ordenar por lo
que más daño hace aguas abajo**.

Con el mismo candado que el resto del sistema: **toda recomendación tiene que
citar un caso fallido o pendiente**. Si cita uno inexistente o uno superado, se
descarta entera y el descarte se cuenta.

---

## 9 · Documentación pendiente, registrada

Sale calculada del propio sistema: cada caso no ejercitado declara qué haría falta.

**Martín** — desbloqueado el 28/08 con el primer documento real:
1. ~~Un PDF escaneado sin capa de texto~~ — **aportado**, y resultó ser la norma
   y no la excepción: el corpus de RALSA son fotocopias. Obligó a añadir OCR.
2. Su salida para más documentos: con uno solo, cuatro casos quedan sin
   ejercitar por construcción (versionado, incoherencia de fechas, vencimiento
   el mismo día, documento sin plazo)
3. Dos documentos del mismo inmueble, para el caso 5 (versionado)
4. Una segunda ejecución sobre el mismo documento, para el caso 10
5. Si «Obsoleto» distingue *sustituido* de *vencido*

**Álvaro** — resuelto lo principal el 27/08:
1. ~~Qué parámetros entran en la señal paramétrica y con qué peso cada uno~~ —
   **aportado**: reparto declarado y tabla de contribución por parámetro para los
   grupos SYN-0041 y SYN-0052. El caso 11 se rehizo sobre ella y pasa.
2. La tabla de contribución de los grupos que faltan (SYN-0047), o el acuerdo de
   que se pide aparte cuando haya que auditar una posición
3. Una consulta con `extra_no_pactado` no vacío
4. Una segunda exportación de la misma consulta

**Mencía** — 80 % tasa, 50 % cobertura:
1. Una exportación de un pedido sin contradicciones
2. Una de un pedido con un documento ilegible o ausente
3. Los dos PDF del PED1004
4. Una segunda exportación del mismo pedido
5. Una exportación con un documento no agrupable

**Juan**:
1. Una discrepancia en un campo distinto de cantidad o gramaje
2. Una segunda ejecución del pedido 42805

**Pablo**: qué entrega su módulo y en qué formato.

---

## 10 · Estado de comprobación

```
python pruebas.py   →   344 comprobaciones en verde
```

No prueba los módulos de los compañeros: prueba el evaluador. Comprueba que la
verdad de campo sobre documentos conocidos es la correcta y que **el sistema
reacciona cuando la salida se altera a propósito** — un contrato vencido declarado
vigente baja la exhaustividad, un documento inventado baja la precisión, dos
ejecuciones distintas no pasan repetibilidad.

Un validador que sólo aprueba no está demostrado.
