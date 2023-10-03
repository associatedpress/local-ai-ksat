**For signed url generation to work properly. You need to apply a CORS policy to your GCP bucket. I will link the resource I used to do that.**

https://cloud.google.com/storage/docs/using-cors#command-line_1

You can set a more restrictive CORS policy if you choose. In this folder I have put the CORS policy I applied for our test bucket.

You also need to make sure that the environment variable GOOGLE_APPLICATION_CREDENTIALS is set to point at your google credentials stored in sv_keys.json

https://stackoverflow.com/questions/57368894/generate-presigned-url-for-uploading-file-to-google-storage-using-python
