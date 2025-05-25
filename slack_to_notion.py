import os
import requests
from datetime import datetime

# ─── 디버그 로그 ───
print("DEBUG: SLACK_TOKEN startswith xoxb?", os.environ.get("SLACK_TOKEN", "").startswith("xoxb-"))
print("DEBUG: SLACK_CHANNEL_ID =", os.environ.get("SLACK_CHANNEL_ID"))
print("DEBUG: SLACK_THREAD_TS  =", os.environ.get("SLACK_THREAD_TS"))
print("DEBUG: NOTION_TOKEN startswith ntn_?", os.environ.get("NOTION_TOKEN", "").startswith("ntn_"))
print("DEBUG: NOTION_DATABASE_ID =", os.environ.get("NOTION_DATABASE_ID"))
print("──────────────────────────────────────────────")

SLACK_TOKEN        = os.environ['SLACK_TOKEN']
SLACK_CHANNEL_ID   = os.environ['SLACK_CHANNEL_ID']
SLACK_THREAD_TS    = os.environ['SLACK_THREAD_TS']
NOTION_TOKEN       = os.environ['NOTION_TOKEN']
NOTION_DATABASE_ID = os.environ['NOTION_DATABASE_ID']

def fetch_thread_replies():
    url = "https://slack.com/api/conversations.replies"
    params = {
        "channel": SLACK_CHANNEL_ID,
        "ts": SLACK_THREAD_TS,
        "limit": 100
    }
    headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}
    resp = requests.get(url, params=params, headers=headers)
    data = resp.json()
    print("DEBUG: Slack API response:", data)
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error: {data.get('error')}")
    # 사용자 메시지만 필터링
    return [m for m in data.get("messages", []) if m.get("user")]

def extract_block(full_text: str, question_title: str) -> str:
    """
    '질문 제목\n답변 내용' 형태에서
    question_title 이후의 답변 부분만 리턴
    """
    parts = full_text.split(question_title, 1)
    if len(parts) == 2:
        return parts[1].strip()
    return ""

def post_to_notion(user: str, text: str, ts: str):
    # ts 앞부분(초)만 골라 ISO date 생성
    created = datetime.fromtimestamp(float(ts.split('.')[0])).date().isoformat()

    # Slack 메시지 안에 Q&A 형식으로 들어있는 각 답변 분리
    yesterday_work = extract_block(text, "어제 어떤 작업을 마쳤나요?")
    today_work     = extract_block(text, "오늘 어떤 작업을 할거에요?")
    # (기분 질문은 free-form 이므로 전체 text 를 Rich text 에 그대로 넣습니다)

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "작성자": {
                "title": [{"text": {"content": user}}]
            },
            "기분": {
                "rich_text": [{"text": {"content": text}}]
            },
            "어제한 일": {
                "rich_text": [{"text": {"content": yesterday_work}}]
            },
            "오늘할 일": {
                "rich_text": [{"text": {"content": today_work}}]
            },
            "날짜": {
                "date": {"start": created}
            }
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": text}}]
                }
            }
        ]
    }

    res = requests.post(
        "https://api.notion.com/v1/pages",
        json=payload,
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
    )
    print(f"DEBUG: Notion POST status={res.status_code} response={res.text}")

def main():
    replies = fetch_thread_replies()
    for msg in replies:
        post_to_notion(msg['user'], msg.get('text', ''), msg['ts'])
    print("DEBUG: sync complete, total posted:", len(replies))

if __name__ == "__main__":
    main()
