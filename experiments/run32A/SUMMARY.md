# run_32A_lora_v6_all bench20 — live summary

updated: 2026-11-10 22:43:22  |  **0/20 resolved**  |  20/20 tasks finished  |  dosya lokalizasyonu (gold kaynak dosyaya dokunan görev): 0/20  |  orchestrator uptime 932s

model: google/gemma-4-E4B-it-qat-w4a16-ct — LoRA: planner/coder/QA for A, coder/QA for B (vLLM 0.33.0, CUDA graphs + prefix caching + chunked prefill, gpu_mem_util 0.88, max_model_len 32768, NVIDIA RTX PRO 6000 96GB, 4 paralel worker)
thinking_budget: planner 8192 / coder_a 12288 / coder_b 12288 / qa_judge 8192 (max_output_tokens 16384/20480/20480/16384, temp 0.2/0.2/0.2/0.1); planner araçlarında edit_file/submit_patch YOK; bağlam koruması: EventsCompactionConfig(15/2/14336/5) + invocation-içi budama
submission: /content/work_v6_g4/submission_v16A_lora_v6_dag  |  eval_config: 58 tool calls / 72 turns / 15 min / cmd timeout 180s
streaming: her görev biter bitmez `results/<task_id>.json` + `task_logs/<task_id>.log` + bu tablo Drive'a yazılıp `os.sync()` çağrılır (resume: Drive'da sonucu olan görev atlanır)

| task | repo | diff | F2P | resolved | submitted | calls | turns | wall_s | src∩gold | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| requests_7205 | psf/requests | easy | 1 | no | False | 58 | 61 | 196.5 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| requests_6644 | psf/requests | easy | 1 | no | False | 58 | 61 | 185.1 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| requests_7309 | psf/requests | medium | 5 | no | False | 58 | 59 | 43.4 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| requests_7315 | psf/requests | easy | 1 | no | False | 58 | 59 | 36.2 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| fastapi_14301 | fastapi/fastapi | easy | 2 | no | False | 58 | 60 | 202.8 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| fastapi_14616 | fastapi/fastapi | medium | 3 | no | False | 58 | 60 | 188.9 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| rich_3454 | Textualize/rich | easy | 1 | no | False | 58 | 60 | 191.7 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| rich_3518 | Textualize/rich | easy | 1 | no | False | 58 | 61 | 186.9 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| fastapi_14964 | fastapi/fastapi | hard | 2 | no | False | 58 | 61 | 194.1 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| rich_3468 | Textualize/rich | hard | 1 | no | False | 58 | 59 | 35.9 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| rich_3506 | Textualize/rich | medium | 1 | no | False | 58 | 59 | 37.9 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| rich_3718 | Textualize/rich | easy | 1 | no | False | 58 | 61 | 221.5 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| rich_3882 | Textualize/rich | easy | 1 | no | False | 58 | 60 | 207.0 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| rich_3052 | Textualize/rich | medium | 1 | no | False | 58 | 61 | 192.2 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| fastapi_14356 | fastapi/fastapi | medium | 8 | no | False | 58 | 60 | 197.7 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| fastapi_14791 | fastapi/fastapi | easy | 36 | no | False | 58 | 60 | 194.7 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| fastapi_14482 | fastapi/fastapi | medium | 1 | no | False | 58 | 61 | 192.5 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| fastapi_13920 | fastapi/fastapi | easy | 1 | no | False | 58 | 59 | 133.1 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| fastapi_14258 | fastapi/fastapi | easy | 1 | no | False | 58 | 59 | 43.4 | 0/1 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |
| httpx_3672 | encode/httpx | hard | 5 | no | False | 58 | 61 | 186.6 | 0/7 (yama boş) | Tur Limiti :: empty patch (after protected-file strip) |

## Hata Taksonomisi

Tur Limiti: 20

`src∩gold` = ajanın değiştirdiği (test/korunaklı olmayan) kaynak dosyalar ∩ gold patch'in kaynak dosyaları. `Yanlış Dosya` kovası yalnızca bu iki küme **hiç** kesişmediğinde dolar; yaması submit edilmiş fakat strip sonrası boş kalan yama `Erken Submit` sayılır; gönderilmeyen yamalar ayrı gösterilir.

