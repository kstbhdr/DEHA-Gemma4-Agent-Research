# run_36_31b_parallel_30m bench20 — live summary

updated: 2026-11-11 22:13:31  |  **13/20 resolved**  |  20/20 tasks finished  |  dosya lokalizasyonu (gold kaynak dosyaya dokunan görev): 17/20  |  çözüm katkısı (winner_branch): auto_recovery: 3  |  fixer_a: 10

model: gemma-4-31b-it-qat-w4a16-ct ← yerelde unsloth gemma-4-31B-it Q3_K_M GGUF — LoRA YOK (llama-server CUDA, -np 2 -c 65536 (2 slot x 32768), KV q4_0, flash-attn, MTP draft n_max=8, NVIDIA L4 24GB, 1 task worker)
yapı: LoopAgent(3) -> Sequential[ParallelAgent(fixer_a || fixer_b), qa_judge]; thinking_budget 6144 / 6144 / 3072 (max_output_tokens 16384, temp 0.15/0.45/0.1); fixer_a /workspace, fixer_b /tmp/wt_b -> /tmp/patch_b.diff, submit_patch yalnızca qa_judge'da; winner_branch: fixer_a / fixer_b = QA turnuvasının submit ettiği aday, auto_recovery = submit yok, /workspace git diff kurtarıldı; bağlam koruması: EventsCompactionConfig(15/2/14336/5) + invocation-içi budama
eval_config: 110 tool calls / 200 turns / 30 min / cmd timeout 300s
**pkg sütunu:** `v2` = orijinal paket (sha1 cc25494…, ilk 6 görev, 2026-11-11 15:34–17:03 oturumu); `v2r` = Drive'da yedeği bulunamayan v2'nin trace'lerden yeniden inşası (sha1 8e2ea028…, kalan 14 görev, yeni L4 oturumu) — bkz. `submission_kaggle_31b_parallel_v2.RECONSTRUCTION.md`. `iters` = QA judge çalışma sayısı.
streaming: her görev biter bitmez `results/<task_id>.json` + `task_logs/<task_id>.log` + bu tablo Drive'a yazılıp `os.sync()` çağrılır

