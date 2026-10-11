from datetime import timedelta
from unittest.mock import patch
from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from core.testing import MarketplaceTestCase
from .models import VehicleView


class AnalyticsFunctionalTests(MarketplaceTestCase):
    def detail(self, client=None):
        return (client or self.client).get(
            reverse("vehicles:detail", args=[self.vehicle.pk])
        )

    def test_authenticated_deduplication_survives_cache_eviction(self):
        self.client.force_login(self.buyer)
        self.assertEqual(self.detail().status_code, 200)
        cache.clear()
        self.detail()
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.view_count, 1)
        self.assertEqual(VehicleView.objects.count(), 1)

    def test_anonymous_sessions_distinct_even_same_ip(self):
        first = Client()
        second = Client()
        self.detail(first)
        self.detail(first)
        self.detail(second)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.view_count, 2)
        views = list(VehicleView.objects.all())
        self.assertEqual(len(views), 2)
        self.assertTrue(views[0].session_key)
        self.assertTrue(views[1].session_key)
        self.assertNotEqual(views[0].session_key, views[1].session_key)

    def test_expired_view_counts_again(self):
        self.client.force_login(self.buyer)
        self.detail()
        VehicleView.objects.update(viewed_at=timezone.now() - timedelta(hours=25))
        cache.clear()
        self.detail()
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.view_count, 2)

    def test_cache_failure_does_not_break_detail(self):
        self.client.force_login(self.buyer)
        with (
            patch(
                "analytics.utils.cache.get", side_effect=ConnectionError("Redis down")
            ),
            patch(
                "analytics.utils.cache.set", side_effect=ConnectionError("Redis down")
            ),
        ):
            self.assertEqual(self.detail().status_code, 200)
            self.assertEqual(self.detail().status_code, 200)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.view_count, 1)

    def test_head_post_and_inaccessible_detail_not_counted(self):
        url = reverse("vehicles:detail", args=[self.vehicle.pk])
        self.assertEqual(self.client.head(url).status_code, 200)
        self.assertEqual(self.client.post(url).status_code, 405)
        self.vehicle.is_active = False
        self.vehicle.save()
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertFalse(VehicleView.objects.exists())

    def test_dashboard_context_matches_template(self):
        self.client.force_login(self.buyer)
        self.detail()
        self.client.force_login(self.admin)
        response = self.client.get(reverse("analytics:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_views"], 1)
        self.assertEqual(response.context["avg_views_per_vehicle"], 1)
        self.assertContains(response, "Corolla")

    def test_empty_dashboard_metrics(self):
        self.vehicle.delete()
        self.client.force_login(self.admin)
        response = self.client.get(reverse("analytics:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_views"], 0)
        self.assertEqual(response.context["avg_views_per_vehicle"], 0)

    def test_permissions_use_same_business_admin_rule(self):
        url = reverse("analytics:dashboard")
        self.assertEqual(self.client.get(url).status_code, 302)
        for user, status in [
            (self.buyer, 403),
            (self.owner, 403),
            (self.admin, 200),
            (self.superuser, 200),
        ]:
            self.client.force_login(user)
            with self.subTest(user=user.username):
                self.assertEqual(self.client.get(url).status_code, status)
        self.other.is_staff = True
        self.other.save()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_stats_detail_and_missing_vehicle(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(
                reverse("analytics:vehicle_stats", args=[self.vehicle.pk])
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("analytics:vehicle_stats", args=[999999])
            ).status_code,
            404,
        )

    def test_redis_cache_hit_avoids_duplicate_tracking_queries(self):
        self.client.force_login(self.buyer)
        with self.captureOnCommitCallbacks(execute=True):
            self.detail()
        from .utils import get_view_cache_key

        request = type("Request", (), {"user": self.buyer})()
        self.assertIs(cache.get(get_view_cache_key(self.vehicle.pk, request)), True)
        self.detail()
        self.assertEqual(VehicleView.objects.count(), 1)

    def test_database_tracking_failure_keeps_detail_available(self):
        with patch(
            "analytics.decorators.record_vehicle_view",
            side_effect=RuntimeError("DB unavailable"),
        ):
            with self.assertLogs("analytics.decorators", level="ERROR"):
                self.assertEqual(self.detail().status_code, 200)

    def test_cache_write_failure_keeps_committed_visit(self):
        self.client.force_login(self.buyer)
        with patch(
            "analytics.utils.cache.set", side_effect=ConnectionError("Redis down")
        ):
            with self.assertLogs("analytics.utils", level="WARNING"):
                with self.captureOnCommitCallbacks(execute=True):
                    self.detail()
        self.assertEqual(VehicleView.objects.count(), 1)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.view_count, 1)
