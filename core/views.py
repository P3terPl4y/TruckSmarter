"""Shared functionality is provided by core.permissions and core.mixins."""

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.http import require_safe
from PIL import Image, UnidentifiedImageError


@require_safe
def catalog_image(request, image_path):
    """Serve public catalogue raster images from the private local media root."""
    root = Path(settings.MEDIA_ROOT).resolve()
    path = (root / image_path).resolve()
    if (
        path == root
        or not path.is_relative_to(root)
        or path.relative_to(root).parts[0] not in {"vehicles", "brands"}
    ):
        raise Http404
    content_types = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "GIF": "image/gif",
        "WEBP": "image/webp",
        "ICO": "image/x-icon",
    }
    try:
        stream = path.open("rb")
    except (OSError, ValueError):
        raise Http404 from None
    try:
        with Image.open(path) as image:
            content_type = content_types.get(image.format)
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
        stream.close()
        raise Http404 from None
    if not content_type:
        stream.close()
        raise Http404
    response = FileResponse(stream, content_type=content_type)
    response["Cache-Control"] = "public, max-age=300"
    response["X-Content-Type-Options"] = "nosniff"
    return response
