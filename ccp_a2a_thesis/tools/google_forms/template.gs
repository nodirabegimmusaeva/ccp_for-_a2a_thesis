// Paste the generated script into script.google.com. Run createReviewForms.
// No API key is required. Forms remain closed until you preview and publish them.
const CASES = /* REVIEW_DATA */;
const VERSION = 'development-human-review-v1';
const RATINGS = ['Yes — meets the requirement', 'No — missing or incorrect', 'Unclear — cannot determine'];

function readableOrder(o) {
  return ['Reported issues:\n' + o.issues.map(x=>'• '+x).join('\n'),
    'Locations:\n'+(o.locations.length ? o.locations.join('\n') : 'None provided'),
    'Proposed actions:\n'+o.actions.map((x,i)=>(i+1)+'. '+x).join('\n'),
    'Clarification requested: '+(o.clarification_required?'Yes':'No'),
    'Clarification details: '+(o.clarification_notes || 'None'),
    'Assigned department: '+(o.department || 'Not assigned'), 'Summary: '+o.summary].join('\n\n');
}
function createReviewForms() {
  const lock=LockService.getScriptLock(); lock.waitLock(30000);
  try {
    const props=PropertiesService.getScriptProperties();
    let state=JSON.parse(props.getProperty(VERSION)||'{"forms":[]}');
    if (state.forms.some(x=>!x.ready)) throw new Error('An earlier build stopped partway. Inspect its form; do not silently duplicate it.');
    if (state.forms.length===Math.ceil(CASES.length/8)) { logLinks(state); return; }
    for(let b=state.forms.length;b<Math.ceil(CASES.length/8);b++) {
      const form=FormApp.create('Municipal work-order review — Part '+(b+1));
      const entry={id:form.getId(),ready:false,items:[]};state.forms.push(entry);
      props.setProperty(VERSION,JSON.stringify(state));
      form.setAcceptingResponses(false).setCollectEmail(false).setPublishingSummary(false)
        .setProgressBar(true).setShuffleQuestions(false).setAllowResponseEdits(false)
        .setConfirmationMessage('Thank you. Please continue with the next part using the same reviewer code.')
        .setDescription('Review eight fictional complaint/work-order pairs. No municipal expertise is required. '+
          'Read the original report, then judge the proposed work order. Yes = requirement satisfied; '+
          'No = missing or contradicted; Unclear = genuinely ambiguous. Judge meaning, not exact words. '+
          'No verified department directory was supplied: do not assume a named department is correct. '+
          'Conditional actions after clarification are acceptable. These are development cases, not real resident records. '+
          'Work independently and do not compare answers with other reviewers until submission. '+
          'This form evaluates the final work order, not intermediate handoff retention.');
      entry.reviewerId=form.addTextItem().setTitle('Reviewer code').setHelpText('Use your assigned code, e.g. R1. Use the same code in all four parts. Do not enter your name or email.').setRequired(true).getId();
      for(const item of CASES.slice(b*8,b*8+8)) {
        form.addPageBreakItem().setTitle('Case '+item.item_id);
        form.addSectionHeaderItem().setTitle('1. Read the original complaint').setHelpText(
          item.original.hintContent+'\n\nRecorded category/address: '+item.original.balloonContent);
        form.addSectionHeaderItem().setTitle('2. Read the proposed work order').setHelpText(readableOrder(item.work_order));
        const criteria=item.reference.constraints;
        const grid=form.addGridItem().setTitle('3. Does the work order meet each requirement?')
          .setRows(criteria.map((c,i)=>(i+1)+'. '+(c.compliance_pass||c.requirement)))
          .setColumns(RATINGS).setRequired(true);
        const completion=form.addMultipleChoiceItem().setTitle('4. Is this a complete, usable draft work order?')
          .setHelpText('Yes only if all requirements above are met and these deliverables are present:\n'+item.reference.deliverables.join('\n')+
          '\nClarification is allowed; actual execution is not required.').setChoiceValues(RATINGS).setRequired(true);
        const notes=form.addParagraphTextItem().setTitle('5. Briefly explain your ratings')
          .setHelpText('Use requirement numbers. Quote supporting wording or identify what is missing. Explain every No or Unclear. If all Yes, give one short supporting example.').setRequired(true);
        entry.items.push({blindId:item.item_id,criteria:criteria.map(c=>c.id),gridId:grid.getId(),completionId:completion.getId(),notesId:notes.getId()});
      }
      entry.ready=true;props.setProperty(VERSION,JSON.stringify(state));
    }
    logLinks(state);
  } finally {lock.releaseLock();}
}
function logLinks(state) {
  state.forms.forEach((f,i)=>{const form=FormApp.openById(f.id);console.log('Part '+(i+1)+' EDIT: '+form.getEditUrl());console.log('RESPOND: '+form.getPublishedUrl());});
}
function csvCell(value) {return '"'+String(value??'').replace(/"/g,'""')+'"';}
function rating(value) {
  const index=RATINGS.indexOf(value);
  if(index<0) throw new Error('Missing or unknown rating: '+value);
  return ['pass','fail','uncertain'][index];
}
function exportRatings() {
  const state=JSON.parse(PropertiesService.getScriptProperties().getProperty(VERSION)||'null');
  if(!state || state.forms.some(f=>!f.ready)) throw new Error('Build forms first.');
  const reviewers={}; const seen=new Set();
  for(const entry of state.forms) {
    for(const response of FormApp.openById(entry.id).getResponses()) {
      const answers={};response.getItemResponses().forEach(r=>answers[r.getItem().getId()]=r.getResponse());
      const reviewer=String(answers[entry.reviewerId]||'').trim();
      if(!/^[A-Za-z0-9_-]{1,40}$/.test(reviewer)) throw new Error('Reviewer code must use letters/numbers/underscore/hyphen.');
      reviewers[reviewer] ||= [];
      for(const item of entry.items) {
        const key=reviewer+'|'+item.blindId;
        if(seen.has(key)) throw new Error('Duplicate submission for '+key+'. Resolve duplicates before exporting.');
        seen.add(key);
        const values=answers[item.gridId];
        if(!Array.isArray(values)||values.length!==item.criteria.length) throw new Error('Incomplete grid for '+key);
        item.criteria.forEach((c,i)=>reviewers[reviewer].push([item.blindId,c,rating(values[i]),answers[item.notesId]]));
        reviewers[reviewer].push([item.blindId,'completion',rating(answers[item.completionId]),answers[item.notesId]]);
      }
    }
  }
  const folder=DriveApp.createFolder('Complaint review ratings '+new Date().toISOString());
  for(const [reviewer,rows] of Object.entries(reviewers)) {
    const count=new Set(rows.map(r=>r[0])).size;
    console.log(reviewer+': '+count+'/'+CASES.length+' cases. Compare raters only after both complete all cases.');
    const csv=[['item_id','criterion','rating','evidence'],...rows].map(r=>r.map(csvCell).join(',')).join('\r\n');
    folder.createFile(reviewer+'.csv',csv,MimeType.CSV);
  }
  console.log('CSV exports: '+folder.getUrl());
}
