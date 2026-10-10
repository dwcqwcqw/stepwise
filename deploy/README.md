# Vercel frontend and private Cloud Run API

The Vercel build copies the same HTML/CSS/JavaScript used by the Compose web container. A same-origin Node gateway allows only readiness, feedback and model-essay routes. Its short-lived Vercel OIDC identity exchanges through Google Workload Identity Federation for a Cloud Run ID token. Google credentials are not embedded in the browser or saved as Vercel secrets.

Cloud Run runs the existing FastAPI application with an immutable export of the 131 official rubric vectors and the pinned ONNX embedding model. Qdrant's local engine loads this snapshot in memory per replica. The MS2 ingestion, chunking and indexing containers still produce and verify that snapshot; the original Compose pipeline keeps its Qdrant server. The backend's dedicated service identity calls Vertex AI through metadata credentials, so Cloud Shell token refresh is no longer needed for the deployed app.

## Deployment

1. Review `scripts/deploy-cloudrun.sh`: it creates three service identities (runtime, invoker, build), a single-project/preview-only OIDC trust, Artifact Registry, build staging storage, and a private Cloud Run service. The runtime gets Vertex AI User; the Vercel identity gets only service invocation. The build identity gets logging, read access to its source bucket and write access to its image repository.
2. In the existing authorized Cloud Shell, pull the verified `milestone2` commit and run `./scripts/deploy-cloudrun.sh` with the existing Compose RAG pipeline running. The frozen bundle is excluded from Git and contains no essays or credentials.
3. Set Vercel preview environment variables `STEPWISE_API_URL` to the returned Cloud Run URL, `GCP_INVOKER_EMAIL` to `stepwise-vercel@stepwise-ac215-20261010.iam.gserviceaccount.com`, and `GCP_WIF_AUDIENCE` to `//iam.googleapis.com/projects/238092527041/locations/global/workloadIdentityPools/stepwise-vercel/providers/vercel`.
4. Enable team-issuer OIDC for the Vercel project. Deploy the source files as a preview with Node 22, `npm ci --ignore-scripts`, `npm run build`, output directory `public`. Keep Vercel deployment protection enabled.
5. Verify readiness shows the 131-point index, then run one actual essay assessment and one generation with independent assessment through the deployed UI. Record source commit, image digest, Cloud Run revision and Vercel deployment ID.

`max-instances=1`, `min-instances=0`, concurrency 2, and 300-second deadlines bound this course demo's infrastructure. Vertex usage still follows model calls. Deployment protection limits access to the configured Vercel viewers; this is not a public production release. Git auto-deployment requires a separate GitHub integration installation if it is not already configured.
