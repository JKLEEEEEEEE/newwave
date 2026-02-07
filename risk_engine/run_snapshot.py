
import sys
import os
import argparse
import json
from datetime import datetime

# 패키지 경로 추가 (현재 디렉토리)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from risk_engine.core import RiskWarningSystem
from risk_engine.dashboard_adapter import export_dashboard_snapshot

def main():
    parser = argparse.ArgumentParser(description="JB DealScanner Snapshot Generator (Wrapper)")
    parser.add_argument("--company", type=str, default="SK하이닉스", help="Target Company Name")
    parser.add_argument("--export", type=str, help="Export Path (JSON)")
    args = parser.parse_args()

    print(f"🚀 [Wrapper] Starting Risk Analysis for {args.company}...")
    
    # 1. 시스템 초기화
    system = RiskWarningSystem(reset_data=False)
    
    # 2. 스냅샷 데이터 생성
    snapshot = export_dashboard_snapshot(args.company, system)
    
    # 3. 결과 출력/저장
    if args.export:
        with open(args.export, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        print(f"✅ Snapshot exported to {args.export}")
    else:
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
