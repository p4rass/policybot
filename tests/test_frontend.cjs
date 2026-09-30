// Exercise the actual frontend with a small DOM/API harness, without browser automation.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

class Element {
  constructor() { this.children=[]; this.className=''; this.value=''; this.hidden=false; this.style={}; this.disabled=false; this.textContent=''; this.classList={toggle(){},add(){},remove(){}}; }
  append(...items){ this.children.push(...items); }
  replaceChildren(...items){ this.children=items; }
  setAttribute(name,value){ this[name]=value; }
  addEventListener(){}
  remove(){this.removed=true;}
  focus(){}
}
const ids=new Map();
const element=id=>{if(!ids.has(id))ids.set(id,new Element());return ids.get(id);};
const apiCalls=[];
const context={
  document:{getElementById:element,createElement:()=>new Element(),querySelectorAll:()=>[]},
  fetch:async(url,options)=>{apiCalls.push({url,options}); const data=url.endsWith('/status')?{ready:true,message:'Local models ready'}:[];return{ok:true,json:async()=>data};},
  confirm:()=>true,setInterval:()=>{},FormData:class{append(){}},console,
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../static/app.js'),'utf8'),context);
setImmediate(async()=>{
  assert.equal(element('model-status').textContent,'Local models ready');
  assert.equal(element('question').disabled,true,'chat should be disabled without a policy');
  vm.runInContext("docs=[{id:'a',name:'<img src=x onerror=alert(1)>',chunks:2}]; active='a'; renderDocs();",context);
  assert.equal(element('documents').children[0].children[0].children[0].textContent,'<img src=x onerror=alert(1)>');
  vm.runInContext("addMessage('assistant','<script>bad()</script>',[{number:1,name:'policy.txt',location:'Page 2',text:'<img src=x>'}]);",context);
  const row=element('messages').children[0];
  assert.equal(row.children[1].children[1].textContent,'<script>bad()</script>');
  assert.equal(row.children[1].children[2].children[1].children[1].textContent,'<img src=x>');
  assert.equal(element('question').disabled,false);
  element('question').value='Leave?';
  vm.runInContext('controls()',context);
  assert.equal(element('send').disabled,false);
  console.log('Frontend checks passed: initial state, selection, safe text rendering, source cards, send controls.');
});
