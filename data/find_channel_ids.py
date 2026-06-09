"""
channels.json의 PLACEHOLDER 채널 ID를 
YouTube API로 자동 검색해서 채우는 스크립트

실행: python find_channel_ids.py
환경변수: YOUTUBE_API_KEY 필요
"""
import json
import requests
import os
import time

API_KEY = os.environ.get("YOUTUBE_API_KEY", "여기에_YouTube_API_키_입력")

def search_channel_id(channel_name):
    """채널명으로 YouTube 채널 ID 검색"""
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": API_KEY,
        "q": channel_name,
        "type": "channel",
        "part": "snippet",
        "maxResults": 1
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        items = resp.json().get("items", [])
        if items:
            channel_id = items[0]["id"]["channelId"]
            title = items[0]["snippet"]["title"]
            return channel_id, title
    except Exception as e:
        print(f"  오류: {e}")
    return None, None

def main():
    # channels.json 로드
    with open("channels.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    channels = data["channels"]
    placeholder_channels = [c for c in channels if c["channel_id"].startswith("PLACEHOLDER")]
    
    print(f"총 {len(placeholder_channels)}개 채널 ID 검색 필요")
    print(f"예상 쿼터 사용: {len(placeholder_channels) * 100} / 10,000")
    print("=" * 50)

    updated = 0
    not_found = []

    for ch in placeholder_channels:
        print(f"검색 중: {ch['name']}...", end=" ")
        channel_id, found_title = search_channel_id(ch["name"])
        
        if channel_id:
            ch["channel_id"] = channel_id
            ch["verified_title"] = found_title
            print(f"✓ {channel_id} ({found_title})")
            updated += 1
        else:
            print("✗ 못 찾음")
            not_found.append(ch["name"])
        
        time.sleep(0.1)  # API 레이트 리밋 방지

    # 저장
    with open("channels_updated.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print(f"✅ 완료: {updated}개 업데이트")
    print(f"❌ 미발견: {len(not_found)}개")
    if not_found:
        print("미발견 채널:", ", ".join(not_found))
    print("\n결과 저장: channels_updated.json")

if __name__ == "__main__":
    main()
