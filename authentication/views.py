from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .forms import RegisterForm,LoginForm

def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect("dashboard")

    else:
        form = RegisterForm()

    return render(request, "register.html", {
        "form": form
    })

def login_view(request):

    if request.method == "POST":
        form = LoginForm(
            request,
            data=request.POST
        )

        print("POST received")   # test

        if form.is_valid():
            print("FORM VALID")   # test

            user = form.get_user()

            login(request, user)

            print("USER LOGIN:", user.username)  # test

            messages.success(
                request,
                "Login successful!"
            )

            return redirect("dashboard")

        else:
            print(form.errors)   # show errors

    else:
        form = LoginForm()

    return render(
        request,
        "login.html",
        {
            "form": form
        }
    )

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("landing:landing")

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def dashboard_view(request):
    context = {
        "stats": {
            "total_fields": 6,
            "active_crops": 4,
            "revenue": "3,240",
            "pending_tasks": 3,
        }
    }
    return render(request, "dashboard.html", context)