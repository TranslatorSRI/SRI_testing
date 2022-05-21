"""
FastAPI web service wrapper for SRI Testing harness
(i.e. for reports to a Translator Runtime Status Dashboard)
"""
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel

import uvicorn
from fastapi import FastAPI

from reasoner_validator import DEFAULT_TRAPI_VERSION
from reasoner_validator.util import latest

# TODO: better to get 'latest' from BMT?
DEFAULT_BIOLINK_VERSION = "2.2.16"

app = FastAPI()


#
# We don't instantiate the full TRAPI models here but
# just use an open-ended dictionary which should have
# query_graph, knowledge_graph and results JSON tag-values
#
class TestRunParameters(BaseModel):
    # Which Test to Run?
    teststyle: Optional[str] = "all"

    # Only use first edge from each KP file
    one: bool = False

    # 'REGISTRY', directory or file from which to retrieve triples.
    # (Default: 'REGISTRY', which triggers the use of metadata, in KP entries
    # from the Translator SmartAPI Registry, to configure the tests).
    triple_source: Optional[str] = 'REGISTRY'

    # 'REGISTRY', directory or file from which to retrieve ARA Config.
    # (Default: 'REGISTRY', which triggers the use of metadata, in ARA entries
    # from the Translator SmartAPI Registry, to configure the tests).
    ARA_source: Optional[str] = 'REGISTRY'

    trapi_version: Optional[str] = DEFAULT_TRAPI_VERSION

    # optional Biolink Model version override against which
    # SRI Testing will be applied to Translator KPs and ARA's.
    # This version will override Translator SmartAPI Registry
    # KP entry specified x-translator specified model releases.
    biolink_version: Optional[str] = DEFAULT_BIOLINK_VERSION


@app.post("/run_tests")
async def run_tests(test_parameters: TestRunParameters):

    trapi_version = latest.get(test_parameters.trapi_version)
    biolink_version = test_parameters.biolink_version

    return {
        "session_id": str(uuid4())
    }


@app.get("/status/{session_id}")
def get_status(session_id: str):
    return {"session_id": session_id}


@app.get("/report/{session_id}")
async def get_results(session_id: str):
    return {"session_id": session_id}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
