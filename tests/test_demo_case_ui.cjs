// Exercise the shipped dashboard script with a small DOM, without a model call.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

async function main() {
  const html = fs.readFileSync(path.join(__dirname, '../app/api/reviewer_ui.py'), 'utf8');
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1]
    .replace(/loadDemoCases\(\);\s*loadCases\(\);\s*$/, '');
  const catalogue = fs.readdirSync(path.join(__dirname, '../app/data/demo_cases')).filter(n => n.endsWith('.json')).sort().map(name => ({
    id: name.slice(0, -5), name, description: 'Synthetic example',
    case: JSON.parse(fs.readFileSync(path.join(__dirname, '../app/data/demo_cases', name), 'utf8')),
  }));
  const elements = Object.fromEntries(['demoCaseSelect','demoCaseStatus','caseInput','caseFile','fileStatus','createDraftButton'].map(id => [id, {
    value:'',textContent:'',disabled:false,options:[],
    replaceChildren(...items) { this.options = items; }, add(item) { this.options.push(item); },
  }]));
  let posts = 0;
  const alerts = [];
  const context = vm.createContext({
    document: {getElementById: id => elements[id]},
    Option: function(text,value) { this.text = text; this.value = value; },
    alert: text => alerts.push(text),
    fetch: async (url,opt) => {
      if (opt?.method === 'POST') posts++;
      return {ok:true,json:async () => catalogue};
    },
  });
  vm.runInContext(script, context);
  const publicHtml=vm.runInContext(`publicDrugEvidence([{
    medication_name:'Synthetic drug',
    rxnorm:{status:'matched',rxcui:'123',retrieved_at:'2026-10-17T00:00:00Z',cache_status:'miss'},
    dailymed:{status:'matched',labels:[{title:'Synthetic label',label_url:'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=test',spl_version:'2'}]},
    openfda:{status:'matched',label_id:'test-id',evidence_excerpts:{warnings:'<script>unsafe markup</script>'}}
  }])`,context);
  assert.ok(publicHtml.includes('RxCUI: 123'));
  assert.ok(publicHtml.includes('Synthetic label'));
  assert.ok(publicHtml.includes('View label excerpts'));
  assert.ok(publicHtml.includes('&lt;script&gt;unsafe markup&lt;/script&gt;'));
  assert.ok(!publicHtml.includes('<script>unsafe markup'));
  assert.ok(vm.runInContext("publicDrugEvidence([{medication_name:'Unknown',rxnorm:{status:'ambiguous'}}])",context).includes('not queried: terminology match required'));
  await vm.runInContext('loadDemoCases()', context);
  assert.equal(elements.demoCaseSelect.options.length, 8);
  assert.equal(posts, 0, 'loading examples must not run the workflow');
  elements.caseFile.value = 'previous.json';
  vm.runInContext("uploadedFileText='previous file';uploadedFileName='previous.json'", context);
  for (const item of catalogue) {
    elements.demoCaseSelect.value = item.id;
    vm.runInContext('selectDemoCase()', context);
    assert.deepEqual(JSON.parse(elements.caseInput.value), item.case);
    assert.equal(elements.caseFile.value, '');
    assert.equal(vm.runInContext('uploadedFileText', context), null);
  }
  assert.equal(posts, 0, 'choosing an example must wait for Create draft');
  let calls = 0, finish;
  context.submitFixture = async input => { calls++;assert.deepEqual(JSON.parse(JSON.stringify(input)), catalogue[6].case);await new Promise(resolve => {finish=resolve;}); };
  vm.runInContext('createCase=submitFixture', context);
  const pending = vm.runInContext('submitCase()', context);
  await vm.runInContext('submitCase()', context);
  assert.equal(calls, 1, 'double clicks must not create duplicate cases');
  assert.equal(elements.createDraftButton.disabled, true);
  finish();await pending;
  assert.equal(elements.createDraftButton.disabled, false);
  assert.equal(elements.caseInput.value, '');
  assert.equal(elements.demoCaseSelect.value, '');
  elements.caseInput.value = '{invalid JSON';
  await vm.runInContext('submitCase()', context);
  assert.equal(calls, 1);
  assert.ok(alerts.some(text => text.includes('Unable to create case')));
  console.log('PASS: seven selectable inputs, no auto-submit, file reset, clear, duplicate-submit guard and invalid JSON handling');
}
main().catch(error => {console.error(error);process.exitCode=1;});
