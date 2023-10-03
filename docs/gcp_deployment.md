# GCP Deployment

Below are details on the initial bootstrapping of the production environment on Google Cloud Platform (GCP) and automated deployment using GCP Cloud Build and related services.

## Pre-reqs

Create Google Cloud Platform account and a Google Cloud Project.

Install [`gcloud`](https://cloud.google.com/sdk/docs/install) command-line tools.


### Secrets and Bot Account

We use a bot gmail account to connect Google Cloud Platform to GitHub in
order to automate our build and deployment process.

Load the bot account credentials into GCP Secret Manager.


## Configure local gcloud CLI tool


```sh
gcloud config configurations create <BOT_NAME>

# Set to GCP Project ID
gcloud config set project <PROJECT_ID>

# Use bot account for project
gcloud config set account <BOT_ACCOUNT_EMAIL>

# Login to account
gcloud auth login

# Set region and zone
gcloud config set compute/region us-central1
gcloud config set compute/zone us-central1-a
```

**This project originally used the US-CENTRAL1 region and there are many references in the code to that. You should select the region most appropriate to you, often, that will be one closest geographically to you.**

## Cloud Run app setup


Overall, follow the steps in the [Django on Cloud Run docs][]

[Django on Cloud Run docs]: https://cloud.google.com/python/django/run


```bash
gcloud auth application-default login


curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.5.0/cloud-sql-proxy.darwin.amd64
chmod +x cloud-sql-proxy
```

Create a Cloud SQL instance with 50GB SSD and db-g1-small tier.

> Below is modified version from the [Django on Cloud Run docs][] that additionally
> specifies storage size and type

```bash
gcloud sql instances create summarize-prod \
    --project <PROJECT_ID> \
    --database-version POSTGRES_14 \
    --storage-size 50 \
    --storage-type SSD \
    --tier db-g1-small \
    --region us-central1

```

**IMPORTANT**: After creating the above, go to the GCP web console for Cloud SQL and edit the instance to make it available on the default private network. This will be important for using a basic SQL connection string in Cloud Run. Under the `Instance IP Assignment` click `Private IP` and choose the option to have Google auto-generate a default network. Don't forget to click `Save` at the bottom of the page!!

The above step will require a database instance restart, which can take a few minutes.


Once the db instance is updated and running again, create a db and user.

```bash
export PROJECT_ID=<PROJECT_ID>
export DB_INSTANCE=summarize-prod
export DB_REGION=us-central1
export DB_NAME=summarize_prod
export DB_USER=admin
export DB_PASS=<DB_PASSWORD>

gcloud sql databases create $DB_NAME --instance $DB_INSTANCE

gcloud sql users create $DB_USER \
    --instance $DB_INSTANCE \
    --password $DB_PASS

```

Create a `.env.gcp` file per [create django secrets file](https://cloud.google.com/python/django/run#create-django-environment-file-as-a-secret):

```
# In particular, you must create the DATABASE_URL setting as below, substituting the
# actual values for that setting

DATABASE_URL='postgres://$DB_USER:$DB_PASS@//cloudsql/$PROJECT_ID:$DB_REGION:$DB_INSTANCE/$DB_NAME'
GS_BUCKET_NAME=summarize-www-prod
DJANGO_SETTINGS_MODULE='clip2story.settings.prod'
GOOGLE_CLOUD_PROJECT=<PROJECT_ID>
```

Once you've created that file, upload it to Secret Manager:


```bash

gcloud secrets create django_settings_prod --data-file .env.gcp

```

Get the Project number for downstream steps:

```bash

gcloud projects describe $PROJECT_ID --format='value(projectNumber)'

export PROJECT_NUM=<PROJECT_NUM> # this will obviously change by project
```


Grant secrets access to cloud run and cloud build service accounts:

```bash
gcloud secrets add-iam-policy-binding django_settings_prod \
    --member serviceAccount:$PROJECT_NUM-compute@developer.gserviceaccount.com \
    --role roles/secretmanager.secretAccessor


gcloud secrets add-iam-policy-binding django_settings_prod \
    --member serviceAccount:$PROJECT_NUM@cloudbuild.gserviceaccount.com \
    --role roles/secretmanager.secretAccessor


```


Skip the [Create Django superuser step](https://cloud.google.com/python/django/run#create_secret_for_djangos_admin_password).

Grant Cloud Build access to Cloud SQL

> Select `None` for the policy condition

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member serviceAccount:$PROJECT_NUM@cloudbuild.gserviceaccount.com \
    --role roles/cloudsql.client

```

Next, use the cloud-sql-proxy to set up the database and create a superuser (note this step strays from the docs). Open a new shell terminal and navigate to where you downloaded the `cloud-sql-proxy` executable.

```bash
export PROJECT_ID=<PROJECT_ID>
export DB_REGION=us-central1
export DB_INSTANCE=summarize-prod

./cloud-sql-proxy $PROJECT_ID:$DB_REGION:$DB_INSTANCE

```

Back in the original terminal shell:

```bash
export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
export USE_CLOUD_SQL_AUTH_PROXY=true
```


Now you should be able to connect to the production database by using your prod settings and create a superuser, migrate the production database, and collect static files on Cloud Storage.



```bash
cd clip2story/

export DJANGO_SETTINGS_MODULE=clip2story.settings.prod

python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
```

Next, we begin the Cloud Run deployment process. 

> Note, here we're going off script from the [Django on Cloud Run docs][] in order to use Artifact Registry instead of Container Registry, which is officially deprecated.

Make sure to enable the relevant APIs per the instructions on [this page](https://cloud.google.com/artifact-registry/docs/transition/changes-gcp#artifact-registry)


Once you've enabled the relevant APIs, we need to create an Artifact Registry [repository](https://cloud.google.com/sdk/gcloud/reference/artifacts/repositories/create) to store the Docker container for use by Cloud Run.


```
gcloud artifacts repositories create summarize-prod \
    --project $PROJECT_ID \
    --repository-format docker \
    --location us-central1 \
    --mode standard-repository
```

Next, update local credentials for `gcloud`: 

```
gcloud auth configure-docker us-central1-docker.pkg.dev
```

Next, build, tag and push a Docker image to Artifact Registry.

> On this initial build and push, we user the `Dockerfile` by default. Later, we'll configure Cloud Run to use `cloudbuild.yaml` to build and push the container whenever the code changes on the `main` branch of our GitHub repo.

```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/$PROJECT_ID/summarize-prod/summarize:v1
```

Next, do a manual Cloud Run deployment:


```bash
gcloud run deploy summarize-service --image us-central1-docker.pkg.dev/<PROJECT_ID>/summarize-prod/summarize:latest \
  --add-cloudsql-instances <PROJECT_ID>:us-central1:summarize-prod \
  --region us-central1 \
  --platform=managed \
  --allow-unauthenticated
```

This first run won't result in a working deployment. But it will provide a key piece of information: The `Service URL: https://GCP_DOMAIN.run.app`

The Service URL must be passed as an environment variable since it is required for security-related settings in the `clip2story/settings/prod.py`. 

Now that we have the service url, let's run the deployment one more time.

> Note the addition of the `--set-env-vars` flag


```bash

gcloud run deploy summarize-service --image us-central1-docker.pkg.dev/<PROJECT_ID>/summarize-prod/summarize:latest \
  --add-cloudsql-instances <PROJECT_ID>:us-central1:summarize-prod \
  --region us-central1 \
  --platform=managed \
  --set-env-vars=CLOUDRUN_SERVICE_URL=https://GCP_DOMAIN.run.app \
  --allow-unauthenticated
```


WOOT! You've now manually built and deployed the containerized app.

But we're not quite done. The last stage is setting up automated deployment when any changes are pushed to the `main` branch of our GitHub repo. Make sure you stash that Service URL because we'll need it in the next step.


### Automated Deployment

We'll use GCP Cloud Build for CI (aka automated deployment) of the application whenever changes are pushed to the `main` branch.

The deployment process configured in `cloudbuild.yaml` performs the following steps:

- build and push the container to Artifact Registry
- migrate the database
- collectstatic (ie deploy CSS, JS, etc to Cloud Storage)
- deploy the latest version of the Cloud Run app


To begin setting up CI, take the Service URL from the last step and add it to the `cloudbuild.yaml` at the bottom under the `substitutions` section:

```
substitutions:
  _CLOUD_SQL_INSTANCE_NAME: summarize-prod
  _CLOUDRUN_SERVICE_URL: https://GCP_DOMAIN.run.app
```


Next, follow the instructions for [setting up continuous deployment from Git using Cloud Build](https://cloud.google.com/run/docs/continuous-deployment-with-cloud-build#existing-service). 

For this step, you need to work in the GCP web console. 

> IMPORTANT: Make sure to log into the Google Cloud Platform using your bot account `BOT_ACCOUNT_EMAIL`. 

You can access the bot credentials by logging into GCP using your normal user account, and then getting the bot account's user/pass from the GCP Secret Manager. You should also grab the `GITHUB_ACCOUNT` login credentials, since during this process you'll need to authorize GCP to access a GitHub repo.

Once you have those credentials, log out of your user account on GCP and log back in using the `BOT_ACCOUNT_EMAIL` credentials.

Then proceed to set up continuous deployment by following the below steps:

- Go to the Cloud Run on GCP web console
- Click on the `summarize-service`
- Click the button to `SET UP CONTINUOUS DEPLOYMENT`
- If the pop-up says `Currently not authenticated`, click `Authenticate`
- If you get a pop-up that says the GitHub App is not currently installed, click `INSTALL GOOGLE CLOUD BUILD`
  - Choose the organization (`GITHUB_ORGANIZATION`)
  - Select `All repositories`
  - Click `Install`
  - Use the bot's GitHub password to confirm the installation
- Once GCP is authenticated to work with GitHub, you can select a repository for the cloud build process.
- Check the user agreement box
- Click `Next`
- Under **Build Configuration**:
  - Leave the `main` branch selected
  - Choose `Dockerfile` for the Build Type

Once the above steps are complete, the repository should be set up to automatically build and deploy to Cloud Run whenever code is pushed or merged into the `main` branch.
