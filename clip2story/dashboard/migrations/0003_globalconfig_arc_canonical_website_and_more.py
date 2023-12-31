# Generated by Django 4.2.3 on 2023-07-25 18:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0002_globalconfig_arc_api_key_globalconfig_arc_api_url_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='globalconfig',
            name='arc_canonical_website',
            field=models.TextField(blank=True, help_text='The main website where the draft article will live inside composer, this is not the same thing as circulation.', null=True),
        ),
        migrations.AlterField(
            model_name='globalconfig',
            name='arc_api_key',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='recording',
            name='status_state',
            field=models.IntegerField(default=0, help_text='0=Nothing, 1=Uploading, 2=Transcribing, 3=Trascribed, 4=Verified, 5=Summarizing, 6=Summarized, 7=Generating tags, 8=Tags generated, 9=In ARC, 10=Error'),
        ),
    ]
