Multi-Agent Topologies, Chain-of-Thought Collapse, and Budget-Aware Orchestration for Gemma-4 Agents
Empirical Lessons from 36 Declarative ADK Evaluations Across 4B and 31B Open-Weights Coding Models
Author: Bahadır Kuşat (DEHA AI Research)
Competition Track: Gemma-4 Developer Agent — Paper Track (November 2026)


________________


Abstract
Deploying open-weights Large Language Models (LLMs) as software engineering (SWE) agents within sandboxed declarative frameworks exposes critical trade-offs among model scale, multi-agent topology, operational budgets, and fine-tuning alignment. We present an empirical study across 36 configurations evaluated on a stratified 20-task Python benchmark (bench20: requests, fastapi, rich, httpx) under the official swegemma / Google Agent Development Kit (ADK) stack targeting Gemma-4-E4B and Gemma-4-31B.


Our investigation yields four principal findings:


1. Scale-Dependent Topology Inversion: A 4-stage sequential Directed Acyclic Graph (Planner -> Coder A -> Coder B -> QA Judge) achieves up to 85% (17/20) source-file localization and 30% (6/20) single-run resolution on Gemma-4-E4B. Transferring this identical read-only Planner topology to Gemma-4-31B induces Exploratory Budget Starvation, where the larger model ignores prompt turn caps and exhausts the shared tool budget on exploration. Removing the standalone planner in favor of an execution-first Fixer -> QA Judge loop immediately reaches 50% (10/20) resolution under the same 15-minute, 58-call budget.
2. Budget-Expanded Asymmetric Parallelism and Consensus Verification: Expanding per-task limits to 30 minutes and 110 calls with an asymmetric parallel loop (LoopAgent wrapping ParallelAgent(Fixer A, Fixer B) -> QA Judge) raises local single-run resolution to 65% (13/20) (70% two-run union). Branch attribution reveals stark cost-benefit asymmetry: the conservative /workspace branch (Fixer A, $T=0.15$) accounts for 10/13 resolutions and harness-level Automatic Unsubmitted Patch Recovery accounts for 3/13, whereas the exploratory branch (Fixer B, $T=0.45$) wins 0/13 patches directly while consuming 40–55% of the shared tool budget. However, Fixer B provides a targeted Consensus Witness signal: in a preliminary case study (requests_7309), detecting identical pre-existing test failures across both branches identified a legacy test pinning buggy behavior, cutting resolution time by 3.6×.
3. Post-Hoc Rationale SFT and Chain-of-Thought (CoT) Collapse: Supervised fine-tuning (SFT) of Gemma-4-E4B (rank-16 LoRA on dequantized QAT weights with logit softcapping) on 528 audited trajectories annotated with concise (20–26 token) third-person role summaries (<planner>, <coder>, <qualityanalyst>) reduces resolution from 30% to 0% (0/20). Trace inspection strongly supports the hypothesis that post-hoc summary tags overwrite native first-person <|channel>thought deliberation (mean 367–378 tokens/turn), causing 0.3-second premature thought termination and unguided tool looping.
4. Hardware-Frugal Local Prototyping: Serving 3-bit GGUF (Q3_K_M) Gemma-4-31B with 4-bit KV-caches and Multi-Token Prediction (draft-mtp) fits two concurrent 32k-context slots into 18.0 GB VRAM on a single 24 GB NVIDIA L4 GPU at 58–77 tok/s, enabling low-cost iteration prior to official 4×L4 W4A16 vLLM evaluation.


________________


1. Introduction
Repository-level issue resolution requires an LLM agent to localize defects across large codebases, formulate a root-cause hypothesis, synthesize a minimal patch, run regression tests, and submit a unified diff under strict wall-clock, context, and tool-call budgets. Unlike unconstrained Python scaffolds where orchestration is coded imperatively on the host, the Gemma-4 Developer Agent competition enforces a declarative security boundary via adk-submission. Submissions consist strictly of YAML agent definitions (LlmAgent, SequentialAgent, ParallelAgent, LoopAgent), markdown prompts, optional eval_config.yaml budget overrides, and optional LoRA weights, compiled into Google ADK trees with dynamic Python imports disabled.


Within these constraints, we investigate four research questions across Gemma-4-E4B and Gemma-4-31B:


