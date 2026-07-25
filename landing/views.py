from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
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
    Dashboard view - redirects to farm app dashboard
    """
    print("="*60)
    print("🔴 LANDING DASHBOARD: REDIRECTING TO FARMS DASHBOARD")
    print("   Going to: /app/")
    print("="*60)
    return redirect('farms:dashboard')

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

def logout_view(request):
    """
    Custom logout view that redirects to landing page with a success message
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully. See you soon! 👋')
    return redirect('landing:landing')