"""
============================================================================
기업 리스크 조기경보 시스템 v11.0 - 모니터링 화면 로그 (View Only)
============================================================================
DB에 저장된 데이터를 기반으로 실제 UI 화면처럼 콘솔에 출력
* 조회 전용 모드: 새로운 스캔을 수행하지 않습니다.
사용법: python log.py
"""

from .core import RiskWarningSystem
from datetime import datetime, timedelta
import re
import sys

# AI 서비스 로드 (실패 시 Fallback 사용)
try:
    from .ai_service import generate_action_guide_ai_v2, analyze_risk_with_ai, analyze_timeline_with_ai, predict_risk_trajectory, AI_AVAILABLE
    USE_AI = AI_AVAILABLE
except ImportError:
    USE_AI = False

# ==============================================================================
# ⚙️ 설정
# ==============================================================================

# 조회할 기업 (DB에 데이터가 있어야 함)
COMPANY = "에스케이하이닉스(주)"

# ==============================================================================
# 🎨 화면 출력 함수
# ==============================================================================

def format_relative_time(date_str: str) -> str:
    """날짜 문자열을 상대 시간(예: 30분 전)으로 변환"""
    if not date_str: return ""
    try:
        # 다양한 날짜 형식 지원
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S GMT",
            "%Y-%m-%d %H:%M:%S",
            "%Y.%m.%d",
            "%Y-%m-%d"
        ]
        
        dt = None
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                break
            except:
                continue
        
        if not dt:
            return date_str[:16]
            
        # timezone 정보 제거
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)
            
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days}일 전"
        elif diff.seconds >= 3600:
            return f"{diff.seconds // 3600}시간 전"
        elif diff.seconds >= 60:
            return f"{diff.seconds // 60}분 전"
        else:
            return "방금 전"
            
    except Exception:
        return date_str[:16]


def get_display_width(s):
    """문자열의 화면 출력 너비 계산 (한글=2, 영문/숫자=1)"""
    return sum(2 if ord(c) > 255 else 1 for c in s)

def print_header():
    print("\033[2J\033[H")  # 화면 클리어
    print("=" * 100)
    print("  \033[1;34mJB DealScanner\033[0m  │  GLOBAL STATUS: \033[1;33m● 주의 권고 1건 발생\033[0m  │  ⏱️", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 100)
    print("  \033[36mDART (공시)\033[0m  │  \033[36mKIPRIS (특허)\033[0m  │  \033[36m대법원 (법무)\033[0m  │  \033[36mNICE (신용)\033[0m  │  \033[35m잡플래닛 (평판)\033[0m  │  \033[35m뉴스/SNS\033[0m")
    print("-" * 100)


def print_global_signals(signals: list):
    """🏆 메인 대시보드: 실시간 리스크 신호 (경진대회 핵심 화면)"""
    print()
    print("┌" + "─" * 98 + "┐")
    
    # 헤더 - 빨간 점 표시
    signal_count = len(signals)
    print(f"│  \033[1;31m●\033[0m \033[1;37mREAL-TIME RISK SIGNALS\033[0m" + " " * 48 + f"최근 1시간 \033[1m{signal_count}건\033[0m 감지 │")
    print("├" + "─" * 98 + "┤")
    
    if signals:
        for signal in signals[:5]:
            # 시그널 타입별 색상 배지
            signal_type = signal.get('signal_type', 'OPERATIONAL')
            if signal_type == 'LEGAL_CRISIS':
                badge = "\033[41m\033[1;37m LEGAL CRISIS SIGNAL \033[0m"
                badge_len = 20
            elif signal_type == 'MARKET_CRISIS':
                badge = "\033[43m\033[1;30m MARKET CRISIS SIGNAL \033[0m"
                badge_len = 21
            else:
                badge = "\033[44m\033[1;37m OPERATIONAL SIGNAL \033[0m"
                badge_len = 19
            
            # 시간 포맷
            time_str = signal.get('time', '')[:16] if signal.get('time') else ''
            time_display = time_str[11:16] if len(time_str) >= 16 else 'N/A'
            
            # 긴급 표시
            urgent_marker = "[긴급] " if signal.get('is_urgent') else ""
            
            # 콘텐츠 (길이 제한)
            content = urgent_marker + signal.get('content', '')[:50]
            w_content = get_display_width(content)
            
            # 첫 번째 줄: 배지 + 시간
            print(f"│  {badge}" + " " * (70 - badge_len) + f"\033[90m{time_display}\033[0m  │")
            
            # 두 번째 줄: 콘텐츠
            print(f"│  {content}" + " " * (88 - w_content) + "│")
            
            # 세 번째 줄: 기업명 + RM 가이드 링크
            company = signal.get('company', '')[:20]
            w_company = get_display_width(company)
            print(f"│    \033[90m{company}\033[0m" + " " * (35 - w_company) + "\033[36mRM 긴급 가이드 ↗\033[0m" + " " * 40 + "│")
            print("│" + " " * 98 + "│")
    else:
        print("│  \033[32m✓ 현재 감지된 리스크 신호가 없습니다.\033[0m" + " " * 57 + "│")
    
    print("└" + "─" * 98 + "┘")


