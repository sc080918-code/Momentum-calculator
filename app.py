import json
import os
from datetime import datetime
import pandas as pd
import streamlit as st
import yfinance as yf

# ==============================================================================
# 1. 페이지 기본 설정 및 파일 경로 (Streamlit 자체 모바일 반응형 지원)
# ==============================================================================
st.set_page_config(page_title="미국 ETF 월별 모멘텀 스코어 계산기", layout="wide")

# 모바일 화면 UI 미세 조정을 위한 커스텀 CSS (버튼 상단 여백 정리)
st.markdown(
    """
    <style>
    @media (max-width: 768px) {
        .stButton button {
            width: 100%;
            margin-top: 5px;
        }
    }
    </style>
""",
    unsafe_allow_html=True,
)

HISTORY_FILE = "momentum_history.json"


# 로컬 파일 데이터 불러오기 함수
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


# 로컬 파일 데이터 저장하기 함수
def save_history(data):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"데이터 저장 실패: {e}")


# 날짜 형식 변환 함수 (YYYY-MM-DD -> YY년 M월 기준)
def format_date_to_kor(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.strftime('%y')}년 {dt.month}월 기준"
    except Exception:
        return date_str


# ==============================================================================
# 2. 세션 상태 안전 초기화 (최상단 배치로 KeyError 방지)
# ==============================================================================
if "monthly_scores_db" not in st.session_state:
    st.session_state["monthly_scores_db"] = load_history()

if "last_search_results" not in st.session_state:
    st.session_state["last_search_results"] = []

if "custom_etf_info" not in st.session_state:
    st.session_state["custom_etf_info"] = {}


# ==============================================================================
# 3. UI 타이틀 및 기본 자산 목록
# ==============================================================================
st.title("📈 미국 ETF 모멘텀 스코어 계산기")
st.write("VAA 가중 모멘텀 스코어를 산출하고 월별 기록을 관리합니다.")

# 기본 18개 종목 사전
DEFAULT_ETF_DICT = {
    "XLK": {
        "분류": "미국 대표 섹터",
        "명칭": "Technology Select Sector SPDR",
        "추종 지수 / 설명": "Apple, MS, NVDA 등 미국 대형 IT/빅테크",
    },
    "XLE": {
        "분류": "미국 대표 섹터",
        "명칭": "Energy Select Sector SPDR",
        "추종 지수 / 설명": "ExxonMobil, Chevron 등 석유/가스 에너지",
    },
    "XLV": {
        "분류": "미국 대표 섹터",
        "명칭": "Health Care Select Sector SPDR",
        "추종 지수 / 설명": "Eli Lilly, J&J, Pfizer 등 제약/바이오/의료",
    },
    "XLC": {
        "분류": "미국 대표 섹터",
        "명칭": "Communication Services SPDR",
        "추종 지수 / 설명": "Alphabet, Meta, Netflix 등 미디어/통신",
    },
    "XLF": {
        "분류": "미국 대표 섹터",
        "명칭": "Financial Select Sector SPDR",
        "추종 지수 / 설명": "Berkshire, JP Morgan, Visa 등 금융/은행",
    },
    "XLY": {
        "분류": "미국 대표 섹터",
        "명칭": "Consumer Discretionary SPDR",
        "추종 지수 / 설명": "Amazon, Tesla 등 임의소비재/경기소비재",
    },
    "XLP": {
        "분류": "미국 대표 섹터",
        "명칭": "Consumer Staples Select SPDR",
        "추종 지수 / 설명": "P&G, Costco, PepsiCo 등 필수소비재",
    },
    "XLI": {
        "분류": "미국 대표 섹터",
        "명칭": "Industrial Select Sector SPDR",
        "추종 지수 / 설명": "GE, Caterpillar, RTX 등 산업재/방산/기계",
    },
    "XLU": {
        "분류": "미국 대표 섹터",
        "명칭": "Utilities Select Sector SPDR",
        "추종 지수 / 설명": "NextEra Energy 등 전력/가스/수도 유틸리티",
    },
    "XLRE": {
        "분류": "미국 대표 섹터",
        "명칭": "Real Estate Select Sector SPDR",
        "추종 지수 / 설명": "Prologis 등 리츠 및 데이터센터 부동산",
    },
    "XLB": {
        "분류": "소재 & 원자재",
        "명칭": "Materials Select Sector SPDR",
        "추종 지수 / 설명": "Linde, Sherwin-Williams 등 화학/기초 소재",
    },
    "XME": {
        "분류": "소재 & 원자재",
        "명칭": "SPDR S&P Metals & Mining",
        "추종 지수 / 설명": "구리, 철강, 알루미늄, 채굴 기업",
    },
    "EFA": {
        "분류": "글로벌 주식",
        "명칭": "iShares MSCI EAEA ETF",
        "추종 지수 / 설명": "미국/캐나다 제외 유럽/아시아/호주 선진국 주식",
    },
    "EEM": {
        "분류": "글로벌 주식",
        "명칭": "iShares MSCI Emerging Markets",
        "추종 지수 / 설명": "한국, 대만, 중국, 인도 등 신흥국 주식",
    },
    "AGG": {
        "분류": "채권 & 안전자산",
        "명칭": "iShares Core U.S. Aggregate Bond",
        "추종 지수 / 설명": "미국 전체 투자등급 종합 채권",
    },
    "LQD": {
        "분류": "채권 & 안전자산",
        "명칭": "iShares iBoxx $ Inv Grade Corp",
        "추종 지수 / 설명": "미국 우량 기업 발행 투자등급 회사채",
    },
    "IEF": {
        "분류": "채권 & 안전자산",
        "명칭": "iShares 7-10 Year Treasury Bond",
        "추종 지수 / 설명": "미국 중기 국채 (7~10년 만기)",
    },
    "SHY": {
        "분류": "채권 & 안전자산",
        "명칭": "iShares 1-3 Year Treasury Bond",
        "추종 지수 / 설명": "미국 단기 국채 (1~3년 만기)",
    },
}

