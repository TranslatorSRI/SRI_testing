from typing import Optional
from os import environ
# just set this environment variable to trigger
# full TRAPI and Biolink Model validation
FULL_VALIDATION: Optional[str] = environ.get("FULL_VALIDATION", None)