def print_project_banner(company: str, score: int, signal: str, metrics: dict, propagated: int = 0, factors: list = None):
    """상단 프로젝트 배너"""
    # 상태 색상 결정
    if score <= 30:
        status_color, status_text = "\033[42m", " PASS "
    elif score <= 60:
        status_color, status_text = "\033[43m", " WARNING "
    else:
        status_color, status_text = "\033[41m", " FAIL "
    
    # signal이 None일 경우 대비
    signal = signal or "N/A"
    
    print()
    print("┌" + "─" * 98 + "┐")
    print("│  \033[34mPROJECT IDENTIFICATION\033[0m   \033[90mIB/인수금융\033[0m" + " " * 50 + "│")
    
    width_company = get_display_width(company)
    print(f"│  \033[1;37m{company} 리스크 모니터링\033[0m" + " " * (70 - width_company) + "│")
    
    width_signal = get_display_width(signal)
    print(f"│  {signal}" + " " * (84 - width_signal) + "│")
    print("├" + "─" * 32 + "┬" + "─" * 21 + "┬" + "─" * 21 + "┬" + "─" * 21 + "┤")
    
    # 지표 행
    ltv = metrics.get('ltv', {})
    ltv_val = ltv.get('current', 'N/A')
    ltv_trend = "🔺" if ltv.get('trend') == 'up' else "🔻"
    ebitda = metrics.get('ebitda', 'N/A')
    covenant = metrics.get('covenant', 'N/A')
    
    # 길이 보정
    w_ltv = get_display_width(str(ltv_val))
    w_ebitda = get_display_width(str(ebitda))
    w_cov = get_display_width(str(covenant))
    
    # 점수 표시 (전이 리스크 포함 - 항상 상세 표시)
    direct_score = score - propagated
    score_text = f"({score}점: 직접 {direct_score}점 + 전이 {propagated}점)"

    # score_text 길이 계산 (한글 포함)
    w_score_text = get_display_width(score_text)
    
    # 레이아웃 조정 (점수 텍스트 길이에 따라 동적 공백)
    # 총 공간 32 (Status 9~10 + Score Text + Spaces)
    # Status Text Len = 6 (PASS) or 9 (WARNING) or 6 (FAIL)
    # We strip ANSI for length calc
    status_len = len(status_text)
    
    # 남은 공간 = 32 - 2(padding) - status_len - 2(gap) - w_score_text
    # But current logic fixes spaces " " * 11
    # I'll manually format it to be safe or use simple approximation if fit
    
    print(f"│  종합 리스크 등급              │ LTV (Real-time)     │ EBITDA (추정)       │ Covenant 상태       │")
    
    # 안전하게 동적 패딩
    left_side = f"  {status_color}\033[1;37m{status_text}\033[0m  \033[90m{score_text}\033[0m"
    # visible length
    vis_len = 2 + status_len + 2 + w_score_text
    padding = max(1, 32 - vis_len)
    
    print(f"│{left_side}" + " " * padding + f"│ {ltv_val} {ltv_trend}" + " " * (12 - w_ltv) + f"│ {ebitda}" + " " * (13 - w_ebitda) + f"│ {covenant}" + " " * (13 - w_cov) + "│")
    
    # 리스크 요인 (Top Factors)
    if factors:
        factor_str = ", ".join(factors[:3])
        w_fac = get_display_width(factor_str)
        print(f"│  \033[31m🔥 TOP RISKS: {factor_str}\033[0m" + " " * max(0, 83 - w_fac) + "│")
        
    print("└" + "─" * 32 + "┴" + "─" * 21 + "┴" + "─" * 21 + "┴" + "─" * 21 + "┘")


