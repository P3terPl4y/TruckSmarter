from pathlib import Path
from tempfile import TemporaryDirectory
import re

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings


class ProductionAssetsTests(SimpleTestCase):
    def test_template_assets_exist_in_production_manifest(self):
        with TemporaryDirectory(prefix="trucksmarter-static-") as directory:
            with override_settings(
                STATIC_ROOT=directory,
                STORAGES={
                    "default": {
                        "BACKEND": "django.core.files.storage.FileSystemStorage"
                    },
                    "staticfiles": {
                        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
                    },
                },
            ):
                call_command("collectstatic", interactive=False, verbosity=0)
                assets = set()
                for folder in [
                    "templates",
                    "vehicles/templates",
                    "users/templates",
                    "dashboard/templates",
                ]:
                    for template in (settings.BASE_DIR / folder).rglob("*.html"):
                        assets.update(
                            re.findall(
                                r"{%\s*static\s+['\"]([^'\"]+)['\"]\s*%}",
                                template.read_text(),
                            )
                        )
                self.assertTrue(assets)
                for asset in assets:
                    with self.subTest(asset=asset):
                        url = staticfiles_storage.url(asset)
                        self.assertTrue(url.startswith("/static/"))
                        self.assertNotEqual(url, "/static/" + asset)
