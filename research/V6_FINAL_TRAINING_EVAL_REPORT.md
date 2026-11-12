# V6 final training and evaluation report

## Data and training

528 rows: 108 Planner, 112 Coder, 94 QA, 94 Master Solver, 120 Python Coding. Eight malformed rows removed; 202 bookkeeping turns masked; eval overlap 0. Agent trace share 77.27%, below requested 78% because of the required 120 coding rows and removal of eight bad rows.

MEMTEST len=28624 loss=1.0090 peak=37.3GB time=29.7s
step 10/132 lr=3.00e-05 avg_loss_last=1.3151 peak=37.3GB
step 20/132 lr=2.96e-05 avg_loss_last=0.9482 peak=37.3GB
step 30/132 lr=2.82e-05 avg_loss_last=1.0694 peak=37.8GB
step 40/132 lr=2.60e-05 avg_loss_last=0.9843 peak=37.9GB
step 50/132 lr=2.31e-05 avg_loss_last=0.8440 peak=37.9GB
step 60/132 lr=1.96e-05 avg_loss_last=0.7472 peak=37.9GB
EPOCH 1 mean_loss=0.9704
step 70/132 lr=1.58e-05 avg_loss_last=0.7791 peak=37.9GB
step 80/132 lr=1.19e-05 avg_loss_last=0.8488 peak=37.9GB
step 90/132 lr=8.29e-06 avg_loss_last=0.8107 peak=37.9GB
step 100/132 lr=5.10e-06 avg_loss_last=0.8164 peak=37.9GB
step 110/132 lr=2.55e-06 avg_loss_last=0.7472 peak=37.9GB
step 120/132 lr=8.33e-07 avg_loss_last=0.6081 peak=37.9GB
step 130/132 lr=4.47e-08 avg_loss_last=0.8316 peak=37.9GB
step 132/132 lr=4.97e-09 avg_loss_last=0.7941 peak=37.9GB
EPOCH 2 mean_loss=0.7317
SAVED ['adapter_config.json', 'adapter_model.safetensors'] epoch_losses [0.9704386251555248, 0.731743071708038]

## Smoke results

The initial three-task all-LoRA smoke failed: no submit, repeated planner/coder tool calls. The base-planner and prompt/penalty diagnostic variants also showed repeated calls or malformed edit_file arguments. See logs/run_32_smoke_* for traces. The requested green-test immediate-submit behavior was not verified. All 20 environment preflights passed.

## Evaluation

- run_32A_lora_v6_all: 0/20 resolved (20 results)
- run_32B_lora_v6_coder_qa: 0/20 resolved (20 results)

Selected: run_32A_lora_v6_all (ties choose A). Full results and traces: logs/run_32A_lora_v6_all and logs/run_32B_lora_v6_coder_qa. Smoke failure remains a material limitation.

Both runs produced 0/20 submitted patches. The archive is a tie-selected comparison artifact and is not recommended for submission: the smoke test and required QA submission behavior did not pass. Local and Drive adapter files matched by SHA-256; ZIP integrity was verified.
