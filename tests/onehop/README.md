# One-hop Tests

This suite tests the ability to retrieve given triples, which we know exist, from instances of **Translator Knowledge Provider** ("KP") under a variety of transformations, both directly, and indirectly, via instances of **Translator Autonomous Relay Agent** ("ARA").

- [Configuring the Tests](#configuring-the-tests)
    - [Translator SmartAPI Registry Configuration](#translator-smartapi-registry-configuration)
    - [KP Test Data Format](#kp-test-data-format)
      - [General Recommendations for Edge Test Data](#general-recommendations-for-edge-test-data)
      - [Excluding Tests](#excluding-tests)
      - [Biolink 3 Revisions](#biolink-3-revisions)
    - [ARA Test Configuration File](#ara-test-configuration-file)
- [Running the Tests](#running-the-tests)
    - [Running only the KP tests](#running-only-the-kp-tests)
    - [Running only the ARA tests](#running-only-the-ara-tests)
    - [Testing Fixed Sets of KP or ARA Tests](#testing-fixed-sets-of-kp-or-ara-services)
    - [TRAPI and Biolink Versioning](#trapi-and-biolink-versioning)
    - [Translator X-Maturity Environments](#translator-x-maturity-environments)
    - [Test CLI Help](#test-cli-help)
- [Test Results](#test-results)
- [What do the Validation Tests mean?](#what-do-the-validation-tests-mean)
    - [Validation Code](#validation-code)
    - [Biolink Model Compliance (Test Input Edges)](#biolink-model-compliance-test-input-edges)
    - [Provenance Checking (ARA Level)](#provenance-checking-ara-level)

## Configuring the Tests

### Translator SmartAPI Registry Configuration

The default operation of SRI Testing now relies on the interrogation of the Translator SmartAPI Registry ("Registry") for test configuration (meta-)data compiled and hosted externally to the SRI Testing harness itself. For this reason, the following Registry properties **must** be properly set for the testing to proceed:

- **info.x-translator.biolink-version:** _must_ be set to the actual Biolink Model release to which the given KP or ARA is asserting compliance. Validation to the 'wrong' Biolink Model version will generate unnecessary validation errors!
- **info.x-trapi.version:** _must_ be set to the TRAPI version to which the given KP or ARA is asserting compliance.
- **info.x-trapi.test_data_location:** see the full specification of the [info.x-trapi.test_data_location](https://github.com/NCATSTranslator/translator_extensions#x-trapi) for the range of formats now available for specifying SRI Testing harness test or configuration data files. URL's registered in whatever fashion within the **info.x-trapi.test_data_location:** values can typically (although not necessarily) be a URL to a Github public repository hosted file (note: this can be 'rawdata' URL or a regular Github URL - the latter is automatically rewritten to a 'rawdata' access for file retrieval). If a non-Github URL is given, it should be visible on the internet without authentication.  Lists of test data files (urls) are all functionally merged into a single set of test edges (annotated by test data knowledge source) for a given KP or ARA/KP component test suite. **_NOTE: THE GIVEN URL CURRENTLY NEEDS TO RESOLVE (AS A 'REST' RESOURCE) TO A SINGLE JSON FILE, NOT AS A FOLDER. THE TEST HARNESS IS NOT CURRENTLY DESIGNED TO HARVEST A FOLDER OF WEB FILES FROM THE GIVEN URL._**
- **servers block:** the SRI Testing harness now sets the TRAPI server endpoint used for testing of KP and ARA resources by selecting a **`url`** specified in the Registry `servers` block. 

Every test run only tests **_one_** endpoint within **_one_** **`x-maturity`** environment. The target **`x-maturity`** environment may now be explicitly specified as a **`/test_run`** API parameter. If omitted, then the **`x-maturity`** is selected based on available `servers` entries in the precedence ordering of '`production`', '`staging`', '`testing`' and '`development`'.  Since the Translator community has deemed all endpoints specified as equivalent when belonging to a specified **`x-maturity`**, the system simply selects the first live ('online') endpoint (ascertained by querying its TRAPI **`/meta_knowledge_graph`** API) within the given **`x-maturity`** list of endpoints. Note that future iterations of the system may revise the above selection heuristics based on Translator community policy decisions.

### KP Test Data Format

For each KP, we need a file with one triple of each type that the KP can provide. Here is an example:

```json
{ 
    "source_type": "primary",
    "infores": "automat",
    "exclude_tests": ["RPBS"],
    "edges": [
        {
            "subject_category": "biolink:AnatomicalEntity",
            "object_category": "biolink:AnatomicalEntity",
            "predicate": "biolink:subclass_of",
            "subject_id": "UBERON:0005453",
            "object_id": "UBERON:0035769"
        },
        {
            "exclude_tests": ["RSE"],
            "subject_category": "biolink:CellularComponent",
            "object_category": "biolink:AnatomicalEntity",
            "predicate": "biolink:subclass_of",
            "subject_id": "GO:0005789",
            "object_id": "UBERON:0000061"
        }
    ]
}
```

For provenance testing, we need to declare the reference ('object_id') identifier of the KP's InfoRes CURIE as a value of the `infores` JSON tag (mandatory). 

In addition, the type of knowledge source is declared, by setting the `source_type` JSON tag, to the prefix of the knowledge source type, i.e. `"primary"` for `biolink:primary_knowledge_source` or `"aggregator"` for `biolink:aggregator_knowledge_source`. Note that if the KP is a `biolink:aggregator_knowledge_source`, then the source_type tag-value is optional (since `"aggregator"` is the default value for a KP, if omitted).

This KP provides two kinds of edges for testing: `AnatomicalEntity-subclass_of->AnatomicalEntity` and `CellularComponent-subclass_of->AnatomicalEntity`. For each of these kinds of edges, we have an entry in the file with a specific `subject_id` and `object_id`, and from these, we can create a variety of tests.

To aid KPs in creating these json files, (some time ago) we generated templates in [templates/KP](templates/KP) using the predicates endpoint or SmartAPI Registry MetaKG entries, which contains the edge types (now likely badly out of date).

Note that the templates are built from KP metadata and are a good starting place, but they are not necessarily a perfect match to the desired test triples.
In particular, if a template contains an entry for two edges, where one edge can be fully calculated given the other, then there is no reason to include 
test data for the derived edge.  For instance, there is no need to include test data for an edge in one direction, and its inverse in the other direction. Here
we will be assuming (and testing) the ability of the KP to handle inverted edges whether they are specified or not.  Similarly, if a KP has
"increases_expression_of" edges, there is no need to include "affects_expression_of" in the test triples, unless there is data that is only known at the
more general level.  If, say, there are triples where all that is known is an "affects_expression_of" predicate, then that should be included.

So the steps for a KP:

1. Copy the KP template from the repository  [templates/KP](templates/KP) into a distinctly named file (Note: these templates are not directly used by the SRI Testing harness but just serve as a hint to KP test data curators on how to creat the required JSON test data file).
2. Edit the copied file to add or remove test data edges using the KP's metaknowledge graph catalog of S-P-O patterns as a guide, and specifying subject and object entries for each triple with a real identifiers that should be retrievable from the KP (Note: update the file to the latest standards as described above)
3. Publish the resulting file as a JSON resource [dereferenced by a test data location configured as described above](#translator-smartapi-registry-configuration) in the KP's Translator SmartAPI Registry entry.

#### General Recommendations for Edge Test Data

Experience with the SRI Testing harness suggests that KP test data curators (whether manual or script-based approaches) be mindful of the following guidelines for KP test edge data:

1. **"Less is More":** it is less important to be exhaustive than to shoot for quality with a tractable number of representative test edges from KP published meta_knowledge_graph _subject category--predicate->object category_ (SPO) patterns. Aiming for 10's of test edges (perhaps much less than 100 test edges) is preferred. For knowledge graphs with a large number of SPO patterns, consider rotating through a list of tractable sampling subsets to iterative resolve validation problems, a few use cases at a time. Edges which consistently pass in a given subset can be removed (although recorded somewhere for reuse in case, one needs to validate if future releases of the system have 'broken' the validation of such edges).
2. **Nature of node categories and edge predicates used in the test edges:** 
   1. Categories and predicates should _**not**_ be `abstract` nor `mixin` classes.   Use of `deprecated` `category` classes and `predicate` slots is in fact ok to detect the persistence of such classes or slots in the underlying KP generated knowledge graphs, but deprecated category classes and predicate slots will trigger a warning message.
   2. The test data should generally be the most specific SPO patterns and identifier instances that the KP knowledge graphs directly represent. In other words, test data edges should generally **_not_** use parent (ancestral) category classes (i.e. `biolink:NamedThing`) and predicate slots (i.e. `biolink:related_to`) in the test data, unless those are the most specific classes and slots actually used in the underlying knowledge graphs.
   3. Edge subject and object node identifiers (not the categories) should generally _**not**_ be Biolink CURIE terms, unless there is a compelling use case in the specific KP to do so.

A couple of examples _**not**_ compliant with the above principles would be a test data edges like the following:

```json
        {
            "subject_category": "biolink:NamedThing",
            "object_category": "biolink:NamedThing",
            "predicate": "biolink:related_to",
            "subject_id": "biolink:decreases_localization_of",
            "object_id": "biolink:localization_decreased_by"
        }
```
```json
        {
            "subject_category": "biolink:NamedThing",
            "object_category": "biolink:PathologicalEntityMixin",
            "predicate": "biolink:related_to",
            "subject_id": "UniProtKB:O15516",
            "object_id": "MESH:D004781"
        }
```
3. Note that the second example above also illustrates another issue: that `subject` and `object` identifiers need to have CURIE prefix (xmlns) namespaces that map onto the corresponding category classes (i.e. are specified in the Biolink Model `id_prefixes` for the given category).  This will be highlighted as a validation warning by the SRI Testing, but simply follows from the observation (above) the **UniProtKB** doesn't specifically map to `biolink:NamedThing` and **MESH** doesn't specifically map to a mixin (let alone `biolink:PathologicalEntityMixin`).

#### Excluding Tests

Note that the above KP JSON configuration has a pair of `exclude_tests` tag values.

Each unit test type in the [One Hop utility module](util.py) is a method marked with a `TestCode` method decorator that associates each test with a 2 - 4 letter acronym.  By including the acronym in a JSON array value for an (optional) tag `exclude_tests`, one or more test types from execution using that triple. 

A test exclusion tag (`exclude_tests`) may be placed at the top level of a KP file JSON configuration and/or within any of its triple entries, as noted in the above data KP template example. In the above example, the unit test corresponding to the "RPBS" test type ("_raise_predicate_by_subject_") is not run for any of the triples of the file, whereas the test type "RSE" ("_raise_subject_entity_") is only excluded for the one specific triple where it is specified. Note that test exclusion for a given triple is the union set of all test exclusions. A table summarizing the test codes for currently available tests (as of April 2022) is provided here for convenience (see the util.py file for more details):

| Test Name                  | Test Code |
|----------------------------|:---------:|
| by subject                 |    BS     |
| inverse by new subject     |   IBNS    |
| by object                  |    BO     |
| raise subject entity       |    RSE    |
| raise object entity        |    ROE    |
| raise object by subject    |   ROBS    |
| raise predicate by subject |   RPBS    |


#### Biolink 3 Revisions

The KP test edge format is [being extended to specify Biolink version 3 qualifier constraints](https://github.com/TranslatorSRI/SRI_testing/issues/60) in the following manner:

- **`association`**: (Optional) add edge category - value set to the id of any child class of **`biolink:Association`** - to assert associated semantic constraints in validating edge data from the specified test edge.
- **`subject_id`** and **`object_id`**: to replace **`subject`** and **`object`** tags, now deprecated. Same meaning as old tags just disambiguates the meaning of those tags (the older tags will still be recognized if used but disappear in future format releases).
- **`qualifiers`**: (Optional) new tag to specify Biolink Model 3.#.# **`qualifier`** constraints on testing, with JSON object composed of **`qualifier_type_id`** and **`qualifier_value`** values (as per the example below).

```json
{
    "source_type": "primary",
    "infores": "molepro",
    "exclude_tests": ["RPBS"],
    "edges": [
       {
            "subject_category": "biolink:SmallMolecule",  
            "object_category": "biolink:Disease",
            "predicate": "biolink:treats",
            "subject_id": "CHEBI:3002",
            "object_id": "MESH:D001249",
            "association": "biolink:ChemicalToDiseaseOrPhenotypicFeatureAssociation",
            "qualifiers": [
                 {
                      "qualifier_type_id": "biolink:causal_mechanism_qualifier",
                      "qualifier_value": "inhibition"
                 }
             ]
        }
   ]
}
```

### ARA Test Configuration File

For each ARA, we want to ensure that it is able to extract information correctly from the KPs.  To do this, we need to know which KPs each ARA interacts with.  Here is an example:

```json
{
    "infores": "aragorn",   
    "KPs": [
        "infores:automat-panther",
        "infores:automat-ontological-hierarchy"
    ]
}
```

The `infores` given is mandatory and is the 'object identifier' of InfoRes CURIE referring to the ARA itself.

In order to correctly link ARAs to KPs, ARAs will need to:

1. Copy the ARA template from the repository [templates/ARA](templates/ARA) into a distinctly named file.
2. Edit the copied file to add or remove KPs that the ARA does not access (Note: update the file to the latest standards as described above).
3. Publish the resulting file as a JSON resource [dereferenced by a test data location configured as described above](#translator-smartapi-registry-configuration) in the ARA's Translator SmartAPI Registry entry.

ARA test templates do not explicitly show the edges to be be tested, but rather, inherit the test data of their dereferenced KP's.  Once again, an infores tag value should be specified, in this case, for the ARA. However, all ARA's are expected to be `biolink:aggregator_knowledge_source` types of knowledge sources, hence, no `source_type` tag is needed (nor expected) here; however, they are checked for proper `'biolink:aggregator_knowledge_source': '<ARA infores CURIE>'` provenance declarations of their TRAPI knowledge graph edge attributes.

## Running the Tests

This section elaborates further on the information provided in the root project [Getting Started](../../README.md#getting-started) page (you have already read Getting Started, right?). Reiterating the initial setup steps:

```
git clone https://github.com/TranslatorSRI/SRI_testing
cd SRI_testing
poetry install
poetry shell
```

configures your poetry (shell) and pytest environment to be ready to run the following tests in various ways  (Note: if you decide to run the tests _outside_ of a poetry shell, then you'll need to prefix the pytest commands  with `poetry run`).

Once again, if you are tempted to run the One Hop tests on **all** of the available KP and ARA resources, you would type the following from *within* the tests/onehop project subfolder:

```bash
pytest test_onehops.py
```

As previously mentioned in the **_Getting Started_** section, such a full test run on **_all_** resources will be very computationally intensive, and also makes a variety of run-time assumptions that may not necessarily meet your needs. Thus, you may wish to constrain the run in various ways, as to be mentioned below.

Also, the raw pytest output will be verbose and opaque to human interpretation. 

However, the full One Hop test results are captured and reformatted into (slightly more) human-readable JSON documents which may either be stored on the local filing system under the 'test_results' folder (adjacent to the test_onehops.py script) or (or, in MongoDb, if [MongoDb is running and properly configured](../../README.md#database-for-the-test-results)). We will review a bit later, the content and various ways in which such JSON result files may be accessed and viewed.

### Running only the KP tests

To only run tests on all Translator SmartAPI Registry catalogued KP resources:
```
pytest test_onehops.py::test_trapi_kps
```

To run KP Tests, but only using one triple from each KP test data file:
```
pytest test_onehops.py::test_trapi_kps --one
```

To restrict test triples to one accessed from a specific KP resource from the Translator SmartAPI Registry, KP test data file dereferenced by the [**info.x-trapi.test_data_location**  specification defined in the KP entry in the Translator SmartAPI Registry](https://github.com/NCATSTranslator/translator_extensions#x-trapi) corresponding to the KP object id of the Infores CURIE of the target KP, i.e. **`automat-sri-reference-kg`** (for **`infores:automat-sri-reference-kg`**):

```
pytest test_onehops.py --kp_id=<kp infores reference>
```

for example:

```
pytest test_onehops.py --kp_id="automat-sri-reference-kg"
```

Note, however, that the KP will also be tested within every ARA that calls it (the default when the `--ara_id` (below) is omitted or empty).  In order to restrict testing solely to the KP(s) specified (and not any ARA calling it), a special **--ara_id** value 'SKIP' needs to be used, namely:

e.g.
```
pytest test_onehops.py --kp_id="molepro" --ara_id="SKIP" 
```

Will only test the MolePro KP and not any ARA calling MolePro.

### Running the ARA tests

Running tests for individual ARAs may be run with the **--ara_id** directive:

```
pytest test_onehops.py --ara_id=<ara infores reference>
```

for example:

```
pytest test_onehops.py --ara_id="arax"
```

This will run tests with test data from all KPs specified in the JSON ARA test configuration file "KPs" section, which also concurrently have valid test data dereferenced by the **info.x-trapi.test_data_location**  specifications defined in the corresponding KP entries.

Constraining the test to one KP accessed via a given ARA may be achieved by combining the --ara_id and --kp_id directives:

```
pytest test_onehops.py --ara_id=<ara infores reference> --kp_id=<kp infores reference>
```

For example:

```
pytest test_onehops.py --ara_id="arax" --kp_id="molepro"
```

## Translator X-Maturity Environments

To constrain testing to one specific [X-Maturity environment](https://github.com/NCATSTranslator/TranslatorArchitecture/blob/master/SmartAPIRegistration.md#environments) say, 'staging'), use the **`--x_maturity`** directive:

```
pytest test_onehops.py --ara_id="arax" --kp_id="molepro" --x_maturity="staging"
```

### Testing Fixed Sets of KP or ARA Services

Either or both of the `--kp_id` or `--ara_id` arguments may be comma delimited list of identifiers. For example:

```
pytest test_onehops.py --kp_id="sri-reference-kg,molepro"
```
will test both the SRI Reference KG and MolePro knowledge providers.  A list of ARA's may be specified in the same way (in the `--ara_id` flag value).

In addition to exact matching of identifiers, simple wildcard identifier patterns may be given, using an asterix as a one or more characters match.

e.g.
```
pytest test_onehops.py --kp_id="automat-*"
```
will test all the **automat** prefixed KP's listed in the Translator SmartAPI Registry.  

Note that a suffix pattern or double sided pattern also works:

```
pytest test_onehops.py --kp_id="*-drug-central"
```
will match **automat-drug-central** and

```
pytest test_onehops.py --kp_id="service-*-trapi"
```
will match **service-provider-trapi**.

### TRAPI and Biolink Versioning

The tests may be globally constrained to validate against a specified TRAPI and/or Biolink Version, as follows:

```shell
pytest test_onehops.py --trapi_version ="1.4" --biolink_version="3.0.3"
```

## Translator X-Maturity Environments

To constrain testing to one specific x-maturity environment (say, 'testing'), use the **`--x_maturity`** directive:

```
pytest test_onehops.py --ara_id="arax" --kp_id="molepro" --x_maturity="testing"
```

## Test CLI Help

The full set of the currently available command line options may be viewed using the help function:

```shell
pytest test_onehops.py --help
```

The above SRI Testing-specific parameters are described as PyTest custom options:

```
  --test_run_id=TEST_RUN_ID
                        Optional Test Run Identifier for internal use to index test results.
  --trapi_version=TRAPI_VERSION
                        TRAPI API version to use for validation, overriding Translator SmartAPI Registry property value (Default: latest public release or ).
  --biolink_version=BIOLINK_VERSION
                        Biolink Model SemVer-compliant version to use for validation, overriding Translator SmartAPI Registry property value. Note that a value of this parameter may also be "suppress" in which case, Biolink Model validation is suppressed during the test run. (Default: latest public release).
  --kp_id=KP_ID         Knowledge Provider identifier ("KP") targeted for testing (Default: None).
 
  --ara_id=ARA_ID       Autonomous Relay Agent ("ARA") targeted for testing (Default: None).
  
  --x_maturity=X_MATURITY
                        Target x_maturity server environment for testing (Default: None).
  
  --teststyle=TESTSTYLE Which One Hop unit test to run?
  
  --one                 Only use first edge from each KP file

```

## Test Results

The above test runs will produce a somewhat verbose and opaque regular Pytest console output. However, the results are reformatted into a more helpful set of structured JSON files.  These JSON  files may either be captured into a [running instance of a Mongo database](#database-for-the-test-results) or (by default) locally dumped onto the local filing system under the **_tests/onehop/test_results_** subfolder within date time stamp-indexed directories, looking something like the following (specific test run details will differ):

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

Briefly, the output files - slightly overlapping in terms of information provided - contain the following information:

- **test_run_summary.json:** top-level summary counts of pass/fail/skip results indexed by KP and/or ARA
- **resource_summary.json:** detailed resource-specific test results aggregated by test edges
- **recommendations.json:** detailed resource-specific test results test results merged by validation codes
- **Set of <KP or ARA resource id>-#.json files:** detailed result summary by test edge, including the original TRAPI Request JSON for each test, generated for the given test edge
- **Set of <KP or ARA resource id>-#-<test id>.json files:** for individual failed tests, the full TRAPI Response JSON by test edge and unit test name

Note that each type of file is accessible through the [web services API](../../api/README.md)  and the content of the individual JSON files are mainly driven by the target functionality of [the Web Dashboard](../../README.md#testing-engine-and-web-dashboard), which renders the content of these result files in a more human-readable fashion.

Further details about the nature of the unit tests is [described in the following section](#what-do-the-validation-tests-mean). 

## What do the Validation Tests mean?

The overall strategy of the SRI Testing Harness is explained in a [slide presentation here](https://docs.google.com/presentation/d/1p9n-UjMNlhWCyQrbI2GonsQKXz0PFdi4-ydDcrF5_tc).

The tests are dynamically generated from the test data Subject-Predicate-Object ("S-P-O") statement triples ('edges') retrieved from KP component owner curated [KP Test Data Formatted files](#kp-test-data-format) noted above. Similarly, [ARA Test Configuration JSON Files](#ara-test-configuration-file) prepared by ARA component owners indicate which KP's they access, directing that suitable test TRAPI queries be attempted using KP-specified test data.

Either way, each KP S-P-O test triple is used to generate set of several distinct types of unit tests (see the [One Hop utility module](util.py) for the specific code dynamically generating each specific TRAPI query test message within the unit test set for that triple).  The following specific unit tests are currently available:

- by subject
- inverse by new subject
- by object
- raise subject entity
- raise object entity
- raise object by subject
- raise predicate by subject

A more complete description of each unit test is provided [here](https://translator-reasoner-validator.readthedocs.io/en/latest/).

Instances of ARA being tested are similarly configured for testing their expected outputs using the list of KPs noted a corresponding JSON configuration files also [dereferenced by a specified test data location](#translator-smartapi-registry-configuration).

For some KP resources or maybe, just specific instances of triples published by the KP, some unit tests are anticipated _a priori_ to fail (i.e. the resource is not expected to have sufficient knowledge to answer the query). In such cases, such specific unit tests may be excluded from execution (see below).

### Validation Code

The SRI Testing harness delegates most validation operations to the [reasoner-validator library](https://github.com/NCATSTranslator/reasoner-validator), which itself delegates TRAPI schema validation to jsonschema run against the [TRAPI schema](https://github.com/NCATSTranslator/ReasonerAPI) and validates Biolink Model semantics via the [Biolink Model Toolkit](https://github.com/biolink/biolink-model-toolkit).  In fact, the reasoner-validator module may be directly used programmatically to conduct validation of TRAPI messages outside of the SRI Testing harness, giving essentially identical results to those seen within the test harness.

### Biolink Model Compliance (Test Input Edges)

While being processed for inclusion into a test, every KP input S-P-O triple is screened for Biolink Model Compliance during the test setup against the specified release of the Biolink Model (see below). This validation issues  informational, warning and error messages. This validation takes place within the `generate_trapi_kp_tests()` KP use case set up method in the **test.onehop.conftest** module. Edges with a non-zero list of error messages are so tagged as _'biolink_errors'_, which later advises the generic KP and ARA unit tests - within the PyTest run in the **tests.onehops.test_onehops** module - to formally skip the specific edge-data-template defined use case and report those errors.

### Provenance Checking (ARA Level)

Provenance checking is attempted on the edge attributes of the TRAPI knowledge graph within the `test_trapi_aras` method in **tests.onehops.test_onehops** module. The provenance checking directly raises `AssertError` exceptions to report specific TRAPI message failures to document the provenance of results (as proper `knowledge_source` related attributes expected for ARA and KP annotated edge attributes of the TRAPI knowledge graph).
