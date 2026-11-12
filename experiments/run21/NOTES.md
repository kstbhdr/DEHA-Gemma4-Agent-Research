## Notlar (run_21_bench20_v5_8 — 2026-11-07)

- Paket: v5.7-sweep (6/20) + mekanik kapılar (`submission_swegemma_v5_8_compile_gate`):
  - Her edit_file sonrası kontrol: `py_compile` + modül importu (paket hiç import edilemiyorsa import adımı atlanır); başarısızsa `git checkout -- FILE` ile otomatik geri alma (`COMPILE_OR_IMPORT_FAILED_REVERTING`).
  - Planner FAST PATH test komutu: değişen tüm .py dosyalarında aynı kapı + SOURCE_FILES (tests/docs hariç) + test BEFORE/AFTER karşılaştırması → yalnızca `READY_TO_SUBMIT` iken submit. MULTI-STEP yolunda planner'ın submit etmesi yasak (requests_7205 v5.7'de test etmeden submit etmişti).
  - QA judge: kaynak .py değişmemişse `NO_SOURCE_FILE_CHANGED` → GATE_FAIL.
  - Warning/Exception kuralı: `git grep -nE 'class [A-Za-z_]*(Warning|Error)' -- <package_dir>/` ile repo'nun kendi sınıfı.
- Bütçe değişmedi: 45 tur / 58 çağrı / 15 dk / 180 s.
- Kapılar requests reposunda manuel doğrulandı (continue-dışı-döngü, IndentationError, modül-seviyesi NameError → geri alındı; test-only → NOT_READY; geçerli src → READY_TO_SUBMIT).