* RQ1 (Scale vs. Topology): Does decomposing localization, editing, and verification across specialized sub-agents transfer monotonically from a 4B model to a 31B model?
* RQ2 (Parallelism under Shared Budgets): When running concurrent patch generators inside a single container (/workspace) with a shared tool-call counter, how do branch diversity, sandbox path rules, and unsubmitted patch recovery interact?
* RQ3 (Reasoning Alignment under LoRA SFT): How does fine-tuning Gemma-4-E4B on verified SWE trajectories with concise third-person role rationales affect its native test-time reasoning channel?
* RQ4 (Deliberation Length and Context Compaction): How much thinking_budget do Gemma-4 agents naturally consume per turn, and what failure modes arise during long-horizon history compaction?


________________


2. Related Work
Coding Scaffolds and SWE Benchmarks. SWE-bench (Jimenez et al., 2024) established hermetic repository-level evaluation via Fail-to-Pass (F2P) and Pass-to-Pass (P2P) test suites. Imperative scaffolds such as SWE-agent (Yang et al., 2024) and OpenHands (Wang et al., 2024) showed that structured file viewing and surgical editing tools strongly govern agent accuracy, whereas Agentless (Xia et al., 2024) demonstrated that fixed hierarchical pipelines (localization followed by repair and test filtering) can rival autonomous loops. Our work evaluates this staged-versus-unified trade-off inside a purely declarative ADK graph across open-weights model scales.


Multi-Agent Scaling Limits and Failure Taxonomies. Recent large-scale studies challenge the assumption that adding agents monotonically improves performance. Cemri et al. (2025) analyzed over 1,600 multi-agent traces (MAST), showing that system-design specification flaws, inter-agent misalignment, and incomplete verification dominate failures rather than raw model reasoning deficits. Crucially, Gao et al. (2025) demonstrated that Multi-Agent Systems (MAS) lose their accuracy advantage over Single-Agent Systems (SAS) as base LLM capability grows, while incurring severe efficiency overhead. Most recently, Kim et al. (2025) established quantitative agent-scaling laws across 260 compute-matched configurations, identifying a capability saturation threshold (beyond ~45% single-agent accuracy, multi-agent coordination often yields diminishing or negative returns) and a tool-coordination trade-off where tool-heavy sequential tasks suffer disproportionately under fixed budgets. Our empirical findings extend Kim et al. (2025) and Gao et al. (2025) to declarative coding DAGs, revealing Exploratory Budget Starvation on 31B planners and severe tool-budget contention in parallel branches.


Test-Time Deliberation and Distillation. Scaling internal chain-of-thought compute (DeepSeek-AI, 2025; Muennighoff et al., 2025) and multi-sample voting (Zhang et al., 2024) improves code repair when sample budgets are independent. While distilling full first-person reasoning chains enhances small models (DeepSeek-AI, 2025), our negative LoRA experiments show that substituting concise post-hoc role summaries collapses native test-time deliberation.


________________


3. Experimental Setup and Methodology
3.1. Evaluation Stack and Benchmark (bench20)
All experiments use the official three-layer harness: adk-submission (YAML schema and validate_single_declared_model), adk-eval-core (budget gates and token accounting), and swegemma (two-container evaluation). In Phase 1, the agent modifies Container A (/workspace) via bound tools (read_file, edit_file, run_command, get_status, search_similar_code, get_code_neighbors, find_files, submit_patch). In Phase 2, the unified diff is tested in a clean Container B against held-out F2P and P2P pytest suites.


For deterministic cross-run comparison with zero training overlap, we fixed a stratified 20-task benchmark (bench20, 1–36 F2P tests/task) across four Python libraries: requests (6644, 7205, 7309, 7315), fastapi (13920, 14258, 14301, 14356, 14482, 14616, 14791, 14964), rich (3052, 3454, 3468, 3506, 3518, 3718, 3882), and httpx (3672).
3.2. Local Prototyping vs. Official 4×L4 Target
The official Kaggle environment runs vLLM (tensor_parallel_size=4, max_model_len=32768) on 4× NVIDIA L4 GPUs (96 GB VRAM) with Compressed-Tensors W4A16 QAT weights (gemma-4-31b-it-qat-w4a16-ct and gemma-4-e4b-it-qat-w4a16-ct). While E4B ablations ran directly on vLLM with W4A16 weights, standard 4-bit 31B serving exceeds a single 24 GB L4 (~22.5 GiB usable) once two 32k KV-caches are allocated.


