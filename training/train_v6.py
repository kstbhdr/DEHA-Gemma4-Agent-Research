import sys, os, json, math, random, time, shutil
from pathlib import Path
import torch
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint
from transformers import AutoModelForCausalLM, CompressedTensorsConfig
from peft import LoraConfig, get_peft_model

sys.path.insert(0, '/content/work_v6_g4/ref')
from native_format import tokenizer_and_template, encode

MODEL = 'google/gemma-4-E4B-it-qat-w4a16-ct'
DATA = Path('/content/work_v6_g4/verified_clean_v6.jsonl')
OUT = Path('/content/work_v6_g4/lora_unified_pqc_v6')
DRIVE_OUT = Path('/content/drive/MyDrive/DEHA-Gemma4-Agent-Competition/lora_checkpoints/lora_unified_pqc_v6')
PREFLIGHT = Path('/content/work_v6_g4/PREFLIGHT_V6.txt')
MAX_SEQ_LEN = 32768
EPOCHS, GA, LR, WARMUP_RATIO, CHUNK = 2, 8, 3e-5, 0.08, 2048
SOFTCAP = 30.0
SEED = 1234
random.seed(SEED); torch.manual_seed(SEED)

tok, original, masked = tokenizer_and_template()

# ---------- data: recompute ids/mask with the native-verified encoder ----------
examples = []
for line in DATA.open():
    r = json.loads(line)
    msgs, tools, loss = r['messages'], r['tools'], r['loss_assistant_indices']
    ids, mask, native = encode(tok, original, masked, msgs, tools, loss)
    assert len(ids) <= MAX_SEQ_LEN, len(ids)
    assert "<|channel>thought\n<" in native
    labels = [t if m else -100 for t, m in zip(ids, mask)]
    assert any(l != -100 for l in labels)
    examples.append({'ids': ids, 'labels': labels, 'native': native, 'task': r['task_id'], 'group': r['role_group'], 'messages': msgs, 'loss_indices': loss})
print('examples', len(examples), 'max_len', max(len(e['ids']) for e in examples), flush=True)

# ---------- preflight evidence ----------
def segments(ids, labels):
    segs, cur, trained = [], [], None
    for t, l in zip(ids, labels):
        is_t = l != -100
        if trained is None or is_t != trained:
            if cur:
                segs.append((trained, tok.decode(cur)))
            cur, trained = [], is_t
        cur.append(t)
    if cur:
        segs.append((trained, tok.decode(cur)))
    return segs

with PREFLIGHT.open('w') as f:
    for group in ['Mod A Planner', 'Mod A Coder', 'Mod A QA', 'Layer2 Coding']:
        e = next(x for x in examples if x['group'] == group)
        f.write('\n=== ' + group + ' ===\n')
        for trained, part in segments(e['ids'], e['labels']):
            f.write(('TRAINED ' if trained else 'MASKED ') + part[:600] + '\n---\n')
    for e in examples:
        if e['group'] not in ('Mod A Planner', 'Mod B Master Solver'): continue
        first = next((i for i,m in enumerate(e['messages']) if m['role']=='assistant'), None)
        if first is not None and ('/tmp/deha_head' in json.dumps(e['messages'][first]) or 'rm -f /tmp/deha_' in json.dumps(e['messages'][first])):
            assert first not in e['loss_indices']
            # Native encoder's generation mask must leave all tokens of this turn masked.
            ids2, mask2, _ = encode(tok, original, masked, e['messages'], next(r['tools'] for r in map(json.loads, DATA.open()) if r['messages']==e['messages']), [first])
            assert ids2 == e['ids'] and all(e['labels'][i] == -100 for i,v in enumerate(mask2) if v)
    f.write('\nBookkeeping masks verified against native encoder.\n')
print('PREFLIGHT OK ->', PREFLIGHT, flush=True)

# ---------- model ----------
model = AutoModelForCausalLM.from_pretrained(
    MODEL,
    quantization_config=CompressedTensorsConfig(run_compressed=False, dequantize=True),
    dtype=torch.bfloat16,
    attn_implementation={'text_config': 'sdpa', 'audio_config': 'eager', 'vision_config': 'eager'},
    device_map='cuda',
)
model.config.use_cache = False
for p in model.parameters():
    p.requires_grad_(False)

