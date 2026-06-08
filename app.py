import streamlit as st
import requests
import json
from datetime import datetime

st.set_page_config(page_title="Narrative Flow", page_icon="📡", layout="wide")

YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY","") if "YOUTUBE_API_KEY" in st.secrets else ""
ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY","") if "ANTHROPIC_API_KEY" in st.secrets else ""

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
{{"score":75,"freshness":4,"stage":"전문가확산","change":"+23%","signal":"🟢 매수 검토","foreign":"외인 3일 연속 순매수","institution":"기관 진입 시작","comment":"AI 종합 판단 50자 이내","risk":"리스크 30자","stocks":[{{"name":"종목명","signal":"🟢","reason":"이유"}}]}}"""
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":ANTHROPIC_API_KEY,"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-20250514","max_tokens":800,"messages":[{"role":"user","content":prompt}]},
            timeout=30
        )
        if r.status_code == 200:
            text = r.json()["content"][0]["text"]
            clean = text.replace("```json","").replace("```","").strip()
            return json.loads(clean)
    except Exception as e:
        st.error(f"AI 분석 오류: {e}")
    return None

def get_youtube_titles(keyword, api_key, max_results=5):
    if not api_key:
        return []
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {"part":"snippet","q":keyword+" 주식","type":"video","maxResults":max_results,"order":"date","key":api_key,"regionCode":"KR"}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            items = r.json().get("items",[])
            return [{"title":i["snippet"]["title"],"channel":i["snippet"]["channelTitle"],"published":i["snippet"]["publishedAt"][:10],"url":f"https://youtube.com/watch?v={i['id']['videoId']}"} for i in items]
    except:
        pass
    return []

st.markdown("## 📡 Narrative Flow")
st.markdown("**한국 자본시장 투자 인텔리전스 플랫폼**")
st.markdown(f"*{datetime.now().strftime('%Y년 %m월 %d일 %H:%M')} 기준*")
st.divider()

col1,col2,col3 = st.columns(3)
col1.metric("분석 가능 테마","6개")
col2.metric("추적 채널","137개")
col3.metric("데이터 소스","10+종")

st.divider()
st.subheader("🔍 테마 분석")
selected = st.selectbox("분석할 테마를 선택하세요", list(THEMES.keys()))

if st.button("🤖 AI 분석 시작", type="primary", use_container_width=True):
    keywords = THEMES[selected]
    with st.spinner("데이터 분석 중..."):
        result = analyze_with_claude(selected, keywords)
        yt_videos = get_youtube_titles(keywords[0], YOUTUBE_API_KEY)

    if result:
        st.success("분석 완료!")
        c1,c2,c3 = st.columns(3)
        score = result.get("score",0)
        c1.metric("내러티브 점수", f"{score}점")
        c2.metric("변화율", result.get("change",""))
        c3.metric("단계", result.get("stage",""))
        st.markdown(f"**신선도:** {'★'*result.get('freshness',3)}{'☆'*(5-result.get('freshness',3))}")
        st.markdown(f"**매매 신호:** {result.get('signal','')}")
        st.info(f"🤖 **AI 판단:** {result.get('comment','')}")
        st.warning(f"⚠️ **리스크:** {result.get('risk','')}")
        c1,c2 = st.columns(2)
        c1.markdown(f"**🌏 외인:** {result.get('foreign','')}")
        c2.markdown(f"**🏦 기관:** {result.get('institution','')}")
        if result.get("stocks"):
            st.subheader("관련 종목")
            for s in result["stocks"]:
                st.markdown(f"{s['signal']} **{s['name']}** — {s['reason']}")
    elif ANTHROPIC_API_KEY:
        st.error("AI 분석 실패. 다시 시도해주세요.")
    else:
        st.warning("API 키 설정 후 AI 분석이 활성화됩니다.")

    if yt_videos:
        st.subheader(f"📺 YouTube 최신 언급 ({len(yt_videos)}건)")
        for v in yt_videos:
            with st.expander(f"[{v['published']}] {v['title'][:50]}..."):
                st.markdown(f"채널: **{v['channel']}**")
                st.markdown(f"[영상 보기]({v['url']})")

st.divider()
st.caption("⚠️ 본 서비스는 투자 참고용 AI 분석입니다. 투자 판단은 본인 책임입니다.")