To prototype 31B topologies frugally on one 24 GB L4, we served 3-bit Gemma-4-31B (unsloth Q3_K_M, 14.7 GB) via llama-server with a Multi-Token Prediction drafter (Q4_0, draft-mtp), 4-bit KV-caches (q4_0), and two concurrent 32,768-token slots. Memory stabilized at 18.0 GB peak VRAM (0 OOMs), lifting single-slot decode speed from 14.8 to 56.0 tok/s and dual-slot throughput to 58–77 tok/s (45% draft acceptance). All submitted ZIP archives use official W4A16 model IDs and pass validate_submission with zero errors.


________________


4. Empirical Findings and Architectural Analysis
4.1. Scale-Dependent Topology Inversion (E4B vs. 31B)
On Gemma-4-E4B, monolithic single-agent prompts frequently triggered premature submissions or edit syntax errors. Decomposing roles into a 4-agent sequential DAG (Planner -> Coder A -> Coder B -> QA Judge) markedly improved discipline: read-only planning achieved 70% (14/20) file localization in run_21 and 85% (17/20) in run_33_v6g (with false-pass reproduction guards). Single-run E4B resolution reached 30% (6/20) (run_21, run_28A), while the oracle union across 18 non-LoRA E4B runs hit 50% (10/20), confirming strong latent capability sensitive to inter-agent handoff fidelity.


Exploratory Budget Starvation on 31B. Porting this identical 4-agent DAG to Gemma-4-31B caused severe degradation. Consistent with the tool-coordination trade-off described by Kim et al. (2025), 31B ignored prompt instructions ordering Planner to stop within 12 calls, chasing transitive call chains until exhausting all 58/58 tool calls in read-only mode before Coder could execute a single edit. Similar prompt-cap violations recurred in later runs (rich_3468 used 63 and 48 calls in single branches despite 20–25 call instructions). Enforcing budget allocation structurally—by removing Planner and running a 2-stage Fixer -> QA Judge loop (run_35, 15m / 58 calls)—immediately lifted resolution to 50% (10/20), solving httpx_3672 (5 F2P) and fastapi_14791 (36 F2P in 7 calls).


________________


4.2. Asymmetric Parallelism, Sandbox Rules, and Consensus Case Study
In run_35, 6 unsolved tasks hit the 15m / 58-call ceiling mid-repair, while 4 tasks localized the exact gold file (1/1) but missed an edge case. In submission_swegemma_31b_parallel_v2 (run_36), we expanded eval_config.yaml to max_time_minutes: 30 and max_tool_calls: 110 over a 3-iteration graph: $$\text{LoopAgent}(N=3) \longrightarrow \text{SequentialAgent}\big[\text{ParallelAgent}(\text{Fixer}_A \parallel \text{Fixer}_B),\ \text{QA_Judge}\big]$$


Three systems insights emerged under single-container execution:


1. Sandbox Path-Stripping Isolation: Under swegemma §6.2, read_file and edit_file strip leading / characters and resolve paths inside /workspace, causing edit_file("/tmp/wt_b/x.py") to overwrite Fixer A's workspace. Removing both tools from Fixer B ($T=0.45$) and restricting it to run_command inside a shared clone (git clone --shared /workspace /tmp/wt_b) eliminated workspace races.
2. In-Place Anchor for Patch Recovery: Under swegemma §8.1, budget exhaustion prior to submit_patch() scores git diff in /workspace. Anchoring conservative Fixer A ($T=0.15$) directly in /workspace guaranteed a valid fallback diff, salvaging 3/13 (23%) of solved tasks in run_36 (fastapi_14616, rich_3052, httpx_3672).
3. Preliminary CONSENSUS Legacy-Test Mechanism: Bug fixes occasionally invalidate legacy tests that assert old defective behavior. Our deterministic QA script implements a CONSENSUS heuristic: if both independent branches pass syntax checks and fail the exact same pre-existing test(s), QA treats those tests as legacy bug assertions and submits Fixer A. While observed on a single task in bench20 (requests_7309, preventing broad statistical generalization), this mechanism resolved a recurring rejection loop and cut task time from 955.9s (unsubmitted) to 263.6s (19 calls, submitted) (3.6× faster).


________________


4.3. Post-Hoc Rationale SFT and Chain-of-Thought Collapse
To improve Gemma-4-E4B without ensembles, we built a 528-example multi-turn SFT dataset (v6_clean: 408 role-segmented SWE trajectories + 120 Python bug-fix pairs, disjoint from bench20, with malformed turns removed and bookkeeping commands loss-masked). On an RTX PRO 6000 (96 GB), we trained a rank-16 LoRA (alpha=16, lr=3e-5, 2 epochs, 32k context) on dequantized bfloat16 E4B-QAT language_model projections with Gemma-4 logit softcapping ($30.0 \cdot \tanh(z / 30.0)$). Loss converged smoothly (0.970 -> 0.732). Both run_32A (LoRA on all 4 agents) and run_32B (base E4B Planner + LoRA on Coder/QA) collapsed from 30% (6/20) to 0% (0/20) resolved.


