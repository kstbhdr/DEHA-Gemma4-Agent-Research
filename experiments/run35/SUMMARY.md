# run_35_l4_31b_gguf bench20 — live summary

updated: 2026-11-11 13:09:37  |  **10/20 resolved**  |  20/20 tasks finished  |  dosya lokalizasyonu (gold kaynak dosyaya dokunan görev): 15/20  |  orchestrator uptime 7399s

model: gemma-4-31b-it-qat-w4a16-ct ← yerelde unsloth gemma-4-31B-it Q3_K_M GGUF — LoRA YOK (llama-server CUDA, -np 1 -c 32768, KV q4_0, flash-attn, MTP draft n_max=8, NVIDIA L4 24GB, 1 worker)
thinking_budget: fixer 4096 / qa_judge 2048 (max_output_tokens 16384/16384, temp 0.2/0.2/0.2/0.1); planner araçlarında edit_file/submit_patch YOK; bağlam koruması: EventsCompactionConfig(15/2/14336/5) + invocation-içi budama
submission: /content/work_l4_gguf/submission_swegemma_31b_single  |  eval_config: 58 tool calls / 72 turns / 15 min / cmd timeout 180s
streaming: her görev biter bitmez `results/<task_id>.json` + `task_logs/<task_id>.log` + bu tablo Drive'a yazılıp `os.sync()` çağrılır (resume: Drive'da sonucu olan görev atlanır)

| task | repo | diff | F2P | resolved | submitted | calls | turns | wall_s | src∩gold | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| fastapi_14616 | fastapi/fastapi | medium | 3 | no | False | 46 | 47 | 907.3 | 0/1 (yama boş) | Erken Submit :: empty patch (after protected-file strip) |
| rich_3506 | Textualize/rich | medium | 1 | no | False | 20 | 21 | 980.5 | 0/1 (yama boş) | Erken Submit :: empty patch (after protected-file strip) |
| httpx_3672 | encode/httpx | hard | 5 | YES | True | 41 | 45 | 805.0 | 3/7 | Çözüldü :: exit=0 required 5/5 passed; ['24 passed in 0.12s'] |
| fastapi_14964 | fastapi/fastapi | hard | 2 | no | True | 23 | 27 | 341.7 | 1/1 | Yanlış Mantık :: exit=1 required 2/2 passed; ['2 failed, 7 passed in 1.10s'] |
| requests_7205 | psf/requests | easy | 1 | YES | True | 15 | 19 | 229.9 | 1/1 | Çözüldü :: exit=0 required 1/1 passed; ['206 passed, 13 skipped in 0.31s'] |
| rich_3454 | Textualize/rich | easy | 1 | YES | False | 45 | 48 | 936.9 | 1/1 | Çözüldü :: exit=0 required 1/1 passed; ['83 passed in 0.20s'] |
| requests_6644 | psf/requests | easy | 1 | YES | True | 18 | 22 | 294.6 | 0/1 | Çözüldü :: exit=0 required 1/1 passed; ['1 passed in 0.01s'] |
| requests_7309 | psf/requests | medium | 5 | YES | False | 30 | 36 | 955.9 | 1/1 | Çözüldü :: exit=0 required 5/5 passed; ['207 passed, 13 skipped in 0.31s'] |
| requests_7315 | psf/requests | easy | 1 | no | True | 32 | 39 | 668.1 | 1/1 | Yanlış Mantık :: exit=1 required 0/1 passed; ['1 failed in 0.04s'] |
| rich_3468 | Textualize/rich | hard | 1 | no | True | 48 | 52 | 826.2 | 1/1 | Yanlış Mantık :: exit=1 required 0/1 passed; ['1 failed, 97 passed in 1.25s'] |
| rich_3718 | Textualize/rich | easy | 1 | no | False | 54 | 58 | 917.9 | 1/1 | Tur Limiti :: exit=1 required 1/1 passed; ['1 failed, 12 passed, 1 warning in 0.20s'] |
| rich_3052 | Textualize/rich | medium | 1 | no | False | 58 | 59 | 843.2 | 1/1 | Tur Limiti :: exit=1 required 0/1 passed; ['1 failed, 6 passed in 0.19s'] |
| fastapi_14356 | fastapi/fastapi | medium | 8 | YES | True | 36 | 40 | 571.0 | 1/1 | Çözüldü :: exit=0 required 8/8 passed; ['41 passed in 0.81s'] |
| fastapi_14791 | fastapi/fastapi | easy | 36 | YES | True | 7 | 11 | 180.8 | 1/1 | Çözüldü :: exit=0 required 36/36 passed; ['165 passed in 2.71s'] |
| fastapi_14482 | fastapi/fastapi | medium | 1 | no | False | 51 | 54 | 934.3 | 0/1 | Tur Limiti :: exit=1 required 0/1 passed; ['1 failed, 2 passed in 0.84s'] |
| fastapi_13920 | fastapi/fastapi | easy | 1 | no | False | 38 | 42 | 908.7 | 0/1 | Tur Limiti :: exit=1 required 0/1 passed; ['1 failed in 0.53s'] |
| fastapi_14258 | fastapi/fastapi | easy | 1 | no | True | 58 | 62 | 863.1 | 1/1 | Yanlış Mantık :: exit=1 required 0/1 passed; ['1 failed in 0.45s'] |
| fastapi_14301 | fastapi/fastapi | easy | 2 | YES | True | 41 | 45 | 528.2 | 1/1 | Çözüldü :: exit=0 required 2/2 passed; ['11 passed in 0.65s'] |
| rich_3518 | Textualize/rich | easy | 1 | YES | True | 50 | 55 | 496.9 | 1/1 | Çözüldü :: exit=0 required 1/1 passed; ['20 passed in 0.26s'] |
| rich_3882 | Textualize/rich | easy | 1 | YES | True | 16 | 20 | 178.0 | 1/1 | Çözüldü :: exit=0 required 1/1 passed; ['8 passed in 0.19s'] |

