import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings
from PIL import Image


class CatalogueMediaTests(SimpleTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.settings_override = override_settings(MEDIA_ROOT=self.root, DEBUG=False)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        (self.root / "vehicles").mkdir()
        Image.new("RGB", (2, 2)).save(self.root / "vehicles" / "car.jpg")

    def test_image_available_in_production(self):
        response = self.client.get("/media/vehicles/car.jpg")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(
            b"".join(response.streaming_content),
            (self.root / "vehicles/car.jpg").read_bytes(),
        )
        response.close()

    def test_head_and_write_methods(self):
        response = self.client.head("/media/vehicles/car.jpg")
        self.assertEqual(response.status_code, 200)
        response.close()
        self.assertEqual(self.client.post("/media/vehicles/car.jpg").status_code, 405)

    def test_missing_and_non_images_are_not_served(self):
        (self.root / "vehicles" / "fake.jpg").write_text("<script>alert(1)</script>")
        for path in [
            "vehicles/missing.jpg",
            "vehicles/fake.jpg",
            "private.txt",
            "vehicles/..",
            "vehicles/../../.env",
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get("/media/" + path).status_code, 404)

    def test_symlink_outside_root_is_rejected(self):
        (self.root / "vehicles" / "escape.jpg").symlink_to("/etc/passwd")
        self.assertEqual(self.client.get("/media/vehicles/escape.jpg").status_code, 404)
