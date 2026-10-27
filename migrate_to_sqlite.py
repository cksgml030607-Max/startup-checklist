"""
migrate_to_sqlite.py
data 폴더의 CSV 데이터들을 설계된 스키마에 맞춰
로컬 SQLite 데이터베이스(startup.db)로 마이그레이션하는 스크립트입니다.
(Python 표준 라이브러리 sqlite3, csv, os, json만 사용)
"""

import os
import csv
import json
import sqlite3
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "startup.db")

INDUSTRY_SYNONYMS = {
    "카페": "커피음료점", "커피": "커피음료점", "디저트": "커피음료점",
    "베이커리": "제과점", "빵": "제과점", "치킨": "치킨집", "통닭": "치킨집",
    "피자": "패스트푸드점", "햄버거": "패스트푸드점", "버거": "패스트푸드점",
    "분식": "분식점", "떡볶이": "분식점", "김밥": "분식점",
    "호프": "기타주점", "주점": "기타주점", "술집": "기타주점",
    "편의점": "편의점", "무인": "편의점", "헬스": "헬스클럽", "피트니스": "헬스클럽",
    "필라테스": "스포츠시설운영업", "체육": "스포츠시설운영업",
    "미용실": "미용실", "헤어": "미용실", "네일": "피부관리업", "피부": "피부관리업",
    "스터디": "독서실", "독서실": "독서실", "pc": "pc방", "피시방": "pc방",
    "식당": "기타음식점", "음식점": "기타음식점", "한식": "한식음식점",
    "중식": "중식음식점", "일식": "일식음식점", "양식": "기타외국식음식점",
    "옷": "옷가게", "의류": "옷가게", "쇼핑몰": "통신판매업", "이커머스": "통신판매업",
    "전자상거래": "통신판매업", "학원": "교습학원", "과외": "교습소ㆍ공부방",
    "꽃": "꽃가게", "플라워": "꽃가게", "세탁": "세탁소", "빨래": "세탁소",
    "부동산": "부동산중개업", "공인중개사": "부동산중개업", "모텔": "여관ㆍ모텔",
    "호텔": "여관ㆍ모텔", "펜션": "여관ㆍ모텔", "게스트하우스": "여관ㆍ모텔",
    "노래방": "노래방", "당구장": "당구장", "골프": "골프연습장", "문구": "문구점",
    "서점": "서점", "정육": "정육점", "슈퍼": "슈퍼마켓", "마트": "슈퍼마켓",
    "과일": "과일가게", "가구": "가구점", "안경": "안경점", "철물": "철물점",
    "약국": "약국", "동물병원": "동물병원", "애완": "애완용품점", "사진": "사진관"
}

SIDO_LIST = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
    "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도",
    "충청북도", "충청남도", "전북특별자치도", "전라남도", "경상북도",
    "경상남도", "제주특별자치도"
]


