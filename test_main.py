from fastapi.testclient import TestClient
from .main import app

client = TestClient(app)

def test_add_user():
    res = client.get('/adduser?client_id=test_user')
    assert res.status_code == 200
    assert res.json() == {'success': True}

def test_heartbeat():
    res = client.get('/heartbeat?client_id=test_user')
    assert res.status_code == 200
    assert res.json() == {'success': True, 'status': 0}

def test_delete_user():
    res = client.get('/deleteuser?client_id=test_user')
    assert res.status_code == 200
    assert res.json() == {'success': True}

