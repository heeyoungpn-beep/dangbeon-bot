"""
당번안내봇 - 예배/회의 인도자 알림 봇
오늘 날짜보다 크거나 같은 첫 번째 일정을 찾아 슬랙으로 전송합니다.
"""

import os
import sys
import csv
import io
from datetime import datetime, date

import requests

# ── 환경 변수 (GitHub Secrets 에서 설정) ─────────────────────
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID")
SHEET_ID = os.environ.get(
    "SHEET_ID", "1STKjC7Rfw-X6FIFG1W-30V1xzpjcEKTITrkNONtEvhU"
)
SHEET_GID = os.environ.get("SHEET_GID", "0")

CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
    f"/export?format=csv&gid={SHEET_GID}"
)


def fetch_rows():
    """구글 시트를 CSV로 내려받아 딕셔너리 리스트로 변환합니다."""
    response = requests.get(CSV_URL, timeout=10)
    response.raise_for_status()
    response.encoding = "utf-8"
    reader = csv.DictReader(io.StringIO(response.text))
    return list(reader)


def parse_date(value):
    """'2026.07.13' 등 다양한 날짜 형식을 date 객체로 변환합니다."""
    value = (value or "").strip()
    for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def find_next_schedule(rows, today):
    """오늘보다 크거나 같은 날짜 중 가장 빠른 일정 행을 반환합니다."""
    candidates = []
    for row in rows:
        parsed = parse_date(row.get("날짜", ""))
        if parsed and parsed >= today:
            candidates.append((parsed, row))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def build_message(row):
    """슬랙에 보낼 메시지 텍스트를 만듭니다."""
    week = row.get("주차(기간)", "").strip()
    date_str = row.get("날짜", "").strip()
    worship_leader = row.get("예배 인도자", "").strip() or "미정"
    meeting_leader = row.get("회의 인도자", "").strip() or "미정"

    return (
        f"📅 *당번 안내* ({week or date_str})\n"
        f"• 예배 인도자: *{worship_leader}*\n"
        f"• 회의 인도자: *{meeting_leader}*"
    )


def send_to_slack(text):
    """Slack chat.postMessage API로 메시지를 전송합니다."""
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        print("SLACK_BOT_TOKEN 또는 SLACK_CHANNEL_ID 환경 변수가 설정되지 않았습니다.")
        sys.exit(1)

    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json={"channel": SLACK_CHANNEL_ID, "text": text},
        timeout=10,
    )
    result = response.json()

    if not result.get("ok"):
        print(f"슬랙 전송 실패: {result}")
        sys.exit(1)

    print("슬랙 전송 완료!")


def main():
    today = date.today()
    print(f"오늘 날짜: {today}")

    rows = fetch_rows()
    print(f"시트에서 {len(rows)}개 행을 읽었습니다.")

    schedule = find_next_schedule(rows, today)

    if not schedule:
        print("오늘 이후의 일정을 찾지 못했습니다.")
        send_to_slack("📅 다가오는 당번 일정이 없습니다. 시트를 확인해 주세요.")
        return

    message = build_message(schedule)
    print(message)
    send_to_slack(message)


if __name__ == "__main__":
    main()
