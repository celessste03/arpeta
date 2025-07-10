import os
import json
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import EmailMessage, send_mail
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from .models import Operador, Vehiculo, Asignacion, Marca, Modelo, Vuelta
from .forms import OperadorForm, VehiculoForm, AsignacionForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from cryptography.fernet import Fernet, InvalidToken
from django.core.exceptions import ImproperlyConfigured
from datetime import timedelta
from django.views.decorators.http import require_POST


# Función para verificar si el usuario pertenece al grupo de administración
def is_administracion(user):
    return user.groups.filter(name='Administracion').exists()


# Función para verificar si el usuario pertenece al grupo de gerente
def is_gerente(user):
    return user.groups.filter(name='Gerente').exists()


# Función para verificar si el usuario pertenece al grupo de nomina
def is_nomina(user):
    return user.groups.filter(name='Nomina').exists()


# Vista para redirigir a la página de inicio según el grupo del usuario
def inicio_redirect(request):
    if request.user.is_authenticated:
        if is_administracion(request.user):
            return redirect('inicio_administracion')
        elif is_gerente(request.user):
            return redirect('inicio_gerente')
        elif is_nomina(request.user):
            return redirect('calcular_pago')
        else:
            return HttpResponse("No tienes permisos para acceder a esta sección. Por favor, contacta al administrador.", status=403)
    else:
        return redirect('login')


# Vista para el inicio de sesión
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                if user.groups.filter(name='Administracion').exists():
                    return redirect('inicio_administracion')
                elif user.groups.filter(name='Gerente').exists():
                    return redirect('inicio_gerente')
                elif user.groups.filter(name='Nomina').exists():
                    return redirect('calcular_pago')
                else:
                    return redirect('inicio_redirect')
            else:
                messages.error(request, "Correo o contraseña incorrectos.")
        else:
            messages.error(request, "Correo o contraseña incorrectos.")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


# Vista para el cierre de sesión
def logout_view(request):
    logout(request)
    return redirect('login')


# Vista para la página de inicio de administración
@login_required
@user_passes_test(is_administracion)
def inicio_administracion(request):
    return render(request, 'administracion/inicio_administracion.html')


# Vista para listar operadores
@login_required
@user_passes_test(is_administracion)
def operadores(request):
    operadores = Operador.objects.all().order_by('nombre')
    paginator = Paginator(operadores, 2)
    page_number = request.GET.get('page')
    operadores = paginator.get_page(page_number)
    return render(request, 'administracion/operadores/index_operador.html', {'operadores': operadores})


# Vista para crear un operador
@login_required
@user_passes_test(is_administracion)
def crear_operador(request):
    if request.method == "POST":
        formulario = OperadorForm(request.POST, request.FILES)
        if formulario.is_valid():
            formulario.save()
            return redirect('operadores')
    else:
        formulario = OperadorForm()
    return render(request, 'administracion/operadores/crear_operador.html', {'formulario': formulario})


# Vista para editar un operador
@login_required
@user_passes_test(is_administracion)
def editar_operador(request, cedula):
    operador = get_object_or_404(Operador, cedula=cedula)
    if request.method == "POST":
        formulario = OperadorForm(request.POST, request.FILES, instance=operador)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, f"Operador {operador.nombre} {operador.apellido} actualizado correctamente.")
            return redirect('operadores')
    else:
        formulario = OperadorForm(instance=operador)
    return render(request, 'administracion/operadores/editar_operador.html', {
        'formulario': formulario,
        'operador': operador
    })


# Vista para borrar un operador
@login_required
@user_passes_test(is_administracion)
def borrar_operador(request, cedula):
    operador = get_object_or_404(Operador, cedula=cedula)
    if Asignacion.objects.filter(operador=operador).exists():
        messages.error(request, f"El operador {operador.nombre} {operador.apellido} (Cédula: {operador.cedula}) no puede ser eliminado porque tiene asignaciones registradas.")
        return redirect('operadores')
    try:
        operador.delete()
        messages.success(request, f"Operador {operador.nombre} {operador.apellido} eliminado correctamente.")
    except Exception as e:
        messages.error(request, f"Error al eliminar el operador {operador.nombre} {operador.apellido}: {str(e)}")
    return redirect('operadores')


# Vista para listar vehículos
@login_required
@user_passes_test(is_administracion)
def vehiculos(request):
    vehiculos = Vehiculo.objects.all().order_by('modelo')
    paginator = Paginator(vehiculos, 2)
    page_number = request.GET.get('page')
    vehiculos = paginator.get_page(page_number)
    return render(request, 'administracion/vehiculos/index_vehiculo.html', {'vehiculos': vehiculos})


# Vista para crear un vehículo
@login_required
@user_passes_test(is_administracion)
def crear_vehiculo(request):
    if request.method == "POST":
        formulario = VehiculoForm(request.POST, request.FILES)
        if formulario.is_valid():
            formulario.save()
            return redirect('vehiculos')
    else:
        formulario = VehiculoForm()
    return render(request, 'administracion/vehiculos/crear_vehiculo.html', {'formulario': formulario})


# Vista para crear una marca y modelo
@login_required
@user_passes_test(is_administracion)
@require_POST
def crear_modelo_marca(request):
    try:
        data = json.loads(request.body)
        marca_nombre = data.get('marca', '').strip()
        modelo_nombre = data.get('modelo', '').strip()
        if not marca_nombre or not modelo_nombre:
            return JsonResponse({'success': False, 'errors': 'La marca y el modelo no pueden estar vacíos.'}, status=400)
        marca_obj, created = Marca.objects.get_or_create(
            nombre__iexact=marca_nombre, 
            defaults={'nombre': marca_nombre.capitalize()}
        )
        if Modelo.objects.filter(marca=marca_obj, nombre__iexact=modelo_nombre).exists():
            return JsonResponse({'success': False, 'errors': 'Este modelo ya existe para esta marca.'}, status=400)
        nuevo_modelo = Modelo.objects.create(marca=marca_obj, nombre=modelo_nombre.capitalize())
        return JsonResponse({
            'success': True,
            'id': nuevo_modelo.id,
            'marca': marca_obj.nombre,
            'modelo': nuevo_modelo.nombre
        })
    except Exception as e:
        return JsonResponse({'success': False, 'errors': str(e)}, status=500)


