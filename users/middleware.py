from django.shortcuts import render
from django.utils import timezone

class BanCheckMiddleware:
    EXEMPT_URLS = [
        '/ban-appeal/',
        '/static/'
    ]

    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if self._is_exempt(request.path):
            return self.get_response(request)

        user = request.user
        
        if user.is_authenticated:
            if user._should_auto_unban():
                user._perform_auto_unban()
                user.save(update_fields=[
                    'is_active',
                    'started_ban',
                    'ended_ban',
                    'reason_ban',
                ])
            
            if user.is_banned():
                return self._render_ban_page(request, user)
        
        return self.get_response(request)

    def _is_exempt(self, path):
        for exempt_url in self.EXEMPT_URLS:
            if path.startswith(exempt_url):
                return True
        return False
    
    def _render_ban_page(self, request, user):
        request.session['banned_user_id'] = user.id
        
        from django.contrib.auth import logout
        logout(request)
        
        context = {
            'reason': user.reason_ban,
            'started': user.started_ban,
            'ended': user.ended_ban,
            'now': timezone.now(),
        }
        return render(request, 'users/banned.html', context, status=403)