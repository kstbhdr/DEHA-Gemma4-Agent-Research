# VALIDATION — 31B Paralel (run_36_31b_parallel_30m) Final Karşılaştırma Raporu

Oluşturma: 2026-11-11 22:13 UTC  |  bench: kaggle_bench_20 (aynı 20 görev, aynı sıra)  |  tamamlanan: 20/20

## Özet skor
| koşu | model / mimari | çözülen |
|---|---|---|
| run_21_bench20_v5_8 (en iyi tek E4B) | E4B-QAT, 4-ajan DAG v5.8 | 6/20 |
| E4B birleşimi (18 E4B koşusu, run_24 DeepSeek hariç) | E4B-QAT, çeşitli | 10/20 |
| run_35_l4_31b_gguf | 31B Q3_K_M+MTP, tekil Fixer→QA, 15 dk / 58 çağrı | 10/20 |
| **run_36_31b_parallel_30m** | **31B Q3_K_M+MTP, LoopAgent(3)→[Fixer A ‖ Fixer B]→QA, 30 dk / 110 çağrı** | **13/20** |
| 31B birleşimi (run_35 ∪ run_36) | — | 14/20 |

run_36 – run_35 farkı: **4 kazanç, 1 regresyon** (net +3).
Çözüm katkısı (winner_branch, yalnız çözülenler): auto_recovery: 3, fixer_a: 10.
Paket dağılımı (çözülenler): v2: 4, v2r: 9 — `v2` = orijinal paket (ilk 6 görev), `v2r` = yeniden inşa (kalan 14).
Yeni oturumdaki 14 görevde kaydedilen LiteLLM başarısız deneme sayısı: 0.

## Görev bazlı tablo
| task | faz | E4B best (run_21) | E4B union | run_35 | run_36 | winner_branch | pkg | submitted | calls | QA iters | wall_s | Δ vs run_35 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rich_3454 | F1 | YES | YES | YES | **YES** | fixer_a | v2 | True | 57 | 0 | 867.2 |  |
| requests_7309 | F1 | YES | YES | YES | **YES** | fixer_a | v2 | True | 19 | 0 | 263.6 |  |
| rich_3506 | F1 | no | YES | no | **no** | auto_recovery | v2 | False | 68 | 0 | 1819.0 |  |
| fastapi_14616 | F1 | YES | YES | no | **YES** | auto_recovery | v2 | False | 110 | 0 | 1416.4 | KAZANÇ |
| fastapi_14964 | F1 | no | no | no | **no** | fixer_a | v2 | True | 50 | 0 | 554.8 |  |
| requests_7315 | F1 | YES | YES | no | **YES** | fixer_a | v2 | True | 24 | 0 | 335.5 | KAZANÇ |
| rich_3468 | F1 | no | no | no | **no** | auto_recovery | v2r | False | 110 | 0 | 1600.9 |  |
| fastapi_14258 | F1 | no | no | no | **no** | fixer_a | v2r | True | 79 | 1 | 753.5 |  |
| rich_3718 | F1 | no | no | no | **YES** | fixer_a | v2r | True | 43 | 1 | 706.2 | KAZANÇ |
| rich_3052 | F1 | no | no | no | **YES** | auto_recovery | v2r | False | 109 | 2 | 1811.1 | KAZANÇ |
| fastapi_14482 | F1 | no | no | no | **no** | fixer_a | v2r | True | 40 | 1 | 473.3 |  |
| fastapi_13920 | F1 | no | no | no | **no** | auto_recovery | v2r | False | 110 | 0 | 1331.1 |  |
| fastapi_14791 | F2 | no | no | YES | **no** | fixer_a | v2r | True | 37 | 1 | 626.5 | REGRESYON |
| requests_7205 | F2 | YES | YES | YES | **YES** | fixer_a | v2r | True | 27 | 1 | 350.7 |  |
| requests_6644 | F2 | no | YES | YES | **YES** | fixer_a | v2r | True | 63 | 1 | 753.2 |  |
| fastapi_14301 | F2 | YES | YES | YES | **YES** | fixer_a | v2r | True | 49 | 1 | 687.7 |  |
| rich_3518 | F2 | no | YES | YES | **YES** | fixer_a | v2r | True | 40 | 1 | 370.1 |  |
| rich_3882 | F2 | no | YES | YES | **YES** | fixer_a | v2r | True | 30 | 1 | 345.9 |  |
| fastapi_14356 | F2 | no | no | YES | **YES** | fixer_a | v2r | True | 61 | 1 | 813.7 |  |
| httpx_3672 | F2 | no | no | YES | **YES** | auto_recovery | v2r | False | 110 | 0 | 1018.3 |  |

