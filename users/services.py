# users/services.py
import requests
from django.conf import settings
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

def send_verification_email(user, token):
    subject = "Verifica tu email en TruckSmarter"
    message = render_to_string('emails/verify_email.html', {
        'user': user,
        'token': token.token,
        'site_url': 'http://localhost:8000',  # Cambiar en producción
    })
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=message,
    )
def verify_email_api(email):
    """
    Verifica la validez de un email usando una API externa.
    """
    api_key = settings.EMAIL_VERIFICATION_API_KEY
    url = f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={api_key}"
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        # Verificar el estado de la respuesta
        if data.get('data', {}).get('status') == 'valid':
            return True
        return False
    except Exception:
        # Si falla la API, permitimos el registro (no bloquear por error de API)
        return True
