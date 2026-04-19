"""
Custom middleware to handle CSRF for API endpoints.
This exempts API endpoints from CSRF checks since they use token auth or are public.
"""

from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class CsrfExemptApiMiddleware(MiddlewareMixin):
    """
    Exempt API endpoints from CSRF validation.
    API endpoints should use authentication tokens or be explicitly public.
    """
    
    def process_request(self, request):
        if request.path.startswith('/api/'):
            # Mark the request as CSRF exempt
            request._dont_enforce_csrf_checks = True
        return None