## Okuma notları
- `winner_branch`: `fixer_a` / `fixer_b` = QA turnuvasının (`/tmp/deha_qa2.py`) submit ettiği aday; `auto_recovery` = submit yok, /workspace'teki git diff harness tarafından kurtarılıp değerlendirildi (Kaggle Automatic Unsubmitted Patch Recovery ile aynı semantik).
- Yerel sunucu 3-bit GGUF (Q3_K_M) + MTP; Kaggle 4xL4'te resmi W4A16 vLLM kullanılır — mutlak skor ve süreler birebir aktarılamaz, mimari karşılaştırması aynı donanım/aynı bench üzerinde geçerlidir.
- Bu oturumun L4 örneği kayıtlı ölçümden ~%25-30 yavaştı (decode ~58 tok/s toplam, kayıtlı 77); 30 dk bütçesine sığma açısından run_36'nın son 14 görevi dezavantajlı koşuldu.
- İlk 6 görev orijinal v2 paketiyle, kalan 14 görev v2r ile koşuldu; paketlerin farkı `submission_kaggle_31b_parallel_v2.RECONSTRUCTION.md` dosyasında.

## Kesin bulgular (run_36, 20/20)
1. **Paralel mimari net kazanç:** 13/20 (run_35 10/20, en iyi tek E4B 6/20). 4 yeni çözüm (fastapi_14616, requests_7315, rich_3718, rich_3052), 1 regresyon (fastapi_14791). 31B birleşimi 14/20.
2. **fixer_b hiç kazanmadı (0/13).** Çözülenlerin 10'u fixer_a (QA submit), 3'ü auto_recovery. fixer_b'nin tek işlevi CONSENSUS'ta ikinci tanık olmak (requests_7309) — çağrı bütçesinin ~%40-55'ini tüketiyor.
3. **Bütçe: v2r ile koşulan 14 görevin 3'ünde QA hiç çalışmadı** (rich_3468, fastapi_13920, httpx_3672; iterations=0, 110/110 çağrı paralel fazda bitti); rich_3052 ise 2 QA iterasyonuna rağmen submit edemeden 30 dk'yı doldurdu. Prompt'taki "25/20 çağrıda bitir" sınırı 31B tarafından yok sayılıyor (rich_3468: B 63, A 48 çağrı); compaction sonrası CONTEXT_RESTART tekrarları (2–7 kez) bütçeyi eritiyor. 3 çözüm (fastapi_14616, rich_3052, httpx_3672) yalnız auto_recovery sayesinde geldi → Kaggle'da da Unsubmitted Patch Recovery'ye bağımlıyız. Not: ilk 6 görevin (v2) `QA iters` değeri güvenilmez — eski harness bunu v2 paketinin kullanmadığı /tmp/deha_iter'den okuyordu (ör. rich_3506 trace'inde 6 QA çağrısı var).
4. **QA kör noktası (fastapi_14791 regresyonu):** turnuva betiği yalnız `tests/test_<modül>.py` arıyor; `fastapi/openapi/utils.py` için `TESTS_NONE` → test edilmeden submit; fazladan `required: input` 36 snapshot testini kırdı (run_35'te aynı görev 7 çağrıda çözülmüştü).
5. **Çözülemeyenlerin kökü:** doğru dosya/yanlış satır (rich_3506), yanlış katman (fastapi_14482 encoders vs _compat/v2), altyapı kurup kullanım noktasına bağlamama (fastapi_13920), gizli testin birebir mesaj/mekanizma beklentisi (fastapi_14258 mesaj, fastapi_14964 `@deprecated`).
6. **Önerilen v3 (test edilmedi, paket güncellenmedi):** (a) fixer_b'yi kaldır veya yalnız iterasyon 1'de çalıştır → bütçe QA'ya kalır; (b) QA betiğinde TESTS_NONE ise `git grep -l <değişen modül adı> tests/` ile ilgili test dosyalarını bul; (c) fixer_a'ya "diff'i issue'nun istediğinden büyütme" kuralı. Bu oturumda doğrulanmadığı için ZIP'ler değiştirilmedi (Adım 4.2: net ve doğrulanmış iyileştirme şartı).
