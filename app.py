import os
import json
import logging
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import data_analyzer

# 1. 환경변수 로드 (.env 파일에서 읽어오기)
load_dotenv()

# 2. 로깅(Logging) 설정: 콘솔에 시간, 로그 레벨, 메시지 출력
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# 3. Flask 앱 인스턴스 생성
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default-dev-secret-key-1234")

# 환경변수에서 설정값 가져오기
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
PUBLIC_DATA_API_KEY = os.getenv("PUBLIC_DATA_API_KEY", "").strip()
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
FLASK_DEBUG = os.getenv("FLASK_ENV", "development").lower() == "development"


def get_local_macro_data():
    """
    외부 네트워크 통신 없이, 오직 data 폴더 내부의 공공데이터 CSV 파일들
    (한국무역보험공사, 근로복지공단, 국민연금공단)에서 직접 거시경제 및 개폐업 통계를 인출합니다.
    """
    return data_analyzer.get_local_macro_indicators()


def generate_gemini_analysis(industry, target_region, mode, macro_info, stats):
    """
    Gemini REST API를 호출하여 시장 진단 리포트를 생성합니다.
    data 폴더의 국세청/중기부 실데이터(stats)를 프롬프트에 주입하여
    팩트 기반의 정밀 분석 리포트를 도출합니다.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        logger.warning("[Gemini API] 유효한 GEMINI_API_KEY가 설정되지 않아 데모 모드 리포트를 생성합니다.")
        return generate_demo_report(industry, target_region, mode, macro_info, stats)

    # Gemini REST API 호출 주소 (안정적인 고속 모델 3.5-flash-lite)
    gemini_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={GEMINI_API_KEY}"

    # 전문가용 심층 리포트로 단일화된 상세 분석 가이드
    mode_description = "전문가용 심층 리포트 (재무 및 거시경제 지표, 기회비용 정밀 산출, 1년차 데스밸리 방어 및 3~7개년 비전 로드맵과 정책자금 연계 전략)"

    nts = stats.get("nts", {})
    costs = stats.get("costs", {}).get("breakdown", {})
    micro = stats.get("micro_profile", {})

    system_prompt = f"""당신은 대한민국 중소벤처기업부 및 창업진흥원, 외식/서비스업 실무 프랜차이즈 최고 전략 컨설턴트입니다.
창업 희망자가 입력한 구체적 아이템은 [{industry}]이며, 정부 공식 공공데이터(국세청 100대 업종 매칭: {stats.get('matched_industry')}, 목표 지역: {target_region})와 세부 특화 실무 데이터를 기반으로 맞춤형 리포트를 작성해주세요.

⚠️ [핵심 작성 지침 - 일반적/포괄적 요식업 서술 엄격 금지]
- '요식업', '외식업', '일반적인 매장'과 같은 두루뭉술하고 포괄적인 일반론적 서술을 엄격히 금지합니다.
- 반드시 사용자가 입력한 구체적인 아이템인 [{industry}]에 100% 집중하여, 해당 업종 특유의 용어(예: 치킨집이면 생닭/육계 원가율, 튀김기 설비, 닭 튀김 소요시간, 폐유 수거, 배달앱 수수료율, 일일 판매 마릿수 손익분기점 등)로 파고들어 작성하세요.

[실측 공공데이터 및 {industry} 세부 특화 실무 지표]
1. 세부 모델 분류: {micro.get('sub_category')}
2. 핵심 원가 구조: {micro.get('cost_model')}
3. 일일 손익분기점(BEP): {micro.get('daily_bep')}
4. 필수 특화 설비: {micro.get('key_facilities')}
5. 핵심 점검 요소: {json.dumps(micro.get('critical_factors', []), ensure_ascii=False)}
6. 국세청 100대 생활업종 사업자 실측 통계:
   - 전국 당월 사업자 수: {nts.get('national_current', 0):,}개소 (전년 동월 대비 증감률: {nts.get('national_yoy', 0)}%)
   - 목표 권역({nts.get('region_name')}) 사업자 수: {nts.get('region_current', 0):,}개소 (증감률: {nts.get('region_yoy', 0)}%)
   - 시장 진단 판정: {nts.get('saturation_level')} (포화도 지수: {nts.get('saturation_score')}/100)
