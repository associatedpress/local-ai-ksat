# Configuring Clip2Story

Before Clip2Story is used, the global config needs to be populated and third-party services need to be setup.

The Global Config is accessed from the Django admin interface, append `/admin` to the end of the URL to access it.
From there, head over to Global Configs and select the first instance in the list.

Some of the config fields within the global config have defaults that can be left alone. These fields are:
- `Url timeout val` - Sets the time in minutes before a generated signed-url expires
- `Age to delete` - Sets the time in days before recordings not being held get deleted
- `Recent transcript limit` - Sets how many transcripts before filtering get pulled from Trint for importing selection

##### Trint transcription configuring

Once a Trint account has been selected to link to Clip2Story, the API's need to be connected. 

Head over to the [`Trint API page`](https://app.trint.com/account/api):
- Copy the API key and paste it into the `Trint api key` field in the global config
- Enable the callback URL to trigger on `Transcript Complete` and `Transcript Verified` events.
- Set the callback URL to the URL of your instance of Clip2Story and append `/dashboard/transcript_msg_receiver`. For example: `https://clip2story.com/dashboard/transcript_msg_receiver`

##### ARC configuring

Decide on an endpoint for generated stories to be sent to and generate an API key for that endpoint.

In the global config, set the ARC fields:
- `ARC API URL` - Set this to the endpoint URL. For example: `https://api.sandbox.gmg.arcpublishing.com`
- `ARC API key` - Set this to the API key generated for the specified endpoint.
- `ARC Canonical Website` - Set this to the website that the generated drafts will be sent to.

##### Final Google Cloud Platform configuring

The GCP deployment is covered in the [GCP documentation file](https://github.com/couric/summarize/blob/main/docs/gcp_deployment.md). All that is left is setting the bucket for the video files to be stored to.

In the global config there is a field called `Bucket name`, set this to the name of the storage bucket you created during deployment. This is where the video files will be uploaded, downloaded, and deleted from.

##### OpenAI configuring

Clip2Story makes heavy use of the generative AI offerings of OpenAI. For the app to properly function, Clip2Story needs an OpenAI API key.

Create an OpenAI account and copy the API key associated to that account and paste it in the `Openai api key` field inside of the global config.

##### The rest of the Global Config

Up to this point we have touched on most of the fields with the exception of two.
- The `Help messages html` field sets the html text to be displayed inside the help page and login page.
- The `Tag prompt` field sets the OpenAI prompt used to generate the tags for the recordings. **IT IS IMPORTANT THAT YOU DO NOT SPECIFY A FORMAT TYPE IN YOUR PROMPT**



# Creating User Accounts

Within the Django admin interface, which can be reached by appending `/admin` to the end of the URL, there is a Users section.

Head over to the Users section and click Add or Add user to access the user creation page. Enter the username and password to create the basic account and Django will drop you into the permissions page to add more details about the users account.

It is important to ensure the user does not have more permissions than intended.



# Creating Prompts

Clip2Story is heavily based on generative AI and generative AI requires thorough instructions to get an output the end user desires. That is why prompts are so crucial and why Clip2Story was built with prompt flexibility in mind.

##### Where to put Prompts

To create a new prompt category, you need to access the Django admin interface by appending `/admin` to the Clip2Story URL.

Once there, click add on the Prompts row, you will be greeted by two fields:
- `Prompt type` - This is the category text that will be displayed in the category drop down, pick something short and succinct.
- `Prompt text` - This is the prompt text itself used by OpenAI to generate the summary. It has a limit of 500 words.

Once those two fields are filled out, save it and it will now be available in the dashboard category dropdown.

##### How to get a good prompt

Generating an initial prompt can seem daunting. It might seem funny to do so, but the best way I have found to generate a decent initial prompt is asking [ChatGPT](https://chat.openai.com/) to do such. Explain that you need to generate a prompt for GPT and give it your initial requirements.

Plug that initial prompt in and generate a summary. Read over the summary and make notes of what it could do better, pull out numbers more, try to discern fact from opinion, etc. Take those notes and give them to ChatGPT again to regenerate the prompt. Once the updated prompt is plugged in, regenerate the summary. Rinse and repeat until you are satisfied.