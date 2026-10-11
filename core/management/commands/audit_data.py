"""Read-only checks to run before applying new database constraints."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, F, Q
from django.db.models.functions import Lower
from django.utils import timezone
from sales.models import Sale
from vehicles.models import Vehicle


class Command(BaseCommand):
    help = "Audita datos existentes sin modificarlos; falla si requieren revisión antes de migrar."

    def handle(self, *args, **options):
        checks = [
            (
                "emails repetidos ignorando mayúsculas",
                get_user_model()
                .objects.annotate(key=Lower("email"))
                .values("key")
                .annotate(n=Count("pk"))
                .filter(n__gt=1),
            ),
            (
                "ofertas pendientes duplicadas",
                Sale.objects.filter(status="offer_pending")
                .values("vehicle_id", "buyer_id")
                .annotate(n=Count("pk"))
                .filter(n__gt=1),
            ),
            (
                "reservas duplicadas",
                Sale.objects.filter(status="reserved")
                .values("vehicle_id")
                .annotate(n=Count("pk"))
                .filter(n__gt=1),
            ),
            (
                "ventas finales duplicadas",
                Sale.objects.filter(status__in=["offer_accepted", "completed"])
                .values("vehicle_id")
                .annotate(n=Count("pk"))
                .filter(n__gt=1),
            ),
            ("precios de vehículo no positivos", Vehicle.objects.filter(price__lte=0)),
            (
                "años fuera del rango admitido",
                Vehicle.objects.filter(
                    Q(year__lt=1886) | Q(year__gt=timezone.now().year + 1)
                ),
            ),
            ("importes de venta no positivos", Sale.objects.filter(amount__lte=0)),
            (
                "precios ofertados inválidos",
                Sale.objects.filter(offered_price__isnull=False).filter(
                    Q(offered_price__lte=0) | Q(offered_price__gte=F("amount"))
                ),
            ),
            (
                "vehículos vendidos todavía activos o reservados",
                Vehicle.objects.filter(sold=True).filter(
                    Q(is_active=True) | Q(reserved=True)
                ),
            ),
            (
                "reservas sin titular o titulares sin reserva",
                Vehicle.objects.filter(
                    Q(reserved=True, reserved_by__isnull=True)
                    | Q(reserved=False, reserved_by__isnull=False)
                ),
            ),
            (
                "anuncios activos sin vendedor",
                Vehicle.objects.filter(is_active=True, created_by__isnull=True),
            ),
            (
                "estados comerciales desconocidos",
                Sale.objects.exclude(
                    status__in=[choice[0] for choice in Sale.STATUS_CHOICES]
                ),
            ),
        ]
        problems = []
        for label, queryset in checks:
            count = queryset.count()
            self.stdout.write(f"{label}: {count}")
            if count:
                problems.append(label)
        if problems:
            raise CommandError(
                "Revisa los datos señalados antes de migrar. No se modificó ningún registro."
            )
        self.stdout.write(self.style.SUCCESS("Auditoría de datos sin incidencias."))