# Vista para editar un vehículo
@login_required
@user_passes_test(is_administracion)
def editar_vehiculo(request, placa):
    vehiculo = get_object_or_404(Vehiculo, placa=placa)
    if Asignacion.objects.filter(vehiculo=vehiculo).exists():
        messages.error(request, f"El vehículo con placa {vehiculo.placa} no puede ser editado porque tiene asignaciones registradas.")
        return redirect('vehiculos')
    if request.method == 'POST':
        formulario = VehiculoForm(request.POST, request.FILES, instance=vehiculo)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, f"Vehículo con placa {vehiculo.placa} actualizado correctamente.")
            return redirect('vehiculos')
    else:
        formulario = VehiculoForm(instance=vehiculo)
    return render(request, 'administracion/vehiculos/editar_vehiculo.html', {'formulario': formulario, 'vehiculo': vehiculo})


# Vista para borrar un vehículo
@login_required
@user_passes_test(is_administracion)
def borrar_vehiculo(request, placa):
    vehiculo = get_object_or_404(Vehiculo, placa=placa)
    if Asignacion.objects.filter(vehiculo=vehiculo).exists():
        messages.error(request, f"El vehículo con placa {vehiculo.placa} no puede ser eliminado porque tiene asignaciones registradas.")
        return redirect('vehiculos')
    try:
        vehiculo.delete()
        messages.success(request, f"Vehículo con placa {vehiculo.placa} eliminado correctamente.")
    except Exception as e:
        messages.error(request, f"Error al eliminar el vehículo {vehiculo.placa}: {str(e)}")
    return redirect('vehiculos')


# Vista para descargar el código QR de un vehículo
@login_required
@user_passes_test(is_administracion)
def descargar_qr(request, placa):
    try:
        placa_vehiculo = Vehiculo.objects.get(placa=placa)
        qr_path = os.path.join(settings.MEDIA_ROOT, placa_vehiculo.codigo_qr.name)
        return FileResponse(open(qr_path, 'rb'), as_attachment=True, filename=os.path.basename(qr_path))
    except (Vehiculo.DoesNotExist, FileNotFoundError):
        raise Http404("El QR no existe.")


# Vista para listar asignaciones
@login_required
@user_passes_test(is_administracion)
def asignaciones(request):
    asignaciones = Asignacion.objects.all().order_by('-fecha_asignacion', '-id')
    paginator = Paginator(asignaciones, 2)
    page_number = request.GET.get('page')
    asignaciones = paginator.get_page(page_number)
    return render(request, 'administracion/asignaciones/index_asignacion.html', {'asignaciones': asignaciones})


# Vista para crear una asignación
@login_required
@user_passes_test(is_administracion)
def crear_asignacion(request):
    fecha_actual = timezone.localtime(timezone.now()).date()
    if request.method == 'POST':
        formulario = AsignacionForm(request.POST)
        if formulario.is_valid():
            operador_seleccionado = formulario.cleaned_data['operador']
            vehiculo_seleccionado = formulario.cleaned_data['vehiculo']
            otras_asignaciones_operador_hoy = Asignacion.objects.filter(
                operador=operador_seleccionado, fecha_asignacion=fecha_actual
            ).exclude(vehiculo=vehiculo_seleccionado)
            if any(a.estado_actual for a in otras_asignaciones_operador_hoy):
                messages.error(request, f"El operador {operador_seleccionado} ya tiene una asignación activa con otro vehículo para hoy.")
                return render(request, 'administracion/asignaciones/crear_asignacion.html', {
                    'formulario': formulario, 'operadores': Operador.objects.all(), 'vehiculos': Vehiculo.objects.all()
                })
            otras_asignaciones_vehiculo_hoy = Asignacion.objects.filter(
                vehiculo=vehiculo_seleccionado, fecha_asignacion=fecha_actual
            ).exclude(operador=operador_seleccionado)
            if any(a.estado_actual for a in otras_asignaciones_vehiculo_hoy):
                messages.error(request, f"El vehículo {vehiculo_seleccionado} ya tiene una asignación activa con otro operador para hoy.")
                return render(request, 'administracion/asignaciones/crear_asignacion.html', {
                    'formulario': formulario, 'operadores': Operador.objects.all(), 'vehiculos': Vehiculo.objects.all()
                })
            asignacion_existente, created = Asignacion.objects.get_or_create(
                operador=operador_seleccionado,
                vehiculo=vehiculo_seleccionado,
                fecha_asignacion=fecha_actual,
                defaults={'estado': True}
            )
            if created:
                messages.success(request, "Nueva asignación creada exitosamente para hoy.")
            else:
                if asignacion_existente.estado:
                    messages.warning(request, f"La asignación para {operador_seleccionado} y {vehiculo_seleccionado} ya existe y está activa para hoy.")
                else:
                    asignacion_existente.estado = True
                    asignacion_existente.vueltas.all().delete()
                    asignacion_existente.save()
                    messages.success(request, f"La asignación existente para {operador_seleccionado} y {vehiculo_seleccionado} ha sido reactivada para hoy.")
            return redirect('asignaciones')
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        formulario = AsignacionForm()
    return render(request, 'administracion/asignaciones/crear_asignacion.html', {
        'formulario': formulario,
        'operadores': Operador.objects.all(),
        'vehiculos': Vehiculo.objects.all()
    })


