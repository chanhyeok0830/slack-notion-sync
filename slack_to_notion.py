import os
import requests
from datetime import datetime, timezone
from functools import lru_cache

SLACK_TOKEN        = os.environ['SLACK_TOKEN']
SLACK_CHANNEL_ID   = os.environ['SLACK_CHANNEL_ID']
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

def get_latest_standup_thread_ts() -> str:
    """오늘(UTC 기준) 가장 최근의 Geekbot Daily Standup 헤더 메시지 ts를 찾아 반환합니다."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    resp = requests.get(
        "https://slack.com/api/conversations.history",
        params={
            "channel": SLACK_CHANNEL_ID,
            "oldest": today_start,
            "limit": 200
        },
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"}
    ).json()
    if not resp.get("ok"):
        raise RuntimeError("Slack API error: " + resp.get("error", ""))
    for msg in resp["messages"]:
        # Geekbot 헤더 메시지 안에 "Daily Standup" 텍스트가 들어있으면 ts 반환
        if msg.get("bot_id") and "Daily Standup" in msg.get("text", ""):
            return msg["ts"]
    raise RuntimeError("오늘자 Daily Standup 헤더 메시지를 찾을 수 없습니다.")

def fetch_thread_replies():
    """가장 최근 헤더 ts를 찾아 그 쓰레드의 attachments 메시지들만 반환합니다."""
    thread_ts = get_latest_standup_thread_ts()
    resp = requests.get(
        "https://slack.com/api/conversations.replies",
        params={
            "channel": SLACK_CHANNEL_ID,
            "ts": thread_ts,
            "limit": 100
        },
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"}
    ).json()
    if not resp.get("ok"):
        raise RuntimeError("Slack API error: " + resp.get("error", ""))
    # 첫 번째 메시지는 헤더 자체이므로 제외, attachments 있는 업데이트만
    return [m for m in resp["messages"][1:] if m.get("attachments")]

def post_to_notion(msg: dict):
    """한 명 한 명의 슬랙 업데이트 msg(dict)를 Notion 페이지로 만듭니다."""
    # 작성자 이름
    user_id = msg.get("user") or msg.get("username", "Unknown")
    user_name = get_user_name(user_id) if msg.get("user") else user_id

    # 날짜
    ts_sec = float(msg["ts"].split(".")[0])
    created = datetime.fromtimestamp(ts_sec).date().isoformat()

    # attachments 순서대로 기분·어제·오늘·협업
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
        # 본문에 협업 필요 사항을 덧붙입니다.
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
    replies = fetch_thread_replies()
    for msg in replies:
        post_to_notion(msg)
    print(f"Sync complete. {len(replies)} entries posted.")

if __name__ == "__main__":
    main()
