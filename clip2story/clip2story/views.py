from django.shortcuts import redirect, render

#Django login system
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView

from dashboard.models import GlobalConfig

# default view gets triggered when a user visits the root domain
# Return: redirect to the dashboard if the user is logged in
@login_required #Django login system
def index(response):
    return redirect('/dashboard/')

# logout_user view triggered by visiting the logout url
# Return: redirect to the login page
def logout_user(request):
    logout(request) #Django login system
    return redirect('/accounts/login/')

# Custom login view that passes the global config object to the login template for grabbing the help text and displaying it on the login page
class CustomLoginView(LoginView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['global_config'] = GlobalConfig.objects.first()

        return context

# help view triggered when visiting the help page. Also passes the global config to grab the help text
def help(request):
    return render(request, 'help.html', {'global_config': GlobalConfig.objects.first()})