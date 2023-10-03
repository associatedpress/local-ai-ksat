from django.db.models.signals import post_save, pre_delete, post_delete, post_migrate
from django.dispatch import receiver
from .models import Recording, GlobalConfig
from .utils import generate_download_url, upload_trint, delete_video, generate_delete_url, RecordingStatus, grab_trint_transcript

#
# This function runs any time a Recording model instance is saved to. There are lots of different scenarios where this function is triggered and are specified below.
#
@receiver(post_save, sender=Recording)
def recording_post_save(sender, instance, created, **kwargs):

    # The Recording instance was just created and it has a filename (meaning this Recording was created using the upload page and the video is on cloud storage).
    # Download the video into memory using a signed url and send the video to Trint, the status of the Recording will be updated by the upload function.
    if(created and instance.upload_filename is not None and instance.imported is False):

        signed_url = generate_download_url(instance)
        if signed_url is not None:
            upload_trint(instance, signed_url) 

    # The Recording instance was just created and the status state is already at verified meaning it was imported from a Trint transcript already in Trint
    # Grab the transcript and save it to the recording instance
    if(created and instance.status_state == RecordingStatus.VERIFIED.value):
        grab_trint_transcript(instance)
        instance.transcript_url = f"https://app.trint.com/editor/{instance.transcript_vendor_id}"
        instance.save()


#
# This function runs any time a Recording model is about to be deleted. It deletes the associated video on cloud storage before deleting the instance.
#
@receiver(pre_delete, sender=Recording)
def recording_pre_delete(sender, instance, **kwargs):

    # Only need to delete videos in GCP if they were uploaded through our app
    if instance.imported is False:
        signed_url = generate_delete_url(instance)
        if signed_url is not None:
            delete_video(signed_url)

#
# This function runs after a migration is applied on GlobalConfig. It makes sure that a GlobalConfig always exists after a migration.
#
@receiver(post_migrate, sender=GlobalConfig)
def recording_post_migrate(sender, **kwargs):
    from .models import GlobalConfig
    if GlobalConfig.objects.count() == 0:
        GlobalConfig.objects.create()

#
# This functions runs after a deletion of a GlobalConfig object occurs. It makes sure that a GlobalConfig always exists during runtime even if someone deletes the only one.
#
@receiver(post_delete, sender=GlobalConfig)
def recording_post_delete(sender, **kwargs):
    from .models import GlobalConfig
    if GlobalConfig.objects.count() == 0:
        GlobalConfig.objects.create()
        