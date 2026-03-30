# User API Deployment

This API is a standalone FastAPI service. It does not need a local database container because it connects directly to MongoDB Atlas through `MONGODB_URI`.

## Files

- `deploy/api/Dockerfile`: container build for the FastAPI service.
- `deploy/api/docker-compose.yml`: local container run for the API only.
- `deploy/api/containerapp.yaml`: Azure Container Apps template.

## Required environment variables

- `MONGODB_URI`: MongoDB Atlas connection string.
- `MONGODB_DB_NAME`: database name. Defaults to `class_demo_db`.

## Local container test

From the repository root:

```bash
docker compose -f deploy/api/docker-compose.yml up --build
```

The API will be available at `http://localhost:8000`.

## Azure Container Apps

1. Build and push the image to Docker Hub.

```bash
docker login
docker build -t mjs1438/user-api:v1 -f deploy/api/Dockerfile .
docker push mjs1438/user-api:v1
```

2. The image value in `deploy/api/containerapp.yaml` is prefilled as `mjs1438/user-api:v1`.

3. Create a secret for the Atlas connection string and deploy the container app.

```bash
az containerapp create \
  --resource-group class-demo-rg \
  --yaml deploy/api/containerapp.yaml \
  --secrets mongodb-uri="<atlas-connection-string>"
```

4. Update an existing deployment with a new image.

```bash
az containerapp update \
  --name user-api \
  --resource-group class-demo-rg \
  --image mjs1438/user-api:<new-tag>
```

## Notes

- The container listens on port `8000`.
- The ACA template stores the Atlas connection string as a secret reference instead of plain text.
- The app UI should be deployed separately from this API.
