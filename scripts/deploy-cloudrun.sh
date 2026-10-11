#!/usr/bin/env bash
# Run in the authorized project's Cloud Shell after reviewing the IAM changes below.
set -euo pipefail
P=stepwise-ac215-20261010
REGION=us-central1
NUMBER=238092527041
TEAM=baileys-projects-7e3a3dc4
RUNTIME=stepwise-runtime@${P}.iam.gserviceaccount.com
INVOKER=stepwise-vercel@${P}.iam.gserviceaccount.com
BUILDER=stepwise-build@${P}.iam.gserviceaccount.com
IMAGE=${REGION}-docker.pkg.dev/${P}/stepwise/api:$(git rev-parse --short=12 HEAD)
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com iamcredentials.googleapis.com sts.googleapis.com --project="$P"
for NAME in stepwise-runtime stepwise-vercel stepwise-build; do
  gcloud iam service-accounts describe "${NAME}@${P}.iam.gserviceaccount.com" --project="$P" >/dev/null 2>&1 || gcloud iam service-accounts create "$NAME" --project="$P"
done
gcloud projects add-iam-policy-binding "$P" --member="serviceAccount:$RUNTIME" --role=roles/aiplatform.user --condition=None >/dev/null
gcloud projects add-iam-policy-binding "$P" --member="serviceAccount:$BUILDER" --role=roles/logging.logWriter --condition=None >/dev/null
gcloud artifacts repositories describe stepwise --location="$REGION" --project="$P" >/dev/null 2>&1 || gcloud artifacts repositories create stepwise --repository-format=docker --location="$REGION" --project="$P"
gcloud artifacts repositories add-iam-policy-binding stepwise --location="$REGION" --project="$P" --member="serviceAccount:$BUILDER" --role=roles/artifactregistry.writer >/dev/null
gcloud storage buckets describe "gs://${P}_cloudbuild" >/dev/null 2>&1 || gcloud storage buckets create "gs://${P}_cloudbuild" --project="$P" --location="$REGION" --uniform-bucket-level-access
gcloud storage buckets add-iam-policy-binding "gs://${P}_cloudbuild" --member="serviceAccount:$BUILDER" --role=roles/storage.objectViewer >/dev/null
gcloud iam workload-identity-pools describe stepwise-vercel --location=global --project="$P" >/dev/null 2>&1 || gcloud iam workload-identity-pools create stepwise-vercel --location=global --project="$P" --display-name='Stepwise Vercel only'
gcloud iam workload-identity-pools providers describe vercel --workload-identity-pool=stepwise-vercel --location=global --project="$P" >/dev/null 2>&1 || gcloud iam workload-identity-pools providers create-oidc vercel --workload-identity-pool=stepwise-vercel --location=global --project="$P" --issuer-uri="https://oidc.vercel.com/$TEAM" --allowed-audiences="https://vercel.com/$TEAM" --attribute-mapping='google.subject=assertion.sub' --attribute-condition="assertion.sub in ['owner:${TEAM}:project:stepwise:environment:preview','owner:${TEAM}:project:stepwise:environment:production']"
for DEPLOY_ENV in preview production; do
  gcloud iam service-accounts add-iam-policy-binding "$INVOKER" --project="$P" --role=roles/iam.workloadIdentityUser --member="principal://iam.googleapis.com/projects/${NUMBER}/locations/global/workloadIdentityPools/stepwise-vercel/subject/owner:${TEAM}:project:stepwise:environment:${DEPLOY_ENV}" >/dev/null
done
if [ ! -f .cloudrun-bundle/manifest.json ]; then ./scripts/export-cloudrun-bundle.sh; fi
python3 - <<'PYVERIFY'
import hashlib,json,pathlib
root=pathlib.Path('.cloudrun-bundle')
for name,expected in json.loads((root/'manifest.json').read_text()).items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected, name
index=json.loads((root/'data/processed/index.manifest.json').read_text())
assert index['points']==369, 'Rebuild and export the paragraph-level rubric index'
points=json.loads((root/'data/processed/points.json').read_text())
assert len(points)==index['points']
assert sum(p['payload']['kind']=='band_statement' for p in points)==238
assert sum(p['payload']['kind']=='band_statement' and p['payload']['task']=='academic_task_2' for p in points)==119
print('Frozen official RAG bundle verified:',index['index_id'],index['points'])
PYVERIFY
gcloud builds submit . --project="$P" --region="$REGION" --config=deploy/cloudrun/cloudbuild.yaml --substitutions="_IMAGE=$IMAGE" --service-account="projects/$P/serviceAccounts/$BUILDER" --gcs-source-staging-dir="gs://${P}_cloudbuild/source"
gcloud run deploy stepwise-api --project="$P" --region="$REGION" --image="$IMAGE" --service-account="$RUNTIME" --no-allow-unauthenticated --port=8080 --cpu=1 --memory=2Gi --concurrency=2 --min-instances=0 --max-instances=1 --timeout=300 --set-env-vars="GOOGLE_CLOUD_PROJECT=$P,GOOGLE_CLOUD_LOCATION=global,GEMINI_MODEL=gemini-3.8-flash"
gcloud run services add-iam-policy-binding stepwise-api --project="$P" --region="$REGION" --member="serviceAccount:$INVOKER" --role=roles/run.invoker >/dev/null
gcloud run services describe stepwise-api --project="$P" --region="$REGION" --format='value(status.url,status.latestReadyRevisionName)'
