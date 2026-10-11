"""Adversarial requests against the local Django test client, never external hosts."""

import hashlib
from unittest.mock import patch

import jwt
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.core.management import call_command
from io import StringIO
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from core.testing import MarketplaceTestCase
from users.models import JWTGrant
from vehicles.models import Vehicle


class BrowserSecurityTests(MarketplaceTestCase):
    def test_headers_nonce_and_escaping(self):
        payload = '<script>alert("xss")</script>'
        self.vehicle.model = payload
        self.vehicle.save()
        response = self.client.get("/")
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, payload)
        policy = response["Content-Security-Policy"]
        self.assertIn("object-src 'none'", policy)
        self.assertIn("frame-ancestors 'none'", policy)
        script_policy = next(
            x for x in policy.split(";") if x.strip().startswith("script-src")
        )
        self.assertNotIn("unsafe-inline", script_policy)
        self.assertIn("'nonce-", script_policy)
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertNotContains(response, "onclick=")
        self.assertNotEqual(policy, self.client.get("/")["Content-Security-Policy"])

    @override_settings(SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
    def test_secure_cookie_attributes(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get("/users/login/", secure=True)
        cookie = response.cookies["csrftoken"]
        self.assertTrue(cookie["secure"])
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Strict")
        response = client.post(
            "/users/login/",
            {"username": "buyer", "password": "SecurePass123!"},
            secure=True,
            HTTP_X_CSRFTOKEN=cookie.value,
            HTTP_ORIGIN="https://testserver",
        )
        self.assertEqual(response.status_code, 302)
        session = response.cookies["sessionid"]
        self.assertTrue(session["secure"])
        self.assertTrue(session["httponly"])
        self.assertEqual(session["samesite"], "Lax")

    def test_csrf_missing_wrong_and_cross_origin(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.buyer)
        client.get("/users/profile/", secure=True)
        token = client.cookies["csrftoken"].value
        for extra in (
            {},
            {"HTTP_X_CSRFTOKEN": "wrong"},
            {"HTTP_X_CSRFTOKEN": token, "HTTP_ORIGIN": "https://evil.example"},
        ):
            with self.subTest(extra=extra):
                self.assertEqual(
                    client.post("/users/api/token/", secure=True, **extra).status_code,
                    403,
                )
        response = client.post(
            "/users/api/token/",
            secure=True,
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="https://testserver",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])

    @override_settings(CORS_ALLOWED_ORIGINS=["https://trusted.example"])
    def test_cors_allowlist_and_scope(self):
        for origin, allowed in [
            ("https://evil.example", False),
            ("null", False),
            ("https://trusted.example", True),
        ]:
            response = self.client.options(
                "/users/api/me/",
                HTTP_ORIGIN=origin,
                HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
                HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization",
            )
            self.assertEqual("Access-Control-Allow-Origin" in response, allowed)
            self.assertNotIn("Access-Control-Allow-Credentials", response)
            if allowed:
                self.assertEqual(response["Access-Control-Allow-Origin"], origin)
        self.assertNotIn(
            "Access-Control-Allow-Origin",
            self.client.get("/", HTTP_ORIGIN="https://trusted.example"),
        )

    def test_sql_injection_does_not_change_catalog_or_authenticate(self):
        for attack in [
            "' OR 1=1 --",
            "'; DROP TABLE vehicles_vehicle; --",
            "0 UNION SELECT 1",
        ]:
            for field in ["q", "brand", "min_price"]:
                with self.subTest(attack=attack, field=field):
                    response = self.client.get("/", {field: attack})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(Vehicle.objects.count(), 1)
                    self.assertEqual(list(response.context["vehicles"]), [])
            response = self.client.post(
                "/users/login/", {"username": attack, "password": attack}
            )
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.PBKDF2PasswordHasher"]
    )
    def test_passwords_use_salted_pbkdf2_sha256(self):
        password = "VeryStrongPassword456!"
        first, second = make_password(password), make_password(password)
        self.assertTrue(first.startswith("pbkdf2_sha256$"))
        self.assertNotEqual(first, second)
        self.assertTrue(check_password(password, first))
        self.assertFalse(check_password("wrong", first))
        self.assertNotEqual(first, hashlib.sha256(password.encode()).hexdigest())


