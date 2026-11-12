Declarative Multi-Agent Topologies, Synthetic Chain-of-Thought Collapse, and Budget-Aware Orchestration for Gemma-4 Software Engineering Agents
Author: Bahadır Kuşat (DEHA AI Research)
Competition Track: Gemma-4 Developer Agent — Paper Track (November 2026)


________________


Abstract
Deploying open-weights Large Language Models (LLMs) as autonomous software engineering (SWE) agents within sandboxed declarative frameworks exposes critical failure modes at the intersection of model scale, multi-agent topology, context compaction, and fine-tuning alignment. In this paper, we present a systematic empirical study across 36 iterative evaluation runs on a stratified 20-task benchmark (requests, fastapi, rich, httpx) under the official swegemma / Google ADK declarative harness (adk-submission and adk-eval-core) targeting 4-bit Quantization-Aware Trained (QAT) Gemma-4-E4B and Gemma-4-31B models.


Our contributions are fourfold:


1. Scale-Dependent Topology Inversion: While a 4-stage Directed Acyclic Graph (Planner -> Coder A -> Coder B -> QA Judge) achieves up to 85.0% (17/20) source-file localization and 30.0% (6/20) single-run resolution (50.0% / 10/20 union across runs) on Gemma-4-E4B, the identical read-only Planner topology fails catastrophically on Gemma-4-31B due to Exploratory Budget Starvation—ignoring prompt-level turn caps to exhaust the shared tool budget on read-only exploration. Collapsing the topology into a direct execution-first Fixer -> QA Judge loop immediately unlocks 50.0% (10/20) resolution under strict budgets (15 min, 58 calls).
2. Asymmetric Parallel Orchestration and Consensus Verification: Scaling to a 30-minute, 110-call budget with a LoopAgent wrapping ParallelAgent(Fixer A, Fixer B) -> QA Judge increases single-run resolution to 65.0% (13/20) and two-run union to 70.0% (14/20) (+116.7% relative over the best single E4B run). Critically, branch attribution reveals a counter-intuitive result: the primary /workspace branch (Fixer A, $T=0.15$) accounts for 10/13 resolutions and harness-level Automatic Unsubmitted Patch Recovery accounts for 3/13, whereas the exploratory branch (Fixer B, $T=0.45$) wins 0/13 patches directly while consuming 40–55% of the shared tool budget. However, Fixer B provides a vital Consensus Witness signal: when both independent branches break the exact same pre-existing unit test, our CONSENSUS rule identifies tests that pin buggy legacy behavior, cutting resolution latency by 3.6× on affected tasks.
3. Synthetic Chain-of-Thought (CoT) Collapse: Fine-tuning Gemma-4-E4B (rank-16 LoRA, bfloat16 dequantized QAT with Gemma-4 logit softcapping at 30.0) on 528 rigorously audited agent trajectories annotated with concise (20–26 token) third-person role summaries (<planner>, <coder>, <qualityanalyst>) reduces resolution from 30.0% to 0.0% (0/20). Trace forensics demonstrate that short post-hoc rationales overwrite Gemma-4's native first-person <|channel>thought reasoning distribution (mean 367–410 tokens/turn), inducing a 0.3-second empty-tag emission followed by unguided tool-call looping.
4. Hardware-Frugal Speculative Prototyping: Combining 3-bit GGUF quantization (Q3_K_M), 4-bit KV-cache (q4_0), and Multi-Token Prediction (draft-mtp) fits two concurrent 32,768-token Gemma-4-31B agent slots into 18.0 GB VRAM on a single 24 GB NVIDIA L4 GPU at 58–77 tokens/s aggregate decode throughput (45% MTP acceptance, 4.6 tokens/step), enabling rapid local architectural iteration prior to 4×L4 W4A16 vLLM deployment.


________________