# Vista para borrar una asignación
@login_required
@user_passes_test(is_administracion)
def borrar_asignacion(request, id):
    asignacion = get_object_or_404(Asignacion, id=id)
    fecha_hoy = timezone.localtime(timezone.now()).date()
    if asignacion.total_vueltas > 0:
        messages.error(request, f"La asignación ID {asignacion.id} no puede ser eliminada porque tiene {asignacion.total_vueltas} vuelta(s) registrada(s).")
        return redirect('asignaciones')
    if asignacion.fecha_asignacion < fecha_hoy:
        messages.error(request, f"La asignación ID {asignacion.id} no puede ser eliminada porque su fecha ({asignacion.fecha_formateada}) ya pasó. Las asignaciones de días pasados no son eliminables.")
        return redirect('asignaciones')
    try:
        asignacion.delete()
        messages.success(request, f"Asignación ID {asignacion.id} eliminada correctamente.")
    except Exception as e:
        messages.error(request, f"Error al eliminar la asignación ID {asignacion.id}: {str(e)}")
    return redirect('asignaciones')


# Vista para cambiar el estado de una asignación
@login_required
@user_passes_test(is_administracion)
@require_POST
def cambiar_estado(request, id):
    asignacion = get_object_or_404(Asignacion, id=id)
    fecha_hoy = timezone.localtime(timezone.now()).date()
    if asignacion.fecha_asignacion != fecha_hoy:
        return JsonResponse({'status': 'error', 'message': 'Solo se puede cambiar el estado de asignaciones del día de hoy.'}, status=400)
    try:
        if asignacion.estado:
            data = json.loads(request.body)
            razon = data.get('razon', '').strip()
            if not razon:
                return JsonResponse({'status': 'error', 'message': 'Debe proporcionar una razón para desactivar la asignación.'}, status=400)
            asignacion.estado = False
            asignacion.razon_inactividad = razon
            asignacion.save()
            return JsonResponse({'status': 'success', 'message': f'Asignación para {asignacion.operador} - {asignacion.vehiculo} ha sido desactivada.'})
        else:
            asignacion.estado = True
            asignacion.razon_inactividad = None
            asignacion.save()
            return JsonResponse({'status': 'success', 'message': f'Asignación para {asignacion.operador} - {asignacion.vehiculo} ha sido activada.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# Vista para registrar una vuelta
@require_POST
def registrar_vuelta(request):
    try:
        data = json.loads(request.body)
        placa_escaneada_encriptada = data.get("placa")
        if not placa_escaneada_encriptada:
            return JsonResponse({"error": "No se proporcionó la placa desde el QR."}, status=400)
        try:
            key = settings.FERNET_KEY
            f = Fernet(key)
            placa_encriptada_bytes = placa_escaneada_encriptada.encode('utf-8')
            placa_original_bytes = f.decrypt(placa_encriptada_bytes)
            placa_original_str = placa_original_bytes.decode('utf-8')
        except AttributeError:
            return JsonResponse({"error": "Error de configuración interna del servidor: FERNET_KEY no definida."}, status=500)
        except InvalidToken:
            return JsonResponse({"error": "Código QR inválido o no reconocido."}, status=400)
        except Exception:
            return JsonResponse({"error": "Error al procesar la información del código QR."}, status=400)
        try:
            vehiculo = Vehiculo.objects.get(placa=placa_original_str)
        except Vehiculo.DoesNotExist:
            return JsonResponse({"error": f"Vehículo con placa '{placa_original_str}' no encontrado."}, status=404)
        fecha_hoy = timezone.localtime(timezone.now()).date()
        try:
            asignacion = Asignacion.objects.get(
                vehiculo=vehiculo,
                fecha_asignacion=fecha_hoy,
                estado=True
            )
        except Asignacion.DoesNotExist:
            return JsonResponse({
                "error": f"No se encontró una asignación activa para el vehículo {placa_original_str} en la fecha de hoy ({fecha_hoy.strftime('%d-%m-%Y')})."
            }, status=404)
        except Asignacion.MultipleObjectsReturned:
            return JsonResponse({
                "error": f"Múltiples asignaciones activas encontradas para {placa_original_str} hoy. Por favor, contacte al administrador."
            }, status=500)
        ultima_vuelta_timestamp = asignacion.ultima_vuelta_registrada_en
        if ultima_vuelta_timestamp:
            ahora = timezone.now()
            tiempo_desde_ultima_vuelta = ahora - ultima_vuelta_timestamp
            tiempo_minimo_entre_vueltas = timedelta(minutes=10)
            if tiempo_desde_ultima_vuelta < tiempo_minimo_entre_vueltas:
                segundos_restantes_total = int((tiempo_minimo_entre_vueltas - tiempo_desde_ultima_vuelta).total_seconds())
                minutos_restantes = segundos_restantes_total // 60
                segundos_restantes = segundos_restantes_total % 60
                return JsonResponse({
                    "error": (f"Este vehículo ya registró una vuelta hace poco. "
                              f"Intente de nuevo en {minutos_restantes} min y {segundos_restantes} seg.")
                }, status=429)
        Vuelta.objects.create(asignacion=asignacion)
        return JsonResponse({
            "message": "Vuelta registrada con éxito.",
            "total_vueltas": asignacion.total_vueltas,
            "total_material_acumulado": float(asignacion.total_material)
        }, status=200)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Solicitud JSON mal formada."}, status=400)
    except Exception as e:
        print(f"Error inesperado en registrar_vuelta: {e}")
        return JsonResponse({"error": f"Ocurrió un error inesperado en el servidor."}, status=500)


# Vista para enviar el código QR de un vehículo por correo electrónico
@login_required
@user_passes_test(is_administracion)
def enviar_qr_correo(request, placa):
    vehiculo = get_object_or_404(Vehiculo, placa=placa)
    if request.method == 'POST':
        correo_destino = request.POST.get('correo')
        if not correo_destino:
            messages.error(request, 'No se proporcionó una dirección de correo válida.')
            return JsonResponse({'message': 'No se proporcionó una dirección de correo válida.'}, status=400)
        nombre_completo_operador = "Operador"
        try:
            operador = Operador.objects.get(correo__iexact=correo_destino)
            nombre_completo_operador = f"{operador.nombre} {operador.apellido}"
        except Operador.DoesNotExist:
            pass
        if vehiculo.codigo_qr and vehiculo.codigo_qr.file:
            subject = f"Código QR del vehículo {vehiculo.placa} - ARPETA"
            html_content = render_to_string('administracion/correo_qr.html', {
                'vehiculo': vehiculo,
                'nombre_operador': nombre_completo_operador
            })
            email = EmailMessage(
                subject,
                html_content,
                settings.DEFAULT_FROM_EMAIL,
                [correo_destino],
            )
            email.content_subtype = "html"
            qr_file_path = vehiculo.codigo_qr.path 
            try:
                email.attach_file(qr_file_path, mimetype='image/png')
                email.send(fail_silently=False)
                messages.success(request, '¡El código QR se envió por correo exitosamente!')
                return JsonResponse({'message': 'Correo enviado exitosamente!'})
            except FileNotFoundError:
                messages.error(request, 'Error: El archivo QR no se encontró en el servidor.')
                return JsonResponse({'message': 'Error: El archivo QR no se encontró en el servidor.'}, status=500)
            except Exception as e:
                messages.error(request, f'Error al enviar el correo: {e}')
                print(f"Error al enviar correo para {vehiculo.placa} a {correo_destino}: {e}")
                return JsonResponse({'message': f'Error al enviar el correo: {e}'}, status=500)
        else:
            messages.error(request, 'El vehículo no tiene un código QR asociado.')
            return JsonResponse({'message': 'El vehículo no tiene código QR.'}, status=400)
    else:
        messages.warning(request, 'Acceso no permitido.')
        return JsonResponse({'message': 'Método no permitido.'}, status=405)


# --------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------

# Vista para la página de inicio de gerente
@user_passes_test(is_gerente)
@login_required
def inicio_gerente(request):
    return render(request, 'gerente/inicio_gerente.html')

# Vista para la página de pagos del gerente
@user_passes_test(is_gerente)
def pagos_gerente(request):
    return render(request, 'gerente/pagos_gerente.html')

# Vista para la página de reportes del gerente
# views.py (nueva vista para el reporte)





#---------------------------------------------Gerente---------------------------------------------------------------------------
@user_passes_test(is_gerente)
def base_gerente(request):
    return render(request, 'gerente/base_gerente.html')

@user_passes_test(is_gerente)
def lista_asignaciones (request):
    return render(request, 'gerente/lista_asignaciones.html')


#------------------------------------------------------Operadores Gerente-----------------------------------------------------------------
from django.shortcuts import render
from django.views import View
from .models import Operador, Asignacion, Vehiculo
from django.db.models import Count, Q
import plotly.express as px
import pandas as pd
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.views import View
from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
import pandas as pd
import plotly.express as px
from django.db.models import Count
from .models import Operador, Asignacion  # Ajusta el import según tu estructura

class OperadoresGerenteView(View):
    template_name = 'gerente/operadores_gerente.html'

    def get(self, request):
        # Obtenemos todos los operadores para la tabla (sin orden por fecha)
        operadores = Operador.objects.all()

        # Estadísticas básicas
        total_operadores = operadores.count()
        operadores_activos = operadores.filter(activo=True).count()
        operadores_inactivos = total_operadores - operadores_activos

        # Operadores con asignaciones activas
        asignaciones_activas = Asignacion.objects.filter(estado=True).select_related('operador', 'vehiculo')

        # Gráfico de Estado de operadores
        estado_data = {
            'Estado': ['Activos', 'Inactivos'],
            'Cantidad': [operadores_activos, operadores_inactivos]
        }
        fig_estado = px.pie(
            estado_data,
            values='Cantidad',
            names='Estado',
            title='Distribución de Operadores por Estado',
            color_discrete_sequence=['#4CAF50', '#F44336']
        )
        fig_estado.update_traces(
            textposition='inside',
            textinfo='percent+label',
            marker=dict(line=dict(color='#FFFFFF', width=1))
        )
        grafico_estado = fig_estado.to_html(full_html=False)

        # Gráfico de Tipo de operadores
        operadores_independientes = operadores.filter(independiente=True).count()
        operadores_no_independientes = total_operadores - operadores_independientes

        tipo_data = {
            'Tipo': ['Independientes', 'No Independientes'],
            'Cantidad': [operadores_independientes, operadores_no_independientes]
        }
        fig_tipo = px.bar(
            tipo_data,
            x='Tipo',
            y='Cantidad',
            title='Distribución por Tipo de Operador',
            color='Tipo',
            color_discrete_sequence=['#2196F3', '#9C27B0']
        )
        fig_tipo.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_title=None,
            yaxis_title='Cantidad'
        )
        grafico_tipo = fig_tipo.to_html(full_html=False)

        # Gráfico de Vehículos más asignados (si hay)
        vehiculos_populares = Asignacion.objects.values(
            'vehiculo__placa', 'vehiculo__modelo__marca__nombre', 'vehiculo__modelo__nombre'
        ).annotate(
            total_asignaciones=Count('id')
        ).order_by('-total_asignaciones')[:5]

        grafico_vehiculos = None
        if vehiculos_populares:
            df_vehiculos = pd.DataFrame(list(vehiculos_populares))
            df_vehiculos['vehiculo'] = df_vehiculos.apply(
                lambda x: f"{x['vehiculo__placa']} ({x['vehiculo__modelo__marca__nombre']} {x['vehiculo__modelo__nombre']})",
                axis=1
            )
            fig_vehiculos = px.bar(
                df_vehiculos,
                x='vehiculo',
                y='total_asignaciones',
                title='Vehículos más asignados',
                labels={'total_asignaciones': 'N° de Asignaciones', 'vehiculo': 'Vehículo'},
                color_discrete_sequence=['#607D8B']
            )
            fig_vehiculos.update_layout(
                xaxis_title=None,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            grafico_vehiculos = fig_vehiculos.to_html(full_html=False)

        context = {
            'operadores': operadores,
            'total_operadores': total_operadores,
            'operadores_activos': operadores_activos,
            'operadores_inactivos': operadores_inactivos,
            'operadores_independientes': operadores_independientes,
            'operadores_no_independientes': operadores_no_independientes,
            'asignaciones_activas': asignaciones_activas,
            'grafico_estado': grafico_estado,
            'grafico_tipo': grafico_tipo,
            'grafico_vehiculos': grafico_vehiculos,
        }

        if 'pdf' in request.GET:
            return self.generate_pdf(context)

        return render(request, self.template_name, context)

    def generate_pdf(self, context):
        template = get_template('gerente/operadores_gerente_pdf.html')
        html = template.render(context)

        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)

        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="reporte_operadores.pdf"'
            return response

        return HttpResponse('Error al generar el PDF', status=400)
    
    
#----------------------------------------------------Vehiculos Gerente-------------------------------------------------------------    

from django.views import View
from django.db.models import Sum, Count, Q
from django.shortcuts import render
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from django.db.models.functions import TruncMonth
from django.db.models import Max 
from django.db.models import DateTimeField
from django.db.models.functions import Extract
from .models import Vehiculo, Asignacion, Vuelta  # Asegúrate de importar tus modelos

class VehiculosGerenteView(View):
    template_name = 'gerente/vehiculos_gerente.html'
    paginate_by = 10

    def get(self, request):
        # Filtros y búsqueda
        search_query = request.GET.get('search', '')
        estado_filter = request.GET.get('estado', None)

        # Datos básicos
        vehiculos_qs = Vehiculo.objects.all().select_related('modelo', 'modelo__marca')
        total_vehiculos = vehiculos_qs.count()
        vehiculos_activos = vehiculos_qs.filter(activo=True).count()
        vehiculos_inactivos = total_vehiculos - vehiculos_activos
        porcentaje_disponibilidad = round((vehiculos_activos / total_vehiculos * 100) if total_vehiculos > 0 else 0)

        # Gráfico circular de Estado de Vehículos (Pie Chart)
        estado_flota_labels = ['Activos', 'Inactivos']
        estado_flota_values = [vehiculos_activos, vehiculos_inactivos]
        estado_flota_colors = ['#10B981', '#EF4444']
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=estado_flota_labels,
            values=estado_flota_values,
            hole=0.4,
            marker_colors=estado_flota_colors,
            textinfo='percent',
            hoverinfo='label+percent+value',
            textfont_size=14
        )])
        
        fig_pie.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False
        )
        
        grafico_estado_pie = fig_pie.to_html(full_html=False, config={'displayModeBar': False})
        
        # Datos para la leyenda
        estado_flota_legend = [
            {'label': 'Activos', 'value': porcentaje_disponibilidad, 'color': '#10B981'},
            {'label': 'Inactivos', 'value': 100 - porcentaje_disponibilidad, 'color': '#EF4444'}
        ]
        
        

        # Gráfico de barras para vueltas diarias
        horas, vueltas_por_hora = self.get_vueltas_por_hora()
        
        fig_bar_daily = px.bar(
            x=horas,
            y=vueltas_por_hora,
            labels={'x': 'Hora del día', 'y': 'Número de vueltas'},
            color_discrete_sequence=['#3B82F6']
        )
        
        fig_bar_daily.update_layout(
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis_title=None,
            yaxis_title=None,
            hovermode='x unified'
        )
        
        grafico_vueltas_diarias_bar = fig_bar_daily.to_html(full_html=False, config={'displayModeBar': False})

        # Gráfico de barras para vueltas mensuales
        meses, vueltas_mensuales = self.get_vueltas_ultimo_anio()
        
        fig_bar_monthly = px.bar(
            x=meses,
            y=vueltas_mensuales,
            labels={'x': 'Mes', 'y': 'Número de vueltas'},
            color_discrete_sequence=['#A78BFA']
        )
        
        fig_bar_monthly.update_layout(
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis_title=None,
            yaxis_title=None,
            hovermode='x unified'
        )
        
        grafico_vueltas_mensuales_bar = fig_bar_monthly.to_html(full_html=False, config={'displayModeBar': False})

        # Gráfico de barras para vueltas por hora del día
        horas_dia, vueltas_hora = self.get_vueltas_por_hora_detallado()
        
        fig_bar_hourly = px.bar(
            x=horas_dia,
            y=vueltas_hora,
            labels={'x': 'Hora del día', 'y': 'Número de vueltas'},
            color_discrete_sequence=['#F9A8D4']
        )
        
        fig_bar_hourly.update_layout(
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis_title=None,
            yaxis_title=None,
            hovermode='x unified'
        )
        
        grafico_vueltas_horarias_bar = fig_bar_hourly.to_html(full_html=False, config={'displayModeBar': False})

        # Asignaciones activas (para la tabla)
        hoy = timezone.now().date()
        asignaciones_qs = Asignacion.objects.filter(
            estado=True,
            fecha_asignacion__lte=hoy
        ).select_related(
            'vehiculo', 'vehiculo__modelo', 'vehiculo__modelo__marca', 'operador'
        ).annotate(
            num_vueltas=Count('vueltas'),
            ultima_vuelta=Max('vueltas__fecha_hora'),

        ).order_by('-ultima_vuelta')

        if search_query:
            asignaciones_qs = asignaciones_qs.filter(
                Q(vehiculo__placa__icontains=search_query) |
                Q(operador__nombre__icontains=search_query) |
                Q(operador__apellido__icontains=search_query) |
                Q(vehiculo__modelo__nombre__icontains=search_query) |
                Q(vehiculo__modelo__marca__nombre__icontains=search_query)
            )

        if estado_filter:
            asignaciones_qs = asignaciones_qs.filter(estado=(estado_filter == 'activo'))

        # Paginación
        paginator = Paginator(asignaciones_qs, self.paginate_by)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            # Totales y estadísticas
            'total_vehiculos': total_vehiculos,
            'vehiculos_activos': vehiculos_activos,
            'vehiculos_inactivos': vehiculos_inactivos,
            'porcentaje_disponibilidad': porcentaje_disponibilidad,
            
            # Gráficos
            'grafico_estado_pie': grafico_estado_pie,
            'estado_flota_legend': estado_flota_legend,
            'grafico_vueltas_diarias_bar': grafico_vueltas_diarias_bar,
            'grafico_vueltas_mensuales_bar': grafico_vueltas_mensuales_bar,
            'grafico_vueltas_horarias_bar': grafico_vueltas_horarias_bar,
            
            # Tabla de asignaciones
            'asignaciones_recientes': page_obj,
            'total_asignaciones_activas': asignaciones_qs.count(),
            
            # Filtros
            'search_query': search_query,
            'estado_filter': estado_filter,
        }
        
        return render(request, self.template_name, context)

    def get_vueltas_por_hora(self):
        """Obtiene vueltas agrupadas por rangos horarios (para gráfico principal)"""
        hoy = timezone.now().date()
        rangos = [
            ('6-9', (6, 9)), ('9-12', (9, 12)), 
            ('12-15', (12, 15)), ('15-18', (15, 18)), 
            ('18-21', (18, 21))
        ]
        
        horas = []
        vueltas = []
        
        for nombre, (hora_inicio, hora_fin) in rangos:
            total = Vuelta.objects.filter(
                fecha_hora__date=hoy,
                fecha_hora__hour__gte=hora_inicio,
                fecha_hora__hour__lt=hora_fin
            ).count()
            
            horas.append(nombre)
            vueltas.append(total)
        
        return horas, vueltas

    def get_vueltas_por_hora_detallado(self):
        """Obtiene vueltas por hora individual (para gráfico secundario)"""
        hoy = timezone.now().date()
        horas = [f"{h}:00" for h in range(6, 22)]  # De 6:00 a 21:00
        vueltas = []
        
        for hora in range(6, 22):
            total = Vuelta.objects.filter(
                fecha_hora__date=hoy,
                fecha_hora__hour=hora
            ).count()
            vueltas.append(total)
        
        return horas, vueltas

    def get_vueltas_ultimo_anio(self):
        """Obtiene vueltas mensuales del año actual"""
        año_actual = timezone.now().year
        meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                        'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        
        resultados = Vuelta.objects.filter(
            fecha_hora__year=año_actual
        ).annotate(
            mes=TruncMonth('fecha_hora')
        ).values('mes').annotate(
            total=Count('id')
        ).order_by('mes')
        
        # Crear diccionario con los resultados
        datos_meses = {r['mes'].month: r['total'] for r in resultados}
        
        # Llenar todos los meses, incluso aquellos sin datos
        vueltas = [datos_meses.get(mes, 0) for mes in range(1, 13)]
        
        return meses_nombres, vueltas
        #---------------Asignaciones Gerente------------------------------------------------------       
