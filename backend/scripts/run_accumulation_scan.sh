#!/usr/bin/env bash
#
# Trigger scan akumulasi harian lewat POST /api/accumulation/scan.
#
# Rahasia TIDAK disimpan di repo: token dibaca dari environment (mis. systemd
# EnvironmentFile di luar repo, atau cron yang meng-source file env).
#
# Variabel lingkungan:
#   ACCUMULATION_SCAN_TOKEN   (wajib) token header X-Scan-Token
#   ACCUMULATION_API_URL      default http://localhost:8000
#   ACCUMULATION_MAX_RETRIES  default 6    (saat skip "data tidak berubah")
#   ACCUMULATION_RETRY_DELAY  default 1800 (detik antar percobaan; ~30 menit)
#   ACCUMULATION_CURL_TIMEOUT default 120
#   ACCUMULATION_FORCE        default false
#
# Backend HARUS berjalan di $ACCUMULATION_API_URL (lihat README: unit backend /
# After=). Keluar:
#   0 sukses atau scan sedang berjalan
#   1 error (token/koneksi/HTTP)
#   2 tidak ada data baru setelah semua percobaan (libur bursa / data telat)
#   3 bukan hari bursa (weekend)

set -uo pipefail

API_URL="${ACCUMULATION_API_URL:-http://localhost:8000}"
TOKEN="${ACCUMULATION_SCAN_TOKEN:-}"
MAX_RETRIES="${ACCUMULATION_MAX_RETRIES:-6}"
RETRY_DELAY="${ACCUMULATION_RETRY_DELAY:-1800}"
CURL_TIMEOUT="${ACCUMULATION_CURL_TIMEOUT:-120}"
FORCE="${ACCUMULATION_FORCE:-false}"

TMP="$(mktemp -t accumulation_scan.XXXXXX)"
trap 'rm -f "$TMP"' EXIT

log() { printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*"; }
die() { log "ERROR: $*"; exit 1; }

[ -n "$TOKEN" ] || die "ACCUMULATION_SCAN_TOKEN belum diset (letakkan di EnvironmentFile luar repo)"
command -v curl >/dev/null 2>&1 || die "curl tidak ditemukan"
command -v python3 >/dev/null 2>&1 || die "python3 tidak ditemukan"

# Hari bursa: lewati Sabtu/Minggu. Libur bursa lain ditangani oleh logika
# "data tidak berubah" (retry) di bawah.
dow="$(date '+%u')"
if [ "$dow" -ge 6 ]; then
  log "SKIP: bukan hari bursa (weekend)"
  exit 3
fi

json_get() { # $1 = ekspresi key, mis. "['data']['status']"
  python3 -c "import sys,json
try:
    d=json.load(sys.stdin)
    print(d$1)
except Exception:
    pass" 2>/dev/null
}

poll_latest() { # tunggu scan selesai; echo JSON latest
  local i body st
  for i in $(seq 1 180); do
    body="$(curl -sS -m 15 "$API_URL/api/accumulation/latest?limit=1" 2>/dev/null || true)"
    st="$(printf '%s' "$body" | json_get "['data']['status']")"
    if [ -n "$st" ] && [ "$st" != "running" ]; then
      printf '%s' "$body"
      return 0
    fi
    sleep 5
  done
  return 1
}

attempt=0
while :; do
  attempt=$((attempt + 1))
  code="$(curl -sS -m "$CURL_TIMEOUT" -o "$TMP" -w '%{http_code}' \
    -X POST "$API_URL/api/accumulation/scan?force=$FORCE" \
    -H "X-Scan-Token: $TOKEN" 2>/dev/null)" || code="000"
  body="$(cat "$TMP" 2>/dev/null || true)"

  case "$code" in
    202)
      sid="$(printf '%s' "$body" | json_get "['scan_id']")"
      log "diterima (202) scan_id=$sid; menunggu selesai..."
      if ! latest="$(poll_latest)"; then
        die "timeout menunggu scan selesai"
      fi
      printf '%s' "$latest" | python3 -c "import sys,json
d=json.load(sys.stdin)['data']
print('DONE scan_date=%s status=%s requests_used=%s quota_remaining=%s signals=%d' % (
  d.get('scan_date'), d.get('status'), d.get('requests_used'),
  d.get('quota_remaining'), len(d.get('signals') or [])))"
      exit 0
      ;;
    200)
      reason="$(printf '%s' "$body" | json_get "['reason']")"
      log "skip: ${reason:-data tidak berubah} (percobaan $attempt/$MAX_RETRIES)"
      if [ "$attempt" -ge "$MAX_RETRIES" ]; then
        log "MENYERAH: data belum berubah setelah $MAX_RETRIES percobaan (mungkin libur bursa / data belum terbit)"
        exit 2
      fi
      sleep "$RETRY_DELAY"
      ;;
    409)
      log "scan sedang berjalan (409); keluar tanpa mengulang"
      exit 0
      ;;
    403)
      die "ditolak 403 (token salah/kosong atau fitur nonaktif)"
      ;;
    000)
      log "gagal koneksi ke $API_URL (percobaan $attempt/$MAX_RETRIES)"
      if [ "$attempt" -ge "$MAX_RETRIES" ]; then die "tidak bisa menghubungi backend"; fi
      sleep "$RETRY_DELAY"
      ;;
    *)
      log "HTTP $code (percobaan $attempt/$MAX_RETRIES)"
      if [ "$attempt" -ge "$MAX_RETRIES" ]; then die "gagal HTTP $code"; fi
      sleep "$RETRY_DELAY"
      ;;
  esac
done