| task | repo | diff | F2P | faz | run_35 | resolved | winner_branch | pkg | submitted | calls | turns | iters | wall_s | src∩gold | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rich_3454 | Textualize/rich | easy | 1 | F1 | YES | YES | fixer_a | v2 | True | 57 | 62 | 0 | 867.2 | 1/1 | Çözüldü :: exit=0 required 1/1 passed; ['83 passed in 0.20s'] |
| requests_7309 | psf/requests | medium | 5 | F1 | YES | YES | fixer_a | v2 | True | 19 | 24 | 0 | 263.6 | 1/1 | Çözüldü :: exit=0 required 5/5 passed; ['207 passed, 13 skipped in 0.31s'] |
| rich_3506 | Textualize/rich | medium | 1 | F1 | no | no | auto_recovery | v2 | False | 68 | 73 | 0 | 1819.0 | 1/1 | Tur Limiti :: exit=1 required 0/1 passed; ['1 failed, 51 passed in 0.29s'] |
| fastapi_14616 | fastapi/fastapi | medium | 3 | F1 | no | YES | auto_recovery | v2 | False | 110 | 112 | 0 | 1416.4 | 0/1 | Çözüldü :: exit=0 required 3/3 passed; ['4 passed in 0.60s'] |
| fastapi_14964 | fastapi/fastapi | hard | 2 | F1 | no | no | fixer_a | v2 | True | 50 | 55 | 0 | 554.8 | 1/1 | Yanlış Mantık :: exit=1 required 2/2 passed; ['2 failed, 7 passed in 1.04s'] |
| requests_7315 | psf/requests | easy | 1 | F1 | no | YES | fixer_a | v2 | True | 24 | 29 | 0 | 335.5 | 1/1 | Çözüldü :: exit=0 required 1/1 passed; ['1 passed in 0.02s'] |
| rich_3468 | Textualize/rich | hard | 1 | F1 | no | no | auto_recovery | v2r | False | 110 | 111 | 0 | 1600.9 | 1/1 | Tur Limiti :: exit=1 required 0/1 passed; ['1 failed, 97 passed in 1.19s'] |
| fastapi_14258 | fastapi/fastapi | easy | 1 | F1 | no | no | fixer_a | v2r | True | 79 | 84 | 1 | 753.5 | 1/1 | Yanlış Mantık :: exit=1 required 0/1 passed; ['1 failed in 0.44s'] |
| rich_3718 | Textualize/rich | easy | 1 | F1 | no | YES | fixer_a | v2r | True | 43 | 48 | 1 | 706.2 | 1/1 | Çözüldü :: exit=0 required 1/1 passed; ['13 passed, 1 warning in 0.18s'] |
| rich_3052 | Textualize/rich | medium | 1 | F1 | no | YES | auto_recovery | v2r | False | 109 | 115 | 2 | 1811.1 | 1/1 | Çözüldü :: exit=0 required 1/1 passed; ['7 passed in 0.17s'] |
| fastapi_14482 | fastapi/fastapi | medium | 1 | F1 | no | no | fixer_a | v2r | True | 40 | 45 | 1 | 473.3 | 0/1 | Yanlış Dosya :: exit=1 required 0/1 passed; ['1 failed, 2 passed in 0.86s'] |
| fastapi_13920 | fastapi/fastapi | easy | 1 | F1 | no | no | auto_recovery | v2r | False | 110 | 111 | 0 | 1331.1 | 1/1 | Tur Limiti :: exit=1 required 0/1 passed; ['1 failed in 0.60s'] |
| fastapi_14791 | fastapi/fastapi | easy | 36 | F2 | YES | no | fixer_a | v2r | True | 37 | 42 | 1 | 626.5 | 1/1 | Syntax/Import Hatası :: exit=1 required 0/36 passed; ['36 failed, 129 passed, 6 errors in 3.53s'] |
| requests_7205 | psf/requests | easy | 1 | F2 | YES | YES | fixer_a | v2r | True | 27 | 32 | 1 | 350.7 | 1/1 | Çözüldü :: exit=0 required 1/1 passed; ['206 passed, 13 skipped in 0.30s'] |
| requests_6644 | psf/requests | easy | 1 | F2 | YES | YES | fixer_a | v2r | True | 63 | 68 | 1 | 753.2 | 0/1 | Çözüldü :: exit=0 required 1/1 passed; ['1 passed in 0.01s'] |
| fastapi_14301 | fastapi/fastapi | easy | 2 | F2 | YES | YES | fixer_a | v2r | True | 49 | 54 | 1 | 687.7 | 1/1 | Çözüldü :: exit=0 required 2/2 passed; ['11 passed in 0.66s'] |
| rich_3518 | Textualize/rich | easy | 1 | F2 | YES | YES | fixer_a | v2r | True | 40 | 45 | 1 | 370.1 | 1/1 | Çözüldü :: exit=0 required 1/1 passed; ['20 passed in 0.26s'] |
| rich_3882 | Textualize/rich | easy | 1 | F2 | YES | YES | fixer_a | v2r | True | 30 | 35 | 1 | 345.9 | 1/1 | Çözüldü :: exit=0 required 1/1 passed; ['8 passed in 0.19s'] |
| fastapi_14356 | fastapi/fastapi | medium | 8 | F2 | YES | YES | fixer_a | v2r | True | 61 | 66 | 1 | 813.7 | 1/1 | Çözüldü :: exit=0 required 8/8 passed; ['41 passed in 0.81s'] |
| httpx_3672 | encode/httpx | hard | 5 | F2 | YES | YES | auto_recovery | v2r | False | 110 | 111 | 0 | 1018.3 | 1/7 | Çözüldü :: exit=0 required 5/5 passed; ['24 passed in 0.13s'] |

## Hata Taksonomisi

Çözüldü: 13  |  Yanlış Dosya: 1  |  Syntax/Import Hatası: 1  |  Yanlış Mantık: 2  |  Tur Limiti: 3

`src∩gold` = ajanın değiştirdiği (test/korunaklı olmayan) kaynak dosyalar ∩ gold patch'in kaynak dosyaları.

# run_36_31b_parallel_30m — NOTES

