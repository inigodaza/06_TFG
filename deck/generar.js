const pptxgen = require("pptxgenjs");

// Paleta: la del propio sistema, para que las diapositivas y la pantalla que
// Íñigo va a enseñar sean la misma cosa.
const TINTA = "0B0B0B";
const SUPERFICIE = "FCFCFB";
const GRIS = "52514E";
const GRIS_CLARO = "8A8885";
const ACENTO = "2A78D6";
const VERDE = "006300";
const ROJO = "D03B3B";
const BLANCO = "FFFFFF";

const H1 = "Cambria";
const BODY = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
const W = 13.333, H = 7.5;

// ---------------------------------------------------------------- utilidades

function fondoOscuro(s) {
  s.background = { color: TINTA };
}
function fondoClaro(s) {
  s.background = { color: SUPERFICIE };
}

function titulo(s, texto, opts = {}) {
  s.addText(texto, {
    x: 0.7, y: opts.y || 0.55, w: W - 1.4, h: 0.9,
    fontFace: H1, fontSize: opts.size || 38, bold: true,
    color: opts.color || TINTA, align: "left", isTextBox: true, margin: 0,
  });
}

function subtitulo(s, texto, y, color) {
  s.addText(texto, {
    x: 0.7, y: y, w: W - 1.4, h: 0.5,
    fontFace: BODY, fontSize: 16, color: color || GRIS,
    isTextBox: true, margin: 0,
  });
}

// La pastilla de estado: glifo + palabra + color. Es el motivo visual del
// sistema —el color nunca carga solo con el significado— y se repite aquí.
function pastilla(s, x, y, glifo, texto, color, fondo) {
  const w = 0.22 + texto.length * 0.105 + 0.3;
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h: 0.38, rectRadius: 0.19,
    fill: { color: fondo }, line: { color: fondo },
  });
  s.addText(glifo + "  " + texto, {
    x, y, w, h: 0.38, fontFace: BODY, fontSize: 12, bold: true,
    color, align: "center", valign: "middle", isTextBox: true, margin: 0,
  });
  return w;
}

function circuloIcono(s, x, y, glifo, colorFondo, colorGlifo) {
  s.addShape(pres.ShapeType.ellipse, {
    x, y, w: 0.52, h: 0.52,
    fill: { color: colorFondo }, line: { color: colorFondo },
  });
  s.addText(glifo, {
    x, y, w: 0.52, h: 0.52, fontFace: BODY, fontSize: 20, bold: true,
    color: colorGlifo, align: "center", valign: "middle",
    isTextBox: true, margin: 0,
  });
}

function filaIcono(s, x, y, ancho, glifo, cabecera, cuerpo, colorCirculo) {
  circuloIcono(s, x, y, glifo, colorCirculo || ACENTO, BLANCO);
  s.addText(cabecera, {
    x: x + 0.78, y: y - 0.04, w: ancho - 0.78, h: 0.4,
    fontFace: BODY, fontSize: 17, bold: true, color: TINTA,
    isTextBox: true, margin: 0,
  });
  s.addText(cuerpo, {
    x: x + 0.78, y: y + 0.36, w: ancho - 0.78, h: 0.95,
    fontFace: BODY, fontSize: 14, color: GRIS, isTextBox: true, margin: 0,
  });
}

function tarjeta(s, x, y, w, h, relleno) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.06,
    fill: { color: relleno || "FFFFFF" },
    line: { color: "E4E2DE", width: 1 },
    shadow: { type: "outer", angle: 90, blur: 8, offset: 2,
              color: "000000", opacity: 0.06 },
  });
}

function pie(s, texto) {
  s.addText(texto, {
    x: 0.7, y: H - 0.68, w: W - 1.4, h: 0.32,
    fontFace: BODY, fontSize: 11, color: GRIS_CLARO,
    isTextBox: true, margin: 0,
  });
}

// ------------------------------------------------------------------ 1 · portada

let s = pres.addSlide();
fondoOscuro(s);
s.addText("Bloque de Evaluación y Calidad", {
  x: 0.9, y: 2.35, w: 11.5, h: 1.1,
  fontFace: H1, fontSize: 46, bold: true, color: BLANCO,
  isTextBox: true, margin: 0,
});
s.addText("Qué hace el sistema cuando un módulo dice algo que el documento no sostiene", {
  x: 0.9, y: 3.5, w: 10.4, h: 0.9,
  fontFace: BODY, fontSize: 19, color: "C9C7C3", isTextBox: true, margin: 0,
});
s.addText("Íñigo Daza Arteche   ·   1 de septiembre de 2026", {
  x: 0.9, y: 5.5, w: 8, h: 0.4,
  fontFace: BODY, fontSize: 14, color: GRIS_CLARO, isTextBox: true, margin: 0,
});
let px = 0.9;
px += pastilla(s, px, 4.55, "✓", "Superado", "9BE39B", "13361A") + 0.16;
px += pastilla(s, px, 4.55, "✕", "Fallido", "F4A6A2", "3A1614") + 0.16;
pastilla(s, px, 4.55, "◌", "Pendiente", "CFCDC8", "2A2926");
s.addNotes("Mi bloque recibe la salida de un módulo, calcula por su cuenta cuál "
  + "debería haber sido, contrasta y emite un veredicto. La frontera del trabajo "
  + "es una frase: la salida se le entrega. No voy a buscarla, y eso está "
  + "razonado, no improvisado.");

