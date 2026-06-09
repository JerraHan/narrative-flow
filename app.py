import streamlit as st
import anthropic
import json
import feedparser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── 페이지 설정 ──────────────────────────────────────────
st.set_page_config(
    page_title="내러티브 흐름 | 투자 인텔리전스",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.main-title { font-size: 2rem; font-weight: 700; color: #0a0a0a; letter-spacing: -0.5px; }
.sub-title  { font-size: 1rem; color: #666; margin-top: -8px; }
.score-card {
    background: #fff; border: 1px solid #e8e8e8; border-radius: 12px;
    padding: 20px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.score-num  { font-size: 2.5rem; font-weight: 700; }
.score-lbl  { font-size: 0.8rem; color: #888; margin-top: 4px; }
.positive   { color: #e63946; }
.negative   { color: #1d6fa4; }
.neutral    { color: #888; }
.tag { display: inline-block; background: #f0f4ff; color: #3355cc; border-radius: 20px; padding: 3px 12px; font-size: 0.78rem; margin: 3px; }
.news-card { background: #fff; border: 1px solid #e8e8e8; border-radius: 10px; padding: 14px 16px; margin: 8px 0; }
.grade-A { background:#fff0f0; color:#c0392b; border-radius:4px; padding:1px 6px; font-size:0.7rem; font-weight:700; }
.grade-B { background:#fff8e1; color:#e67e22; border-radius:4px; padding:1px 6px; font-size:0.7rem; font-weight:700; }
.grade-C { background:#f0f0f0; color:#666; border-radius:4px; padding:1px 6px; font-size:0.7rem; font-weight:700; }
.integrated-score { font-size: 4rem; font-weight: 900; text-align: center; padding: 20px; border-radius: 16px; }
.signal-strong-buy  { background: #fff0f0; color: #c0392b; }
.signal-buy         { background: #fff5f5; color: #e74c3c; }
.signal-neutral     { background: #f8f8f8; color: #666; }
.signal-sell        { background: #f0f4ff; color: #2980b9; }
.signal-strong-sell { background: #e8f0ff; color: #1a5276; }
</style>
""", unsafe_allow_html=True)

# ── API 키 (Secrets 우선, 없으면 사이드바) ───────────────
def get_api_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except:
        return st.session_state.get("manual_api_key", "")

# ── RSS 함수 ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_rss_list():
    try:
        with open("news_rss.json", "r", encoding="utf-8") as f:
            return json.load(f)["media"]
    except:
        return []

def fetch_single_rss(media):
    try:
        feed = feedparser.parse(media["rss"])
        articles = []
        for entry in feed.entries[:3]:
            articles.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", "")[:200] if entry.get("summary") else "",
                "source": media["name"], "grade": media["grade"], "category": media["category"]
            })
        return articles
    except:
        return []

@st.cache_data(ttl=600)
def fetch_rss_news(grade_filter="A", category_filter="전체", max_sources=20):
    media_list = load_rss_list()
    if grade_filter != "전체": media_list = [m for m in media_list if m["grade"] == grade_filter]
    if category_filter != "전체": media_list = [m for m in media_list if m["category"] == category_filter]
    media_list = media_list[:max_sources]
    all_articles = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_single_rss, m): m for m in media_list}
        for future in as_completed(futures):
            all_articles.extend(future.result())
    return all_articles

# ── YouTube 데이터 로드 ───────────────────────────────────
@st.cache_data(ttl=600)
def load_youtube_data():
    try:
        with open("data/youtube_latest.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

# ── 주가 함수 ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_stock_data(ticker, period_days=30):
    try:
        import FinanceDataReader as fdr
        end = datetime.today()
        start = end - timedelta(days=period_days)
        df = fdr.DataReader(ticker, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        return df if not df.empty else None
    except:
        return None

# ── 통합 점수 계산 ────────────────────────────────────────
def calculate_integrated_score(news_score, youtube_score, news_weight=0.6, youtube_weight=0.4):
    return round(news_score * news_weight + youtube_score * youtube_weight)

def score_to_signal(score):
    if score >= 60:   return "강한 매수", "signal-strong-buy", "🔴"
    if score >= 20:   return "매수", "signal-buy", "🟠"
    if score >= -20:  return "중립", "signal-neutral", "⚪"
    if score >= -60:  return "매도", "signal-sell", "🔵"
    return "강한 매도", "signal-strong-sell", "🟣"

# ── 사이드바 ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 설정")
    try:
        st.secrets["ANTHROPIC_API_KEY"]
        st.success("✅ API 키 자동 로드됨")
    except:
        manual_key = st.text_input("Anthropic API 키", type="password", placeholder="sk-ant-...")
        st.session_state["manual_api_key"] = manual_key
    st.markdown("---")
    analysis_depth = st.select_slider("분석 깊이", options=["빠른 분석", "기본 분석", "심층 분석"], value="기본 분석")
    show_keywords = st.checkbox("키워드 추출", value=True)
    show_risk = st.checkbox("리스크 신호 감지", value=True)
    st.markdown("---")
    st.info("📺 YouTube 채널 137개\n\n📰 뉴스 미디어 175개")
    st.caption("Narrative Flow v0.4 MVP")

# ── 헤더 ─────────────────────────────────────────────────
st.markdown('<p class="main-title">📊 내러티브 흐름</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">한국 주식시장 투자 인텔리전스 플랫폼</p>', unsafe_allow_html=True)
st.markdown("---")

tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎯 통합 점수", "🔍 내러티브 분석", "📰 뉴스 RSS", "📈 주가 연동", "🔥 트렌드 탐지", "📋 분석 기록"])

# ════════════════════════════════════════════════════════
# TAB 0 : 통합 점수 (메인 대시보드)
# ════════════════════════════════════════════════════════
with tab0:
    st.subheader("🎯 뉴스 + YouTube 통합 내러티브 점수")
    st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    col_settings, col_run = st.columns([3, 1])
    with col_settings:
        target_keyword = st.text_input("분석 키워드 (종목/테마)", placeholder="삼성전자, 2차전지, 반도체, KOSPI...")
    with col_run:
        st.markdown("<br>", unsafe_allow_html=True)
        run_integrated = st.button("🚀 통합 분석", type="primary", use_container_width=True)

    # 가중치 설정
    with st.expander("⚙️ 가중치 설정"):
        col_w1, col_w2 = st.columns(2)
        with col_w1: news_weight = st.slider("뉴스 가중치", 0.0, 1.0, 0.6, 0.1)
        with col_w2: youtube_weight = round(1 - news_weight, 1); st.metric("YouTube 가중치", f"{youtube_weight}")

    if run_integrated:
        api_key = get_api_key()
        if not api_key:
            st.error("⚠️ API 키를 입력해 주세요.")
        else:
            with st.spinner("뉴스 + YouTube 데이터 수집 및 분석 중..."):
                # 1. 뉴스 수집
                news_articles = fetch_rss_news("A", "전체", 15)
                if target_keyword:
                    news_articles = [a for a in news_articles if target_keyword in a["title"] or target_keyword in a.get("summary","")]
                news_headlines = "\n".join([f"- {a['title']} ({a['source']})" for a in news_articles[:15]])

                # 2. YouTube 데이터 로드
                yt_data = load_youtube_data()
                yt_titles = []
                if yt_data and yt_data.get("videos"):
                    videos = yt_data["videos"]
                    if target_keyword:
                        videos = [v for v in videos if target_keyword in v.get("title","") or target_keyword in v.get("description","")]
                    yt_titles = [f"- {v['title']} ({v.get('channel_title','')})" for v in videos[:15]]

                try:
                    client = anthropic.Anthropic(api_key=api_key)

                    # 뉴스 분석
                    news_prompt = f"""한국 주식시장 투자자 관점으로 아래 뉴스를 분석하세요.
{'키워드: ' + target_keyword if target_keyword else '전체 시장 분석'}
뉴스: {news_headlines if news_headlines else '수집된 뉴스 없음'}
JSON만: {{"score":-100에서100정수,"sentiment":"긍정"|"부정"|"혼조"|"중립","hot_topics":["t1","t2","t3"],"summary":"2문장"}}"""

                    news_resp = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=400,
                        messages=[{"role":"user","content":news_prompt}])
                    news_raw = news_resp.content[0].text.strip()
                    if news_raw.startswith("```"):
                        news_raw = news_raw.split("```")[1]
                        if news_raw.startswith("json"): news_raw = news_raw[4:]
                    news_result = json.loads(news_raw)

                    # YouTube 분석
                    yt_score = 0
                    yt_result = {"score": 0, "sentiment": "데이터 없음", "hot_topics": [], "summary": "YouTube 데이터 없음"}
                    if yt_titles:
                        yt_prompt = f"""한국 주식 YouTube 영상 제목들을 투자자 관점으로 분석하세요.
{'키워드: ' + target_keyword if target_keyword else '전체'}
영상: {chr(10).join(yt_titles)}
JSON만: {{"score":-100에서100정수,"sentiment":"긍정"|"부정"|"혼조"|"중립","hot_topics":["t1","t2","t3"],"summary":"2문장"}}"""
                        yt_resp = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=400,
                            messages=[{"role":"user","content":yt_prompt}])
                        yt_raw = yt_resp.content[0].text.strip()
                        if yt_raw.startswith("```"):
                            yt_raw = yt_raw.split("```")[1]
                            if yt_raw.startswith("json"): yt_raw = yt_raw[4:]
                        yt_result = json.loads(yt_raw)

                    # 통합 점수
                    n_score = news_result.get("score", 0)
                    y_score = yt_result.get("score", 0)
                    integrated = calculate_integrated_score(n_score, y_score, news_weight, youtube_weight)
                    signal, signal_class, emoji = score_to_signal(integrated)

                    st.session_state["integrated_result"] = {
                        "integrated": integrated, "news_score": n_score, "yt_score": y_score,
                        "signal": signal, "signal_class": signal_class, "emoji": emoji,
                        "news_result": news_result, "yt_result": yt_result,
                        "keyword": target_keyword or "전체 시장",
                        "news_count": len(news_articles), "yt_count": len(yt_titles),
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    }

                except Exception as e:
                    st.error(f"분석 오류: {e}")

    # 결과 표시
    if "integrated_result" in st.session_state:
        r = st.session_state["integrated_result"]
        st.markdown("---")

        # 메인 통합 점수
        integrated = r["integrated"]
        score_color = "#e63946" if integrated > 20 else ("#1d6fa4" if integrated < -20 else "#666")
        st.markdown(f"""
        <div style="background:#fff;border:2px solid {score_color};border-radius:20px;padding:30px;text-align:center;margin:10px 0">
            <div style="font-size:0.9rem;color:#888;margin-bottom:8px">📊 {r['keyword']} 통합 내러티브 점수</div>
            <div style="font-size:4rem;font-weight:900;color:{score_color}">{integrated:+d}</div>
            <div style="font-size:1.3rem;font-weight:700;color:{score_color};margin-top:8px">{r['emoji']} {r['signal']}</div>
            <div style="font-size:0.75rem;color:#aaa;margin-top:8px">{r['timestamp']} 기준</div>
        </div>
        """, unsafe_allow_html=True)

        # 세부 점수
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            ns = r["news_score"]
            nc = "#e63946" if ns > 20 else ("#1d6fa4" if ns < -20 else "#888")
            st.markdown(f'<div class="score-card"><div class="score-num" style="color:{nc}">{ns:+d}</div><div class="score-lbl">📰 뉴스 점수<br><small>{r["news_count"]}개 기사</small></div></div>', unsafe_allow_html=True)
        with c2:
            ys = r["yt_score"]
            yc = "#e63946" if ys > 20 else ("#1d6fa4" if ys < -20 else "#888")
            st.markdown(f'<div class="score-card"><div class="score-num" style="color:{yc}">{ys:+d}</div><div class="score-lbl">📺 YouTube 점수<br><small>{r["yt_count"]}개 영상</small></div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.2rem;padding-top:10px">{int(news_weight*100)}% / {int(youtube_weight*100)}%</div><div class="score-lbl">뉴스 / YouTube 가중치</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 뉴스 vs YouTube 분석 비교
        col_n, col_y = st.columns(2)
        with col_n:
            st.markdown("**📰 뉴스 분석**")
            st.info(r["news_result"].get("summary", ""))
            st.markdown("**핫 토픽**")
            st.markdown(" ".join([f'<span class="tag">{t}</span>' for t in r["news_result"].get("hot_topics",[])]), unsafe_allow_html=True)
        with col_y:
            st.markdown("**📺 YouTube 분석**")
            st.info(r["yt_result"].get("summary", ""))
            st.markdown("**핫 토픽**")
            st.markdown(" ".join([f'<span class="tag">{t}</span>' for t in r["yt_result"].get("hot_topics",[])]), unsafe_allow_html=True)

        # 점수 히스토리 저장
        if "score_history" not in st.session_state:
            st.session_state["score_history"] = []
        st.session_state["score_history"].append({
            "time": r["timestamp"], "keyword": r["keyword"],
            "integrated": integrated, "news": r["news_score"], "youtube": r["yt_score"], "signal": r["signal"]
        })

        # 점수 히스토리 차트
        if len(st.session_state["score_history"]) > 1:
            st.markdown("---")
            st.markdown("**📈 점수 히스토리**")
            import pandas as pd
            hist_df = pd.DataFrame(st.session_state["score_history"])
            st.line_chart(hist_df.set_index("time")[["integrated", "news", "youtube"]])

# ════════════════════════════════════════════════════════
# TAB 1 : 내러티브 분석
# ════════════════════════════════════════════════════════
with tab1:
    st.subheader("YouTube / 뉴스 콘텐츠 내러티브 분석")
    col_in, col_ex = st.columns([2, 1])
    with col_in:
        content_input = st.text_area("분석할 콘텐츠 입력", height=180,
            placeholder="YouTube 영상 제목, 설명, 뉴스 기사 내용 등을 붙여넣으세요.")
        ticker_input = st.text_input("관련 종목 (선택)", placeholder="예: 005930, 삼성전자")
    with col_ex:
        st.markdown("**예시 콘텐츠**")
        examples = [
            "삼성전자 목표주가 10만원 상향, 지금이 매수 타이밍",
            "코스피 2500 붕괴 임박? 외국인 순매도 지속",
            "2차전지 섹터 반등 신호 – 기관 대량 매집 포착",
            "금리 인하 기대감에 부동산 관련주 급등 전망",
        ]
        for ex in examples:
            if st.button(f"📌 {ex[:20]}...", key=ex, use_container_width=True):
                st.session_state["example_text"] = ex
    if "example_text" in st.session_state:
        content_input = st.session_state["example_text"]

    if st.button("🚀 AI 분석 시작", type="primary", use_container_width=True):
        api_key = get_api_key()
        if not api_key: st.error("⚠️ API 키를 입력해 주세요.")
        elif not content_input.strip(): st.warning("콘텐츠를 입력해 주세요.")
        else:
            with st.spinner("분석 중..."):
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    depth_map = {"빠른 분석": "간결하게 핵심만", "기본 분석": "균형 있게", "심층 분석": "상세하고 깊이 있게"}
                    prompt = f"""한국 주식시장 전문 투자 분석 AI로서 {depth_map[analysis_depth]} 분석.
[콘텐츠] {content_input}
{f"[종목] {ticker_input}" if ticker_input else ""}
JSON만: {{"sentiment_score":-100에서100정수,"sentiment_label":"강한 매수 신호"|"매수 신호"|"중립"|"매도 신호"|"강한 매도 신호","confidence":0에서100정수,"narrative_type":"실적 기대"|"테마/섹터"|"매크로"|"리스크"|"내부자/기관"|"기타","keywords":["k1","k2","k3","k4","k5"],"risk_signals":["r1","r2"],"summary":"2-3문장","investment_implication":"1-2문장","data_quality":"높음"|"보통"|"낮음"}}"""
                    response = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=1000,
                        messages=[{"role":"user","content":prompt}])
                    raw = response.content[0].text.strip()
                    if raw.startswith("```"):
                        raw = raw.split("```")[1]
                        if raw.startswith("json"): raw = raw[4:]
                    result = json.loads(raw)
                    st.markdown("---"); st.markdown("### 📊 분석 결과")
                    score = result.get("sentiment_score", 0)
                    sc = "positive" if score > 20 else ("negative" if score < -20 else "neutral")
                    label = result.get("sentiment_label", "")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.markdown(f'<div class="score-card"><div class="score-num {sc}">{score:+d}</div><div class="score-lbl">내러티브 점수</div></div>', unsafe_allow_html=True)
                    with c2: st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.3rem;padding-top:8px">{label}</div><div class="score-lbl">신호 유형</div></div>', unsafe_allow_html=True)
                    with c3: st.markdown(f'<div class="score-card"><div class="score-num">{result.get("confidence",0)}%</div><div class="score-lbl">신뢰도</div></div>', unsafe_allow_html=True)
                    with c4: st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.1rem;padding-top:12px">{result.get("narrative_type","")}</div><div class="score-lbl">내러티브 유형</div></div>', unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    if ticker_input:
                        ticker_code = ticker_input.strip().replace("삼성전자","005930").replace("SK하이닉스","000660").replace("현대차","005380")
                        df = get_stock_data(ticker_code, 5)
                        if df is not None and not df.empty:
                            latest = df.iloc[-1]; prev = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
                            chg_pct = ((latest["Close"] - prev["Close"]) / prev["Close"]) * 100
                            arrow = "▲" if chg_pct > 0 else "▼"
                            sc1, sc2, sc3 = st.columns(3)
                            with sc1: st.metric("현재가", f"{latest['Close']:,.0f}원")
                            with sc2: st.metric("등락률", f"{arrow}{abs(chg_pct):.2f}%")
                            with sc3: st.metric("거래량", f"{latest['Volume']:,}")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**📝 핵심 요약**"); st.info(result.get("summary",""))
                        st.markdown("**💡 투자 시사점**"); st.success(result.get("investment_implication",""))
                    with col_b:
                        if show_keywords:
                            st.markdown("**🏷️ 핵심 키워드**")
                            st.markdown(" ".join([f'<span class="tag">{k}</span>' for k in result.get("keywords",[])]), unsafe_allow_html=True)
                        if show_risk and result.get("risk_signals"):
                            st.markdown("<br>**⚠️ 리스크 신호**", unsafe_allow_html=True)
                            for r2 in result.get("risk_signals",[]):
                                if r2: st.warning(f"• {r2}")
                    if "history" not in st.session_state: st.session_state["history"] = []
                    st.session_state["history"].append({"time": datetime.now().strftime("%H:%M:%S"),
                        "content": content_input[:50]+"...", "score": score, "label": label, "ticker": ticker_input or "-"})
                except Exception as e:
                    st.error(f"오류: {e}")

# ════════════════════════════════════════════════════════
# TAB 2 : 뉴스 RSS
# ════════════════════════════════════════════════════════
with tab2:
    st.subheader("📰 실시간 뉴스 RSS 수집")
    media_list = load_rss_list()
    categories = ["전체"] + sorted(list(set(m["category"] for m in media_list)))
    cf1, cf2, cf3 = st.columns(3)
    with cf1: gf = st.selectbox("등급 필터", ["A급만","A+B급","전체"], index=0)
    with cf2: catf = st.selectbox("카테고리", categories)
    with cf3: maxs = st.slider("소스 수", 5, 30, 15)
    gmap = {"A급만":"A","A+B급":"AB","전체":"전체"}
    cb1, cb2 = st.columns(2)
    with cb1: fb = st.button("📡 뉴스 수집", type="primary", use_container_width=True)
    with cb2: ab = st.button("🤖 AI 분석", use_container_width=True)
    if fb:
        with st.spinner("수집 중..."):
            sg = gmap[gf]
            arts = fetch_rss_news("A",catf,maxs//2)+fetch_rss_news("B",catf,maxs//2) if sg=="AB" else fetch_rss_news(sg,catf,maxs)
            st.session_state["rss_articles"] = arts
            st.success(f"✅ {len(arts)}개 수집 완료")
    if "rss_articles" in st.session_state and st.session_state["rss_articles"]:
        arts = st.session_state["rss_articles"]
        kw = st.text_input("🔎 키워드 검색", placeholder="삼성전자, 반도체...")
        if kw: arts = [a for a in arts if kw in a["title"] or kw in a.get("summary","")]
        st.markdown(f"**총 {len(arts)}개**")
        for a in arts[:50]:
            gc = f"grade-{a['grade']}"; pub = a["published"][:16] if a["published"] else ""
            sm = f'<div style="font-size:0.82rem;color:#555;margin-top:6px">{a["summary"]}</div>' if a["summary"] else ""
            st.markdown(f'<div class="news-card"><div><span class="{gc}">{a["grade"]}</span>&nbsp;<a href="{a["link"]}" target="_blank" style="color:#0a0a0a;text-decoration:none;font-weight:600">{a["title"]}</a></div><div style="font-size:0.75rem;color:#999;margin-top:4px">📰 {a["source"]} · {pub}</div>{sm}</div>', unsafe_allow_html=True)
    if ab:
        api_key = get_api_key()
        if not api_key: st.error("⚠️ API 키 필요")
        elif "rss_articles" not in st.session_state: st.warning("먼저 수집해 주세요.")
        else:
            arts2 = st.session_state["rss_articles"][:20]
            hl = "\n".join([f"- {a['title']} ({a['source']})" for a in arts2])
            with st.spinner("분석 중..."):
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    resp = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=800,
                        messages=[{"role":"user","content":f"뉴스 분석:\n{hl}\nJSON만:\n{{\"market_sentiment\":\"긍정\"|\"부정\"|\"혼조\"|\"중립\",\"sentiment_score\":-100에서100정수,\"dominant_themes\":[\"t1\",\"t2\",\"t3\"],\"hot_sectors\":[\"s1\",\"s2\"],\"summary\":\"3문장\",\"investment_signal\":\"2문장\"}}"}])
                    raw2 = resp.content[0].text.strip()
                    if raw2.startswith("```"):
                        raw2 = raw2.split("```")[1]
                        if raw2.startswith("json"): raw2 = raw2[4:]
                    res2 = json.loads(raw2)
                    sc2 = res2.get("sentiment_score",0)
                    scc = "positive" if sc2>0 else ("negative" if sc2<0 else "neutral")
                    c1,c2 = st.columns(2)
                    with c1: st.markdown(f'<div class="score-card"><div class="score-num {scc}">{sc2:+d}</div><div class="score-lbl">시장 점수</div></div>', unsafe_allow_html=True)
                    with c2: st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.4rem;padding-top:6px">{res2.get("market_sentiment","")}</div><div class="score-lbl">시장 심리</div></div>', unsafe_allow_html=True)
                    st.markdown(" ".join([f'<span class="tag">{s}</span>' for s in res2.get("hot_sectors",[])]), unsafe_allow_html=True)
                    st.info(res2.get("summary","")); st.success(res2.get("investment_signal",""))
                except Exception as e: st.error(f"오류: {e}")

# ════════════════════════════════════════════════════════
# TAB 3 : 주가 연동
# ════════════════════════════════════════════════════════
with tab3:
    st.subheader("📈 실시간 주가 조회 & AI 기술적 분석")
    quick_stocks = {"삼성전자":"005930","SK하이닉스":"000660","현대차":"005380","POSCO홀딩스":"005490","셀트리온":"068270","카카오":"035720","네이버":"035420","한화에어로":"012450","LG에너지솔루션":"373220","에코프로":"086520"}
    cols = st.columns(5)
    for i,(name,code) in enumerate(quick_stocks.items()):
        with cols[i%5]:
            if st.button(name, key=f"q_{code}", use_container_width=True):
                st.session_state["sel_ticker"] = code; st.session_state["sel_name"] = name
    st.markdown("---")
    cs1, cs2 = st.columns([2,1])
    with cs1: ticker = st.text_input("종목코드", value=st.session_state.get("sel_ticker","005930"))
    with cs2: period = st.selectbox("기간", ["1개월","3개월","6개월","1년"])
    pmap = {"1개월":30,"3개월":90,"6개월":180,"1년":365}
    if st.button("📊 주가 조회", type="primary", use_container_width=True):
        with st.spinner("조회 중..."):
            df = get_stock_data(ticker, pmap[period])
            if df is not None:
                st.session_state["stock_df"] = df; st.session_state["stock_ticker"] = ticker
                st.success(f"✅ {ticker} {len(df)}일 데이터 로드")
            else: st.error("데이터 없음. 종목코드 확인해 주세요.")
    if "stock_df" in st.session_state:
        df = st.session_state["stock_df"]
        latest = df.iloc[-1]; prev = df.iloc[-2] if len(df)>1 else df.iloc[-1]
        chg = latest["Close"]-prev["Close"]; chg_p = (chg/prev["Close"])*100
        arrow = "▲" if chg_p>0 else "▼"
        m1,m2,m3,m4 = st.columns(4)
        with m1: st.metric("현재가", f"{latest['Close']:,.0f}원")
        with m2: st.metric("등락률", f"{arrow}{abs(chg_p):.2f}%", delta=f"{chg:+,.0f}원")
        with m3: st.metric("거래량", f"{latest['Volume']:,}")
        with m4:
            pc = ((latest["Close"]-df.iloc[0]["Close"])/df.iloc[0]["Close"])*100
            st.metric("기간 수익률", f"{pc:+.2f}%")
        st.line_chart(df[["Close"]].rename(columns={"Close":"종가"}))
        st.bar_chart(df[["Volume"]].rename(columns={"Volume":"거래량"}))
        api_key = get_api_key()
        if api_key and st.button("🤖 AI 기술적 분석", use_container_width=True):
            with st.spinner("분석 중..."):
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    recent = df.tail(10)[["Close","Volume"]].to_string()
                    resp = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=600,
                        messages=[{"role":"user","content":f"종목 {ticker} 주가 분석.\n최근10일:{recent}\nJSON만:\n{{\"trend\":\"상승추세\"|\"하락추세\"|\"횡보\",\"trend_strength\":\"강함\"|\"보통\"|\"약함\",\"support_level\":정수,\"resistance_level\":정수,\"volume_signal\":\"매수세\"|\"관망\"|\"변곡점 가능\",\"technical_signal\":\"매수\"|\"매도\"|\"중립\",\"summary\":\"2문장\",\"caution\":\"1문장\"}}"}])
                    raw3 = resp.content[0].text.strip()
                    if raw3.startswith("```"):
                        raw3 = raw3.split("```")[1]
                        if raw3.startswith("json"): raw3 = raw3[4:]
                    res3 = json.loads(raw3)
                    ta1,ta2,ta3 = st.columns(3)
                    with ta1: st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.4rem;padding-top:6px">{res3.get("trend","")}</div><div class="score-lbl">추세</div></div>', unsafe_allow_html=True)
                    with ta2: st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.4rem;padding-top:6px">{res3.get("technical_signal","")}</div><div class="score-lbl">기술적 신호</div></div>', unsafe_allow_html=True)
                    with ta3: st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.4rem;padding-top:6px">{res3.get("trend_strength","")}</div><div class="score-lbl">추세 강도</div></div>', unsafe_allow_html=True)
                    st.info(res3.get("summary","")); st.warning(res3.get("caution",""))
                    sv1,sv2 = st.columns(2)
                    with sv1: st.metric("지지선",f"{res3.get('support_level',0):,}원")
                    with sv2: st.metric("저항선",f"{res3.get('resistance_level',0):,}원")
                except Exception as e: st.error(f"오류: {e}")

# ════════════════════════════════════════════════════════
# TAB 4 : 트렌드 탐지
# ════════════════════════════════════════════════════════
with tab4:
    st.subheader("🔥 주요 투자 테마 트렌드 탐지")
    themes = {
        "🔋 2차전지":["삼성SDI","LG에너지솔루션","POSCO홀딩스","에코프로"],
        "🤖 AI/반도체":["삼성전자","SK하이닉스","한미반도체","리노공업"],
        "💊 바이오":["삼성바이오로직스","셀트리온","HLB","유한양행"],
        "🏗️ 방산":["한화에어로스페이스","LIG넥스원","현대로템","한국항공우주"],
        "🏦 금융":["KB금융","신한지주","하나금융","우리금융"],
        "🚗 자동차":["현대차","기아","현대모비스","HL만도"],
        "🌐 통신":["SK텔레콤","KT","LG유플러스","삼성SDS"],
        "🏭 조선":["HD현대중공업","삼성중공업","한화오션","HD현대"],
        "🛒 유통":["롯데쇼핑","이마트","GS리테일","BGF리테일"],
        "🎮 게임/엔터":["넥슨","크래프톤","넷마블","카카오게임즈"],
    }
    sel = st.selectbox("테마 선택", list(themes.keys()))
    rstocks = themes[sel]
    tcols = st.columns(len(rstocks))
    for i,s in enumerate(rstocks):
        with tcols[i]: st.markdown(f'<div class="score-card"><div style="font-size:0.9rem;font-weight:600">{s}</div><div class="score-lbl">모니터링 중</div></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    ttext = st.text_area(f"{sel} 관련 뉴스/영상", height=140, placeholder="관련 헤드라인 입력")
    api_key = get_api_key()
    if st.button("🔍 테마 분석", type="primary") and ttext and api_key:
        with st.spinner("분석 중..."):
            try:
                client = anthropic.Anthropic(api_key=api_key)
                resp = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=400,
                    messages=[{"role":"user","content":f"{sel} 테마 분석.\n{ttext}\n종목:{','.join(rstocks)}\nJSON만:\n{{\"theme_momentum\":\"상승\"|\"횡보\"|\"하락\",\"momentum_score\":-100에서100정수,\"key_driver\":\"1문장\",\"watch_points\":[\"p1\",\"p2\"],\"summary\":\"2문장\"}}"}])
                raw4 = resp.content[0].text.strip()
                if raw4.startswith("```"):
                    raw4 = raw4.split("```")[1]
                    if raw4.startswith("json"): raw4 = raw4[4:]
                res4 = json.loads(raw4)
                ms = res4.get("momentum_score",0); mc = "positive" if ms>0 else ("negative" if ms<0 else "neutral")
                tc1,tc2 = st.columns(2)
                with tc1: st.markdown(f'<div class="score-card"><div class="score-num {mc}">{ms:+d}</div><div class="score-lbl">테마 모멘텀</div></div>', unsafe_allow_html=True)
                with tc2: st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.5rem;padding-top:4px">{res4.get("theme_momentum","")}</div><div class="score-lbl">방향</div></div>', unsafe_allow_html=True)
                st.info(res4.get("key_driver",""))
                for wp in res4.get("watch_points",[]): st.markdown(f"• {wp}")
                st.success(res4.get("summary",""))
            except Exception as e: st.error(f"오류: {e}")

# ════════════════════════════════════════════════════════
# TAB 5 : 분석 기록
# ════════════════════════════════════════════════════════
with tab5:
    st.subheader("📋 분석 기록")
    history = st.session_state.get("history", [])
    if not history: st.info("분석 기록 없음")
    else:
        st.markdown(f"**총 {len(history)}건**")
        for h in reversed(history):
            sc = h["score"]; color = "#e63946" if sc>20 else ("#1d6fa4" if sc<-20 else "#888")
            st.markdown(f'<div style="border:1px solid #eee;border-radius:8px;padding:12px;margin:6px 0;background:#fff"><span style="color:#999;font-size:0.8rem">{h["time"]}</span><span style="margin-left:12px;font-weight:500">{h["content"]}</span><span style="float:right;color:{color};font-weight:700">{sc:+d} · {h["label"]}</span></div>', unsafe_allow_html=True)
        if st.button("🗑️ 기록 초기화"):
            st.session_state["history"] = []; st.rerun()
