# SRI Testing Package

- [Jupyter Notebook to facilitate access to Translator SmartAPI TRAPI entries for KPs and ARAs](SmartAPI.ipynb) in the Translator SmartAPI Registry.
- Scripts:
    - [`create_template.py`](create_templates.py) to create testing templates by interrogation of the Translator SmartAPI Registry.
    - [`report_missing_predicates.py`](report_missing_predicates.py) to report predicates missing in a specified Biolink Model release. Optional command line argument is a SemVer of the release to target.
    - [`status_dashboard_data.py`](status_dashboard_data.py) to capture Translator Dashboard Status data
- [Utility Package](util).
