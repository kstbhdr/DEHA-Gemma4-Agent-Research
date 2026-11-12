# run_21_bench20_v5_8 bench20 — live summary

updated: 2026-11-07 22:47:52  |  **6/20 resolved**  |  20/20 tasks finished  |  dosya lokalizasyonu (gold kaynak dosyaya dokunan görev): 17/20  |  orchestrator uptime 4885s

model: google/gemma-4-E4B-it-qat-w4a16-ct (vLLM 0.33.0, CUDA graphs + prefix caching + chunked prefill, gpu_mem_util 0.90, max_model_len 32768)
submission: /content/submission_swegemma_v5_8_compile_gate  |  eval_config: 58 tool calls / 45 turns / 15 min / cmd timeout 180s
streaming: her görev biter bitmez `results/<task_id>.json` + `task_logs/<task_id>.log` + bu tablo Drive'a yazılıp `os.sync()` çağrılır (resume: Drive'da sonucu olan görev atlanır)

| task | repo | diff | F2P | resolved | submitted | calls | turns | wall_s | src∩gold | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| requests_7205 | psf/requests | easy | 1 | YES | True | 12 | 14 | 124.2 | 1/1 | Çözüldü :: exit=0 required 1/1 passed; ['206 passed, 13 skipped in 0.30s'] |
| fastapi_14964 | fastapi/fastapi | hard | 2 | no | True | 31 | 40 | 398.2 | 1/1 | Yanlış Mantık :: exit=1 required 0/2 passed; ['7 failed, 2 passed in 1.59s'] |
| rich_3468 | Textualize/rich | hard | 1 | no | False | 38 | 45 | 482.4 | 1/1 | Tur Limiti :: exit=1 required 0/1 passed; ['1 failed, 97 passed in 1.19s'] |
| rich_3882 | Textualize/rich | easy | 1 | no | True | 13 | 15 | 213.4 | 1/1 | Yanlış Mantık :: exit=1 required 0/1 passed; ['7 failed, 1 passed in 0.25s'] |
| rich_3454 | Textualize/rich | easy | 1 | YES | True | 5 | 8 | 123.2 | 1/1 | Çözüldü :: exit=0 required 1/1 passed; ['83 passed in 0.20s'] |
| rich_3518 | Textualize/rich | easy | 1 | no | False | 38 | 45 | 487.7 | 1/1 | Tur Limiti :: exit=1 required 0/1 passed; ['2 failed, 18 passed in 0.28s'] |
| requests_6644 | psf/requests | easy | 1 | no | True | 13 | 15 | 172.7 | 0/1 | Yanlış Dosya :: exit=1 required 0/1 passed; ['1 failed in 0.04s'] |
| requests_7309 | psf/requests | medium | 5 | YES | True | 6 | 8 | 64.5 | 1/1 | Çözüldü :: exit=0 required 5/5 passed; ['207 passed, 13 skipped in 0.30s'] |
| requests_7315 | psf/requests | easy | 1 | YES | True | 20 | 29 | 238.9 | 1/1 | Çözüldü :: exit=0 required 1/1 passed; ['1 passed in 0.02s'] |
| fastapi_14301 | fastapi/fastapi | easy | 2 | YES | True | 13 | 15 | 105.4 | 1/1 | Çözüldü :: exit=0 required 2/2 passed; ['11 passed in 0.63s'] |
| fastapi_14356 | fastapi/fastapi | medium | 8 | no | True | 36 | 45 | 523.8 | 1/1 | Syntax/Import Hatası :: exit=1 required 0/8 passed; ['34 failed, 7 passed, 12 errors in 1.02s'] |
| rich_3718 | Textualize/rich | easy | 1 | no | True | 8 | 10 | 113.4 | 1/1 | Yanlış Mantık :: exit=1 required 0/1 passed; ['1 failed, 12 passed, 1 warning in 0.19s'] |
| rich_3506 | Textualize/rich | medium | 1 | no | True | 5 | 7 | 107.9 | 1/1 | Yanlış Mantık :: exit=1 required 0/1 passed; ['20 failed, 32 passed in 0.45s'] |
| rich_3052 | Textualize/rich | medium | 1 | no | True | 6 | 8 | 129.3 | 1/1 | Yanlış Mantık :: exit=1 required 0/1 passed; ['1 failed, 6 passed in 0.19s'] |
| fastapi_13920 | fastapi/fastapi | easy | 1 | no | True | 29 | 38 | 333.0 | 1/1 | Yanlış Mantık :: exit=1 required 0/1 passed; ['1 failed in 0.60s'] |
| fastapi_14258 | fastapi/fastapi | easy | 1 | no | True | 18 | 20 | 175.1 | 0/1 (yama boş) | Erken Submit :: empty patch (after protected-file strip) |
| fastapi_14791 | fastapi/fastapi | easy | 36 | no | True | 6 | 8 | 68.8 | 1/1 | Syntax/Import Hatası :: exit=1 required 0/36 passed; ['36 failed, 129 passed, 6 errors in 3.54s'] |
| fastapi_14616 | fastapi/fastapi | medium | 3 | YES | True | 37 | 39 | 314.6 | 1/1 | Çözüldü :: exit=0 required 3/3 passed; ['4 passed in 0.61s'] |
| fastapi_14482 | fastapi/fastapi | medium | 1 | no | True | 20 | 22 | 170.2 | 0/1 | Yanlış Dosya :: exit=1 required 0/1 passed; ['1 failed, 2 passed in 0.83s'] |
| httpx_3672 | encode/httpx | hard | 5 | no | True | 21 | 23 | 298.6 | 1/7 | Yanlış Mantık :: exit=1 required 0/5 passed; ['5 failed, 19 passed in 0.17s'] |

