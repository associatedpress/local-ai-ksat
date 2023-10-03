from django.urls import path

from . import views

app_name = 'dashboard'
urlpatterns = [
    #If you plan on using hrefs in html to a specific url pattern you have to use the app_name and url pattern name, look at templates/accounts/passwordchangesuccess.html as an example
    path('', views.dashboard_view, name='index'), 
    path('search/', views.search_view, name='search'),
    path('transcript_msg_receiver', views.trint_webhook_receiver, name='transcript_msg_receiver'),
    path('recording/update_file_title', views.update_file_title, name='update_file_title'),
    path('recording/update_prompt_selection', views.update_prompt_selection, name='update_prompt_selection'),
    path('recording/<int:pk>/<int:user_id>/trigger_summarization', views.trigger_summarization, name='trigger_summarization'),
    path('recording/<int:pk>/delete', views.delete_recording, name='delete_recording'),
    path('recording/<int:pk>/hold', views.hold_recording, name='hold_recording'),
]
