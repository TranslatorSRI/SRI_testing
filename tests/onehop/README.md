# One-hop Tests

This suite tests the ability to retrieve given triples, which we know exist, from instances of **Translator Knowledge Provider** ("KP") under a variety of transformations, both directly, and indirectly, via instances of **Translator Autonomous Relay Agent** ("ARA").

- [Configuring the Tests](#configuring-the-tests)
    - [Translator SmartAPI Registry Configuration](#translator-smartapi-registry-configuration)
    - [KP Test Data Format](#kp-test-data-format)
        - [Excluding Tests](#excluding-tests)
    - [ARA Test Configuration File](#ara-test-configuration-file)
- [Running the Tests](#running-the-tests)
    - [Running only the KP tests](#running-only-the-kp-tests)
    - [Running only the ARA tests](#running-only-the-ara-tests)
- [How the Framework works](#how-the-one-hop-tests-work)
    - [Biolink Model Compliance (Test Input Edges)](#biolink-model-compliance-test-input-edges)
    - [Provenance Checking (ARA Level)](#provenance-checking-ara-level)

## Configuring the Tests

### Translator SmartAPI Registry Configuration

The default operation of SRI Testing now relies on the interrogation of the Translator SmartAPI Registry ("Registry") for test configuration (meta-)data compiled and hosted externally to the SRI Testing harness itself. For this reason, the following Registry properties **must** be properly set for the testing to proceed:

- **info.x-translator.biolink-version:** _must_ be set to the actual Biolink Model release to which the given KP or ARA is asserting compliance. Validation to the 'wrong' Biolink Model version will generate unnecessary validation errors!
- **info.x-trapi.version:** _must_ be set to the TRAPI version to which the given KP or ARA is asserting compliance.
- **info.x-trapi.test_data_location:** _must_ be a public REST resource URL dereferencing the online JSON test configuration file (see KP and ARA instructions below). This can typically (although not necessarily) be a URL to a Github public repository hosted file (note: this can be 'rawdata' URL or a regular Github URL - the latter is automatically rewritten to a 'rawdata' access for file retrieval). If a non-Github URL is given, it should be visible on the internet without authentication.
- **servers block:** testing now sets the TRAPI server endpoint for testing using a **`url`** specified in the Registry 'servers' block. Lack of standardization of testing targets means that the system is currently agnostic about **`x-maturity`** but simply takes the first **`servers`** block entry with a '**`url`**' property set. If there is more than one server entry in the **`servers`** block, then the wrong testing endpoint may be used. Note that future iterations of the system may follow a different heuristic which recognizes the **`x-maturity`** property.

**Note:** the **info.x-trapi.test_data_location** may change in the near future to accommodate the need for differential testing across various `x-maturity` deployments of KPs and ARAs.

### KP Test Data Format

For each KP, we need a file with one triple of each type that the KP can provide.  For instance, `test_triples/KP/Test_KP/Automat_Human_GOA.json` contains the following json:

```
{
    "url": "https://automat.renci.org/ontological-hierarchy/1.2",
    "source_type": "original",
    "infores": "automat",
    "exclude_tests": ["RPBS"],
    "edges": [
        {
            "subject_category": "biolink:AnatomicalEntity",
            "object_category": "biolink:AnatomicalEntity",
            "predicate": "biolink:subclass_of",
            "subject": "UBERON:0005453",
            "object": "UBERON:0035769"
        },
        {
            "exclude_tests": ["RSE"],
            "subject_category": "biolink:CellularComponent",
            "object_category": "biolink:AnatomicalEntity",
            "predicate": "biolink:subclass_of",
            "subject": "GO:0005789",
            "object": "UBERON:0000061"
        }
    ]
}
```

The `url` tag **must** be a well-formed _resolvable_ TRAPI URL (namely, with **http://** or **https://** scheme).

For provenance testing, we need to declare the KP's infores CURIE as a value of the `infores` JSON tag (mandatory). 

In addition, the type of knowledge source is declared, by setting the `source_type` JSON tag, to the prefix of the knowledge source type, i.e. `"original"` for `biolink:original_knowledge_source`, `"primary"` for `biolink:primary_knowledge_source` or `"aggregator"` for `biolink:aggregator_knowledge_source`. Note that if the KP is a `biolink:aggregator_knowledge_source`, then the source_type tag-value is optional (since `"aggregator"` is the default value for a KP).

This KP provides two kinds of edges for testing: `AnatomicalEntity-subclass_of->AnatomicalEntity` and `CellularComponent-subclass_of->AnatomicalEntity`. For each of these kinds of edges, we have an entry in the file with a specific `subject` and `object`, and from these, we can create a variety of tests.

To aid KPs in creating these json files, we have generated templates in `templates/KP` using the predicates endpoint or smartAPI Registry MetaKG entries, which contains the edge types.
Note that the templates are built from KP metadata and are a good starting place, but they are not necessarily a perfect match to the desired test triples.
In particular, if a template contains an entry for two edges, where one edge can be fully calculated given the other, then there is no reason to include 
test data for the derived edge.  For instance, there is no need to include test data for an edge in one direction, and its inverse in the other direction. Here
we will be assuming (and testing) the ability of the KP to handle inverted edges whether they are specified or not.  Similarly, if a KP has
"increases_expression_of" edges, there is no need to include "affects_expression_of" in the test triples, unless there is data that is only known at the
more general level.  If, say, there are triples where all that is known is an "affects_expression_of" predicate, then that should be included.

So the steps for a KP:

1. copy a template json from `templates` into a distinctly named file in a suitable (KP-specific) subfolder location inside `test_triples/KP`
2. filter out logically derivable template entries
3. fill in the subject and object entries for each triple with a real identifiers that should be retrievable from the KP

Note: you can selectively exclude specific KP configuration files or whole subfolders of such files from execution by appending *_SKIP* to the specific file or subfolder name (see below for finer grained test exclusions).

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
            "subject": "biolink:decreases_localization_of",
            "object": "biolink:localization_decreased_by"
        }
```
```json
        {
            "subject_category": "biolink:NamedThing",
            "object_category": "biolink:PathologicalEntityMixin",
            "predicate": "biolink:related_to",
            "subject": "UniProtKB:O15516",
            "object": "MESH:D004781"
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
| raise object by subject    |   ROBS    |
| raise predicate by subject |   RPBS    |

### ARA Test Configuration File

For each ARA, we want to ensure that it is able to extract information correctly from the KPs.  To do this, we need to know which KPs each ARA interacts with.  We have generated template ARA json files under `templates/ARA` that contains annotations linking the ARA to all KPs.  For instance (under _tests/onehop/test_triples/ARA/Test_ARA/ARAGORN.json_):

```
{
    "url": "https://aragorn.renci.org/1.2",
    "infores": "aragorn",   
    "KPs": [
        "Automat Panther",
        "Automat Ontological Hierarchy"
    ]
}
```
Once again, the `url` tag **must** be a well-formed _resolvable_ TRAPI URL (namely, with **http://** or **https://** scheme).

The `infores` given is mandatory and is the 'object identifier' of InfoRes CURIE referring to the ARA itself.

In order to correctly link ARAs to KPs, ARAs will need to:

1. Copy the ARA template from `templates` into a distinctly named file, in a suitable (ARA-specific) subfolder location inside `test_triples/ARA`
2. Edit the copied file to remove KPs that the ARA does not access.

Note: as with the KP template files, you can selectively exclude complete ARA test files or whole subfolders of such files from execution, by appending *_SKIP* to the specific file or subfolder name. 

ARA test templates do not explicitly show the edges to be be tested, but rather, inherit the test data of their dereferenced KP's.  Once again, an infores tag value should be specified, in this case, for the ARA. However, all ARA's are expected to be `biolink:aggregator_knowledge_source` types of knowledge sources, hence, no `source_type` tag is needed (nor expected) here; however, they are checked for proper `'biolink:aggregator_knowledge_source': '<ARA infores CURIE>'` provenance declarations of their TRAPI knowledge graph edge attributes.


## Running the Tests

Tests are implemented with pytest.  To run all tests, from _within_ the `tests/onehop` project subdirectory, simply run:

```
pytest test_onehops.py
```

But this likely takes quite some time, so frequently you will want to limit the tests run.

### Running only the KP tests

To run only KP tests:
```
pytest test_onehops.py::test_trapi_kps
```

To run KP Tests, but only using one triple from each KP:
```
pytest test_onehops.py::test_trapi_kps --one
```

To restrict test triples to one accessed from "REGISTRY" (the default value), that is, KP test data files retrieved from the 'test_data_location' URL defined in the KP records in the Translator SmartAPI Registry Translatorthose from a given directory or file:
```
pytest test_onehops.py::test_trapi_kps --triple_source=<triple_source>
```
e.g.
```
pytest test_onehops.py::test_trapi_kps --triple_source=test_triples/KP/Unit_Test_KP
```
or
```
pytest test_onehops.py::test_trapi_kps --triple_source=test_triples/KP/Unit_Test_KP/Test_KP.json
```

The tests may be globally constrained to validate against a specified TRAPI and/or Biolink Version, as follows:

```shell
pytest test_onehops.py::test_trapi_kps --TRAPI_Version ="1.2" --Biolink_Version="2.2.0"
```

The full set of available command line options may be viewed using the help function:


```shell
pytest test_onehops.py --help
```

These include the following Testing-specific custom options:

```
  --teststyle=TESTSTYLE
                        Which Test to Run?
  --one                 Only use first edge from each KP file
  --triple_source=TRIPLE_SOURCE
                        'REGISTRY', directory or file from which to retrieve triples.
                        (Default: 'REGISTRY', which triggers the use of metadata, in KP entries
                        from the Translator SmartAPI Registry, to configure the tests).
  --ARA_source=ARA_SOURCE
                        'REGISTRY', directory or file from which to retrieve ARA Config.
                        (Default: 'REGISTRY', which triggers the use of metadata, in ARA entries
                        from the Translator SmartAPI Registry, to configure the tests).
  --TRAPI_Version=TRAPI_VERSION
                        TRAPI API Version to use for the tests 
                        (Default: latest public release or REGISTRY metadata value).
  --Biolink_Version=BIOLINK_VERSION
                        Biolink Model Version to use for the tests
                        (Default: latest Biolink Model Toolkit default or REGISTRY metadata value).
```

### Running only the ARA tests

The ARA tests cannot generally be run in isolation of the above KP tests (given their dependency on the generation of the KP test cases).


## How the One Hop Tests Work

The overall strategy of the SRI Testing Harness is explained in a [slide presentation here](https://docs.google.com/presentation/d/1p9n-UjMNlhWCyQrbI2GonsQKXz0PFdi4-ydDcrF5_tc).

The tests are dynamically generated from sample data Subject-Predicate-Object ("S-P-O") statement triples for each KP with test data rewtrieved from JSON test data/configuration files published online by KP (ARA) owners as web accessible JSON REST document resources (typically, a document in a Github repository) [dereferenced by a test data location configured as described above](#translator-smartapi-registry-configuration).

The KP files contain sample data for each triple that the KP can provide.  Each triple noted therein is used to build a set of distinct types of unit tests (see the [One Hop utility module](util.py) for the specific code dynamically generating each specific TRAPI query test message within the unit test set for that triple).  The following specific unit tests are currently available:

- by subject
- inverse by new subject
- by object
- raise subject entity
- raise object by subject
- raise predicate by subject

See the [aforementioned slide presentation](https://docs.google.com/presentation/d/1p9n-UjMNlhWCyQrbI2GonsQKXz0PFdi4-ydDcrF5_tc) for specific details about each unit test.

Instances of ARA being tested are similarly configured for testing their expected outputs using the list of KPs noted a corresponding JSON configuration files also [dereferenced by a specified test data location](#translator-smartapi-registry-configuration).

For some KP resources or maybe, just specific instances of triples published by the KP, some unit tests are anticipated _a priori_ to fail (i.e. the resource is not expected to have sufficient knowledge to answer the query). In such cases, such specific unit tests may be excluded from execution (see below).

### Biolink Model Compliance (Test Input Edges)

While being processed for inclusion into a test, every KP input S-P-O triple is screened for Biolink Model Compliance during the test setup by calling a function `check_biolink_model_compliance()` implemented in the **translator.sri.testing** package module. This method runs a series of tests against templated edge - using the specified release of the Biolink Model (see below) documenting validation - informational, warning and error - messages. This function is called within the `generate_trapi_kp_tests()` KP use case set up method in the **test.onehop.conftest** module. Edges with a non-zero list of error messages are so tagged as _'biolink_errors'_, which later advises the generic KP and ARA unit tests - within the PyTest run in the **tests.onehops.test_onehops** module - to formally skip the specific edge-data-template defined use case and report those errors. 

**Note:** at the moment, the Test harness reports the identical Biolink Model violation for all unit tests on the defective edge. This test output duplication is a bit verbose but tricky to avoid (some clever Testing PyTest logic - as yet unimplemented - may be needed to avoid this).

### Provenance Checking (ARA Level)

Provenance checking is attempted on the edge attributes of the TRAPI knowledge graph, by the `check_provenance()` method, called by the `test_trapi_aras` method in **tests.onehops.test_onehops** module. The `check_provenance()` method directly raises `AssertError` exceptions to report specific TRAPI message failures to document the provenance of results (as proper `knowledge_source` related attributes expected for ARA and KP annotated edge attributes of the TRAPI knowledge graph).
