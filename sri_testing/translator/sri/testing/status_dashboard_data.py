import requests
# import pandas as pd
import json

from sri_testing.translator.registry import SMARTAPI_URL, query_smart_api, iterate_services_from_registry


def get_meta_kg(server_url, meta_path):
    data = None
    try:
        request = requests.get(server_url + meta_path)
        if request.status_code == 200:
            data = request.json()
    except Exception as e:
        print(e)
    return data


registry_data = query_smart_api(SMARTAPI_URL)
service_data = iterate_services_from_registry(registry_data)
with open("../../../dashboard_data/translator_services_status.json", 'w') as tss:
    json.dump(service_data, tss)
