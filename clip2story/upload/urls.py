from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'upload'
urlpatterns = [
    #Django login system
    path('', login_required(views.UploadView.as_view()), name='upload'),
    #Django login system
    path('import/', login_required(views.ImportView.as_view()), name='import'),
    #Django login system
    path('signed-url/', login_required(views.SignedURLView.as_view()), name='signed-url')
]