Mechanistic Hypothesis (CoT Collapse). Although SFT introduces multiple potential confounders (including missing JSON handoff artifacts in 32A), 32B isolates failure to the LoRA-adapted Coder after receiving valid plans from the unmodified base Planner. Whereas base E4B-QAT emits 330–497 tokens (15–25s) of first-person <|channel>thought reasoning per turn, our training trajectories had been annotated post-hoc with 20–26 token third-person summaries (<coder>...</coder>). At inference, the adapted model emitted a bare tag ("thought": "<coder>") in 0.3 seconds and looped blindly over grep/read_file until exhausting all 58 calls—strongly suggesting that short post-hoc rationales condition Gemma-4 to bypass test-time deliberation.


________________


4.4. Deliberation Token Utilization and Context Compaction
Across 1,660 vLLM calls (run_30–run_31) with 8192/12288 thinking_budget caps, base E4B-QAT naturally self-regulated deliberation: mean thought length was 378 tokens (Planner), 367–373 tokens (Coders), and 128 tokens (QA), hitting the 12,288 ceiling in just 0.18% (3/1660) of calls while unlocking rich_3882 and rich_3506. Conversely, 31B at thinking_budget >= 12288 often generated 7,000–8,000 thought tokens/turn; capping 31B at 6144 (Fixer) / 3072 (QA) prevented turn starvation. Under EventsCompactionConfig (14,336-token threshold), persistent sentinel flags (/tmp/deha_a_started, /tmp/deha_b_started) eliminated post-compaction setup restarts, while bounding summarizer retries prevented silent >32k context overflow stalls.


________________


5. Quantitative Results and Ablation Discussion
Table 1 summarizes milestone performance on bench20.


Run / Configuration
	Model & Backend
	Agent Topology
	Budget (Time / Calls)
	File Loc.
	Resolved (bench20)
	run_21 / run_28A
	E4B-QAT (vLLM)
	4-Agent Sequential DAG (think 4k)
	15m / 58
	14/20 (70%)
	6/20 (30%)
	run_30_highthink*
	E4B-QAT (vLLM)
	4-Agent DAG (think 8k/12k, 45t)
	15m / 45t
	13/15 (87%)
	6/15 (40%)
	run_32A / 32B
	E4B + LoRA (vLLM)
	4-Agent DAG (All / Coder+QA LoRA)
	15m / 58
	0–2/20 (0–10%)
	0/20 (0%)
	run_33_v6g
	E4B-QAT (vLLM)
	4-Agent DAG + Repro Guard
	15m / 58
	17/20 (85%)
	5/20 (25%)
	E4B Oracle Union
	E4B-QAT (vLLM)
	Union across 18 non-LoRA E4B runs
	—
	18/20 (90%)
	10/20 (50%)
	run_35_31b_single
	31B (GGUF+MTP)
	2-Stage Fixer -> QA (No Planner)
	15m / 58
	15/20 (75%)
	10/20 (50%)
	run_36_31b_par
	31B (GGUF+MTP)
	Loop(3)[Fixer A ‖ B -> QA] + Consensus
	30m / 110
	18/20 (90%)
	13/20 (65%)
	31B Union (35∪36)
	31B (GGUF+MTP)
	Combined single + parallel 31B set
	—
	19/20 (95%)
	14/20 (70%)
	

*Note: run_30 terminated after 15 tasks due to turn-limit reconfiguration.
Disentangling Budget Expansion from Parallel Branching (Fixer B Paradox)
Comparing run_35 (10/20) and run_36 (13/20) requires caution because topology and budget (58 vs. 110 calls; 15m vs. 30m) changed jointly. run_36 added four new solves (fastapi_14616, requests_7315, rich_3718, rich_3052) and one regression (fastapi_14791, where unrequested schema edits missed snapshot tests due to exact-filename test lookup).


