from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.utils.translation import activate
from django.conf import settings

def landing_page(request):
    context = {
        'page_title': 'AgriVision - မြန်မာလယ်သမားများအတွက် စမတ်စိုက်ပျိုးရေးစနစ်',
        'is_landing': True,
    }
    return render(request, 'landing/index.html', context)

@login_required
def dashboard(request):
    return redirect('farms:dashboard')

def set_language(request):
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
    logout(request)
    messages.success(request, 'You have been logged out successfully. See you soon! 👋')
    return redirect('landing:landing')