#!/usr/bin/env bash
# pixel-office-presence.sh — 业务仓出勤；经 WikiIndex provider 取址；无大屏静默跳过
# 用法: pixel-office-presence.sh <working|blocked|idle> [summary]
set -euo pipefail

STATE="${1:-}"
SUMMARY="${2:-}"

if [[ -z "${STATE}" ]]; then
  echo "usage: $0 <working|blocked|idle> [summary]" >&2
  exit 1
fi
case "${STATE}" in
  working|blocked|idle) ;;
  *)
    echo "usage: $0 <working|blocked|idle> [summary]" >&2
    exit 1
    ;;
esac

# 仓根：git toplevel 或 cwd
if ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  :
else
  ROOT="${PWD}"
fi
ID="$(basename "${ROOT}")"

resolve_provider() {
  if [[ -n "${PIXEL_OFFICE_PROVIDER:-}" && -f "${PIXEL_OFFICE_PROVIDER}" ]]; then
    echo "${PIXEL_OFFICE_PROVIDER}"
    return
  fi
  local sibling="${ROOT}/../AgentWikiIndex/scripts/pixel-office-provider.sh"
  if [[ -f "${sibling}" ]]; then
    echo "$(cd "$(dirname "${sibling}")" && pwd)/pixel-office-provider.sh"
    return
  fi
  echo ""
}

PROVIDER="$(resolve_provider)"
if [[ -z "${PROVIDER}" ]]; then
  exit 0
fi
# shellcheck disable=SC1090
source "${PROVIDER}"

if ! curl -sf -o /dev/null "${PIXEL_OFFICE_BASE}/api/openapi.json"; then
  exit 0
fi

BODY="$(printf '{"id":"%s","state":"%s"' "${ID}" "${STATE}")"
if [[ -n "${SUMMARY}" ]]; then
  # 粗略转义 summary 内双引号与反斜杠
  ESCAPED="$(printf '%s' "${SUMMARY}" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')"
  BODY="$(printf '%s,"summary":"%s"}' "${BODY}" "${ESCAPED}")"
else
  BODY="$(printf '%s}' "${BODY}")"
fi

curl_args=(-sS -w "\n%{http_code}" -X POST "${PIXEL_OFFICE_BASE}/api/presence" -H "Content-Type: application/json")
if [[ -n "${PIXEL_OFFICE_AUTH_HEADER}" ]]; then
  curl_args+=(-H "${PIXEL_OFFICE_AUTH_HEADER}")
fi
curl_args+=(-d "${BODY}")

RESP="$(curl "${curl_args[@]}" || true)"
HTTP_CODE="$(printf '%s' "${RESP}" | tail -n 1)"
if [[ "${HTTP_CODE}" == "404" ]]; then
  echo "pixel-office-presence: 花名册无 id=${ID}，请先在 WikiIndex 跑 refresh-and-push-catalog.sh" >&2
fi
exit 0
