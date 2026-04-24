# Nichetify

A web application for Spotify music discovery, built with NiceGUI and Python. Users can log in, connect their Spotify account, view listening history, and get recommendations for lesser-known songs based on genre diversity — sourced from the iTunes Search API to avoid Spotify rate limits.

## Features

- **User accounts** — register, log in, update profile (stored in MongoDB)
- **Spotify OAuth (PKCE)** — connect your Spotify account without exposing secrets
- **Listening History** — view your recently played Spotify tracks
- **Discover Lesser-Known Songs** — genre-diverse recommendations sourced from the iTunes API, playable via the embedded Spotify player
- **Admin panel** — list and manage users (admin role)

## Tech Stack

| Layer | Technology |
|---|---|
| UI | [NiceGUI](https://nicegui.io) (Python) |
| Auth | Spotify PKCE OAuth |
| Discovery | iTunes Search API |
| Database | MongoDB (Atlas) |
| Container | Docker / Azure Container Apps |

## Project Structure

```
src/
  class_demo/
    listening_service/    # Spotify API integration, OAuth, recommendations
    user_service/         # User CRUD, authentication, bcrypt passwords
    user_app/
      listening/          # Listening history & recommendation UI + controller
      users/              # User profile & admin UI
      main.py             # NiceGUI page definitions
      logic.py            # App business logic
  run_app.py              # Entry point
deploy/
  app/                    # Dockerfile, docker-compose, Azure Container App config
tests/
  listening/              # Unit + integration tests for Spotify/recommendations
  user_service/           # Unit + integration tests for user service
```

## Local Development

### Prerequisites

- Python 3.11+
- MongoDB (local or Atlas connection string)
- Spotify Developer app ([create one here](https://developer.spotify.com/dashboard))

### Setup

```bash
git clone <repo-url>
cd cs-518-group
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
MONGODB_URI=mongodb+srv://<user>:<pass>@cluster.mongodb.net/
MONGODB_DB_NAME=class_demo_db
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=yourpassword
```

### Run

```bash
cd src
python run_app.py
```

The app will be available at `http://localhost:8080`.

### Run with Docker

```bash
docker compose -f deploy/app/docker-compose.yml up --build
```

## Running Tests

```bash
python -m pytest tests/ -v
```

Run a specific suite:

```bash
python -m pytest tests/listening/ -v
python -m pytest tests/user_service/ -v
```

## Deployment (Azure Container Apps)

Build, push, and deploy a new version:

```powershell
$v="vXX"
docker build -f deploy/app/Dockerfile -t mjs1438/user-app:$v .
docker push mjs1438/user-app:$v
az containerapp update --name user-app --resource-group class-demo-rg --image mjs1438/user-app:$v
```

Live URL: `https://user-app.whitebay-c606c597.eastus.azurecontainerapps.io`

> **Note:** The app's in-memory Spotify session resets on every container restart. Users must reconnect Spotify after each new deployment.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `MONGODB_URI` | MongoDB connection string | *(required)* |
| `MONGODB_DB_NAME` | Database name | `class_demo_db` |
| `ADMIN_USERNAME` | Seeded admin username | `admin` |
| `ADMIN_EMAIL` | Seeded admin email | `admin@example.com` |
| `ADMIN_PASSWORD` | Seeded admin password | `admin123` |
| `HOST` | Server bind address | `0.0.0.0` |
| `PORT` | Server port | `8080` |
