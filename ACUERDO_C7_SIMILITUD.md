# Acuerdo de conexión C7 — Similitud de proyectos → Evaluación y Calidad

**Productor:** Álvaro Subias (Kelvion) · **Consumidor:** Íñigo Daza (Evaluación y Calidad)
**Estado:** documentada · **Última revisión:** 27/08/2026

Este documento existe porque el evaluador se equivocó. La versión anterior de su
caso 11 marcaba como incoherentes salidas que eran correctas, y sólo se supo
porque Álvaro explicó cómo se construye la puntuación. Lo que sigue es lo que
hacía falta saber para no volver a equivocarse.

---

## 1 · Qué viaja por C7

La exportación en JSON de una consulta. No hay documentos: el módulo consulta un
histórico ya indexado y devuelve un ranking. El JSON es **a la vez el dato de
origen y la salida a evaluar**.

Campos pactados: `id_consulta`, `fecha_hora`, `pedido_consultado`, `resultados`,
`descartados`, `esquema_version`, `peso_semantico`.

`extra_no_pactado` viaja aparte, a propósito: es propuesta de Álvaro y todavía no
forma parte del acuerdo (caso 9).

---

## 2 · Cómo se construye la puntuación

Declarado por Álvaro el 27/08/2026.

| Componente | Peso total | Nº de parámetros | Peso unitario |
|---|---|---|---|
| Numéricos | 50 % | 11 | ≈ 4,5 % |
| Categóricos blandos | 50 % | 7 | ≈ 7,1 % |
| Categóricos duros | 0 % | 6 | 0 % |

El reparto dentro de cada mitad es **media simple (1/N)**. La puntuación que se
publica es ese bruto **normalizado min-max dentro del grupo de supervivientes**:
el mejor vale 1 y el peor 0.

Los seis categóricos duros —tipo de equipo, fluidos, materiales, código de
diseño— aportan cero porque son los filtros de la Capa 1: todos los
supervivientes los cumplen por construcción, así que no pueden discriminar.

**Álvaro declara el reparto 1/N como deuda técnica**, no como ponderación
razonada por importancia de ingeniería, y lo deja fuera del alcance de su TFG por
estar a seis días de la entrega: rediseñarlo movería la línea base con la que
está midiendo. Queda escrito para que la decisión sea explícita.

---

## 3 · Advertencia de trazabilidad ⚠

> **`parametros_justificativos` es informativo y NO explica la posición en el
> ranking.**

Publica ocho parámetros duros. Seis valen cero y los otros dos —presión y
temperatura de diseño— suman **menos del 10 %**. Quien decide son **siete
categóricos secundarios que no se publican**: diámetro de aleta, rating de
conexiones, normativa de marcado, unión tubo-placa y similares.

Consecuencia para cualquier consumidor de C7: **evaluar coherencia suponiendo
que la justificación explica la posición produce falsos positivos.** Le pasó a
este evaluador con SYN-0053 (4,10 % de desviación, puntuación 0,243) frente a
SYN-0092 (44,29 %, puntuación 0,646). No era un fallo: SYN-0092 tiene peor
componente numérico (0,106 frente a 0,275) pero coincide en 6 de 7 specs
secundarias frente a 3 de 7, y esa mitad pesa lo mismo.

El evaluador conserva la medición —ρ negativa, pares invertidos— como **hallazgo
de trazabilidad**, que informa y no puntúa.

---

## 4 · Qué hace falta para auditar una posición

La salida sola no basta. Para reproducir una puntuación desde fuera hace falta la
**tabla de contribución por parámetro**: una fila por candidata y parámetro, con
lo que cada uno aporta al bruto.

Álvaro la aportó el 27/08 para los grupos SYN-0041 y SYN-0052
(`diagnostico_peso_semantico_0.csv`, 17 supervivientes). Con ella, el caso 11 del
evaluador rehace las 17 puntuaciones y el orden completo: **diferencia máxima
0,0006**, dentro del redondeo de la propia tabla.

