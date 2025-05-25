import os, requests
from datetime import datetime

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
    data = requests.get(url, params=params, headers=headers).json()
    if not data.get("ok"):
        raise RuntimeError(data.get("error"))
    # bot 메시지는 빼고, 실제 유저 메시지만
    return [m for m in data['messages'] if m.get('user')]

def post_to_notion(user_name, text, ts):
    # ts는 '1641371234.000200' 꼴 → 초 단위로 잘라 ISO 날짜 생성
    date_iso = datetime.fromtimestamp(int(float(ts))).date().isoformat()

    payload = {
      "parent": { "database_id": NOTION_DATABASE_ID },
      "properties": {
        # 갤러리 카드 타이틀로 쓸 속성 (title 타입)
        "작성자": {
          "title": [
            {"text": {"content": user_name}}
          ]
        },
        # 날짜 필드
        "날짜": {
          "date": { "start": date_iso }
        },
        # rich_text 속성들
        "기분": {
          "rich_text": [
            {"text": {"content": extract_answer(text, "오늘 컨디션 어때요?")}}
          ]
        },
        "어제한 일": {
          "rich_text": [
            {"text": {"content": extract_answer(text, "어제 어떤 작업을 마쳤나요?")}}
          ]
        },
        "오늘할 일": {
          "rich_text": [
            {"text": {"content": extract_answer(text, "오늘 어떤 작업을 할거에요?")}}
          ]
        },
      },
      "children": [
        {
          "object": "block",
          "type": "paragraph",
          "paragraph": {
            "rich_text": [
              {"text": {"content": text}}
            ]
          }
        }
      ]
    }

    r = requests.post(
      "https://api.notion.com/v1/pages",
      headers={
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
      },
      json=payload
    )
    print("Notion:", r.status_code, r.text)

def extract_answer(full_text, question):
    """
    Geekbot이 붙여주는 질문 타이틀로 답변을
    분리해서 리턴합니다. 단순 split 활용 예시:
    """
    if question in full_text:
        return full_text.split(question,1)[1].strip()
    return ""

def main():
    replies = fetch_thread_replies()
    for msg in replies:
        post_to_notion(msg['user'], msg['text'], msg['ts'])

if __name__=="__main__":
    main()
