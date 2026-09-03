# Formulario de Eventos S@MI

> Para la documentacion completa (arquitectura, reglas de negocio, estandar de
> nombres, alertamiento y supuestos abiertos), ver [DOCUMENTACION.md](DOCUMENTACION.md).

Un **Portal de Monitoreo** (`portal.py`, pagina principal) con acceso simple y un
menu de tarjetas hacia tres herramientas: dos sobre la Planilla Control de Eventos
S@MI, y una nueva e independiente para el monitoreo de disponibilidad tipo Nagios.
Todas con las mismas validaciones de calidad de datos que el panel de
disponibilidad `Analisis-Python.1-v3.0-BETA`: ningun evento incompleto o
cronologicamente inconsistente llega al calculo de SLA (meta: 98% de
disponibilidad o superior).

0. **Portal de Monitoreo** (`portal.py`): pantalla de entrada con una clave de
   acceso simple (`PORTAL_PASSWORD`, opcional — ver `.env.example`; **no** es un
   sistema de usuarios, ver `auth.py`) y tarjetas para entrar a cada herramienta.
1. **Formulario de captura** (`pages/1_Captura_de_Eventos.py`): para
   registrar eventos nuevos a medida que ocurren, con fecha/hora por
   selector (nunca texto libre), evitando de raiz errores de formato de
   hora.
2. **Revision del archivo mensual** (`pages/2_Revisar_archivo_mensual.py`):
   para el rol de revisor que descarga el archivo del mes ya diligenciado,
   detecta filas con problemas (campos vacios, Fin anterior a Inicio —
   sintoma tipico de una hora digitada en el formato equivocado), permite
   corregirlas, y separa la **disponibilidad total** (todas las causas
   cuentan) de la **disponibilidad ajustada** (excluyendo incidencias
   marcadas como "no controladas", por ejemplo fallas electricas o de un
   proveedor externo como Tigo/Une). Ambas se comparan contra la meta de
   SLA por separado — la clasificacion de que cuenta como "no controlado"
   siempre la decide el revisor, el sistema solo sugiere un punto de
   partida segun palabras clave en la Causa. Cada fila que inicia en fin de
   semana recibe ademas una nota automatica: esas horas cuentan completas,
   la nota es solo trazabilidad.
3. **Monitoreo de disponibilidad** (`pages/3_Monitoreo_Nagios.py`): formulario
   nuevo e independiente para el reporte tipo Nagios (HOST_NAME, % arriba,
   % abajo), con el estandar de nombres `avail_<mes>_<año>.xlsx`, reporte PDF
   de dispositivos caidos, y alertas manuales por correo o webhook de chat
   corporativo (Teams/Slack/Google Chat) cuando una categoria esta por debajo
   del SLA — ver `.env.example` para habilitarlas.

## Que resuelve

La Planilla S@MI original (`Planilla Control de Eventos S@MI - Julio 2026 1 (1).xlsx`)
tenia dos problemas que impedian construir un formulario sobre ella:

1. **No se podia abrir en modo escritura.** Una relacion de imagen rota
   (`Target="NULL"` en `xl/drawings/_rels/drawing1.xml.rels`) hacia que
   `openpyxl` fallara al cargar el archivo. `repair_source.py` corrige esa
   relacion (y de paso corrige la hoja "Data Center", que tenia el
   encabezado de una columna sobrescrito y una formula rota en la fila 1).
2. **Las formulas de "Horas sin servicio" de la hoja `Resumen` estan rotas**
   (`=+Telecomunicaciones!#REF!` en todas las plataformas) porque referencian
   una columna que ya no existe. Ese calculo no se repara automaticamente
   aqui (no hay forma de saber con certeza que columna se elimino); en su
   lugar, el formulario **recalcula la disponibilidad en Python**,
   directamente desde `Fecha/Hora Inicio Evento` y `Fecha/Hora Fin Evento` de
   cada hoja de plataforma, sin depender de esas formulas.

## Ejecutar

```powershell
py -m pip install -r requirements.txt
py main.py
```

Abre `http://localhost:8501`. Primero aparece el **Portal de Monitoreo**
(pantalla de acceso, si `PORTAL_PASSWORD` esta configurada, y despues el
menu de tarjetas). Desde ahi entras a cada herramienta; dentro de cada una
eliges la plataforma (hoja) y, opcionalmente, cargas una Planilla S@MI
distinta a la incluida (`sami_source_reparado.xlsx`).

## Como funciona

