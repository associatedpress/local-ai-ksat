from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe

from datetime import datetime, timedelta

class GlobalConfig(models.Model):
    config_id               = models.AutoField(primary_key=True)
    arc_api_url             = models.URLField(null=True, blank=True, help_text="URL for the Arc website being used with an api slapped at the front as is api.[DOMAIN_NAME].")
    arc_api_key             = models.TextField(null=True, blank=True)
    arc_canonical_website   = models.TextField(null=True, blank=True, help_text="The main website where the draft article will live inside composer, this is not the same thing as circulation.")
    openai_api_key          = models.CharField(max_length=255, null=True, blank=True)
    trint_api_key           = models.CharField(max_length=255, null=True, blank=True)
    url_timeout_val         = models.IntegerField(default=1440, help_text="How long before generated signed-urls expire in minutes") #bucket url timeout in minutes, default is 1440 which is 24 hours
    bucket_name             = models.CharField(null=True, blank=True, help_text="Name of the Google Cloud Platform bucket that the videos will be uploaded to")
    age_to_delete           = models.IntegerField(default=14, help_text="How many days after creating a recording will it be deleted automatically") # how many days to wait before deleting a clip, default is 2 weeks
    recent_transcript_limit = models.IntegerField(default=30, help_text="How many recent transcripts to grab from Trint for the import video page")
    help_messages_html      = models.TextField(null=True, blank=True, help_text="HTML help text for login and help page")
    tag_prompt              = models.TextField(null=True, blank=True, help_text="GPT Prompt for generating tags from summaries. Do not specify in your prompt how to format the tags.")

    # Function allows the help_message_html text field to contain html in it
    def help_message_as_html(self):
        return mark_safe(self.help_messages_html)

class Prompt(models.Model):
    # Function ensures that the prompt text does not exceed 500 words
    def validate_word_limit(value):
        word_limit = 500  
        words = value.split()
        if len(words) > word_limit:
            raise ValidationError(f"Exceeded word limit of {word_limit} words.")
        
    prompt_type             = models.TextField(primary_key=True, max_length=255)
    prompt_text             = models.TextField(validators=[validate_word_limit], help_text="500 word limit for prompts.") # Limit prompt length to 500 so there is no token issue

    def __str__(self):
        return f"{self.prompt_type} category prompt"

class Recording(models.Model):
    recording_id            = models.AutoField(primary_key=True)
    title                   = models.CharField(max_length=255)
    uploaded_dt             = models.DateTimeField('date uploaded', auto_now_add=True)
    upload_filename         = models.CharField(max_length=255, null=True, blank=True)
    upload_filetype         = models.CharField(max_length=255, null=True, blank=True)
    thumbnail_image         = models.ImageField(null=True, blank=True)
    status_text             = models.TextField()
    status_state            = models.IntegerField(default=0, help_text='0=Nothing, 1=Uploading, 2=Transcribing, 3=Trascribed, 4=Verified, 5=Summarizing, 6=Summarized, 7=Generating tags, 8=Tags generated, 9=In ARC, 10=Error') 
    prompt_key              = models.ForeignKey(   Prompt,       on_delete=models.SET_NULL, null=True, blank=True) # If the prompt associated with the recording is deleted, the key is set to null

    #Django login system
    uploaded_by_user        = models.ForeignKey(   User,         on_delete=models.CASCADE,             related_name='uploaded_by_user')  # If a user is deleted from the database, so will their recordings.
    summary_by_user         = models.ForeignKey(   User,         on_delete=models.SET_NULL, null=True, related_name='summary_by_user', blank=True) # If a user is deleted from the database, the summary id will be set to null for summaries they triggered
    
    transcript_vendor_id    = models.CharField(max_length=255, null=True, blank=True) # ID passed back by the transcription API to associate to the transcript
    arc_uuid                = models.TextField(null=True, blank=True, default=None) # ID passed back on initial ARC document creation from ARC
    transcript              = models.TextField(null=True, blank=True) 
    summary                 = models.TextField(null=True, blank=True)
    tags                    = models.JSONField(null=True, blank=True)
    transcript_url          = models.URLField(null=True, blank=True)
    summary_url             = models.URLField(null=True, blank=True)
    age                     = models.DateField(auto_now_add=True)
    hold_indefinitely       = models.BooleanField(default=False)

    imported                = models.BooleanField(default=False)

    # Function finds all the recordings older than the specified age in the GlobalConfig and deletes them if they do not have hold indefinitely enabled
    def remove_old_recordings():
        days_threshold = GlobalConfig.objects.first().age_to_delete
        threshold_date = datetime.now().date() - timedelta(days=days_threshold)

        remove_recording_list = Recording.objects.filter(age__lte=threshold_date, hold_indefinitely=False)

        remove_recording_list.delete()

    def __str__(self):
        return f"{self.title} uploaded by {self.uploaded_by_user}"
