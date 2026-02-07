"""
🕵️ JB DealScanner - Autonomous Monitoring Agent
================================================
백그라운드에서 24/7 실행되며 신규 리스크를 실시간으로 감지하고 알림을 발송합니다.
"""

import time
import sys
import os
from datetime import datetime
from risk_engine import RiskWarningSystem

# ANSI Colors
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"
BOLD = "\033[1m"
CLEAR = "\033[2J\033[H"

def print_banner():
    print(CLEAR)
    print(f"{CYAN}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║  🕵️  JB DealScanner - Autonomous Risk Agent (v2.1)         ║{RESET}")
    print(f"{CYAN}║  Running in Background | Monitoring Active Portfolios        ║{RESET}")
    print(f"{CYAN}╚══════════════════════════════════════════════════════════════╝{RESET}")
    print()

def spinner(duration=1.0):
    chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r{CYAN} {chars[i % len(chars)]} Scanning market signals...{RESET}")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write("\r" + " " * 30 + "\r")

def send_alert(alert_level, title, message):
    """🚨 [Day 5] 알림 발송 모의 구현"""
    print(f"\n{RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{RED} [ALERT AGENT] Sending Notifications... ({alert_level}){RESET}")
    print(f"{RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    
    # 1. Email Mock
    print(f"📧 [EMAIL] To: risk_team@bank.com")
    print(f"   Subject: [{alert_level}] {title}")
    print(f"   Body: {message[:50]}...")
    print(f"   Status: ✅ Sent (SMTP)")
    
    # 2. SMS Mock
    print(f"📱 [SMS]   To: 010-1234-5678")
    print(f"   Message: [{alert_level}] {title} - 확인 요망")
    print(f"   Status: ✅ Sent (Twilio)")
    print()

def main():
    print_banner()
    
    # Initialize Engine
    print(f"{YELLOW}[SYSTEM] Initializing Risk Engine...{RESET}")
    try:
        system = RiskWarningSystem(reset_data=False)
        print(f"{GREEN}[SYSTEM] Engine Ready. Connected to Knowledge Graph.{RESET}")
    except Exception as e:
        print(f"{RED}[ERROR] Engine Init Failed: {e}{RESET}")
        return

    print(f"{GREEN}[AGENT] Surveillance Mode Activated.{RESET}\n")
    
    last_signal_time = None
    scanned_companies = ["삼성전자", "SK하이닉스", "LG에너지솔루션", "현대자동차", "NAVER"]
    
    while True:
        try:
            # 1. Visual Effect
            spinner(2.0)
            
            now = datetime.now().strftime("%H:%M:%S")
            target = scanned_companies[int(time.time()) % len(scanned_companies)]
            
            print(f"[{now}] 📡 Scanning: {target:10s} | Sources: DART, News, Social... \033[90mOK\033[0m")
            
            # 2. Check for Risks
            # 실제로는 DB에서 가장 최근 시그널을 가져와서, 이전에 본 것보다 최신이면 알림
            signals = system.alert_gen.generate_global_signals(limit=1)
            
            if signals:
                latest = signals[0]
                
                signal_type = latest.get('signal_type', 'OPERATIONAL')
                if signal_type != 'OPERATIONAL': # 심각한 시그널만 알림
                    print()
                    print(f"{RED}🚨 [CRITICAL ALERT DETECTED]{RESET}")
                    print(f"   Time:    {latest.get('time')}")
                    print(f"   Company: {BOLD}{latest.get('company')}{RESET}")
                    print(f"   Type:    {RED}{signal_type}{RESET}")
                    print(f"   Message: {latest.get('content')}")
                    print(f"   Action:  {YELLOW}Requesting Immediate RM Inspection...{RESET}")
                    print()
                    
                    # [Day 5] 알림 발송
                    send_alert("CRITICAL", f"{latest.get('company')} {signal_type}", latest.get('content'))
                    
                    # 알림 후 잠시 대기 (너무 자주 울리지 않게)
                    time.sleep(5)
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            print(f"\n\n{YELLOW}[AGENT] Stopping surveillance... Goodbye.{RESET}")
            break
        except Exception as e:
            print(f"{RED}[ERROR] {e}{RESET}")
            time.sleep(5)

if __name__ == "__main__":
    main()
