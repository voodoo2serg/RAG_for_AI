import uuid
from django.utils.deprecation import MiddlewareMixin


class RequestIDMiddleware(MiddlewareMixin):
    HEADER = "HTTP_X_REQUEST_ID"

    def process_request(self, request):
        request.request_id = request.META.get(self.HEADER) or str(uuid.uuid4())

    def process_response(self, request, response):
        request_id = getattr(request, "request_id", None)
        if request_id:
            response["X-Request-ID"] = request_id
        return response
