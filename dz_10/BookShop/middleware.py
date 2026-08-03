from django.middleware.locale import LocaleMiddleware


class BypassAPILocaleMiddleware(LocaleMiddleware):
    def process_request(self, request):
        # Если запрос начинается с /api/, Django вообще пропустит этот middleware
        if request.path_info.startswith("/api/"):
            return None
        return super().process_request(request)

    def process_response(self, request, response):
        if request.path_info.startswith("/api/"):
            return response
        return super().process_response(request, response)
