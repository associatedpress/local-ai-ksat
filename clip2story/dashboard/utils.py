import requests, datetime, json, warnings, os
from enum import Enum
from asgiref.sync import sync_to_async

from .models import GlobalConfig

from google.cloud import storage
import openai, tiktoken

# An enumeration class to make it easier to tell in the code what state the Recording state is being set to
class RecordingStatus(Enum):
    #0=Nothing, 1=Uploading, 2=Transcribing, 3=Trascribed, 4=Verified, 5=Summarizing, 6=Summarized, 7=Generating tags, 8=Tags generated, 9=In ARC, 10=Error
    NOTHING        = 0
    UPLOADING      = 1
    TRANSCRIBING   = 2
    TRANSCRIBED    = 3
    VERIFIED       = 4
    SUMMARIZING    = 5
    SUMMARIZED     = 6
    GENERATE_TAGS  = 7
    TAGS_GENERATED = 8
    IN_ARC         = 9
    ERROR          = 10

# Function takes the given download signed url and downloads the video into RAM.
# Takes that video and then turns around and uploads it to Trint.
# Updates the associated Recording instance with the status of the Trint upload
# Return: function does not return anything
def upload_trint(recording_instance, download_signed_url):
    global_config = GlobalConfig.objects.first()

    signed_url_response = requests.get(download_signed_url)

    # If the trint api key is set, continue
    if global_config.trint_api_key is not None:
        # Downloading the video from the signed_url worked and now it can be sent to Trint
        if signed_url_response.status_code == 200:
            trint_url = f"https://upload.trint.com/?filename={recording_instance.upload_filename}"

            trint_headers = {
                "accept": "application/json",
                "api-key": global_config.trint_api_key,
                "content-type": recording_instance.upload_filetype
            }

            trint_response = requests.post(trint_url, headers=trint_headers, data=signed_url_response.content)

            # The video uploaded to Trint with no issues and the id can be pulled from the response and placed in the Recording model
            if trint_response.status_code == 200:
                recording_instance.transcript_vendor_id = trint_response.json()["trintId"]
                recording_instance.transcript_url = f"https://app.trint.com/editor/{recording_instance.transcript_vendor_id}"

                recording_instance.status_state = RecordingStatus.TRANSCRIBING.value
                recording_instance.save()
            else:
                recording_instance.status_text = f"Trint upload error: {trint_response.text}"
                recording_instance.status_state = RecordingStatus.ERROR.value
                recording_instance.save()

        else:
            recording_instance.status_text = f"Signed-URL download error: {signed_url_response.text}"
            recording_instance.status_state = RecordingStatus.ERROR.value
            recording_instance.save()

    else:
        recording_instance.status_text = "Trint upload error: Trint API key not set"
        recording_instance.status_state = RecordingStatus.ERROR.value
        recording_instance.save()
        warnings.warn("Trint API key is not configured in Django Admin, operation will not execute", RuntimeWarning)


# Function takes in the Recording instance and grabs the Trint id to generate an export transcript request.
# It takes the request's response and grabs the text from the exported file and plops it into the Recording instance
# Return: function does not return anything
def grab_trint_transcript(recording_instance):
    global_config = GlobalConfig.objects.first()

    # If the trint api key is set, continue
    if global_config.trint_api_key is not None:
        trint_url = f"https://api.trint.com/export/text/{recording_instance.transcript_vendor_id}"
        trint_header = {
            "accept": "application/json",
            "api-key": global_config.trint_api_key
        }

        trint_response = requests.get(trint_url, headers=trint_header)

        if trint_response.status_code == 200:
            trint_txt_url = trint_response.json()["url"] #Trint will give a url to where they exported the transcript to

            trint_txt_response = requests.get(trint_txt_url)

            if trint_txt_response.status_code == 200:
                recording_instance.transcript = trint_txt_response.text
                recording_instance.save()
    else:
        recording_instance.status_text = "Trint export error: Trint API key not set"
        recording_instance.status_state = RecordingStatus.ERROR.value
        recording_instance.save()
        warnings.warn("Trint API key is not configured in Django Admin, operation will not execute", RuntimeWarning)

