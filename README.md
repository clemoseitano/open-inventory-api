# {{ project_name }}
Spin up a new project with this template
`django-admin startproject --template ./service-template your-service-name .`
## Getting started

This is a basic django project with django-rest-framework.
To run the project, you can run the following commands:
- `DB_NAME, DB_HOST,DB_PORT, DB_USER, DB_PASSWORD, APPLICATION_NAME,
LOG_LEVEL, SECRET_KEY, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD,
EMAIL_TIMEOUT, BASE_URL, PASSWORD_RESET_TIMEOUT` should be set in order to run it properly.


- `python manage.py migrate`
- `python manage.py createsuperuser`
- `python manage.py runserver`

## Authorization
This project uses the Oauth2 implementation for authentication/authorization.
Register an OAuth application with this:
- `http://localhost:8000/o/applications/`
Click on the link to create a new application and fill the form with the following data:

- Name: `settings.APPLICATION_NAME` value
- Client Type: confidential
- Authorization Grant Type: Resource owner password-based
- Save your app!

In case you face any issue with accessing the link, set a `LOGIN_URL` in your
settings file
`LOGIN_URL='/admin/login/'`

## Background Tasks
Background tasks are handled by Celery, with RabbitMQ as the broker.
RabbitMQ must be setup to successfully run the celery tasks.

## Running in a Docker container

The project has a Dockerfile and docker-compose.yml that aims to set up the full application with all it's dependencies.

Run the following command to run the backend on port 8000:

- ***docker-compose up --build***

This builds and deploys the following containers:

- `celery-worker`; running tasks
- `celery-beat`; a ticking clock to trigger the celery-worker
- `fc-backend`; the Django app
- `rabbitmq`; the message broker for celery
- `db`; the Postgres database
- **fc-backend_rabbitmq_go_net**; the custom network that all the containers run on

For diagnostics and shell access into the containers, run the following:

- ***docker exec -it fc-backend /bin/sh***

To tail logs from the containers, run the following command:
 - ***docker logs -f CONTAINER_NAME***

Where `CONTAINER_NAME` is the name for any of the containers listed above.

To shut down the docker containers, run the following command:

- ***docker-compose down***