1. Introduction
Autonomous repository-level issue resolution requires an agent to localize defects across tens of thousands of lines of code, formulate a root-cause hypothesis, synthesize a minimal syntactic and semantic patch, execute targeted regression suites, and submit a clean unified diff—all under strict wall-clock, context-window, and tool-invocation budgets. Unlike unconstrained Python agent frameworks where arbitrary orchestration logic can be imperative-coded on the host, the Gemma-4 Developer Agent competition enforces a strict declarative security boundary via adk-submission. Competitors submit pure YAML agent specifications (LlmAgent, SequentialAgent, ParallelAgent, LoopAgent), markdown instructions, optional eval_config.yaml operational budgets, and optional PEFT/LoRA weights, which are compiled into live Google Agent Development Kit (ADK) trees without dynamic Python imports (importlib is disabled).


Operating within this declarative contract raises fundamental systems and alignment questions for open-weights Gemma-4 models (gemma-4-e4b-it-qat-w4a16-ct and gemma-4-31b-it-qat-w4a16-ct):


* RQ1 (Topology vs. Scale): Does a specialized multi-agent division of labor (separate Planner, Coder, and QA sub-agents) transfer monotonically from a 4B-class model (E4B) to a 31B-class model (31B)?
* RQ2 (Parallel Diversity vs. Shared Budget Contention): When orchestrating concurrent patch generators via ParallelAgent inside a single shared container (/workspace) and a shared per-task tool budget, how do sandbox path resolution semantics, automatic patch recovery, and branch diversity interact?
* RQ3 (Reasoning Alignment under LoRA SFT): Can a compact E4B model be elevated toward 31B performance via Supervised Fine-Tuning (SFT) on verified SWE-bench trajectories when intermediate reasoning steps are represented by concise role-tagged summaries?
* RQ4 (Thinking Budgets and Context Compaction): How much test-time compute (thinking_budget) do Gemma-4 models actually consume per turn, and what failure modes emerge during long-horizon context compaction (EventsCompactionConfig)?


Across 36 controlled experimental iterations (run_01 through run_36), we systematically answer each question with trace-level forensic evidence, culminating in our production submission_swegemma_31b_parallel_v2 architecture (65.0% single-run, 70.0% union resolution on our 20-task benchmark).


________________


2. System Constraints & Experimental Methodology
2.1. Evaluation Stack and Benchmark Suite
All experiments adhere strictly to the three-layer competition stack: (1) adk-submission for declarative YAML validation (validate_directory and validate_single_declared_model, enforcing zero cross-model mixing within a submission), (2) adk-eval-core for sandboxed execution and token/budget accounting, and (3) swegemma for two-phase hermetic evaluation. In Phase 1, the agent interacts with Container A (/workspace, editable install at baseline commit) using up to 9 bound tools (read_file, edit_file, run_command, get_status, search_similar_code, get_code_neighbors, find_files, submit_patch, etc.). In Phase 2 (verify_task), the extracted unified diff (git add -N . && git diff --binary) is applied to a fresh Container B alongside held-out Fail-to-Pass (F2P) and Pass-to-Pass (P2P) pytest suites.


To ensure zero data contamination and deterministic cross-run comparability, we fixed a stratified 20-task evaluation benchmark (EVAL_20_IDS, denoted bench20) spanning four major Python ecosystems and varying test-suite complexities (1 to 36 F2P tests):


* requests (4 tasks): requests_7205, requests_6644, requests_7309, requests_7315
* fastapi (8 tasks): fastapi_14301, fastapi_14616, fastapi_14964, fastapi_14356, fastapi_14791, fastapi_14482, fastapi_13920, fastapi_14258
* rich (7 tasks): rich_3454, rich_3518, rich_3468, rich_3506, rich_3718, rich_3882, rich_3052
* httpx (1 hard task): httpx_3672
2.2. Hardware-Frugal Local Prototyping vs. 4×L4 Production Target
While the official Kaggle evaluation environment provisions 4× NVIDIA L4 GPUs (96 GB total VRAM, Ada sm_89) running vLLM with tensor_parallel_size=4 on official w4a16 Compressed-Tensors checkpoints (max_model_len=32768), running full 20-task ablations exclusively on 96 GB instances (e.g., NVIDIA RTX PRO 6000 Blackwell) is cost-prohibitive. Conversely, fitting Gemma-4-31B (~18 GB in 4-bit, plus a 262k-vocabulary output head and two concurrent 32k KV-cache slots) onto a single 24 GB L4 (~22.5 GiB usable under ECC) triggers Out-Of-Memory (OOM) failures under standard serving configurations.


