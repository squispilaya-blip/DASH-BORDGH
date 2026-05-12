# Dashboard de Vacunación

Sistema de seguimiento del esquema de vacunación infantil según la **NTS N° 196-MINSA/DGIESP-2022** (RM 884-2022-MINSA).

Permite cargar el padrón Excel exportado del sistema de salud, visualizar el estado vacunal de cada niño y exportar reportes con color por estado.

---

## Despliegue en Streamlit Community Cloud

### 1. Subir el código a GitHub

Crea un repositorio **privado** en GitHub y sube este proyecto.

### 2. Crear la app en Streamlit Cloud

1. Ingresa a [share.streamlit.io](https://share.streamlit.io)
2. Haz clic en **"New app"**
3. Conecta tu repositorio de GitHub
4. Archivo principal: `app.py`
5. Haz clic en **"Advanced settings"** → **"Secrets"**

### 3. Configurar los secrets

En el campo de secrets pega lo siguiente con tus credenciales reales:

```toml
[auth]
username = "tu_usuario"
password = "tu_contraseña"
```

> El archivo `.streamlit/secrets.toml` **no se sube al repositorio** (está en `.gitignore`).
> Los secrets se configuran únicamente desde el dashboard de Streamlit Cloud.

### 4. Desplegar

Haz clic en **"Deploy"**. La app estará lista en unos minutos.

---

## Uso

1. Inicia sesión con las credenciales configuradas.
2. Carga el padrón Excel (hoja `Consulta2`).
3. Usa los filtros del sidebar para explorar los datos.
4. Descarga el reporte Excel con el botón **"Generar reporte Excel"**.

---

## Dependencias

- [Streamlit](https://streamlit.io)
- [Pandas](https://pandas.pydata.org)
- [OpenPyXL](https://openpyxl.readthedocs.io)
- [python-dateutil](https://dateutil.readthedocs.io)
