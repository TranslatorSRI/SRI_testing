# SRI Testing

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

This repository contains a compendium of semantics-driven tests for assessing Translator Knowledge Providers (KPs) and Autonomous Relay Agents (ARAs) within the [Biomedical Data Translator](https://ncats.nih.gov/translator). The application may be run directly from a terminal, accessed programmatically via a [web services API](api) or previously run test results viewed via a [web dashboard](./dashboard) (see below).

Further details about the application is available in the project's [GitPages repository](https://ncatstranslator.github.io/SRI_Testing/) and also [Translator Developer Documentation](https://translator-developer-documentation.readthedocs.io/en/latest/guide-for-developers/sri_testing/).

# Getting Started

The tests are run using Python 3.9 or better. 

As of release 2.0.0, the SRI Testing project uses the [poetry dependency management](https://python-poetry.org) tool to manage its local installation, virtual environment and dependencies.

After [installing poetry](https://python-poetry.org/docs/#installation), the project may be cloned, the Poetry installation run, and a (Poetry) virtual shell environment for running the tests set up as follows (or use your favorite IDE - e.g. like PyCharms - to set up the Poetry environment as such):

```bash
git clone https://github.com/TranslatorSRI/SRI_testing
cd SRI_testing

# creates a new virtual environment or reuses
# a current one, then installs dependencies
poetry install
```

The SRI Testing harness testing leverages the Python testing [Pytest](https://docs.pytest.org) framework to generate a series of unit tests to be run based on test data and test configurations curated for available Translator ARA and KP resources. The core test script - **test_onehops.py** - for achieving this is under the **tests/onehop** project respository subfolder. Those tests are most conveniently run from inside that subfolder:

```bash
cd tests/onehop
```

The One Hop tests may be run on **_all_** the available Translator ARA and KP resources by simply typing the following command (from within the test/onehop folder):

```bash
poetry run pytest test_onehops.py
```

Since it is a bit tiring to type poetry run each time, let's start running the test script inside a poetry shell (such a shell allows running of commands *without* the need to prefix run Poetry-installed applications with the 'poetry run' command directive):

```bash
poetry shell
pytest test_onehops.py
```

Running all the tests on all Translator components is **_very_** computationally intensive. Besides, you have your favorite KP or ARA, don't you? 

The running of the test script may therefore be constrained to run on one (or a smaller number) of the KP and/or ARA resources, by specifying the Infores object identifiers in question (comma-delimited string for multiple resources) as the values of the **`--kp_id`** and **`--ara_id`** command line parameters. 

If you wish to solely run a KP test and possibly wish to skip ARA tests, you may also provide a value of **`SKIP`** to the **`--ara_id`**.  For example, to solely run tests on the Broad Institute's Molecular Provider service, the following command works (assuming that they have [properly curated their test edge data](https://github.com/TranslatorSRI/SRI_testing/blob/main/tests/onehop/README.md#configuring-the-tests)):

```bash
pytest test_onehops.py --kp_id="molepro" --ara_id="SKIP" --x_maturity="staging"
```

Note here that we also specified the [X-Maturity environment](https://github.com/NCATSTranslator/TranslatorArchitecture/blob/master/SmartAPIRegistration.md#environments) being tested (in this case, "**_staging_**"). In fact, **_every_** SRI Testing One Hop test run only accesses one **X-Maturity** environment. If you don't specify such an environment, the system chooses one for you, based on environment precedence ('production' > 'staging' > 'testing' > 'development') and availability of test data.

The above test run will produce a somewhat verbose and opaque regular Pytest console output (albeit with a 'short test summary info' section at the end giving a general indication of the outcome of the test run). Have no fear: there are more digestible sources for the results captured in the form of a set of structured JSON files.  If you haven't [configured a full (Mongo) database](#database-for-the-test-results) to capture the results, then these JSON files are locally dumped onto your filing system under the **_tests/onehop/test_results_** subfolder within a date time stamp-indexed directory, looking something like (specific test run details will differ):

```
# example of a test run under 'tests/onehop/test_results'
ls -R1 test_results/2023-06-06_10-44-19
KP
test_run_summary.json

test_results/2023-06-06_10-44-19/KP:
molepro

test_results/2023-06-06_10-44-19/KP/molepro:
molepro-6-by_object.json
molepro-6-by_subject.json
molepro-6-inverse_by_new_subject.json
molepro-6-raise_object_by_subject.json
molepro-6-raise_predicate_by_subject.json
molepro-6.json
recommendations.json
resource_summary.json
```

For more complete details about SRI Testing One Hop tests and JSON file results, see the full [One Hop tests](./tests/onehop/README.md) documentation.

We again briefly mention here the use of a Mongo database to conveniently manage your test run output; use of the web service programmatic API to retrieve test results; and availability of a web UI Dashboard to view such results in a more convenient human-readable fashion (see below).

# Contents of this Repository

The project has four top-level folders:

- Modules under [translator](sri_testing/translator) package, containing code shared between all categories of tests, including some generic TRAPI and Translator Status Dashboard scripts.
- Modules of the actual (Py)test harness under [tests](tests). At the moment, only one category of Translator of testing is implemented, that is, [One Hop Tests](tests/onehop/README.md).  Note that to run these tests, [KPs and ARAs need to configure web visible test data](tests/onehop/README.md#configuring-the-tests).
- The [Web Service API code](./api/README.md).
- The [Web User Interface code](./dashboard/README.md).

# SRI Testing as a Web Service

The SRI Testing Harness may be run as a Web Service. See [here](api/README.md) for more details.

# TRAPI Validation Dashboard

A nice web interface is available to browse through results of SRI Testing Harness test runs.  [Documentation about this web interface](dashboard/README.md) is available. The interface may also be deployed as a Docker container (see below).

A Translator Reference deployment of the web user interface, hosted by RENCI, is available at https://sri-testing.apps.renci.org.

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

Pointing a web browser to  http://localhost will display the Dashboard web interface to SRI Testing results (test runs on the filing system or in a Mongo database). Concurrently, the docker-compose has started up the web services container delivering the data to the Dashboard. This OpenAPI documentation of this service implementation may be directly viewed via the endpoint http://localhost:8090/docs  (the API paths themselves directly accessed via the endpoint).  Docker logs may be viewed in a streaming fashion by:

```shell
docker-compose logs -f
```

To stop the Docker containers:

```shell
docker-compose down
docker-compose -f run-mongodb.yaml down
```

Of course, the above `docker-compose` commands may be overridden by the user to suit their needs. Note that the docker implementation assumes the use of uvicorn (installed as a dependency).

## Limitations (and Future Work?)

- SRI Testing uses the reasoner-validator library which uses specific versions of the Biolink Model Toolkit. See the [list of reasoner-validator limitations](https://github.com/NCATSTranslator/reasoner-validator/blob/master/README.md#code-limitations-implied-future-work) for further details (e.g. why is my canonical predicate in my Biolink 2.4.8 compliant knowledge graph tagged as non-compliant?)