// ------------------------------------------------------- 2 · qué funciona hoy

s = pres.addSlide();
fondoClaro(s);
titulo(s, "Qué funciona hoy");
subtitulo(s, "Cuatro módulos con batería de preguntas cerrada y ejecutada contra la salida real del compañero.", 1.45);

const anchoCol = 5.5;
filaIcono(s, 0.7, 2.55, anchoCol, "1",
  "Las baterías, integradas",
  "Martín y Álvaro entran en el sistema con sus preguntas propias. La de Juan ya estaba.");
filaIcono(s, 0.7, 4.55, anchoCol, "2",
  "Una interfaz por módulo",
  "Se elige a quién evaluar, se entrega su salida y el sistema hace todo lo demás.");
filaIcono(s, 7.15, 2.55, anchoCol, "3",
  "El ciclo completo",
  "Lee, deduce qué debería haber salido, contrasta, puntúa por severidad y redacta.");
filaIcono(s, 7.15, 4.55, anchoCol, "!",
  "Lo que no está",
  "No hay recogida automática de la salida: alguien la pega. Es una decisión de alcance, y está razonada.",
  GRIS);
pie(s, "42 casos diseñados · 13 criterios cualitativos");
s.addNotes("Cuatro módulos, no dos. Y lo que no está no es un olvido: no hay "
  + "recogida automática porque ningún módulo publica un punto de acceso, y un "
  + "puente contra prototipos que cambian cada semana rompe lo único que un "
  + "evaluador no puede permitirse: distinguir si falla el módulo o falla el puente.");

// ------------------------------------------------- 3 · la demo, módulo de Martín

s = pres.addSlide();
fondoClaro(s);
titulo(s, "Un documento de Martín, de principio a fin");
subtitulo(s, "Contratos de arrendamiento escaneados. Ninguno traía texto: son fotocopias.", 1.45);

const pasos = [
  ["Reconocer", "El sistema escanea la imagen y saca el texto por su cuenta"],
  ["Enseñar lo leído", "Se ve el texto reconocido, para poder comprobar cada valor"],
  ["Deducir", "De las cláusulas salen las fechas, el plazo y la prórroga"],
  ["Contrastar", "Sólo entonces se mira lo que dijo el módulo"],
];
let cx = 0.7;
const anchoPaso = 2.80, hueco = 0.28;
pasos.forEach((p, i) => {
  tarjeta(s, cx, 2.35, anchoPaso, 2.45);
  s.addText(String(i + 1), {
    x: cx + 0.3, y: 2.6, w: 0.6, h: 0.5, fontFace: H1, fontSize: 30,
    bold: true, color: ACENTO, isTextBox: true, margin: 0,
  });
  s.addText(p[0], {
    x: cx + 0.3, y: 3.18, w: anchoPaso - 0.55, h: 0.4,
    fontFace: BODY, fontSize: 16, bold: true, color: TINTA,
    isTextBox: true, margin: 0,
  });
  s.addText(p[1], {
    x: cx + 0.3, y: 3.6, w: anchoPaso - 0.55, h: 1.1,
    fontFace: BODY, fontSize: 12.5, color: GRIS, isTextBox: true, margin: 0,
  });
  cx += anchoPaso + hueco;
});

s.addText("El sistema empezó dando veredicto sobre 1 de los 13 documentos. Hoy sobre 11.", {
  x: 0.7, y: 5.35, w: 11.9, h: 0.5,
  fontFace: BODY, fontSize: 18, italic: true, color: TINTA,
  isTextBox: true, margin: 0,
});
pie(s, "Y cuando el escaneo no da para más, el veredicto lo dice: «no se ha podido comprobar» no es «sin incidencias».");
s.addNotes("Enseñar el panel por documento con CONTRATO ARRENDAMIENTO CRED: "
  + "ocho de ocho campos leídos de un escaneo sin capa de texto, y debajo el "
  + "texto reconocido. Después pegar la ficha de IAlert y enseñar la batería por "
  + "encima, sin entrar caso por caso.");

