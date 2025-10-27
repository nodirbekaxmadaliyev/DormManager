from django.shortcuts import redirect
from django.urls import reverse

EXEMPT_URLS = [
    '/accounts/login/',
    '/accounts/logout/',
    '/admin/',
    '/stream',
]

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            path = request.path_info
            if not any(path.startswith(url) for url in EXEMPT_URLS):
                return redirect(reverse('login'))
        return self.get_response(request)
