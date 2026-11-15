from django.shortcuts import render
from django.shortcuts import redirect
from .forms import SignupForm


def landing(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('welcome')
    else:
        form = SignupForm()

    return render(request, 'members/landing.html', {'form': form})


def welcome(request):
    return render(request, 'members/welcome.html')