Crucially, Fixer A ($T=0.15$) won 10/13 tasks via QA submission and auto_recovery (Fixer A's /workspace diff) won 3/13, whereas Fixer B ($T=0.45$) won 0/13 tasks directly while consuming 40–55% of the shared 110-call budget via bash-only inspection—starving QA Judge completely on 3 tasks (rich_3468, fastapi_13920, httpx_3672). Thus, the 50% $\rightarrow$ 65% gain stemmed primarily from expanded iteration headroom, /workspace auto-recovery, and CONSENSUS verification, not direct patch selection from Fixer B. Gating secondary branches to spawn only upon a legacy-test conflict offers superior budget efficiency.


________________


6. Limitations and Reproducibility
1. Confounded Budget Shift & Single-Case Consensus: Without an intermediate 110-call single-fixer 31B ablation, we cannot isolate Fixer B's exact opportunity cost, and our CONSENSUS speedup was triggered on a single bench20 task (requests_7309).
2. Benchmark Size & Quantization Gap: Iterating across 36 runs on bench20 carries architectural overfitting risk, and local 31B runs used 3-bit Q3_K_M GGUF (llama.cpp) rather than official 4×L4 W4A16 (vLLM, Kaggle submission ref 58250635 pending final scoring).
3. Non-Isolated SFT Variables: Definitive proof of CoT Collapse requires controlled SFT ablations varying solely rationale length (25 vs. 400 tokens) on identical DAG handoffs.


Reproducibility & Artifacts: Declarative YAML configurations (agent.yaml, eval_config.yaml, sub-agent prompts), bench20 task IDs, SFT auditing scripts, and JSON execution traces (run_21–run_36) are attached via our official Kaggle competition submission (ref 58250635) and companion artifact archive: https://github.com/kstbhdr/DEHA-Gemma4-Agent-Research.


________________


7. Conclusion
Across 36 evaluations on the declarative swegemma / Google ADK stack, we showed that open-weights SWE agent design is governed by scale-specific dynamics: Gemma-4-E4B benefits from 4-stage Planner -> Coder -> QA decomposition (85% localization, 30% single-run / 50% union resolution) yet collapses (0%) under short post-hoc rationale SFT. Conversely, Gemma-4-31B suffers Exploratory Budget Starvation with standalone planners, but achieves 65% (13/20) local single-run resolution (70% union) as an in-place Fixer paired with /workspace patch recovery and consensus verification.


________________


References
1. Cemri, M., Pan, M. Z., Yang, S., Agrawal, L. A., Chopra, B., Tiwari, R., Keutzer, K., Parameswaran, A., Klein, D., & Ramchandran, K. (2025). Why Do Multi-Agent LLM Systems Fail? In Advances in NeurIPS 2025 (arXiv:2503.13657).
2. DeepSeek-AI. (2025). DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning. arXiv:2501.12948.
3. Gao, M., Li, Y., Liu, B., Yu, Y., Wang, P., Lin, C.-Y., & Lai, F. (2025). Single-Agent or Multi-Agent Systems? Why Not Both? arXiv:2505.18286.
4. Google DeepMind. (2026). Gemma 4 Technical Report & Quantization-Aware Training Model Card. Hugging Face / Kaggle Models.
5. Jimenez, C. E., Yang, J., Wettig, A., Yao, S., Pei, K., Press, O., & Narasimhan, K. (2024). SWE-bench: Can Language Models Resolve Real-World GitHub Issues? In Proceedings of ICLR 2024.
6. Kim, Y., Gu, K., Park, C., Park, C., Schmidgall, S., Heydari, A. A., Yan, Y., Zhang, Z., Zhuang, Y., Liang, P. P., et al. (2025). Towards a Science of Scaling Agent Systems. arXiv:2512.08296.
7. Muennighoff, N., Yang, Z., Shi, W., Li, X. L., Fei-Fei, L., Hajishirzi, H., Zettlemoyer, L., Liang, P., Candès, E., & Hashimoto, T. (2025). s1: Simple Test-Time Scaling. arXiv:2501.19393.
8. Wang, X., Li, B., Song, Y., Xu, F. F., Tang, X., Zhuge, M., Pan, J., et al. (2024). OpenHands: An Open Platform for AI Software Developers as Generalist Agents. arXiv:2407.16741.
9. Xia, C. S., Deng, Y., Dunn, S., & Zhang, L. (2024). Agentless: Demystifying LLM-based Software Engineering Agents. arXiv:2407.01489.
10. Yang, J., Jimenez, C. E., Wettig, A., Lieret, K., Yao, S., Narasimhan, K., & Press, O. (2024). SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering. In Advances in NeurIPS 2024.
11. Zhang, K., Li, J., Li, G., Shi, X., & Jin, Z. (2024). CodeAgent: Enhancing Code Generation with Tool-Integrated Agent Systems for Real-World Repo-Level Coding Challenges. In Proceedings of ACL 2024.