from django.shortcuts import render
from django.db.models import Sum, Count, F, FloatField, ExpressionWrapper
from django.db.models.functions import TruncMonth
from .models import Asignacion, Vuelta
import plotly.express as px
import pandas as pd
from django.utils import timezone
import json

def dashboard_asignaciones(request):
    # Estadísticas básicas con annotate
    asignaciones = Asignacion.objects.annotate(
        total_vueltas_calculado=Count('vueltas')
    )
    
    total_asignaciones = asignaciones.count()
    asignaciones_activas = asignaciones.filter(estado=True).count()
    asignaciones_inactivas = asignaciones.filter(estado=False).count()

    # Calcular total de material usando annotate
    total_material = sum(
        asignacion.total_vueltas_calculado * float(asignacion.vehiculo.alto) * 
        float(asignacion.vehiculo.ancho) * float(asignacion.vehiculo.largo)
        for asignacion in asignaciones.select_related('vehiculo')
        if asignacion.vehiculo
    )

    # Gráfico de Estado de Asignaciones
    estado_data = {
        'Estado': ['Activas', 'Inactivas'],
        'Cantidad': [asignaciones_activas, asignaciones_inactivas]
    }
    fig_estado = px.pie(
        estado_data,
        values='Cantidad',
        names='Estado',
        title='Distribución de Asignaciones por Estado',
        color_discrete_sequence=['#4CAF50', '#F44336']
    )
    fig_estado.update_traces(textposition='inside', textinfo='percent+label')
    grafico_estado = fig_estado.to_html(full_html=False)

    # Gráfico de Asignaciones por Mes con annotate
    asignaciones_mes = (
        Asignacion.objects
        .annotate(
            mes=TruncMonth('fecha_asignacion'),
            total_vueltas=Count('vueltas')
        )
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )
    
    meses_labels = [item['mes'].strftime('%b %Y') for item in asignaciones_mes]
    meses_data = [item['total'] for item in asignaciones_mes]
    
    grafico_meses = None
    if meses_data:
        fig_meses = px.line(
            x=meses_labels,
            y=meses_data,
            title='Asignaciones por Mes',
            labels={'x': 'Mes', 'y': 'N° de Asignaciones'},
            markers=True
        )
        fig_meses.update_traces(line_color='#2196F3', marker_color='#2196F3')
        fig_meses.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        grafico_meses = fig_meses.to_html(full_html=False)

    # Asignaciones recientes con annotate
    fecha_limite = timezone.now() - timezone.timedelta(days=30)
    asignaciones_recientes = (
        Asignacion.objects
        .annotate(
            total_vueltas_calculado=Count('vueltas')
        )
        .select_related(
            'operador', 'vehiculo', 'vehiculo__modelo', 'vehiculo__modelo__marca'
        )
        .filter(fecha_asignacion__gte=fecha_limite)
        .order_by('-fecha_asignacion')[:10]
    )

    context = {
        'total_asignaciones': total_asignaciones,
        'asignaciones_activas': asignaciones_activas,
        'asignaciones_inactivas': asignaciones_inactivas,
        'total_material': round(total_material, 2),
        'grafico_estado': grafico_estado,
        'grafico_meses': grafico_meses,
        'asignaciones_recientes': asignaciones_recientes,
    }
    
    return render(request, 'gerente/asignaciones_gerente.html', context)

