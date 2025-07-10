"""
Configuración de Django para el proyecto ARPETA (Actualizado para despliegue en Render).
"""

import os
import dj_database_url
from pathlib import Path

# --- Configuración Base ---
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')


# --- Seguridad y Modo de Ejecución (Configurado para Render) ---
# --------------------------------------------------------------------------

# Las claves se leen de las Variables de Entorno en producción para mayor seguridad.
SECRET_KEY = os.environ.get('SECRET_KEY')
FERNET_KEY = os.environ.get('FERNET_KEY')

# El modo DEBUG se desactiva automáticamente en Render (producción).
# Será True solo si defines una variable de entorno DEVELOPMENT=True.
DEBUG = os.environ.get('DEVELOPMENT') == 'True'

# Se configura automáticamente el host de Render.
# En modo DEBUG, también se permiten los hosts locales.
ALLOWED_HOSTS = []
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

if DEBUG:
    ALLOWED_HOSTS.extend(['127.0.0.1', 'localhost', '::1'])


# --- Aplicaciones y Middleware ---
# --------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'auditlog',
    'django.contrib.sites',
    'arpeta',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise Middleware para servir archivos estáticos eficientemente.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'auditlog.middleware.AuditlogMiddleware',
    'arpeta.middleware.CurrentDateMiddleware',
]

ROOT_URLCONF = 'sistema.urls'
WSGI_APPLICATION = 'sistema.wsgi.application'


# --- Configuración de Plantillas ---
# --------------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATE_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# --- Base de Datos (Configurada para Render) ---
# --------------------------------------------------------------------------
# Lee la variable de entorno DATABASE_URL de Render.
# Si no la encuentra, usa la base de datos local para desarrollo.
DATABASES = {
    'default': dj_database_url.config(
        default=f"postgresql://postgres:mia2712@localhost:5432/arpeta_final",
        conn_max_age=600 # Mantiene las conexiones activas por 10 minutos
    )
}


# --- Validación de Contraseñas ---
# --------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# --- Internacionalización ---
# --------------------------------------------------------------------------
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Caracas'
USE_I18N = True
USE_TZ = True


# --- Archivos Estáticos (Configurado para WhiteNoise) ---
# --------------------------------------------------------------------------
STATIC_URL = 'static/'
# Directorio donde `collectstatic` reunirá todos los archivos estáticos para producción.
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Directorio de estáticos a nivel de proyecto.
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
# Almacenamiento de estáticos para que WhiteNoise pueda servirlos.
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# --- Autenticación ---
# --------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/login/'
AUTHENTICATION_BACKENDS = [
    'arpeta.backends.EmailAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]


# --- Configuración de Correo Electrónico (Configurado para Render) ---
# --------------------------------------------------------------------------
# Lee las credenciales de correo desde las Variables de Entorno.
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('EMAIL_HOST_USER')