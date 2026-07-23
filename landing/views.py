# landing/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.translation import activate
from django.conf import settings

def landing_page(request):
    """
    Landing page view for AgriVision
    Serves as the entry point for both authenticated and unauthenticated users
    """
    context = {
        'page_title': 'AgriVision - မြန်မာလယ်သမားများအတွက် စမတ်စိုက်ပျိုးရေးစနစ်',
        'is_landing': True,
    }
    return render(request, 'landing/index.html', context)

@login_required
def dashboard(request):
    """
    Dashboard view - main entry point after login
    """
    context = {
        'page_title': 'AgriVision Dashboard',
        'user': request.user,
    }
    return render(request, 'landing/dashboard.html', context)

def set_language(request):
    """
    Set the language for the user
    """
    language = request.GET.get('language') or request.POST.get('language')
    next_url = request.GET.get('next', '/')
    
    if language and language in dict(settings.LANGUAGES).keys():
        activate(language)
        request.session['django_language'] = language
        response = redirect(next_url)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language)
        return response
    return redirect(next_url)