# Function gets the most recent metadata for the transcripts on Trint up to a certain amount set in the global config.
# Return: a JSON response with the transcript metadata or None if an error occurred
def get_recent_trint_transcriptions():
    global_config = GlobalConfig.objects.first()

    if global_config.trint_api_key is not None:
        trint_url = f"https://api.trint.com/transcripts?limit={global_config.recent_transcript_limit}&skip=0"
        trint_header = {
            "accept": "application/json",
            "api-key": global_config.trint_api_key
        }

        response = requests.get(trint_url, headers=trint_header)

        if response.status_code == 200:
            return response.json()
        else:
            return None
    else:
        warnings.warn("Trint API key is not configured in Django Admin, operation will not execute", RuntimeWarning)

# Function generates a download signed-url for the associated video that is stored on GCP
# Return: the URL as a string or returns None if an error occurred
def generate_download_url(recording_instance):
    global_config = GlobalConfig.objects.first()

    # Ensure that the environment variable for the GCP credentials is set as well as the bucket name before generating a URL, otherwise return None
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") is not None and global_config.bucket_name is not None:

        # Initiate a client object for GCP with the service account credentials key stored in the certs folder
        client = storage.Client() # Have to make sure that the environment variable GOOGLE_APPLICATION_CREDENTIALS is a path to the service account credentials file

        # Specify which signed url "bucket" the files will live in
        bucket = client.bucket(global_config.bucket_name)

        # Let GCP know what the filename is for the video we're going to download
        blob = bucket.blob(f"videos/{recording_instance.upload_filename}")

        # Generate the signed url given all the above info that lasts for as long as the timeout value is set to (5/22/23 it is 30 minutes)
        signed_url = blob.generate_signed_url(
            version='v4',
            expiration=datetime.timedelta(minutes=global_config.url_timeout_val), 
            method='GET', 
            )
        
        return signed_url
    
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") is None:
        warnings.warn("GOOGLE_APPLICATION_CREDENTIALS environment variable not set, Signed-URL generation will not work", RuntimeWarning)

    if global_config.bucket_name is None:
        warnings.warn("Bucket name is not configured in Django Admin, signed-url generation will not execute", RuntimeWarning)

    return None #Indicate to the caller than an error occurred


# Function generates a upload signed-url for putting the video being summarized onto GCP
# Return: the URL as a string or returns None if an error occurred
def generate_upload_url(request):
    global_config = GlobalConfig.objects.first()

    # Ensure that the environment variable for the GCP credentials is set as well as the bucket name before generating a URL, otherwise return None
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") is not None and global_config.bucket_name is not None:

        # Initiate a client object for GCP with the service account credentials key stored in the certs folder
        client = storage.Client() # Have to make sure that the environment variable GOOGLE_APPLICATION_CREDENTIALS is a path to the service account credentials file

        # Specify which signed url "bucket" the files will live in
        bucket = client.bucket(global_config.bucket_name)
        
        # Let GCP know what the filename is for the video we're going to upload
        blob = bucket.blob(f"videos/{json.loads(request.body)['fileName']}")

        # Generate the signed url given all the above info that lasts for as long as the timeout value is set to (5/31/23 it is 24 hours)
        signed_url = blob.generate_signed_url(
            version='v4',
            expiration=datetime.timedelta(minutes=global_config.url_timeout_val), 
            method='PUT', # The URL itself expects PUT to replace the data at the link
            content_type=f"{json.loads(request.body)['fileType']}" # Should be in the format of "video/mp4" if its an mp4 file
        )

        return signed_url
    
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") is None:
        warnings.warn("GOOGLE_APPLICATION_CREDENTIALS environment variable not set, Signed-URL generation will not work", RuntimeWarning)

    if global_config.bucket_name is None:
        warnings.warn("Bucket name is not configured in Django Admin, signed-url generation will not execute", RuntimeWarning)

    return None #Indicate to the caller than an error occurred

