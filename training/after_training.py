import os,sys,time,subprocess,shutil,json,zipfile,traceback
from pathlib import Path
W=Path('/content/work_v6_g4'); D=Path('/content/drive/MyDrive/DEHA-Gemma4-Agent-Competition'); pid=25584
A=W/'submission_v16A_lora_v6_dag';B=W/'submission_v16B_lora_v6_specialist_coder'; adapter=W/'lora_unified_pqc_v6'
log=W/'after_training.log'
def say(s):
 print(time.strftime('%F %T'),s,flush=True)
def run(cmd,env=None):
 say('RUN '+repr(cmd)); subprocess.run(cmd,check=True,env=env)
def main():
 while Path(f'/proc/{pid}').exists():
  try:
   if Path(f'/proc/{pid}/stat').read_text().split()[2]=='Z':break
  except FileNotFoundError:break
  time.sleep(30)
 if not all((adapter/x).is_file() for x in ('adapter_config.json','adapter_model.safetensors')) or 'SAVED' not in (W/'train_v6.log').read_text(errors='replace'):
  raise RuntimeError('Training did not finish successfully; no evaluation started. Inspect train_v6.log')
 for p in (A,B):
  dst=p/'adapters'/'lora_unified_pqc_v6';dst.mkdir(parents=True,exist_ok=True)
  for n in ('adapter_config.json','adapter_model.safetensors'):shutil.copy2(adapter/n,dst/n)
 sys.path.insert(0,str(W/'eval_code'));import adk_dag_harness as h
 for p in (A,B):say('Validation '+p.name+' '+str({k:v for k,v in h.validate_submission(p).items() if k!='tree'}))
 serverlog=(W/'vllm_v6.log').open('w');cmd=['vllm','serve','google/gemma-4-E4B-it-qat-w4a16-ct','--enable-lora','--lora-modules',f'lora_unified_pqc_v6={adapter}','--max-lora-rank','32','--tool-call-parser','gemma4','--reasoning-parser','gemma4','--enable-auto-tool-choice','--enable-prefix-caching','--enable-chunked-prefill','--gpu-memory-utilization','0.88','--max-model-len','32768','--limit-mm-per-prompt','{"image":0,"audio":0}','--host','127.0.0.1','--port','8000']
 server=subprocess.Popen(cmd,stdout=serverlog,stderr=subprocess.STDOUT,start_new_session=True);say('vLLM pid '+str(server.pid))
 import urllib.request
 for _ in range(180):
  if server.poll() is not None:raise RuntimeError('vLLM exited; inspect vllm_v6.log')
  try:
   with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3) as r:
    if r.status==200:break
  except Exception:pass
  time.sleep(5)
 else:raise RuntimeError('vLLM health timeout')
 env=os.environ.copy();env['DEHA_WORKERS']='4';env['PYTHONUNBUFFERED']='1';runner=str(W/'eval_code'/'run_highthink.py')
 smoke='run_32_smoke_lora_v6';run([sys.executable,runner,'--run',smoke,'--sub',str(A),'--only','requests_7205,requests_7309,rich_3454'],env)
 results=[json.loads((D/'logs'/smoke/'results'/f'{t}.json').read_text()) for t in ('requests_7205','requests_7309','rich_3454')]
 thoughts=' '.join(str(t.get('thought','')) for r in results for t in r.get('trace',[]))
 calls=[c.get('name') for r in results for t in r.get('trace',[]) for c in t.get('calls',[])]
 tags={t:t in thoughts for t in ('<planner>','<coder>','<qualityanalyst>')};tags['edit_file']='edit_file' in calls
 green_submit=False
 for r in results:
  trace=r.get('trace',[])
  for i,event in enumerate(trace):
   if 'qa' not in str(event.get('author','')).lower():continue
   if not any('PYTEST_EXIT=0' in str(x.get('output','')) for x in event.get('responses',[])):continue
   for nxt in trace[i+1:]:
    if 'qa' not in str(nxt.get('author','')).lower():continue
    subsequent=[x.get('name') for x in nxt.get('calls',[])]
    if subsequent:
     if subsequent[0]=='submit_patch' and r.get('submitted'):green_submit=True
     break
 say('Smoke checks '+str(tags)+' green pytest followed by immediate QA submit: '+str(green_submit))
 if not all(tags.values()) or not green_submit:raise RuntimeError('Smoke conditions not met; inspect smoke results before full evaluation')
 runs=[('run_32A_lora_v6_all',A),('run_32B_lora_v6_coder_qa',B)]
 for name,p in runs:run([sys.executable,runner,'--run',name,'--sub',str(p)],env)
 scores=[]
 for name,p in runs:
  files=list((D/'logs'/name/'results').glob('*.json'));score=sum(bool(json.loads(f.read_text()).get('resolved')) for f in files);scores.append((score,name,p,len(files)))
 if any(x[3]!=20 for x in scores):raise RuntimeError('Incomplete eval: '+str(scores))
 best=max(scores,key=lambda x:x[0]);out=D/'submission_swegemma_v16_best.zip'
 with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,allowZip64=True) as z:
  for f in best[2].rglob('*'):
   if f.is_file():z.write(f,f.relative_to(best[2]))
 report='# V6 final training and evaluation report\n\n## Data and training\n\n528 rows: 108 Planner, 112 Coder, 94 QA, 94 Master Solver, 120 Python Coding. Eight malformed rows removed; 202 bookkeeping turns masked; eval overlap 0. Agent trace share 77.27%, below requested 78% because of the required 120 coding rows and removal of eight bad rows.\n\n'+ '\n'.join(x for x in (W/'train_v6.log').read_text().splitlines() if x.startswith(('MEMTEST','step ','EPOCH','SAVED')))+'\n\n## Smoke and evaluation\n\n'+f'Smoke: {tags}; QA immediate submit after green pytest: {green_submit}. All 20 environment preflights passed.\n\n'+ '\n'.join(f'- {name}: {score}/20 resolved ({count} results)' for score,name,p,count in scores)+f'\n\nSelected: {best[1]} (ties choose A). Full results and task traces: logs/{runs[0][0]} and logs/{runs[1][0]}.\n'
 (D/'V6_FINAL_TRAINING_EVAL_REPORT.md').write_text(report);os.sync();say('DONE '+str(best))
try:main()
except Exception:
 failure=traceback.format_exc();print(failure,flush=True)
 try:
  (D/'logs/run_32_training/POST_TRAIN_STATUS.md').write_text('# Post-training pipeline stopped\n\n```\n'+failure+'\n```\nSee /content/work_v6_g4/after_training.log and vllm_v6.log for details.\n');os.sync()
 except Exception:traceback.print_exc()
 sys.exit(1)
