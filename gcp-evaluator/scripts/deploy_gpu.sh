gcloud run deploy gpu-evaluator \
  --source ./gpu_evaluator \
  --region us-central1 \
  --allow-unauthenticated \
  --cpu=4 \
  --memory=16Gi
