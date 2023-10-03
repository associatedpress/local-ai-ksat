# Management Tasks and Cloud Jobs

We use standard [Django management commands][] to perform sundry tasks such as deleting old records.

Tasks that need to run regularly are deployed automatically as [Cloud Run Jobs][].

There is one managmement command under the `dashboard` app that deletes video recordings if they are older than a time window configured in GlobalConfig via the Django admin.

You can run this command locally as below:

```bash
pipenv shell
cd clip2story/
python manage.py delete_recordings
```

In production, we use a `delete-recordings` job to execute the management command every 30 minutes.

The important moving parts:

- `Dockerfile.delete_recording_job`
- `cloudbuild-delete-job.yaml` - builds and pushes a container to Artifact Registry and deploys the new container as a Cloud Run Job
- `clip2story/jobs/delete_recordings.sh` - Shell script that invokes `python manage.py delete_recordings`. The file *must be executable*. Note that Cloud Run Jobs require an executable file such as a shell script or Python script.

In terms of setup, we manually performed the following steps in the GCP web console to wire everything up and run the job on a schedule:

- Created an Artifact Registry Repository called `summarize-jobs` which hosts the `delete-recordings` Job container. New Jobs can use the same repository.
- Created several secrets such as the database connection string (*see `cloudbuild-delete-job.yaml` for details*).
- Created a Cloud Build trigger that builds and deploys the job using `cloudbuild-delete-job.yaml`
- Created a Cloud Scheduler trigger to run the Cloud Run job every 30 minutes

Note, if you add new secrets for a job, you must grant the Cloud Run and Cloud Build service accounts permission to access the secrets.

For example:

```bash
gcloud secrets add-iam-policy-binding NAME_OF_SECRET \
    --member serviceAccount:<SERVICE_ACCOUNT>@developer.gserviceaccount.com \
    --role roles/secretmanager.secretAccessor


gcloud secrets add-iam-policy-binding NAME_OF_SECRET \
    --member serviceAccount:<SERVICE_ACCOUNT>@cloudbuild.gserviceaccount.com \
    --role roles/secretmanager.secretAccessor
```


[Django management commands]: https://docs.djangoproject.com/en/4.2/howto/custom-management-commands/
[Cloud Run Jobs]: https://cloud.google.com/run/docs/quickstarts/jobs
