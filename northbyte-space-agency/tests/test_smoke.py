from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_pages():
    for route in ('/', '/about', '/missions', '/satellite-tracker',
                  '/earth-observation', '/observatory', '/research', '/journal',
                  '/contact', '/admin', '/health'):
        r = client.get(route)
        assert r.status_code == 200, (route, r.status_code, r.text[:300])


def test_legal_disclosures_and_brand():
    home = client.get('/').text
    assert 'NorthByte Norway Tec Ltd.' in home
    assert 'House of Yegin' in home
    assert 'NorthByte Space Agency' in home


def test_journal_seed():
    page = client.get('/journal').text
    assert 'Introducing NorthByte Space Agency' in page
    assert client.get('/journal/a-new-chapter-for-northbyte').status_code == 200
    assert client.get('/journal/does-not-exist').status_code == 404


def test_csrf_contact():
    # Direct POST without matching session CSRF must fail.
    r = client.post('/contact', data={'name':'X', 'email':'x@example.com', 'subject':'test', 'message':'hello there'})
    assert r.status_code == 403


def test_satellite_invalid_group():
    r = client.get('/api/satellites?group=INVALID')
    assert r.status_code == 400


def test_health():
    r = client.get('/health')
    assert r.json()['status'] == 'ok'
