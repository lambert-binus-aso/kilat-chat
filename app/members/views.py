from django.shortcuts import render
from django.shortcuts import redirect
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from .forms import SignupForm, LoginForm
from .models import User


def landing(request):
    return render(request, 'members/landing.html')


def welcome(request):
    return render(request, 'members/welcome.html')


# Presentation-only routes. Authentication and AI API calls will be connected later.
@ensure_csrf_cookie
def login_page(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            request.session.flush()
            request.session['user_id'] = form.user.pk
            return JsonResponse({'ok': True, 'redirect': '/chat/'})
        return JsonResponse({'ok': False, 'errors': form.errors.get_json_data()}, status=400)
    return render(request, 'members/login.html')


@ensure_csrf_cookie
def signup_page(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            request.session.flush()
            request.session['user_id'] = user.pk
            return JsonResponse({'ok': True, 'redirect': '/chat/'}, status=201)
        return JsonResponse({'ok': False, 'errors': form.errors.get_json_data()}, status=400)
    return render(request, 'members/signup.html')


def logout_page(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=405)
    request.session.flush()
    return JsonResponse({'ok': True, 'redirect': '/login/'})


def current_user(request):
    user_id = request.session.get('user_id')
    user = User.objects.filter(pk=user_id).first() if user_id else None
    if user is None:
        return JsonResponse({'authenticated': False}, status=401)
    return JsonResponse({'authenticated': True, 'id': user.pk, 'username': user.username, 'email': user.email})


@ensure_csrf_cookie
def new_chat_page(request):
    return render(request, 'members/new_chat.html')


def conversation_page(request, conversation_id='neural-networks'):
    return render(request, 'members/conversation.html')