#------------------------------------------Reporte Gerente------------------------------------------------------------------

from django.shortcuts import render
from django.db.models import Sum, F, FloatField, ExpressionWrapper, Avg, Count
from .models import Operador, Vehiculo, Asignacion, Vuelta
from datetime import datetime
import json

def reportes_gerente(request):
    """
    Vista para generar reportes consolidados para el gerente
    Genera estadísticas de operadores, vehículos y asignaciones
    """
    
    # 1. DATOS DE OPERADORES (optimizado con annotate)
    operadores = Operador.objects.annotate(
        num_asignaciones=Count('asignacion')
    )
    total_operadores = operadores.count()
    operadores_activos = operadores.filter(activo=True).count()
    operadores_inactivos = total_operadores - operadores_activos
    operadores_independientes = operadores.filter(independiente=True).count()
    operadores_no_independientes = total_operadores - operadores_independientes

    # 2. DATOS DE VEHÍCULOS (optimizado con annotate)
    vehiculos = Vehiculo.objects.annotate(
        num_asignaciones=Count('asignacion'),
        capacidad_carga_calculada=F('alto') * F('ancho') * F('largo')
    )
    total_vehiculos = vehiculos.count()
    vehiculos_activos = vehiculos.filter(activo=True).count()
    vehiculos_mantenimiento = total_vehiculos - vehiculos_activos
    porcentaje_disponibilidad = round((vehiculos_activos / total_vehiculos * 100) if total_vehiculos > 0 else 0)

    # Cálculo de capacidad promedio usando la annotation
    capacidad_promedio = vehiculos.aggregate(
        avg_capacidad=Avg('capacidad_carga_calculada')
    ).get('avg_capacidad', 0) or 0

    # 3. DATOS DE ASIGNACIONES (optimizado con annotate)
    asignaciones = Asignacion.objects.annotate(
        total_vueltas_calculado=Count('vueltas'),
        volumen_transportado=ExpressionWrapper(
            Count('vueltas') * F('vehiculo__alto') * F('vehiculo__ancho') * F('vehiculo__largo'),
            output_field=FloatField()
        )
    )
    
    total_asignaciones = asignaciones.count()
    asignaciones_activas = asignaciones.filter(estado=True).count()
    asignaciones_inactivas = total_asignaciones - asignaciones_activas
    
    # Total material transportado usando la annotation
    total_material = asignaciones.aggregate(
        total_volumen=Sum('volumen_transportado')
    ).get('total_volumen', 0) or 0

    # 4. ASIGNACIONES RECIENTES (optimizado con select_related y prefetch_related)
    asignaciones_recientes = asignaciones.select_related(
        'operador', 
        'vehiculo', 
        'vehiculo__modelo',
        'vehiculo__modelo__marca'
    ).prefetch_related('vueltas').order_by('-fecha_asignacion')[:5]

    # 5. GRÁFICO DE ACTIVIDAD POR HORA (optimizado)
    horas = range(6, 21, 2)  # De 6am a 8pm cada 2 horas
    actividad_horaria = []
    
    for h in horas[:-1]:
        count = Vuelta.objects.filter(
            fecha_hora__hour__gte=h,
            fecha_hora__hour__lt=h+2
        ).count()
        actividad_horaria.append(count)

    # 6. TOP OPERADORES (nuevo)
    top_operadores = operadores.order_by('-num_asignaciones')[:5]

    # 7. TOP VEHÍCULOS (nuevo)
    top_vehiculos = vehiculos.order_by('-num_asignaciones')[:5]

    # 8. PREPARAR CONTEXTO PARA TEMPLATE
    context = {
        # Operadores
        'total_operadores': total_operadores,
        'operadores_activos': operadores_activos,
        'operadores_inactivos': operadores_inactivos,
        'operadores_independientes': operadores_independientes,
        'operadores_no_independientes': operadores_no_independientes,
        'top_operadores': top_operadores,
        
        # Vehículos
        'total_vehiculos': total_vehiculos,
        'vehiculos_activos': vehiculos_activos,
        'vehiculos_mantenimiento': vehiculos_mantenimiento,
        'porcentaje_disponibilidad': porcentaje_disponibilidad,
        'capacidad_promedio': round(capacidad_promedio, 2),
        'top_vehiculos': top_vehiculos,
        
        # Asignaciones
        'total_asignaciones': total_asignaciones,
        'asignaciones_activas': asignaciones_activas,
        'asignaciones_inactivas': asignaciones_inactivas,
        'total_material': round(total_material, 2),
        'asignaciones_recientes': asignaciones_recientes,
        
        # Datos para gráficos
        'horas_labels': json.dumps([f"{h}:00-{h+2}:00" for h in horas[:-1]]),
        'actividad_horaria': json.dumps(actividad_horaria),
        
        # Fecha de generación
        'fecha_generacion': datetime.now().strftime("%d/%m/%Y %H:%M")
    }

    return render(request, 'gerente/reportes_gerente.html', context)
