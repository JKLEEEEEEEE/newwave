"""
🏆 Text2Cypher CLI - 자연어로 그래프 데이터베이스 질의
사용법: python query.py "질문"
"""

import sys
from ai_service import text2cypher, ask_graph, AI_AVAILABLE

def print_result(result: dict):
    """결과 출력"""
    print("\n" + "="*60)
    print(f"📝 질문: {result['question']}")
    print("="*60)
    
    if result['success']:
        print(f"\n🔍 생성된 Cypher:")
        print(f"   {result['cypher']}")
        print(f"\n💬 답변:")
        print(f"   {result['answer']}")
        
        if result['results']:
            print(f"\n📊 원시 결과 ({len(result['results'])}건):")
            for i, r in enumerate(result['results'][:5], 1):
                print(f"   {i}. {r}")
            if len(result['results']) > 5:
                print(f"   ... 외 {len(result['results']) - 5}건")
    else:
        print(f"\n❌ 오류: {result['answer']}")
    
    print("="*60 + "\n")


def run_tests():
    """테스트 케이스 실행"""
    print("\n🧪 Text2Cypher 테스트 시작...\n")
    
    test_cases = [
        # 기본 조회
        "분석된 기업 목록을 보여줘",
        "SK하이닉스 리스크 점수는?",
        "리스크 점수가 가장 높은 기업 TOP 5",
        
        # 리스크 레벨 관련
        "위험 등급 기업 목록",
        "정상 상태인 기업은?",
        
        # 뉴스 관련
        "최근 뉴스 5개 보여줘",
        "부정적인 뉴스 목록",
        
        # 공시 관련
        "공시 건수가 많은 카테고리",
        
        # 관계 조회
        "SK하이닉스의 임원 목록",
        "주주 관련 정보",
    ]
    
    passed = 0
    failed = 0
    
    for question in test_cases:
        print(f"🔹 테스트: {question}")
        result = text2cypher(question)
        
        if result['success']:
            print(f"   ✅ 성공 - Cypher: {result['cypher'][:50]}...")
            passed += 1
        else:
            print(f"   ❌ 실패 - {result['answer']}")
            failed += 1
        print()
    
    print(f"\n📊 테스트 결과: {passed}/{len(test_cases)} 성공 ({failed} 실패)")
    return passed, failed


def interactive_mode():
    """대화형 모드"""
    print("\n🏆 Text2Cypher 대화형 모드")
    print("종료: 'exit' 또는 'quit' 입력\n")
    
    while True:
        try:
            question = input("📝 질문: ").strip()
            if question.lower() in ['exit', 'quit', '종료']:
                print("👋 종료합니다.")
                break
            if not question:
                continue
            
            result = text2cypher(question)
            print_result(result)
            
        except KeyboardInterrupt:
            print("\n👋 종료합니다.")
            break


if __name__ == "__main__":
    if not AI_AVAILABLE:
        print("⚠️ AI 서비스를 사용할 수 없습니다.")
        sys.exit(1)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            run_tests()
        elif sys.argv[1] == "--interactive" or sys.argv[1] == "-i":
            interactive_mode()
        else:
            # 단일 질문 처리
            question = " ".join(sys.argv[1:])
            result = text2cypher(question)
            print_result(result)
    else:
        # 인자 없으면 대화형 모드
        interactive_mode()
