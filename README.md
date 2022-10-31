# SRI Testing

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

This repository contains a compendium of semantics-driven tests for assessing Translator Knowledge Providers (KPs) and Autonomous Relay Agents (ARAs) within the [Biomedical Data Translator](https://ncats.nih.gov/translator).

# Contents of the Repository

The project has two top level folders:

- Modules under [translator](translator) package, containing code shared between all categories of tests, including some generic TRAPI and Translator Status Dashboard scripts.
- Modules of the actual (Py)test harness under [tests](tests). At the moment, only one category of Translator of testing is implemented, that is, [One Hop Tests](tests/onehop/README.md).  Note that to run these tests, [KPs and ARAs need to configure web visible test data](tests/onehop/README.md#configuring-the-tests).

# Getting Started

The tests are recommended to be run using Python 3.9 or better. 

If not running inside a Docker container, the creation of a virtual environment is recommended.

## Python Dependencies

From within your virtual environment, install the indicated Python dependencies in the `requirements.txt` file:

```shell
(venv) $ pip install -r requirements.txt  # or equivalent command
```

## Run the Tests

Simply run available [tests](tests) using Pytest, within your favorite modality (i.e. terminal, favorite IDE, etc.).

# SRI Testing as a Web Service

The SRI Testing Harness may be run as a Web Service. See [here](api/README.md) for more details.

# TRAPI Validation Dashboard

A nice web interface is available to browse through results of SRI Testing Harness test runs.  [Documentation about this web interface](dashboard/README.md) is available. The interface may also be deployed as a Docker container (see below).

# Running the System within Docker

The SRI Testing system may also be run within Docker containers, using Docker Compose.

Assuming that you have installed both [Docker (or rather, Docker Desktop)](https://docs.docker.com/get-docker/) and [Docker-Compose](https://docs.docker.com/compose/install/) (Note: Docker Desktop now conveniently installs both...), then the following steps can be followed to run the system.

## Pre-Configuration

Two Dockerfile templates are available: [Dockerfile_RENCI_PRODUCTION](Dockerfile_RENCI_PRODUCTION) and [Dockerfile_SIMPLE](Dockerfile_SIMPLE). If you simply want to run the system locally, the SIMPLE dockerfile may do. A more robust Dockerfile configuration file - the RENCI variant - is more optimized for Kubernetes deployment in an institutional setting (like RENCI!).  Copy one or the other file into a single file named "Dockerfile" then continue with the instructions below.

The SRI Testing Dashboard also relies on some site specific parameters - encoded in a **.env** environmental variable configuration file -to work properly.  The **.env** file is **.gitignored** in the repo. A template file, [dot_env_template](dashboard/dot_env_template) is provided. A copy of this file should be made into a file called **.env** and customized to site requirements (see [full details here](dashboard/README.md)).

Note that the application now normally (by default) retrieves its Translator KP and ARA test data via settings in the Translator SmartAPI Registry (the 'Registry'). For testing purposes, the Registry may be bypassed and "mock" data used, by setting the environment variable MOCK_TRANSLATOR_REGISTRY to '1'. Setting this variable to zero ('0') forces the use of the 'real' Registry. Make a copy of the _doc_env_template_ located in the root project directory, into a file called **.env** and uncomment out the variable setting therein.

## Database for the Test Results

You will generally want to have the backend persist its test results in a MongoDb database(*), so first start up a Mongo instance as so:

```shell
docker-compose -f run-mongodb.yaml up -d
```

Note that the application will default to use the filing system for its test run under a local **results** directory, if the MongoDb container is not running.  The application will start a bit more slowly in such a situation as it awaits the timeout of the attempted connection to a MongoDb database.

If the database is running, the Mongo-Express container may be run to look at it:

```shell
docker-compose -f run-mongodb-monitor.yaml up -d
```

Mongo-Express web page is available at http://localhost:8081.  It is generally not a good idea to run this on a production server.

## Testing Engine and Web Dashboard

Next, build then start up the services consisting of Docker containers for the testing dashboard and backend engine - defined in the default _Dockerfile_ - using **Docker Compose**, by the root directory of the project, build the local docker container

```shell
docker-compose build
docker-compose up -d
```

Once again, go to  http://localhost/docs to see the service documentation.  Docker logs may be viewed in a streaming fashion by:

```shell
docker-compose logs -f
```

To stop the Docker containers:

```shell
docker-compose down
docker-compose -f run-mongodb.yaml down
```

Of course, the above `docker-compose` commands may be overridden by the user to suit their needs. Note that the docker implementation assumes the use of uvicorn (installed as a dependency).
