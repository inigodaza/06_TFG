# Reunión del 1 de septiembre · 10:00
## Íñigo Daza — Bloque de Evaluación y Calidad

---

# PARTE 1 · La fila de la tabla maestra
### Para pegar hoy antes de las 18:00

> Los dos `«…»` son los únicos huecos: pega la URL de tu app en Streamlit y la del
> repositorio. Todo lo demás está comprobado hoy, 31/08.

---

### 1 · Qué funciona hoy y qué no

**Funciona:** el ciclo completo sobre cuatro módulos — se entrega la salida del
compañero, el evaluador calcula por su cuenta cuál debería haber sido, contrasta,
ejecuta la batería, gradúa por severidad y emite veredicto con informe. 42 casos
diseñados, 13 criterios cualitativos, 389 comprobaciones automáticas en verde.

**No funciona / no está:** (a) no hay recogida automática de la salida de los
módulos — es a petición y por decisión de alcance, no por falta de tiempo;
(b) Pablo no tiene batería porque no hay salida que ver; (c) el modo asistido por
modelo está construido y probado, pero **no medido** contra el conjunto de
referencia; (d) el ciclo de mejora completo —hallazgo, corrección del compañero,
nueva medición— no se ha cerrado todavía con nadie.

---

### 2 · Evidencia

| Qué | Dónde |
|---|---|
| App en funcionamiento | «PEGA AQUÍ LA URL DE STREAMLIT» |
| Código y baterías | «PEGA AQUÍ LA URL DEL REPOSITORIO» |
| Alcance, hallazgos y límites declarados | `ALCANCE.md` en el repositorio |
| Batería de comprobación | `python pruebas.py` → 389 en verde |
| Medición contra verdad etiquetada a mano | `python medir.py referencia/etiquetado.xlsx` |
| Que el OCR funciona sin caché | `python prueba_ocr_real.py` → 13/13 |
| Que aguanta escaneos peores | `python prueba_robustez_ocr.py` → 21 variantes, 0 invenciones |

---

### 3 · Qué he hecho desde la última reunión

- **Corpus real de Martín**: 13 documentos escaneados, ninguno con capa de texto.
  Se incorporó OCR y el lector pasó de dar veredicto sobre **1 de 13** a **11 de 13**.
- **Conjunto de referencia etiquetado a mano**: 7 documentos leídos por una persona,
  campo a campo, para medir al evaluador contra una verdad que no ha escrito él.
  Precisión **63,6 % → 76,9 %**; prudencia **100 %**; estado de vigencia **57,1 % → 83,3 %**.
- **Caso 11 de Álvaro rehecho** con la tabla de contribución que aportó: 17 de 17
  posiciones reproducidas, desviación máxima 0,0006. El hallazgo original era falso
  y se retiró; en su lugar queda uno correcto sobre la justificación publicada.
- **Cinco fallos propios encontrados y corregidos**, todos del mismo tipo: el
  evaluador acusaba a un compañero de algo que no había hecho. El último, ayer: el
  caso 7 daba FALLIDO a Martín por no declarar la antelación de una insignia de
  ficha, que es una cuenta atrás y no una alerta.

---

### 4 · Qué necesito, de quién y para cuándo

| De quién | Qué | Para cuándo |
|---|---|---|
| **Martín** | Las 7 fichas de IAlert que faltan (tengo 6 de 13) y una captura del panel de «Próximos eventos» | Esta semana |
| **Martín** | Confirmar si «Obsoleto» distingue *sustituido* de *vencido* | En la reunión |
| **Mencía** | Reexportación del PED1004 con el hecho descartado en `is_active = 0` | Esta semana |
| **Álvaro** | Una consulta con `extra_no_pactado` no vacío, y una segunda exportación de la misma consulta | Sin urgencia |
| **Juan** | Una discrepancia en un campo distinto de cantidad o gramaje | Sin urgencia |
| **Pablo** | Qué entrega su módulo y en qué formato | Para poder empezar |

---

### 5 · Qué entrego yo a otros módulos

No entrego datos a ningún módulo: **soy el final de la cadena**. Lo que entrego es
el veredicto sobre su salida, en cuatro formatos, todos exportables desde la app:

- **Informe de evaluación** (Markdown) — veredicto, métricas, hallazgos y límites declarados.
- **Plantilla común de casos** (Markdown y CSV) — caso, entradas, esperado, observado, severidad, pasa/no pasa.
- **Aspectos a mejorar**, cada uno citando el caso que lo evidencia. Si no cita un caso, se descarta.
- **Lista de lo que necesito de cada uno** para poder ejercitar los casos que hoy están pendientes.

---

### 6 · Bloqueo o decisión para el martes

**Ninguno técnico. Uno de criterio, y es de equipo.**

Cuando el evaluador y el compañero discrepan y el documento admite las dos
lecturas, ¿quién fija el criterio? Tengo tres casos concretos sobre el contrato de
ZURITA, que pacta *«UN AÑO, prorrogándose por plazos anuales sucesivos hasta DIEZ,
para volverse a prorrogar por CINCO, hasta un máximo de QUINCE»*:

- **El plazo pactado**, ¿es 1 año (el primer tramo) o 15 (el tope)?
- **La fecha de vencimiento** de un contrato así, ¿cuál es? Hoy me abstengo y lo declaro.
- La cláusula que **renuncia a la tácita reconducción**, ¿hace la prórroga «renunciada» o «expresa»?

Lo que decidamos hay que aplicarlo igual en el módulo de Martín y en mi evaluador;
si no, la discrepancia es de vocabulario y no de calidad. **Cinco minutos con Martín
y Fabián y queda cerrado.**

---

### 7 · Resultado medible de la siguiente prueba

La prueba pasa si, con las 13 fichas de Martín y las 13 filas del conjunto de
referencia etiquetadas:

| Métrica | Umbral | Hoy |
|---|---|---|
| Prudencia (campos que el documento no dice y el sistema calla) | **100 %** — cero invenciones | **100 %** ✓ |
| Precisión de lo que afirma | **≥ 85 %** | 76,9 % |
| Cobertura de la batería de Martín (casos verificados / diseñados) | **≥ 75 %** (9 de 12) | 50 % (6 de 12) |

**La primera no es negociable.** Un evaluador que se inventa un campo acusa a un
compañero de un fallo que no ha cometido, y eso le quita autoridad a todo lo demás.
Las otras dos se mueven con los datos que me lleguen.

---

### Sobre las conexiones — hablado / documentado / probado

| Conexión | Estado |
|---|---|
| C1 · Martín → Evaluación | **Documentada y probada**: 13 PDF reales + 6 fichas reales de IAlert → veredicto |
| C6 · Mencía → Evaluación | **Documentada y probada**: `export_PED1004.json` real → veredicto |
| C7 · Álvaro → Evaluación | **Documentada y probada**: JSON real → ranking reproducido 17/17 |
| C8 · Juan → Evaluación | **Documentada y probada**: salida real de GraphyFlow → veredicto |
| Pablo → Evaluación | **Ni hablado en términos técnicos.** Sin salida, sin formato, sin batería |

**La precisión que importa:** las cuatro están probadas **en formato** —la salida
real entra y produce veredicto— pero **el transporte es manual**: alguien pega la
salida. No hay conexión automática con ningún módulo, y no la hay por decisión de
alcance documentada, no por falta de tiempo: ninguno de los cinco módulos publica
un punto de acceso, y un puente contra prototipos que cambian cada semana rompe la
única cosa que un evaluador no puede permitirse — distinguir si falla el módulo o
falla el puente. Está razonado en `ALCANCE.md` §2.

**Nada falla en las conexiones.** Lo que falta es volumen de salida.

---
---

# PARTE 2 · Los cinco minutos del martes

## Minuto 0-1 · Qué es y dónde termina

> «Mi bloque recibe la salida de un módulo, calcula por su cuenta cuál debería
> haber sido, contrasta y emite un veredicto. La frontera es una frase: **la salida
> se le entrega**. No voy a buscarla, y eso está razonado, no improvisado.»

## Minuto 1-3 · La demo · **una sola pantalla**

Abre el módulo de Martín con **CONTRATO_ARRENDAMIENTO_CRED** y enseña **el panel por
documento**:

