"""Bound dynamic requests before views or database work; Redis counters are atomic."""

import hashlib
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class RequestGuardMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if len(request.META.get("QUERY_STRING", "")) > settings.MAX_QUERY_LENGTH:
            return JsonResponse({"error": "Query too large"}, status=414)
        length = request.META.get("CONTENT_LENGTH", "")
        try:
            if length and (int(length) < 0 or int(length) > settings.MAX_REQUEST_BYTES):
                return JsonResponse({"error": "Request too large"}, status=413)
        except ValueError:
            return JsonResponse({"error": "Invalid content length"}, status=400)
        if settings.REQUEST_GUARD_ENABLED and not request.path.startswith(
            ("/static/", "/media/")
        ):
            # Never accept untrusted X-Forwarded-For as the client identity.
            identity = hashlib.sha256(
                request.META.get("REMOTE_ADDR", "").encode()
            ).hexdigest()
            window = int(time.time()) // 60
            buckets = [("all", settings.REQUESTS_PER_MINUTE)]
            if request.method not in ("GET", "HEAD", "OPTIONS"):
                buckets.append(("write", settings.WRITES_PER_MINUTE))
            try:
                for scope, limit in buckets:
                    key = f"guard:{scope}:{window}:{identity}"
                    count = 1 if cache.add(key, 1, timeout=120) else cache.incr(key)
                    if count > limit:
                        response = JsonResponse(
                            {"error": "Too many requests"}, status=429
                        )
                        response["Retry-After"] = str(60 - int(time.time()) % 60)
                        return response
            except Exception:
                logger.warning("Request limiter unavailable")
                response = JsonResponse(
                    {"error": "Service temporarily unavailable"}, status=503
                )
                response["Retry-After"] = "60"
                return response
        return self.get_response(request)


class TrustedCloudflareMiddleware:
    """Trust edge headers only on a private origin reached by an allowed tunnel peer."""

    def __init__(self, get_response):
        from ipaddress import ip_address

        self.get_response = get_response
        self.peers = {ip_address(value) for value in settings.CLOUDFLARED_TRUSTED_PEERS}

    def __call__(self, request):
        if settings.CLOUDFLARED_ENABLED:
            from ipaddress import ip_address

            try:
                peer = ip_address(request.META.get("REMOTE_ADDR", ""))
                if peer not in self.peers:
                    raise ValueError
                client = ip_address(request.headers.get("CF-Connecting-IP", ""))
                protocol = request.headers.get("X-Forwarded-Proto", "")
                if protocol not in ("http", "https"):
                    raise ValueError
            except ValueError:
                return JsonResponse({"error": "Untrusted tunnel request"}, status=403)
            request.META["REMOTE_ADDR"] = str(client)
            request.META["wsgi.url_scheme"] = protocol
        return self.get_response(request)
