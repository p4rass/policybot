import io
import json

import pytest
from docx import Document
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'DATA', tmp_path)
    monkeypatch.setattr(main, 'embed', lambda texts, query=False: [[1.0, 0.0] for _ in texts])
    return TestClient(main.app)


def upload(client, name='leave.txt', text='Employees receive 18 days of annual leave. Manager approval is required.'):
    response = client.post('/api/documents', files={'file': (name, text.encode())})
    assert response.status_code == 201, response.text
    return response.json()['id']


def test_docx_paragraphs_and_tables_in_order():
    doc = Document()
    doc.add_paragraph('Before table')
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = 'Annual leave'
    table.cell(0, 1).text = '18 days'
    doc.add_paragraph('After table')
    buffer = io.BytesIO()
    doc.save(buffer)
    text = main.parse_document('policy.docx', buffer.getvalue())[0][1]
    assert text.index('Before') < text.index('18 days') < text.index('After')


def test_chunks_preserve_all_text_and_page_location():
    text = ''.join(chr(0x400 + i % 150) for i in range(4000))
    chunks = main.chunk_sections([('Page 2', text)])
    restored = chunks[0]['text'] + ''.join(c['text'][180:] for c in chunks[1:])
    assert restored == text
    assert all(c['location'] == 'Page 2' and len(c['text']) <= 1100 for c in chunks)


def test_retrieval_uses_lexical_signal_when_vectors_tie():
    rows = [{'text': 'The office opens Monday.', 'vector': '[1,0]'}, {'text': 'Sick leave requires a medical certificate.', 'vector': '[1,0]'}]
    found = main.retrieve(rows, [1,0], 'medical certificate', limit=1)
    assert 'medical certificate' in found[0]['text']


def test_empty_scan_and_encrypted_pdf(client):
    pdf = PdfWriter()
    pdf.add_blank_page(width=300, height=300)
    buffer = io.BytesIO()
    pdf.write(buffer)
    response = client.post('/api/documents', files={'file': ('scan.pdf', buffer.getvalue())})
    assert response.status_code == 422 and 'OCR' in response.json()['detail']
    pdf.encrypt('secret')
    buffer = io.BytesIO()
    pdf.write(buffer)
    response = client.post('/api/documents', files={'file': ('locked.pdf', buffer.getvalue())})
    assert response.status_code == 422 and 'unlocked' in response.json()['detail']


def test_pdf_text_and_page_numbers():
    pdf = PdfWriter()
    for text in ('Annual leave is 18 days.', 'Sick leave is 10 days.'):
        page = pdf.add_blank_page(width=600, height=800)
        font = DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):pdf._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(f'BT /F1 12 Tf 50 750 Td ({text}) Tj ET'.encode())
        page[NameObject('/Contents')] = pdf._add_object(stream)
    buffer = io.BytesIO()
    pdf.write(buffer)
    sections = main.parse_document('policy.pdf', buffer.getvalue())
    assert sections[0][0] == 'Page 1' and '18 days' in sections[0][1]
    assert sections[1][0] == 'Page 2' and '10 days' in sections[1][1]


def test_invalid_files_and_whitespace(client):
    for name, content, code in [('bad.exe', b'abc', 415), ('empty.txt', b'   ', 422), ('bad.pdf', b'broken', 422), ('bad.txt', b'\xff', 422)]:
        assert client.post('/api/documents', files={'file': (name, content)}).status_code == code
    assert client.get('/api/documents').json() == []


def test_failed_embeddings_do_not_save_partial_policy(client, monkeypatch):
    def fail(*args, **kwargs):
        raise HTTPException(503, 'Unavailable')
    monkeypatch.setattr(main, 'embed', fail)
    assert client.post('/api/documents', files={'file': ('test.txt', b'Policy text')}).status_code == 503
    assert client.get('/api/documents').json() == []


def test_selected_policy_only_and_citation_validation(client, monkeypatch):
    first = upload(client)
    upload(client, 'other.txt', 'Secret second policy: bonus is 500 dollars.')
    def model(path, payload=None, **kwargs):
        prompt = payload['messages'][0]['content']
        assert '18 days' in prompt
        assert '500 dollars' not in prompt
        return {'message': {'content': json.dumps({'answer': '18 days [1]. Unknown [99].', 'source_ids': [1,99]})}}
    monkeypatch.setattr(main, 'ollama', model)
    response = client.post('/api/chat', json={'document_id':first,'question':'How much annual leave?'})
    assert response.status_code == 200
    result = response.json()
    assert '[99]' not in result['answer']
    assert len(result['sources']) == 1 and result['sources'][0]['name'] == 'leave.txt'
    history = client.get(f'/api/documents/{first}/messages').json()
    assert [m['role'] for m in history] == ['user','assistant']
    assert history[1]['sources'] == result['sources']


def test_no_sources_becomes_refusal(client, monkeypatch):
    doc_id = upload(client)
    monkeypatch.setattr(main, 'ollama', lambda *args, **kwargs: {'message':{'content':'{"answer":"Your salary is 90000", "source_ids":[]}'}})
    result = client.post('/api/chat', json={'document_id':doc_id,'question':'What is my salary?'}).json()
    assert "couldn't find" in result['answer'] and not result['sources']


def test_model_failure_does_not_persist_chat(client, monkeypatch):
    doc_id = upload(client)
    monkeypatch.setattr(main, 'ollama', lambda *args, **kwargs: {'message': {'content':'invalid json'}})
    assert client.post('/api/chat', json={'document_id':doc_id,'question':'Leave?'}).status_code == 502
    assert client.get(f'/api/documents/{doc_id}/messages').json() == []


def test_clear_and_delete_cascade(client, monkeypatch):
    doc_id = upload(client)
    monkeypatch.setattr(main, 'ollama', lambda *a, **kw: {'message':{'content':'{"answer":"18 days [1]", "source_ids":[1]}'}})
    assert client.post('/api/chat', json={'document_id':doc_id,'question':'Leave?'}).status_code == 200
    assert client.delete(f'/api/documents/{doc_id}/messages').status_code == 200
    assert client.get(f'/api/documents/{doc_id}/messages').json() == []
    assert len(client.get('/api/documents').json()) == 1
    assert client.delete(f'/api/documents/{doc_id}').status_code == 200
    with main.db() as conn:
        assert conn.execute('SELECT COUNT(*) FROM chunks').fetchone()[0] == 0
    assert client.get(f'/api/documents/{doc_id}/messages').status_code == 404


def test_model_change_and_blank_question(client, monkeypatch):
    doc_id = upload(client)
    assert client.post('/api/chat', json={'document_id':doc_id,'question':'   '}).status_code == 422
    monkeypatch.setattr(main, 'EMBED_MODEL', 'other-model')
    assert client.post('/api/chat', json={'document_id':doc_id,'question':'Leave?'}).status_code == 409


def test_frontend_and_persistence(client):
    doc_id = upload(client)
    other_client = TestClient(main.app)
    assert other_client.get('/api/documents').json()[0]['id'] == doc_id
    assert 'Policybot' in client.get('/').text
    assert client.get('/static/app.js').status_code == 200