# 입력란 및 초기화 버튼
default_tickers = ", ".join(DEFAULT_ETF_DICT.keys())
col_input, col_reset = st.columns([4, 1])

with col_input:
    tickers_input = st.text_input("분석할 티커 목록 (쉼표로 구분)", default_tickers)

with col_reset:
    st.write(" ")
    st.write(" ")
    if st.button("🗑️ 전체 초기화"):
        st.session_state["last_search_results"] = []
        st.session_state["monthly_scores_db"] = {}
        st.session_state["custom_etf_info"] = {}
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        st.rerun()

submit_button = st.button("🚀 모멘텀 스코어 계산하기")


# ==============================================================================
# 4. 데이터 수집 및 과거 스코어 소급 계산 로직
# ==============================================================================
if submit_button:
    ticker_list = [
        t.strip().upper() for t in tickers_input.split(",") if t.strip()
    ]

    now = datetime.now()
    current_year_month = now.strftime("%Y-%m")
    current_run_results = []

    with st.spinner("과거 데이터 수집 및 월별 스코어 백테스팅 중..."):
        for ticker in ticker_list:
            try:
                yf_ticker = yf.Ticker(ticker)

                # 종목 기본 정보 설정
                if ticker in DEFAULT_ETF_DICT:
                    etf_name = DEFAULT_ETF_DICT[ticker]["명칭"]
                    etf_category = DEFAULT_ETF_DICT[ticker]["분류"]
                    etf_desc = DEFAULT_ETF_DICT[ticker]["추종 지수 / 설명"]
                elif ticker in st.session_state["custom_etf_info"]:
                    etf_name = st.session_state["custom_etf_info"][ticker][
                        "명칭"
                    ]
                    etf_category = st.session_state["custom_etf_info"][ticker][
                        "분류"
                    ]
                    etf_desc = st.session_state["custom_etf_info"][ticker][
                        "추종 지수 / 설명"
                    ]
                else:
                    info = yf_ticker.info
                    etf_name = (
                        info.get("longName")
                        or info.get("shortName")
                        or ticker
                    )
                    etf_category = info.get("quoteType", "기타 사용자 추가")
                    if etf_category == "ETF":
                        etf_category = "사용자 추가 ETF"
                    elif etf_category == "EQUITY":
                        etf_category = "개별 주식"

                    etf_desc = (
                        info.get("category")
                        or info.get("industry")
                        or info.get("summary", "상세 설명 없음")
                    )

                    st.session_state["custom_etf_info"][ticker] = {
                        "분류": etf_category,
                        "명칭": etf_name,
                        "추종 지수 / 설명": etf_desc,
                    }

                # 과거 3년 시세 수집
                data = yf_ticker.history(
                    period="3y", interval="1d", auto_adjust=False
                )

                if data.empty:
                    st.warning(f"{ticker}: 데이터를 가져올 수 없습니다.")
                    continue

                close_prices = data["Close"].dropna()

                try:
                    prices = close_prices.resample("ME").last().dropna()
                except Exception:
                    prices = close_prices.resample("M").last().dropna()

                # 진행 중인 이번 달 데이터 제외
                if (
                    not prices.empty
                    and prices.index[-1].strftime("%Y-%m") == current_year_month
                ):
                    prices = prices.iloc[:-1]

                if len(prices) >= 13:
                    if ticker not in st.session_state["monthly_scores_db"]:
                        st.session_state["monthly_scores_db"][ticker] = {}

                    st.session_state["monthly_scores_db"][ticker]["종목명"] = (
                        etf_name
                    )

                    # 과거 최대 12개 월말 기준 과거 히스토리 스코어 소급 계산
                    max_lookback = min(12, len(prices) - 12)
                    for offset in range(max_lookback, -1, -1):
                        end_idx = len(prices) - offset
                        sub_prices = prices.iloc[:end_idx]

                        if len(sub_prices) >= 13:
                            p_curr = sub_prices.iloc[-1]
                            p_1 = sub_prices.iloc[-2]
                            p_3 = sub_prices.iloc[-4]
                            p_6 = sub_prices.iloc[-7]
                            p_12 = sub_prices.iloc[-13]

                            dt_raw = sub_prices.index[-1].strftime("%Y-%m-%d")

                            r1 = (p_curr - p_1) / p_1
                            r3 = (p_curr - p_3) / p_3
                            r6 = (p_curr - p_6) / p_6
                            r12 = (p_curr - p_12) / p_12

                            score = (
                                (12 * r1) + (4 * r3) + (2 * r6) + (1 * r12)
                            )
                            score_rounded = round(score, 2)

                            # DB에 저장
                            st.session_state["monthly_scores_db"][ticker][
                                dt_raw
                            ] = score_rounded

                            if offset == 0:
                                current_run_results.append({
                                    "티커": ticker,
                                    "종목명": etf_name,
                                    "자산 분류": etf_category,
                                    "기준 월말일": format_date_to_kor(
                                        dt_raw
                                    ),
                                    "기준 월말가 ($)": round(p_curr, 2),
                                    "모멘텀 점수": score_rounded,
                                    "1개월 수익률": f"{r1 * 100:.2f}%",
                                    "3개월 수익률": f"{r3 * 100:.2f}%",
                                    "6개월 수익률": f"{r6 * 100:.2f}%",
                                    "12개월 수익률": f"{r12 * 100:.2f}%",
                                })

                else:
                    st.warning(
                        f"{ticker}: 과거 데이터 수량이 부족합니다. (최소"
                        " 13개월 필요)"
                    )
            except Exception as e:
                st.error(f"{ticker} 데이터 조회 중 오류 발생: {e}")

    save_history(st.session_state["monthly_scores_db"])
    st.session_state["last_search_results"] = current_run_results


