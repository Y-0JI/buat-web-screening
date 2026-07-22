# Debug: SEMUA data riset kosong + error

## Update dari klarifikasi user
- Gejala: **SEMUA data kosong** (bukan cuma Market Intelligence).
- Backend: user **nggak yakin** jalan dari branch mana / lagi jalan apa nggak.

→ Ini bukan bug fitur MI. Ini **seluruh frontend↔backend gagal**.
Satu-satunya penyebab yang bikin SEMUA endpoint kosong: browser nggak bisa
sambung ke backend (backend mati / port salah / branch lama tanpa route /
CORS / `NEXT_PUBLIC_API_URL` salah).

## Fakta yang sudah diverifikasi (kode OK)
- Backend **bisa** balikin data (jalankan `get_intelligence` langsung → dividen,
  foreign flow, broker terisi). Provider IDX reachable dari environment ini.
- Frontend `npx tsc --noEmit` bersih.
- `NEXT_PUBLIC_API_URL=http://localhost:8000` (di `frontend/.env`).

## Diagnosis ranked (semua = connectivity, bukan logic)
1. **Backend nggak jalan** → semua `/api/*` reject → "Data tidak ditemukan" /
   error card, nol data. Paling maybe karena user nggak yakin backend nyala.
2. **Backend jalan dari `main` (sebelum PR #139–#145)** → route MI 404, TAPI
   `/api/research` & `/api/stock/.../profile` tetap jalan → berarti BUKAN
   "semua kosong". Jadi kalau beneran SEMUA kosong, ini bukan penyebab utama.
3. **CORS / origin salah** → buka app lewat `127.0.0.1:3000` atau domain lain,
   `cors_origins` cuma `localhost:3000` (`config.py:22`) → semua fetch block.
4. **`NEXT_PUBLIC_API_URL` di-override env user** → nunjuk ke host mati.

## Rencana eksekusi (setelah plan mode)
### Step 1 — Pastikan backend nyala & reachable
```bash
# di folder backend, branch ini:
uvicorn app.main:app --reload --port 8000
# cek dari terminal:
curl -s http://localhost:8000/            # harua {"app":"BSJP AI",...}
curl -s http://localhost:8000/api/market-intelligence/BBCA | head -c 300
```
Kalau `curl` gagal → backend mati → nyalain. Pastikan jalan dari branch
`feat/16.5.5-frontend-integration` (atau `main` SETELAH PR #139–#145 merge).

### Step 2 — Cek dari browser (DevTools → Network)
Buka riset BBCA, lihat request `/api/research` & `/api/stock/BBCA/profile`:
- Status **(failed) / net::ERR_CONNECTION_REFUSED** → backend mati / port salah.
- Status **404** → backend jalan dari branch lama → restart dari branch ini.
- **CORS error** di Console → tambah origin ke `cors_origins` (`config.py:22`),
  mis. `"http://localhost:3000,http://127.0.0.1:3000"`.
- Status **200** tapi `data:null` → backend jalan tapi provider gagal (cek log
  backend untuk `MI fetch_* error` / error IDX). Dari env ini provider OK, jadi
  kemungkinan network user ke IDX bermasalah.

### Step 3 — Fix kecil UI (tetap dikerjain, independent)
Hoist kartu MI keluar dari guard `report` di `research-view.tsx:121` supaya MI
render mandiri walau `report` kosong.

## Yang saya butuh dari lu (biar fix tepat sasaran)
Buka DevTools → Network, buka riset BBCA, kabarin:
- Status request `/api/research` & `/api/market-intelligence/BBCA` apa?
- Di Console ada error merah nggak (CORS / connection refused)?
- Backend lagi nyala apa nggak (coba `curl http://localhost:8000/`)?
