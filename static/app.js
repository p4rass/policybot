const $ = id => document.getElementById(id);
let docs = [], active = null, busy = false, ready = false;
async function api(path, options = {}) {
  const response = await fetch('/api' + path, options);
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Please check your request and try again.');
  return result;
}
function notice(message = '') { $('notice').textContent = message; $('notice').hidden = !message; }
function controls() {
  $('question').disabled = !active || busy || !ready;
  $('send').disabled = !active || busy || !ready || !$('question').value.trim();
  $('clear').disabled = !active || busy;
  $('file').disabled = busy;
  $('dropzone').classList.toggle('busy', busy);
  $('question').placeholder = !active ? 'Upload a policy to start asking questions…' : !ready ? 'Start the local models to ask a question…' : 'Ask a question about this policy…';
  document.querySelectorAll('.document button, .suggestions button').forEach(b => b.disabled = busy);
}
async function status() {
  try { const s = await api('/status'); ready = s.ready; $('model-status').textContent = s.message; $('model-status').classList.toggle('ready', ready); }
  catch { ready = false; $('model-status').textContent = 'Unable to reach Policybot'; }
  controls();
}
function renderDocs() {
  $('documents').replaceChildren(); $('count').textContent = docs.length;
  if (!docs.length) { const p = document.createElement('span'); p.className = 'empty-library'; p.textContent = 'Your first policy goes here.'; $('documents').append(p); }
  for (const doc of docs) {
    const row = document.createElement('div'); row.className = 'document' + (active === doc.id ? ' selected' : '');
    const select = document.createElement('button'); select.className = 'document-select'; select.title = doc.name;
    const name = document.createElement('strong'); name.textContent = doc.name;
    const meta = document.createElement('small'); meta.textContent = `${doc.chunks} indexed passages`;
    select.append(name, meta); select.onclick = () => choose(doc.id).catch(e => notice(e.message));
    const remove = document.createElement('button'); remove.className = 'delete'; remove.textContent = '×'; remove.setAttribute('aria-label', 'Delete ' + doc.name);
    remove.onclick = async () => {
      if (busy || !confirm(`Delete "${doc.name}" and its chat history?`)) return;
      busy = true; controls();
      try { await api('/documents/' + doc.id, {method:'DELETE'}); if (active === doc.id) active = null; await refresh(); await choose(active || docs[0]?.id || null); notice(); }
      catch(e) { notice(e.message); } finally { busy = false; controls(); }
    };
    row.append(select, remove); $('documents').append(row);
  }
  controls();
}
async function refresh() { docs = await api('/documents'); renderDocs(); }
function addMessage(role, content, sources = []) {
  const row = document.createElement('div'); row.className = 'message ' + role;
  const avatar = document.createElement('div'); avatar.className = 'avatar'; avatar.textContent = role === 'user' ? 'Y' : '✦';
  const body = document.createElement('div'); body.className = 'message-body';
  const speaker = document.createElement('div'); speaker.className = 'speaker'; speaker.textContent = role === 'user' ? 'YOU' : 'POLICYBOT';
  const text = document.createElement('div'); text.className = 'content'; text.textContent = content;
  body.append(speaker, text);
  if (sources.length) {
    const box = document.createElement('div'); box.className = 'sources';
    const label = document.createElement('small'); label.textContent = 'FROM YOUR POLICY'; box.append(label);
    for (const source of sources) {
      const details = document.createElement('details'), summary = document.createElement('summary'), p = document.createElement('p');
      summary.textContent = `[${source.number}] ${source.name} · ${source.location}`; p.textContent = source.text; details.append(summary, p); box.append(details);
    }
    body.append(box);
  }
  row.append(avatar, body); $('messages').append(row);
  $('conversation').scrollTop = $('conversation').scrollHeight;
  return row;
}
async function choose(id) {
  active = id; notice(); $('messages').replaceChildren(); renderDocs();
  $('active-name').textContent = docs.find(d => d.id === id)?.name || 'Choose a policy to get started';
  $('welcome').hidden = !!id; $('suggestions').hidden = !id;
  $('question').value = ''; controls();
  if (id) {
    const history = await api('/documents/' + id + '/messages');
    if (id !== active) return;
    for (const message of history) addMessage(message.role, message.content, message.sources);
    if (!history.length) addMessage('assistant', 'Your policy is ready. Ask me about its rules, requirements, or exceptions — I’ll show you the passages behind my answer.');
    $('suggestions').hidden = history.length > 0;
  }
}
async function upload(file) {
  if (!file || busy) return;
  busy = true; controls(); notice(); $('upload-status').textContent = 'Reading and indexing locally… Larger policies may take a few minutes.';
  const data = new FormData(); data.append('file', file);
  try { const doc = await api('/documents', {method:'POST',body:data}); await refresh(); await choose(doc.id); $('upload-status').textContent = 'Policy ready. Start a conversation.'; }
  catch(e) { $('upload-status').textContent = ''; notice(e.message); }
  finally { busy = false; $('file').value = ''; await status(); controls(); }
}
$('file').onchange = e => upload(e.target.files[0]);
$('dropzone').onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); if (!busy) $('file').click(); } };
for (const type of ['dragenter','dragover']) $('dropzone').addEventListener(type, e => { e.preventDefault(); $('dropzone').classList.add('drag'); });
for (const type of ['dragleave','drop']) $('dropzone').addEventListener(type, e => { e.preventDefault(); $('dropzone').classList.remove('drag'); });
$('dropzone').addEventListener('drop', e => upload(e.dataTransfer.files[0]));
$('question').oninput = () => { $('question').style.height = 'auto'; $('question').style.height = Math.min($('question').scrollHeight, 130) + 'px'; controls(); };
$('question').onkeydown = e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (!$('send').disabled) $('chat-form').requestSubmit(); } };
$('chat-form').onsubmit = async e => {
  e.preventDefault(); const question = $('question').value.trim(); if (!question || !active || busy || !ready) return;
  busy = true; controls(); notice(); $('suggestions').hidden = true;
  const user = addMessage('user', question); $('question').value = ''; $('question').style.height = 'auto';
  const pending = addMessage('assistant', 'Finding passages and thinking locally…'); pending.classList.add('thinking');
  try { const answer = await api('/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({document_id:active,question})}); pending.remove(); addMessage('assistant', answer.answer, answer.sources); }
  catch(e) { pending.remove(); user.remove(); $('question').value = question; notice(e.message); }
  finally { busy = false; controls(); $('question').focus(); }
};
document.querySelectorAll('.suggestions button').forEach(button => button.onclick = () => { $('question').value = button.textContent; controls(); if (!$('send').disabled) $('chat-form').requestSubmit(); });
$('clear').onclick = async () => {
  if (!active || busy || !confirm('Clear the conversation for this policy?')) return;
  busy = true; controls();
  try { await api('/documents/' + active + '/messages', {method:'DELETE'}); await choose(active); }
  catch(e) { notice(e.message); } finally { busy = false; controls(); }
};
async function init() { await status(); try { await refresh(); if (docs.length) await choose(docs[0].id); } catch(e) { notice(e.message); } }
init(); setInterval(status, 15000);
