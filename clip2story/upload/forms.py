from django import forms
from dashboard.models import Recording

#
# Created so that the form associated to the Recording model can have hidden fields.
# This allows the ability to create a database entry for the Recording without user intervention when they upload a video.
#
class UploadFileForm(forms.ModelForm):
    class Meta:
        model  = Recording

        #Specific fields I want to populate when uploading a video
        fields = (
            'title', 
            'upload_filename',
            'upload_filetype', 
            'status_text', 
            'status_state',
            'hold_indefinitely',
            'uploaded_by_user',
              )
        
        #Specifying that all of those fields should be hidden
        widgets = {
            'title': forms.HiddenInput(),
            'upload_filename': forms.HiddenInput(),
            'upload_filetype': forms.HiddenInput(),
            'status_text': forms.HiddenInput(),
            'status_state': forms.HiddenInput(),
            'hold_indefinitely': forms.HiddenInput(),
            'uploaded_by_user': forms.HiddenInput(),
        }

#
# Created so that the form associated to the Recording model can have hidden fields.
# This allows the ability to create a database entry for the Recording without user intervention when they import a video.
#
class ImportFileForm(forms.ModelForm):
    class Meta:
        model  = Recording

        #Specific fields I want to populate when uploading a video
        fields = (
            'title', 
            'status_text', 
            'status_state',
            'hold_indefinitely',
            'uploaded_by_user',
            'transcript_vendor_id',
            'imported',
              )
        
        #Specifying that all of those fields should be hidden
        widgets = {
            'title': forms.HiddenInput(),
            'status_text': forms.HiddenInput(),
            'status_state': forms.HiddenInput(),
            'hold_indefinitely': forms.HiddenInput(),
            'uploaded_by_user': forms.HiddenInput(),
            'transcript_vendor_id': forms.HiddenInput(),
            'imported': forms.HiddenInput()
        }