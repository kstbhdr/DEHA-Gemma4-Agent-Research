# Koşular arası karşılaştırma (bench20)

| görev | r21 v5.8 | r28A v5.8 | r30 v5.8-HT (15/20) | r31 v5.9 | r32 v6f | r33 v6g | r34 v6h | kaç kez |
|---|---|---|---|---|---|---|---|---|
| requests_7205 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 7 |
| requests_6644 | · | ✅ | · | · | ✅ | · | · | 2 |
| requests_7309 | ✅ | ✅ | ✅ | ✅ | · | ✅ | · | 5 |
| requests_7315 | ✅ | ✅ | ✅ | ✅ | ✅ | · | ✅ | 6 |
| fastapi_14301 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 7 |
| fastapi_14616 | ✅ | · | · | · | · | · | · | 1 |
| rich_3454 | ✅ | ✅ | ✅ | · | · | ✅ | · | 4 |
| rich_3518 | · | · | · | · | · | ✅ | · | 1 |
| fastapi_14964 | · | · | · | · | · | · | · | 0 |
| rich_3468 | · | · | · | · | · | · | · | 0 |
| rich_3506 | · | · | · | ✅ | · | · | · | 1 |
| rich_3718 | · | · | · | · | · | · | · | 0 |
| rich_3882 | · | · | ✅ | · | · | · | · | 1 |
| rich_3052 | · | · | · | · | · | · | · | 0 |
| fastapi_14356 | · | · | · | · | · | · | · | 0 |
| fastapi_14791 | · | · | — | · | · | · | · | 0 |
| fastapi_14482 | · | · | — | · | · | · | · | 0 |
| fastapi_13920 | · | · | — | · | · | · | · | 0 |
| fastapi_14258 | · | · | — | · | · | · | · | 0 |
| httpx_3672 | · | · | — | · | · | · | · | 0 |
| **toplam** | 6 | 6 | 6 | 5 | 4 | 5 | 3 | birleşim 10/20 |

## Değerlendirme
- Tek koşuda en iyi skor 6/20 (v5.8, üç kez). Sonraki sürümler: v5.9 5, v6f 4, v6g 5, v6h 3. Hiçbiri 10/20'ye yaklaşmadı.
- v6h'nin kaybettiği görevlerde (requests_7309, rich_3454, rich_3518, requests_6644) yeni 'planner yoksa coder planlasın' yedeği hiç devreye girmedi. Yani bu kayıplar değişiklikten değil, koşular arası rastgelelikten geliyor (rich_3454'te bozuk yama 48 testi kırdı).
- Sonuç: 20 görevlik benchte bir koşudan diğerine ±2-3 görevlik dalgalanma var. Prompt düzeltmelerinin etkisi bu gürültüden ayırt edilemiyor. 10 görev 7 koşunun hiçbirinde çözülmedi; bunlarda model yanlış mantıkla düzeltme yazıyor.
- Önerilen gönderim: **v5.8 highthink** (`submission_swegemma_v5_8_highthink.zip`), çünkü en tutarlı skoru verdi. `submission_swegemma_v6g.zip` yedek olarak duruyor.
