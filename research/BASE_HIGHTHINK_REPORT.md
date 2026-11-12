# BASE_HIGHTHINK_REPORT — v5.8 saf taban, thinking 4096 → 8192/12288

oluşturma: 2026-11-10 20:33:09

## Skor

| koşu | thinking_budget | resolved | biten |
|---|---|---|---|
| `run_21_bench20_v5_8` | 4096 | **6/20** | 20/20 |
| `run_28A_base_control_v5` | 4096 | **6/20** | 20/20 |
| `run_30_base_highthink` | 8K/12K | **6/20** | 15/20 |
| `run_31_feedback_fix` | 8K/12K + geri bildirim düzeltmesi | **5/20** | 20/20 |

## Görev bazında

| task | run21 | run28A | run30 | run31 | run31 kova | run31 calls/turns/wall_s |
|---|---|---|---|---|---|---|
| requests_7205 | YES | YES | YES | YES | Çözüldü | 35/50/443.8 |
| requests_6644 | no | YES | no | no | Yanlış Mantık | 24/32/251.5 |
| requests_7309 | YES | YES | YES | YES | Çözüldü | 53/72/719.2 |
| requests_7315 | YES | YES | YES | YES | Çözüldü | 52/72/711.0 |
| fastapi_14301 | YES | YES | YES | YES | Çözüldü | 22/29/236.3 |
| fastapi_14616 | YES | no | no | no | Yanlış Mantık | 26/32/338.1 |
| rich_3454 | YES | YES | YES | no | Erken Submit | 52/72/722.2 |
| rich_3518 | no | no | no | no | Erken Submit | 56/72/753.6 |
| fastapi_14964 | no | no | no | no | Erken Submit | 38/46/929.8 |
| rich_3468 | no | no | no | no | Tur Limiti | 57/72/622.1 |
| rich_3506 | no | no | no | YES | Çözüldü | 50/66/604.9 |
| rich_3718 | no | no | no | no | Yanlış Mantık | 42/57/559.6 |
| rich_3882 | no | no | YES | no | Erken Submit | 21/29/289.9 |
| rich_3052 | no | no | no | no | Yanlış Mantık | 38/53/661.0 |
| fastapi_14356 | no | no | no | no | Syntax/Import Hatası | 27/35/453.1 |
| fastapi_14791 | no | no | — (koşulmadı) | no | Syntax/Import Hatası | 13/21/170.3 |
| fastapi_14482 | no | no | — (koşulmadı) | no | Tur Limiti | 53/72/774.2 |
| fastapi_13920 | no | no | — (koşulmadı) | no | Yanlış Dosya | 18/26/195.8 |
| fastapi_14258 | no | no | — (koşulmadı) | no | Yanlış Dosya | 47/56/666.2 |
| httpx_3672 | no | no | — (koşulmadı) | no | Yanlış Mantık | 42/51/548.0 |
- **run_30_base_highthink:** 4096'da hiç çözülmemişken çözülen: ['rich_3882']; iki 4096 koşusunda da çözülmüşken kaybedilen: —
- **run_31_feedback_fix:** 4096'da hiç çözülmemişken çözülen: ['rich_3506']; iki 4096 koşusunda da çözülmüşken kaybedilen: ['rich_3454']
- 4096 kontrolünün kendi gürültüsü: iki koşuda da çözülen ['fastapi_14301', 'requests_7205', 'requests_7309', 'requests_7315', 'rich_3454']; yalnız birinde çözülen ['fastapi_14616', 'requests_6644']
- Dört koşunun **herhangi birinde** çözülen görevler (birleşim): 9/20 — ['fastapi_14301', 'fastapi_14616', 'requests_6644', 'requests_7205', 'requests_7309', 'requests_7315', 'rich_3454', 'rich_3506', 'rich_3882']

## Ajan başına düşünce token'ları (model yanıtı başına)

Not: run21 trace'lerinde düşünce metni saklanmadığı için o sütun boş. Aynı yöntem: trace'teki düşünce metni Gemma-4 tokenizer'ı ile sayıldı (eski koşular yalnızca metni sakladığı için). run30 için vLLM `usage.reasoning_tokens` sütunu da verildi.

| ajan | run21 ort / maks (n) | run28A ort / maks (n) | run30 ort / maks (n) | run31 ort / maks (n) | run30+31 vLLM usage ort / maks (n) | bütçe (run30/31) |
|---|---|---|---|---|---|---|
| planner | — | 329 / 4094 (343) | 336 / 2916 (213) | 410 / 4601 (268) | 378 / 4601 (481) | 8192 |
| coder_a | — | 497 / 3062 (26) | 343 / 3828 (232) | 381 / 12286 (336) | 367 / 12286 (568) | 12288 |
| coder_b | — | 324 / 2185 (25) | 417 / 12286 (100) | 350 / 3796 (203) | 373 / 12286 (303) | 12288 |
| qa_judge | — | 167 / 940 (37) | 135 / 714 (100) | 122 / 864 (208) | 128 / 865 (308) | 8192 |