1. Paket: /content/work_l4_gguf/submission_swegemma_31b_parallel_v2 — LoopAgent(3) -> SequentialAgent[ParallelAgent(fixer_a, fixer_b), qa_judge]; model `google/gemma-4-31b-it-qat-w4a16-ct` (tüm YAML'lar); thinking 6144/6144/3072, max_output 16384, temp 0.15/0.45/0.1; eval_config 300 s / 110 calls / 200 turns / 30 min. validate_submission: 0 error, 0 warning, adapter yok.
2. Yol kısıtı (Kontrol A): HARNESS_README §6.2 — read_file/edit_file yolları baştaki `/` silinerek /workspace altında çözülür (`/tmp/wt_b/x` -> `/workspace/tmp/wt_b/x`). Bu yüzden fixer_b'de read_file/edit_file YOK; okuma/düzenleme/test `run_command` + /tmp/deha_bedit.py (show/edit/test/py/diff) ile yalnızca /tmp/wt_b içinde. Her başarılı edit /tmp/patch_b.diff'i otomatik yazar; test dosyası düzenlemesi reddedilir.
3. eval_config şeması (Kontrol B): `evaluation:` altında timeout_seconds / max_tool_calls / max_time_minutes / max_turns (README §7.1) — dört anahtar da geçerli.
4. llama-server testi (2 eşzamanlı istek x 2 tur, 5.5K prompt tool-call + 700 token üretim): -np 1 -c 32768 MTP: 54.2 s/tur, 16.5 GB; -np 2 -c 65536 MTP: 41.5 s/tur (%23 hızlı, toplam ~77 tok/s), 18.0 GB, OOM yok, tool-call 4/4. -> -np 2 -c 65536 kilitlendi (serve.sh varsayılanı).
5. Yerel harness: ParallelAgent derleme desteği + agent_class doğrulaması eklendi; her görev başında /tmp/wt_b, /tmp/patch_[ab].diff temizlenir (Kaggle'da her görev taze container); sonuçta `winner_branch` (fixer_a / fixer_b / auto_recovery / none) ve `par_left` kaydedilir. Compaction 14336 ve submit edilmeyen /workspace diff'inin kurtarılması (auto recovery) zaten vardı.
6. Smoke 1 (requests_7309, logs/run_36_smoke_parallel_try1): RESOLVED ama auto_recovery, 101 call, 1873 s. Bulgular: (a) iki aday aynı eski-davranış testini kırdı -> QA ikisini de reddetti; (b) QA 140 satırlık heredoc'u iki kez `PEOF'` ile kapattı (betik oluşmadı); (c) ~13.5K token'da EventsCompaction tetiklenince include_contents:none ajan kendi geçmişini kaybedip 1. adıma döndü (B için `rm -rf /tmp/wt_b` = kendi işini silme riski).
7. Düzeltmeler: CONSENSUS kuralı (iki aday da gate geçer ve TAM AYNI mevcut testleri kırarsa -> o testler eski davranışı sabitliyor, A submit); tırnaksız `<<PEOF` heredoc (betiklerde $ ` \ yok, doğrulandı); restart bayrakları /tmp/deha_[ab]_started (B klonu korur, A tek satır cevapla biter; QA her iterasyonda sıfırlar); fixer_b için `bedit py` (kendi kopyasını import eder).
8. Smoke 2 (requests_7309): RESOLVED, submitted=True, winner=fixer_a (CONSENSUS), 21 call, 287 s, /tmp/wt_b ve /tmp/patch_b.diff kalıntısı yok.
9. Sıra: FAZ 1 (run_35'te kaçan 12) -> FAZ 2 (kazanılmış 8, regresyon). TASK_CONCURRENCY=1, görev başına orkestratör zaman aşımı 3000 s.
10. **2026-11-11 ~18:30 UTC — YENİ L4 OTURUMU, STREAMING RESUME (kalan 14 görev).** Önceki oturum 17:03'te `rich_3468` sırasında kapandı; ilk 6 sonuç (results/*.json) **dokunulmadan** korundu ve atlandı.
11. `code/` yedeği Drive'da yoktu → paket ve harness yeniden inşa edildi (**v2r**, paket ağacı sha1 8e2ea028…; ayrıntı `code/RECONSTRUCTION_v2r.md`, kökte `submission_kaggle_31b_parallel_v2.RECONSTRUCTION.md`). Betikler (fixer_a restart guard, fixer_b kurulum + deha_bedit.py, qa deha_qa2.py) bu koşunun kendi trace'lerinden bayt-bayt kurtarıldı; ek olarak fixer_a 25 / fixer_b 20 çağrı/iterasyon sınırı (rich_3506'da QA'ya sıra gelmemesi dersi). Kalan 14 görev v2r ile koşuldu (SUMMARY `pkg` sütunu).
12. rich_3506 LiteLLM tekrarı: 73 LLM çağrısının hepsi STOP ile bitmişti; banner'lar kayıt dışı (retry edilen / compaction özetleyici) çağrılardan geliyordu ve istisna metni bastırılıyordu. Yerel istemcide: `litellm.suppress_debug_info`, her başarısız denemenin gerçek istisnasını `litellm_errors` alanına yazan callback, istek timeout 900 s, özetleyici num_retries=1 / max_tokens 1024 / timeout 300 s. Asıl kayıp sebebi fixer'ların 30 dk boyunca ParallelAgent'ta kalmasıydı (iterations=0). Gönderim mantığı değişmedi.
13. llama.cpp f3b407c yeniden derlendi (CUDA 13.0, sm_89; yedek `tools_cache/llama-server-sm89`). Ölçüm bu örnekte: decode 2 slot ≈ 2 x 28-30 tok/s (~58 toplam), tek slot 31-37 tok/s, prefill 300-400 tok/s, MTP kabul 0.33-0.47, VRAM 18.0 GB, tool-call 2/2 — kayıtlı 77/56/578'in ~%25-30 altında (aynı locked komut). Smoke (requests_7309, yerel, Drive'a yazılmadı): RESOLVED, submitted, winner=fixer_a (CONSENSUS), 23 çağrı, 270 s, 0 LiteLLM hatası.