def print_entity_graph(company: str, graph):
    """🏆 [Screen 2] Entity Relationship Graph Refined"""
    
    # 관계사(Affiliates) 조회 - 법인 주주
    affiliates = graph.graph.query("""
        MATCH (c:Company {name: $name})-[:HAS_CATEGORY]->(cat:Category {type: '주주'})-[:CONTAINS]->(p:Company)
        RETURN p.name AS name, p.risk_score AS risk
        ORDER BY p.risk_score DESC LIMIT 3
    """, {"name": company})
    
    # 핵심 인물(Key Persons) - 개인 주주 및 임원
    key_persons = graph.graph.query("""
        MATCH (c:Company {name: $name})-[:HAS_CATEGORY]->(cat:Category)-[:CONTAINS]->(p:Person)
        RETURN p.name AS name, p.risk_score AS risk, labels(p) as labels
        ORDER BY p.risk_score DESC LIMIT 5
    """, {"name": company})

    # 공급망(Supply Chain) 조회 - 주요 공급사
    supply_chain = graph.graph.query("""
        MATCH (s:Company)-[:SUPPLIES_TO]->(c:Company {name: $name})
        RETURN s.name AS name, s.risk_score AS risk
        ORDER BY s.risk_score DESC LIMIT 3
    """, {"name": company})

    # 그래프 통계 조회 (Interactive 느낌 강화)
    try:
        stats = graph.graph.query("""
            MATCH (c:Company {name: $name})-[r*1..2]-(m)
            RETURN count(DISTINCT m) AS nodes, count(DISTINCT r) AS edges
        """, {"name": company})
        node_cnt = stats[0]['nodes'] if stats else 0
        edge_cnt = stats[0]['edges'] if stats else 0
    except:
        node_cnt, edge_cnt = 0, 0

    print()
    print("┌" + "─" * 98 + "┐")
    print(f"│  \033[34m▌\033[0m [1] ENTITY RELATIONSHIP GRAPH (인터랙티브 관계도 Refined)" + " " * 18 + f"\033[32m● LIVE: {node_cnt} Nodes / {edge_cnt} Edges\033[0m │")
    print("├" + "─" * 98 + "┤")
    print("│                                                                                                  │")
    
    # 중앙에 회사
    display_name = company[:15]
    pad_left = 40
    pad_right = 98 - 2 - pad_left - 2 - get_display_width(display_name)
    
    print(f"│" + " " * pad_left + f"\033[1;36m🏢\033[0m {display_name}" + " " * pad_right + "│")
    print("│                                      │                                                           │")
    
    # 관계사 (Affiliates)
    if affiliates:
        print("│  \033[33m[관계사/투자자]\033[0m" + " " * 84 + "│")
        for aff in affiliates:
            name = aff['name'][:15]
            risk = aff.get('risk') or 0
            risk_color = "\033[31m" if risk > 50 else "\033[32m"
            w_name = get_display_width(name)
            print(f"│    🏢 \033[1m{name}\033[0m " + " " * (20 - w_name) + f"{risk_color}● 리스크 {risk}점\033[0m" + " " * 52 + "│")
            print("│      │                                                                                           │")

    # 공급망 (Supply Chain)
    print("│  \033[36m[주요 공급망 (Supply Chain)]\033[0m" + " " * 71 + "│")
    if supply_chain:
        for sup in supply_chain:
            name = sup['name'][:15]
            risk = sup.get('risk') or 0
            risk_color = "\033[31m" if risk > 50 else "\033[32m"
            w_name = get_display_width(name)
            print(f"│    🏭 \033[1m{name}\033[0m " + " " * (20 - w_name) + f"{risk_color}● 리스크 {risk}점\033[0m" + " " * 52 + "│")
            print("│      │                                                                                           │")
    else:
        print("│    \033[90m연결된 공급망 데이터가 없습니다.\033[0m" + " " * 65 + "│")
        print("│      │                                                                                           │")
    
    # 핵심 인물 (Key Persons)
    if key_persons:
        print("│  \033[35m[핵심 인물]\033[0m" + " " * 88 + "│")
        for p in key_persons:
            name = p['name'][:10]
            risk = p.get('risk') or 0
            risk_color = "\033[31m" if risk > 30 else "\033[32m"
            role = "주주" if "주주" in str(p.get('labels')) else "임원"
            w_name = get_display_width(name)
            
            print(f"│    👤 {name}" + " " * (15 - w_name) + f"({role}) {risk_color}● {risk}점\033[0m" + " " * 57 + "│")

    print("│                                                                                                  │")
    print("└" + "─" * 98 + "┘")