run30+31'de bütçe tavanına (≥ bütçe−16) dayanan yanıt sayısı: {'planner': 0, 'coder_a': 2, 'coder_b': 1, 'qa_judge': 0}

## Bağlam koruması (run30 + run31)

- model çağrısı: 1660; budama tetiklenen: 45; max_output_tokens kısılan (prompt+çıktı > 32768 olacaktı): 39; maks prompt tahmini: 30830 → budama sonrası maks 16120
- finish_reason dağılımı: {'FinishReason.STOP': 1660}; LLM hata kodlu yanıt: 0
- 15 dk zaman bütçesine takılan görevler: ['31:fastapi_14964']

## Taksonomi

- `run_21_bench20_v5_8`: Çözüldü: 6  |  Yanlış Dosya: 2  |  Tur Limiti: 2  |  Yanlış Mantık: 7  |  Syntax/Import Hatası: 2  |  Erken Submit: 1
- `run_28A_base_control_v5`: Çözüldü: 6  |  Yanlış Mantık: 5  |  Erken Submit: 6  |  Tur Limiti: 1  |  Syntax/Import Hatası: 1  |  Yanlış Dosya: 1
- `run_30_base_highthink`: Çözüldü: 6  |  Tur Limiti: 8  |  Erken Submit: 1
- `run_31_feedback_fix`: Çözüldü: 5  |  Yanlış Mantık: 5  |  Erken Submit: 4  |  Tur Limiti: 2  |  Syntax/Import Hatası: 2  |  Yanlış Dosya: 2

## Kurulum ve yöntem

- GPU: NVIDIA L4 24 GB → 2 paralel worker; her görev `unshare -m` ile özel `/workspace` + `/tmp` (kaynak: `/tmp/work_highthink_<task_id>`).
- vLLM 0.33.0 (referans koşularla aynı sürüm): `--tool-call-parser gemma4 --reasoning-parser gemma4 --enable-auto-tool-choice --enable-prefix-caching --enable-chunked-prefill --gpu-memory-utilization 0.88 --max-model-len 32768` (+ `--served-model-name google/gemma-4-E4B-it-qat-w4a16-ct gemma-4-e4b-it-qat-w4a16-ct`, `--limit-mm-per-prompt {"image":0,"audio":0}`). LoRA yok.
- Paket `submission_v5_8_highthink`: v5.8 compile-gate prompt'ları; `sub_agents/{planner,coder_a,coder_b,qa_judge}.yaml` (talimatlar satır içi; `!include` kök/dosya-göreli belirsizliği yok), hiçbir ajanda `adapter:` yok, model `google/gemma-4-E4B-it-qat-w4a16-ct`.
- Planner araçları: `search_similar_code, get_code_neighbors, get_code_subgraph, read_file, run_command, get_status` (`edit_file` ve `submit_patch` kaldırıldı). Planner prompt'undaki FAST PATH (planner'ın kendisinin düzeltip submit etmesi) artık olmayan araçları gerektirdiği için "her zaman görev dosyası yaz → tek fonksiyonlu düzeltmede yalnız Task A" yoluna çevrildi; Coder/QA prompt'ları değişmedi.
- Bütçe değişmedi: 58 tool call / 45 tur / 15 dk / 180 s.

## ADIM 3 kanıtı — thinking_budget iletimi

