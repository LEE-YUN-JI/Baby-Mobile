import requests

url = 'https://kauth.kakao.com/oauth/token'
rest_api_key = '1dc6c5c352ace9f21024a052a2b850c3'
redirect_uri = 'https://example.com/oauth'
authorize_code = 'SbNgn_QOMWhZW9CyMUIz4xeSibTEU_rZS_xF_-io2josT0oMs4eLPgAAAAQKPXKYAAABkzB0uze2W8wW6V7rJg'

data = {
    'grant_type':'authorization_code',
    'client_id':rest_api_key,
    'redirect_uri':redirect_uri,
    'code': authorize_code,
    }

response = requests.post(url, data=data)
tokens = response.json()
print(tokens)

import json
with open(r"C:\Users\yunji\codes\kakao_code.json","w") as fp:
    json.dump(tokens, fp)
