"""
Custom middleware to handle CSRF for API endpoints.
This exempts API endpoints from CSRF checks since they use token auth or are public.
"""

from django.utils.deprecation import MiddlewareMixin


class CsrfExemptApiMiddleware(MiddlewareMixin):
    """
    Exempt API endpoints from CSRF validation.
    API endpoints should use authentication tokens or be explicitly public.
    """
    
    def process_view(self, request, callback, callback_args, callback_kwargs):
        if request.path.startswith('/api/'):
            from django.views.decorators.csrf import csrf_exempt
            request._csrf_exempt = True
        return None
