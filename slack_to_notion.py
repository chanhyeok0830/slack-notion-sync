import os
import requests
from datetime import datetime

# ─── 디버그 로그: 환경변수 제대로 읽히는지 확인 ───
print("DEBUG: SLACK_TOKEN startswith xoxb?", os.environ.get("SLACK_TOKEN", "").startswith("xoxb-"))
print("DEBUG: SLACK_CHANNEL_ID =", os.environ.get("SLACK_CHANNEL_ID"))
print("DEBUG: SLACK_THREAD_TS  =", os.environ.get("SLACK_THREAD_TS"))
print("DEBUG: NOTION_TOKEN startswith secret?", os.environ.get("NOTION_TOKEN", "").startswith("secret_"))
print("DEBUG: NOTION_DATABASE_ID =", os.environ.get("NOTION_DATABASE_ID"))
print("──────────────────────────────────────────────")

SLACK_TOKEN       = os.environ['SLACK_TOKEN']
SLACK_CHANNEL_ID  = os.environ['SLACK_CHANNEL_ID']
SLACK_THREAD_TS   = os.environ['SLACK_THREAD_TS']
NOTION_TOKEN      = os.environ['NOTION_TOKEN']
NOTION_DATABASE_ID= os.environ['NOTION_DATABASE_ID']

def fetch_thread_replies():
    url = "https://slack.com/api/conversations.replies"
    params = {
        "channel": SLACK_CHANNEL_ID,
        "ts": SLACK_THREAD_TS,
        "limit": 100
    }
    headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}
    resp = requests.get(url, params=params, headers=headers)
    print("DEBUG: Slack API HTTP status:", resp.status_code)
    data = resp.json()
    print("DEBUG: Slack API ok:", data.get("ok"), "| messages:", len(data.get("messages", [])))
    return [m for m in data.get("messages", []) if m.get("user")]

def post_to_notion(user, text, ts):
    created = datetime.fromtimestamp(float(ts.split('.')[0])).date().isoformat()
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "작성자": {"rich_text":[{"text":{"content":user}}]},
            "날짜": {"date":{"start":created}}
        },
        "children":[
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
    resp = requests.get(url, params=params, headers=headers)
    data = resp.json()
    print("DEBUG: Slack API response:", data)
    return [m for m in data.get("messages", []) if m.get("user")]


if __name__=="__main__":
    main()
