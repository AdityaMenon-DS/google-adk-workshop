# Optional Cloud Run task

Status: prepared instructions only; no cloud resources have been created.

First finish the live local tests. You will need a Google Cloud project with
billing enabled, Google Cloud CLI, permission to deploy Cloud Run, and your own
Gemini API key. Cloud and model usage may incur charges.

1. In Google Cloud, enable Cloud Run, Cloud Build, Artifact Registry and Secret
   Manager for your project. Install the Google Cloud CLI and run `gcloud auth login`.
2. Create a Secret Manager secret named `gemini-api-key` containing your key.
   Give the Cloud Run runtime service account permission to read that secret.
   Use a dedicated service account if possible.
3. Create a clean source directory without copying `.env`. From the project root:

```powershell
New-Item -ItemType Directory -Force work/cloud/personal_assistant
Copy-Item agents/personal_assistant/agent.py work/cloud/personal_assistant/
Copy-Item agents/personal_assistant/tools.py work/cloud/personal_assistant/
Copy-Item agents/personal_assistant/__init__.py work/cloud/personal_assistant/
Copy-Item requirements.txt work/cloud/personal_assistant/
```

4. Replace `YOUR_PROJECT_ID` and `YOUR_RUNTIME_SERVICE_ACCOUNT` below, then run:

```powershell
.\.venv\Scripts\adk.exe deploy cloud_run --project=YOUR_PROJECT_ID --region=us-central1 --service_name=workshop-personal-assistant --with_ui --adk_version=2.11.0 --env=GOOGLE_GENAI_USE_VERTEXAI=FALSE --env=GEMINI_MODEL=gemini-3.8-flash work/cloud/personal_assistant -- --service-account=YOUR_RUNTIME_SERVICE_ACCOUNT --set-secrets=GOOGLE_API_KEY=gemini-api-key:latest --max-instances=1
```

`--with_ui` includes the ADK Web interface. The secret is supplied at runtime,
not stored in the source. At the access prompt, choose the access policy needed
for the workshop. Allowing unauthenticated access makes the agent usable by
anyone with its URL, using your model quota; the ADK interface is a development UI.
One maximum instance is not a spending cap.

5. Open the returned service URL. Test search, calculation, text analysis and the
   combined request. Submit the returned URL only after these work.
6. After evaluation, remove the service if you no longer need it.

If deployment fails on permissions or billing, resolve that in your own Cloud
project. Never add a service-account JSON key or actual `.env` to the submission.

Reference: [Google ADK Cloud Run deployment](https://adk.dev/deploy/cloud-run/).
Flags were checked against the installed ADK 2.11.0 CLI; the deployment itself
has not been tested.
