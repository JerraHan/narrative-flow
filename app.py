import streamlit as st
import anthropic
import json
import feedparser
from datetime import datetime
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
.news-title { font-size: 0.95rem; font-weight: 600; color: #0a0a0a; line-height: 1.5; }
.news-meta  { font-size: 0.75rem; color: #999; margin-top: 4px; }
.grade-A { background:#fff0f0; color:#c0392b; border-radius:4px; padding:1px 6px; font-size:0.7rem; font-weight:700; }
.grade-B { background:#fff8e1; color:#e67e22; border-radius:4px; padding:1px 6px; font-size:0.7rem; font-weight:700; }
.grade-C { background:#f0f0f0; color:#666;    border-radius:4px; padding:1px 6px; font-size:0.7rem; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ── RSS 데이터 로드 ──────────────────────────────────────
@st.cache_data(ttl=3600)
def load_rss_list():
    try:
        with open("news_rss.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["media"]
    except Exception:
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
                "source": media["name"],
                "grade": media["grade"],
                "category": media["category"]
            })
        return articles
    except Exception:
        return []

@st.cache_data(ttl=600)
def fetch_rss_news(grade_filter="A", category_filter="전체", max_sources=20):
    media_list = load_rss_list()
    if grade_filter != "전체":
        media_list = [m for m in media_list if m["grade"] == grade_filter]
    if category_filter != "전체":
        media_list = [m for m in media_list if m["category"] == category_filter]
    media_list = media_list[:max_sources]
    all_articles = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_single_rss, m): m for m in media_list}
        for future in as_completed(futures):
            all_articles.extend(future.result())
    return all_articles

# ── 사이드바 ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 설정")
    api_key = st.text_input("Anthropic API 키", type="password", placeholder="sk-ant-...")
    st.markdown("---")
    st.markdown("**분석 옵션**")
    analysis_depth = st.select_slider("분석 깊이", options=["빠른 분석", "기본 분석", "심층 분석"], value="기본 분석")
    show_keywords = st.checkbox("키워드 추출", value=True)
    show_sentiment = st.checkbox("감성 분석", value=True)
    show_risk = st.checkbox("리스크 신호 감지", value=True)
    st.markdown("---")
    st.markdown("**모니터링 채널**")
    st.info("📺 YouTube 채널 137개\n\n📰 뉴스 미디어 175개")
    st.markdown("---")
    st.caption("Narrative Flow v0.2 MVP\n내러티브 레이더 | 투자 인텔리전스")

# ── 헤더 ─────────────────────────────────────────────────
st.markdown('<p class="main-title">📊 내러티브 흐름</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">한국 주식시장 투자 인텔리전스 플랫폼</p>', unsafe_allow_html=True)
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["🔍 내러티브 분석", "📰 뉴스 RSS", "📈 트렌드 탐지", "📋 분석 기록"])

# ════════════════════════════════════════════════════════
# TAB 1
# ════════════════════════════════════════════════════════
with tab1:
    st.subheader("YouTube / 뉴스 콘텐츠 내러티브 분석")
    col_in, col_ex = st.columns([2, 1])
    with col_in:
        content_input = st.text_area("분석할 콘텐츠 입력", height=180,
            placeholder="YouTube 영상 제목, 설명, 뉴스 기사 내용 등을 붙여넣으세요.")
        ticker_input = st.text_input("관련 종목 (선택)", placeholder="예: 삼성전자, 005930, KOSPI")
    with col_ex:
        st.markdown("**분석 예시 콘텐츠**")
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
                    prompt = f"""당신은 한국 주식시장 전문 투자 분석 AI입니다.
아래 콘텐츠를 {depth_map[analysis_depth]} 분석해 주세요.
[분석 콘텐츠] {content_input}
{f"[관련 종목] {ticker_input}" if ticker_input else ""}
반드시 아래 JSON 형식으로만 응답하세요:
{{"sentiment_score": -100에서 100 정수, "sentiment_label": "강한 매수 신호"|"매수 신호"|"중립"|"매도 신호"|"강한 매도 신호",
"confidence": 0에서 100 정수, "narrative_type": "실적 기대"|"테마/섹터"|"매크로"|"리스크"|"내부자/기관"|"기타",
"keywords": ["키워드1","키워드2","키워드3","키워드4","키워드5"], "risk_signals": ["리스크1","리스크2"],
"summary": "2-3문장 핵심 요약", "investment_implication": "투자 시사점 1-2문장", "data_quality": "높음"|"보통"|"낮음"}}"""
                    response = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=1000,
                        messages=[{"role": "user", "content": prompt}])
                    raw = response.content[0].text.strip()
                    if raw.startswith("```"):
                        raw = raw.split("```")[1]
                        if raw.startswith("json"): raw = raw[4:]
                    result = json.loads(raw)
                    st.markdown("---")
                    st.markdown("### 📊 분석 결과")
                    score = result.get("sentiment_score", 0)
                    score_class = "positive" if score > 20 else ("negative" if score < -20 else "neutral")
                    label = result.get("sentiment_label", "")
                    confidence = result.get("confidence", 0)
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.markdown(f'<div class="score-card"><div class="score-num {score_class}">{score:+d}</div><div class="score-lbl">내러티브 점수</div></div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.3rem;padding-top:8px">{label}</div><div class="score-lbl">신호 유형</div></div>', unsafe_allow_html=True)
                    with c3:
                        st.markdown(f'<div class="score-card"><div class="score-num">{confidence}%</div><div class="score-lbl">신뢰도</div></div>', unsafe_allow_html=True)
                    with c4:
                        st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.1rem;padding-top:12px">{result.get("narrative_type","")}</div><div class="score-lbl">내러티브 유형</div></div>', unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**📝 핵심 요약**"); st.info(result.get("summary", ""))
                        st.markdown("**💡 투자 시사점**"); st.success(result.get("investment_implication", ""))
                    with col_b:
                        if show_keywords:
                            st.markdown("**🏷️ 핵심 키워드**")
                            st.markdown(" ".join([f'<span class="tag">{k}</span>' for k in result.get("keywords", [])]), unsafe_allow_html=True)
                        if show_risk and result.get("risk_signals"):
                            st.markdown("<br>**⚠️ 리스크 신호**", unsafe_allow_html=True)
                            for r in result.get("risk_signals", []):
                                if r: st.warning(f"• {r}")
                    if "history" not in st.session_state: st.session_state["history"] = []
                    st.session_state["history"].append({"time": datetime.now().strftime("%H:%M:%S"),
                        "content": content_input[:50] + "...", "score": score, "label": label, "ticker": ticker_input or "-"})
                except json.JSONDecodeError:
                    st.error("JSON 파싱 오류. 다시 시도해 주세요.")
                except anthropic.AuthenticationError:
                    st.error("API 키가 올바르지 않습니다.")
                except Exception as e:
                    st.error(f"오류 발생: {e}")

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
        with st.spinner(f"뉴스 수집 중... (최대 {max_sources}개 소스)"):
            if selected_grade == "AB":
                articles = fetch_rss_news("A", category_filter, max_sources // 2) + fetch_rss_news("B", category_filter, max_sources // 2)
            else:
                articles = fetch_rss_news(selected_grade, category_filter, max_sources)
            st.session_state["rss_articles"] = articles
            st.success(f"✅ {len(articles)}개 기사 수집 완료")

    if "rss_articles" in st.session_state and st.session_state["rss_articles"]:
        articles = st.session_state["rss_articles"]
        keyword_search = st.text_input("🔎 키워드 검색", placeholder="삼성전자, 반도체, 금리...")
        if keyword_search:
            articles = [a for a in articles if keyword_search in a["title"] or keyword_search in a["summary"]]
            st.caption(f"'{keyword_search}' 검색 결과: {len(articles)}건")
        st.markdown(f"**총 {len(articles)}개 기사**")
        for article in articles[:50]:
            grade_class = f"grade-{article['grade']}"
            summary_html = f'<div style="font-size:0.82rem;color:#555;margin-top:6px">{article["summary"]}</div>' if article["summary"] else ""
            pub = article["published"][:16] if article["published"] else ""
            st.markdown(f'''<div class="news-card">
<div class="news-title"><span class="{grade_class}">{article["grade"]}</span>&nbsp;<a href="{article["link"]}" target="_blank" style="color:#0a0a0a;text-decoration:none">{article["title"]}</a></div>
<div class="news-meta">📰 {article["source"]} · {article["category"]} · {pub}</div>{summary_html}</div>''', unsafe_allow_html=True)

    if analyze_news_btn:
        if not api_key:
            st.error("⚠️ 사이드바에서 API 키를 입력해 주세요.")
        elif "rss_articles" not in st.session_state or not st.session_state["rss_articles"]:
            st.warning("먼저 뉴스를 수집해 주세요.")
        else:
            articles = st.session_state["rss_articles"][:20]
            headlines = "\n".join([f"- {a['title']} ({a['source']})" for a in articles])
            with st.spinner("AI가 뉴스 흐름을 분석 중..."):
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    response = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=1000,
                        messages=[{"role": "user", "content": f"""한국 주식시장 투자자 관점에서 아래 뉴스 헤드라인들을 분석해 주세요.
{headlines}
JSON으로만 응답:
{{"market_sentiment":"긍정"|"부정"|"혼조"|"중립","sentiment_score":-100에서 100 정수,
"dominant_themes":["테마1","테마2","테마3"],"hot_sectors":["섹터1","섹터2"],
"risk_factors":["리스크1","리스크2"],"summary":"전체 뉴스 흐름 요약 3문장","investment_signal":"투자 시사점 2문장"}}"""}])
                    raw = response.content[0].text.strip()
                    if raw.startswith("```"):
                        raw = raw.split("```")[1]
                        if raw.startswith("json"): raw = raw[4:]
                    result = json.loads(raw)
                    st.markdown("---"); st.markdown("### 🤖 뉴스 흐름 AI 분석")
                    score = result.get("sentiment_score", 0)
                    score_class = "positive" if score > 0 else ("negative" if score < 0 else "neutral")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f'<div class="score-card"><div class="score-num {score_class}">{score:+d}</div><div class="score-lbl">시장 내러티브 점수</div></div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.4rem;padding-top:6px">{result.get("market_sentiment","")}</div><div class="score-lbl">시장 심리</div></div>', unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**🔥 핫 섹터**")
                        st.markdown(" ".join([f'<span class="tag">{s}</span>' for s in result.get("hot_sectors", [])]), unsafe_allow_html=True)
                        st.markdown("<br>**📋 주요 테마**", unsafe_allow_html=True)
                        for t in result.get("dominant_themes", []): st.markdown(f"• {t}")
                    with col_b:
                        st.markdown("**📝 뉴스 흐름 요약**"); st.info(result.get("summary", ""))
                        st.markdown("**💡 투자 시사점**"); st.success(result.get("investment_signal", ""))
                except Exception as e:
                    st.error(f"분석 오류: {e}")

