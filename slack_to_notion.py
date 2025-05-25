import os
import requests
from datetime import datetime

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
    data = resp.json()
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
    requests.post(
        "https://api.notion.com/v1/pages",
        json=payload,
        headers={
          "Authorization": f"Bearer {NOTION_TOKEN}",
          "Notion-Version":"2022-06-28"
        }
    )

def main():
    for msg in fetch_thread_replies():
        post_to_notion(msg['user'], msg['text'], msg['ts'])

if __name__=="__main__":
    main()
