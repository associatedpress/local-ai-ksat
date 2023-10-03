import json
import asyncio
from google.cloud import logging

from django.shortcuts               import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models     import User
from django.views.decorators.csrf   import csrf_exempt
from django.views.decorators.http   import require_POST
from django.http                    import HttpResponse
from django.http                    import JsonResponse
from django.db.models               import Q
from django.shortcuts               import render
from .models                        import Recording, Prompt
from .utils                         import grab_trint_transcript, generate_summary, RecordingStatus

# Default dashboard view. Passes files, prompts, and the default found_results variables to the dashboard template
# found_results is set to True because it is a search dependent variable in the dashboard template and the default view is not executing a search
# Return: the dashboard template with the variables included
@login_required #Django login system 
def dashboard_view(request):
    files   = Recording.objects.order_by('-recording_id')
    prompts = Prompt.objects.all()
    return render(request, 'dashboard/index.html', {'files': files, 'found_results': True, 'prompts': prompts})

# Search view, used when a search is executed on the dashboard. Passes files, prompts, and a found_results variable that gets set to True if files is not empty
# Return: the dashboard template with the variables included
@login_required #Django login system
def search_view(request):
    search_query = request.GET.get('search_query', '')
    files   = Recording.objects.filter(Q(title__icontains=search_query))
    prompts = Prompt.objects.all()
    context = {'files': files, 'search_query': search_query, 'found_results': bool(files), 'prompts': prompts}
    return render(request, 'dashboard/index.html', context)

# delete_recording view is triggered by a get request from the dashboard template
# It passes in a primary key of the recording wanting to be deleted and uses that to do a lookup and then delete the video
# Return: redirect to the dashboard page to regenerate the template with the updated info
@login_required #Django login system
def delete_recording(request, pk):
    recording_instance = get_object_or_404(Recording, pk=pk)
    recording_instance.delete()
    return redirect('dashboard:index')

# hold_recording view is triggered by a get request from the dashboard template
# It passes in a primary key of the recording wanting to be marked as held on unheld and uses that to do a lookup and then invert the video holds status
# Return: redirect to the dashboard page to regenerate the template with the updated info
@login_required #Django login system
def hold_recording(request, pk):
    recording_instance = get_object_or_404(Recording, pk=pk)
    recording_instance.hold_indefinitely = not recording_instance.hold_indefinitely
    recording_instance.save()
    return redirect('dashboard:index')

# update_file_title view is triggered by a post request from the dashboard template
# The post request stores the primary key and the title inside of the request body. The function grabs these variables and uses them to do a lookup and change the title
# Return: a JSON response object indicating if the post request was successful or not
@login_required #Django login system
@require_POST
def update_file_title(request):
    file_id = request.POST.get('file_id')
    value = request.POST.get('value')

    try:
        file = Recording.objects.get(recording_id=file_id)
        setattr(file, "title", value)
        file.save()
        return JsonResponse({'success': True})
    except Recording.DoesNotExist:
        pass

    return JsonResponse({'success': False})

# update_prompt_selection view is triggered by a post request from the dashboard template
# The post request stores the primary key and the prompt selection inside the request body. The function grabs these variables and uses them to do a lookup of the recording object and prompt object to set the prompt key
# Return: a JSON response object indicating if the post request was successful or not
@login_required #Django login system
@require_POST
def update_prompt_selection(request):
    prompt_selected = request.POST.get('selection')
    recording_id = request.POST.get('file_id')

    try:
        prompt = Prompt.objects.get(prompt_type=prompt_selected)
        file = Recording.objects.get(recording_id=recording_id)
        setattr(file, "prompt_key", prompt)
        file.save()
        return JsonResponse({'success': True})
    except Recording.DoesNotExist:
        pass
    except Prompt.DoesNotExist:
        pass

    return JsonResponse({'success': False})

# trigger_summarization view is triggered by a get request from the dashboard template
# It passes a primary key to grab the recording instance and a user_id of the user asking for the summary to be generated to save that to the recording instance
# Return: redirect to the dashboard page to regenerate the template with the updated info
@login_required
def trigger_summarization(request, pk, user_id):
    recording_instance = get_object_or_404(Recording, pk=pk)
    prompt = recording_instance.prompt_key

    recording_instance.summary_by_user = User.objects.get(id=user_id)
    recording_instance.save()

    asyncio.run(generate_summary(recording_instance, prompt))
    
    return redirect('dashboard:index')

# trint_webhook_receiver view is triggered by a post request sent by Trint
# The post body contains a json payload that contains a Trint id which is used for a Recording lookup as well as the event type to mark the recording accordingly.
# For more information on the payload: https://dev.trint.com/reference/events
# Return: HTTP response indicating success or not on grabbing the transcript
@csrf_exempt  #Does not require a CSRF cookie since the website POSTing to this URL will not be able to send a CSRF cookie
@require_POST #This is to ensure that no other request types are accepted since a POST request is what we are expecting
def trint_webhook_receiver(request):
    logging_client = logging.Client()
    logger = logging_client.logger("trint_webhook_receiver")
    
    try:
        trint_msg = json.loads(request.body) #The trint request's payload is json
    except:
        pass

    logger.log_text(json.dumps(trint_msg))

    try:
        # We may get Trint requests on transcriptions generated outside of our program.
        # For that reason its not a guarantee that there is a database entry for it, if there is no database entry, we can ignore the request
        recording_instance = Recording.objects.get(transcript_vendor_id=trint_msg['transcriptId']) 

        # By getting to this point, the Trint request was for a video in our database, figure out which request it was for and then update the text accordingly
        if trint_msg['eventType'] == "TRANSCRIPT_COMPLETE":
            recording_instance.status_state = RecordingStatus.TRANSCRIBED.value
            recording_instance.save()
        elif trint_msg['eventType'] == "TRANSCRIPT_VERIFIED":
            recording_instance.status_state = RecordingStatus.VERIFIED.value
            grab_trint_transcript(recording_instance)
            recording_instance.save()

        return HttpResponse("Database entry found, status text updated and potentially the transcript is as well", content_type="text/plain")
    except Recording.DoesNotExist:
        #If it does not exist, the transcript was most likely generated outside of the app and therefore we don't need to do anything
        return HttpResponse("Trint entry does not exist in database", content_type="text/plain")