"""clip2story URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
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
import os
from django.contrib import admin
from django.urls import path, include

#Django login system
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path('', views.index),
    path('help/', views.help, name='help'),
    path('dashboard/', include('dashboard.urls')),
    path('upload/', include('upload.urls')),

    #Django login system
    path('accounts/login/', views.CustomLoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('accounts/logout/', views.logout_user, name='logout'),
    #path('accounts/passwordreset/', auth_views.PasswordResetView.as_view(template_name='accounts/passwordreset.html'), name='passwordreset'), #not fully implemented
    path('accounts/changepassword/', auth_views.PasswordChangeView.as_view(template_name='accounts/changepassword.html', success_url='/accounts/passwordchangesuccess/')),
    path('accounts/passwordchangesuccess/', auth_views.PasswordChangeDoneView.as_view(template_name='accounts/passwordchangesuccess.html')),

    path('admin/', admin.site.urls),
]

if os.getenv('DEBUG', 'False') == 'True':
    urlpatterns.append(
        path('__debug__/', include('debug_toolbar.urls'))
    )
