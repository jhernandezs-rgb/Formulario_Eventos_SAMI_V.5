"""Validacion de un dispositivo capturado en el formulario de monitoreo,
con el mismo criterio que `validate_and_clean_data()` de Analisis-Python.1:
HOST_NAME obligatorio, PERCENT_UP y PERCENT_DOWN numericos en 0-100, y su
suma no debe superar 105 (margen para UNREACHABLE/UNDETERMINED)."""

from monitoreo_schema import DispositivoPayload


def validate_dispositivo(payload: DispositivoPayload) -> list[str]:
    errors: list[str] = []

    if not payload.categoria or not payload.categoria.strip():
        errors.append("Categoria es obligatoria.")
    if not payload.host_name or not payload.host_name.strip():
        errors.append("HOST_NAME (dispositivo o URL) no puede estar vacio.")

    for etiqueta, valor in (
        ("PERCENT_TOTAL_TIME_UP", payload.percent_up),
        ("PERCENT_TOTAL_TIME_DOWN", payload.percent_down),
        ("PERCENT_TOTAL_TIME_UNREACHABLE", payload.percent_unreachable),
        ("PERCENT_TOTAL_TIME_UNDETERMINED", payload.percent_undetermined),
    ):
        if valor is None:
            errors.append(f"{etiqueta} es obligatorio.")
        elif not (0 <= valor <= 100):
            errors.append(f"{etiqueta} debe estar entre 0 y 100 (valor: {valor}).")

    if payload.percent_up is not None and payload.percent_down is not None:
        if payload.percent_up + payload.percent_down > 105:
            errors.append(
                "PERCENT_TOTAL_TIME_UP + PERCENT_TOTAL_TIME_DOWN supera 105%: "
                "revisa los porcentajes digitados."
            )

    if payload.percent_down and payload.percent_down > 0 and not payload.causa.strip():
        errors.append(
            "Hay tiempo de caida (PERCENT_TOTAL_TIME_DOWN > 0) pero no se "
            "indico la Causa."
        )

    return errors