7. 창업진흥원 실측 평균 창업비용:
   - 총 창업비용 평균: 약 {costs.get('total', 9500):,}만 원 (보증금 {costs.get('deposit', 2900):,}만 원, 시설인테리어비 {costs.get('facility', 2500):,}만 원, 원자재비 {costs.get('raw_materials', 2000):,}만 원, 권리금 {costs.get('premium', 1500):,}만 원, 가맹/기타 {costs.get('franchise', 100) + costs.get('others', 500):,}만 원)
8. 창업기업 연차별 매출액 기여도: 1년차(8.3% - 데스밸리) ➔ 2년차(15.1% - BEP) ➔ 3년차(16.4% - 정점) ➔ 7년차(13.8%)
9. data 폴더 원천 거시·노동 지표: 국내 물가상승률 {macro_info.get('inflation_rate')}, 경제성장률 {macro_info.get('gdp_growth')} (한국무역보험공사.csv), 전국 사업장 신규 대비 폐업 소멸률 {macro_info.get('closure_rate', '87.9%')} (근로복지공단.csv), 자영업 지역가입자 평균 월소득 {macro_info.get('self_employed_income', '163만 원')} (국민연금공단.csv)

[작성 가이드라인 - 반드시 포함할 5대 핵심 파트]
# 1. 📊 [{industry}] 세부 실무 시장 트렌드 및 경쟁 강도
- 일반 요식업이 아닌, [{industry}]의 배달 vs 홀 비중, 주요 프랜차이즈 및 개인 매장 간의 포화 실태와 최근 식자재/원자재가 동향 분석.
# 2. 🌊 레드오션 정밀 진단 및 틈새 차별화 필승 전략
- 인근 동종 매장과의 출혈 가격 경쟁을 피하기 위한 시그니처 메뉴(조리법, 독점 소스, 타겟층) 및 브랜딩 차별화 3대 공식.
# 3. 💰 [{industry}] 전용 초기 투자비용 분해 및 1년차 손익분기점(BEP) 계산
- 보증금, 권리금 외에 [{industry}] 필수 설비({micro.get('key_facilities')}) 비용과 원가 구조({micro.get('cost_model')})를 고려한 '일일 판매량 기준 손익분기점' 명시.
# 4. 🚀 청년 창업가를 위한 3개년 스케일업 비전 로드맵
- 1년차(데스밸리 방어, 단골 100명 확보 및 일일 BEP 달성) ➔ 2년차(객단가 인상 및 다각화) ➔ 3년차(시스템화 및 2호점/프랜차이즈 검토).
# 5. ✅ [{industry}] 특화 인허가 및 오픈 전 필수 실무 체크리스트
- 영업신고증, 위생교육, 전용 설비 감리, 배달대행 계약, 폐유 수거/배출 등 [{industry}]에 특화된 실무 체크박스.
"""

    payload = {
        "contents": [{"parts": [{"text": system_prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 3500}
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        logger.info(f"[Gemini API] 통계 연동 호출 시작 - 업종: {industry}, 모드: {mode}")
        response = requests.post(gemini_endpoint, headers=headers, json=payload, timeout=35)

        if response.status_code == 200:
            result_data = response.json()
            candidates = result_data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts and "text" in parts[0]:
                    generated_text = parts[0]["text"]
                    logger.info("[Gemini API] 호출 성공 및 응답 수신 완료")
                    return generated_text

            logger.error(f"[Gemini API] 응답 파싱 실패: {result_data}")
            return generate_demo_report(industry, target_region, mode, macro_info, stats)
        else:
            logger.error(f"[Gemini API] 오류 응답 코드: {response.status_code}, 메시지: {response.text}")
            return generate_demo_report(industry, target_region, mode, macro_info, stats, api_error=response.text)

    except requests.exceptions.Timeout:
        logger.error("[Gemini API] 요청 시간 초과 (Timeout)")
        return generate_demo_report(industry, target_region, mode, macro_info, stats, note="API 응답 시간이 지연되어 실측 데이터 템플릿으로 생성되었습니다.")
    except Exception as e:
        logger.error(f"[Gemini API] 호출 중 예외 발생: {e}")
        return generate_demo_report(industry, target_region, mode, macro_info, stats, note=str(e))


def generate_demo_report(industry, target_region, mode, macro_info, stats, note=None, api_error=None):
    """
    실측 데이터(stats)를 기반으로 생성되는 백업 정밀 리포트입니다.
    """
    mode_title = "전문가용 심층 리포트"
    nts = stats.get("nts", {})
    costs = stats.get("costs", {}).get("breakdown", {})

    notice_banner = ""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        notice_banner = "> ℹ️ **알림:** `.env`에 `GEMINI_API_KEY`가 미설정되어 **정부 실측 통계 데이터 템플릿**으로 정밀 리포트가 생성되었습니다.\n\n"
    elif api_error:
        notice_banner = f"> ⚠️ **Gemini API 연동 주의:** AI 호출 일시 오류로 **정부 실측 통계 데이터 기반 정밀 리포트**로 안전하게 전환되었습니다.\n\n"

    return f"""{notice_banner}# 📋 [{industry}] 데이터 기반 창업 진단 & 비전 리포트 ({mode_title})

