from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

# Obtiene el modelo de usuario activo en el proyecto
User = get_user_model()

# Backend personalizado para autenticar usuarios usando su email
class EmailAuthBackend(ModelBackend):
    # Método para autenticar al usuario
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(email=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None