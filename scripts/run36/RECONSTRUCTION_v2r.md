# submission_swegemma_31b_parallel_v2 — YENİDEN İNŞA (v2r) NOTU — 2026-11-11

**Neden:** SECOND_BRAIN, paketin ve harness kodunun `logs/run_36_31b_parallel_30m/code/` altına yedeklendiğini söylüyordu; yeni oturumda
bu dizin Drive'da **yoktu**. Paket (sha1 `cc25494995feedcd4fb43fa892f4037eac143e5f`) ve run_33–36 harness'ı yalnızca silinen yerel
`/content/work_l4_gguf/` altındaydı. Drive'ın tamamında (dosya adı + tam metin araması) başka kopya bulunamadı.

**Nasıl yeniden kuruldu (`tools/build_pkg.py`):**
1. Yapı/parametreler: `AGENT_INFERENCE_CONFIG.json` (LoopAgent(3) → Sequential[ParallelAgent(fixer_a, fixer_b), qa_judge];
   temp 0.15/0.45/0.1; thinking 6144/6144/3072; max_output 16384; araç listeleri; eval_config 300 s/110/30 dk/200).
2. Talimat metni tabanı: `submission_swegemma_31b_base.zip` (run_35 fixer + qa_judge) — mühendislik kuralları ve cerrahi edit protokolü
   (`/tmp/deha_check.py` betiği dahil) **aynen**; run_36 trace'indeki deha_check.py ile karşılaştırıldı, fark yalnızca modelin kopya gürültüsü.
3. **Bayt-bayt kurtarılan betikler** (run_36 results/*.json trace'lerindeki araç çağrısı argümanlarından):
   - fixer_a ilk komutu (`/tmp/deha_a_started` CONTEXT_RESTART koruması) — fastapi_14964 trace'i, 486 karakter
   - fixer_b kurulum komutu (`git clone --shared /workspace /tmp/wt_b`, `/tmp/deha_b_started`, tam `/tmp/deha_bedit.py` show/edit/test/py/diff) — fastapi_14616, 4674 karakter
   - qa_judge turnuva betiği `/tmp/deha_qa2.py` (A/B değerlendirme, CONSENSUS kuralı, tırnaksız `<<PEOF`) — fastapi_14964, 7802 karakter
4. Yeniden yazılan kısım: fixer_b ve qa_judge'ın düzyazı talimatları (betik çağrı kalıpları trace'lerdeki gerçek kullanımla birebir) ve
   fixer_a'ya "bu iterasyonu 25 çağrıda bitir" / fixer_b'ye "20 çağrıda bitir" sınırı (rich_3506'da QA'ya hiç sıra gelmemesi dersi).

**Sonuç:** 7 dosya, 30.450 bayt (orijinal 31.130), validate: 0 error / 0 warning. Yeni paket ağacı sha1: `8e2ea028f07e0a7c5dc69d3384d6ff5f038d5139`.
run_36'nın ilk 6 görevi orijinal v2 ile, kalan 14 görev v2r ile koşuldu — SUMMARY'de `pkg` sütunu bunu gösterir.
E4B kardeşi: aynı dosyalar, yalnızca `model: gemma-4-e4b-it-qat-w4a16-ct` (HARNESS_README §3 kayıt alias'ı; `google/…-E4B-…` yazımı
validator'da büyük/küçük harf normalleştirme uyarısı üretir), adapter yok; paket sha1 `f70e18e1bb05cf4623e89b927ae097c51a12388b`.