- **Listas desplegables** (Analista, Causa, Areas Involucradas) se leen de
  la hoja `Hoja1` de la propia planilla, con opcion "Otro (escribir)" para
  valores nuevos. El nombre del analista se muestra y se guarda **sin el
  turno** que trae la hoja original (`"Nombre / 06:00 - 14:00"` se limpia a
  `"Nombre"` con `clean_analista_name()` en `workbook_io.py`); de paso esto
  deduplica la lista, que antes repetia a cada persona una vez por turno.
- **Validacion antes de guardar:** campos obligatorios completos y
  `Fecha/Hora Fin Evento >= Fecha/Hora Inicio Evento`. Si algo falla, se
  bloquea el envio y se listan exactamente los campos a corregir (ver
  `validation.py`).
- **Al guardar**, el evento se escribe en la primera fila disponible de la
  hoja de esa plataforma, reutilizando las formulas de `Tiempo Total /
  Minutos / Horas` que ya trae cada fila (o creandolas, si hay que agregar
  una fila nueva).
- **SLA en vivo:** se recalculan las horas de caida acumuladas de la
  plataforma y, si la hoja `Resumen` tiene una fila de referencia para ella
  (numero de dispositivos y horas del mes), se muestra el porcentaje de
  disponibilidad contra la meta de SLA (98% o superior). La hoja **Data Center no tiene fila
  en `Resumen`** en el archivo de origen, asi que para esa plataforma solo
  se muestran las horas de caida, sin porcentaje.
- **Descargar Planilla S@MI actualizada** entrega una copia con los eventos
  capturados en la sesion. El archivo original en disco nunca se modifica
  automaticamente.

### Pagina "Revisar archivo mensual"

- Recorre la hoja de la plataforma elegida y marca cada fila con los
  problemas que encuentra: campos obligatorios vacios, `Fin` anterior a
  `Inicio`, o una duracion mayor a un mes (ambas suelen delatar una hora
  digitada en el formato equivocado).
- Sugiere automaticamente que filas son **"no controladas"** buscando
  palabras clave en la Causa (electrica, energia, Tigo, Une, proveedor,
  tercero, mantenimiento programado — ver `PALABRAS_NO_CONTROLADO` en
  `review.py`). La sugerencia es solo un punto de partida: la casilla se
  edita fila por fila en la tabla.
- La tabla (`st.data_editor`) permite corregir Dispositivo, Analista,
  Ticket, Causa, Areas, Solucion, Inicio y Fin directamente. El boton
  "Guardar correcciones en el libro" escribe esos cambios en el Excel; la
  clasificacion "no controlado" en cambio vive solo en la sesion de
  Streamlit (no se escribe como columna nueva en el archivo, para no
  alterar el formato oficial de la planilla).
- Muestra dos porcentajes de disponibilidad, ambos contra la misma meta de
  SLA: **total** (todas las horas de caida cuentan) y **ajustada**
  (excluyendo las filas marcadas como no controladas).

## Limitacion conocida: recalculo de formulas en Excel

Este entorno no tiene LibreOffice instalado, asi que las formulas nuevas o
modificadas no traen un valor en cache al descargar el archivo. Esto no es
un problema al abrir el archivo en Microsoft Excel real: Excel recalcula
automaticamente al abrir (son formulas simples de resta/multiplicacion/
division, sin funciones que dependan de una version reciente de Excel). Si
se abre con una herramienta que solo lee valores en cache (por ejemplo
`pandas.read_excel` sin pasar por Excel primero), esas celdas apareceran
vacias hasta que el archivo se abra y guarde una vez en Excel.

## Pruebas

```powershell
py -m pip install -r requirements.txt pytest
py -m pytest qa -v
```

`qa/test_validacion.py` cubre las reglas de `validate_event()`.
`qa/test_workbook_io.py` cubre lectura de listas, linea base de SLA por
plataforma, escritura de eventos (incluida la variante con columnas TIGO) y
el calculo de disponibilidad — incluyendo una prueba de regresion para el
error `ValueError: I/O operation on closed file` que producia `wb.save()`
al llamarse mas de una vez sobre el mismo libro (ver seccion siguiente).

## Nota tecnica: por que se descartan las imagenes al cargar

`openpyxl` consume el flujo de datos de una imagen incrustada la primera
vez que se guarda el libro. Streamlit vuelve a ejecutar todo el script en
cada interaccion del usuario, y el boton de descarga llama a `wb.save()` en
cada una de esas ejecuciones — la segunda llamada sobre el mismo objeto
revienta con `ValueError: I/O operation on closed file` al intentar
reincrustar la imagen decorativa de la hoja `Resumen`. `load_workbook_for_write()`
en `workbook_io.py` descarta esas imagenes al cargar por eso: el formulario
prioriza poder guardarse de forma repetida y confiable sobre conservar un
logo decorativo.
