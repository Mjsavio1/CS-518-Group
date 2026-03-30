# User App Deployment

The UI is containerized separately from the API. In the current codebase, the NiceGUI app still talks directly to MongoDB and seeds the admin user on startup, so it needs its own MongoDB connection settings.

## Files

- `deploy/app/Dockerfile`: container build for the NiceGUI app.
- `deploy/app/docker-compose.yml`: local container run for the app only.
- `deploy/app/containerapp.yaml`: Azure Container Apps template for the UI.

## Required environment variables

- `MONGODB_URI`: MongoDB Atlas connection string.
- `MONGODB_DB_NAME`: database name. Defaults to `class_demo_db`.
- `ADMIN_USERNAME`: optional seeded admin username.
- `ADMIN_EMAIL`: optional seeded admin email.
- `ADMIN_PASSWORD`: optional seeded admin password.

## Local container test

From the repository root:

```bash
docker compose -f deploy/app/docker-compose.yml up --build
```

The UI will be available at `http://localhost:8080`.

## Azure Container Apps

1. Build and push the UI image.

```bash
docker login
docker build -t mjs1438/user-app:v1 -f deploy/app/Dockerfile .
docker push mjs1438/user-app:v1
```

2. The image value in `deploy/app/containerapp.yaml` is prefilled as `mjs1438/user-app:v1`.

3. Deploy the UI as a separate container app.

```bash
az containerapp create \
  --resource-group class-demo-rg \
  --yaml deploy/app/containerapp.yaml \
  --secrets mongodb-uri="<atlas-connection-string>" admin-password="<admin-password>"
```

## Separate deployment note

The UI and API now have separate deployment assets under `deploy/app` and `deploy/api`. They can be built and released independently.

If you later want the UI to call the API instead of using the service layer directly, that requires an application refactor. The current deployment split only separates packaging and hosting.