Sin esa tabla el caso queda **pendiente**, no fallado. Un evaluador que acusa sin
poder demostrarlo es exactamente lo que este sistema le reprocha a los módulos
que evalúa.

*Pendiente de acordar:* si la tabla pasa a formar parte de la salida, o se sigue
pidiendo aparte cuando haga falta auditar.

---

## 5 · Comportamientos deliberados — no son fallos

Propuestos por Álvaro el 27/08 y **aceptados** por Evaluación y Calidad.

| Comportamiento | Cómo lo trata el evaluador |
|---|---|
| **Lista vacía** | Resultado válido. Los casos de ranking pasan a *no aplica*; sólo se exige que el aviso diga **qué parámetro** dejó fuera a todas las candidatas (caso 8, severidad crítica). Una lista vacía sin causa se lee aguas abajo como «no hay nada parecido», que es otra cosa. |
| **Precedente antiguo en cabeza** | Aceptado. La fecha no descarta; sólo desempata entre candidatos técnicamente equivalentes. Ningún caso penaliza la antigüedad. |
| **Candidato marcado con datos faltantes** | Aceptado: benevolencia con marca, nunca descarte en silencio. El evaluador no lo trata como fallo, pero **sí exige que la marca conste** (caso 9): una candidata que sobrevive porque le faltaba el dato no está verificada igual que una que sobrevive por coincidir. Hoy eso vive en `extra_no_pactado`; debería entrar en el acuerdo. |

---

## 6 · Lo que el evaluador sigue señalando

No son incumplimientos del acuerdo: son diferencias entre lo que el módulo
optimiza y lo que espera quien lo consume. Se registran para que la decisión sea
explícita.

- **Caso 4 · equivalentes fuera de cabeza.** Con la definición de equivalencia
  del evaluador —coincidencia categórica exacta y desviación numérica bajo el
  umbral derivado del propio conjunto—, hay proyectos equivalentes que no llegan
  al top-5. La causa es el reparto 1/N de la sección 2. Álvaro lo asume como
  deuda; queda registrado, no oculto.
- **Hallazgo · la señal semántica se calcula y no se usa.** `peso_semantico` es 0
  en las cuatro salidas del juego cerrado: lo que viaja por C7 hoy es un ranking
  **íntegramente paramétrico**. Quien lo consuma no debería suponer que hay
  comprensión de texto detrás. Al re-medirlo con documentos reales, el hallazgo
  se cierra o se confirma.
- **Hallazgo · el corpus no es el mismo en todas las consultas.** Cuando el
  pedido procede de una ficha del propio histórico, esa ficha se autoexcluye y el
  total baja en una. El comportamiento es correcto —un proyecto no se parece a sí
  mismo— pero no está escrito, y quien compare dos consultas verá 96 y 97 sin
  saber por qué.

---

## 7 · Juego cerrado de evaluación

Cuatro salidas, aportadas el 27/08, las cuatro con `esquema_version` y
`peso_semantico`:

| Fichero | Qué es | Veredicto del evaluador |
|---|---|---|
| `caso1_syn0047_acierto.json` | Acierto limpio | 8 pasa · 2 pendiente · 1 no aplica |
| `caso2_syn0041_fallo_conocido.json` | Fallo conocido (SYN-0045) | 8 pasa · 1 no pasa (caso 4) · 1 pendiente · 1 no aplica |
| `caso3_syn0052_distractores.json` | Distractores compitiendo | 8 pasa · 1 no pasa (caso 4) · 1 pendiente · 1 no aplica |
| `caso4_lista_vacia.json` | Lista vacía | 4 pasa · 3 pendiente · 4 no aplica |

Los casos 10 (repetibilidad) quedan pendientes en las cuatro: hace falta una
segunda exportación de la misma consulta sobre el mismo corpus.
