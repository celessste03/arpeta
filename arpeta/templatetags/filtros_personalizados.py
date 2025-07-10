from django import template
from ..models import Asignacion, Operador

register = template.Library()

@register.filter
def formato_decimal(valor):
    try:
        numero = float(valor)
        return f"{numero:,.2f}".replace('.', '_').replace(',', '.').replace('_', ',')
    except (ValueError, TypeError):
        return valor

@register.simple_tag
def asignaciones_por_vehiculo(vehiculo):
    if vehiculo:
        return Asignacion.objects.filter(vehiculo=vehiculo).count()
    return 0

@register.simple_tag
def asignaciones_por_operador(operador):
    """
    Retorna el número de asignaciones asociadas a un operador específico.
    """
    if operador:
        return Asignacion.objects.filter(operador=operador).count()
    return 0