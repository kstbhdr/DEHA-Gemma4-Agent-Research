import json,re,sys,collections,ast,os,shutil
from pathlib import Path
sys.path.insert(0,'/content/work_v6_g4/ref')
from native_format import tokenizer_and_template,encode
P=Path('/content/work_v6_g4'); rows=[json.loads(x) for x in (P/'verified_hybrid_v6.jsonl').open()]
eval_ids=set('requests_7205 requests_6644 requests_7309 requests_7315 fastapi_14301 fastapi_14616 rich_3454 rich_3518 fastapi_14964 rich_3468 rich_3506 rich_3718 rich_3882 rich_3052 fastapi_14356 fastapi_14791 fastapi_14482 fastapi_13920 fastapi_14258 httpx_3672'.split())
tok,orig,masked=tokenizer_and_template(); valid=[]; coding=[]; reasons=collections.Counter(); masked_count=0
for r in rows:
 g=r['role_group']
 if g=='Layer2 Planning': reasons['planning']+=1; continue
 if r['task_id'] in eval_ids: reasons['eval_overlap']+=1;continue
 m=r['messages']
 if any(a['role']==b['role']=='assistant' for a,b in zip(m,m[1:])): reasons['consecutive_assistant']+=1;continue
 if g=='Layer2 Coding':
  content='\n'.join(str(x.get('content','')) for x in m if x['role']=='assistant')
  if re.search(r'\b(setup\.py|distutils|setuptools)\b',content,re.I): reasons['coding_setup']+=1;continue
  blocks=re.findall(r'```(?:python|py)\s*\n(.*?)```',content,re.S|re.I)
  score=0
  for b in blocks:
   try: tree=ast.parse(b)
   except SyntaxError: continue
   funcs=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]
   exits=[n for n in ast.walk(tree) if isinstance(n,(ast.Return,ast.Raise,ast.Yield,ast.YieldFrom))]
   if funcs and exits: score=max(score,len(funcs)*3+len(exits)*2+min(len(b)//300,10))
  if not score: reasons['coding_not_python_logic']+=1;continue
 try:
  inds=[i for i,x in enumerate(m) if x['role']=='assistant'] if r.get('loss_assistant_indices') is None else list(r['loss_assistant_indices'])
  if g in ('Mod A Planner','Mod B Master Solver'):
   first=next((i for i,x in enumerate(m) if x['role']=='assistant'),None)
   if first is not None and re.search(r'rm\s+-f\s+/tmp/deha_|/tmp/deha_head',json.dumps(m[first])):
    if first in inds: inds.remove(first);masked_count+=1
  r['loss_assistant_indices']=inds
  ids,mask,native=encode(tok,orig,masked,m,r['tools'],inds)
  if re.search(r'<\|turn>model\n(?:(?!<\|channel>thought|<turn\|>|<\|tool_call>).)+<\|channel>thought',native,re.S): reasons['text_before_thought']+=1;continue
  if len(ids)>32768: reasons['too_long']+=1;continue
 except Exception as e:
  reasons['encoding_'+type(e).__name__]+=1;continue
 if g=='Layer2 Coding': coding.append((score,r))
 else: valid.append(r)
coding.sort(key=lambda x:-x[0]); valid += [r for _,r in coding[:120]]
assert len(coding)>=120, f'Only {len(coding)} qualified coding examples; cannot safely manufacture 120'
assert not any(r['task_id'] in eval_ids for r in valid)
assert not any(any(a['role']==b['role']=='assistant' for a,b in zip(r['messages'],r['messages'][1:])) for r in valid)
out=P/'verified_clean_v6.jsonl';out.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in valid))
summary=f"Counts: {dict(collections.Counter(r['role_group'] for r in valid))}\nDiscarded: {dict(reasons)}\nQualified coding: {len(coding)}; selected: 120\nBookkeeping turns masked: {masked_count}\nEval overlap: 0\nBad format rows: 0\n"
print(summary); d=Path('/content/drive/MyDrive/DEHA-Gemma4-Agent-Competition/lora_datasets/v6_clean');d.mkdir(parents=True,exist_ok=True);shutil.copy2(out,d/out.name);(d/'CLEAN_AUDIT.md').write_text('# v6 clean audit\n\n'+summary);os.sync()
