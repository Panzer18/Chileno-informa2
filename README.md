# Chilenos Informa2 (IWG400, Equipo 10 "Grupo y los Minions")

Sitio web desarrollado con Django que reúne, en un solo lugar, enlaces a información
hídrica y ambiental de **fuentes oficiales** (DGA, SMA, MMA, SIMBIO, PRAS y Ley Chile)
para las comunas de **Petorca** y **Quintero-Puchuncaví**. No genera información nueva.

## Requisitos

- Python 3 (versión usada en el desarrollo: ___ ; se comprueba con `python --version`)
- Django (se instala con `requirements.txt`)
- No necesita internet para ejecutarse, salvo para abrir los enlaces externos a las fuentes.

## Cómo ejecutarlo en local (Windows, PowerShell)

```powershell
git clone https://github.com/Panzer18/Chileno-informa2.git
cd Chileno-informa2
python -m venv entv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\entv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py cargar_datos
python manage.py runserver
```

En macOS o Linux, el entorno se activa con `source entv/bin/activate`.

Luego abrir <http://127.0.0.1:8000/> en el navegador.

`cargar_datos` crea las dos comunas, los enlaces de monitoreo y las fuentes necesarias para
probar la funcionalidad corazón. Se puede ejecutar más de una vez sin duplicar datos.

## Cómo probar la funcionalidad corazón

La funcionalidad corazón permite seleccionar una comuna y ver, en una sola vista, su
información de monitoreo hídrico y ambiental, con un aviso cuando no hay datos.

**Caso 1 (escenario principal):** en la portada, elegir **Quintero-Puchuncaví** y luego
**Monitoreo del sector**. Se muestran tarjetas de monitoreo hídrico (DGA) y ambiental
(SMA y PRAS), cada una con su enlace a la fuente oficial.

**Caso 2 (escenario alternativo):** en la portada, elegir **Petorca** y luego
**Monitoreo del sector**. Se muestra la tarjeta hídrica (DGA) y, en la sección ambiental,
el aviso "No hay información de monitoreo ambiental disponible para esta comuna".

## Pruebas automáticas

```powershell
python manage.py test
```

## Panel de administración (opcional)

Para cargar normas, noticias u otros monitoreos:

```powershell
python manage.py createsuperuser
python manage.py runserver
```

y entrar a <http://127.0.0.1:8000/admin/>.

## Estructura

| Carpeta | Contenido |
|---|---|
| `OWID/` | Configuración del proyecto (`settings.py`, `urls.py`) |
| `core/` | Portada, buscador, página de fuentes y modelo `Fuente` |
| `comunas/` | Modelos `Comuna` y `Monitoreo` (funcionalidad corazón) |
| `normativa/` | Modelo `Norma` y página de leyes |
| `noticias/` | Modelo `Noticia` y página de noticias |
| `templates/`, `static/` | Plantillas HTML y CSS propio |