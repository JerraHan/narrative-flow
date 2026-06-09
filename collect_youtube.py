"""
YouTube 데이터 자동 수집 스크립트
GitHub Actions에서 매일 오후 4시 실행
"""
import os
import json
import requests
from datetime import datetime, timezone

API_KEY = os.environ.get("YOUTUBE_API_KEY")
OUTPUT_FILE = "data/youtube_latest.json"

def load_channels():
    with open("channels.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    # PLACEHOLDER가 아닌 실제 channel_id만 사용
    return [c for c in data["channels"] if not c["channel_id"].startswith("PLACEHOLDER")]

def get_channel_videos(channel_id, max_results=5):
    """채널의 최신 영상 수집"""
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": API_KEY,
        "channelId": channel_id,
        "part": "snippet",
        "order": "date",
        "maxResults": max_results,
        "type": "video",
        "publishedAfter": "2026-01-01T00:00:00Z"
    }
    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code != 200:
        return []
    items = resp.json().get("items", [])
    videos = []
    for item in items:
        snippet = item.get("snippet", {})
        videos.append({
            "video_id": item["id"].get("videoId", ""),
            "title": snippet.get("title", ""),
            "description": snippet.get("description", "")[:300],
            "published_at": snippet.get("publishedAt", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "channel_id": channel_id,
            "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", "")
        })
    return videos

def get_video_stats(video_ids):
    """영상 조회수/좋아요 수집"""
    if not video_ids:
        return {}
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "key": API_KEY,
        "id": ",".join(video_ids),
        "part": "statistics"
    }
    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code != 200:
        return {}
    stats = {}
    for item in resp.json().get("items", []):
        s = item.get("statistics", {})
        stats[item["id"]] = {
            "view_count": int(s.get("viewCount", 0)),
            "like_count": int(s.get("likeCount", 0)),
            "comment_count": int(s.get("commentCount", 0))
        }
    return stats

def main():
    if not API_KEY:
        print("❌ YOUTUBE_API_KEY 환경변수가 없습니다.")
        return

    channels = load_channels()
    print(f"✅ 수집 대상 채널: {len(channels)}개")

    all_videos = []
    quota_used = 0

    for ch in channels:
        try:
            videos = get_channel_videos(ch["channel_id"])
            if videos:
                # 통계 수집
                video_ids = [v["video_id"] for v in videos if v["video_id"]]
                stats = get_video_stats(video_ids)
                for v in videos:
                    v.update(stats.get(v["video_id"], {}))
                    v["tier"] = ch["tier"]
                    v["category"] = ch["category"]
                all_videos.extend(videos)
                quota_used += 102  # search: 100 + videos: 2
                print(f"  ✓ {ch['name']}: {len(videos)}개")
        except Exception as e:
            print(f"  ✗ {ch['name']}: {e}")

    # 저장
    os.makedirs("data", exist_ok=True)
    output = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "total_videos": len(all_videos),
        "channels_collected": len(channels),
        "quota_used": quota_used,
        "videos": all_videos
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 완료: {len(all_videos)}개 영상 저장 → {OUTPUT_FILE}")
    print(f"📊 예상 쿼터 사용: {quota_used} / 10,000")

if __name__ == "__main__":
    main()
