"""
Núcleo común del sistema de evaluación — TFG Íñigo Daza · Bloque de Evaluación y Calidad.

Lo que vive aquí es lo que NO cambia de un módulo a otro:

  · cómo se lee un documento                        (pdf.py)
  · cómo se normaliza y se compara un valor         (texto.py)
  · cómo se contrasta lo reportado contra lo real   (contraste.py)
  · cómo se ejecuta una batería y se resume         (bateria.py)
  · cómo se redacta el veredicto y se exporta       (veredicto.py)
  · dónde encajaría un modelo de lenguaje           (llm.py)

Lo que cambia vive en `modulos/`: de qué documentos se extraen los campos, qué
campos son comparables, cómo se lee la respuesta de ese módulo y qué casos
forman su batería.

El sistema no es una suma de validadores independientes porque todas las ramas
emiten el mismo objeto, con las mismas dos métricas —exhaustividad y precisión—
y la misma regla de anclaje: cada aspecto a mejorar cita el caso que lo evidencia.
Lo comparable no son los módulos, es el veredicto.
"""

# Versión del paquete completo. La interfaz la comprueba al arrancar para avisar
# si algún fichero se ha quedado descompasado al subirlo a GitHub.
VERSION = 12
