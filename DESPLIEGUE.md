# Cómo desplegar esto sin que se rompa

El fallo más frecuente de este proyecto no es de código: es que la subida a GitHub
**aplana las carpetas**. Los ficheros de `nucleo/` acaban sueltos en la raíz, las
carpetas conservan la versión anterior, y Python importa la vieja. El resultado es
un `AttributeError` que parece de programación pero es de despliegue.

La app se defiende: al arrancar comprueba que cada fichero tiene las piezas que
los demás esperan, y si no, lo dice con el nombre del fichero que falta en vez de
reventar a mitad de camino.

---

## La estructura que tiene que quedar en el repositorio

```
app.py
ui.py
esquema.py
pruebas.py
requirements.txt
packages.txt
README.md
ALCANCE.md
DESPLIEGUE.md
.streamlit/
    config.toml
nucleo/
    __init__.py  pdf.py  texto.py  contraste.py  bateria.py  veredicto.py
    llm.py  jueces.py  informe.py  plantilla.py  asesor.py  historial.py
modulos/
    __init__.py  auditoria.py  vigencia.py  similitud.py
    contradicciones.py  gobernanza.py
demo/
    __init__.py
    guion.py
    datos/
        vigencia/          PRUEBA_1.pdf … PRUEBA_6.pdf
        similitud/         caso1…caso4.json, README.md
        contradicciones/   export_PED1004.json
        auditoria/         LEEME.md
```

**Si ves `asesor.py`, `guion.py` o `vigencia.py` sueltos en la raíz, está mal.**
Esos tres viven dentro de `nucleo/`, `demo/` y `modulos/` respectivamente.

---

## Método recomendado: GitHub Desktop

Es el único que no aplana nada, y se hace una vez.

1. Instala **GitHub Desktop** (desktop.github.com) y entra con tu cuenta.
2. `File → New repository`. Nombre: `04_TFG`. **Marca «Initialize with README»**
   y anota la carpeta local que te propone.
3. Abre esa carpeta en el explorador y **copia dentro todo el contenido** de la
   carpeta extraída del zip — los ocho ficheros sueltos y las cuatro carpetas.
   No la carpeta `01_TFG` entera: su contenido.
4. Vuelve a GitHub Desktop. Verás la lista de cambios. Escribe un mensaje
   («versión 6») y pulsa **Commit to main**.
5. Pulsa **Publish repository**. Desmarca «Keep this code private» sólo si
   quieres que sea pública — con la clave de Gemini en Secrets, **déjala
   privada**.

A partir de aquí, actualizar es: copiar los ficheros nuevos encima, Commit, Push.
Nunca se vuelve a aplanar.

---

## Método sin instalar nada (web de GitHub)

Funciona, pero hay que crear cada carpeta a mano **antes** de subir sus ficheros.

1. Crea un repositorio nuevo y vacío (`04_TFG`), privado.
2. **Primero los ficheros de la raíz.** `Add file → Upload files` y arrastra sólo
   los ocho de arriba (`app.py`, `ui.py`, `esquema.py`, `pruebas.py`,
   `requirements.txt`, `packages.txt`, `README.md`, `ALCANCE.md`). Commit.
3. **Ahora cada carpeta, una a una.** Para crear `nucleo/`:
   `Add file → Create new file`, y en el nombre escribe exactamente
   `nucleo/__init__.py`. Pega dentro el contenido de ese fichero. Commit.
   Eso crea la carpeta.
4. Entra en la carpeta `nucleo/` recién creada y usa `Add file → Upload files`
   para arrastrar **los otros once** ficheros de `nucleo/`. Commit.
5. Repite el par crear-y-subir con:
   - `modulos/__init__.py`, luego los cinco restantes
   - `demo/__init__.py`, luego `guion.py`
   - `demo/datos/vigencia/PRUEBA_1.pdf` — al crear el fichero con esa ruta
     completa se crean las dos carpetas de golpe; después sube los otros cinco PDF
   - lo mismo para `demo/datos/similitud/`, `demo/datos/contradicciones/` y
     `demo/datos/auditoria/`
   - `.streamlit/config.toml`

Es tedioso, pero sólo una vez. La clave es **crear la carpeta con
`Create new file` escribiendo la ruta completa**, y sólo entonces subir el resto
dentro.

---

## Comprobar que ha ido bien

Antes de tocar Streamlit, en el repositorio:

- La raíz tiene **ocho ficheros y cuatro carpetas**, ni uno más.
- Dentro de `nucleo/` hay **doce** ficheros, incluidos `asesor.py`,
  `historial.py` y `plantilla.py` (son nuevos: si faltan, la subida no llegó).
- Abre `ui.py` y busca `bloque_evolucion`. Tiene que aparecer.

Y en la app, cuando arranque: el lateral dice **núcleo v6**. Si dice v5, algo se
quedó atrás y la propia app te dirá qué.

---

## Streamlit Cloud

1. `New app` → elige el repositorio nuevo, rama `main`, fichero `app.py`.
2. En `Settings → Secrets`, vuelve a pegar:
   ```
   GEMINI_API_KEY = "..."
   ```
   Los secretos no viajan con el repositorio: son de la app, y la app es nueva.
3. `packages.txt` con `poppler-utils` es imprescindible. Sin él no hay
   `pdftotext` y la app no arranca.

El plan gratuito permite **una sola app privada**: borra la anterior antes de
desplegar ésta.


---

## Cuota del nivel gratuito

El plan gratuito de Gemini da **5 peticiones por minuto y por modelo**. Es poco, y
condiciona el diseño de todo lo que llama al modelo:

- **El panel de jueces cuesta 3 llamadas**, no una por juez y criterio. Cada juez
  vota todos los criterios de golpe. Los jueces siguen sin verse entre sí, que es
  la independencia que importa.
- **El sistema espera entre llamadas** en vez de fallar. Si el proveedor devuelve
  un 429, lee cuántos segundos pide esperar y reintenta. Las esperas se cuentan y
  se enseñan en el lateral, para que se vea que está frenando y no colgado.
- **Todo lo que se calcula queda en caché.** Volver a pedir el mismo panel sobre
  la misma salida no gasta nada.

Si aun así se agota, espera un minuto: lo ya calculado no se repite.

`GEMINI_MODELO` en Secrets permite cambiar de modelo sin redesplegar, por si otro
tuviera más cuota gratuita.