# Function generates a delete signed-url for removing the recording instance's associated GCP file
# Return: the URL as a string or returns None if an error occurred
def generate_delete_url(recording_instance):
    global_config = GlobalConfig.objects.first()

    # Ensure that the environment variable for the GCP credentials is set as well as the bucket name before generating a URL, otherwise return None
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") is not None and global_config.bucket_name is not None:

        # Initiate a client object for GCP with the service account credentials key stored in the certs folder
        client = storage.Client() # Have to make sure that the environment variable GOOGLE_APPLICATION_CREDENTIALS is a path to the service account credentials file

        # Specify which signed url "bucket" the files will live in
        bucket = client.bucket(global_config.bucket_name)

        # Let GCP know what the filename is for the video we're going to download
        blob = bucket.blob(f"videos/{recording_instance.upload_filename}")

        # Generate the signed url given all the above info that lasts for as long as the timeout value is set to (5/22/23 it is 30 minutes)
        signed_url = blob.generate_signed_url(
            version='v4',
            expiration=datetime.timedelta(minutes=global_config.url_timeout_val), 
            method='DELETE', 
            )
        
        return signed_url
    
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") is None:
        warnings.warn("GOOGLE_APPLICATION_CREDENTIALS environment variable not set, Signed-URL generation will not work", RuntimeWarning)

    if global_config.bucket_name is None:
        warnings.warn("Bucket name is not configured in Django Admin, signed-url generation will not execute", RuntimeWarning)

    return None #Indicate to the caller than an error occurred

# Function deletes the video specified using the pre-generated signed-url
# Return: function does not return anything
def delete_video(signed_url):
    response = requests.delete(signed_url)

    if response.status_code != 204:
        warnings.warn(f"Object deletion encountered error, HTTP Status Code: {response.status_code}", RuntimeWarning)

# Function generates an ANS json schema to be passed to ARC.
# To understand ANS, consult https://github.com/washingtonpost/ans-schema
# Return: Json object
async def generate_ANS(recording_instance):
    global_config = await sync_to_async(GlobalConfig.objects.first)()

    ANS_VERSION = "0.10.7"
    ANS_TYPE    = "story"
    recording_tags = json.loads(recording_instance.tags)
    ans_tags = []
    ans_dictionary = {}

    # The formatting of the tags is slightly different than what is stored in the database so a conversion will be performed
    tag_count = 0
    for tag in recording_tags:
        tag_json = {"_id" : f"{tag_count}",
                    "text": tag}
        ans_tags.append(tag_json)
        tag_count += 1

    

    ans_dictionary["type"]              = ANS_TYPE
    ans_dictionary["version"]           = ANS_VERSION
    ans_dictionary["canonical_website"] = global_config.arc_canonical_website
    ans_dictionary["headlines"]         = {"basic"   : f"{recording_instance.title} CLIP2STORY GENERATED"} # set the default headline to the recordings title
    ans_dictionary["taxonomy"]          = {"tags": ans_tags}
    ans_dictionary["content_elements"]  = [{"_id"     : "0",
                                           "type"    : "text",
                                           "content" : recording_instance.summary}]

    return ans_dictionary