def print_timeline(timeline: list):
    """🏆 [2] Risk Timeline - 3단계 선행 감지 로직 (경진대회 핵심 화면)"""
    from datetime import datetime
    
    print()
    print("┌" + "─" * 98 + "┐")
    
    # 마지막 업데이트 시간
    now = datetime.now().strftime("%H:%M")
    print(f"│  \033[34m▌\033[0m [2] RISK TIMELINE (3단계 선행 감지 로직)" + " " * 30 + f"최근 업데이트: \033[36m{now}\033[0m (Real-time) │")
    print("├" + "─" * 98 + "┤")
    
    if timeline:
        # 3단계별 이벤트 분류
        stage1_events = [e for e in timeline if e.get('stage') == 1]
        stage2_events = [e for e in timeline if e.get('stage') == 2]
        stage3_events = [e for e in timeline if e.get('stage') == 3]
        
        # 타임라인 헤더 (가로 흐름)
        print("│" + " " * 98 + "│")
        
        # 시간대 표시
        times = []
        for e in timeline[:3]:
            date_str = e.get('date', '')
            if date_str and len(date_str) >= 16:
                times.append(date_str[11:16])  # HH:MM
            elif date_str and len(date_str) >= 10:
                times.append(date_str[5:10])   # MM-DD
            else:
                times.append('--:--')
        
        while len(times) < 3:
            times.append('--:--')
        
        print(f"│         {times[0]}" + " " * 23 + f"{times[1]}" + " " * 23 + f"{times[2]}" + " " * 25 + "│")
        
        # 타임라인 진행 막대
        s1_icon = "\033[34m●\033[0m" if stage1_events else "\033[90m○\033[0m"
        s2_icon = "\033[33m●\033[0m" if stage2_events else "\033[90m○\033[0m"
        s3_icon = "\033[31m●\033[0m" if stage3_events else "\033[90m○\033[0m"
        
        print(f"│          {s1_icon}───────────────────────────{s2_icon}───────────────────────────{s3_icon}" + " " * 24 + "│")
        
        # 단계명 표시
        print(f"│         \033[34m📰 뉴스 보도\033[0m" + " " * 15 + "\033[33m📋 금융위 통지\033[0m" + " " * 15 + "\033[31m🏦 대주단 확인\033[0m" + " " * 17 + "│")
        
        # 각 단계별 대표 이벤트 설명
        s1_desc = stage1_events[0].get('description', '선행 감지')[:20] if stage1_events else "감지 대기"
        s2_desc = stage2_events[0].get('description', '규제 개입')[:20] if stage2_events else "발생 전"
        s3_desc = stage3_events[0].get('description', '조치 필요')[:20] if stage3_events else "발생 전"
        
        print(f"│         \033[90m\"{s1_desc}\"\033[0m" + " " * (26 - get_display_width(s1_desc)) + f"\033[90m\"{s2_desc}\"\033[0m" + " " * (26 - get_display_width(s2_desc)) + f"\033[90m\"{s3_desc}\"\033[0m" + " " * (26 - get_display_width(s3_desc)) + "│")
        
        print("│" + " " * 98 + "│")
        
        # 상세 이벤트 목록 (최대 3건)
        print("├" + "─" * 98 + "┤")
        for event in timeline[:3]:
            stage = event.get('stage', 1)
            icon = event.get('icon', '🔵')
            stage_label = event.get('stage_label', '뉴스 보도')
            label = event.get('label', '')[:45]
            date = event.get('date', '')[:10] if event.get('date') else 'N/A'
            
            # 단계별 색상
            if stage == 3:
                color = "\033[31m"
            elif stage == 2:
                color = "\033[33m"
            else:
                color = "\033[34m"
            
            w_label = get_display_width(label)
            print(f"│  {icon} {color}[{stage_label}]\033[0m  {label}" + " " * max(0, 60 - w_label) + f"\033[90m{date}\033[0m │")
    else:
        print("│  \033[90m타임라인 이벤트가 없습니다. 먼저 run.py를 실행하여 데이터를 생성해주세요.\033[0m" + " " * 24 + "│")
    
    print("└" + "─" * 98 + "┘")


def print_alerts(alerts: list):
    """알림 섹션"""
    print()
    print("┌" + "─" * 98 + "┐")
    print(f"│  \033[34m▌\033[0m [3] ACTIVE ALERTS (실시간 알림)" + " " * 52 + f"총 {len(alerts)}건 │")
    print("├" + "─" * 98 + "┤")
    
    if alerts:
        for alert in alerts[:5]:
            sev = alert.get('severity', 'low')
            if sev == 'high':
                color, badge = "\033[41m", " HIGH "
            elif sev == 'medium':
                color, badge = "\033[43m", " MED  "
            else:
                color, badge = "\033[100m", " LOW  "
            
            content = alert.get('content', '')[:60]
            
            # 상대 시간 포맷팅 적용
            raw_time = alert.get('time', '')
            time_str = format_relative_time(raw_time) if raw_time else ''
            
            w_content = get_display_width(content)
            w_badge = 8  # " HIGH " length
            
            print(f"│  {color}{badge}\033[0m {content}" + " " * max(0, 68 - w_content) + f"\033[90m{time_str}\033[0m" + " " * max(1, 15 - get_display_width(time_str)) + "│")
    else:
        print("│  \033[32m✓ 현재 활성 알림이 없습니다.\033[0m" + " " * 64 + "│")
    
    print("└" + "─" * 98 + "┘")


def print_risk_breakdown(breakdown: dict, weights: dict):
    """14-카테고리 점수 분석 (v13.0)"""
    print()
    print("┌" + "─" * 98 + "┐")
    print("│  \033[34m▌\033[0m [4] RISK BREAKDOWN (14-카테고리 분석)" + " " * 47 + "│")
    print("├" + "─" * 98 + "┤")
    
    # v13.0: 14개 카테고리 (기존 8개 + 신규 6개)
    categories = [
        "공시", "뉴스", "주주", "임원", "특허", "채용리뷰", "소송", "신용등급",
        "금감원", "ESG", "SNS", "부동산", "상표", "경쟁사"
    ]
    icons = {
        "공시": "📄", "뉴스": "📰", "주주": "📊", "임원": "👔", 
        "특허": "📜", "채용리뷰": "👥", "소송": "⚖️", "신용등급": "📉",
        "금감원": "🏛️", "ESG": "🌿", "SNS": "💬", 
        "부동산": "🏢", "상표": "🏷️", "경쟁사": "🏭"
    }
    
    for cat in categories:
        score = breakdown.get(cat, 0)
        weight = weights.get(cat, 0)
        weighted = round(score * weight)
        
        # 진행바
        bar_len = 20  # Shortened to fit 14 categories
        filled = min(bar_len, int(bar_len * min(score, 100) / 100))
        color = "\033[31m" if score > 60 else "\033[33m" if score > 30 else "\033[32m"
        
        width_cat = get_display_width(cat)
        padding = max(0, 8-width_cat)
        
        print(f"│  {icons.get(cat, '📌')} {cat}" + " " * padding + f" [{color}{'█' * filled}\033[0m{'░' * (bar_len - filled)}] {score:3.0f}점 × {int(weight*100):2d}% = {weighted:3d}점 │")
    
    print("└" + "─" * 98 + "┘")


