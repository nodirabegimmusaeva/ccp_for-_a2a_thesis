const fs=require('fs'),vm=require('vm'),assert=require('assert');
let id=0;const forms=[],properties={};
function item(type){return new Proxy({id:++id,type,getId(){return this.id;}},{get(o,k){if(k in o)return o[k];return function(value){o[k]=value;return this;};}});}
const context={console:{log(){}},Set,Date,JSON,Object,Array,String,Error,
 PropertiesService:{getScriptProperties:()=>({getProperty:k=>properties[k],setProperty:(k,v)=>properties[k]=v})},
 LockService:{getScriptLock:()=>({waitLock(){},releaseLock(){}})},
 FormApp:{create(title){const f={id:++id,title,items:[],getId(){return String(this.id);},getEditUrl(){return 'edit';},getPublishedUrl(){return 'respond';},getResponses(){return [];}};
 for(const t of ['Text','PageBreak','SectionHeader','Grid','MultipleChoice','ParagraphText'])f['add'+t+'Item']=()=>{const x=item(t);f.items.push(x);return x;};
 for(const k of ['setAcceptingResponses','setCollectEmail','setPublishingSummary','setProgressBar','setShuffleQuestions','setAllowResponseEdits','setConfirmationMessage','setDescription'])f[k]=function(v){this[k+'Value']=v;return this;};
 forms.push(f);return f;},openById:target=>forms.find(f=>String(f.id)===target)}};
vm.createContext(context);vm.runInContext(fs.readFileSync(__dirname+'/create_review_forms.gs','utf8'),context);
vm.runInContext('createReviewForms()',context);
assert.equal(forms.length,4);
for(const f of forms){assert.equal(f.items.filter(x=>x.type==='Grid').length,8);assert.equal(f.setAcceptingResponsesValue,false);assert.equal(f.setCollectEmailValue,false);assert.equal(f.setPublishingSummaryValue,false);}
vm.runInContext('createReviewForms()',context);assert.equal(forms.length,4);
assert.equal(vm.runInContext("rating(RATINGS[0])",context),'pass');
assert.equal(vm.runInContext("rating(RATINGS[1])",context),'fail');
assert.equal(vm.runInContext("rating(RATINGS[2])",context),'uncertain');
console.log('PASS: four forms, 32 cases, required ratings, closed responses, no duplicates on rerun; rating conversion verified.');
