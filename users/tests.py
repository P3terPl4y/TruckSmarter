from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()

class UserModelTest(TestCase):
    """Pruebas para el modelo User personalizado."""

    def test_create_user(self):
        """Verifica que se pueda crear un usuario."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='customer'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.role, 'customer')
        self.assertTrue(user.check_password('testpass123'))

    def test_create_superuser(self):
        """Verifica que se pueda crear un superusuario."""
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)


class ProfileModelTest(TestCase):
    """Pruebas para el modelo Profile."""

    def test_profile_creation_signal(self):
        """Verifica que se cree un perfil automáticamente al crear usuario."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertTrue(hasattr(user, 'profile'))
        self.assertEqual(user.profile.user, user)


class RegistrationTest(TestCase):
    """Pruebas para el registro de usuarios."""

    def setUp(self):
        self.client = Client()

    def test_register_view(self):
        """Verifica que el registro de usuario funcione."""
        response = self.client.post(reverse('users:register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'role': 'customer',
        })
        self.assertEqual(response.status_code, 302)  # Redirección
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertEqual(user.role, 'customer')
        self.assertTrue(hasattr(user, 'profile'))


class LoginTest(TestCase):
    """Pruebas para el inicio de sesión."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
       

    def test_login_view(self):
        """Verifica que el login funcione correctamente."""
        response = self.client.post(reverse('users:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirección
        # Verificar que el usuario está autenticado
        response = self.client.get(reverse('vehicles:list'))
        self.assertEqual(response.context['user'].username, 'testuser')


class ProfileViewTest(TestCase):
    """Pruebas para ProfileView."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='admin'
        )
       

    def test_profile_view_authenticated(self):
        """Verifica que un usuario autenticado pueda ver su perfil."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')

    def test_profile_view_unauthenticated(self):
        """Verifica que usuarios no autenticados sean redirigidos."""
        response = self.client.get(reverse('users:profile'))
        self.assertRedirects(response, f'/users/login/?next={reverse("users:profile")}')

    def test_profile_update(self):
        """Verifica que el perfil se pueda actualizar."""
        self.client.force_login(self.user)
        response = self.client.post(reverse('users:profile'), {
            'username': 'updateduser',
            'email': 'updated@example.com',
            'first_name': 'New',
            'last_name': 'Name',
            'phone': '123456789',
            'address': 'Calle Falsa 123',
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'updateduser')
        self.assertEqual(self.user.email, 'updated@example.com')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.phone, '123456789')