We solved this development bottleneck by decoupling the local OpenAI-compatible inference server from the declarative submission package:


* Local 1×L4 (24 GB) Prototyping Engine: We compiled llama.cpp (f3b407c, -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=89) to serve unsloth/gemma-4-31B-it-GGUF (Q3_K_M, 14.7 GB) paired with a Multi-Token Prediction draft model (mtp-google_gemma-4-31B-it-Q4_0.gguf, --spec-type draft-mtp --spec-draft-n-max 8), Flash Attention (-fa on), 4-bit quantized K/V caches (-ctk q4_0 -ctv q4_0), and two parallel 32,768-token slots (-np 2 -c 65536). This configuration stabilizes at exactly 18.0 GB peak VRAM (0 OOMs across all 20-task runs) while elevating single-slot decode speed from 14.8 tok/s to 56.0 tok/s and dual-slot concurrent throughput to 58–77 tok/s (MTP acceptance rate 0.33–0.47, mean 4.6 accepted tokens/draft; 12k-token prefill at 300–578 tok/s depending on L4 clock bin).
* Kaggle 4×L4 Production Package: The validated YAML submission archives remain 100% compliant with official vLLM (gemma-4-31b-it-qat-w4a16-ct and gemma-4-e4b-it-qat-w4a16-ct), passing validate_submission with 0 errors and 0 warnings.


________________


3. Architectural Evolution & Key Empirical Discoveries
3.1. Discovery 1: Scale-Dependent Topology Inversion (E4B vs. 31B)
On the compact Gemma-4-E4B model, combining localization, code editing, and test verification inside a single monolithic prompt frequently led to premature patch submission or syntax corruption. Decomposing the workflow into a 4-agent sequential DAG (Planner -> Coder A -> Coder B -> QA Judge, architecture v5.8) proved highly effective for E4B:


* Restricting Planner to read-only exploration tools (read_file, search_similar_code, find_files) and passing structured handoff artifacts (/tmp/deha_isolated_tasks.json) achieved 14/20 (70.0%) source-file localization in run_21 and climbed to 17/20 (85.0%) in run_33_v6g after adding false-pass reproduction script checks.
* Across 18 pure E4B-QAT runs, single-run resolution peaked at 6/20 (30.0%) (run_21, run_28A, and run_30_base_highthink achieving 6/15 before turn-cap truncation), while the union of solved tasks across E4B runs reached 10/20 (50.0%), proving that E4B possesses latent solving capacity for half the benchmark when orchestrated without turn starvation.
* Critical State-Wipe Bug (run_31): Forensic inspection of multi-iteration loops revealed that a seemingly benign initial bookkeeping command (rm -f /tmp/deha_*) inside Planner wiped /tmp/deha_qa_feedback.md at the start of Iteration 2 before Coder could read the failure diagnosis, silently breaking closed-loop repair across 5 tasks.


The 31B Inversion (Exploratory Budget Starvation): When we ported this exact 4-agent DAG to Gemma-4-31B, resolution stalled completely on complex repositories. Trace analysis revealed a striking behavioral divergence: despite explicit system instructions commanding Planner to "stop and hand off within 12 tool calls," Gemma-4-31B's stronger intrinsic curiosity caused it to chase transitive call chains across the codebase until it exhausted all 58/58 available tool calls in read-only mode—terminating before Coder could execute a single edit. Even in our final run_36 experiments, soft prompt caps ("finish within 20–25 calls") were routinely ignored by 31B (e.g., rich_3468, where Fixer B and Fixer A executed 63 and 48 calls respectively).


Architectural Principle 1: Prompt-level tool-call budgets are unenforceable on 31B-scale reasoning models; budget allocation must be enforced structurally via agent topology. Removing the standalone Planner and allowing 31B to operate directly as an integrated Fixer -> QA Judge loop (run_35_l4_31b_gguf, 15-minute / 58-call cap) immediately jumped single-run performance from 6/20 (E4B) to 10/20 (50.0%), solving httpx_3672 (hard, 5 F2P), fastapi_14356 (medium, 8 F2P), and fastapi_14791 (36 F2P tests solved in just 7 tool calls / 180s) on the first pass.


