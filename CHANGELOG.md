# Change Log

The SRI Testing harness package is evolving along with progress in TRAPI (including the reasoner-validator package) and Biolink standards within the NCATS Biomedical Knowledge Translator. 

## v3.0.0
- Pruning the release 2# down to size as the SRI Testing 'lite' version, branch code-named 'Hoplite' (an ancient Greek civilian soldier). 'Hoplite' is essentially lacking the TRAPI schema and Biolink Model validation of TRAPI Responses and simply verifies that test input edges are recovered in the TRAPI Response results.  Setting the environment variable 'FULL_VALIDATION' to any non-empty value (default: None) triggers the original 'full' validation. The Test Run Summary JSON report has a 'mode' tag set accordingly either to value "FullComplianceValidation" or "HopLite".

## v2.2.0
- Upgrade to reasoner-validator 3.9.4: fixed methods moved into validation classes
- Upgrade to reasoner-validator 3.7.1: added 'sources' of validation messages to reports
- Upgrade to reasoner-validator 3.6.2 with additional repair of SRI Testing test edge validation in Response
- Upgrade to reasoner-validator 3.6.1 with 'critical' validation errors
- extracted OneHop test code relating to inverse predicate into get_inverse_predicate() method in BiolinkValidator class
- various TRAPI edge case validation against Knowledge Graph, moved from SRI Testing harness to TRAPIValidator class
- Upgraded to reasoner-validator 3.5.8 containing the above code
- refactored SRI Testing code to suit
- TRAPI call method moved to the reasoner-validator.trapi package module in release 3.5.6

## v2.1.7
- specify chokidar instead as a dev dependency

## v2.1.6
- Troubleshooting chokidar error in Dashboard deployment

## v2.1.5
- Updated the Dashboard UI to Node 20 / npm 9.6.6, fixing Docker deployments along the way. Updated UI now working.

## v2.1.4
- Upgraded to reasoner-validator 3.5.4

## v2.1.3
- Upgrade to reasoner-validator 3.4.22

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