# Vista para ver todos los detalles de un operador
@login_required
@user_passes_test(is_administracion)
def detalles_operador(request, cedula):
    try:
        operador = Operador.objects.get(cedula=cedula)
        
        data = {
            'cedula': operador.cedula,
            'nombre': operador.nombre,
            'apellido': operador.apellido,
            'telefono': str(operador.telefono),
            'correo': operador.correo or 'No especificado',
            'direccion': operador.direccion or 'No especificada',
            'independiente_texto': 'Sí' if operador.independiente else 'No',
            'foto_operador': operador.foto_operador.url if operador.foto_operador else None,
        }
        return JsonResponse(data)

    except Operador.DoesNotExist:
        return JsonResponse({'error': 'Operador no encontrado'}, status=404)

#----------------------------------------------------Nomina---------------------------------------------------------------------

@user_passes_test(is_nomina)
def base_nomina (request):
    return render(request, 'nomina/base_nomina')

@user_passes_test(is_nomina)
def pagos_nomina (request):
    return render(request, 'nomina/pagos_nomina')



#----------------------------------------------------------Calcular Pago-----------------------------------------------------------
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from datetime import datetime
from .models import Asignacion

def calcular_pago(request):
    asignaciones_activas = Asignacion.objects.filter(estado=True)
    
    if request.method == 'POST':
        try:
            asignacion_id = request.POST.get('asignacion')
            tipo_pago = request.POST.get('tipo_pago')
            confirmar = request.POST.get('confirmar', False)
            
            if not asignacion_id or not tipo_pago:
                messages.error(request, "Debe completar todos los campos del formulario")
                return redirect('calcular_pago')
                
            if not confirmar:
                messages.error(request, "Debe confirmar que los datos son correctos")
                return redirect('calcular_pago')
            
            asignacion = Asignacion.objects.get(pk=asignacion_id, estado=True)
            
            if asignacion.total_vueltas < 16:
                messages.error(request, f"El operador no ha completado las 16 vueltas mínimas. Vueltas actuales: {asignacion.total_vueltas}")
                return redirect('calcular_pago')
            
            capacidad_camion = float(asignacion.vehiculo.capacidad_carga)
            
            # Tasas fijas para cada tipo de pago
            tasas = {
                'arena': 12,
                'gravilla': 12,
                'granzon': 4,
                'polvillo': 2,
                'divisas': 12  # Mismo valor que arena/gravilla
            }
            
            # Calcular el pago
            pago = capacidad_camion * tasas.get(tipo_pago, 12)
            
            # Determinar el tipo de material o divisas
            if tipo_pago == 'divisas':
                material = 'divisas'
            else:
                material = tipo_pago  # Usar directamente el tipo de material seleccionado
            
            context = {
                'asignacion': asignacion,
                'tipo_pago': tipo_pago,
                'pago': pago,
                'material': material,  # Ahora muestra el material específico o divisas
                'tasa': tasas.get(tipo_pago, 12),
                'fecha': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                'capacidad_camion': capacidad_camion,
            }
            
            if 'generar_pdf' in request.POST:
                return PagoOperadorForm(request, context)
            
            return render(request, 'nomina/resultado_pago.html', context)
            
        except Asignacion.DoesNotExist:
            messages.error(request, "La asignación seleccionada no es válida")
            return redirect('calcular_pago')
        except Exception as e:
            messages.error(request, f"Ocurrió un error: {str(e)}")
            return redirect('calcular_pago')
    
    return render(request, 'nomina/calcular_pago.html', {
        'asignaciones': asignaciones_activas
    })