def init_db(conn):
    """테이블 생성"""
    cur = conn.cursor()

    cur.executescript("""
    -- 1. 업종 마스터
    CREATE TABLE IF NOT EXISTS industries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL,
        synonyms_json TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_ind_name ON industries(name);

    -- 2. 행정구역 마스터
    CREATE TABLE IF NOT EXISTS regions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sido_name TEXT NOT NULL,
        sigungu_name TEXT,
        region_zone TEXT NOT NULL
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_reg_sido_sigungu ON regions(sido_name, sigungu_name);

    -- 3. 국세청 100대 생활업종 시계열 통계
    CREATE TABLE IF NOT EXISTS nts_business_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        industry_name TEXT NOT NULL,
        sido_name TEXT NOT NULL,
        sigungu_name TEXT NOT NULL,
        base_year_month TEXT NOT NULL,
        current_count INTEGER NOT NULL,
        prev_month_count INTEGER DEFAULT 0,
        prev_year_count INTEGER DEFAULT 0,
        mom_change_rate REAL DEFAULT 0.0,
        yoy_change_rate REAL DEFAULT 0.0
    );
    CREATE INDEX IF NOT EXISTS idx_nts_ind_sido ON nts_business_metrics(industry_name, sido_name);

    -- 4. 창업비용 통계
    CREATE TABLE IF NOT EXISTS startup_costs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_type TEXT NOT NULL,
        target_name TEXT NOT NULL,
        total_cost INTEGER NOT NULL,
        deposit_cost INTEGER NOT NULL,
        facility_cost INTEGER NOT NULL,
        raw_material_cost INTEGER NOT NULL,
        premium_cost INTEGER DEFAULT 0,
        franchise_fee INTEGER DEFAULT 0,
        others_cost INTEGER DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_cost_target ON startup_costs(target_name);

    -- 5. 연차별 매출액 기여도
    CREATE TABLE IF NOT EXISTS startup_lifecycles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operating_year TEXT NOT NULL UNIQUE,
        revenue_share REAL NOT NULL,
        growth_stage_desc TEXT NOT NULL
    );

    -- 6. 사업장 입지 분포
    CREATE TABLE IF NOT EXISTS location_distributions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_type TEXT NOT NULL UNIQUE,
        ratio REAL NOT NULL,
        description TEXT
    );

    -- 7. 사용자 분석 이력 로그
    CREATE TABLE IF NOT EXISTS analysis_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        industry TEXT NOT NULL,
        region TEXT,
        mode TEXT,
        report_markdown TEXT,
        client_ip TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    print("✅ 데이터베이스 테이블 생성 완료")


def import_nts_data(conn):
    """국세청 100대 생활업종 데이터 적재"""
    nts_file = os.path.join(DATA_DIR, "국세청_사업자현황_100대 생활업종_20260831.csv")
    if not os.path.exists(nts_file):
        print("⚠️ 국세청 CSV 파일이 없습니다.")
        return

    cur = conn.cursor()
    cur.execute("DELETE FROM nts_business_metrics;")
    cur.execute("DELETE FROM industries;")
    cur.execute("DELETE FROM regions;")

    industries_set = set()
    regions_set = set()
    records = []

    with open(nts_file, encoding="utf-8-sig") as f:
        r = csv.reader(f)
        header = next(r)
        for row in r:
            if not row or len(row) < 6:
                continue
            ind = row[0].strip()
            sido = row[1].strip()
            sigungu = row[2].strip()
            cur_val = int(row[3].strip().replace(",", "") or 0)
            prev_val = int(row[4].strip().replace(",", "") or 0)
            py_val = int(row[5].strip().replace(",", "") or 0)

            mom = round(((cur_val - prev_val) / prev_val * 100), 2) if prev_val else 0.0
            yoy = round(((cur_val - py_val) / py_val * 100), 2) if py_val else 0.0

            industries_set.add(ind)
            regions_set.add((sido, sigungu))

            records.append((ind, sido, sigungu, "2026-08", cur_val, prev_val, py_val, mom, yoy))

    # 1. industries 적재
    ind_records = []
    for ind in sorted(industries_set):
        synonyms = [k for k, v in INDUSTRY_SYNONYMS.items() if v == ind]
        category = "음식점업" if "음식" in ind or "카페" in ind or "점" in ind else "기타서비스업"
        ind_records.append((ind, category, json.dumps(synonyms, ensure_ascii=False)))

    cur.executemany("INSERT INTO industries (name, category, synonyms_json) VALUES (?, ?, ?);", ind_records)

    # 2. regions 적재
    reg_records = []
    for sido, sigungu in regions_set:
        zone = "수도권" if sido in ["서울특별시", "경기도", "인천광역시"] else ("광역시" if "광역시" in sido else "비수도권")
        reg_records.append((sido, sigungu, zone))
    cur.executemany("INSERT INTO regions (sido_name, sigungu_name, region_zone) VALUES (?, ?, ?);", reg_records)

    # 3. metrics 적재 (대량 배치 INSERT)
    cur.executemany("""
    INSERT INTO nts_business_metrics 
    (industry_name, sido_name, sigungu_name, base_year_month, current_count, prev_month_count, prev_year_count, mom_change_rate, yoy_change_rate)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, records)

    conn.commit()
    print(f"✅ 국세청 데이터 적재 완료: {len(records):,} 건, 업종 {len(industries_set)}개, 행정구역 {len(regions_set)}개")