- **목표 타겟/지역:** {target_region} (정부 통계 기준: {stats.get('matched_region', '전국')})
- **매칭 생활업종:** 국세청 100대 업종 분류 [{stats.get('matched_industry', industry)}]
- **참고 거시·노동 지표:** 물가상승률 {macro_info.get('inflation_rate', '1.6%')} (무역보험공사.csv), 전국 폐업소멸률 {macro_info.get('closure_rate', '87.9%')} (근로복지공단.csv), 자영업 평균월소득 {macro_info.get('self_employed_income', '163만 원')} (국민연금공단.csv)

---

## 1. 📊 실측 데이터 기반 시장 트렌드 및 기회 요인
- **전국 시장 규모:** 국세청 공식 집계 기준, 현재 전국 **{nts.get('national_current', 0):,}개소**의 사업자가 영업 중입니다.
- **성장률 추이:** 전년 동월 대비 전국 증감률은 **{nts.get('national_yoy', 0):+}%**, 목표 권역({nts.get('region_name')})은 **{nts.get('region_yoy', 0):+}%**를 기록하고 있습니다.
- **소비 트렌드:** 고물가 기조 속에서 가격 양극화(초가성비 vs 프리미엄 경험)가 뚜렷해지고 있어, 어설픈 중간 가격대 매장은 고객 유입이 급감하는 추세입니다.

---

## 2. 🌊 레드오션 vs 블루오션 정밀 진단 및 경쟁 강도
| 진단 지표 | 실측 통계값 | 시장 평가 및 대응 가이드 |
| :--- | :---: | :--- |
| **시장 포화도 진단** | **{nts.get('saturation_level')}** | 포화도 지수 **{nts.get('saturation_score')}/100**점. 단순 모방 창업 지양 |
| **전국 사업자 수** | **{nts.get('national_current', 0):,}개소** | 상권 내 기존 매장과의 물리적 거리 및 시그니처 메뉴 필수 |
| **권역별 성장세** | **{nts.get('region_yoy', 0):+}% (YoY)** | 최근 개폐업 변동성이 크므로 상권 유동인구 요일별 정밀 실측 필수 |

---

## 3. 💰 초기 투자비용 정밀 분석 및 1년차 데스밸리 방어 전략
### 중소벤처기업부 실측 평균 창업비용 구성
- **총 창업비용:** 평균 **약 {costs.get('total', 9500):,}만 원**
  - **임차 보증금:** 약 {costs.get('deposit', 2900):,}만 원
  - **인테리어 및 시설 설비:** 약 {costs.get('facility', 2500):,}만 원
  - **초기 원자재 및 부자재:** 약 {costs.get('raw_materials', 2000):,}만 원
  - **바닥 권리금:** 약 {costs.get('premium', 1500):,}만 원
  - **가맹비 / 인허가 / 기타:** 약 {costs.get('franchise', 100) + costs.get('others', 500):,}만 원

