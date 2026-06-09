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
.tag {
    display: inline-block; background: #f0f4ff; color: #3355cc;
    border-radius: 20px; padding: 3px 12px; font-size: 0.78rem; margin: 3px;
}
.news-card {
    background: #fff; border: 1px solid #e8e8e8; border-radius: 10px;
    padding: 14px 16px; margin: 8px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.grade-A { background:#fff0f0; color:#c0392b; border-radius:4px; padding:1px 6px; font-size:0.7rem; font-weight:700; }
.grade-B { background:#fff8e1; color:#e67e22; border-radius:4px; padding:1px 6px; font-size:0.7rem; font-weight:700; }
.grade-C { background:#f0f0f0; color:#666;    border-radius:4px; padding:1px 6px; font-size:0.7rem; font-weight:700; }
.stock-up   { color: #e63946; font-weight: 700; }
.stock-down { color: #1d6fa4; font-weight: 700; }
.stock-flat { color: #888; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

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
        for entry in feed.entries[:5]:
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

# ── 주가 함수 ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_stock_data(ticker, period_days=30):
    try:
        import FinanceDataReader as fdr
        end = datetime.today()
        start = end - timedelta(days=period_days)
        df = fdr.DataReader(ticker, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        if df.empty:
            return None
        return df
    except Exception as e:
        return None

def get_stock_info(ticker):
    df = get_stock_data(ticker, 5)
    if df is None or df.empty:
        return None
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    change = latest["Close"] - prev["Close"]
    change_pct = (change / prev["Close"]) * 100
    return {
        "close": latest["Close"],
        "change": change,
        "change_pct": change_pct,
        "volume": latest["Volume"],
        "high": latest["High"],
        "low": latest["Low"],
    }

# ── 사이드바 ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 설정")
    api_key = st.text_input("Anthropic API 키", type="password", placeholder="sk-ant-...")
    st.markdown("---")
    analysis_depth = st.select_slider("분석 깊이", options=["빠른 분석", "기본 분석", "심층 분석"], value="기본 분석")
    show_keywords = st.checkbox("키워드 추출", value=True)
    show_risk = st.checkbox("리스크 신호 감지", value=True)
    st.markdown("---")
    st.info("📺 YouTube 채널 137개\n\n📰 뉴스 미디어 175개")
    st.caption("Narrative Flow v0.3 MVP")

# ── 헤더 ─────────────────────────────────────────────────
st.markdown('<p class="main-title">📊 내러티브 흐름</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">한국 주식시장 투자 인텔리전스 플랫폼</p>', unsafe_allow_html=True)
st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 내러티브 분석", "📰 뉴스 RSS", "📈 주가 연동", "🎯 트렌드 탐지", "📋 분석 기록"])

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

    analyze_btn = st.button("🚀 AI 분석 시작", type="primary", use_container_width=True)
    if analyze_btn:
        if not api_key:
            st.error("⚠️ 사이드바에서 Anthropic API 키를 입력해 주세요.")
        elif not content_input.strip():
            st.warning("분석할 콘텐츠를 입력해 주세요.")
        else:
            with st.spinner("AI가 내러티브를 분석 중입니다..."):
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    depth_map = {"빠른 분석": "간결하게 핵심만", "기본 분석": "균형 있게", "심층 분석": "상세하고 깊이 있게"}
                    prompt = f"""한국 주식시장 전문 투자 분석 AI로서 아래 콘텐츠를 {depth_map[analysis_depth]} 분석하세요.
[콘텐츠] {content_input}
{f"[종목] {ticker_input}" if ticker_input else ""}
JSON으로만 응답:
{{"sentiment_score":-100에서100정수,"sentiment_label":"강한 매수 신호"|"매수 신호"|"중립"|"매도 신호"|"강한 매도 신호",
"confidence":0에서100정수,"narrative_type":"실적 기대"|"테마/섹터"|"매크로"|"리스크"|"내부자/기관"|"기타",
"keywords":["k1","k2","k3","k4","k5"],"risk_signals":["r1","r2"],
"summary":"2-3문장 요약","investment_implication":"시사점 1-2문장","data_quality":"높음"|"보통"|"낮음"}}"""
                    response = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=1000,
                        messages=[{"role": "user", "content": prompt}])
                    raw = response.content[0].text.strip()
                    if raw.startswith("```"):
                        raw = raw.split("```")[1]
                        if raw.startswith("json"): raw = raw[4:]
                    result = json.loads(raw)
                    st.markdown("---"); st.markdown("### 📊 분석 결과")
                    score = result.get("sentiment_score", 0)
                    score_class = "positive" if score > 20 else ("negative" if score < -20 else "neutral")
                    label = result.get("sentiment_label", "")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.markdown(f'<div class="score-card"><div class="score-num {score_class}">{score:+d}</div><div class="score-lbl">내러티브 점수</div></div>', unsafe_allow_html=True)
                    with c2: st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.3rem;padding-top:8px">{label}</div><div class="score-lbl">신호 유형</div></div>', unsafe_allow_html=True)
                    with c3: st.markdown(f'<div class="score-card"><div class="score-num">{result.get("confidence",0)}%</div><div class="score-lbl">신뢰도</div></div>', unsafe_allow_html=True)
                    with c4: st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.1rem;padding-top:12px">{result.get("narrative_type","")}</div><div class="score-lbl">내러티브 유형</div></div>', unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)

                    # 주가 연동 (종목 입력 시)
                    if ticker_input:
                        ticker_code = ticker_input.strip().replace("삼성전자","005930").replace("SK하이닉스","000660").replace("현대차","005380")
                        info = get_stock_info(ticker_code)
                        if info:
                            st.markdown("**📈 실시간 주가**")
                            chg_class = "stock-up" if info["change_pct"] > 0 else ("stock-down" if info["change_pct"] < 0 else "stock-flat")
                            arrow = "▲" if info["change_pct"] > 0 else ("▼" if info["change_pct"] < 0 else "–")
                            sc1, sc2, sc3 = st.columns(3)
                            with sc1: st.metric("현재가", f"{info['close']:,.0f}원")
                            with sc2: st.metric("등락", f"{arrow}{abs(info['change_pct']):.2f}%")
                            with sc3: st.metric("거래량", f"{info['volume']:,}")

                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**📝 핵심 요약**"); st.info(result.get("summary", ""))
                        st.markdown("**💡 투자 시사점**"); st.success(result.get("investment_implication", ""))
                    with col_b:
                        if show_keywords:
                            st.markdown("**🏷️ 핵심 키워드**")
                            st.markdown(" ".join([f'<span class="tag">{k}</span>' for k in result.get("keywords",[])]), unsafe_allow_html=True)
                        if show_risk and result.get("risk_signals"):
                            st.markdown("<br>**⚠️ 리스크 신호**", unsafe_allow_html=True)
                            for r in result.get("risk_signals", []):
                                if r: st.warning(f"• {r}")
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
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1: grade_filter = st.selectbox("등급 필터", ["A급만", "A+B급", "전체"], index=0)
    with col_f2: category_filter = st.selectbox("카테고리", categories)
    with col_f3: max_sources = st.slider("수집 소스 수", 5, 30, 15)
    grade_map = {"A급만": "A", "A+B급": "AB", "전체": "전체"}
    selected_grade = grade_map[grade_filter]
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1: fetch_btn = st.button("📡 뉴스 수집 시작", type="primary", use_container_width=True)
    with col_btn2: analyze_news_btn = st.button("🤖 수집 뉴스 AI 분석", use_container_width=True)
    if fetch_btn:
        with st.spinner(f"수집 중..."):
            if selected_grade == "AB":
                articles = fetch_rss_news("A", category_filter, max_sources//2) + fetch_rss_news("B", category_filter, max_sources//2)
            else:
                articles = fetch_rss_news(selected_grade, category_filter, max_sources)
            st.session_state["rss_articles"] = articles
            st.success(f"✅ {len(articles)}개 기사 수집 완료")
    if "rss_articles" in st.session_state and st.session_state["rss_articles"]:
        articles = st.session_state["rss_articles"]
        kw = st.text_input("🔎 키워드 검색", placeholder="삼성전자, 반도체, 금리...")
        if kw: articles = [a for a in articles if kw in a["title"] or kw in a["summary"]]
        st.markdown(f"**총 {len(articles)}개 기사**")
        for article in articles[:50]:
            gc = f"grade-{article['grade']}"
            pub = article["published"][:16] if article["published"] else ""
            sm = f'<div style="font-size:0.82rem;color:#555;margin-top:6px">{article["summary"]}</div>' if article["summary"] else ""
            st.markdown(f'<div class="news-card"><div class="news-title"><span class="{gc}">{article["grade"]}</span>&nbsp;<a href="{article["link"]}" target="_blank" style="color:#0a0a0a;text-decoration:none">{article["title"]}</a></div><div class="news-meta">📰 {article["source"]} · {article["category"]} · {pub}</div>{sm}</div>', unsafe_allow_html=True)
    if analyze_news_btn:
        if not api_key: st.error("⚠️ API 키를 입력해 주세요.")
        elif "rss_articles" not in st.session_state: st.warning("먼저 뉴스를 수집해 주세요.")
        else:
            articles = st.session_state["rss_articles"][:20]
            headlines = "\n".join([f"- {a['title']} ({a['source']})" for a in articles])
            with st.spinner("AI 분석 중..."):
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    response = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=1000,
                        messages=[{"role":"user","content":f"한국 주식시장 투자자 관점으로 뉴스 분석:\n{headlines}\nJSON으로만:\n{{\"market_sentiment\":\"긍정\"|\"부정\"|\"혼조\"|\"중립\",\"sentiment_score\":-100에서100정수,\"dominant_themes\":[\"t1\",\"t2\",\"t3\"],\"hot_sectors\":[\"s1\",\"s2\"],\"risk_factors\":[\"r1\",\"r2\"],\"summary\":\"3문장요약\",\"investment_signal\":\"시사점2문장\"}}"}])
                    raw = response.content[0].text.strip()
                    if raw.startswith("```"):
                        raw = raw.split("```")[1]
                        if raw.startswith("json"): raw = raw[4:]
                    result = json.loads(raw)
                    st.markdown("---"); st.markdown("### 🤖 뉴스 흐름 AI 분석")
                    score = result.get("sentiment_score", 0)
                    sc = "positive" if score > 0 else ("negative" if score < 0 else "neutral")
                    c1, c2 = st.columns(2)
                    with c1: st.markdown(f'<div class="score-card"><div class="score-num {sc}">{score:+d}</div><div class="score-lbl">시장 내러티브 점수</div></div>', unsafe_allow_html=True)
                    with c2: st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.4rem;padding-top:6px">{result.get("market_sentiment","")}</div><div class="score-lbl">시장 심리</div></div>', unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    ca, cb = st.columns(2)
                    with ca:
                        st.markdown("**🔥 핫 섹터**")
                        st.markdown(" ".join([f'<span class="tag">{s}</span>' for s in result.get("hot_sectors",[])]), unsafe_allow_html=True)
                        st.markdown("<br>**📋 주요 테마**", unsafe_allow_html=True)
                        for t in result.get("dominant_themes",[]): st.markdown(f"• {t}")
                    with cb:
                        st.markdown("**📝 뉴스 흐름 요약**"); st.info(result.get("summary",""))
                        st.markdown("**💡 투자 시사점**"); st.success(result.get("investment_signal",""))
                except Exception as e:
                    st.error(f"오류: {e}")

# ════════════════════════════════════════════════════════
# TAB 3 : 주가 연동
# ════════════════════════════════════════════════════════
with tab3:
    st.subheader("📈 실시간 주가 조회 & 내러티브 비교")

    # 주요 종목 빠른 선택
    st.markdown("**주요 종목 빠른 조회**")
    quick_stocks = {
        "삼성전자": "005930", "SK하이닉스": "000660", "현대차": "005380",
        "POSCO홀딩스": "005490", "셀트리온": "068270", "카카오": "035720",
        "네이버": "035420", "한화에어로": "012450", "LG에너지솔루션": "373220", "에코프로": "086520"
    }
    cols = st.columns(5)
    for i, (name, code) in enumerate(quick_stocks.items()):
        with cols[i % 5]:
            if st.button(name, key=f"quick_{code}", use_container_width=True):
                st.session_state["selected_ticker"] = code
                st.session_state["selected_name"] = name

    st.markdown("---")

    col_s1, col_s2 = st.columns([2, 1])
    with col_s1:
        default_ticker = st.session_state.get("selected_ticker", "005930")
        ticker = st.text_input("종목코드 입력", value=default_ticker, placeholder="005930")
    with col_s2:
        period = st.selectbox("조회 기간", ["1개월", "3개월", "6개월", "1년"], index=0)

    period_map = {"1개월": 30, "3개월": 90, "6개월": 180, "1년": 365}

    if st.button("📊 주가 조회", type="primary", use_container_width=True):
        with st.spinner("주가 데이터 조회 중..."):
            df = get_stock_data(ticker, period_map[period])
            if df is not None and not df.empty:
                st.session_state["stock_df"] = df
                st.session_state["stock_ticker"] = ticker
                st.success(f"✅ {ticker} 데이터 로드 완료 ({len(df)}일)")
            else:
                st.error("주가 데이터를 가져올 수 없습니다. 종목코드를 확인해 주세요.")

    if "stock_df" in st.session_state:
        df = st.session_state["stock_df"]
        ticker_name = st.session_state.get("selected_name", st.session_state.get("stock_ticker", ""))

        # 현재가 요약
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
        change = latest["Close"] - prev["Close"]
        change_pct = (change / prev["Close"]) * 100
        chg_class = "stock-up" if change_pct > 0 else ("stock-down" if change_pct < 0 else "stock-flat")
        arrow = "▲" if change_pct > 0 else ("▼" if change_pct < 0 else "–")

        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("현재가", f"{latest['Close']:,.0f}원")
        with m2: st.metric("등락률", f"{arrow}{abs(change_pct):.2f}%", delta=f"{change:+,.0f}원")
        with m3: st.metric("거래량", f"{latest['Volume']:,}")
        with m4:
            period_change = ((latest["Close"] - df.iloc[0]["Close"]) / df.iloc[0]["Close"]) * 100
            st.metric("기간 수익률", f"{period_change:+.2f}%")

        # 차트
        st.markdown("**📉 주가 차트**")
        chart_data = df[["Close"]].rename(columns={"Close": "종가"})
        st.line_chart(chart_data)

        # 거래량 차트
        st.markdown("**📊 거래량**")
        vol_data = df[["Volume"]].rename(columns={"Volume": "거래량"})
        st.bar_chart(vol_data)

        # AI 주가 분석
        if api_key:
            if st.button("🤖 주가 + 내러티브 AI 분석", use_container_width=True):
                with st.spinner("AI 분석 중..."):
                    try:
                        client = anthropic.Anthropic(api_key=api_key)
                        recent = df.tail(10)[["Close","Volume"]].to_string()
                        response = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=800,
                            messages=[{"role":"user","content":f"""종목 {ticker_name}({ticker})의 최근 주가 데이터를 분석해 주세요.
최근 10일 데이터:
{recent}
기간 수익률: {period_change:+.2f}%
JSON으로만:
{{"trend":"상승추세"|"하락추세"|"횡보","trend_strength":"강함"|"보통"|"약함",
"support_level":지지선가격정수,"resistance_level":저항선가격정수,
"volume_signal":"거래량 증가 (매수세)"|"거래량 감소 (관망)"|"거래량 급증 (변곡점 가능)",
"technical_signal":"매수"|"매도"|"중립","summary":"기술적 분석 2문장","caution":"주의사항 1문장"}}"""}])
                        raw = response.content[0].text.strip()
                        if raw.startswith("```"):
                            raw = raw.split("```")[1]
                            if raw.startswith("json"): raw = raw[4:]
                        result = json.loads(raw)
                        st.markdown("---"); st.markdown("### 🤖 AI 기술적 분석")
                        ta1, ta2, ta3 = st.columns(3)
                        with ta1: st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.4rem;padding-top:6px">{result.get("trend","")}</div><div class="score-lbl">추세</div></div>', unsafe_allow_html=True)
                        with ta2: st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.4rem;padding-top:6px">{result.get("technical_signal","")}</div><div class="score-lbl">기술적 신호</div></div>', unsafe_allow_html=True)
                        with ta3: st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.4rem;padding-top:6px">{result.get("trend_strength","")}</div><div class="score-lbl">추세 강도</div></div>', unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.info(f"📊 {result.get('summary','')}")
                        st.warning(f"⚠️ {result.get('caution','')}")
                        sv1, sv2 = st.columns(2)
                        with sv1: st.metric("지지선", f"{result.get('support_level',0):,}원")
                        with sv2: st.metric("저항선", f"{result.get('resistance_level',0):,}원")
                        st.info(f"📊 거래량 신호: {result.get('volume_signal','')}")
                    except Exception as e:
                        st.error(f"분석 오류: {e}")

# ════════════════════════════════════════════════════════
# TAB 4 : 트렌드 탐지
# ════════════════════════════════════════════════════════
with tab4:
    st.subheader("🎯 주요 투자 테마 트렌드 탐지")
    themes = {
        "🔋 2차전지": ["삼성SDI", "LG에너지솔루션", "POSCO홀딩스", "에코프로"],
        "🤖 AI/반도체": ["삼성전자", "SK하이닉스", "한미반도체", "리노공업"],
        "💊 바이오": ["삼성바이오로직스", "셀트리온", "HLB", "유한양행"],
        "🏗️ 방산": ["한화에어로스페이스", "LIG넥스원", "현대로템", "한국항공우주"],
        "🏦 금융": ["KB금융", "신한지주", "하나금융", "우리금융"],
        "🚗 자동차": ["현대차", "기아", "현대모비스", "HL만도"],
        "🌐 통신": ["SK텔레콤", "KT", "LG유플러스", "삼성SDS"],
        "🏭 조선": ["HD현대중공업", "삼성중공업", "한화오션", "HD현대"],
        "🛒 유통": ["롯데쇼핑", "이마트", "GS리테일", "BGF리테일"],
        "🎮 게임/엔터": ["넥슨", "크래프톤", "넷마블", "카카오게임즈"],
    }
    selected_theme = st.selectbox("테마 선택", list(themes.keys()))
    related_stocks = themes[selected_theme]
    cols = st.columns(len(related_stocks))
    for i, stock in enumerate(related_stocks):
        with cols[i]:
            st.markdown(f'<div class="score-card"><div style="font-size:0.9rem;font-weight:600">{stock}</div><div class="score-lbl">모니터링 중</div></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    theme_text = st.text_area(f"{selected_theme} 관련 최신 뉴스/영상", height=140, placeholder="관련 헤드라인을 입력하세요.")
    if st.button("🔍 테마 분석", type="primary") and theme_text and api_key:
        with st.spinner("분석 중..."):
            try:
                client = anthropic.Anthropic(api_key=api_key)
                response = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=600,
                    messages=[{"role":"user","content":f"한국 주식 {selected_theme} 테마 분석.\n콘텐츠:{theme_text}\n종목:{','.join(related_stocks)}\nJSON만:\n{{\"theme_momentum\":\"상승\"|\"횡보\"|\"하락\",\"momentum_score\":-100에서100정수,\"key_driver\":\"드라이버1문장\",\"watch_points\":[\"p1\",\"p2\"],\"summary\":\"전망2문장\"}}"}])
                raw = response.content[0].text.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"): raw = raw[4:]
                result = json.loads(raw)
                ms = result.get("momentum_score", 0)
                mc = "positive" if ms > 0 else ("negative" if ms < 0 else "neutral")
                c1, c2 = st.columns(2)
                with c1: st.markdown(f'<div class="score-card"><div class="score-num {mc}">{ms:+d}</div><div class="score-lbl">테마 모멘텀</div></div>', unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.5rem;padding-top:4px">{result.get("theme_momentum","")}</div><div class="score-lbl">방향</div></div>', unsafe_allow_html=True)
                st.markdown("<br>**🎯 핵심 드라이버**", unsafe_allow_html=True); st.info(result.get("key_driver",""))
                for wp in result.get("watch_points",[]): st.markdown(f"• {wp}")
                st.success(result.get("summary",""))
            except Exception as e:
                st.error(f"오류: {e}")

# ════════════════════════════════════════════════════════
# TAB 5 : 분석 기록
# ════════════════════════════════════════════════════════
with tab5:
    st.subheader("📋 분석 기록")
    history = st.session_state.get("history", [])
    if not history:
        st.info("아직 분석 기록이 없습니다.")
    else:
        st.markdown(f"**총 {len(history)}건**")
        for h in reversed(history):
            score = h["score"]
            color = "#e63946" if score > 20 else ("#1d6fa4" if score < -20 else "#888")
            st.markdown(f'<div style="border:1px solid #eee;border-radius:8px;padding:12px;margin:6px 0;background:#fff"><span style="color:#999;font-size:0.8rem">{h["time"]}</span><span style="margin-left:12px;font-weight:500">{h["content"]}</span><span style="float:right;color:{color};font-weight:700">{score:+d} · {h["label"]}</span></div>', unsafe_allow_html=True)
        if st.button("🗑️ 기록 초기화"):
            st.session_state["history"] = []
            st.rerun()