def import_cost_data(conn):
    """창업비용 데이터 적재"""
    cost_file = os.path.join(DATA_DIR, "창업비용_평균__20261027114949.csv")
    if not os.path.exists(cost_file):
        return

    cur = conn.cursor()
    cur.execute("DELETE FROM startup_costs;")

    records = []
    with open(cost_file, encoding="utf-8-sig") as f:
        r = list(csv.reader(f))
        for row in r[3:]:
            if not row or len(row) < 10:
                continue
            cat1, cat2 = row[0].strip(), row[1].strip()
            total = int(row[3] or 0)
            deposit = int(row[4] or 0)
            premium = int(row[5] or 0)
            facility = int(row[6] or 0)
            raw_mat = int(row[7] or 0)
            franchise = int(row[8] or 0)
            others = int(row[9] or 0)
            records.append((cat1, cat2, total, deposit, facility, raw_mat, premium, franchise, others))

    cur.executemany("""
    INSERT INTO startup_costs 
    (category_type, target_name, total_cost, deposit_cost, facility_cost, raw_material_cost, premium_cost, franchise_fee, others_cost)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, records)
    conn.commit()
    print(f"✅ 창업비용 데이터 적재 완료: {len(records)} 건")


def import_lifecycle_data(conn):
    """연차별 매출 비중 적재"""
    cur = conn.cursor()
    cur.execute("DELETE FROM startup_lifecycles;")

    data = [
        ("1년차", 8.3, "초기 시장 진입 및 데스밸리 구간 (매출 저조, 고객 확보 집중)"),
        ("2년차", 15.1, "손익분기점 도전 및 충성 고객 확보 단계"),
        ("3년차", 16.4, "성장 정점 도달 (본격 이익 실현 및 시장 안착)"),
        ("4년차", 16.1, "안정화 및 시설·마케팅 재투자 시기"),
        ("5년차", 15.6, "경쟁 심화 대응 및 서비스 리뉴얼 단계"),
        ("6년차", 14.6, "성숙기 (단골 고객 중심 유지 관리)"),
        ("7년차", 13.8, "장기 존속 기업 안착")
    ]
    cur.executemany("INSERT INTO startup_lifecycles (operating_year, revenue_share, growth_stage_desc) VALUES (?, ?, ?);", data)
    conn.commit()
    print("✅ 연차별 매출 사이클 데이터 적재 완료")


def import_location_data(conn):
    """입지 유형 데이터 적재"""
    cur = conn.cursor()
    cur.execute("DELETE FROM location_distributions;")

    data = [
        ("일반상업지역", 62.9, "역세권 및 번화가 중심, 유동인구 최대 집객, 높은 임대료"),
        ("일반주택지역", 19.6, "아파트 및 주거 밀착형 상권, 안정적 단골 확보 유리"),
        ("산업단지 및 지식산업센터", 8.5, "B2B 제조/IT 특화 입지, 평일 집중 소비"),
        ("대학 및 연구단지", 0.2, "20대 청년층 타겟, 방학 비수기 존재"),
        ("기타 외곽 및 무점포(온라인)", 8.8, "창고형 매장 또는 1인 이커머스")
    ]
    cur.executemany("INSERT INTO location_distributions (location_type, ratio, description) VALUES (?, ?, ?);", data)
    conn.commit()
    print("✅ 입지 분포 데이터 적재 완료")


def main():
    t0 = time.time()
    print(f"🚀 SQLite 마이그레이션 시작 -> DB 경로: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        import_nts_data(conn)
        import_cost_data(conn)
        import_lifecycle_data(conn)
        import_location_data(conn)
        print(f"🎉 마이그레이션 성공! (소요 시간: {time.time()-t0:.2f}초)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
