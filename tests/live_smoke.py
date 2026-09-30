"""Optional real-model check. Run from the project root after setup."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main
from fastapi.testclient import TestClient

if __name__ == '__main__':
    with tempfile.TemporaryDirectory(dir=main.ROOT / 'data') as temporary:
        main.DATA = Path(temporary)
        client = TestClient(main.app)
        status = client.get('/api/status').json()
        assert status['ready'], status
        sample = (main.ROOT / 'examples' / 'sample-policy.txt').read_bytes()
        response = client.post('/api/documents', files={'file': ('sample-policy.txt', sample)})
        assert response.status_code == 201, response.text
        doc_id = response.json()['id']
        questions = [
            ('How many annual leave days do full-time employees receive?', '18', True),
            ('How many unused annual leave days can I carry forward, and when must they be used?', '5', True),
            ('What about sick leave? How many days?', '10', True),
            ('What salary increment am I entitled to?', "couldn't find", False),
        ]
        for question, expected, cited in questions:
            response = client.post('/api/chat', json={'document_id':doc_id,'question':question})
            assert response.status_code == 200, response.text
            answer = response.json()
            print(json.dumps({'question':question, **answer}, ensure_ascii=False), flush=True)
            assert expected in answer['answer'], answer
            assert bool(answer['sources']) == cited, answer
        assert len(client.get(f'/api/documents/{doc_id}/messages').json()) == 8
        other = client.post('/api/documents', files={'file': ('other-policy.txt', b'Employees receive 27 days of annual leave. All requests need director approval.')}).json()['id']
        response = client.post('/api/chat', json={'document_id':other,'question':'How many annual leave days do employees receive?'})
        assert response.status_code == 200, response.text
        result = response.json()
        print(json.dumps({'question':'Other policy annual leave', **result}), flush=True)
        assert '27' in result['answer'] and all(s['name'] == 'other-policy.txt' for s in result['sources']), result
        assert client.delete(f'/api/documents/{doc_id}').status_code == 200
        assert client.delete(f'/api/documents/{other}').status_code == 200
        assert client.get('/api/documents').json() == []
        print('Real-model smoke checks passed.', flush=True)
