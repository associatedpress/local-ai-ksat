# Generated by Django 4.2.3 on 2023-07-21 18:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='globalconfig',
            name='arc_api_key',
            field=models.TextField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='globalconfig',
            name='arc_api_url',
            field=models.URLField(blank=True, help_text='URL for the Arc website being used with an api slapped at the front, for example: api.[YOUR_DOMAIN] ', null=True),
        ),
        migrations.AddField(
            model_name='recording',
            name='arc_uuid',
            field=models.TextField(blank=True, default=None, null=True),
        ),
        migrations.AlterField(
            model_name='recording',
            name='status_text',
            field=models.TextField(),
        ),
    ]