> «Ocho de ocho campos leídos de un escaneo sin capa de texto. Y aquí abajo, el texto
> que ha reconocido: cada valor se puede comprobar contra el documento.»

Después pega la salida de IAlert y enseña **dos casos, no doce**:

- **Un hallazgo real** (prórroga tácita vs expresa, severidad crítica):
  > «Con prórroga tácita, no hacer nada renueva el contrato. Con prórroga expresa,
  > no hacer nada lo extingue. Quien lea "tácita ✓" se quedará quieto y perderá la
  > estación de servicio. Los dos textos contienen la palabra "prórroga"; el
  > discriminante es el verbo de la cláusula.»

- **El caso 7, que ayer daba FALLIDO y hoy dice PENDIENTE**:
  > «Éste es el que más me importa enseñar, porque el fallo era mío. Estaba contando
  > una insignia de la ficha como si fuera una alerta, y le exigía a Martín declarar
  > la antelación de algo que no salta. La respuesta correcta no es "Martín falla",
  > es "todavía no me has enseñado esa pantalla".»

## Minuto 3-4 · Que el evaluador también se mide

> «Todo lo anterior dice cuántos documentos leo. No dice si lo que leo es correcto.
> Un lector que se invente siete fechas plausibles saca la misma cifra que uno que
> las lea bien. Así que hay un conjunto de referencia etiquetado a mano, y contra él
> se cuentan cinco desenlaces por campo — y dos van en mayúsculas: **ERROR** e
> **INVENCIÓN**. Precisión 76,9 %. Prudencia **100 %**: ni una sola vez ha afirmado
> un campo que el documento no dice.»

Y el remate, si hay tiempo:

> «Lo probé también con escaneos peores: 21 variantes degradadas, cero invenciones.
> Cuando la calidad baja y pierde campos, el contrato pasa de "vigente" a "no
> clasificado" — no a "caducado". Se declara incapaz en vez de acusar.»

## Minuto 4-5 · Lo que pido

> «Necesito volumen de salida, no conexiones nuevas. Siete fichas de Martín, la
> reexportación de Mencía, y cinco minutos para cerrar un criterio: qué es el plazo
> pactado en un contrato que se prorroga en escalera.»

---

## Las tres preguntas que te va a hacer, con la respuesta preparada

**«Enséñame el bucle cerrado de mejora.»**
> «El mecanismo está construido y probado: guarda una instantánea por evaluación y
> compara. Lo que **no** puedo enseñar es un ciclo completo con la corrección de un
> compañero, porque depende de que Mencía reexporte. Está declarado así en ALCANCE
> §7, y el historial además es de sesión: en Streamlit se borra al redesplegar.
> Persistirlo está en la documentación pendiente.»

**«¿Por qué no has automatizado la recogida?»**
> «Porque no hay dónde enchufarse: ninguno de los cinco publica un endpoint. Exige
> que cada compañero publique un contrato técnico y lo mantenga, y eso es calendario
> de equipo. Además sería un puente sobre prototipos que cambian cada semana, y si
> se rompe deja de poder distinguirse si falla el módulo o falla el puente — que para
> un evaluador es el peor fallo posible. Lo que sí está hecho es toda la mitad
> difícil: el intérprete, el esquema, la frontera de tipos y el acuerdo escrito. El
> día que alguien publique un endpoint, sólo hay que escribir la llamada.»

**«¿Cómo sé que tu evaluador no se equivoca?»**
> «Porque se mide contra una verdad que no ha escrito él, y porque he encontrado y
> corregido cinco fallos propios — todos del mismo tipo: acusar a un compañero de
> algo que no había hecho. Los llevo documentados uno a uno. Un validador que sólo
> aprueba no está demostrado.»

---

## Antes de las 10:00

- [ ] Fila de la tabla maestra pegada (**hoy antes de las 18:00**)
- [ ] Subir el zip de hoy al repositorio y comprobar que la app abre
- [ ] Abrir la app **antes** de la reunión — el primer arranque es lento
- [ ] **No subir un documento nuevo en directo**: son ~10 s por página
- [ ] Tener a mano `ALCANCE.md` por si pregunta por un límite concreto