- Koşu harness'ı ile derlenen her ajandan bir gerçek istek, yakalama proxy'si üzerinden vLLM'e gönderildi (`logs/budget_proof.json`): gönderilen `thinking_token_budget` = planner **8192**, coder_a **12288**, coder_b **12288**, qa_judge **8192**; `chat_template_kwargs.enable_thinking=true`; `max_tokens` 16384/20480/20480/16384; temperature 0.2/0.2/0.2/0.1. 4096'ya düşen yok.
- İletim yolu Kaggle README §2.4 ile aynıdır: `extra_body.thinking_token_budget` (ADK `ThinkingConfig`, LiteLLM tarafında yalnızca `reasoning_effort`'a çevrildiği için bilerek kullanılmadı; referans 6/20 koşuları da bu yolu kullanıyordu).
- Uygulanma: bütçe 256 ile istek → vLLM `reasoning_tokens` = **256** (sert kesim). vLLM 0.33'te bütçe yalnızca `reasoning_config` etkinse kabul edilir; `--reasoning-parser gemma4` bunu otomatik etkinleştiriyor (aksi halde 400 dönerdi).
- 4096 üstünün gerçekten kullanıldığının kanıtı aşağıdaki "ajan başına düşünce token'ları" tablosundaki vLLM usage maksimumlarıdır (4096'yı aşan yanıtlar).

## Bağlam koruması

- Kaggle `inference.py` eşdeğeri: `App(events_compaction_config=EventsCompactionConfig(compaction_interval=15, overlap_size=2, token_threshold=14336, event_retention_size=5))` (özetleyici: düşüncesiz aynı model).
- ADK 2.14 bu sıkıştırmayı yalnızca invocation **sonrasında** çalıştırıyor; tek DAG invocation'ı içinde bağlam büyümeye devam eder. Bu yüzden ek olarak her model çağrısından önce (`before_model_callback`) tahmini prompt 14 336 token'ı geçerse son 5 içerik dışındaki eski tool çıktıları kısa özetlere, eski düşünce parçaları kaldırılır (oturum geçmişi değişmez, yalnız giden istek). Son çare: prompt+max_output_tokens > 32 768 ise max_output_tokens kısılır (sayılır, raporlanır).
- Gözlem: vLLM 0.33 prompt+max_tokens > 32 768 olduğunda 400 döndürmüyor, çıktıyı kendisi kısıyor (15 021 + 20 480 istek kabul edildi).

## Uyarılar

- **Model adı büyük harfli:** `google/gemma-4-E4B-it-qat-w4a16-ct` önek atılınca `gemma-4-E4B-it-qat-w4a16-ct` olur; `ALLOWED_MODEL_NAMES` küçük harflidir. Yerel doğrulayıcı büyük/küçük harf duyarsız eşleştirip 4 uyarı verdi (0 hata). Kaggle'ın `normalize_model_name`'i küçük harfe çevirmiyorsa gönderim `ParticipantVisibleError` alabilir; risksiz yol `model: gemma-4-e4b-it-qat-w4a16-ct`.
- Hız: L4'te tek akış ≈ 52 tok/s; 12K düşünce ≈ 4 dk. 15 dk ajan bütçesi, yüksek düşünce bütçesinde daha sık dolabilir (Kaggle 4×L4'te hız farklıdır).
- 4096 kontrolünün kendi varyansı yüksektir (run21 ve run28A aynı paketle 6/20 aldı ama farklı görevleri çözdü); tek koşuluk ±1–2 görev farkı gürültü sınırındadır.

## run_31_feedback_fix — geri bildirim döngüsü düzeltmesi (aynı 8K/12K bütçe)

Değişiklikler: `logs/run_31_feedback_fix/NOTES.md` (8 madde: STEP 0 sıfırlaması kaldırıldı, Coder'lar geri bildirimi okuyor, QA traceback ekliyor, QA'nın kendi iterasyon sayacı, ardışık-satır `DUPLICATE_LINES`, `max_turns` 45→72, mekanik `TESTS_GREEN/TESTS_RED`, harness budama düzeltmesi).

| ölçüm | run28A (4096) | run30 (8K/12K) | run31 (düzeltme) |
|---|---|---|---|
| QA geri bildirimi yazılan görev | 4/20 | 10/15 | 11/20 |
| sonraki iterasyonda geri bildirim modele **ulaştı** | 2 | 2 | **14** |
| geri bildirim okunmadan **silindi** | 3 | 5 | **0** |
| QA'nın submit ettiği görev | 0 | 2 | **13** |
| Planner görev JSON'unu dosyaya yazmak yerine düz metin olarak yazdı (planner koşusu) | 0 | 4 | **10** |

Yorum:
- Döngü mekanik olarak artık çalışıyor (geri bildirim kaybı 0, iterasyon sayacı doğru, QA submit ediyor), ama çözülen sayı artmadı (5/20). Yeni çözülen `rich_3506` (hiçbir koşuda çözülmemişti); kaybedilen `rich_3454` ve `rich_3882` (Coder test dosyasını değiştirdi / yanlış regex) ve run30'a göre `fastapi_14301` hariç fastapi tarafı değişmedi.
- **Asıl kısıt doğrulama sinyali:** QA yalnızca reponun mevcut `tests/test_<modül>.py` dosyalarını koşuyor; değerlendirmedeki FAIL_TO_PASS testleri ajan tarafından görülmüyor. `TESTS_GREEN` çoğu zaman "hiçbir şeyi bozmadın" demek, "hatayı düzelttin" değil → QA 13 görevde submit etti, 5'i doğru. Geri bildirim ancak test kırıldığında bilgi taşıyor.
- **Yeni darboğaz:** read-only Planner sık sık görev listesini `run_command` ile `/tmp/deha_isolated_tasks.json`'a yazmak yerine son mesajda düz metin olarak veriyor (run31'de 10 planner koşusu). Coder A bu mesajı bağlamda gördüğü için çoğu zaman yine de çalışıyor, ama Coder B / sonraki iterasyonlar görev dosyasını bulamıyor.
- Düşünce bütçesi: model 8K/12K bütçeyi nadiren kullanıyor (tablodaki ortalamalar); bütçe artışı tek başına skor getirmedi.
- Öneri: (1) Planner'ın son adımını "tek izin verilen son çağrı: görev dosyasını yazan run_command" diye sıkılaştırmak ya da Coder A'nın NO_TASKS durumunda planner mesajındaki JSON'u kendisinin dosyaya yazması; (2) QA'ya issue'daki örnekten küçük bir yeniden üretim (repro) betiği yazdırıp onu da BEFORE/AFTER koşturmak — gerçek "hata düzeldi" sinyali; (3) thinking_budget'i 4096'ya geri almak (hız, aynı kalite).