async def export_ARC(recording_instance):
    global_config = await sync_to_async(GlobalConfig.objects.first)()
    ARC_TYPE = "story"

    if global_config.arc_api_key is not None and global_config.arc_api_url is not None:
        ans_json = await generate_ANS(recording_instance)
        
        # if there is no Arc id, this will be the first time we send this document to ARC. Use the document create endpoint
        if recording_instance.arc_uuid is None or len(recording_instance.arc_uuid) == 0:
            arc_create_url = f"{global_config.arc_api_url}/draft/v1/{ARC_TYPE}"
            arc_create_headers = {
                "Content-Type" : "application/json", 
                "Authorization": f"Bearer {global_config.arc_api_key}"
            }

            response = requests.post(arc_create_url, headers=arc_create_headers, json=ans_json)

            if response.status_code == 200:
                response_json = response.json()
                recording_instance.arc_uuid = response_json["id"]

                #Generate the ARC url by stripping the api from the arc url to get the main url and then inserting ARC UUID into the url
                recording_instance.summary_url = f"{global_config.arc_api_url.replace('api.', '')}/composer/edit/{recording_instance.arc_uuid}/"

                recording_instance.status_state = RecordingStatus.IN_ARC.value
                recording_instance.status_text = "Exported to ARC"
                await sync_to_async(recording_instance.save)()
            elif any(response.status_code == code for code in [400, 429, 500]):
                response_json = response.json()
                recording_instance.status_state = RecordingStatus.ERROR.value

                if response_json['error_message']:
                    recording_instance.status_text  = f"ARC export error: {response_json['error_message']}"
                else:
                    recording_instance.status_text  = f"ARC export error: {response_json['error_code']}"

                await sync_to_async(recording_instance.save)()
            else:
                recording_instance.status_state = RecordingStatus.ERROR.value
                recording_instance.status_text  = f"ARC export error: {response.text}"
                await sync_to_async(recording_instance.save)()

        # if there is an Arc id, someone is regenerating the summary and the document on ARC should use the revision endpoint
        else:
            arc_create_url = f"{global_config.arc_api_url}/draft/v1/{ARC_TYPE}/{recording_instance.arc_uuid}/revision/draft"
            arc_create_headers = {
                "Content-Type" : "application/json", 
                "Authorization": f"Bearer {global_config.arc_api_key}"
            }
            arc_revision_json = {"document_id": f"{recording_instance.arc_uuid}",
                                 "ans": ans_json,
                                 "type": "DRAFT"}
            
            response = requests.put(arc_create_url, headers=arc_create_headers, json=arc_revision_json)
            response_json = response.json()

            if response.status_code == 200:
                recording_instance.status_state = RecordingStatus.IN_ARC.value
                recording_instance.status_text = "Exported to ARC"
                await sync_to_async(recording_instance.save)()
            else:
                recording_instance.status_state = RecordingStatus.ERROR.value
                recording_instance.status_text  = f"ARC export error: {response_json['error_code']}"
                await sync_to_async(recording_instance.save)()
    else:
        recording_instance.status_text = "ARC export error: ARC API key or ARC URL not set"
        recording_instance.status_state = RecordingStatus.ERROR.value
        await sync_to_async(recording_instance.save)()
        warnings.warn("ARC API key or ARC URL are not configured in Django Admin, operation will not execute", RuntimeWarning)