> 💡 **데스밸리(Death Valley) 생존 공식:**  
> 통계청 데이터상 창업기업의 **1년차 매출 비중은 전체 수명의 8.3%**에 불과합니다. 오픈 직후 바로 흑자가 나지 않으므로, 최소 6개월 치의 고정비(월세+인건비+관리비 약 1,500만 원 이상)를 **'예비 운영자금'**으로 반드시 별도 분리해 두어야 폐업을 방지할 수 있습니다.

---

## 4. 🚀 청년 창업가를 위한 차별화 시장 진입(GTM) 및 3개년 사업 비전 설계
1. **1년차 (생존 및 손익분기점 달성):**  
   - 무리한 외형 확장 지양, 소자본 린 스타트업 실행.
   - 인근 반경 500m 타겟 고객 100명의 충성 고객(단골) 명단 확보 및 네이버 플레이스 리뷰 200개 돌파.
2. **2년차 (매출 도약기 - 점유율 15.1% 구간):**  
   - 시그니처 대표 메뉴/상품의 객단가 인상 및 테이크아웃/배달/온라인 판매 다각화.
   - 중소벤처기업부 **청년전용창업자금** 또는 소상공인 정책자금을 연계하여 설비 고도화.
3. **3년차 (성장 정점기 - 점유율 16.4% 구간):**  
   - 표준화된 운영 매뉴얼 완성으로 대표자 없이도 돌아가는 오토 매장화.
   - 2호점 출점 또는 프랜차이즈/라이선스 비즈니스 모델로 스케일업.

---

