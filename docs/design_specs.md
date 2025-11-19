# 1. Introduction

## 1.1 Purpose

This document provides a detailed architecture and design specification for a Django REST API project which will manage
a user's product catalog.

## 1.2 Scope

This application will expose RESTful endpoints for user management and product catalog management. The design covers the
backend application architecture, database design, API specification, and system dependencies.

# 2. Design Inputs

## 2.1 COTS (Commercial Off-The-Shelf) Components

- Django framework
- Django REST framework
- PostgreSQL database
- Celery for background tasks
- Docker for containerization
- Pip and Virtualenv for dependency management
- Postman for API documentation
- Git and GitHub for version control

## 2.2 New Components

Custom components will need to be developed for user and product management.

# 3. Design Outputs

## 3.1 System Architecture

The system will be designed as a containerized Django application with a Postgres database. It will utilize the Django
REST Framework to expose RESTful endpoints for user and product management. Celery will be used for asynchronous tasks.

## 3.2 Software Detailed Design

### User Management

Users will have the following fields:

- First Name
- Last Name
- Email
- Password (hashed and salted)

#### Endpoints:

- User Registration
- Account Activation
- User Login
- Forgot Password
- Password Reset

#### User Registration

- `POST /register/`

The backend shall provide the user with an endpoint to create or register an account
on the platform.
The registration endpoint accepts the following fields under Request Body and shall upon
success return the fields declared in Response Body.

Request Body:

| Field        | Type   | Description                                   |
|:-------------|:-------|:----------------------------------------------|
| `email`      | string | The email of the user trying to sign up.      |
| `password`   | string | The password of the user trying to sign up.   |
| `first_name` | string | The first name of the user trying to sign up. |
| `last_name`  | string | The last name of the user trying to sign up.  |

Response Body:

| Field     | Type   | Description                                          |
|:----------|:-------|:-----------------------------------------------------|
| `success` | string | A message describing the status of the registration. |

##### Notes

The registration process also has a side effect of scheduling an account activation email to
be sent to the user through a [Celery](https://pypi.org/project/celery/) task.

#### User Login

- `POST /login/`

The backend shall provide the user with an endpoint to log in to their account.
The login endpoint accepts the following fields under Request Body and shall upon
success return the fields declared in Response Body.

Request Body:

| Field      | Type   | Description                                |
|:-----------|:-------|:-------------------------------------------|
| `email`    | string | The email of the user trying to log in.    |
| `password` | string | The password of the user trying to log in. |

Response Body:

| Field   | Type        | Description                                            |
|:--------|:------------|:-------------------------------------------------------|
| `user`  | JSON Object | The basic user details of the user trying to log in.   |
| `token` | JSON Object | The authentication token for subsequent authorization. |

##### `user` Object:

| Field        | Type   | Description                           |
|:-------------|:-------|:--------------------------------------|
| `email`      | string | The email of the logged-in user.      |
| `first_name` | string | The first name of the logged-in user. |
| `last_name`  | string | The last name of the logged-in user.  |

##### `token` Object:

| Field           | Type    | Description                                              |
|:----------------|:--------|:---------------------------------------------------------|
| `access_token`  | string  | The token that provides access to protected routes.      |
| `token_type`    | string  | The type of the token, in this case, Bearer.             |
| `expires_in`    | integer | The time (in seconds) for which the token is valid.      |
| `refresh_token` | string  | The token that can be used to obtain a new access token. |
| `scope`         | string  | The level of access that the token provides.             |

#### Forgot Password

- `POST /forgot-password/`

The backend shall provide the user with an endpoint to initiate a password reset of their account
through the forgot-password endpoint.
The forgot-password endpoint accepts the following fields under Request Body and shall upon
success return the fields declared in Response Body.

Request Body:

| Field   | Type   | Description                                                   |
|:--------|:-------|:--------------------------------------------------------------|
| `email` | string | The email of the user trying to initiate the password change. |

Response Body:

| Field     | Type   | Description                                                    |
|:----------|:-------|:---------------------------------------------------------------|
| `success` | string | A message describing the status of the password reset attempt. |

##### Notes

The `/forgot-password/` endpoint shall schedule and email message with a reset token
to be sent to the user's email, if the request is successful

#### Reset Password

- `POST /reset-password/`

The backend shall provide the user with an endpoint to reset or change the password of their account
through the reset-password endpoint.
The reset-password endpoint accepts the following fields under Request Body and shall upon
success return the fields declared in Response Body.

Request Body:

| Field      | Type   | Description                   |
|:-----------|:-------|:------------------------------|
| `password` | string | The new password of the user. |

Response Body:

| Field     | Type   | Description                                            |
|:----------|:-------|:-------------------------------------------------------|
| `success` | string | A message describing the status of the password reset. |

### Product Management

Products will have the following fields:

- Name
- Price
- Quantity
- Image

Endpoints (authorized):

- Create a product
- View all products
- View a single product
- Update a product
- Delete a product

# 4. Design Rationale

Given the requirements for the system, Django and the Django REST Framework were chosen due to their robustness,
scalability, and ease of use for building RESTful APIs. PostgreSQL is a powerful, open-source object-relational database
system.

# 5. System Interface Description

The system will expose a RESTful API for interacting with user and product data. The API will be documented using
Postman.

# 6. Design Verification and Validation

Unit tests will be written to ensure the functionality of the system. Validation will be performed through rigorous
manual and automated testing.

# 7. Design Traceability

Each requirement given corresponds to components described in the system architecture and detailed design.

# 8. Design Quality Assurance

Code review and rigorous testing strategies will be employed, including unit testing and integration testing. Continuous
Integration/Continuous Delivery (CI/CD) will be set up to ensure quality control.

# 9. Design Evolution

The design is open for future enhancements like expanding user management, product categories, adding product reviews,
etc.
