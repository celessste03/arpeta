import os
import django
from django.contrib.auth import get_user_model

# Configura el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema.settings')
django.setup()

# Obtiene las credenciales desde las variables de entorno
username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

User = get_user_model()

# Comprueba si el usuario ya existe para no fallar en ejecuciones futuras
if not User.objects.filter(username=username).exists():
    if username and email and password:
        print(f"Creando cuenta de superusuario para {username} ({email})")
        User.objects.create_superuser(username, email, password)
    else:
        print("Error: Las variables de entorno para el superusuario no están definidas.")
else:
    print(f"La cuenta de superusuario '{username}' ya existe.")