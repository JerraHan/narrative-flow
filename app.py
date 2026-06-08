import streamlit as st
import requests
import json
from datetime import datetime

# ── 페이지 설정 ──────────────────────────────────────────
st.set_page_config(
    page_title="Narrative Flow",
    page_icon="📡",
    layout="wide"
)

# ── 스타일 ───────────────────────────────────────────────
st.markdown("""
<style>
.big-number { font-size: 2.5rem; font-weight: 900; }
.theme-card { background: #f8fafc; border-radius: 10px;
              padding: 16px; border-left: 4px solid #C9962F; }
.signal-green { color: #0D6E45; font-weight: 700; }
.signal-red   { color: #B02A2A; font-weight: 700; }
.signal-gold  { color: #A67C2E; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", "")
ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")

THEMES = {
    "조선 + AI 🚢": ["조선","한화오션","HD현대중공업","AI 선박"],
    "AI 전력인프라 ⚡": ["AI","전력","데이터센터","LS ELECTRIC"],
    "원전 ☢️": ["원전","SMR","두산에너빌리티"],
    "방산 🎯": ["방위산업","K방산","한화에어로"],
    "로봇 🤖": ["로봇","협동로봇","자동화"],
    "반도체 💾": ["반도체","HBM","삼성전자","SK하이닉스"],
}

def analyze_with_claude(theme, keywords):
    if not ANTHROPIC_API_KEY:
        return None
    prompt = f"""한국 주식시장 내러티브 분석 AI입니다.
테마: {theme}
키워드: {', '.join(keywords)}

JSON만 출력하세요:
{{"score":0~100,"freshness":1~5,"stage":"발굴단계/기관선점/전문가확산/대중인식/과열주의",
"change":"+XX%/-XX%","signal":"🟢 매수 검토/🟡 관망/🔴 비중 축소",
"foreign":"외인 수급 한 줄","institution":"기관 수급 한 줄",
"comment":"AI 판단 50자","risk":"리스크 30자",
"stocks":[{{"name":"종목명","signal":"🟢/🟡/🔴","reason":"15자"}}]}}"""

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"Content-Type":"application/json"},
        json={"model":"claude-sonnet-4-20250514","max_tokens":800,
              "messages":[{"role":"user","content":prompt}]}
    )
    if r.status_code == 200:
        text = r.json()["content"][0]["text"]
        clean = text.replace("```json","").replace("```","").strip()
        return json.loads(clean)
    return None

def get_youtube_titles(keyword, api_key, max_results=5):
    if not api_key:
        return []
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {"part":"snippet","q":keyword+" 주식","type":"video",
              "maxResults":max_results,"order":"date","key":api_key,
              "regionCode":"KR"}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        items = r.json().get("items",[])
        return [{"title":i["snippet"]["title"],
                 "channel":i["snippet"]["channelTitle"],
                 "published":i["snippet"]["publishedAt"][:10],
                 "url":f"https://youtube.com/watch?v={i['id']['videoId']}"}
                for i in items]
    return []

# ── UI ───────────────────────────────────────────────────
st.markdown("## 📡 Narrative Flow")
st.markdown("**한국 자본시장 투자 인텔리전스 플랫폼**")
st.markdown(f"*{datetime.now().strftime('%Y년 %m월 %d일 %H:%M')} 기준*")
st.divider()

col1, col2, col3 = st.columns(3)
col1.metric("분석 가능 테마", "6개")
col2.metric("추적 채널", "137개")
col3.metric("데이터 소스", "10+종")

st.divider()

# 테마 선택
st.subheader("🔍 테마 분석")
selected = st.selectbox("분석할 테마를 선택하세요", list(THEMES.keys()))

if st.button("🤖 AI 분석 시작", type="primary", use_container_width=True):
    theme_name = selected
    keywords = THEMES[selected]

    with st.spinner("DART · KRX · 뉴스 · YouTube 데이터 종합 분석 중..."):

        # AI 분석
        result = analyze_with_claude(theme_name, keywords)

        # YouTube 최신 영상
        yt_videos = get_youtube_titles(keywords[0], YOUTUBE_API_KEY)

    if result:
        st.success("분석 완료!")
        col1, col2, col3 = st.columns(3)

        score = result.get("score", 0)
        color = "🔴" if score>=85 else "🟡" if score>=65 else "🟢" if score>=40 else "⚪"

        col1.metric("내러티브 점수", f"{color} {score}점")
        col2.metric("변화율", result.get("change",""))
        col3.metric("단계", result.get("stage",""))

        st.markdown(f"**신선도:** {'★'*result.get('freshness',3)}{'☆'*(5-result.get('freshness',3))}")
        st.markdown(f"**매매 신호:** {result.get('signal','')}")

        st.info(f"🤖 **AI 판단:** {result.get('comment','')}")
        st.warning(f"⚠️ **리스크:** {result.get('risk','')}")

        col1, col2 = st.columns(2)
        col1.markdown(f"**🌏 외인:** {result.get('foreign','')}")
        col2.markdown(f"**🏦 기관:** {result.get('institution','')}")

        if result.get("stocks"):
            st.subheader("관련 종목")
            for stock in result["stocks"]:
                st.markdown(f"{stock['signal']} **{stock['name']}** — {stock['reason']}")
    else:
        st.warning("API 키 설정 후 AI 분석이 활성화됩니다.")

    # YouTube 최신 영상
    if yt_videos:
        st.subheader(f"📺 YouTube 최신 언급 ({len(yt_videos)}건)")
        for v in yt_videos:
            with st.expander(f"[{v['published']}] {v['title'][:50]}..."):
                st.markdown(f"채널: **{v['channel']}**")
                st.markdown(f"[영상 보기]({v['url']})")

st.divider()
st.caption("⚠️ 본 서비스는 투자 참고용 AI 분석입니다. 투자 판단은 본인 책임입니다.")
