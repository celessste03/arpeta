from django.contrib import admin
from .models import Operador, Marca, Modelo, Vehiculo, Asignacion, Vuelta

admin.site.register(Operador)
admin.site.register(Marca)
admin.site.register(Modelo)
admin.site.register(Vehiculo)
admin.site.register(Asignacion)
admin.site.register(Vuelta)