from django.shortcuts import redirect
from django.conf import settings
from django.urls import reverse


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Login talab qilinmaydigan URL lar
        exempt_urls = [
            settings.LOGIN_URL.lstrip('/'),
            'admin/',
            'logout/',
            'register/',
            'password_reset/',
            'static/',
            'media/'
        ]

        # Agar login qilmagan bo'lsa va URL ruxsat etilganlar ro'yxatida bo'lmasa
        if not request.user.is_authenticated and \
                not any(request.path.lstrip('/').startswith(url) for url in exempt_urls):
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        return None