# Function enables asynchronous generation of tags for a given recording instance that is passed to the function using the summary saved to the recording instance
# Return: function does not return anything
async def generate_tags(recording_instance):
    global_config =  await sync_to_async(GlobalConfig.objects.first)()

    if global_config.openai_api_key is not None:
        openai.api_key = global_config.openai_api_key

    recording_instance.status_state = RecordingStatus.GENERATE_TAGS.value
    await sync_to_async(recording_instance.save)()

    if recording_instance.summary is not None and len(recording_instance.summary) > 0:

        # Allow for a custom tag prompt but hard code the format
        if global_config.tag_prompt is not None:
            gpt_prompt = global_config.tag_prompt + "\nGiven the following news summary, please generate a comma-delimited list of tags:"
        else:
            gpt_prompt = """You are an AI tasked with generating tags for a news story based on a text summary. You are looking for important persons, places, things, concepts/subjects
                            Given the following news summary, please generate a comma-delimited list of tags:"""

        # Convert the summary into the tokens that OpenAI uses.
        encoding = tiktoken.get_encoding("cl100k_base")
        transcript_tokenized = encoding.encode(recording_instance.summary)

        # Divide up the summary into 2000 token chunks 
        chunk_size = 2000
        num_chunks = len(transcript_tokenized) // chunk_size + 1
        tags = list()

        # Generate tags for each 2000 token chunk of the summary
        for i in range(num_chunks):
            start = i * chunk_size
            end = min((i + 1) * chunk_size, len(transcript_tokenized))
            chunk = transcript_tokenized[start:end]
            
            try:
                tags += openai.ChatCompletion.create(
                    model='gpt-3.5-turbo',
                    messages=[
                        {"role": "system", "content": gpt_prompt},
                        {"role": "user", "content": "News Story: " + encoding.decode(chunk)},
                        {"role": "user", "content": "Tags: "}
                    ],
                    temperature=0,
                    max_tokens=1000
                ).choices[0].message['content'].split(',')

                recording_instance.status_text  = "In Progress"
                recording_instance.status_state = RecordingStatus.TAGS_GENERATED.value
            except Exception as e:
                recording_instance.status_text = f"Tag generation error: {e}" #If API key is not set, OpenAI will make it known here
                recording_instance.status_state = RecordingStatus.ERROR.value
                break

        recording_instance.tags = json.dumps(tags)

        await sync_to_async(recording_instance.save)()

        await export_ARC(recording_instance)
    else:
        recording_instance.status_text = f"Tag generation error: No summary."
        recording_instance.status_state = RecordingStatus.ERROR.value
        await sync_to_async(recording_instance.save)()

# Function enables asynchronous generation of a summary for a given recording instance that is passed to the function using the transcript saved to the recording instance
# Return: function does not return anything
async def generate_summary(recording_instance, prompt, request=None):
    global_config =  await sync_to_async(GlobalConfig.objects.first)()

    if global_config.openai_api_key is not None:
        openai.api_key = global_config.openai_api_key

    recording_instance.status_state = RecordingStatus.SUMMARIZING.value
    await sync_to_async(recording_instance.save)()

    if prompt is not None:
        gpt_prompt = prompt.prompt_text

        # Convert the transcript into the tokens that OpenAI uses.
        encoding = tiktoken.get_encoding("cl100k_base")
        transcript_tokenized = encoding.encode(recording_instance.transcript)

        # Divide up the transcript into 2000 token chunks 
        chunk_size = 2000
        num_chunks = len(transcript_tokenized) // chunk_size + 1
        summary = ""

        # Summarize each chunk of 2000 tokens and add the summaries together
        for i in range(num_chunks):
            start = i * chunk_size
            end = min((i + 1) * chunk_size, len(transcript_tokenized))
            chunk = transcript_tokenized[start:end]
            
            try:
                summary += " " + openai.ChatCompletion.create(
                    model='gpt-3.5-turbo',
                    messages=[
                        {"role": "system", "content": gpt_prompt},
                        {"role": "user", "content": encoding.decode(chunk)}
                    ],
                    temperature=0,
                    max_tokens=1000
                ).choices[0].message['content']

                recording_instance.status_text  = "In Progress"
                recording_instance.status_state = RecordingStatus.SUMMARIZED.value
                if request is not None:
                    recording_instance.summary_by_user = request.user
            except Exception as e:
                recording_instance.status_text = f"Summarization error: {e}" #If API key is not set, OpenAI will make it known here
                recording_instance.status_state = RecordingStatus.ERROR.value
                recording_instance.summary_by_user = None
                break

        # Save the summary to the recording instance if nothing went wrong during chunking
        if recording_instance.status_state != RecordingStatus.ERROR.value:
            recording_instance.summary = summary

        await sync_to_async(recording_instance.save)()

        await generate_tags(recording_instance)

    else:
        recording_instance.status_text = f"Summarization error: Prompt type for Recording not set."
        recording_instance.status_state = RecordingStatus.ERROR.value
        await sync_to_async(recording_instance.save)()