// -------------------------------------------- 4 · dos formatos, un mismo veredicto

s = pres.addSlide();
fondoClaro(s);
titulo(s, "Dos módulos, dos formatos, el mismo veredicto");

tarjeta(s, 0.7, 1.95, 5.85, 3.15);
circuloIcono(s, 1.1, 2.3, "▤", ACENTO, BLANCO);
s.addText("Martín · documentos", {
  x: 1.88, y: 2.32, w: 4.4, h: 0.4, fontFace: BODY, fontSize: 18, bold: true,
  color: TINTA, isTextBox: true, margin: 0,
});
s.addText([
  { text: "PDF escaneados, sin texto dentro", options: { bullet: true, breakLine: true } },
  { text: "Hay que reconocer la imagen antes de poder leer nada", options: { bullet: true, breakLine: true } },
  { text: "Lo que se contrasta es una lectura contra otra lectura", options: { bullet: true } },
], {
  x: 1.15, y: 3.0, w: 5.05, h: 1.95, fontFace: BODY, fontSize: 14,
  color: GRIS, paraSpaceAfter: 8, isTextBox: true, margin: 0,
});

tarjeta(s, 6.9, 1.95, 5.75, 3.15);
circuloIcono(s, 7.3, 2.3, "{ }", ACENTO, BLANCO);
s.addText("Álvaro · exportación", {
  x: 8.08, y: 2.32, w: 4.3, h: 0.4, fontFace: BODY, fontSize: 18, bold: true,
  color: TINTA, isTextBox: true, margin: 0,
});
s.addText([
  { text: "Aquí no hay documentos: el módulo entrega JSON", options: { bullet: true, breakLine: true } },
  { text: "El evaluador rehace la puntuación y el orden por su cuenta", options: { bullet: true, breakLine: true } },
  { text: "Y decide él mismo qué proyectos son equivalentes", options: { bullet: true } },
], {
  x: 7.35, y: 3.0, w: 4.95, h: 1.95, fontFace: BODY, fontSize: 14,
  color: GRIS, paraSpaceAfter: 8, isTextBox: true, margin: 0,
});

s.addText("Lo comparable no son los módulos: es el veredicto.", {
  x: 0.7, y: 5.6, w: 11.9, h: 0.6, fontFace: H1, fontSize: 24, bold: true,
  color: TINTA, isTextBox: true, margin: 0,
});
s.addNotes("Todas las ramas emiten el mismo objeto, con las mismas dos métricas "
  + "y la misma regla de anclaje. Por eso el sistema no es una suma de "
  + "validadores independientes.");

// ------------------------------------------------ 5 · el caso reñido de Álvaro

s = pres.addSlide();
fondoOscuro(s);
s.addText("La prueba que sí encuentra algo", {
  x: 0.9, y: 0.85, w: 11.5, h: 0.9, fontFace: H1, fontSize: 38, bold: true,
  color: BLANCO, isTextBox: true, margin: 0,
});
s.addText("Un validador que sólo aprueba no está demostrado.", {
  x: 0.9, y: 1.8, w: 11, h: 0.5, fontFace: BODY, fontSize: 17,
  color: "C9C7C3", italic: true, isTextBox: true, margin: 0,
});

s.addShape(pres.ShapeType.roundRect, {
  x: 0.9, y: 2.75, w: 11.5, h: 1.5, rectRadius: 0.08,
  fill: { color: "1C1C1A" }, line: { color: "34332F", width: 1 },
});
s.addText("En el módulo de Álvaro, dos proyectos que NO son equivalentes al pedido "
  + "adelantan en el ranking a uno que sí lo es.", {
  x: 1.25, y: 3.0, w: 10.8, h: 1.0, fontFace: BODY, fontSize: 19,
  color: BLANCO, isTextBox: true, margin: 0,
});

s.addText([
  { text: "Es un caso reñido, y el propio autor lo señala como el más interesante.", options: { bullet: true, breakLine: true } },
  { text: "El evaluador no lo detecta mirando la puntuación: la rehace desde las señales declaradas.", options: { bullet: true, breakLine: true } },
  { text: "Le propuse antes otro hallazgo y Álvaro demostró que mi premisa era falsa. Rehíce el caso con los datos que me aportó, y ahora pasa.", options: { bullet: true } },
], {
  x: 0.9, y: 4.6, w: 11.5, h: 2.0, fontFace: BODY, fontSize: 15,
  color: "C9C7C3", paraSpaceAfter: 10, isTextBox: true, margin: 0,
});
s.addNotes("Que el evaluador acepte que se equivocó vale más que un caso que "
  + "pasa. Es la parte del trabajo que demuestra que discrimina.");

// ------------------------------------------- 6 · desde la última reunión