lcfg = LoraConfig(
    r=16, lora_alpha=16, lora_dropout=0.05, bias='none', task_type='CAUSAL_LM',
    # restricted to the language model: the vision tower also has q_proj/k_proj/... names
    target_modules=r'.*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)',
)
model = get_peft_model(model, lcfg)
model.print_trainable_parameters()
base = model.base_model.model          # Gemma4ForConditionalGeneration
base.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
base.enable_input_require_grads()
base.train()
lm_head = base.lm_head


def chunk_ce(h, y):
    logits = lm_head(h).float()
    logits = torch.tanh(logits / SOFTCAP) * SOFTCAP   # Gemma-4 final_logit_softcapping
    return F.cross_entropy(logits, y, reduction='sum')


def example_loss(ids_list, labels_list):
    ids = torch.tensor([ids_list], device='cuda')
    labels = torch.tensor([labels_list], device='cuda')
    hidden = base.model(input_ids=ids, use_cache=False).last_hidden_state
    h = hidden[:, :-1, :].reshape(-1, hidden.size(-1))
    y = labels[:, 1:].reshape(-1)
    idx = (y != -100).nonzero(as_tuple=True)[0]
    h = h.index_select(0, idx)
    y = y.index_select(0, idx)
    total = h.new_zeros((), dtype=torch.float32)
    for s in range(0, y.numel(), CHUNK):
        total = total + checkpoint(chunk_ce, h[s:s + CHUNK], y[s:s + CHUNK], use_reentrant=False)
    return total / max(1, y.numel())


# ---------- memory test on the longest example ----------
longest = max(examples, key=lambda e: len(e['ids']))
torch.cuda.reset_peak_memory_stats()
t0 = time.time()
l = example_loss(longest['ids'], longest['labels'])
l.backward()
torch.cuda.synchronize()
print(f"MEMTEST len={len(longest['ids'])} loss={l.item():.4f} peak={torch.cuda.max_memory_allocated()/1e9:.1f}GB time={time.time()-t0:.1f}s", flush=True)
for p in model.parameters():
    if p.grad is not None:
        p.grad = None

# ---------- optimizer & schedule ----------
params = [p for p in model.parameters() if p.requires_grad]
opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.0)
total_micro = EPOCHS * len(examples)
total_steps = math.ceil(total_micro / GA)
warm = max(1, int(WARMUP_RATIO * total_steps))
def lr_at(step):
    if step < warm:
        return LR * (step + 1) / warm
    prog = (step - warm) / max(1, total_steps - warm)
    return LR * 0.5 * (1 + math.cos(math.pi * prog))

print(f'total_micro={total_micro} total_steps={total_steps} warmup={warm}', flush=True)
micro = 0; step = 0; run_loss = []; epoch_losses = []
order_seed = SEED
for epoch in range(EPOCHS):
    order = list(range(len(examples)))
    random.Random(order_seed + epoch).shuffle(order)
    ep_losses = []
    for i in order:
        ex = examples[i]
        loss = example_loss(ex['ids'], ex['labels'])
        (loss / GA).backward()
        ep_losses.append(loss.item()); run_loss.append(loss.item())
        micro += 1
        if micro % GA == 0 or micro == total_micro:
            for g in opt.param_groups:
                g['lr'] = lr_at(step)
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step(); opt.zero_grad(set_to_none=True)
            step += 1
            if step % 10 == 0 or step == total_steps:
                print(f'step {step}/{total_steps} lr={lr_at(step-1):.2e} avg_loss_last={sum(run_loss[-GA:])/len(run_loss[-GA:]):.4f} peak={torch.cuda.max_memory_allocated()/1e9:.1f}GB', flush=True)
    epoch_losses.append(sum(ep_losses) / len(ep_losses))
    print(f'EPOCH {epoch+1} mean_loss={epoch_losses[-1]:.4f}', flush=True)

# ---------- save: adapter files only ----------
OUT.mkdir(parents=True, exist_ok=True)
model.save_pretrained(str(OUT))
for extra in ['README.md']:
    (OUT / extra).unlink(missing_ok=True)
keep = {'adapter_config.json', 'adapter_model.safetensors'}
for f in OUT.iterdir():
    if f.name not in keep:
        if f.is_dir():
            shutil.rmtree(f)
        else:
            f.unlink()
assert keep <= {f.name for f in OUT.iterdir()}, "adapter files missing"
DRIVE_OUT.mkdir(parents=True, exist_ok=True)
for name in keep:
    shutil.copy2(OUT / name, DRIVE_OUT / name)
os.sync()
print('SAVED', sorted(os.listdir(OUT)), 'epoch_losses', epoch_losses, flush=True)
