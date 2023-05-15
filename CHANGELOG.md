# Change Log

The SRI Testing harness package is evolving along with progress in TRAPI (including the reasoner-validator package) and Biolink standards within the NCATS Biomedical Knowledge Translator. 

## v2.1.1

- Upgrade to reasoner-validator 3.4.16
- Validation of TRAPI being iteratively updated to include full semantic validation to TRAPI 1.4.0
- Upgraded validation of TRAPI Response output against test input edge data (i.e. full presence of original test data in the knowledge graph and results) 

## v2.1.0

- Upgrade to reasoner-validator 3.4.15
- Provided extra context for "error.trapi.request.invalid" validation error

## v2.0.0

- conversion to poetry dependency management
- Upgrade to reasoner-validator 3.3.3 (with modified validation message format)

## v1.1.5

- Upgrade to reasoner-validator 3.2.4
- clarified CLI docs, especially, use of ara_id SKIP and testing of subsets of (possibly wildcard) kp_id or ara_id identified services

## v1.1.4

- **/registry** data initialized globally as a singleton at application startup

## v1.1.3

Backend code made `x-maturity` and complex `info.x-trapi.test_data_location` aware:

- back end engine and web service API (but not yet UI) is fully x-maturity aware
    - **/registry** reports (lists of) x-maturity associated with KP and ARA resources
    - **/run_tests** accepts an optional `x-maturity` constraint (otherwise defaults to one sensible `x-maturity` per test run)
    - diverse reports now report x-maturity
- back end engine gracefully deals with diverse complex **info.x-trapi.test_data_location** specs
    - `x-maturity` constraints drive test data selection
    - lists of test data files (from lists of test data urls) are merged into single test edge data runs

## v1.1.0 - v1.1.2

- iterative refinements of UI

## v1.0.0

First substantial Production Release of SRI Testing:

- uses new reasoner-validator with ValidatorReporter - error, warning and information - messages with substantial Biolink Model validation support
- has a full web dashboard with overview, details and recommendations views
- added several utility API endpoints, including one to return the catalog of 'testable resources' from the Translator SmartAPI Registry

## v2.0.0