
'use strict';
const $ = id => document.getElementById(id);
const labels={idle:'Ready',pending:'Pending',running:'Researching',waiting_for_feedback:'Waiting for feedback',completed:'Completed',failed:'Failed',cancelled:'Cancelled'};
let taskId=null, timer=null, report='', active=false;
const terminal=new Set(['completed','failed','cancelled']);
function busy(value){active=value;$('start').disabled=value;$('topic').disabled=value;$('cancel').disabled=!value||!taskId;}
function remember(){try{sessionStorage.setItem('deep-researcher.task',taskId);}catch{}}
async function api(path,options={}){
  const response=await fetch(path,{...options,signal:AbortSignal.timeout(15000)});
  let data;try{data=await response.json();}catch{throw new Error('The server did not return JSON. Check that your backend is running.');}
  if(!response.ok){const error=new Error(typeof data.detail==='string'?data.detail:`Request failed (${response.status})`);error.status=response.status;throw error;}
  return data;
}
function display(data){
  $('feedbackForm').hidden=data.status!=='waiting_for_feedback';
  $('feedbackSections').textContent=(data.sections||[]).join('\n');
  const state=data.status || (typeof data.report==='string'&&data.report?'completed':'running');
  $('status').textContent=labels[state]||state;$('status').dataset.state=state;
  $('step').textContent=state==='waiting_for_feedback'?'Review the plan below to continue.':(data.step||labels[state]||state);
  $('taskId').textContent=taskId?`Task ${taskId}`:'';
  $('error').textContent=data.error||'';
  if(typeof data.report==='string'&&data.report){report=data.report;renderMarkdown(report, $('report'));$('report').hidden=false;$('empty').hidden=true;$('copy').disabled=false;$('download').disabled=false;}
  busy(!terminal.has(state));return state;
}
async function poll(id){
  if(id!==taskId)return;
  let again=true;
  try{const data=await api(`/research/${encodeURIComponent(id)}`);if(id!==taskId)return;again=!terminal.has(display(data));}
  catch(error){if(id!==taskId)return;if(error.status===404){again=false;busy(false);$('status').textContent='Task not found';$('status').dataset.state='failed';try{sessionStorage.removeItem('deep-researcher.task');}catch{}}$('error').textContent=`Could not retrieve status: ${error.message} If the server restarted, refresh the page and start a new research task.`;$('step').textContent='Connection lost. Retrying…';}
  clearTimeout(timer);if(again&&id===taskId)timer=setTimeout(()=>poll(id),2500);
}
$('form').addEventListener('submit',async event=>{
  event.preventDefault();const topic=$('topic').value.trim();if(!topic||active)return;
  clearTimeout(timer);taskId=null;busy(true);report='';$('report').hidden=true;$('empty').hidden=false;$('copy').disabled=true;$('download').disabled=true;$('error').textContent='';$('taskId').textContent='';$('status').textContent='Submitting';$('step').textContent='Creating your research task…';
  try{const data=await api('/research',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({topic})});if(!data.task_id)throw new Error('The server did not return a task ID.');taskId=data.task_id;remember();display({status:'running',step:'Research task started'});poll(taskId);}
  catch(error){busy(false);$('status').textContent='Submission failed';$('status').dataset.state='failed';$('error').textContent=error.message;$('step').textContent='Check your backend connection. If the request timed out, the task may still have started. Check the server logs before submitting again.';}
});
$('cancel').addEventListener('click',async()=>{
  if(!taskId)return;const id=taskId;$('cancel').disabled=true;
  try{await api(`/research/${encodeURIComponent(id)}`,{method:'DELETE'});clearTimeout(timer);await poll(id);}
  catch(error){$('error').textContent=`Could not cancel: ${error.message}`;}
  finally{if(active)$('cancel').disabled=false;}
});
$('copy').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(report);$('copy').textContent='Copied';setTimeout(()=>$('copy').textContent='Copy report',1500);}catch{$('error').textContent='Clipboard access is unavailable. Select the report to copy it manually, or download it.';}});
$('download').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([report],{type:'text/markdown;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=`research-${taskId||'report'}.md`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
async function restore(){
  if(location.protocol==='file:'){$('error').textContent='Open this page at http://127.0.0.1:8000 rather than opening the HTML file directly.';$('start').disabled=true;return;}
  let id;try{id=sessionStorage.getItem('deep-researcher.task');}catch{}if(!id)return;
  try{const data=await api(`/research/${encodeURIComponent(id)}`);taskId=id;if(data.topic)$('topic').value=data.topic;const state=display(data);if(!terminal.has(state))poll(id);}
  catch{$('error').textContent='Your previous task could not be restored. The server may have restarted. You can start a new research task.';}
}
restore();

$('feedbackForm').addEventListener('submit', async event => {
  event.preventDefault();
  const feedback=$('feedbackText').value.trim();
  if(!taskId || !feedback) return;
  $('sendFeedback').disabled=true;
  try {
    await api(`/research/${encodeURIComponent(taskId)}/feedback`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({feedback})});
    $('feedbackText').value=''; $('feedbackForm').hidden=true;
    clearTimeout(timer); await poll(taskId);
  } catch(error) {$('error').textContent=error.message;}
  finally {$('sendFeedback').disabled=false;}
});
