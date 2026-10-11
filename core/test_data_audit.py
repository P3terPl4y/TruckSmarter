from io import StringIO
from django.core.management import call_command, CommandError
from core.testing import MarketplaceTestCase


class DataAuditTests(MarketplaceTestCase):
    def test_valid_data_passes(self):
        output = StringIO()
        call_command("audit_data", stdout=output)
        self.assertIn("sin incidencias", output.getvalue())

    def test_invalid_legacy_state_reported_without_mutation(self):
        self.vehicle.sold = True
        self.vehicle.is_active = True
        self.vehicle.save()
        with self.assertRaises(CommandError):
            call_command("audit_data", stdout=StringIO())
        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.is_active)