## 5. ✅ 단계별 실행 체크리스트
- [ ] **D-90 (시장 검증):** 국세청 상권 내 동일 업종 5곳 직접 방문 후 장단점 분석표 작성
- [ ] **D-60 (자금 및 행정):** 총 예산의 30% 이상을 예비비로 편성, 사업자등록 및 위생/영업신고 준비
- [ ] **D-30 (공간 및 브랜딩):** 보증금 및 권리금 계약서 특약사항(원상복구 범위 등) 법률 검토
- [ ] **D-15 (사전 마케팅):** 네이버 스마트플레이스 등록, 인스타그램 릴스 사전 오픈 티저 영상 업로드
- [ ] **D-Day (정식 런칭):** 첫 방문 고객 대상 재방문 유도 쿠폰 증정 및 피드백 실시간 기록
"""


def generate_gemini_followup(question, industry, target_region, macro_info, stats):
    """
    사용자의 추가 질문에 대해 동일한 공공데이터 실측치를 연동하여
    Gemini AI 기반 맞춤형 추가 답변을 생성합니다.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        return generate_demo_followup(question, industry, target_region, stats)

    gemini_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={GEMINI_API_KEY}"

    nts = stats.get("nts", {})
    costs = stats.get("costs", {}).get("breakdown", {})
    micro = stats.get("micro_profile", {})

    system_prompt = f"""당신은 대한민국 청년 창업 최고 전략 수석 컨설턴트입니다.
현재 창업 희망자가 [{industry}] (정부 통계 매칭: {stats.get('matched_industry')}, 세부 모델: {micro.get('sub_category')}, 목표 지역: {target_region})에 대한 전문가 심층 리포트를 확인한 뒤 추가 질문을 제출했습니다.

⚠️ [핵심 주의]
- '요식업', '외식업'과 같은 포괄적 표현 대신 [{industry}]의 고유한 실무 운영 요소(원가율: {micro.get('cost_model')}, 손익분기점: {micro.get('daily_bep')}, 필수 장비: {micro.get('key_facilities')})를 직접 인용하여 세밀하게 답변해주세요.

[보유한 실측 공공데이터 지표]
- 국세청 100대 업종: 전국 {nts.get('national_current', 0):,}개소 (증감률 {nts.get('national_yoy', 0)}%), 목표 권역 {nts.get('region_name')} {nts.get('region_current', 0):,}개소 (증감률 {nts.get('region_yoy', 0)}%), 시장 포화도: {nts.get('saturation_level')}
- 창업진흥원 평균 창업비용: 총 {costs.get('total', 9500):,}만 원 (보증금 {costs.get('deposit', 2900):,}만 원, 시설인테리어비 {costs.get('facility', 2500):,}만 원, 원자재비 {costs.get('raw_materials', 2000):,}만 원, 권리금 {costs.get('premium', 1500):,}만 원)
- 연차별 매출액 기여도: 1년차(8.3% 데스밸리 구간) ➔ 2년차(15.1% BEP 도전) ➔ 3년차(16.4% 정점)
- 국내 거시지표: 소비자물가상승률 {macro_info.get('inflation_rate')}, GDP성장률 {macro_info.get('gdp_growth')}

[사용자의 추가 질문]
"{question}"

[답변 작성 가이드]
- 위 실측 수치와 [{industry}] 전용 실무 수치({micro.get('cost_model')})를 직접 수식/예시로 계산하여 명확하고 구체적인 실행 행동 지침(Action Plan)을 작성하세요.
"""

    payload = {
        "contents": [{"parts": [{"text": system_prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2500}
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        logger.info(f"[추가 질문 Gemini API 호출] 업종: {industry}, 질문: {question[:30]}...")
        response = requests.post(gemini_endpoint, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            result_data = response.json()
            candidates = result_data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts and "text" in parts[0]:
                    return parts[0]["text"]
        logger.error(f"[추가 질문 Gemini API 오류] 응답 코드: {response.status_code}, 메시지: {response.text}")
        return generate_demo_followup(question, industry, target_region, stats)
    except Exception as e:
        logger.error(f"[추가 질문 호출 예외] {e}")
        return generate_demo_followup(question, industry, target_region, stats)


def generate_demo_followup(question, industry, target_region, stats):
    """추가 질문 데모 답변 템플릿"""
    nts = stats.get("nts", {})
    costs = stats.get("costs", {}).get("breakdown", {})
    return f"""### 💡 [{industry}] 추가 질문에 대한 전문가 답변

> **질문:** "{question}"

---

#### 1. 📊 실측 데이터 기반 핵심 진단
- **상권 및 경쟁 강도:** 목표 권역({nts.get('region_name')}) 내 동종 업소 수는 현재 **{nts.get('region_current', 0):,}개소**로, 시장 포화도는 **{nts.get('saturation_level')}** 상태입니다.
- **예상 자본 구조:** 평균 초기 자본금 **약 {costs.get('total', 9500):,}만 원** 중 회수 가능 자산(보증금 {costs.get('deposit', 2900):,}만 원)을 제외한 소모성 초기 투자비(시설비 등 약 {costs.get('facility', 2500):,}만 원)의 감가상각을 36개월 균등 분할로 상각 계획을 세워야 합니다.

#### 2. 🎯 질문 맞춤형 실행 가이드 (Action Plan)
1. **손익분기점(BEP) 관리:** 1년차 매출 비중(8.3%)을 감안하여 월 고정비(임대료+인건비+공과금)의 최소 1.5배 이상을 손익분기 월 매출 목표로 수립하세요.
2. **청년 전용 정책금융 활용:** 사업자등록 후 3개월 이내 중소벤처기업진흥공단 **청년전용창업자금**(연 2%대 고정금리, 최대 1억 원) 신청을 병행하여 자금 압박을 완화하세요.
3. **지역 밀착형 마케팅:** 오프라인 매장의 경우 반경 500m 이내 네이버 스마트플레이스 로컬SEO 최적화 및 당근마켓 지역 광고를 오픈 2주 전부터 집중 집행하는 것이 가장 효과적입니다.
"""


# 4. 라우트(Route) 정의

@app.route("/")
def index():
    logger.info(f"[페이지 접속] 사용자 접속 - IP: {request.remote_addr}")
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True)
    if not data:
        logger.warning(f"[검증 실패] JSON 형식의 요청 데이터가 없습니다. - IP: {request.remote_addr}")
        return jsonify({
            "success": False,
            "error": "요청 데이터가 올바르지 않습니다. JSON 형식으로 전달해주세요."
        }), 400

    industry = data.get("industry", "").strip()
    target_region = data.get("target_region", "").strip()
    # 전문가용 심층 리포트로 단일화
    mode = "pro"

    if not industry:
        logger.warning(f"[검증 실패] 업종명이 입력되지 않았습니다. - IP: {request.remote_addr}")
        return jsonify({
            "success": False,
            "error": "관심 업종을 입력해주세요. (예: 감성 디저트 카페, 24시 무인 스터디카페 등)"
        }), 400

    if len(industry) > 50 or len(target_region) > 50:
        return jsonify({
            "success": False,
            "error": "입력값은 50자 이하로 간결하게 입력해주세요."
        }), 400

    if not target_region:
        target_region = "전국 / 2030 청년층"



    logger.info(f"[분석 요청 접수] 업종: '{industry}', 타겟: '{target_region}', 모드: '{mode}' - IP: {request.remote_addr}")

    try:
        # 1. data 폴더의 공공데이터 CSV 통합 정밀 분석
        stats = data_analyzer.analyze_startup_data(industry, target_region)
        logger.info(f"[공공데이터 정밀 분석 완료] 매칭 업종: {stats['matched_industry']}, 매칭 지역: {stats['matched_region']}")

        # 2. data 폴더 원천 거시경제 및 고용 지표 인출
        macro_info = stats.get("macro") or get_local_macro_data()

        # 3. Gemini AI 기반 실데이터 연동 진단 리포트 생성
        report_markdown = generate_gemini_analysis(industry, target_region, mode, macro_info, stats)

        logger.info(f"[분석 완료] '{industry}'에 대한 리포트 생성 성공")

        return jsonify({
            "success": True,
            "industry": industry,
            "target_region": target_region,
            "mode": mode,
            "report_markdown": report_markdown,
            "macro_info": macro_info,
            "stats": stats
        }), 200

    except Exception as e:
        logger.error(f"[서버 오류 발생] 진단 처리 중 예외 발생: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"서버에서 분석 리포트를 생성하는 중 오류가 발생했습니다: {str(e)}"
        }), 500


@app.route("/ask", methods=["POST"])
def ask():
    """
    분석 결과에 대한 후속 질의응답(Q&A) API:
    사용자가 질문을 제출하면 동일한 업종/지역의 공공데이터 실측치를 즉각 연동하여
    Gemini AI가 정밀 분석 답변을 반환합니다.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "요청 데이터가 없습니다."}), 400

    question = data.get("question", "").strip()
    industry = data.get("industry", "").strip()
    target_region = data.get("target_region", "").strip()

    if not question:
        return jsonify({"success": False, "error": "질문 내용을 입력해주세요."}), 400

    if not industry:
        industry = "창업 일반"

    if not target_region:
        target_region = "전국"

    logger.info(f"[추가 질의 접수] 업종: '{industry}', 지역: '{target_region}', 질문: '{question[:40]}...'")

    try:
        # 1. 동일한 로직으로 data 폴더 CSV 원천 통계 인출
        stats = data_analyzer.analyze_startup_data(industry, target_region)
        macro_info = stats.get("macro") or get_local_macro_data()

        # 2. Gemini AI 추가 분석 답변 생성
        answer_markdown = generate_gemini_followup(question, industry, target_region, macro_info, stats)

        logger.info(f"[추가 질의 답변 완료] 질문: '{question[:20]}...'")

        return jsonify({
            "success": True,
            "question": question,
            "industry": industry,
            "target_region": target_region,
            "answer_markdown": answer_markdown,
            "stats": stats
        }), 200

    except Exception as e:
        logger.error(f"[추가 질의 오류] {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"추가 분석 중 오류가 발생했습니다: {str(e)}"
        }), 500


if __name__ == "__main__":
    logger.info("==================================================")
    logger.info("🚀 청년 창업 체크리스트 웹 서버 시작")
    logger.info(f"📍 접속 주소: http://127.0.0.1:{FLASK_PORT}")
    logger.info(f"⚙️ 디버그 모드: {FLASK_DEBUG}")
    logger.info(f"🔑 Gemini API 키 설정 여부: {'설정 완료' if (GEMINI_API_KEY and GEMINI_API_KEY != 'your_gemini_api_key_here') else '미설정 (데모 모드로 동작)'}")
    logger.info("==================================================")

    app.run(host="0.0.0.0", port=FLASK_PORT, debug=FLASK_DEBUG)
