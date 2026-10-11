from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from core.testing import MarketplaceTestCase
from .forms import ProfileForm
from .models import EmailVerification

User = get_user_model()


class UsersFunctionalTests(MarketplaceTestCase):
    def test_registration_cannot_assign_admin_or_staff(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("users:register"),
                {
                    "username": "new",
                    "email": "NEW@example.com",
                    "password1": "SomethingSecure123!",
                    "password2": "SomethingSecure123!",
                    "role": "admin",
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="new")
        self.assertEqual(user.role, "customer")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.email, "new@example.com")
        token = EmailVerification.objects.get(user=user)
        self.assertGreater(token.expires_at, timezone.now())
        self.assertTrue(mail.outbox)

    def test_duplicate_email_case_insensitive(self):
        response = self.client.post(
            reverse("users:register"),
            {
                "username": "duplicate",
                "email": self.buyer.email.upper(),
                "password1": "SomethingSecure123!",
                "password2": "SomethingSecure123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="duplicate").exists())

    def test_weak_password_rejected(self):
        response = self.client.post(
            reverse("users:register"),
            {
                "username": "weak",
                "email": "weak@example.com",
                "password1": "123",
                "password2": "123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="weak").exists())

    def test_token_default_expiry_and_consumption(self):
        token = EmailVerification.objects.create(
            user=self.buyer, email=self.buyer.email
        )
        self.assertAlmostEqual(
            (token.expires_at - timezone.now()).total_seconds(), 86400, delta=2
        )
        url = reverse("users:verify_email", args=[token.token])
        self.assertEqual(self.client.get(url).status_code, 302)
        token.refresh_from_db()
        self.assertTrue(token.is_verified)
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_expired_and_changed_email_tokens_rejected(self):
        for email, expires in [
            (self.buyer.email, timezone.now() - timedelta(seconds=1)),
            ("old@example.com", timezone.now() + timedelta(hours=1)),
        ]:
            token = EmailVerification.objects.create(
                user=self.buyer, email=email, expires_at=expires
            )
            self.client.get(reverse("users:verify_email", args=[token.token]))
            token.refresh_from_db()
            self.assertFalse(token.is_verified)

    def test_logout_only_post(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(reverse("users:logout")).status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.post(reverse("users:logout")).status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_initial_values_and_commit_false(self):
        profile = self.buyer.profile
        profile.phone = "555"
        profile.bank_account = "123"
        profile.save()
        response = None
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("users:profile"))
        self.assertEqual(response.context["form"]["phone"].value(), "555")
        data = {
            "username": self.buyer.username,
            "email": self.buyer.email,
            "phone": "999",
            "address": "new",
        }
        form = ProfileForm(data, instance=self.buyer)
        self.assertTrue(form.is_valid(), form.errors)
        form.save(commit=False)
        profile.refresh_from_db()
        self.assertEqual(profile.phone, "555")

    def test_profile_cannot_elevate_role_or_edit_another_user(self):
        self.client.force_login(self.buyer)
        data = {
            "username": self.buyer.username,
            "email": self.buyer.email,
            "phone": "999",
            "role": "admin",
            "is_superuser": True,
            "id": self.other.pk,
        }
        self.assertEqual(
            self.client.post(reverse("users:profile"), data).status_code, 302
        )
        self.buyer.refresh_from_db()
        self.assertEqual(self.buyer.role, "customer")
        self.assertFalse(self.buyer.is_superuser)
        self.other.profile.refresh_from_db()
        self.assertEqual(self.other.profile.phone, "")

    def test_profile_email_change_invalidates_tokens(self):
        token = EmailVerification.objects.create(
            user=self.buyer, email=self.buyer.email
        )
        self.client.force_login(self.buyer)
        self.client.post(
            reverse("users:profile"),
            {"username": self.buyer.username, "email": "changed@example.com"},
        )
        self.assertFalse(EmailVerification.objects.filter(pk=token.pk).exists())

    def test_admin_routes_permission_matrix(self):
        for name, args in [("admin_list", []), ("admin_edit", [self.buyer.pk])]:
            url = reverse("users:" + name, args=args)
            self.assertEqual(self.client.get(url).status_code, 302)
            for user, status in [
                (self.buyer, 403),
                (self.owner, 403),
                (self.admin, 200),
                (self.superuser, 200),
            ]:
                with self.subTest(name=name, user=user.username):
                    self.client.force_login(user)
                    self.assertEqual(self.client.get(url).status_code, status)
            self.client.logout()

    def test_login_honors_safe_next_and_rejects_external_redirect(self):
        for target, expected in [
            ("/sales/history/", "/sales/history/"),
            ("https://evil.example/", "/"),
        ]:
            self.client.logout()
            response = self.client.post(
                reverse("users:login"),
                {
                    "username": self.buyer.username,
                    "password": "SecurePass123!",
                    "next": target,
                },
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, expected)

    def test_inactive_cannot_login(self):
        self.buyer.is_active = False
        self.buyer.save()
        response = self.client.post(
            reverse("users:login"),
            {"username": self.buyer.username, "password": "SecurePass123!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(RATELIMIT_ENABLE=True)
    def test_login_rate_limit_returns_429(self):
        for _ in range(5):
            self.assertEqual(
                self.client.post(
                    reverse("users:login"),
                    {"username": "missing", "password": "invalid"},
                ).status_code,
                200,
            )
        self.assertEqual(
            self.client.post(
                reverse("users:login"), {"username": "missing", "password": "invalid"}
            ).status_code,
            429,
        )

    @override_settings(RATELIMIT_ENABLE=True)
    def test_registration_rate_limit_returns_429(self):
        for _ in range(5):
            self.client.post(reverse("users:register"), {})
        self.assertEqual(
            self.client.post(reverse("users:register"), {}).status_code, 429
        )

    @patch("users.views.send_verification_email", side_effect=RuntimeError("SMTP down"))
    def test_email_failure_preserves_registered_user(self, mock):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("users:register"),
                {
                    "username": "smtp",
                    "email": "smtp@example.com",
                    "password1": "SomethingSecure123!",
                    "password2": "SomethingSecure123!",
                },
            )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="smtp").exists())

    @override_settings(SITE_URL="https://trucks.example")
    def test_verification_email_uses_configured_url(self):
        from .services import send_verification_email

        token = EmailVerification.objects.create(
            user=self.buyer, email=self.buyer.email
        )
        send_verification_email(self.buyer, token)
        self.assertIn("https://trucks.example", mail.outbox[-1].body)

    @override_settings(EMAIL_VALIDATE_DNS=True)
    @patch("dns.resolver.resolve")
    def test_dns_validation_uses_mx_and_rejects_bad_domain(self, resolve):
        import dns.resolver
        from django.core.exceptions import ValidationError
        from .validators import validate_email_domain

        validate_email_domain("user@example.com")
        resolve.assert_called_once_with("example.com", "MX", lifetime=2)
        resolve.side_effect = dns.resolver.NXDOMAIN
        with self.assertRaises(ValidationError):
            validate_email_domain("user@example.com")

    @override_settings(EMAIL_VERIFICATION_API_KEY="test-api-key")
    @patch("users.services.requests.get")
    def test_external_email_validation_is_mocked_and_fail_open(self, get):
        from .services import verify_email_api

        get.return_value.json.return_value = {"data": {"status": "valid"}}
        self.assertTrue(verify_email_api("user@example.com"))
        self.assertEqual(get.call_args.kwargs["params"]["email"], "user@example.com")
        get.return_value.json.return_value = {"data": {"status": "invalid"}}
        self.assertFalse(verify_email_api("user@example.com"))
        get.side_effect = ConnectionError("Provider unavailable")
        self.assertTrue(verify_email_api("user@example.com"))

    @patch("users.forms.verify_email_api", return_value=False)
    def test_rejected_email_not_registered(self, verify):
        response = self.client.post(
            reverse("users:register"),
            {
                "username": "rejected",
                "email": "bad@example.com",
                "password1": "SomethingSecure123!",
                "password2": "SomethingSecure123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="rejected").exists())

    @patch("users.views.EmailVerification.objects.create")
    def test_registration_integrity_error_rolls_back_partial_user(self, create):
        from django.db import IntegrityError

        create.side_effect = IntegrityError("Concurrent duplicate")
        response = self.client.post(
            reverse("users:register"),
            {
                "username": "rollback",
                "email": "rollback@example.com",
                "password1": "SomethingSecure123!",
                "password2": "SomethingSecure123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="rollback").exists())
