# Improvement: AI Error Handling (Graceful)

## Problem
Saat layanan AI (Gemini) error — quota habis, rate limit, timeout, provider down —
detail exception bocor ke UI:
- `orchestrator.py:121` menambahkan `f" | Gagal memanggil AI: {str(e)}"` langsung ke
  `report.summary` (narasi AI yang ditampilkan di kartu Insight AI).
- `research.py:84` duplikat leak yang sama via `report.summary += ...`.
- `chat.py:150` return `{"error": str(e)}` — exception string sampai ke UI.
- `vision.py:111` `f"Gagal menganalisis gambar: {str(e)}"` ke `analysis_text`.

Syarat dari user:
1. Tangani error AI graceful, jangan tampilkan exception/stack trace.
2. Pesan ramah pengguna (user-friendly).
3. **Pertahankan hasil non-AI** yang sudah sukses (skor, chart, teknikal, fundamental, berita).
4. Log detail error ke backend untuk debugging.
5. Memungkinkan retry tanpa merusak tampilan.

## Existing good reference
`insight.py:116` sudah pola benar: `except Exception: sentiment="neutral"; summary="Ringkasan AI tidak tersedia saat ini."` (generic + tetap return data). Jadikan standar.

Logging: `configure_logging()` sudah aktif (main.py:25). Cukup `logger.error("...: %s", e, exc_info=True)`.

## Files to change (backend)

### 1. `backend/app/ai/orchestrator.py`
- Tambah `import logging` + `logger = logging.getLogger(__name__)`.
- Ganti `except Exception as e: report.summary += f" | Gagal memanggil AI: {str(e)}"`
  menjadi: `logger.error("AI enhancement gagal untuk %s: %s", report.ticker, e, exc_info=True)`
  lalu `report.summary += " | Insight AI sedang tidak tersedia, silakan coba beberapa saat lagi."`
- Ganti pesan key-missing & timeout ke bahasa ramah konsisten:
  - key missing (`line 65`): `" | AI reasoning tidak tersedia (belum dikonfigurasi)."` (sudah ok, hanya tweak wording opsional).
  - timeout (`line 119`): `" | Insight AI timeout, silakan coba lagi."`
- Hasil non-AI (report.summary asli dari scoring) tetap utuh; hanya append suffix.
- `enhance_with_ai` sudah tidak raise (ditangani di dalam), jadi `research.py:81-84 try/except` jadi redundant — biarkan tapi sederhanakan pesannya.

### 2. `backend/app/routers/research.py`
- Hapus/ubah leak di `line 84`: ganti `report.summary += f" | AI enhancement gagal: {str(e)}"`
  menjadi pesan generik `" | Insight AI sedang tidak tersedia, silakan coba lagi."`
  (dan log sudah di orchestrator; atau pindah log ke sini). Karena orchestrator sudah
  try/except internal, blok ini praktis tak terpanggil — tetap perbaiki demi aman.

### 3. `backend/app/routers/chat.py`
- `line 150`: `return {"success": False, "error": str(e)}` → log dulu lalu return pesan generik:
  `logger.error("Chat AI error: %s", e, exc_info=True); return {"success": False, "error": "Layanan AI sedang tidak tersedia. Coba kirim pesan lagi nanti."}`
- Frontend chat-panel (`chat-panel.tsx:156-160`) sudah tampil generic ("Gagal menghubungi AI. Coba lagi.") — cukup; tidak perlu ubah, tapi pastikan tidak menampilkan `error` mentah. (Saat ini catch block tidak pakai `res.error`, jadi aman.)

### 4. `backend/app/ai/vision.py`
- `line 108-116`: `analysis_text` jangan leak `str(e)`. Ubah ke:
  `logger.error("Vision AI gagal untuk %s: %s", filename, e, exc_info=True)`
  `analysis_text: "Gagal menganalisis gambar karena layanan AI tidak tersedia. Coba lagi nanti."`

### 5. `backend/app/routers/insight.py`
- Sudah graceful (line 116-118). Tidak diubah, hanya pastikan log ada:
  ganti `except Exception:` → `except Exception as e:` + `logger.error("Market insight AI gagal: %s", e, exc_info=True)` sebelum generic message.

## Frontend (DITAMBAH — user setuju)
- `stock-report.tsx` kartu Insight AI (line ~213-222): deteksi kalau `data.summary`
  mengandung marker AI-offline (backend akan set flag, lihat schema di bawah) → tampilkan
  badge amber "AI sedang tidak tersedia — coba lagi nanti" di header kartu, tanpa mengubah
  layout/merusak tampilan. Narasi fallback tetap ditampilkan sebagai teks.
- Tambah field `ai_available: bool` (default True) ke `StockReport` schema (backend) dan ke
  `StockReport` interface di `frontend/src/lib/api.ts`. Orchestrator set `ai_available=False`
  saat error/timeout/key-missing; frontend pakai flag ini untuk badge (lebih robust daripada
  string-matching).
- `cd frontend && npx tsc --noEmit` wajib.

## Verification
- Backend: jalankan smoke test panggil `enhance_with_ai` dengan API key sengaja salah /
  `timeout` pendek → assertion `report.summary` TIDAK mengandung substring `google.api_core`,
  `ResourceExhausted`, `traceback`, `genai.` dst; mengandung kata "tidak tersedia"/"coba lagi".
- `chat.py` / `vision.py`: mock raise → response `error` tidak mengandung trace.
- `cd backend && python -c "import app..."` import check; jalankan server, hit `/api/research`
  dengan AI mati → UI tetap tampil skor/chart/teknikal, hanya Insight AI berisi pesan ramah.
- `cd frontend && npx tsc --noEmit` (jika ubah frontend).

## Deliverable
- Branch: **gabung ke `feat/16.4.4-news-engine`** (otomatis masuk PR #125, base `main`). Jangan merge.
- Issue GitHub: upload plan ini (issue baru).
- Commit terpisah dari fix news frontend (pesan jelas: `fix(ai): graceful error handling`).
