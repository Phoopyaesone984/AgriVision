from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm, ProfileForm
from .models import Profile


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, "profile.html", {"profile": profile})


@login_required
def profile_edit(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("profile")
    else:
        form = ProfileForm(instance=profile)
    return render(request, "profile_edit.html", {"form": form})


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect("farms:dashboard")
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

            # 👑 Admin/Staff ဖြစ်ပါက Admin Dashboard ဆီသို့၊ ရိုးရိုး User ဖြစ်ပါက Farms Dashboard ဆီသို့
            if user.is_staff or user.is_superuser:
                return redirect("adminpanel:dashboard")
            return redirect("farms:dashboard")
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
    # 👑 Role စစ်ဆေးပြီး သက်ဆိုင်ရာ Dashboard ဆီ Redirect ပေးခြင်း
    if request.user.is_staff or request.user.is_superuser:
        return redirect("adminpanel:dashboard")
    return redirect("farms:dashboard")