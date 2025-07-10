from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.inicio_redirect, name='inicio_redirect'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('reset_password/', auth_views.PasswordResetView.as_view(template_name="password_reset/password_reset_form.html", email_template_name="password_reset/password_reset_email.html", html_email_template_name="password_reset/password_reset_email.html"), name='password_reset'),
    path('reset_password_done/', auth_views.PasswordResetDoneView.as_view(template_name="password_reset/password_reset_done.html"), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name="password_reset/password_reset_confirm.html"), name='password_reset_confirm'),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(template_name="password_reset/password_reset_complete.html"), name='password_reset_complete'),

    path('administracion', views.inicio_administracion, name='inicio_administracion'),
    path('administracion/operadores', views.operadores, name='operadores'),
    path('administracion/operadores/crear_operador', views.crear_operador, name='crear_operador'),
    path('administracion/operadores/editar_operador/<str:cedula>/', views.editar_operador, name='editar_operador'),
    path('administracion/operadores/borrar_operador/<str:cedula>/', views.borrar_operador, name='borrar_operador'),
    path('administracion/operadores/detalles/<str:cedula>/', views.detalles_operador, name='detalles_operador'),

    path('administracion/vehiculos', views.vehiculos, name='vehiculos'),
    path('administracion/vehiculos/crear_vehiculo', views.crear_vehiculo, name='crear_vehiculo'),
    path('administracion/vehiculos/editar_vehiculo/<str:placa>/', views.editar_vehiculo, name='editar_vehiculo'),
    path('administracion/vehiculos/borrar_vehiculo/<str:placa>/', views.borrar_vehiculo, name='borrar_vehiculo'),
    path('administracion/crear_modelo_marca/', views.crear_modelo_marca, name='crear_modelo_marca'),
    path('administracion/descargar_qr/<str:placa>/', views.descargar_qr, name='descargar_qr'),
    path('administracion/enviar_qr_correo/<str:placa>', views.enviar_qr_correo, name='enviar_qr_correo'),

    path('administracion/asignaciones', views.asignaciones, name='asignaciones'),
    path('administracion/asignaciones/crear_asignacion', views.crear_asignacion, name='crear_asignacion'),
    path('administracion/asignaciones/borrar_asignacion/<int:id>/', views.borrar_asignacion, name='borrar_asignacion'),
    path('administracion/asignaciones/cambiar_estado/<int:id>/', views.cambiar_estado, name='cambiar_estado'),
    path("administracion/registrar_vuelta/", views.registrar_vuelta, name="registrar_vuelta"),

    path('gerente/inicio_gerente.html', views.inicio_gerente, name='inicio_gerente'),
    path('gerente/base_gerente.html', views.base_gerente, name='base_gerente'),
    path('gerente/reportes_gerente.html', views.reportes_gerente, name='reportes_gerente'),
    path('gerente/lista_asignaciones.html', views.lista_asignaciones, name='lista_asignaciones'),
    path('gerente/asignaciones_gerente.html',views.dashboard_asignaciones, name='asignaciones_gerente'),
    path('gerente/vehiculos_gerente.html', views.VehiculosGerenteView.as_view(), name='vehiculos_gerente'),
    path('gerente/operadores', views.OperadoresGerenteView.as_view(), name='operadores_gerente'),  

  
    path('nomina/calcular_pago.html', views. calcular_pago, name='calcular_pago'),
    path('nomina/resultado_pago.html', views.PagoOperadorForm, name='resultado_pago'),
    path('nomina/base_nomina.html', views.base_nomina, name='base_nomina')
]