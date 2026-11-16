"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from members import views, api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing, name='landing'),
    path('welcome/', views.welcome, name='welcome'),
    path('login/', views.login_page, name='login'),
    path('signup/', views.signup_page, name='signup'),
    path('logout/', views.logout_page, name='logout'),
    path('api/me/', views.current_user, name='current_user'),
    path('api/models/', api.models_api, name='models_api'),
    path('api/chat/', api.chat_api, name='chat_api'),
    path('api/conversations/', api.conversations_api, name='conversations_api'),
    path('api/conversations/<int:conversation_id>/', api.conversation_api, name='conversation_api'),
    path('chat/', views.new_chat_page, name='new_chat'),
]
