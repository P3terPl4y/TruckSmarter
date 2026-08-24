from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    # Si necesitas crear grupos o permisos, usa el método ready()
    # def ready(self):
    #     from django.contrib.auth.models import Group
    #     from django.contrib.contenttypes.models import ContentType
    #     # ... lógica aquí
