import random
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from rest_framework_simplejwt.tokens import RefreshToken


def generate_otp():
    return random.randint(1000, 9999)

def send_email(email):
    otp_code = generate_otp()
    subject = "Your OTP for Email Verification"
    
    html_message = render_to_string('accounts/send-otp.html', {
        'otp_code': otp_code,
    })
    
    from_email = settings.EMAIL_HOST_USER

    send_mail(
        subject,
        "",
        from_email,
        [email],
        fail_silently=False,
        html_message=html_message,
    )
    return otp_code


def get_tokens_for_user(user):
    """
    Generate access and refresh tokens for a given user.
    """
    refresh = RefreshToken.for_user(user)
    return {
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh)
    }