# ==============================================================================
# 5. 누적 DB 최근 월 기준 Top 3 지표 카드
# ==============================================================================
if st.session_state["monthly_scores_db"]:
    st.markdown("---")

    db_df = (
        pd.DataFrame.from_dict(
            st.session_state["monthly_scores_db"], orient="index"
        )
        .reset_index()
        .rename(columns={"index": "티커"})
    )

    date_cols = [c for c in db_df.columns if c not in ["티커", "종목명"]]
    date_cols = sorted(date_cols, reverse=True)

    if date_cols:
        latest_raw_date = date_cols[0]
        latest_display_date = format_date_to_kor(latest_raw_date)
        st.subheader(f"🔥 {latest_display_date} 모멘텀 스코어 Top 3")

        top3_df = (
            db_df.dropna(subset=[latest_raw_date])
            .sort_values(by=latest_raw_date, ascending=False)
            .head(3)
            .reset_index(drop=True)
        )

        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]

        for i in range(3):
            with cols[i]:
                if i < len(top3_df):
                    row = top3_df.iloc[i]
                    score_val = row[latest_raw_date]
                    delta_type = "normal" if score_val > 0 else "inverse"
                    st.metric(
                        label=f"Rank {i+1}: {row['티커']} ({row['종목명']})",
                        value=f"{score_val:.2f} 점",
                        delta=f"{'양수 (+)' if score_val > 0 else '음수 (-)'}",
                        delta_color=delta_type,
                    )
                else:
                    st.metric(label=f"Rank {i+1}: 데이터 없음", value="-")


# ==============================================================================
# 6. 검색 종목 상세 표
# ==============================================================================
if st.session_state["last_search_results"]:
    st.markdown("---")
    st.subheader("📋 검색 종목 상세 모멘텀 현황")

    search_df = pd.DataFrame(st.session_state["last_search_results"])
    search_df = search_df.sort_values(
        by="모멘텀 점수", ascending=False
    ).reset_index(drop=True)
    search_df.index = search_df.index + 1

    st.dataframe(search_df, use_container_width=True)


