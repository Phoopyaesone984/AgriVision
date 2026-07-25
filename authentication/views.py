from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm

def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect("farms:dashboard")  # 👈 CHANGED TO FARMS DASHBOARD
    else:
        form = RegisterForm()
    return render(request, "register.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect("farms:dashboard")  # 👈 CHANGED TO FARMS DASHBOARD
        else:
            print(form.errors)
    else:
        form = LoginForm()
    return render(request, "login.html", {"form": form})

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("landing:landing")

@login_required
def dashboard_view(request):
    # 👈 THIS IS THE AUTH DASHBOARD - WE DON'T NEED IT
    # We'll redirect to farms dashboard instead
    return redirect("farms:dashboard")