#------------------------------------------------------------Resumen del pago-------------------------------------------------------------
from datetime import datetime
from django.shortcuts import render, redirect
from django.core.exceptions import ValidationError
from django.utils import timezone
import json
from .models import Asignacion
from django.contrib import messages

def PagoOperadorForm(request):
    error_messages = []
    asignaciones_activas = Asignacion.objects.filter(estado=True)
    
    if request.method == 'POST':
        try:
            asignacion_id = request.POST.get('asignacion')
            tipo_pago = request.POST.get('tipo_pago')
            confirmar = request.POST.get('confirmar', False)
            
            if not asignacion_id or not tipo_pago:
                error_messages.append("Debe completar todos los campos del formulario")
                return redirect('PagoOperadorForm')
                
            if not confirmar:
                error_messages.append("Debe confirmar que los datos son correctos")
                return redirect('PagoOperadorForm')
            
            asignacion = Asignacion.objects.get(pk=asignacion_id, estado=True)
            
            if asignacion.total_vueltas < 16:
                error_messages.append(f"El operador no ha completado las 16 vueltas mínimas. Vueltas actuales: {asignacion.total_vueltas}")
                return redirect('PagoOperadorForm')
            
            capacidad_camion = float(asignacion.vehiculo.capacidad_carga)
            
            # Tasas fijas para cada tipo de pago
            tasas = {
                'arena': 12,
                'gravilla': 12,
                'granzon': 4,
                'polvillo': 2,
                'divisas': 12  # Mismo valor que arena/gravilla
            }
            
            # Todos los métodos de pago usan la misma fórmula pero con diferentes tasas
            pago = capacidad_camion * tasas.get(tipo_pago, 12)
            
            context = {
                'asignaciones': asignaciones_activas,
                'error_messages': error_messages,
                'asignacion': asignacion,
                'tipo_pago': tipo_pago,
                'pago': pago,
                'pago_divisas': pago if tipo_pago == 'divisas' else None,
                'pago_arena': pago if tipo_pago == 'arena' else None,
                'material': 'materia prima',  # Siempre será materia prima
                'tasa': tasas.get(tipo_pago, 12),
                'fecha': timezone.now().strftime("%d/%m/%Y"),
                'capacidad_camion': capacidad_camion,
                'valores_previos': {
                    'asignacion_id': asignacion.id if asignacion else '',
                    'tipo_pago': tipo_pago,
                    'confirmar': bool(confirmar)
                },
                'datos_recibo_json': json.dumps({
                    'operador': f"{asignacion.operador.nombre} {asignacion.operador.apellido}" if asignacion else "",
                    'cedula': asignacion.operador.cedula if asignacion else "",
                    'telefono': asignacion.operador.telefono if asignacion else "",
                    'vehiculo_placa': asignacion.vehiculo.placa if asignacion else "",
                    'vehiculo_modelo': str(asignacion.vehiculo.modelo) if asignacion else "",
                    'capacidad_camion': capacidad_camion,
                    'material': 'materia prima',
                    'vueltas': asignacion.total_vueltas if asignacion else 0,
                    'fecha': timezone.now().strftime("%d/%m/%Y"),
                    'tipo_pago': tipo_pago,
                    'pago_divisas': pago if tipo_pago == 'divisas' else None,
                    'pago_arena': pago if tipo_pago == 'arena' else None,
                    'tasa': tasas.get(tipo_pago, 12)
                }) if asignacion else "{}"
            }
            
            return render(request, 'nomina/resultado_pago.html', context)
            
        except Asignacion.DoesNotExist:
            error_messages.append("La asignación seleccionada no es válida")
            return redirect('PagoOperadorForm')
        except Exception as e:
            error_messages.append(f"Ocurrió un error: {str(e)}")
            return redirect('PagoOperadorForm')
    
    # GET request or initial load
    context = {
        'asignaciones': asignaciones_activas,
        'error_messages': error_messages,
        'valores_previos': {
            'asignacion_id': '',
            'tipo_pago': '',
            'confirmar': False
        }
    }
    return render(request, 'nomina/resultado_pago.html', context)