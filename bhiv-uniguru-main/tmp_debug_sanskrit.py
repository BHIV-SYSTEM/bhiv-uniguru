from fastapi.testclient import TestClient
from service.uniguru_runtime_api import app

client = TestClient(app)
response = client.post('/runtime/sanskrit/decode', json={'query': 'धर्म', 'emit_proof': False})
print(response.status_code)
print(response.text)
