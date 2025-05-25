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
    # url 변수가 이 함수 안에서만 유효해야 합니다
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
    return [m for m in data.get("messages", []) if m.get("user")]

def post_to_notion(user, text, ts):
    created = datetime.fromtimestamp(float(ts.split('.')[0])).date().isoformat()
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "작성자":    {"rich_text":[{"text":{"content":user}}]},
            "날짜":      {"date":     {"start":created}}
        },
        "children": [
            {"object":"block","type":"paragraph",
             "paragraph":{"rich_text":[{"text":{"content":text}}]}}
        ]
    }
    res = requests.post(
        "https://api.notion.com/v1/pages",
        json=payload,
        headers={
          "Authorization": f"Bearer {NOTION_TOKEN}",
          "Notion-Version":"2022-06-28"
        }
    )
    print(f"DEBUG: Notion POST status={res.status_code} for user={user}")

def main():
    replies = fetch_thread_replies()
    for msg in replies:
        post_to_notion(msg['user'], msg['text'], msg['ts'])
    print("DEBUG: sync complete, total posted:", len(replies))

if __name__ == "__main__":
    main()
