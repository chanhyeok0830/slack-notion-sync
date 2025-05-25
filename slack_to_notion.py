import os
import requests
from datetime import datetime
from functools import lru_cache

SLACK_TOKEN        = os.environ['SLACK_TOKEN']
SLACK_CHANNEL_ID   = os.environ['SLACK_CHANNEL_ID']
SLACK_THREAD_TS    = os.environ['SLACK_THREAD_TS']
NOTION_TOKEN       = os.environ['NOTION_TOKEN']
NOTION_DATABASE_ID = os.environ['NOTION_DATABASE_ID']

@lru_cache()
def get_user_name(user_id: str) -> str:
    """Slack user ID로 실제 이름을 가져옵니다."""
    resp = requests.get(
        "https://slack.com/api/users.info",
        params={"user": user_id},
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"}
    ).json()
    if resp.get("ok"):
        profile = resp["user"]["profile"]
        return profile.get("real_name") or profile.get("display_name") or profile.get("name")
    return user_id

def fetch_thread_replies():
    data = requests.get(
        "https://slack.com/api/conversations.replies",
        params={"channel": SLACK_CHANNEL_ID, "ts": SLACK_THREAD_TS, "limit": 100},
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"}
    ).json()
    if not data.get("ok"):
        raise RuntimeError(data.get("error"))
    # 첫 메시지는 헤더이므로 제외, attachments가 있는 메시지만 사용
    return [m for m in data["messages"][1:] if m.get("attachments")]

def post_to_notion(msg: dict):
    # user가 없으면 bot 메시지의 username으로 fallback
    user_id = msg.get("user") or msg.get("username", "Unknown")
    user_name = get_user_name(user_id) if msg.get("user") else user_id

    ts = msg["ts"].split(".")[0]
    created = datetime.fromtimestamp(float(ts)).date().isoformat()

    atts = msg["attachments"]
    mood      = atts[0].get("text", "")
    yesterday = atts[1].get("text", "")
    today     = atts[2].get("text", "")
    collab    = atts[3].get("text", "")

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "작성자":   {"title":     [{"text": {"content": user_name}}]},
            "기분":     {"rich_text": [{"text": {"content": mood}}]},
            "어제한 일": {"rich_text": [{"text": {"content": yesterday}}]},
            "오늘할 일": {"rich_text": [{"text": {"content": today}}]},
            "날짜":     {"date":      {"start": created}}
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"text": {"content": f"협업 필요: {collab}"}}
                    ]
                }
            }
        ]
    }

    r = requests.post(
        "https://api.notion.com/v1/pages",
        json=payload,
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
    )
    if r.status_code != 200:
        print("Notion error:", r.text)

def main():
    for msg in fetch_thread_replies():
        post_to_notion(msg)
    print("Sync complete.")

if __name__ == "__main__":
    main()
