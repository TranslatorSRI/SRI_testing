"""
Registry package
"""
from os import getenv

# Setting the following flag to 'True' triggers use of the
# local 'mock' Registry data entries immediately below
MOCK_REGISTRY: bool = getenv('MOCK_REGISTRY', default=False)


def mock_registry(status: bool):
    global MOCK_REGISTRY
    MOCK_REGISTRY = status


# This 'mock' registry entry relies a bit on ARAGORN (Ranking Agent)
# and the RENCI Automat KP's, which may sometimes be offline?
MOCK_TRANSLATOR_SMARTAPI_REGISTRY_METADATA = {
    "total": 3,
    "hits": [
        {
            "info": {
                "title": "SRI Reference Knowledge Graph API (trapi v-1.3.0)",
                "version": "1.3.0-1",
                "x-translator": {
                    "component": "KP",
                    "infores": "infores:sri-reference-kg",
                    "team": ["SRI"],
                    "biolink-version": "2.4.7"
                },
                "x-trapi": {
                    "version": "1.3.0",
                    "test_data_location": "https://raw.githubusercontent.com/monarch-initiative/" +
                                          "monarch-plater-docker/main/test_data/sri_reference_kg_test_data.json"
                }
            },
            "servers": [
                {
                    "description": "Default server",
                    "url": "https://automat.renci.org/sri-reference-kg/1.3",
                    "x-location": "ITRB",
                    "x-maturity": "testing"
                 }
            ]
        },
        #
        # MolePro used as a part of MOCK Registry
        #
        {
            'info': {
                'contact': {
                    'email': 'translator@broadinstitute.org',
                    'name': 'Molecular Data Provider',
                    'x-role': 'responsible organization'
                },
                'description': 'Molecular Data Provider for NCATS Biomedical Translator',
                'title': 'MolePro',
                'version': '1.3.0.0',
                'x-translator': {
                    'biolink-version': '2.4.7',
                    'component': 'KP',
                    'infores': 'infores:molepro',
                    'team': ['Molecular Data Provider']
                },
                'x-trapi': {
                     'test_data_location': 'https://github.com/broadinstitute/molecular-data-provider/blob/master/test/data/MolePro-test-data.json',
                     'version': '1.3.0'
                 }
            },
            'servers': [
                {
                    'description': 'TRAPI production service for MolePro',
                    'url': 'https://molepro-trapi.transltr.io/molepro/trapi/v1.3',
                    'x-maturity': 'production'
                },
                {
                    'description': 'TRAPI test service for MolePro',
                    'url': 'https://molepro-trapi.test.transltr.io/molepro/trapi/v1.3',
                    'x-maturity': 'testing'
                },
                {
                    'description': 'TRAPI staging service for MolePro',
                    'url': 'https://molepro-trapi.ci.transltr.io/molepro/trapi/v1.3',
                    'x-maturity': 'staging'
                },
                {
                    'description': 'TRAPI development service for MolePro',
                    'url': 'https://translator.broadinstitute.org/molepro/trapi/v1.3',
                    'x-maturity': 'development'
                }
            ],
        },
        #
        # ARAX Endpoint as test ARA
        #
        {
            'info': {
                'contact': {
                    'email': 'edeutsch@systemsbiology.org'
                },
                'description': 'TRAPI 1.3 endpoint for the NCATS Biomedical Translator Reasoner called ARAX',
                'license': {
                     'name': 'Apache 2.0',
                     'url': 'http://www.apache.org/licenses/LICENSE-2.0.html'
                },
                'termsOfService': 'https://github.com/RTXteam/RTX/blob/master/LICENSE',
                'title': 'ARAX Translator Reasoner - TRAPI 1.3.0',
                'version': '1.3.0',
                'x-translator': {
                    'biolink-version': '2.2.11',
                    'component': 'ARA',
                    'infores': 'infores:arax',
                    'team': ['Expander Agent']
                },
                'x-trapi': {
                    # We substitute a pared down version of the ARAX ARA test_data_location JSON here in this repo
                    # 'test_data_location': 'https://raw.githubusercontent.com/RTXteam/RTX/' +
                    #                       'master/code/ARAX/Documentation/arax_kps.json',
                    'test_data_location': 'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                                          'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                    'version': '1.3.0'
                }
            },
            'servers': [
                {
                    'description': 'ARAX TRAPI 1.3 endpoint - production',
                    'url': 'https://arax.ncats.io/api/arax/v1.3',
                    'x-maturity': 'production'
                }, {
                    'description': 'ARAX TRAPI 1.3 endpoint - testing',
                    'url': 'https://arax.test.transltr.io/api/arax/v1.3',
                    'x-maturity': 'testing'
                }, {
                    'description': 'ARAX TRAPI 1.3 endpoint - staging',
                    'url': 'https://arax.ci.transltr.io/api/arax/v1.3',
                    'x-maturity': 'staging'
                }, {
                    'description': 'ARAX TRAPI 1.3 endpoint - development',
                    'url': 'https://arax.ncats.io/beta/api/arax/v1.3',
                    'x-maturity': 'development'
                }
            ],
        }
    ]
}
