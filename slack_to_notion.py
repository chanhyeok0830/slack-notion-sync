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
    # bot 메시지는 제외하고, 실제 사람 혹은 다른 bot이 작성한 update 만 취급
    return [m for m in data.get("messages", []) if m.get("user")]

def post_to_notion(user, text, ts):
    # 슬랙 ts 앞부분(초)로부터 ISO 날짜 문자열 생성
    created = datetime.fromtimestamp(float(ts.split('.')[0])).date().isoformat()

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            # 제목 속성(Title)
            "작성자": {
                "title": [
                    {"text": {"content": user}}
                ]
            },
            # 날짜 속성(Date)
            "날짜": {
                "date": {"start": created}
            },
            # 나머지 속성 모두 Rich Text 타입으로 매핑
            "기분": {
                "rich_text": [
                    {"text": {"content": extract_block(text, "오늘 컨디션 어때요?")}}
                ]
            },
            "어제한 일": {
                "rich_text": [
                    {"text": {"content": extract_block(text, "어제 어떤 작업을 마쳤나요?")}}
                ]
            },
            "오늘할 일": {
                "rich_text": [
                    {"text": {"content": extract_block(text, "오늘 어떤 작업을 할거에요?")}}
                ]
            }
        },
        # 페이지 본문에도 전체 텍스트를 덧붙여 줍니다.
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": text}}]}
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
    print(f"DEBUG: Notion POST status={res.status_code} for user={user}")
    if res.status_code != 200:
        print("Notion response:", res.text)

def extract_block(full_text, question_title):
    """
    Slack 메시지 텍스트에서 qna 형식으로 작성된 블록을
    "질문 제목\n답변 내용" 으로 주고받았다면, 
    질문 제목 뒤의 답변 부분만 분리해 리턴합니다.
    단순하게는 full_text.split(question_title,1)[1] 로 구현 가능합니다.
    """
    parts = full_text.split(question_title, 1)
    if len(parts) == 2:
        # 질문 제목 이후에 개행을 포함한 답변을 추출
        return parts[1].strip()
    return ""  # 못 찾으면 빈 문자열

def main():
    replies = fetch_thread_replies()
    for msg in replies:
        post_to_notion(msg['user'], msg.get('text', ''), msg['ts'])
    print("DEBUG: sync complete, total posted:", len(replies))

if __name__ == "__main__":
    main()
