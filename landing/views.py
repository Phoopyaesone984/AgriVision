# landing/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

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