def generate_ai_action_guide(signal_type: str, company: str, news_content: str = "", risk_score: int = 0) -> dict:
    """🏆 AI 대응 가이드 생성"""
    if USE_AI and 'generate_action_guide_ai_v2' in globals():
        try:
            return generate_action_guide_ai_v2(signal_type=signal_type, company=company, news_content=news_content, risk_score=risk_score)
        except Exception as e:
            print(f"⚠️ AI 호출 실패, Fallback 사용: {e}")
    
    GUIDES = {
        'LEGAL_CRISIS': {
            'rm_title': '💡 RM 영업 가이드',
            'rm_guide': '"스폰서 부도 리스크 심화, 신규 대출 중단 및 기존 자금 점검 필요."',
            'rm_todos': ['스폰서 자금 관리인 면담', '공동 투자자 리스크 분담 타진', 'White Knight 탐색'],
            'ops_title': '🛡️ OPS 방어 가이드',
            'ops_guide': '"금융약정 위반 EOD 통지서 작성, 계좌 모니터링 및 자금 이탈 차단."',
            'ops_todos': ['☑ EOD 통지서 발송 준비', '자산 현황 재점검', '법무법인 선임']
        },
        'MARKET_CRISIS': {
            'rm_title': '💡 RM 영업 가이드',
            'rm_guide': f'"{company} 시장 위기 감지. 헤지 포지션 및 유동성 확보 검토."',
            'rm_todos': ['시장 동향 모니터링 강화', '유동성 확보 방안 검토', '파트너사 커뮤니케이션'],
            'ops_title': '🛡️ OPS 방어 가이드',
            'ops_guide': '"LTV 한도 재검토 및 추가 담보 요청. 시장 변동성 대응 시나리오."',
            'ops_todos': ['담보 가치 재평가', 'Covenant 위반 점검', '비상 유동성 확보']
        },
        'OPERATIONAL': {
            'rm_title': '💡 RM 영업 가이드',
            'rm_guide': f'"{company} 운영 리스크 주의. 정기 모니터링 및 경영진 면담 권장."',
            'rm_todos': ['정기 경영 보고서 검토', '현장 실사 일정 조율', '경영진 면담 요청'],
            'ops_title': '🛡️ OPS 방어 가이드',
            'ops_guide': '"내부 통제 점검 및 운영 효율성 분석. 이상 징후 시 즉시 보고."',
            'ops_todos': ['내부 감사 결과 확인', '운영 효율성 분석', 'IT 보안 점검']
        }
    }
    return GUIDES.get(signal_type, GUIDES['OPERATIONAL'])


def print_action_board(signal_type: str, company: str, risk_score: int = 0):
    """🏆 [3] RM/OPS Action Board - 좌우 분할 레이아웃 (경진대회 핵심 화면)"""
    guide = generate_ai_action_guide(signal_type, company, risk_score=risk_score)
    
    print()
    # 좌측 헤더 (RM)
    industry = guide.get('industry', 'General')
    rm_header = f"│  \033[33m🏈\033[0m RM ACTION BOARD ({industry})"
    ops_header = f"\033[36m●\033[0m OPS ACTION BOARD (DEFENSE)"
    print("┌" + "─" * 48 + "┬" + "─" * 49 + "┐")
    print(f"{rm_header}" + " " * 8 + f"│  {ops_header}" + " " * 12 + "│")
    print("├" + "─" * 48 + "┼" + "─" * 49 + "┤")
    
    # AI 가이드 타이틀
    rm_title = guide['rm_title']
    ops_title = guide['ops_title']
    print(f"│  {rm_title}" + " " * (40 - get_display_width(rm_title)) + f"│  {ops_title}" + " " * (41 - get_display_width(ops_title)) + "│")
    
    # AI 가이드 내용 (줄바꿈 처리)
    rm_guide = guide['rm_guide'][:45]
    ops_guide = guide['ops_guide'][:45]
    print(f"│  \033[90m{rm_guide}\033[0m" + " " * max(0, 38 - get_display_width(rm_guide)) + f"│  \033[90m{ops_guide}\033[0m" + " " * max(0, 39 - get_display_width(ops_guide)) + "│")
    
    print("│" + " " * 48 + "│" + " " * 49 + "│")
    
    # To-Do 아이템
    rm_todos = guide['rm_todos']
    ops_todos = guide['ops_todos']
    max_todos = max(len(rm_todos), len(ops_todos))
    
    for i in range(max_todos):
        rm_item = rm_todos[i] if i < len(rm_todos) else ""
        ops_item = ops_todos[i] if i < len(ops_todos) else ""
        
        # 체크박스 스타일
        if rm_item.startswith('☑'):
            rm_checkbox = "\033[32m☑\033[0m"
            rm_item = rm_item[2:]
        else:
            rm_checkbox = "☐"
        
        if ops_item.startswith('☑'):
            ops_checkbox = "\033[32m☑\033[0m"
            ops_item = ops_item[2:]
        else:
            ops_checkbox = "☐"
        
        rm_display = rm_item[:35]
        ops_display = ops_item[:35]
        
        print(f"│  {rm_checkbox} {rm_display}" + " " * max(0, 40 - get_display_width(rm_display)) + f"│  {ops_checkbox} {ops_display}" + " " * max(0, 41 - get_display_width(ops_display)) + "│")
    
    # 산업 인사이트 (AI V2)
    insight = guide.get('industry_insight', '')
    if insight:
        w_ins = get_display_width(insight)
        print("├" + "─" * 98 + "┤")
        print(f"│  \033[35m🤖 AI Insight ({industry}):\033[0m {insight}" + " " * max(0, 75 - w_ins) + "│")

    print("└" + "─" * 48 + "┴" + "─" * 49 + "┘")