________________


3.2. Discovery 2: Asymmetric Parallelism, Sandbox Path Traps, and the CONSENSUS Rule
Error taxonomy of the 10 unsolved tasks in run_35 revealed two distinct bottlenecks: (1) 6 tasks hit the 900s / 58-call ceiling mid-repair (including rich_3454 and requests_7309, where valid patches existed in /workspace without submit_patch), and (2) 4 tasks achieved 100% file localization (1/1 gold file match) but committed to a flawed edge-case hypothesis.


To address both failure modes simultaneously, we designed submission_swegemma_31b_parallel_v2, configuring eval_config.yaml to expand per-task operational limits (max_time_minutes: 30, max_tool_calls: 110, max_turns: 200, timeout_seconds: 300) and structuring the ADK graph as: $$\text{LoopAgent}(N=3) \longrightarrow \text{SequentialAgent}\big[\text{ParallelAgent}(\text{Fixer}_A \parallel \text{Fixer}_B),\ \text{QA_Judge}\big]$$


Designing conflict-free parallel execution inside swegemma uncovered three critical systems insights:


1. Sandbox Path-Stripping Trap (HARNESS_README §6.2): Because ParallelAgent executes sub-agents concurrently against the same Container A, two agents editing /workspace simultaneously corrupt each other's working tree. Our initial isolation design cloned /workspace to /tmp/wt_b for Fixer B. However, trace auditing revealed that swegemma's built-in read_file and edit_file tools strip leading / characters and resolve all paths strictly inside /workspace—meaning edit_file("/tmp/wt_b/foo.py") silently wrote to /workspace/tmp/wt_b/foo.py or mutated Fixer A's files! We resolved this structurally by removing read_file and edit_file from Fixer B's YAML toolset, restricting Fixer B to run_command over a 0.2-second shared clone (git clone --shared /workspace /tmp/wt_b) equipped with a lightweight Python helper (/tmp/deha_bedit.py) that outputs /tmp/patch_b.diff.
2. Preserving Automatic Unsubmitted Patch Recovery: Under swegemma §8.1, if an episode hits max_time_minutes or max_tool_calls before submit_patch() is invoked, the harness automatically extracts git diff from /workspace. Had both parallel branches worked in /tmp/wt_a and /tmp/wt_b, any timeout prior to QA Judge would yield an empty /workspace diff and forfeit the task. By anchoring conservative Fixer A ($T=0.15$) directly inside /workspace while isolating exploratory Fixer B ($T=0.45$) in /tmp/wt_b, /workspace continuously holds the highest-probability surgical patch. In run_36, this single design decision salvaged 3/13 (23.1%) of all solved tasks (fastapi_14616, rich_3052, httpx_3672) when parallel tool calls hit 110/110 before QA could run.
3. The CONSENSUS Legacy-Test Rule: During verification on requests_7309, both Fixer A and Fixer B independently synthesized the exact fix required by the issue description, yet both broke a single existing unit test that explicitly asserted the old, buggy behavior. A naive QA Judge rejected both patches, causing a 955.9s timeout loop in run_35. In v2, we introduced a deterministic tournament script (/tmp/deha_qa2.py, written via unquoted <<PEOF heredoc to eliminate trailing-quote PEOF' LLM generation typos and save ~1,200 output tokens/turn) implementing CONSENSUS: if both Fixer A and Fixer B pass syntax/AST checks and fail the exact same pre-existing test(s), treat those tests as pinning legacy buggy behavior and immediately call submit_patch() on Fixer A. On requests_7309, resolution time plummeted from 955.9s (unsubmitted) to 263.6s (19 calls, submitted)—a 3.6× speedup.


________________


3.3. Discovery 3: Synthetic Chain-of-Thought Collapse in LoRA Fine-Tuning
To boost Gemma-4-E4B for the Small Model track, we constructed a rigorously audited 528-example multi-turn dataset (v6_clean: 108 Planner, 112 Coder, 94 QA, 94 Master Solver SWE-bench trajectories + 120 pure Python bug-fix examples; 0% overlap with EVAL_20_IDS; 8 malformed turn-order rows removed; 202 legacy rm -f /tmp/deha_* bookkeeping turns loss-masked to -100). Using an NVIDIA RTX PRO 6000 (96 GB), we trained lora_unified_pqc_v6 (r=16, alpha=16, dropout=0.05, lr=3e-5, 2 epochs, 32,768 sequence length, 37.9 GB peak VRAM) on dequantized bfloat16 QAT weights targeting only language_model linear projections (q/k/v/o/gate/up/down_proj, excluding vision/audio towers) while preserving Gemma-4's exact output logit softcapping: $$\text{logits}_{\text{capped}} = 30.0 \cdot \tanh!\left(\frac{\text{logits}}{30.0}\right)$$ Training converged smoothly (Epoch 1 loss: 0.9704 -> Epoch 2 loss: 0.7317). We then evaluated two submission variants on bench20: run_32A_lora_v6_all (adapter on all 4 agents) and run_32B_lora_v6_coder_qa (base E4B Planner + LoRA on Coder and QA).


Catastrophic Negative Result (0/20 Resolution): Both run_32A and run_32B collapsed from 6/20 (base E4B) to 0/20 resolved (0/20 submitted patches; localization dropped from 17/20 to 0/20 in 32A and 2/20 in 32B).


Forensic Root Cause (CoT Collapse): Comparing raw JSON trajectories on requests_7205 between base E4B and v6 LoRA exposed the exact mechanism:


* Base Gemma-4-E4B: Emits 330–497 tokens (15–25 seconds) of rich, first-person analytical reasoning inside <|channel>thought before every tool call (e.g., "Let's inspect how PreparedRequest handles body encoding when files and data coexist...").
* v6 LoRA (E4B): Because the SWE-bench training trajectories (deepseek_annotated_v4) lacked original native <|channel>thought traces, their reasoning channels had been populated post-hoc with concise 20–26 token third-person action summaries wrapped in role tags (<planner>...</planner>, <coder>...</coder>). Supervised fine-tuning on this distribution taught the model to emit a bare single-token tag ("thought": "<planner>" or "<coder>") and close the thought channel in 0.3 seconds! Deprived of test-time deliberation, the agent degenerated into blind, repetitive grep/read_file loops until exhausting all 58 tool calls without ever reaching QA Judge. Furthermore, trajectories split from monolithic runs lacked the /tmp/deha_isolated_tasks.json handoff convention, creating a protocol mismatch in 32A—though 32B proved that even when base Planner wrote valid handoff files, CoT Collapse inside Coder alone was fatal (0/20).


________________


3.4. Discovery 4: Natural Thinking Utilization & Context Compaction Dynamics
We instrumented vLLM (usage.reasoning_tokens) and the Gemma-4 tokenizer across 1,660 model invocations in run_30 and run_31 (BASE_HIGHTHINK_REPORT) to test whether raising thinking_budget from 4096 to 8192 (Planner/QA) and 12288 (Coder A/B) improves reasoning depth:


* Self-Regulating Deliberation on E4B: Despite an 8192–12288 ceiling, E4B's mean reasoning length remained remarkably compact and stable across roles: 378 tokens (Planner, max 4601), 367 tokens (Coder A, max 12286), 373 tokens (Coder B, max 12286), and 128 tokens (QA Judge, max 865). Only 3 out of 1,660 calls (0.18%) hit the 12288 ceiling, unlocking two previously unsolved rich tasks (rich_3882, rich_3506) with zero API length errors.
* Over-Thinking Latency Trap on 31B: Conversely, setting thinking_budget >= 12288 on Gemma-4-31B caused single turns to emit 7,000–8,000 reasoning tokens (3–4 minutes/turn on single L4), starving multi-iteration repair. Constraining 31B to 6144 (Fixer) / 3072 (QA Judge) provided the optimal latency-accuracy trade-off.
* Context Compaction Overflow & Restart Loops: Under EventsCompactionConfig(compaction_interval=15, overlap_size=2, token_threshold=14336, event_retention_size=5), our pre-model pruning callback capped maximum prompt size from 30,830 down to 16,120 tokens across 45 compaction events while dynamically clamping max_output_tokens = min(yaml_max, 32768 - input_tokens - 512). However, rich_3506 in run_36 exposed a subtle ADK failure mode: when an unpruned tool output burst pushed a summarization request to 70,100 tokens (> 32,768), LiteLLM silently retried ContextWindowExceededError behind suppressed debug banners (1819s stall), which we fixed by setting summarizer num_retries=1 and registering explicit litellm_errors callbacks (0 LiteLLM errors across the subsequent 14 tasks). Additionally, post-compaction memory loss caused 31B agents to re-run initial repository setup 2–7 times (CONTEXT_RESTART), which we mitigated via persistent /tmp/deha_a_started and /tmp/deha_b_started filesystem sentinel flags.


________________


4. Quantitative Results & Ablation Analysis
Table 1 summarizes end-to-end performance across our primary architectural milestones on the fixed 20-task bench20 suite.


Run ID
	Base Model
	Agent Topology & Key Configuration
	Budget (Time / Calls)
	File Loc.
	Resolved (bench20)
	run_21 / run_28A
	E4B-QAT
	4-Agent Sequential DAG (v5.8, think 4k)
	15m / 58
	14/20 (70%)
	6/20 (30.0%)
	run_30_highthink
	E4B-QAT
	4-Agent DAG (think 8k/12k, 45 turns, partial 15)
	15m / 45t
	13/15 (87%)
	6/15 (40.0%)
	run_31_feedback
	E4B-QAT
	4-Agent DAG (rm /tmp/deha_* fix, 72 turns)
	15m / 72t
	13/20 (65%)
	5/20 (25.0%)
	run_32A / 32B
	E4B + v6 LoRA
	Rank-16 QAT+Softcap LoRA (All / Coder+QA)
	15m / 58
	0–2/20 (10%)
	0/20 (0.0%)
	run_33_v6g
	E4B-QAT
	4-Agent DAG + False-Pass Repro Guard
	15m / 58
	17/20 (85%)
	5/20 (25.0%)
	E4B Union (18 runs)
	E4B-QAT
	Oracle union across all non-LoRA E4B configs
	—
	18/20 (90%)
	10/20 (50.0%)
	run_35_31b_single
	31B (GGUF+MTP)
	2-Stage Fixer -> QA Judge (Planner removed)
	15m / 58
	15/20 (75%)
	10/20 (50.0%)
	run_36_31b_parallel
	31B (GGUF+MTP)
	Loop(3)[Parallel(Fixer A ‖ B) -> QA] + Consensus
	30m / 110
	18/20 (90%)
	13/20 (65.0%)
	31B Union (35 ∪ 36)
	31B
	Combined single + parallel 31B solved set
	—
	19/20 (95%)
	14/20 (70.0%)
	4.1. Per-Task Progression and Branch Attribution (run_35 vs. run_36)
Table 2 details task-level outcomes in run_36_31b_parallel_30m alongside E4B baselines and run_35:


* Consistent Core Solves (9 tasks): rich_3454 (57 calls, 867s), requests_7309 (19 calls, 264s via CONSENSUS), requests_7205 (27 calls, 351s), requests_6644 (63 calls, 753s), fastapi_14301 (49 calls, 688s), rich_3518 (40 calls, 370s), rich_3882 (30 calls, 346s), fastapi_14356 (61 calls, 814s), and httpx_3672 (110 calls, 1018s via auto_recovery).
* 4 Net New Gains in run_36: fastapi_14616 (110 calls, 1416s, salvaged via auto_recovery), requests_7315 (24 calls, 336s, fixer_a clean submit), rich_3718 (43 calls, 706s, fixer_a after 1 QA iteration—never previously solved by any E4B or 31B run), and rich_3052 (109 calls, 1811s, 2 QA iterations + auto_recovery—also a first-time solve).
* The Fixer B Budget Paradox (0/13 Direct Wins): Across the 13 solved tasks in run_36, Fixer A (T=0.15) won 10 tasks via QA submission and auto_recovery (extracting Fixer A's /workspace diff) won 3 tasks, whereas Fixer B (T=0.45) won 0 tasks directly. Because Fixer B operated without built-in read_file/edit_file tools, its bash-based inspection consumed 40–55% of the shared 110-call budget. On 3 tasks (rich_3468, fastapi_13920, httpx_3672), parallel exploration consumed all 110/110 calls during Iteration 1, starving QA Judge completely (QA iters = 0).
* Single Regression (fastapi_14791) & QA Blind Spot: In run_35, single-agent 31B solved fastapi_14791 in 7 calls. In run_36, Fixer A over-engineered the patch in fastapi/openapi/utils.py (adding unrequested required: input and additionalProperties schema constraints), breaking 36 OpenAPI snapshot tests. QA Judge failed to catch this regression because /tmp/deha_qa2.py searched only for tests/test_<module>.py (test_utils.py was absent -> TESTS_NONE), submitting the over-scoped diff unverified.
* Root Causes of the 6 Remaining Unsolved Tasks: None failed due to syntax errors; all represent subtle semantic gaps—exact line placement (rich_3506), architectural layer mismatch (fastapi_14482 editing encoders.py instead of _compat/v2.py), helper function written but unwired to call site (fastapi_13920), exact exception string/decorator expectations in hidden tests (fastapi_14258, fastapi_14964), and incomplete BrokenPipeError stream handling (rich_3468).


________________


5. Discussion & Actionable Recommendations for Agent Designers
Our findings yield five concrete engineering principles for declarative open-weights coding agents:


1. Match Agent Topology to Model Scale: Small models (E4B) benefit from explicit Planner -> Coder -> QA role separation to achieve high localization (85%), whereas larger reasoning models (31B) suffer from Exploratory Budget Starvation in read-only roles and perform substantially better as unified Fixer agents backed by deterministic QA verification.
2. Gate Parallel Branches by Iteration (v3 Design): Unconditional ParallelAgent execution across all loop iterations wastes ~50% of shared tool calls when the conservative branch already dominates (10/13 vs. 0/13). Running a single /workspace Fixer in Iteration 1 and spawning a secondary hypothesis/consensus witness branch only when Iteration 1 triggers a legacy-test conflict preserves budget for QA Judge while retaining CONSENSUS benefits.
3. Never Fine-Tune Reasoning Models on Post-Hoc Action Summaries: Replacing native first-person <|channel>thought chains with short third-person rationales induces total CoT Collapse (0/20). SFT datasets for Gemma-4 agents must strictly preserve authentic, unedited first-person reasoning trajectories generated on the exact target handoff schema (via rejection sampling).
4. Design for Sandbox Semantics and Unsubmitted Recovery: Always verify how harness tools resolve paths (/workspace prefix stripping) before running concurrent agents, and ensure the primary agent mutates /workspace in-place so harness-level patch recovery acts as a zero-cost safety net under budget exhaustion.
5. Eliminate TESTS_NONE Verification Blind Spots: When direct tests/test_<module>.py lookup misses, QA scripts must fall back to git grep -l <modified_symbol_or_module> tests/ and enforce minimal-diff scope rules to prevent snapshot regressions like fastapi_14791.


________________


6. Conclusion
Through 36 systematic experiments on the swegemma ADK stack, we progressed from a 30.0% (6/20) Gemma-4-E4B baseline to a 65.0% (13/20) single-run and 70.0% (14/20) combined resolution rate with Gemma-4-31B—without relying on external proprietary models at inference time and while prototyping entirely within a single 24 GB L4 GPU via 3-bit GGUF + MTP speculative decoding. Equally important, our negative results—demonstrating Synthetic CoT Collapse under short-rationale LoRA (0/20), Exploratory Budget Starvation in 31B planners, and the 0/13 direct-win paradox of unthrottled parallel branches—provide reproducible, trace-verified guidance for building reliable open-weights software engineering agents.