# Translator Reasoner Application Programming Interface Utilities

Package of methods to:

- Manage global **TRAPI** versioning (`set_trapi_version`, `get_trapi_version`)
- Validate candidate TRAPI JSON `message` bodies against the specified TRAPI version (`is_valid_trapi`)
- Validate `message` provenance (`check_provenance`- currently just a stub function)
- Make a call on a specified TRAPI endpoint (`call_trapi`).
- Execute a created TRAPI query to a (KP or ARA) resource using a TRAPI call (`execute_trapi_lookup`).