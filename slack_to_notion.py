# slack_to_notion.py
import os
import requests
from datetime import datetime

# ─── 디버그 로그 ───
print("DEBUG: SLACK_TOKEN startswith xoxb?", os.environ.get("SLACK_TOKEN","").startswith("xoxb-"))
print("DEBUG: SLACK_CHANNEL_ID =", os.environ.get("SLACK_CHANNEL_ID"))
print("DEBUG: SLACK_THREAD_TS  =", os.environ.get("SLACK_THREAD_TS"))
print("DEBUG: NOTION_TOKEN startswith ntn_?", os.environ.get("NOTION_TOKEN","").startswith("ntn_"))
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
    # bot_id 가 있는 bot_message 중 parent_user_id 가 존재하는(=사람이 쓴 답변) 것만 필터
    return [
        m for m in data.get("messages", [])
        if m.get("subtype")=="bot_message" and m.get("parent_user_id")
    ]

def post_to_notion(msg):
    user        = msg['username']             # 예: '공찬혁'
    ts          = msg['ts']                   # 예: '1748047551.009099'
    created_iso = datetime.fromtimestamp(float(ts.split('.')[0])).date().isoformat()

    # 기본 프로퍼티들
    properties = {
        "작성자": {
            "title": [
                {"text": {"content": user}}
            ]
        },
        "날짜": {
            "date": {"start": created_iso}
        }
    }

    # Slack attachments 를 순회하며 프로퍼티 추가
    for att in msg.get("attachments", []):
        key = att.get("title")     # 예: '어제 어떤 작업을 마쳤나요?'
        val = att.get("text")      # 예: '회의록 작성, 노션&슬랙 연동 방법'
        if not key or val is None:
            continue
        # Notion 컬럼 이름과 정확히 일치시켜야 합니다
        properties[key] = {
            "rich_text": [
                {"text": {"content": val}}
            ]
        }

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": properties
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
    print(f"DEBUG: Notion POST status={res.status_code} for user={user}")
    if res.status_code != 200:
        print("DEBUG: Notion response:", res.text)

def main():
    replies = fetch_thread_replies()
    for msg in replies:
        post_to_notion(msg)
    print("DEBUG: sync complete, total posted:", len(replies))

if __name__ == "__main__":
    main()
