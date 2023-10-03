from pathlib import Path

from django.urls                    import reverse
from django.http                    import HttpResponse, JsonResponse
from django.views                   import generic

from dashboard.models import Recording
from dashboard.utils  import generate_upload_url, get_recent_trint_transcriptions

from .forms import UploadFileForm, ImportFileForm

BASE_DIR = Path(__file__).parents[1]

#
#
#   NOTE: You have to set a CORS policy for the GCP bucket that your signed url is going to for the upload to work properly
#
#
# Custom view to generate an upload signed-url which is triggered by a post request from the upload template
# Return: Json object with the signed url if successful, Http object if an error occurred generating the signed-url
class SignedURLView(generic.View):
    def post(self, request, *args, **kwargs):
        signed_url = generate_upload_url(request)
        if signed_url is not None:
            return JsonResponse({"url": signed_url})
        else:
            return HttpResponse("Error in generating upload url, check server warnings for more details", content_type="text/plain")

# Custom Upload view for generating the upload template. The template has a custom form for creating a recording object in a hidden to the user manner
class UploadView(generic.CreateView):
    template_name = "upload/file_upload.html"
    model = Recording
    form_class = UploadFileForm

    # upon form submission, send user back to dashboard
    def get_success_url(self):
        return reverse("dashboard:index") 

# Custom Import view for generating the import template. The template has a custom form for creating a recording object in a hidden to the user manner
# Also adds recent transcript data to the template.
class ImportView(generic.CreateView):
    template_name = "upload/file_import.html"
    model = Recording
    form_class = ImportFileForm

    # upon form submission, send user back to dashboard
    def get_success_url(self):
        return reverse("dashboard:index")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        transcripts_json = get_recent_trint_transcriptions()

        # Filter out transcripts that were created by the clip2story app so that all that is left are the ones uploaded by others
        filtered_transcripts = [transcript for transcript in transcripts_json if "CLIP2STORY" not in transcript['title']]

        context['transcripts'] = filtered_transcripts  

        return context