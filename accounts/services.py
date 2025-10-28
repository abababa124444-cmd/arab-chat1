import os
import random
import re
from datetime import timedelta
from typing import Tuple

import requests
from django.utils import timezone
from django.conf import settings

from .models import OTP


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D+", "", phone or "")
    if digits.startswith("00"):
        digits = digits[2:]
    if not digits.startswith("+"):
        # Assume country code added by user; prepend '+' if missing
        digits = "+" + digits
    return digits


def create_otp(phone: str, purpose: str = OTP.PURPOSE_SIGNUP) -> Tuple[OTP, bool]:
    now = timezone.now()
    # Throttle: if an OTP exists in last 60s, reuse it
    recent = OTP.objects.filter(phone=phone, purpose=purpose, is_used=False, expires_at__gt=now).order_by('-created_at').first()
    if recent and (now - recent.created_at).total_seconds() < 60:
        if getattr(settings, 'DEBUG', False) or os.getenv('USE_STATIC_OTP'):
            if recent.code != '123456':
                recent.code = '123456'
                recent.save(update_fields=['code'])
        return recent, False
    code = f"{random.randint(0, 999999):06d}"
    if getattr(settings, 'DEBUG', False) or os.getenv('USE_STATIC_OTP'):
        code = '123456'
    otp = OTP.objects.create(
        phone=phone,
        code=code,
        purpose=purpose,
        expires_at=now + timedelta(minutes=5),
    )
    return otp, True


def send_whatsapp_otp_via_twilio(phone: str, code: str) -> bool:
    if getattr(settings, 'DEBUG', False) or os.getenv('USE_STATIC_OTP'):
        return True
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    wa_from = os.getenv('TWILIO_WHATSAPP_FROM')  # e.g. 'whatsapp:+14155238886'
    if not all([account_sid, auth_token, wa_from]):
        return False
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    data = {
        'From': wa_from,
        'To': f'whatsapp:{phone}' if not phone.startswith('whatsapp:') else phone,
        'Body': f'رمز التحقق الخاص بك هو: {code}\nArab Chat'
    }
    try:
        resp = requests.post(url, data=data, auth=(account_sid, auth_token), timeout=10)
        return 200 <= resp.status_code < 300
    except Exception:
        return False
