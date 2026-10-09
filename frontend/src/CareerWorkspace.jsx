import React, {useState, useEffect, useRef} from 'react';
import {Sparkles, ArrowUpRight, ArrowRight, FileText, Check, Plus, BookOpen, Download, LoaderCircle, Copy, Target, Clock3, RefreshCw, Trash2, ChevronDown, ShieldCheck} from 'lucide-react';
import {api} from './api';

const exampleJD = `Full-stack Developer — Example Product Team
We are looking for a full-stack engineer to build and maintain a recruitment platform. You will build accessible React interfaces, develop Django REST APIs, design MySQL schemas and improve performance.
Essential: Python, Django REST Framework, React, JavaScript, SQL/MySQL, JWT authentication, Git, testing, debugging, and clear communication with product stakeholders. Demonstrate one end-to-end project and explain API security and database query optimization.
Preferred: Docker, AWS deployment, CI/CD pipelines, asynchronous background jobs, and experience with resume parsing or AI API integrations.
Responsibilities: translate requirements into maintainable features, test permissions, conduct code reviews, diagnose bottlenecks and collaborate with designers. Be prepared to discuss architecture, technical tradeoffs and what you personally contributed.`;

function exportReport(report) {
  const r=report.result;
  const sections=[
    report.title, 'JD COACHING & INTERVIEW PREPARATION', 'Generated with '+report.model,
    'Practice questions are predictions, not guaranteed actual interview questions.',
    'TARGET JOB DESCRIPTION\n'+report.job_description,
    'OVERVIEW\n'+r.overview+'\nEvidence coverage: '+r.coverage_score+'/100\n'+r.score_explanation,
    'STRENGTHS\n'+r.strengths.map(s=>'- '+s).join('\n'),
    'REQUIREMENTS\n'+r.requirements.map(s=>s.requirement+' ['+s.status+'; '+s.importance+']\nEvidence: '+s.resume_evidence+'\nRecommendation: '+s.recommendation).join('\n\n'),
    'RESUME EDITS\n'+r.resume_edits.map(s=>s.section+' — '+s.action+(s.needs_confirmation?' [CONFIRM BEFORE USING]':'')+'\nOriginal: '+(s.original||'New addition')+'\nSuggested: '+s.suggested+'\nReason: '+s.reason+'\nEvidence: '+s.evidence).join('\n\n'),
    'TAILORED SUMMARY\n'+r.tailored_summary,
    'KEYWORDS TO HIGHLIGHT\n'+r.keywords_to_highlight.join(', '),
    'SKILLS TO DEVELOP\n'+r.skills_to_develop.join(', '),
    'INTERVIEW QUESTIONS & SAMPLE ANSWERS\n'+r.interview_questions.map((q,i)=>(i+1)+'. ['+q.category+'] '+q.question+'\nWhy asked: '+q.why_asked+'\nSample answer: '+q.sample_answer+'\nAnswer points: '+q.answer_points.join('; ')+'\nResume/JD connection: '+q.resume_connection+'\nFollow-ups: '+q.follow_up_questions.join('; ')).join('\n\n'),
    'PREPARATION PLAN\n'+r.preparation_plan.map(d=>'Day '+d.day+': '+d.focus+'\n'+d.tasks.map(t=>'- '+t).join('\n')).join('\n\n'),
    'QUESTIONS TO ASK\n'+r.questions_to_ask.map(q=>'- '+q).join('\n'),
    'LIMITATIONS\n'+r.limitations.join('\n'),
  ];
  const blob=new Blob([sections.join('\n\n')],{type:'text/plain;charset=utf-8'});
  const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=report.title.replace(/[^a-z0-9 -]/gi,'').slice(0,80)+' — interview preparation.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function Coverage({value}) {return <div className="score-ring small"><div><strong>{value}</strong></div></div>;}
export default function CareerWorkspace({resumes, jobs, onUpload, isDemo = false}) {
  const [reports,setReports]=useState([]),[selected,setSelected]=useState(null),[config,setConfig]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[tab,setTab]=useState('Resume fit');
  const [resumeId,setResumeId]=useState(''),[title,setTitle]=useState(''),[jd,setJD]=useState(''),[consent,setConsent]=useState(false),[category,setCategory]=useState('All'),[revealed,setRevealed]=useState({}),[answers,setAnswers]=useState({}),[copied,setCopied]=useState('');
  const selectedRef=useRef(null),mounted=useRef(true);
  const active=reports.find(r=>r.id===selected);
  const generating=active&&['queued','running'].includes(active.status);
  useEffect(()=>{selectedRef.current=selected;},[selected]);
  useEffect(()=>{if(resumes.length&&!resumes.some(r=>String(r.id)===resumeId))setResumeId(String(resumes[0].id));if(!resumes.length)setResumeId('');},[resumes,resumeId]);
  async function load() {
    const items=await api('career-reports/');
    if(!mounted.current)return;
    setReports(items);if(selectedRef.current===null&&items.length)setSelected(items[0].id);
  }
  useEffect(()=>{
    mounted.current=true;
    Promise.all([load(),api('career-config/').then(c=>{if(mounted.current)setConfig(c);})]).catch(e=>{if(mounted.current)setError(e.message);});
    return()=>{mounted.current=false;};
  },[]);
  const pending=reports.some(r=>['queued','running'].includes(r.status));
  useEffect(()=>{
    if(!pending)return;
    const timer=setInterval(()=>load().catch(e=>{if(mounted.current)setError(e.message);}),3000);
    return()=>clearInterval(timer);
  },[pending]);
  useEffect(()=>{setRevealed({});setAnswers({});setCategory('All');},[selected]);
  async function generate(e) {
    e.preventDefault();setError('');setBusy(true);
    try {
      const report=await api('career-reports/',{method:'POST',body:{resume:Number(resumeId),title:title||'My target opportunity',job_description:jd,consent}});
      setReports(prev=>[report,...prev]);setSelected(report.id);setTab('Resume fit');
    } catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function copy(value,label) {try {await navigator.clipboard.writeText(value);setCopied(label);setTimeout(()=>setCopied(''),2000);}catch{setError('Clipboard unavailable. Select and copy the text directly.');}}
  async function remove() {
    if(!active||!window.confirm('Delete this private coaching report?'))return;
    setBusy(true);
    try {await api('career-reports/'+active.id+'/',{method:'DELETE'});setReports(prev=>prev.filter(r=>r.id!==active.id));setSelected(null);}catch(e){setError(e.message);}finally{setBusy(false);}
  }
  function fillPostedJob(id) {
    const j=jobs.find(j=>String(j.id)===id);if(!j)return;
    setTitle(j.title+' — '+j.company);
    setJD([j.title+' at '+j.company,'Location: '+j.location,j.description,'Required skills: '+j.skills.join(', ')].join('\n\n'));
  }
  const r=active?.status==='completed'?active.result:null;
  const questions=r?.interview_questions||[];
  return <div className="career-workspace">
    <section className="career-intro"><div className="career-intro-icon"><Target size={23}/></div><div><h3>One resume. One opportunity. A clearer plan.</h3><p>Understand what this role needs, refine your resume honestly, and prepare answers you can make your own.</p></div><span className={'pill '+(!config?.configured?'neutral':'')}>{config?.configured?<><Sparkles size={12}/>API key configured</>:config?'OpenAI not configured':'Checking AI connection…'}</span></section>
    {error&&<div className="error" role="alert">{error}</div>}
    {config&&!config.configured&&<div className="error">OpenAI is not configured on the backend. Add the API key to backend/.env and restart the server.</div>}
    <div className="career-layout"><aside className="career-input panel"><div className="panel-heading"><div><h3>Your target opportunity</h3><p>A specific JD creates better guidance.</p></div><Sparkles size={19}/></div>
      <form onSubmit={generate}><label>Select your resume<select aria-label="Select your resume" required value={resumeId} onChange={e=>setResumeId(e.target.value)}><option value="">Choose a resume</option>{resumes.map(r=><option key={r.id} value={r.id}>{r.title}</option>)}</select></label><button className="text-button" type="button" disabled={isDemo} onClick={onUpload}><Plus size={13}/> Upload another resume</button>
      <label className="career-title-label">Report title<input maxLength={150} value={title} onChange={e=>setTitle(e.target.value)} placeholder="e.g. Backend engineer at Acme"/></label>
      {jobs.length>0&&<label>Use a posted job (optional)<select defaultValue="" onChange={e=>fillPostedJob(e.target.value)}><option value="">Select a job to fill its JD</option>{jobs.map(j=><option key={j.id} value={j.id}>{j.title} — {j.company}</option>)}</select></label>}
      <label>Job description<textarea required minLength={100} maxLength={20000} rows={12} value={jd} onChange={e=>setJD(e.target.value)} placeholder="Paste the full job description, requirements, and responsibilities…"/></label>
      <div className="jd-tools"><button className="text-button" type="button" onClick={()=>{setJD(exampleJD);setTitle('Full-stack Developer — Example Team');}}>Use example JD</button><span>{jd.length.toLocaleString()} / 20,000</span></div>
      <label className="consent-label"><input type="checkbox" required checked={consent} onChange={e=>setConsent(e.target.checked)}/><span>Send my selected resume text and this JD to OpenAI to generate this report. API usage may incur charges.</span></label>
      <button className="button generate-button" disabled={isDemo||busy||!resumeId||!config?.configured}><Sparkles size={17}/>{busy?'Starting…':'Analyze & prepare interview'}<ArrowRight size={16}/></button>
      <p className="fine-print">Your original resume stays unchanged. Check every suggestion before using it. Reports are private to your account.</p></form>
      <div className="career-history"><div className="panel-heading"><h3>Saved reports</h3><button className="icon-button" type="button" aria-label="Refresh reports" onClick={()=>load().catch(e=>setError(e.message))}><RefreshCw size={14}/></button></div>{reports.length?reports.map(report=><button key={report.id} className={'history-item '+(selected===report.id?'active':'')} onClick={()=>setSelected(report.id)}><FileText size={16}/><div><strong>{report.title}</strong><span>{new Date(report.created_at).toLocaleDateString()} · {report.status}</span></div><span className={'history-dot '+report.status}/></button>):<p className="fine-print">Your first report will appear here.</p>}</div>
    </aside>
    <section className="career-results">
    {!active&&<div className="panel career-empty"><div className="career-empty-art"><FileText size={34}/><ArrowRight size={20}/><BookOpen size={34}/></div><span className="eyebrow">PREPARE WITH PURPOSE</span><h2>A tailored resume.<br/>A more confident conversation.</h2><p>Choose your resume and paste a JD to get a practical report built around your experience.</p><div className="career-benefits">{[['01','See your fit','Requirement-by-requirement evidence and gaps.'],['02','Refine your story','Specific additions and before-and-after rewrites.'],['03','Practice your answers','20 questions, detailed answers, and follow-ups.']].map(([n,t,d])=><div key={n}><span>{n}</span><div><strong>{t}</strong><p>{d}</p></div></div>)}</div></div>}
    {generating&&<div className="panel generation-state" role="status"><div className="generation-icon"><LoaderCircle size={31} className="spin"/></div><span className="eyebrow">YOUR REPORT IS TAKING SHAPE</span><h2>Connecting your experience<br/>to this opportunity.</h2><p>OpenAI is reading your resume and JD, drafting truthful edits, and preparing 20 interview answers. This can take a few minutes.</p><div className="generation-steps"><span><Check size={15}/>Resume and JD received</span><span><LoaderCircle className="spin" size={15}/>Generating your coaching report</span><span><BookOpen size={15}/>Interview preparation included</span></div><p className="fine-print">You can leave this page and return to Saved reports. Refreshing does not start another API request.</p></div>}
    {active?.status==='failed'&&<div className="panel career-failed"><ShieldCheck size={32}/><h2>This report could not finish.</h2><p>{active.error}</p><button className="button secondary" disabled={isDemo||busy} onClick={()=>{setResumeId(String(active.resume));setJD(active.job_description);setTitle(active.title);setSelected(null);}}>Load inputs to try again <RefreshCw size={15}/></button><p className="fine-print">A new generation request uses the API again. Existing resumes and completed reports are preserved.</p></div>}
    {r&&<><div className="panel report-header"><div><span className="eyebrow">YOUR PERSONAL COACHING REPORT</span><h2>{active.title}</h2><p>{active.resume_title} · {active.model} · {new Date(active.created_at).toLocaleDateString()}</p></div><div className="report-actions"><button className="button secondary" onClick={()=>exportReport(active)}><Download size={15}/> Export report</button><button className="icon-button" aria-label="Delete report" onClick={remove} disabled={isDemo||busy}><Trash2 size={17}/></button></div></div>
    <div className="report-tabs" role="tablist">{['Resume fit','Resume edits','Interview prep','Study plan'].map(t=><button role="tab" aria-selected={tab===t} className={tab===t?'active':''} key={t} onClick={()=>setTab(t)}>{t==='Interview prep'?<BookOpen size={15}/>:null}{t}</button>)}</div>
    {tab==='Resume fit'&&<><section className="panel coverage-panel"><div className="coverage-score"><strong>{r.coverage_score}<small>/100</small></strong><span>JD evidence coverage</span></div><div><h3>{r.job_title}</h3><p>{r.overview}</p><p className="fine-print">{r.score_explanation}</p></div></section><section className="panel strengths-panel"><h3>Your strongest connections</h3><div>{r.strengths.map((s,i)=><p key={i}><Check size={15}/>{s}</p>)}</div></section><section className="panel requirements-panel"><div className="panel-heading"><div><h3>What the role asks for</h3><p>Evidence from your resume, one requirement at a time.</p></div><span className="pill">{r.requirements.length} requirements</span></div><div className="requirement-list">{r.requirements.map((req,i)=><article key={i}><div className="requirement-heading"><strong>{req.requirement}</strong><span className={'status-pill '+req.status}>{req.status}</span></div><span className="requirement-importance">{req.importance}</span><p className="resume-evidence">“{req.resume_evidence}”</p><p>{req.recommendation}</p></article>)}</div></section><section className="panel"><h3 className="career-section-title">Skills to develop</h3><p className="fine-print">These are development targets. Add them as skills only when you can demonstrate them.</p><div className="tags">{r.skills_to_develop.map((s,i)=><span key={i}>{s}</span>)}</div></section></>}
    {tab==='Resume edits'&&<><section className="info-banner"><ShieldCheck size={17}/>These are proposed changes. Verify facts and resolve placeholders before updating your resume.</section><section className="panel tailored-summary"><div className="panel-heading"><h3>Suggested professional summary</h3><button className="text-button" onClick={()=>copy(r.tailored_summary,'summary')}><Copy size={14}/>{copied==='summary'?'Copied':'Copy'}</button></div><p>{r.tailored_summary}</p></section><section className="panel"><h3 className="career-section-title">Supported keywords to highlight</h3><div className="tags">{r.keywords_to_highlight.map((s,i)=><span key={i}>{s}</span>)}</div></section><div className="edit-list">{r.resume_edits.map((edit,i)=><article className="panel edit-card" key={i}><div className="panel-heading"><div><span className="eyebrow">{edit.action.toUpperCase()}</span><h3>{edit.section}</h3></div><span className={'pill '+(edit.needs_confirmation?'confirmation-pill':'')}>{edit.needs_confirmation?'Confirm facts first':'Review before using'}</span></div><div className="edit-comparison">{edit.original&&<div className="edit-original"><span>BEFORE</span><p>{edit.original}</p></div>}<div className="edit-suggested"><span>{edit.action==='remove'?'RECOMMENDATION':'SUGGESTED CHANGE'}</span><p>{edit.suggested}</p><button className="text-button" onClick={()=>copy(edit.suggested,'edit'+i)}><Copy size={12}/>{copied==='edit'+i?'Copied':'Copy suggestion'}</button></div></div><p className="edit-reason">{edit.reason}</p><p className="fine-print">Evidence: {edit.evidence}</p></article>)}</div></>}
    {tab==='Interview prep'&&<><section className="interview-banner"><BookOpen size={24}/><div><h3>{questions.length} questions. Answers you can make your own.</h3><p>Realistic practice based on this resume and JD. Actual interview questions will vary. Bracketed details need your own truthful examples.</p></div></section><div className="interview-controls"><label>Question category<select aria-label="Question category" value={category} onChange={e=>setCategory(e.target.value)}>{['All','technical','project','behavioral','scenario','HR'].map(c=><option key={c}>{c}</option>)}</select></label><button className="text-button" onClick={()=>setRevealed(Object.fromEntries(questions.map((_,i)=>[i,true])))}>Show all sample answers <ChevronDown size={15}/></button></div><div className="interview-list">{questions.map((q,i)=>category==='All'||q.category===category?<article className="panel interview-card" key={i}><div className="question-meta"><span className="question-number">{String(i+1).padStart(2,'0')}</span><span className="pill">{q.category}</span><span className="difficulty">{q.difficulty}</span></div><h3>{q.question}</h3><p className="why-asked">{q.why_asked}</p><details className="practice-answer"><summary>Practice your answer first</summary><textarea aria-label={'Your practice answer '+(i+1)} rows={5} value={answers[i]||''} onChange={e=>setAnswers({...answers,[i]:e.target.value})} placeholder="Try answering out loud, then write your key points here. These notes stay on this page and are not sent to OpenAI."/></details><button className="text-button reveal-answer" onClick={()=>setRevealed({...revealed,[i]:!revealed[i]})}>{revealed[i]?'Hide sample answer':'Show sample answer'}<ChevronDown size={15} style={{transform:revealed[i]?'rotate(180deg)':''}}/></button>{revealed[i]&&<div className="answer-content"><div className="sample-answer"><div className="panel-heading"><strong>Sample answer</strong><button className="text-button" onClick={()=>copy(q.sample_answer,'answer'+i)}><Copy size={13}/>{copied==='answer'+i?'Copied':'Copy'}</button></div><p>{q.sample_answer}</p></div><h4>Points to cover</h4><ul>{q.answer_points.map((p,k)=><li key={k}>{p}</li>)}</ul><div className="resume-connection"><FileText size={15}/><p>{q.resume_connection}</p></div><h4>Be ready for follow-ups</h4><ul>{q.follow_up_questions.map((p,k)=><li key={k}>{p}</li>)}</ul></div>}</article>:null)}</div></>}
    {tab==='Study plan'&&<><div className="study-grid">{r.preparation_plan.map((day,i)=><article className="panel study-day" key={i}><span className="day-label"><Clock3 size={14}/> DAY {day.day}</span><h3>{day.focus}</h3><ul>{day.tasks.map((t,k)=><li key={k}>{t}</li>)}</ul></article>)}</div><section className="panel interviewer-questions"><h3>Questions you can ask the interviewer</h3><ul>{r.questions_to_ask.map((q,i)=><li key={i}>{q}</li>)}</ul></section></>}
    <details className="report-sources panel"><summary>Source JD & report limitations</summary><h4>Job description used</h4><pre>{active.job_description}</pre><h4>Limitations</h4><ul>{r.limitations.map((l,i)=><li key={i}>{l}</li>)}</ul><p className="fine-print">Your original resume is unchanged. Generated content may contain mistakes; confirm details before use. Reports are based on the resume snapshot at generation time.</p></details></>}
    </section></div></div>;
}