## Hata Taksonomisi

Çözüldü: 6  |  Yanlış Dosya: 2  |  Erken Submit: 1  |  Syntax/Import Hatası: 2  |  Yanlış Mantık: 7  |  Tur Limiti: 2

`src∩gold` = ajanın değiştirdiği (test/korunaklı olmayan) kaynak dosyalar ∩ gold patch'in kaynak dosyaları. `Yanlış Dosya` kovası yalnızca bu iki küme **hiç** kesişmediğinde dolar; yaması strip'ten sonra boşalan görev `Erken Submit` sayılır, bu yüzden lokalizasyon bu sütundan okunur.

## Notlar (run_21_bench20_v5_8 — 2026-11-07)

- Paket: v5.7-sweep (6/20) + mekanik kapılar (`submission_swegemma_v5_8_compile_gate`):
  - Her edit_file sonrası kontrol: `py_compile` + modül importu (paket hiç import edilemiyorsa import adımı atlanır); başarısızsa `git checkout -- FILE` ile otomatik geri alma (`COMPILE_OR_IMPORT_FAILED_REVERTING`).
  - Planner FAST PATH test komutu: değişen tüm .py dosyalarında aynı kapı + SOURCE_FILES (tests/docs hariç) + test BEFORE/AFTER karşılaştırması → yalnızca `READY_TO_SUBMIT` iken submit. MULTI-STEP yolunda planner'ın submit etmesi yasak (requests_7205 v5.7'de test etmeden submit etmişti).
  - QA judge: kaynak .py değişmemişse `NO_SOURCE_FILE_CHANGED` → GATE_FAIL.
  - Warning/Exception kuralı: `git grep -nE 'class [A-Za-z_]*(Warning|Error)' -- <package_dir>/` ile repo'nun kendi sınıfı.
- Bütçe değişmedi: 45 tur / 58 çağrı / 15 dk / 180 s.
- Kapılar requests reposunda manuel doğrulandı (continue-dışı-döngü, IndentationError, modül-seviyesi NameError → geri alındı; test-only → NOT_READY; geçerli src → READY_TO_SUBMIT).
