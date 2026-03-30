# Deploy API

I want to containerize my user API (/src/user_api/) and deploy it to Azure Container Apps.  

* I don't need to run a db service because my API will connect to mongoDB Atlas.

## assets

Containerization and deployment assets should go in:

* /deploy/api/

## documentation

Please generate simple instructions for deployment.  

Documentation should go in:

* docs/deploy/api/

## notes

The user app (/src/user_app/) and the API (/src/user_api/) should be two separate deployments.

* please refactor so that the deployment assets and documentation are moved to /deploy/app and /docs/deploy/app, respectively.
* please also update the file contents as needed (e.g. docker-compose and the deployment instructions)