@override_settings(
    REQUEST_GUARD_ENABLED=True, REQUESTS_PER_MINUTE=3, WRITES_PER_MINUTE=2
)
class AbuseSecurityTests(MarketplaceTestCase):
    def test_rate_limit_and_spoofed_forwarding(self):
        with patch("core.security.time.time", return_value=120):
            for index in range(3):
                self.assertEqual(
                    self.client.get(
                        "/", HTTP_X_FORWARDED_FOR=f"1.2.3.{index}"
                    ).status_code,
                    200,
                )
            response = self.client.get("/")
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response["Retry-After"], "60")
            self.assertEqual(
                self.client.get("/", REMOTE_ADDR="127.0.0.2").status_code, 200
            )
        with patch("core.security.time.time", return_value=180):
            self.assertEqual(self.client.get("/").status_code, 200)

    def test_write_bucket(self):
        for unused in range(2):
            self.assertEqual(self.client.post("/users/api/token/").status_code, 401)
        self.assertEqual(self.client.post("/users/api/token/").status_code, 429)

    def test_cache_outage_fails_closed(self):
        with patch("core.security.cache.add", side_effect=ConnectionError):
            self.assertEqual(self.client.get("/").status_code, 503)

    def test_size_limits_before_views(self):
        self.assertEqual(self.client.get("/", {"q": "a" * 4097}).status_code, 414)
        self.assertEqual(
            self.client.generic(
                "POST", "/users/api/token/", CONTENT_LENGTH=str(7 * 1024 * 1024)
            ).status_code,
            413,
        )
        self.assertEqual(
            self.client.generic(
                "POST", "/users/api/token/", CONTENT_LENGTH="invalid"
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.generic(
                "POST", "/users/api/token/", CONTENT_LENGTH="-1"
            ).status_code,
            413,
        )


class TokenSecurityTests(MarketplaceTestCase):
    def issue(self):
        self.client.force_login(self.buyer)
        return self.client.post("/users/api/token/").json()["access_token"]

    def me(self, token):
        return Client().get("/users/api/me/", HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_issue_auth_and_methods(self):
        self.assertEqual(self.client.post("/users/api/token/").status_code, 401)
        self.assertEqual(self.client.get("/users/api/token/").status_code, 405)
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get("/users/api/me/").status_code, 401)
        self.assertEqual(self.client.post("/users/api/me/").status_code, 405)

    def test_valid_token_fingerprint_and_live_role(self):
        token = self.issue()
        self.assertEqual(self.me(token).json()["id"], self.buyer.pk)
        payload = jwt.decode(
            token,
            settings.JWT_SIGNING_KEY,
            algorithms=["HS256"],
            audience=settings.JWT_AUDIENCE,
        )
        grant = JWTGrant.objects.get()
        self.assertEqual(
            grant.jti_digest, hashlib.sha256(payload["jti"].encode()).hexdigest()
        )
        self.assertNotIn("role", payload)
        self.buyer.role = "seller"
        self.buyer.save()
        self.assertEqual(self.me(token).json()["role"], "seller")

    def test_logout_revokes_token(self):
        token = self.issue()
        self.client.post("/users/logout/")
        self.assertEqual(self.me(token).status_code, 401)

    def test_password_change_revokes_token(self):
        token = self.issue()
        self.buyer.set_password("ChangedPass456!")
        self.buyer.save()
        self.assertEqual(self.me(token).status_code, 401)

    def test_inactive_user_revokes_token(self):
        token = self.issue()
        self.buyer.is_active = False
        self.buyer.save()
        self.assertEqual(self.me(token).status_code, 401)

    def test_invalid_claims_and_signatures(self):
        token = self.issue()
        payload = jwt.decode(
            token,
            settings.JWT_SIGNING_KEY,
            algorithms=["HS256"],
            audience=settings.JWT_AUDIENCE,
        )
        attacks = [
            token + "corrupt",
            jwt.encode(
                payload, "wrong-key-at-least-thirty-two-bytes!", algorithm="HS256"
            ),
            jwt.encode(payload, key="", algorithm="none"),
        ]
        for field, value in [
            ("exp", 1),
            ("nbf", 9999999999),
            ("iat", 9999999999),
            ("aud", "other"),
            ("iss", "other"),
            ("sub", "nonnumeric"),
            ("jti", "unknown"),
            ("type", "refresh"),
        ]:
            modified = {**payload, field: value}
            attacks.append(
                jwt.encode(modified, settings.JWT_SIGNING_KEY, algorithm="HS256")
            )
        for field in ["exp", "iat", "nbf", "sub", "jti", "aud", "iss"]:
            modified = dict(payload)
            del modified[field]
            attacks.append(
                jwt.encode(modified, settings.JWT_SIGNING_KEY, algorithm="HS256")
            )
        for attack in attacks:
            with self.subTest(attack=attack[:30]):
                self.assertEqual(self.me(attack).status_code, 401)

    def test_grant_expiry_and_deletion(self):
        token = self.issue()
        JWTGrant.objects.update(expires_at=timezone.now())
        self.assertEqual(self.me(token).status_code, 401)
        JWTGrant.objects.all().delete()
        self.assertEqual(self.me(token).status_code, 401)

    @override_settings(JWT_SIGNING_KEY="")
    def test_missing_key_disables_service(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.post("/users/api/token/").status_code, 503)
        self.assertEqual(self.me("anything").status_code, 503)

    def test_prune_removes_only_expired_fingerprints(self):
        self.issue()
        active = JWTGrant.objects.get()
        JWTGrant.objects.create(
            user=self.buyer,
            jti_digest="f" * 64,
            session_key=active.session_key,
            auth_hash=active.auth_hash,
            expires_at=timezone.now(),
        )
        call_command("prune_tokens", stdout=StringIO())
        self.assertEqual(
            list(JWTGrant.objects.values_list("pk", flat=True)), [active.pk]
        )

    def test_token_issuance_bounded(self):
        self.client.force_login(self.buyer)
        for unused in range(10):
            self.assertEqual(self.client.post("/users/api/token/").status_code, 200)
        self.assertEqual(self.client.post("/users/api/token/").status_code, 429)


@override_settings(
    CLOUDFLARED_ENABLED=True,
    CLOUDFLARED_TRUSTED_PEERS=["127.0.0.1"],
    REQUEST_GUARD_ENABLED=True,
    REQUESTS_PER_MINUTE=2,
)
class CloudflareSecurityTests(MarketplaceTestCase):
    def forwarded(self, ip="203.0.113.1", **extra):
        return self.client.get(
            "/", HTTP_CF_CONNECTING_IP=ip, HTTP_X_FORWARDED_PROTO="https", **extra
        )

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_trusted_tunnel_preserves_https_without_redirect_loop(self):
        response = self.forwarded()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.is_secure())
        self.assertEqual(response.wsgi_request.META["REMOTE_ADDR"], "203.0.113.1")

    def test_client_limits_are_separate_behind_tunnel(self):
        self.assertEqual(self.forwarded().status_code, 200)
        self.assertEqual(self.forwarded().status_code, 200)
        self.assertEqual(self.forwarded().status_code, 429)
        self.assertEqual(self.forwarded("203.0.113.2").status_code, 200)

    def test_external_peer_cannot_spoof_edge_headers(self):
        self.assertEqual(self.forwarded(REMOTE_ADDR="198.51.100.1").status_code, 403)

    def test_missing_or_invalid_edge_headers_rejected(self):
        self.assertEqual(self.client.get("/").status_code, 403)
        self.assertEqual(self.forwarded("garbage").status_code, 403)
        self.assertEqual(self.forwarded("1.2.3.4, 5.6.7.8").status_code, 403)
        self.assertEqual(
            self.client.get(
                "/",
                HTTP_CF_CONNECTING_IP="203.0.113.1",
                HTTP_X_FORWARDED_PROTO="https,http",
            ).status_code,
            403,
        )

    @override_settings(CLOUDFLARED_ENABLED=False)
    def test_disabled_mode_ignores_edge_headers(self):
        response = self.forwarded()
        self.assertEqual(response.wsgi_request.META["REMOTE_ADDR"], "127.0.0.1")
        self.assertFalse(response.wsgi_request.is_secure())