def print_prediction(prediction: dict):
    """🔮 [Screen 3.5] AI Future Risk Forecast"""
    if not prediction: return

    scenarios = prediction.get('scenarios', {})
    trend = prediction.get('trend', '변동성 확대')
    
    print()
    print("┌" + "─" * 98 + "┐")
    print(f"│  \033[35m🔮\033[0m \033[1;37mAI PREDICTIVE FORECAST\033[0m (향후 1개월)" + " " * 44 + f"추세: \033[1m{trend}\033[0m" + " " * (13 - get_display_width(trend)) + "│")
    print("├" + "─" * 32 + "┬" + "─" * 32 + "┬" + "─" * 32 + "┤")
    
    # 헤더
    print(f"│  \033[32m📈 BEST CASE ({scenarios.get('best', {}).get('prob', 'N/A')})\033[0m" + " " * 14 + f"│  \033[33m📉 BASE CASE ({scenarios.get('base', {}).get('prob', 'N/A')})\033[0m" + " " * 14 + f"│  \033[31m💣 WORST CASE ({scenarios.get('worst', {}).get('prob', 'N/A')})\033[0m" + " " * 13 + "│")
    
    # 내용
    best = scenarios.get('best', {}).get('event', '')[:18]
    base = scenarios.get('base', {}).get('event', '')[:18]
    worst = scenarios.get('worst', {}).get('event', '')[:18]
    
    w_best = get_display_width(best)
    w_base = get_display_width(base)
    w_worst = get_display_width(worst)
    
    print(f"│  {best}" + " " * (30 - w_best) + f"│  {base}" + " " * (30 - w_base) + f"│  {worst}" + " " * (30 - w_worst) + "│")
    
    # 점수
    s_best = scenarios.get('best', {}).get('score', 0)
    s_base = scenarios.get('base', {}).get('score', 0)
    s_worst = scenarios.get('worst', {}).get('score', 0)
    
    print(f"│  예상 리스크: {s_best}점" + " " * 13 + f"│  예상 리스크: {s_base}점" + " " * 13 + f"│  예상 리스크: {s_worst}점" + " " * 13 + "│")
    
    print("└" + "─" * 32 + "┴" + "─" * 32 + "┴" + "─" * 32 + "┘")


