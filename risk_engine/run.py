"""
============================================================================
기업 리스크 조기경보 시스템 v10.0 - 실행 파일
============================================================================
사용법: python run.py
"""

from risk_engine import RiskWarningSystem

# ==============================================================================
# ⚙️ 설정 (여기만 수정하세요)
# ==============================================================================

# 분석할 기업 목록
COMPANIES = [
    # "삼성전자",
    "SK하이닉스",
    # "LG전자",
    # 추가할 기업 이름을 여기에 입력
]

# 데이터 초기화 여부 (True: 기존 데이터 삭제 후 새로 분석)
RESET_DATA = True

# 고도화 기능 사용 여부 (알림, 타임라인, 지표 출력)
USE_ENHANCED_FEATURES = True

# KIPRIS 특허청 API 사용 여부 (False: 뉴스만 사용, API 호출 절약)
# ⚠️ 개인 무료 한도: 월 1,000건 (기업당 1회 호출)
USE_KIPRIS = False  # 🏆 경진대회 데모 안정성: KIPRIS API 비활성화

# ==============================================================================
# 🚀 실행 (아래는 수정하지 마세요)
# ==============================================================================

if __name__ == "__main__":
    # 시스템 초기화
    system = RiskWarningSystem(reset_data=RESET_DATA, use_kipris=USE_KIPRIS)
    
    print(f"\n📋 {len(COMPANIES)}개 기업 분석 시작...\n")
    
    if USE_ENHANCED_FEATURES:
        # 고도화 기능 포함 분석
        for company in COMPANIES:
            result = system.full_analysis(company)
            if result:
                # 알림 출력
                alerts = result.get('alerts', [])
                if alerts:
                    print(f"\n   🔔 알림 ({len(alerts)}건):")
                    for alert in alerts[:3]:
                        print(f"      [{alert['severity'].upper()}] {alert['content'][:50]}...")
                
                # 타임라인 출력
                timeline = result.get('timeline', [])
                if timeline:
                    print(f"\n   📅 타임라인 ({len(timeline)}건):")
                    for event in timeline[:3]:
                        print(f"      • {event['date'][:10] if event.get('date') else 'N/A'}: {event['label']}")
                
                # 지표 출력
                metrics = result.get('metrics', {})
                if metrics:
                    print(f"\n   📊 주요 지표 (Mock):")
                    ltv = metrics.get('ltv', {})
                    print(f"      LTV: {ltv.get('current', 'N/A')} ({ltv.get('trend', '')})")
                    print(f"      EBITDA: {metrics.get('ebitda', 'N/A')}")
                    print(f"      Covenant: {metrics.get('covenant', 'N/A')}")
        
        # 전이 재계산
        system.recalc_propagation()
    else:
        # 기본 분석만
        system.batch_analyze(COMPANIES)
    
    # 결과 출력
    system.show_leaderboard(10)
    system.show_summary()
    
    print("\n✅ 분석 완료!")
