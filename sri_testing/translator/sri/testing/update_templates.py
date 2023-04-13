import os
import json
import requests

kps = os.listdir("../../../../tests/onehop/templates/KP")
for kp in kps:
    kpis = os.listdir(f"templates/kp/{kp}")
    for kpi in kpis:
        with open(f"templates/kp/{kp}/{kpi}", "r") as kpij:
            kpjson = json.load(kpij)
            kpj_url = kpjson['url']
            if "http" in kpj_url:
                print(kp, kpi, kpj_url)
                kprequest = requests.get(kpj_url + "/meta_knowledge_graph")
                print(kprequest.status_code)
