"""Short-lived, session-bound access tokens; no bearer authentication on HTML views."""

import hashlib
import secrets
from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .models import JWTGrant


def signing_key():
    key = settings.JWT_SIGNING_KEY
    return key if len(key.encode()) >= 32 else None


def fingerprint(value):
    return hashlib.sha256(value.encode()).hexdigest()


@never_cache
@require_POST
@transaction.atomic
def issue_token(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    key = signing_key()
    if not key:
        return JsonResponse({"error": "Token service unavailable"}, status=503)
    get_user_model().objects.select_for_update().get(pk=request.user.pk)
    now = timezone.now()
    grants = JWTGrant.objects.filter(session_key=request.session.session_key)
    grants.filter(expires_at__lte=now).delete()
    if grants.count() >= 10:
        return JsonResponse({"error": "Too many active tokens"}, status=429)
    ttl = min(max(settings.JWT_TTL_SECONDS, 1), 900)
    expires = now + timedelta(seconds=ttl)
    jti = secrets.token_urlsafe(32)
    JWTGrant.objects.create(
        user=request.user,
        jti_digest=fingerprint(jti),
        session_key=request.session.session_key,
        auth_hash=request.user.get_session_auth_hash(),
        expires_at=expires,
    )
    token = jwt.encode(
        {
            "sub": str(request.user.pk),
            "jti": jti,
            "iat": now,
            "nbf": now,
            "exp": expires,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "type": "access",
        },
        key,
        algorithm="HS256",
    )
    return JsonResponse(
        {"access_token": token, "token_type": "Bearer", "expires_in": ttl}
    )


@never_cache
@require_GET
def current_user(request):
    key = signing_key()
    if not key:
        return JsonResponse({"error": "Token service unavailable"}, status=503)
    authorization = request.headers.get("Authorization", "")
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer" or len(token) > 4096:
            raise ValueError
        payload = jwt.decode(
            token,
            key,
            algorithms=["HS256"],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={"require": ["sub", "jti", "iat", "nbf", "exp", "iss", "aud"]},
        )
        if payload.get("type") != "access" or not isinstance(payload["jti"], str):
            raise ValueError
        user_id = int(payload["sub"])
        if not 0 < user_id <= 9223372036854775807:
            raise ValueError
        grant = JWTGrant.objects.select_related("user").get(
            jti_digest=fingerprint(payload["jti"]),
            user_id=user_id,
            expires_at__gt=timezone.now(),
        )
        if not grant.user.is_active or not constant_time_compare(
            grant.auth_hash, grant.user.get_session_auth_hash()
        ):
            raise ValueError
        session = Session.objects.get(
            session_key=grant.session_key, expire_date__gt=timezone.now()
        )
        if session.get_decoded().get("_auth_user_id") != str(grant.user_id):
            raise ValueError
    except (
        jwt.InvalidTokenError,
        ValueError,
        TypeError,
        JWTGrant.DoesNotExist,
        Session.DoesNotExist,
    ):
        response = JsonResponse({"error": "Invalid or expired token"}, status=401)
        response["WWW-Authenticate"] = "Bearer"
        return response
    user = grant.user
    return JsonResponse({"id": user.pk, "username": user.username, "role": user.role})