# ==============================================================================
# 7. 전체 누적 종목 월별 모멘텀 점수 비교 표 (Top 3 색상 강조 & 범례 추가)
# ==============================================================================
if st.session_state["monthly_scores_db"]:
    st.markdown("---")
    st.subheader("📊 월별 모멘텀 스코어 비교표")

    history_df = (
        pd.DataFrame.from_dict(
            st.session_state["monthly_scores_db"], orient="index"
        )
        .reset_index()
        .rename(columns={"index": "티커"})
    )

    cols = list(history_df.columns)
    date_cols = [c for c in cols if c not in ["티커", "종목명"]]
    date_cols = sorted(date_cols, reverse=True)

    ordered_cols = ["티커", "종목명"] + date_cols
    history_df = history_df[ordered_cols]

    if date_cols:
        latest_col = date_cols[0]
        history_df = history_df.sort_values(
            by=latest_col, ascending=False, na_position="last"
        ).reset_index(drop=True)

    history_df.index = history_df.index + 1

    # 컬럼명을 'YY년 M월 기준'으로 변경한 디스플레이용 데이터프레임
    column_renames = {d: format_date_to_kor(d) for d in date_cols}
    display_df = history_df.rename(columns=column_renames)
    formatted_date_cols = [format_date_to_kor(d) for d in date_cols]

    # 각 월별 열 기준 Top 3 색상 하이라이트 스타일 함수
    def highlight_top3(column):
        if column.name not in formatted_date_cols:
            return [""] * len(column)

        numeric_vals = pd.to_numeric(column, errors="coerce")
        valid_vals = numeric_vals.dropna().unique()
        sorted_vals = sorted(valid_vals, reverse=True)

        styles = []
        for val in numeric_vals:
            if pd.isna(val) or len(sorted_vals) == 0:
                styles.append("")
            elif val == sorted_vals[0]:
                styles.append(
                    "background-color: #d4edda; color: #155724; font-weight:"
                    " bold;"
                )  # Top 1
            elif len(sorted_vals) > 1 and val == sorted_vals[1]:
                styles.append(
                    "background-color: #d1ecf1; color: #0c5460; font-weight:"
                    " bold;"
                )  # Top 2
            elif len(sorted_vals) > 2 and val == sorted_vals[2]:
                styles.append(
                    "background-color: #fff3cd; color: #856404; font-weight:"
                    " bold;"
                )  # Top 3
            else:
                styles.append("")
        return styles

    # 스타일 적용 후 표시
    styled_df = display_df.style.apply(highlight_top3, axis=0).format(
        na_rep="-", precision=2
    )
    st.dataframe(styled_df, use_container_width=True)

    # 표 하단 순위 색상 범례 안내 (HTML 스타일)
    legend_html = """
    <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-top: 8px; font-size: 14px;">
        <span style="font-weight: bold; color: #555;">💡 순위 범례 :</span>
        <span style="background-color: #d4edda; color: #155724; padding: 4px 10px; border-radius: 6px; font-weight: bold;">Top 1</span>
        <span style="background-color: #d1ecf1; color: #0c5460; padding: 4px 10px; border-radius: 6px; font-weight: bold;">Top 2</span>
        <span style="background-color: #fff3cd; color: #856404; padding: 4px 10px; border-radius: 6px; font-weight: bold;">Top 3</span>
    </div>
    """
    st.markdown(legend_html, unsafe_allow_html=True)


# ==============================================================================
# 8. 하단 통합 종목 정보 안내 표
# ==============================================================================
st.markdown("---")
st.subheader("📌 분석 섹터 및 자산 안내")

all_info_list = []s

for ticker, info in DEFAULT_ETF_DICT.items():
    all_info_list.append({
        "분류": info["분류"],
        "티커": ticker,
        "명칭": info["명칭"],
        "추종 지수 / 설명": info["추종 지수 / 설명"],
    })

for ticker, info in st.session_state["custom_etf_info"].items():
    all_info_list.append({
        "분류": f"✨ 추가된 종목 ({info['분류']})",
        "티커": ticker,
        "명칭": info["명칭"],
        "추종 지수 / 설명": info["추종 지수 / 설명"],
    })

info_df = pd.DataFrame(all_info_list)
info_df.index = info_df.index + 1

st.dataframe(info_df, use_container_width=True)