## Hata Taksonomisi

Çözüldü: 10  |  Erken Submit: 2  |  Yanlış Mantık: 4  |  Tur Limiti: 4

`src∩gold` = ajanın değiştirdiği (test/korunaklı olmayan) kaynak dosyalar ∩ gold patch'in kaynak dosyaları. `Yanlış Dosya` kovası yalnızca bu iki küme **hiç** kesişmediğinde dolar; yaması strip'ten sonra boşalan görev `Erken Submit` sayılır, bu yüzden lokalizasyon bu sütundan okunur.

# run_35_l4_31b_gguf — 31B (3-bit GGUF) + v6g mimarisi, tek L4, CONCURRENCY=1
1. Sunucu: llama.cpp (f3b407c, CUDA sm_89, kaynaktan derlendi) `llama-server -m gemma-4-31B-it-Q3_K_M.gguf (unsloth, 14.7 GB) -ngl 99 -fa on -ctk q4_0 -ctv q4_0 -np 1 -c 32768 --jinja --reasoning-format deepseek`.
2. Speculative karşılaştırma (aynı tool-call isteği / 600 tokenlık serbest üretim): draft yok 14.9 / 14.8 tok/s; E2B Q4_K_M draft (`--spec-type draft-simple`) 37.0 / 22.4 tok/s, 17.4 GB VRAM; **MTP draft** (bartowski `mtp-google_gemma-4-31B-it-Q4_0.gguf`, `--spec-type draft-mtp`) n_max 4: 45.6/36.4, 6: 54.3/37.8, **8: 56.0/39.1 tok/s, 16.5 GB VRAM** → kilitlendi. Not: `-md` tek başına draft'ı yüklüyor ama kullanmıyor; `--spec-type` şart. Tüm modlarda tool_calls JSON 100% doğru.
3. Prefill: 11.9K token prompt 578 tok/s (~20 s).
4. Harness uyarlaması: `DEHA_BACKEND=llamacpp` → istek başına `thinking_budget_tokens` (llama-server alanı; vLLM'deki `thinking_token_budget` yerine). Proxy ile doğrulandı: thinking_budget_tokens=12288, max_completion_tokens=16384, enable_thinking=true; bütçe 64 ile reasoning ~175 karakterde kesildi. reasoning_content → ADK thought parçası olarak geliyor. Bağlam koruması (14336 sıkıştırma, 32768-girdi-512 dinamik tavan) aynen aktif.
5. Paket `submission_swegemma_31b_single` (v6g tabanlı): model `gemma-4-31b-it-qat-w4a16-ct` (README registry alias), thinking 8192/12288/12288/6144, max_output 16384; adapter yok; validate_submission 0 hata. Hızlandırma: QA ve coder kontrol betikleri ilk kullanımda `/tmp/deha_qa_check.py` / `/tmp/deha_check.py` olarak kendini kaydeder, sonraki turlarda tek satırlık `test -f ... && python3 ...` (bozuk/eksikse tam betiğe geri döner); QA VERDICT: SUBMIT sonrası ilk araç çağrısı submit_patch; planner repro en fazla 2 koşu.
6. (a) İlk deneme durduruldu (`results_aborted_a_planner_overexplore/`): fastapi_14616'da 31B planner STEP 0'ı atladı ve 58 araç çağrısının **tamamını** keşifle (python3 -c pydantic deneyleri, aynı dosyaları tekrar okuma) harcadı; görev listesi hiç yazılmadı. Doğru yeri (getlist / is_sequence_field) bulmuştu. Ölçümler: üretim ~23.5K token / 15 dk, MTP kabul oranı ~%45 (ortalama 4.6 token), VRAM tepe 16.47 GB. → planner'a "en fazla 12 araç çağrısı, 10. çağrıda görev listesini yaz, kütüphane iç deneyleri yok", coder A/B'ye 14/12 çağrı sınırı eklendi.
7. (b) İkinci deneme durduruldu (`results_aborted_b_planner_budget_ignored/`): prompt'taki "en fazla 12 çağrı" kuralına rağmen planner fastapi_14616'da yine 58/58, rich_3506'da 30/30 çağrının tamamını keşifle harcadı (görev listesi yok, boş yama). 31B'de bir araç çağrısı ~20-30 s sürüyor → görev başına ~30-45 çağrı sığıyor; 4 ajanlı "planla-devret" yapısı bu bütçeye sığmıyor.
8. (c) Yapı değişikliği: **fixer → QA judge** (LoopAgent max_iterations=3, sıralı, paralel ajan yok). Fixer hatayı bulur VE düzeltir (planner'ın konumlandırma kuralları + coder'ın cerrahi edit protokolü + hızlı kontrol betiği); "8. çağrıda ilk edit_file" kuralı; repro adımı yok (zaman). QA aynı (kendini kuran /tmp/deha_qa_check.py, SUBMIT → hemen submit_patch). Thinking: fixer 12288, qa 6144; max_output 16384. validate_submission 0 hata.
9. (c) fixer→QA ilk deneme (thinking 12288/6144, `results_aborted_c_fixer_think12k/`): **rich_3506 çözüldü** (E4B 7 koşuda 1 kez), fastapi_14616 yine zaman aşımı (ilk edit 42. çağrıda). Ama çağrı başına ortalama ~60 s: tek tek çağrılarda 7224 / 8467 / 6695 tokenlık thinking (her biri ~3-4 dk). rich_3506'da QA'ya hiç sıra gelmedi (diff submit edilmeden değerlendirildi).
10. (d) Thinking bütçesi fixer 4096 / qa 2048'e indirildi (12288 thinking ~39 tok/s'de tek çağrıda 5 dk demek; 15 dk sınırına sığmıyor). Koşu temiz başlatıldı.

11. 11:06 — Queue reordered: E4B-never-solved tasks first (rich_3468, rich_3718, rich_3052, fastapi_14356, fastapi_14791, fastapi_14482, fastapi_13920, fastapi_14258), then fastapi_14301, rich_3518, rich_3882. Orchestrator restarted with resume (9 done results skipped); fastapi_14301 was interrupted seconds after start and will rerun at the end. Part-1 log: logs/orch_run35_part1.log (local).