def print_evidence(company: str, graph=None):
    """🏆 [4] Evidence Data - 교차 검증 섹션 (실제 DB 데이터 기반)"""
    print()
    print("┌" + "─" * 98 + "┐")
    print("│  \033[34m▌\033[0m [4] EVIDENCE DATA (교차 검증 근거)" + " " * 58 + "│")
    print("├" + "─" * 98 + "┤")
    
    evidence_data = []
    
    # Neo4j에서 실제 뉴스 데이터 조회
    if graph:
        try:
            news_query = """
            MATCH (c:Company {name: $company})<-[:ABOUT]-(n:NewsArticle)
            WHERE n.is_risk = true
            RETURN n.title AS title, n.date AS date, n.source_type AS source, n.risk_score AS score
            ORDER BY n.risk_score DESC
            LIMIT 2
            """
            results = graph.graph.query(news_query, {"company": company})
            
            for item in results:
                evidence_data.append({
                    'ext_type': 'EXT NEWS',
                    'ext_title': item.get('title', '')[:60],
                    'ext_source': item.get('source', '뉴스')[:15],
                    'ext_date': item.get('date', '')[:10] if item.get('date') else 'N/A',
                    'int_type': 'INT ANALYSIS',
                    'int_title': f"리스크 점수 {item.get('score', 0)}점 - 내부 규정 검토 대상",
                    'int_source': '리스크관리팀',
                    'int_date': datetime.now().strftime('%Y.%m.%d')
                })
        except Exception as e:
            pass
    
    if evidence_data:
        for ev in evidence_data:
            # 외부 뉴스
            ext_badge = "\033[41m\033[1;37m EXT NEWS \033[0m"
            ext_title = ev['ext_title'][:55]
            w_ext = get_display_width(ext_title)
            print(f"│  {ext_badge}  {ext_title}" + " " * max(0, 76 - w_ext) + "│")
            print(f"│    \033[90m{ev['ext_source']}\033[0m  │  \033[33m{ev['ext_date']}\033[0m" + " " * 70 + "│")
            print("│" + " " * 98 + "│")
            
            # 내부 문서 (매핑)
            int_badge = "\033[44m\033[1;37m INT ANALYSIS \033[0m"
            int_title = ev['int_title'][:55]
            w_int = get_display_width(int_title)
            print(f"│  {int_badge}  {int_title}" + " " * max(0, 72 - w_int) + "│")
            print(f"│    \033[90m{ev['int_source']}\033[0m  │  {ev['int_date']}" + " " * 68 + "│")
            print("│" + " " * 98 + "│")
    else:
        print("│  \033[90m교차 검증 대상 데이터가 없습니다.\033[0m" + " " * 62 + "│")
    
    print("└" + "─" * 98 + "┘")


def print_footer():
    print()
    print("=" * 100)
    print(f"  \033[90m© 2026 JB DealScanner v10.0 | 마지막 분석: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\033[0m")
    print("=" * 100)


# ==============================================================================
# 📊 Data Snapshot Adapter (for Web UI)
# ==============================================================================

def export_dashboard_snapshot(company: str, system: object) -> dict:
    import traceback
    try:
        """
        UI(React)에서 사용할 수 있는 완벽한 형태의 JSON 스냅샷 생성
        """
        raw_data = system.get_dashboard_data(company)
        if not raw_data:
            return {
                "schemaVersion": "monitoring.v1",
                "generatedAt": datetime.now().isoformat(),
                "data": {},
                "_meta": {"error": f"No data found for {company}"}
            }
        analyze_result = raw_data.get('_analyze_result', {})
        if analyze_result is None:
            analyze_result = {}
        score = analyze_result.get('score') or 0
        sys.stderr.write(f"DEBUG: score={score} ({type(score)})\\n")
        propagated = analyze_result.get('propagated') or 0
        coverage = analyze_result.get('coverage') or 0
        
        # 1. Status Derivation
        try:
            if score <= 30: status = "PASS"
            elif score <= 60: status = "WARNING"
            else: status = "FAIL"
        except:
            status = "UNKNOWN"
        
        # 2. Tranche Calculation (요약 문구)
        try:
            breakdown = analyze_result.get('breakdown', {}) or {}
            valid_items = [(k, v) for k, v in breakdown.items() if (v is not None and isinstance(v, (int, float)))]
            top_factors = sorted(valid_items, key=lambda x: x[1], reverse=True)
            top_factor_name = top_factors[0][0] if top_factors else "기타"
            tranche = f"{top_factor_name} 리스크 심화 ({score}점) - 주의 필요"
        except:
            tranche = f"리스크 분석 중 ({score}점)"
        
        # 3. AI Guides (Fallback)
        rm_actions = {
            "guide": "주요 리스크 요인에 대한 선제적 방어 논리 수립 필요",
            "todos": [
                {"id": "rm1", "text": "스폰서 긴급 미팅 소집", "completed": False},
                {"id": "rm2", "text": "LTV 준수 여부 법률 검토", "completed": False},
                {"id": "rm3", "text": "대주단 대응 논리 수립", "completed": False}
            ]
        }
        ops_actions = {
            "guide": "EOD 트리거 가능성 점검 및 자산 동결 대비",
            "todos": [
                {"id": "ops1", "text": "담보 평가 보고서 최신화", "completed": False},
                {"id": "ops2", "text": "현장 실사 일정 확정", "completed": False},
                {"id": "ops3", "text": "자금 집행 정지 여부 통보", "completed": False}
            ]
        }
        
        # 4. Timeline Adapter
        # 4. Timeline Adapter (Updated v14.2: Direct Pass-through)
        # core.py에서 이미 완벽한 5-Stage 포맷으로 생성하므로 그대로 전달
        timeline_adapter = raw_data.get('timeline', []) or []

        # 5. Evidence Adapter
        evidence_adapter = []
        try:
            news_query = """
                MATCH (c:Company {name: $company})<-[:ABOUT]-(n:NewsArticle)
                WHERE n.is_risk = true
                RETURN n.title AS title, n.source AS source, n.date AS date, n.sentiment AS sentiment
                ORDER BY n.risk_score DESC LIMIT 5
            """
            if system.graph and system.graph.graph:
                ev_res = system.graph.graph.query(news_query, {"company": company})
                if ev_res:
                    for i, e in enumerate(ev_res):
                        evidence_adapter.append({
                            "id": f"e{i}",
                            "title": e['title'],
                            "source": e.get('source', '뉴스'),
                            "date": e.get('date', '')[:10] if e.get('date') else 'N/A',
                            "sentiment": e.get('sentiment', '중립')
                        })
        except:
            pass

        import json
        return {
            "schemaVersion": "monitoring.v1",
            "generatedAt": datetime.now().isoformat(),
            "data": {
                "dealName": company,
                "tranche": tranche,
                "status": status,
                "metrics": {
                    "ltv": raw_data.get('metrics', {}).get('ltv', {
                        "current": "N/A",
                        "prev": "0.0%",
                        "trend": "up"
                    }),
                    "ebitda": raw_data.get('metrics', {}).get('ebitda', "N/A"),
                    "covenant": raw_data.get('metrics', {}).get('covenant', "정상")
                },
                "timeline": timeline_adapter,
                "graph": raw_data.get('graph', {"nodes": [], "edges": []}),
                "rmActions": rm_actions, 
                "opsActions": ops_actions,
                "evidence": evidence_adapter
            },
            "_meta": {
                "score": score,
                "propagated": analyze_result.get('propagated', 0),
                "coverage": analyze_result.get('coverage', 0),
                "signal": analyze_result.get('signal', 'UNKNOWN'),
                "source": "neo4j-risk-engine"
            }
        }
    except Exception as e:
        sys.stderr.write(traceback.format_exc())
        return {"error": str(e)}


