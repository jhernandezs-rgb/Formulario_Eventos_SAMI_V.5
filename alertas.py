"""Alertamiento cuando la disponibilidad de una plataforma/dispositivo cae
por debajo de la meta de SLA. Responde a "validar si se puede hacer un
alertamiento": si es viable, y aqui esta la implementacion.

Diseño deliberado:
- Esta herramienta NUNCA envia nada por si sola. `evaluar_alertas()` solo
  calcula que mensajes corresponderia enviar; `enviar_correo()` y
  `enviar_webhook()` solo se ejecutan cuando el usuario hace clic en un
  boton dentro de la app (ver pages/2_Monitoreo_Nagios.py). Enviar
  correos o mensajes de chat de forma automatica y desatendida requeriria
  guardar credenciales SMTP y una URL de webhook como configuracion
  permanente; eso queda fuera del alcance de este cambio hasta que se
  confirme explicitamente.
- Las credenciales SMTP y la URL del webhook NUNCA se piden por el chat de
  Claude ni se hardcodean aqui: se leen de variables de entorno (ver
  `.env.example`). Si faltan, las funciones de envio fallan con un mensaje
  claro en vez de intentar adivinar valores.
- El webhook de Teams, Slack y Google Chat aceptan el mismo formato basico
  `{"text": "..."}`, por eso `enviar_webhook()` sirve para cualquiera de
  los tres ("chat corporativo" generico): solo cambia la URL.
"""

import os
import smtplib
from dataclasses import dataclass
from email.mime.text import MIMEText

import requests


@dataclass
class AlertaSLA:
    plataforma: str
    disponibilidad: float
    meta: float
    horas_caida: float

    @property
    def mensaje(self) -> str:
        return (
            f"⚠️ SLA en riesgo — {self.plataforma}: disponibilidad {self.disponibilidad:.2f}% "
            f"(meta {self.meta:.0f}%), {self.horas_caida:.1f} h de caida acumuladas este mes."
        )


def evaluar_alertas(resultados_por_plataforma: dict, meta: float) -> list[AlertaSLA]:
    """`resultados_por_plataforma` es {plataforma: {'disponibilidad': x,
    'horas_caida': y}}. Retorna una alerta por cada plataforma por debajo
    de la meta."""
    alertas = []
    for plataforma, resultado in resultados_por_plataforma.items():
        disponibilidad = resultado.get("disponibilidad")
        if disponibilidad is None:
            continue
        if disponibilidad < meta:
            alertas.append(
                AlertaSLA(
                    plataforma=plataforma,
                    disponibilidad=disponibilidad,
                    meta=meta,
                    horas_caida=resultado.get("horas_caida", 0.0),
                )
            )
    return alertas


class ConfiguracionFaltante(RuntimeError):
    pass


def _env(nombre: str) -> str:
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        raise ConfiguracionFaltante(
            f"Falta la variable de entorno {nombre}. Ver .env.example."
        )
    return valor


def enviar_correo(destinatarios: list[str], asunto: str, cuerpo: str) -> None:
    """Envia un correo via SMTP. Requiere SMTP_HOST, SMTP_PORT, SMTP_USER,
    SMTP_PASSWORD, SMTP_FROM en variables de entorno."""
    host = _env("SMTP_HOST")
    port = int(_env("SMTP_PORT"))
    usuario = _env("SMTP_USER")
    password = _env("SMTP_PASSWORD")
    remitente = _env("SMTP_FROM")

    mensaje = MIMEText(cuerpo, "plain", "utf-8")
    mensaje["Subject"] = asunto
    mensaje["From"] = remitente
    mensaje["To"] = ", ".join(destinatarios)

    with smtplib.SMTP(host, port, timeout=15) as servidor:
        servidor.starttls()
        servidor.login(usuario, password)
        servidor.sendmail(remitente, destinatarios, mensaje.as_string())


def enviar_webhook(mensaje: str, webhook_url: str | None = None) -> None:
    """Envia un mensaje a un webhook entrante de Teams, Slack o Google Chat
    (los tres aceptan {"text": mensaje}). Si no se pasa `webhook_url`, se
    lee de la variable de entorno ALERTAS_WEBHOOK_URL."""
    url = webhook_url or _env("ALERTAS_WEBHOOK_URL")
    respuesta = requests.post(url, json={"text": mensaje}, timeout=15)
    respuesta.raise_for_status()


def config_correo_disponible() -> bool:
    return all(
        os.environ.get(v, "").strip()
        for v in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM")
    )


def config_webhook_disponible() -> bool:
    return bool(os.environ.get("ALERTAS_WEBHOOK_URL", "").strip())
