from django.contrib import admin
from .models import *

# Register models to appear in the admin page so we can manipulate the database holding these models.
admin.site.register(GlobalConfig)
admin.site.register(Recording)
admin.site.register(Prompt)