s = pres.addSlide();
fondoClaro(s);
titulo(s, "Desde la última reunión");

filaIcono(s, 0.7, 1.85, 11.9, "◍",
  "Llegó el corpus real y obligó a rehacer la lectura",
  "Trece contratos de RALSA, ninguno con texto dentro. Hubo que reconocer la imagen para poder leer una sola fecha.");
filaIcono(s, 0.7, 3.45, 11.9, "▦",
  "Medir al evaluador contra una verdad que no ha escrito él",
  "Leí unos cuantos documentos a mano, campo a campo, y contra eso se mide el sistema. No cuántos lee: cuántos lee bien, y cuántas veces se calla cuando debe.");
filaIcono(s, 0.7, 5.05, 11.9, "⟲",
  "Cinco fallos propios, encontrados y corregidos",
  "Todos del mismo tipo: el evaluador acusaba a un compañero de algo que no había hecho. Es el error que este bloque existe para detectar.",
  ROJO);
s.addNotes("El tercero es el importante. El último apareció ayer: un caso daba "
  + "FALLIDO a Martín por no declarar la antelación de una insignia de ficha, "
  + "que es una cuenta atrás y no una alerta. Ahora dice PENDIENTE: falta una "
  + "pantalla, no falla un módulo.");

// ------------------------------------------------- 7 · próximos pasos

s = pres.addSlide();
fondoOscuro(s);
s.addText("Los siguientes pasos", {
  x: 0.9, y: 0.9, w: 11.5, h: 0.9, fontFace: H1, fontSize: 40, bold: true,
  color: BLANCO, isTextBox: true, margin: 0,
});
s.addText("Quedan dos módulos del proyecto por cerrar conmigo.", {
  x: 0.9, y: 1.9, w: 11.2, h: 0.5, fontFace: BODY, fontSize: 18,
  color: "C9C7C3", isTextBox: true, margin: 0,
});

const siguientes = [
  ["Mencía", "Cerrar su módulo con ella",
   "Su exportación trae los hechos y las contradicciones en el mismo fichero. "
   + "Quiero repasarla con ella antes de dar nada por bueno, y después necesito "
   + "una segunda exportación para comprobar que una corrección se refleja."],
  ["Pablo", "Empezar el suyo desde cero",
   "Aquí no hay nada todavía, y no por dejarlo: no sé qué entrega ni en qué "
   + "formato. Escribirle preguntas sin haber visto una salida real sería el "
   + "mismo error que mido en los demás."],
];
let sy = 2.72;
siguientes.forEach((item, i) => {
  s.addShape(pres.ShapeType.roundRect, {
    x: 0.9, y: sy, w: 11.5, h: 1.72, rectRadius: 0.08,
    fill: { color: "1C1C1A" }, line: { color: "34332F", width: 1 },
  });
  s.addShape(pres.ShapeType.ellipse, {
    x: 1.3, y: sy + 0.36, w: 0.62, h: 0.62,
    fill: { color: ACENTO }, line: { color: ACENTO },
  });
  s.addText(String(i + 1), {
    x: 1.3, y: sy + 0.36, w: 0.62, h: 0.62, fontFace: BODY, fontSize: 22,
    bold: true, color: BLANCO, align: "center", valign: "middle",
    isTextBox: true, margin: 0,
  });
  s.addText(item[0] + "  ·  " + item[1], {
    x: 2.2, y: sy + 0.28, w: 9.8, h: 0.42, fontFace: BODY, fontSize: 19,
    bold: true, color: BLANCO, isTextBox: true, margin: 0,
  });
  s.addText(item[2], {
    x: 2.2, y: sy + 0.76, w: 9.8, h: 0.85, fontFace: BODY, fontSize: 14,
    color: "ADABA7", isTextBox: true, margin: 0,
  });
  sy += 1.92;
});

s.addText("Y una decisión que no puedo tomar solo: cuando un contrato se renueva "
  + "por tramos, ¿qué plazo tiene pactado?", {
  x: 0.9, y: 6.58, w: 11.5, h: 0.42, fontFace: BODY, fontSize: 13.5,
  color: GRIS_CLARO, isTextBox: true, margin: 0,
});
s.addNotes("Los dos pasos que quedan. Y de paso, lo que necesito hoy: de Martín, "
  + "las fichas que me faltan y la pantalla de avisos; de Álvaro, una segunda "
  + "exportación de la misma consulta. La decisión del pie es la única que "
  + "traigo: lo que decidamos hay que aplicarlo igual en el módulo y en el "
  + "evaluador, o la discrepancia es de vocabulario y no de calidad.");

pres.writeFile({ fileName: "/home/claude/01_TFG/deck/Evaluacion_y_Calidad_01sep.pptx" })
  .then((f) => console.log("escrito:", f));