# ==============================================================================
# 🚀 메인 실행
# ==============================================================================

if __name__ == "__main__":
    import argparse
    import json
    import sys
    
    parser = argparse.ArgumentParser(description="JB DealScanner Dashboard & Snapshot Agent")
    parser.add_argument("--company", type=str, default="SK하이닉스", help="Target Company Name")
    parser.add_argument("--json", action="store_true", help="Output JSON snapshot to stdout")
    parser.add_argument("--export", type=str, help="Export JSON snapshot to file path")
    args = parser.parse_args()
    
    # 시스템 초기화 (reset_data=False로 기존 데이터 유지 중요!)
    system = RiskWarningSystem(reset_data=False)
    COMPANY = args.company  # Compatibility alias
    
    # 1. JSON Export Mode
    if args.json or args.export:
        snapshot = export_dashboard_snapshot(COMPANY, system)
        
        if args.export:
            with open(args.export, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            if not args.json:
                print(f"✅ Snapshot exported to {args.export}")
        
        if args.json:
            print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 2. Legacy Terminal Dashboard Mode
    print_header()
    
    # 🏆 [Screen 1] 메인 대시보드: 전체 포트폴리오 리스크 신호
    global_signals = system.alert_gen.generate_global_signals(limit=5)
    print_global_signals(global_signals)
    
    # 🔍 [Screen 2] 개별 딜 상세: DB 조회 (스캔 없이)
    result = system.get_dashboard_data(COMPANY)
    
    if result:
        analyze_result = result.get('_analyze_result', {})
        
        print_project_banner(
            company=result.get('dealName', COMPANY),
            score=analyze_result.get('score', 0),
            signal=analyze_result.get('signal', ''),
            metrics=result.get('metrics', {}),
            propagated=analyze_result.get('propagated', 0),
            factors=analyze_result.get('factors', [])
        )
        
        print_entity_graph(result.get('dealName', COMPANY), system.graph)
        
        print_timeline(result.get('timeline', []))
        
        # 🏆 [Screen 3] Action Board + Evidence (경진대회 핵심!)
        # 시그널 타입 결정 (가장 최근 글로벌 시그널 기준)
        signal_type = global_signals[0].get('signal_type', 'OPERATIONAL') if global_signals else 'OPERATIONAL'
        print_action_board(signal_type, result.get('dealName', COMPANY), risk_score=analyze_result.get('score', 0))
        
        # 🔮 AI 예측 섹션 추가
        if 'predict_risk_trajectory' in globals():
            # 뉴스 요약 생성을 위한 간단한 로직
            start_news = result.get('start_urls', []) or []
            news_summary = ", ".join([u.get('title', '') for u in start_news[:3]])
            prediction = predict_risk_trajectory(result.get('dealName', COMPANY), analyze_result.get('score', 0), news_summary)
            print_prediction(prediction)
        
        print_evidence(result.get('dealName', COMPANY), system.graph)
        
        print_alerts(result.get('alerts', []))
        
        print_risk_breakdown(
            analyze_result.get('breakdown', {}),
            analyze_result.get('adjusted_weights', {})
        )
        
        print_footer()
    else:
        print(f"\n❌ '{COMPANY}'에 대한 데이터 조회 실패")
        print("   먼저 run.py를 실행하여 데이터를 생성해주세요.")
