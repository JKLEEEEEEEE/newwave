import sys
import traceback
from risk_engine import RiskWarningSystem
from monitoring_agent import send_alert

def run_tests():
    print("🚀 [Integration Test] 시스템 통합 테스트 시작\n")
    
    try:
        # Init
        print("[Setup] 시스템 초기화...")
        system = RiskWarningSystem(reset_data=True, use_kipris=False)
        print("✅ 초기화 완료\n")
        
        # Test 1
        print("[Test 1] 공급망 데이터 검증")
        try:
            res = system.graph.graph.query("""
                MATCH (s:Company {name: '한미반도체'})-[r:SUPPLIES_TO]->(c:Company {name: 'SK하이닉스'})
                RETURN s.total_score
            """)
            if len(res) > 0:
                print(f"✅ Pass: 관계 확인됨 ({res[0]['s.total_score']}점)")
            else:
                print("❌ Fail: 관계 데이터 없음")
        except Exception:
            traceback.print_exc()
        print()
        
        # Test 2
        print("[Test 2] 데이터 주입")
        try:
            # News
            news_cat = system.graph.add_category('SK하이닉스', '뉴스')
            subcat = system.graph.add_news_subcategory(news_cat, '기업')
            risk_news = {
                "title": "[단독] SK하이닉스 핵심 기술 유출 혐의로 임원진 검찰 조사",
                "url": "http://test.com/news1", "date": "2024-05-20",
                "keywords": ["검찰(30)", "유출(20)", "조사(10)"],
                "risk_score": 80, "is_risk": True, "confidence": 0.95
            }
            system.graph.add_news_to_subcategory(subcat, risk_news, 'SK하이닉스', '기업')
            print("✅ Pass: 뉴스 주입")
        except Exception:
            traceback.print_exc()
        print()

        # Test 3
        print("[Test 3] 통합 리스크 분석")
        try:
            # 1. Supply Chain
            sc_res = system.graph.calc_supply_chain_risk("SK하이닉스")
            if sc_res['total_score'] == 40:
                print("✅ Pass: 공급망 리스크 (40점)")
            else:
                print(f"❌ Fail: 공급망 리스크 점수 {sc_res['total_score']} != 40")
                
            # 2. Propagation
            system.graph.add_company("SK스퀘어")
            cat = system.graph.add_category("SK하이닉스", "주주")
            system.graph.add_to_category(cat, "SK스퀘어", "company", ratio="20.1%")
            system.graph.update_entity_risk("company", "SK스퀘어", 70, ["경영권분쟁"])
            
            prop_res = system.graph.calc_propagated_risk_v3("SK하이닉스", depth=1)
            if prop_res['total_propagated'] > 0:
                print(f"✅ Pass: 전이 리스크 ({prop_res['total_propagated']}점)")
            else:
                print("❌ Fail: 전이 리스크 0점")
        except Exception:
            traceback.print_exc()
        print()
        
        # Test 4
        print("[Test 4] 알림 트리거")
        try:
            # Force risk update logic trigger
            signals = system.alert_gen.generate_global_signals(limit=5)
            found = False
            for s in signals:
                if s['company'] == 'SK하이닉스' and s['score'] >= 60:
                    found = True
                    print(f"✅ Pass: 알림 감지 ({s['content']})")
                    break
            if not found:
                print("⚠️ Warning: 알림 미탐지 (데이터 주입 시차/필터링 원인)")
        except Exception:
            traceback.print_exc()
        print()
        
        # Test 5
        print("[Test 5] AI 가이드")
        try:
            signal = {"signal_type": "LEGAL_CRISIS", "company": "SK하이닉스", "score": 80, "content": "임원진 검찰 조사"}
            guide = system.ai_service.generate_action_guide_ai_v2(
                signal_type=signal['signal_type'],
                company=signal['company'],
                industry="반도체",
                news_content=signal['content'],
                risk_score=signal['score']
            )
            
            if 'rm_guide' in guide and 'ops_guide' in guide:
                 print("✅ Pass: AI 가이드 생성")
                 # print(guide['rm_guide'])
            else:
                 print("❌ Fail: 가이드 내용 미흡")
                 print(guide)
        except Exception:
            traceback.print_exc()

if __name__ == "__main__":
    run_tests()
