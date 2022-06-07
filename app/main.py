"""
FastAPI web service wrapper for SRI Testing harness
(i.e. for reports to a Translator Runtime Status Dashboard)
"""
from typing import Optional, Union, List, Dict
from pydantic import BaseModel

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from reasoner_validator.util import latest
from app.util import OneHopTestHarness, DEFAULT_WORKER_TIMEOUT, SRITestReport

app = FastAPI()

origins = [
    "http://localhost:8080",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
#
# We don't instantiate the full TRAPI models here but
# just use an open-ended dictionary which should have
# query_graph, knowledge_graph and results JSON tag-values
#
class TestRunParameters(BaseModel):

    # TODO: we ignore the other SRI Testing parameters
    #       for the initial design of the web service
    #
    # # Which Test to Run?
    # teststyle: Optional[str] = "all"
    #
    # # Only use first edge from each KP file
    # one: bool = False
    #
    # # 'REGISTRY', directory or file from which to retrieve triples.
    # # (Default: 'REGISTRY', which triggers the use of metadata, in KP entries
    # # from the Translator SmartAPI Registry, to configure the tests).
    # triple_source: Optional[str] = 'REGISTRY'
    #
    # # 'REGISTRY', directory or file from which to retrieve ARA Config.
    # # (Default: 'REGISTRY', which triggers the use of metadata, in ARA entries
    # # from the Translator SmartAPI Registry, to configure the tests).
    # ara_source: Optional[str] = 'REGISTRY'

    # Optional TRAPI version override override against which
    # SRI Testing will be applied to Translator KPs and ARA's.
    # This version will override Translator SmartAPI Registry
    # KP or ARA entry specified 'x-trapi' metadata tag value
    # specified TRAPI version (Default: None).
    trapi_version: Optional[str] = None

    # optional Biolink Model version override against which
    # SRI Testing will be applied to Translator KPs and ARA's.
    # This version will override Translator SmartAPI Registry
    # KP entry specified 'x-translator' metadata tag value
    # specified Biolink Model version (Default: None)..
    biolink_version: Optional[str] = None

    # Worker Process data access timeout; defaults to DEFAULT_WORKER_TIMEOUT
    # which implies caller blocking until the data is available
    timeout: Optional[int] = DEFAULT_WORKER_TIMEOUT


@app.post("/run_tests")
async def run_tests(test_parameters: TestRunParameters) -> Dict:

    trapi_version: Optional[str] = latest.get(test_parameters.trapi_version) if test_parameters.trapi_version else None
    biolink_version: Optional[str] = test_parameters.biolink_version

    testrun = OneHopTestHarness(test_parameters.timeout)
    session_id: str = testrun.run(
        trapi_version=trapi_version,
        biolink_version=biolink_version
    )

    return {
        "session_id": session_id,

        # TODO: user specified TRAPI version...
        #       we should somehow try to report the
        #       actual version used by the system
        # "trapi_version": trapi_version,

        # TODO: user specified Biolink Model version...
        #       we should somehow try to report the
        #       actual version used by the system
        # "biolink_version": biolink_version,
    }


@app.get("/report/{session_id}")
async def get_report(session_id: str):
    report: Optional[Union[str, SRITestReport]] = OneHopTestHarness.get_report(session_id)
    return {
        "session_id": session_id,
        "report": report
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