# ════════════════════════════════════════════════════════
# TAB 3 : 트렌드 탐지
# ════════════════════════════════════════════════════════
with tab3:
    st.subheader("📈 주요 투자 테마 트렌드 탐지")
    themes = {
        "🔋 2차전지": ["삼성SDI", "LG에너지솔루션", "POSCO홀딩스", "에코프로"],
        "🤖 AI/반도체": ["삼성전자", "SK하이닉스", "한미반도체", "리노공업"],
        "💊 바이오": ["삼성바이오로직스", "셀트리온", "HLB", "유한양행"],
        "🏗️ 방산": ["한화에어로스페이스", "LIG넥스원", "현대로템", "한국항공우주"],
        "🏦 금융": ["KB금융", "신한지주", "하나금융", "우리금융"],
        "🚗 자동차": ["현대차", "기아", "현대모비스", "HL만도"],
        "🌐 네트워크/통신": ["SK텔레콤", "KT", "LG유플러스", "삼성SDS"],
        "🏭 조선/중공업": ["HD현대중공업", "삼성중공업", "한화오션", "HD현대"],
        "🛒 유통/소비재": ["롯데쇼핑", "이마트", "GS리테일", "BGF리테일"],
        "🎮 게임/엔터": ["넥슨", "크래프톤", "넷마블", "카카오게임즈"],
    }
    selected_theme = st.selectbox("테마 선택", list(themes.keys()))
    related_stocks = themes[selected_theme]
    cols = st.columns(len(related_stocks))
    for i, stock in enumerate(related_stocks):
        with cols[i]:
            st.markdown(f'<div class="score-card"><div style="font-size:0.9rem;font-weight:600">{stock}</div><div class="score-lbl">모니터링 중</div></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    theme_text = st.text_area(f"{selected_theme} 관련 최신 뉴스/영상 내용 입력", height=140,
        placeholder=f"{selected_theme} 테마 관련 YouTube 제목이나 뉴스 헤드라인을 입력하세요.")
    if st.button("🔍 테마 분석", type="primary") and theme_text and api_key:
        with st.spinner("테마 분석 중..."):
            try:
                client = anthropic.Anthropic(api_key=api_key)
                response = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=600,
                    messages=[{"role": "user", "content": f"""한국 주식시장 {selected_theme} 테마 분석.
콘텐츠: {theme_text} | 관련 종목: {', '.join(related_stocks)}
JSON으로만 응답:
{{"theme_momentum":"상승"|"횡보"|"하락","momentum_score":-100에서 100 정수,
"key_driver":"핵심 드라이버 1문장","watch_points":["포인트1","포인트2"],"summary":"테마 전망 2문장"}}"""}])
                raw = response.content[0].text.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"): raw = raw[4:]
                result = json.loads(raw)
                m_score = result.get("momentum_score", 0)
                m_class = "positive" if m_score > 0 else ("negative" if m_score < 0 else "neutral")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f'<div class="score-card"><div class="score-num {m_class}">{m_score:+d}</div><div class="score-lbl">테마 모멘텀 점수</div></div>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<div class="score-card"><div class="score-num" style="font-size:1.5rem;padding-top:4px">{result.get("theme_momentum","")}</div><div class="score-lbl">모멘텀 방향</div></div>', unsafe_allow_html=True)
                st.markdown("<br>**🎯 핵심 드라이버**", unsafe_allow_html=True); st.info(result.get("key_driver", ""))
                st.markdown("**📋 주목 포인트**")
                for wp in result.get("watch_points", []): st.markdown(f"• {wp}")
                st.markdown("**📊 테마 전망**"); st.success(result.get("summary", ""))
            except Exception as e:
                st.error(f"오류: {e}")

# ════════════════════════════════════════════════════════
# TAB 4 : 분석 기록
# ════════════════════════════════════════════════════════
with tab4:
    st.subheader("📋 분석 기록")
    history = st.session_state.get("history", [])
    if not history:
        st.info("아직 분석 기록이 없습니다.")
    else:
        st.markdown(f"**총 {len(history)}건 분석 완료**")
        for h in reversed(history):
            score = h["score"]
            color = "#e63946" if score > 20 else ("#1d6fa4" if score < -20 else "#888")
            st.markdown(f'''<div style="border:1px solid #eee;border-radius:8px;padding:12px;margin:6px 0;background:#fff">
<span style="color:#999;font-size:0.8rem">{h["time"]}</span>
<span style="margin-left:12px;font-weight:500">{h["content"]}</span>
<span style="float:right;color:{color};font-weight:700">{score:+d} · {h["label"]}</span></div>''', unsafe_allow_html=True)
        if st.button("🗑️ 기록 초기화"):
            st.session_state["history"] = []
            st.rerun()
