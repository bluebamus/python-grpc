#!/usr/bin/env bash
#
# 모든 예제 폴더의 FastAPI / Django 샘플 통합 테스트를 순차 실행하고 결과를 요약한다.
#
# 사용법:
#   bash run_all_sample_tests.sh
#
# 참고:
# - 각 샘플은 독립 uv 프로젝트이며 `uv run pytest` 로 실행된다(필요 시 자동 동기화).
# - 같은 예제 폴더의 fastapi/django 통합 테스트는 동일한 gRPC 테스트 포트를 쓰므로
#   반드시 "순차" 실행해야 한다(병렬 실행 시 포트 충돌).
# - 코드가 없는 폴더(15, 18, 20)는 샘플이 없으므로 제외한다.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1

FOLDERS=(
  "1_bookstore" "2_Unary-Streaming" "3_ServerStreaming" "4_Client_Streaming"
  "5_Bidirectional_Streaming" "6_요청취소기법" "7_데이터압축하기" "8_데이터압축기법"
  "9_인터셉터" "10_에러핸들링" "11_서버상태체크-healthcheck"
  "12_서버의정보받아오기-리플렉션" "13_타임아웃설정과통신연결유지기법"
  "14_메타데이터활용하기" "16_TLS보안" "17_재시도기법" "19_asyncio와threading"
)

total_pass=0
total_fail=0
fail_list=()

printf "%-42s %-10s %-10s\n" "FOLDER" "FASTAPI" "DJANGO"
printf "%-42s %-10s %-10s\n" "------" "-------" "------"

for d in "${FOLDERS[@]}"; do
  row_fa="-"; row_dj="-"
  for fw in fastapi django; do
    dir="$ROOT/$d/$fw"
    if [ ! -f "$dir/pyproject.toml" ]; then
      res="MISSING"
    else
      out=$(cd "$dir" && env -u VIRTUAL_ENV uv run pytest -q 2>&1)
      summary=$(echo "$out" | grep -E "passed|failed|error" | tail -1)
      p=$(echo "$summary" | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+"); p=${p:-0}
      f=$(echo "$summary" | grep -oE "[0-9]+ (failed|error)" | grep -oE "[0-9]+" | head -1); f=${f:-0}
      if [ "$f" -gt 0 ]; then
        res="FAIL($p/$((p+f)))"
        fail_list+=("$d/$fw :: $summary")
        total_fail=$((total_fail+1))
      else
        res="OK($p)"
        total_pass=$((total_pass+1))
      fi
    fi
    [ "$fw" = "fastapi" ] && row_fa="$res" || row_dj="$res"
  done
  printf "%-42s %-10s %-10s\n" "$d" "$row_fa" "$row_dj"
done

echo
echo "==== SUMMARY: suites_pass=$total_pass suites_fail=$total_fail ===="
if [ ${#fail_list[@]} -gt 0 ]; then
  echo "---- FAILURES ----"
  for x in "${fail_list[@]}"; do echo "$x"; done
  exit 1
fi
