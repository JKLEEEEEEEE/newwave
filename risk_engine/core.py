"""
============================================================================
기업 리스크 조기경보 시스템 v10.0
============================================================================
통합 라이브러리 모듈 (BusiSearch.py + busi_enhanced.py)
"""

import os, json, re, requests, zipfile, time, math, uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from collections import Counter
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph
from bs4 import BeautifulSoup

# .env.local 파일 로드 (현재 디렉토리 및 상위 디렉토리에서 검색)
import pathlib
env_path = pathlib.Path(__file__).parent.parent / ".env.local"  # Root directory
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # 기본 .env 파일 시도

# ==============================================================================
# 상수 및 유틸리티
# ==============================================================================

DECAY_HALF_LIFE = 30
PROPAGATION_DECAY = 0.3
TOP_N_FACTORS = 5

def calc_decay(days_old, half_life=DECAY_HALF_LIFE):
    return math.exp(-days_old / half_life)

def parse_date(date_str):
    if not date_str: return datetime.now()
    try: return parsedate_to_datetime(date_str).replace(tzinfo=None)
    except: pass
    try: return datetime.strptime(date_str, "%Y%m%d")
    except: pass
    return datetime.now()

def calc_confidence(keywords, title_length):
    if not keywords: return 0.3
    return round(min(0.5 + len(keywords) * 0.15, 0.95), 2)


# ==============================================================================
# DART API (전자공시)
# ==============================================================================

class DartAPI:
    BASE = "https://opendart.fss.or.kr/api"
    CORP_FILE = "d:/neo4j-graphrag/CORPCODE.xml"
    RISK_KEYWORDS = {
        "횡령": 50, "배임": 50, "분식회계": 50, "소송": 25, "고발": 30, "고소": 25,
        "과징금": 35, "제재": 30, "벌금": 25, "손해배상": 20,
        "부도": 60, "파산": 60, "회생": 50, "워크아웃": 45, "자본잠식": 40, "채무불이행": 45,
        "부적정": 60, "한정": 35, "의견거절": 70, "감사범위제한": 30, "계속기업불확실": 40,
        "최대주주변경": 20, "대표이사": 10, "사임": 15, "해임": 25, "경영권분쟁": 35, "주주총회": 5,
        "사업중단": 40, "허가취소": 45, "영업정지": 40, "폐업": 50, "정정": 10, "조회공시": 5, "풍문": 5
    }
    CATEGORY_KEYWORDS = {
        "리스크": ["횡령", "배임", "소송", "과징금", "제재", "부도", "파산", "회생", "부적정", "한정", "의견거절"],
        "지배구조": ["최대주주", "대표이사", "사임", "해임", "선임", "임원", "정정"],
        "재무": ["사업보고서", "분기보고서", "반기보고서", "유상증자", "전환사채"]
    }
    PERSON_PATTERNS = [r"대표이사\s*([가-힣]{2,4})", r"([가-힣]{2,4})\s*대표", r"([가-힣]{2,4})\s*이사"]
    
    def __init__(self):
        self.key = os.getenv("OPENDART_API_KEY")
        self._load_codes()
        self._cache = {}
    
    def _load_codes(self):
        if not os.path.exists(self.CORP_FILE):
            r = requests.get(f"{self.BASE}/corpCode.xml?crtfc_key={self.key}")
            with open("d:/neo4j-graphrag/corpCode.zip", "wb") as f: f.write(r.content)
            with zipfile.ZipFile("d:/neo4j-graphrag/corpCode.zip", 'r') as z: z.extractall("d:/neo4j-graphrag/")
        tree = ET.parse(self.CORP_FILE)
        self.codes, self.corp_names = {}, set()
        for c in tree.getroot().findall('list'):
            name, code, stock = c.find('corp_name').text, c.find('corp_code').text, c.find('stock_code').text
            if name not in self.codes or (stock and stock.strip()): self.codes[name] = code
            self.corp_names.add(name)
    
    def get_code(self, name):
        if name in self.codes: return self.codes[name]
        clean = name.replace("㈜", "").replace("(주)", "").replace("주식회사", "").strip()
        if clean in self.codes: return self.codes[clean]
        candidates = []
        for corp_name in self.codes:
            corp_clean = corp_name.replace("㈜", "").replace("(주)", "").replace("주식회사", "").strip()
            if clean == corp_clean: return self.codes[corp_name]
            if clean in corp_clean or corp_clean in clean: candidates.append((len(corp_name), corp_name))
        if candidates: return self.codes[sorted(candidates)[0][1]]
        return None
    
    def _req(self, ep, p):
        key = f"{ep}:{json.dumps(p, sort_keys=True)}"
        if key in self._cache: return self._cache[key]
        p["crtfc_key"] = self.key
        try: r = requests.get(f"{self.BASE}/{ep}", params=p, timeout=15).json()
        except: r = {"status": "error"}
        self._cache[key] = r
        return r
    
    def get_info(self, code): return self._req("company.json", {"corp_code": code})
    
    def get_shareholders(self, code):
        r = self._req("hyslrSttus.json", {"corp_code": code, "bsns_year": "2024", "reprt_code": "11011"})
        if r.get("status") != "000":
            r = self._req("hyslrSttus.json", {"corp_code": code, "bsns_year": "2023", "reprt_code": "11011"})
        return r.get("list", []) if r.get("status") == "000" else []
    
    def get_executives(self, code):
        r = self._req("elestock.json", {"corp_code": code})
        return r.get("list", []) if r.get("status") == "000" else []
    
    def classify_category(self, title):
        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in title for kw in keywords): return cat
        return "재무"
    
    def calc_risk_score(self, title, date_str=None):
        score, matched = 0, []
        for kw, pts in self.RISK_KEYWORDS.items():
            if kw in title: score += pts; matched.append(f"{kw}({pts})")
        if date_str and score > 0:
            days_old = (datetime.now() - parse_date(date_str)).days
            score = round(score * calc_decay(max(0, days_old)))
        return min(score, 100), matched
    
    def extract_persons(self, title):
        persons = []
        for p in self.PERSON_PATTERNS: persons.extend(re.findall(p, title))
        return list(set(persons))
    
    def get_disclosures(self, code, corp_name, days=180):
        end, start = datetime.now(), datetime.now() - timedelta(days=days)
        r = self._req("list.json", {"corp_code": code, "bgn_de": start.strftime("%Y%m%d"), "end_de": end.strftime("%Y%m%d"), "page_count": 100})
        categorized = {"리스크": [], "지배구조": [], "재무": []}
        for d in r.get("list", []) if r.get("status") == "000" else []:
            title, date_str = d.get("report_nm", ""), d.get("rcept_dt", "")
            category = self.classify_category(title)
            score, keywords = self.calc_risk_score(title, date_str)
            categorized[category].append({"code": d.get("rcept_no", ""), "title": title, "date": date_str,
                "submitter": d.get("flr_nm", ""), "category": category, "risk_score": score,
                "keywords": keywords, "persons": self.extract_persons(title), "is_risk": score > 0})
        return categorized


# ==============================================================================
# 뉴스 스캐너
# ==============================================================================

class NewsScanner:
    RISK_KW = {"횡령": 50, "배임": 50, "분식회계": 50, "검찰": 30, "압수수색": 40, "구속": 40, "기소": 35,
               "소송": 20, "고발": 25, "제재": 30, "과징금": 30, "부도": 60, "파산": 60, "회생": 45,
               "위반": 15, "논란": 10, "비리": 25, "갑질": 15, "불매": 10, "스캔들": 15}
    
    def __init__(self): self.seen_urls = set()
    def reset_session(self): self.seen_urls = set()
    
    def scan(self, query, limit=15):
        articles, duplicates = [], 0
        try:
            r = requests.get("https://news.google.com/rss/search", params={"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"}, timeout=10)
            soup = BeautifulSoup(r.content, "xml")
            for item in soup.find_all("item")[:limit]:
                title = item.find("title").get_text() if item.find("title") else ""
                url = item.find("link").get_text() if item.find("link") else ""
                if url in self.seen_urls: duplicates += 1; continue
                self.seen_urls.add(url)
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                source = ""
                if " - " in title: parts = title.rsplit(" - ", 1); title, source = (parts[0], parts[1]) if len(parts)==2 else (title, "")
                matched, raw_score = [], 0
                for kw, pts in self.RISK_KW.items():
                    if kw in title: matched.append(f"{kw}({pts})"); raw_score += pts
                days_old = (datetime.now() - parse_date(pub_date)).days
                decay = calc_decay(max(0, days_old))
                decayed_score = round(raw_score * decay) if raw_score > 0 else 0
                articles.append({"title": title, "url": url, "date": pub_date, "source": source, "keywords": matched,
                    "raw_score": min(raw_score, 100), "risk_score": min(decayed_score, 100), "days_old": days_old,
                    "decay_rate": round(decay, 2), "confidence": calc_confidence(matched, len(title)),
                    "is_risk": decayed_score > 0, "sentiment": "부정" if decayed_score > 0 else "중립"})
        except Exception as e: print(f"  ⚠️ 뉴스 오류: {e}")
        time.sleep(0.3)
        return articles, duplicates


# ==============================================================================
# 네이버 뉴스 스캐너 (NEW - Day 2)
# ==============================================================================

class NaverNewsScanner:
    """네이버 뉴스 검색 스캐너 (한국 뉴스 커버리지 강화)"""
    RISK_KW = {
        "횡령": 50, "배임": 50, "분식회계": 50, "검찰": 30, "압수수색": 40, "구속": 40, "기소": 35,
        "소송": 20, "고발": 25, "제재": 30, "과징금": 30, "부도": 60, "파산": 60, "회생": 45,
        "위반": 15, "논란": 10, "비리": 25, "갑질": 15, "불매": 10, "스캔들": 15
    }
    
    def __init__(self):
        self.seen_urls = set()
    
    def reset_session(self):
        self.seen_urls = set()
    
    def scan(self, query, limit=15):
        """네이버 뉴스 RSS 검색"""
        articles, duplicates = [], 0
        try:
            # 네이버 뉴스 RSS 검색
            import urllib.parse
            encoded_query = urllib.parse.quote(query)
            url = f"https://news.google.com/rss/search?q={encoded_query}+site:naver.com&hl=ko&gl=KR&ceid=KR:ko"
            
            r = requests.get(url, timeout=10)
            soup = BeautifulSoup(r.content, "xml")
            
            for item in soup.find_all("item")[:limit]:
                title = item.find("title").get_text() if item.find("title") else ""
                article_url = item.find("link").get_text() if item.find("link") else ""
                
                if article_url in self.seen_urls:
                    duplicates += 1
                    continue
                self.seen_urls.add(article_url)
                
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                source = "네이버뉴스"
                
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title, source = (parts[0], parts[1]) if len(parts) == 2 else (title, "네이버뉴스")
                
                matched, raw_score = [], 0
                for kw, pts in self.RISK_KW.items():
                    if kw in title:
                        matched.append(f"{kw}({pts})")
                        raw_score += pts
                
                days_old = (datetime.now() - parse_date(pub_date)).days
                decay = calc_decay(max(0, days_old))
                decayed_score = round(raw_score * decay) if raw_score > 0 else 0
                
                articles.append({
                    "title": title,
                    "url": article_url,
                    "date": pub_date,
                    "source": source,
                    "keywords": matched,
                    "raw_score": min(raw_score, 100),
                    "risk_score": min(decayed_score, 100),
                    "days_old": days_old,
                    "decay_rate": round(decay, 2),
                    "confidence": calc_confidence(matched, len(title)),
                    "is_risk": decayed_score > 0,
                    "sentiment": "부정" if decayed_score > 0 else "중립",
                    "channel": "naver"
                })
                
        except Exception as e:
            print(f"  ⚠️ 네이버뉴스 오류: {e}")
        
        time.sleep(0.3)
        return articles, duplicates


# ==============================================================================
# KIND 공시 스캐너 (NEW - Day 2)
# ==============================================================================

class KindScanner:
    """한국거래소 KIND 공시 스캐너 (실제 KIND RSS + 뉴스 폴백)"""
    KIND_RSS_URL = "http://kind.krx.co.kr/disclosure/todaydisclosure.do"
    
    RISK_KW = {
        "상장폐지": 80, "관리종목": 70, "불성실공시": 60, "조회공시": 40,
        "횡령": 60, "배임": 60, "소송": 35, "가압류": 45, "피소": 40,
        "감사의견거절": 75, "의견거절": 70, "한정": 50, "계속기업": 65,
        "부도": 75, "회생": 55, "파산": 80, "채무불이행": 70,
        "유상증자": 20, "무상감자": 45, "자본잠식": 60,
        "정정공시": 25, "단일판매": 20, "최대주주변경": 35
    }
    
    def __init__(self):
        self.seen_ids = set()
    
    def reset_session(self):
        self.seen_ids = set()
    
    def scan(self, company, limit=10):
        """KIND RSS 공시 검색 (실제 KIND 사이트 크롤링 + 뉴스 폴백)"""
        disclosures, duplicates = [], 0
        
        # 1차: KIND 웹사이트 직접 크롤링 시도
        try:
            kind_url = f"http://kind.krx.co.kr/disclosure/todaydisclosure.do?method=searchTodayDisclosureSub&searchCorpName={company}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            r = requests.get(kind_url, headers=headers, timeout=10)
            
            if r.status_code == 200 and company in r.text:
                # KIND 페이지 파싱
                soup = BeautifulSoup(r.content, "html.parser")
                rows = soup.select("table.list tbody tr")[:limit]
                
                for row in rows:
                    cols = row.select("td")
                    if len(cols) >= 4:
                        title = cols[2].get_text(strip=True) if cols[2] else ""
                        corp = cols[1].get_text(strip=True) if cols[1] else ""
                        date_str = cols[0].get_text(strip=True) if cols[0] else ""
                        link = cols[2].find("a")
                        url = f"http://kind.krx.co.kr{link.get('href', '')}" if link else ""
                        
                        if company not in corp and company not in title:
                            continue
                        
                        if url in self.seen_ids:
                            duplicates += 1
                            continue
                        self.seen_ids.add(url)
                        
                        matched, raw_score = [], 0
                        for kw, pts in self.RISK_KW.items():
                            if kw in title:
                                matched.append(f"{kw}({pts})")
                                raw_score += pts
                        
                        disclosures.append({
                            "title": f"[KIND] {title}",
                            "url": url,
                            "date": date_str,
                            "source": "KIND 공시",
                            "keywords": matched,
                            "raw_score": min(raw_score, 100),
                            "risk_score": min(raw_score, 100),  # KIND 공시는 시의성이 높아 decay 미적용
                            "is_risk": raw_score > 0,
                            "sentiment": "부정" if raw_score > 0 else "중립",
                            "channel": "kind_direct"
                        })
                
                if disclosures:
                    print(f"     ✅ KIND 직접 수집 성공")
                    time.sleep(0.3)
                    return disclosures, duplicates
        except Exception as e:
            print(f"     ⚠️ KIND 직접 수집 실패, 뉴스 폴백: {e}")
        
        # 2차: 뉴스 폴백
        try:
            query = f"{company} KIND 공시 OR 한국거래소 공시"
            r = requests.get(
                "https://news.google.com/rss/search",
                params={"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"},
                timeout=10
            )
            soup = BeautifulSoup(r.content, "xml")
            
            for item in soup.find_all("item")[:limit]:
                title = item.find("title").get_text() if item.find("title") else ""
                url = item.find("link").get_text() if item.find("link") else ""
                
                if url in self.seen_ids:
                    duplicates += 1
                    continue
                self.seen_ids.add(url)
                
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                source = "KIND뉴스"
                
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title, source = (parts[0], parts[1]) if len(parts) == 2 else (title, "KIND뉴스")
                
                matched, raw_score = [], 0
                for kw, pts in self.RISK_KW.items():
                    if kw in title:
                        matched.append(f"{kw}({pts})")
                        raw_score += pts
                
                days_old = (datetime.now() - parse_date(pub_date)).days
                decay = calc_decay(max(0, days_old))
                decayed_score = round(raw_score * decay) if raw_score > 0 else 0
                
                disclosures.append({
                    "title": title,
                    "url": url,
                    "date": pub_date,
                    "source": source,
                    "keywords": matched,
                    "raw_score": min(raw_score, 100),
                    "risk_score": min(decayed_score, 100),
                    "days_old": days_old,
                    "decay_rate": round(decay, 2),
                    "is_risk": decayed_score > 0,
                    "sentiment": "부정" if decayed_score > 0 else "중립",
                    "channel": "kind_news"
                })
                
        except Exception as e:
            print(f"  ⚠️ KIND 뉴스 폴백 오류: {e}")
        
        time.sleep(0.3)
        return disclosures, duplicates


# ==============================================================================
# 다음 뉴스 스캐너 (C2)
# ==============================================================================

class DaumNewsScanner:
    """다음 뉴스 스캐너 (댓글 여론 포함)"""
    RISK_KW = {
        "횡령": 50, "배임": 50, "분식회계": 50, "검찰": 30, "압수수색": 40, "구속": 40, "기소": 35,
        "소송": 20, "고발": 25, "제재": 30, "과징금": 30, "부도": 60, "파산": 60, "회생": 45,
        "위반": 15, "논란": 10, "비리": 25, "갑질": 15, "불매": 10, "스캔들": 15
    }
    
    def __init__(self):
        self.seen_urls = set()
    
    def reset_session(self):
        self.seen_urls = set()
    
    def scan(self, company, limit=10):
        articles, duplicates = [], 0
        try:
            import urllib.parse
            encoded = urllib.parse.quote(company)
            url = f"https://news.google.com/rss/search?q={encoded}+site:daum.net&hl=ko&gl=KR&ceid=KR:ko"
            r = requests.get(url, timeout=10)
            soup = BeautifulSoup(r.content, "xml")
            
            for item in soup.find_all("item")[:limit]:
                title = item.find("title").get_text() if item.find("title") else ""
                article_url = item.find("link").get_text() if item.find("link") else ""
                if article_url in self.seen_urls: duplicates += 1; continue
                self.seen_urls.add(article_url)
                
                source = "다음뉴스"
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title, source = (parts[0], parts[1]) if len(parts) == 2 else (title, "다음뉴스")
                
                matched, raw = [], 0
                for kw, pts in self.RISK_KW.items():
                    if kw in title: matched.append(f"{kw}({pts})"); raw += pts
                
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                days_old = (datetime.now() - parse_date(pub_date)).days
                score = round(raw * calc_decay(max(0, days_old)))
                
                articles.append({
                    "title": title, "url": article_url, "date": pub_date, "source": source,
                    "keywords": matched, "risk_score": min(score, 100), "is_risk": score > 0,
                    "sentiment": "부정" if score > 0 else "중립", "channel": "daum"
                })
        except Exception as e: print(f"  ⚠️ 다음뉴스 오류: {e}")
        time.sleep(0.3)
        return articles, duplicates


# ==============================================================================
# 대법원 판례 스캐너 (C5)
# ==============================================================================

class CourtScanner:
    """대법원 판례/사건 검색 스캐너"""
    RISK_KW = {
        "판결": 25, "패소": 50, "승소": -10, "손해배상": 40, "원고": 15, "피고": 15,
        "기각": 20, "인용": 25, "항소": 20, "상고": 25, "대법원": 20,
        "형사": 35, "민사": 20, "행정": 25, "가처분": 35, "가압류": 40
    }
    
    def __init__(self):
        self.seen_urls = set()
    
    def reset_session(self):
        self.seen_urls = set()
    
    def scan(self, company, limit=10):
        articles, duplicates = [], 0
        try:
            query = f"{company} 대법원 판결 OR 판례 OR 소송"
            r = requests.get("https://news.google.com/rss/search",
                params={"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"}, timeout=10)
            soup = BeautifulSoup(r.content, "xml")
            
            for item in soup.find_all("item")[:limit]:
                title = item.find("title").get_text() if item.find("title") else ""
                url = item.find("link").get_text() if item.find("link") else ""
                if url in self.seen_urls: duplicates += 1; continue
                self.seen_urls.add(url)
                
                source = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title, source = (parts[0], parts[1]) if len(parts) == 2 else (title, "")
                
                matched, raw = [], 0
                for kw, pts in self.RISK_KW.items():
                    if kw in title: matched.append(f"{kw}({pts})"); raw += pts
                
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                days_old = (datetime.now() - parse_date(pub_date)).days
                score = round(max(0, raw) * calc_decay(max(0, days_old)) * 1.3)  # 법원 판결 가중
                
                articles.append({
                    "title": title, "url": url, "date": pub_date, "source": source,
                    "keywords": matched, "risk_score": min(score, 100), "is_risk": score > 0,
                    "sentiment": "부정" if score > 0 else "중립", "channel": "court"
                })
        except Exception as e: print(f"  ⚠️ 대법원 스캔 오류: {e}")
        time.sleep(0.3)
        return articles, duplicates



# ==============================================================================
# 신용평가사 스캐너 (C10)
# ==============================================================================

class RatingAgencyScanner:
    """신용평가사 직접 발표 스캐너"""
    AGENCIES = ["한국신용평가", "한신평", "NICE", "나이스신용평가", "한국기업평가", "한기평", 
                "S&P", "무디스", "Moody", "피치", "Fitch"]
    RISK_KW = {
        "하향": 60, "하락": 55, "강등": 60, "부정적": 40, "워치": 45,
        "투기등급": 70, "BB": 30, "B등급": 45, "CCC": 65, "디폴트": 80,
        "유동성": 35, "재무위험": 45, "상환능력": 40
    }
    POSITIVE_KW = {
        "상향": -30, "상승": -25, "긍정적": -20, "안정적": -15, "투자등급": -20
    }
    
    def __init__(self):
        self.seen_urls = set()
    
    def reset_session(self):
        self.seen_urls = set()
    
    def scan(self, company, limit=10):
        articles, duplicates = [], 0
        try:
            # 신용평가사 직접 언급 검색
            agencies_query = " OR ".join(self.AGENCIES[:5])
            query = f"{company} ({agencies_query}) 신용등급"
            r = requests.get("https://news.google.com/rss/search",
                params={"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"}, timeout=10)
            soup = BeautifulSoup(r.content, "xml")
            
            for item in soup.find_all("item")[:limit]:
                title = item.find("title").get_text() if item.find("title") else ""
                url = item.find("link").get_text() if item.find("link") else ""
                if url in self.seen_urls: duplicates += 1; continue
                self.seen_urls.add(url)
                
                # 신용평가사 언급 확인
                agency_found = next((a for a in self.AGENCIES if a in title), None)
                if not agency_found: continue  # 신용평가사 미언급시 스킵
                
                source = agency_found
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title, source = (parts[0], agency_found) if len(parts) == 2 else (title, agency_found)
                
                matched, raw = [], 0
                for kw, pts in self.RISK_KW.items():
                    if kw in title: matched.append(f"{kw}({pts})"); raw += pts
                for kw, pts in self.POSITIVE_KW.items():
                    if kw in title: matched.append(f"{kw}({pts})"); raw += pts
                
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                days_old = (datetime.now() - parse_date(pub_date)).days
                score = round(max(0, raw) * calc_decay(max(0, days_old)) * 1.5)  # 평가사 직접 발표 고가중
                
                articles.append({
                    "title": title, "url": url, "date": pub_date, "source": source,
                    "keywords": matched, "risk_score": min(score, 100), "is_risk": score > 0,
                    "sentiment": "부정" if score > 0 else "중립", "channel": "rating_agency",
                    "agency": agency_found
                })
        except Exception as e: print(f"  ⚠️ 신용평가사 스캔 오류: {e}")
        time.sleep(0.3)
        return articles, duplicates


class PatentScanner:
    """KIPRIS API 연동 특허 스캐너 (구글 뉴스 폴백 포함)"""
    KIPRIS_BASE = "http://plus.kipris.or.kr/openapi/rest"
    RISK_KW = {"특허침해": 45, "무효심판": 35, "기술유출": 50, "영업비밀": 45, "특허소송": 40, "침해": 30, "분쟁": 25}
    
    def __init__(self, use_kipris: bool = True):
        self.api_key = os.getenv("KIPRIS_API_KEY")
        self.seen_ids = set()
        # use_kipris=False 이면 API 키가 있어도 비활성화
        self.use_kipris = use_kipris and bool(self.api_key)
        if self.use_kipris:
            print("✅ KIPRIS API 활성화됨")
        elif self.api_key and not use_kipris:
            print("⏸️ KIPRIS API 비활성화됨 (옵션)")
    
    def reset_session(self):
        self.seen_ids = set()
    
    def _search_kipris(self, company: str, limit: int = 10) -> List[Dict]:
        """KIPRIS API로 특허 검색"""
        patents = []
        try:
            # 출원인 검색 API
            url = f"{self.KIPRIS_BASE}/patUtiModInfoSearchSevice/applicantNameSearchInfo"
            params = {
                "applicant": company,
                "ServiceKey": self.api_key,
                "numOfRows": limit,
                "pageNo": 1
            }
            r = requests.get(url, params=params, timeout=15)
            
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                items = root.findall(".//item")
                
                for item in items[:limit]:
                    app_no = item.findtext("applicationNumber", "")
                    if app_no in self.seen_ids:
                        continue
                    self.seen_ids.add(app_no)
                    
                    title = item.findtext("inventionTitle", "")
                    app_date = item.findtext("applicationDate", "")
                    status = item.findtext("registerStatus", "")
                    
                    # 리스크 키워드 매칭
                    matched, raw = [], 0
                    for kw, pts in self.RISK_KW.items():
                        if kw in title or kw in status:
                            matched.append(f"{kw}({pts})")
                            raw += pts
                    
                    patents.append({
                        "title": title,
                        "url": f"https://kipris.or.kr/patent/{app_no}",
                        "date": app_date,
                        "source": "KIPRIS",
                        "application_number": app_no,
                        "status": status,
                        "keywords": matched,
                        "risk_score": min(raw, 100),
                        "is_risk": raw > 0,
                        "sentiment": "부정" if raw > 0 else "중립"
                    })
                
                print(f"   📜 KIPRIS: {len(patents)}건 조회")
        except Exception as e:
            print(f"  ⚠️ KIPRIS API 오류: {e}")
        
        return patents
    
    def _search_news(self, company: str, limit: int = 10) -> List[Dict]:
        """구글 뉴스 폴백 검색"""
        articles = []
        try:
            r = requests.get("https://news.google.com/rss/search", 
                           params={"q": f"{company} 특허 소송", "hl": "ko", "gl": "KR", "ceid": "KR:ko"}, 
                           timeout=10)
            soup = BeautifulSoup(r.content, "xml")
            for item in soup.find_all("item")[:limit]:
                title = item.find("title").get_text() if item.find("title") else ""
                url = item.find("link").get_text() if item.find("link") else ""
                if url in self.seen_ids:
                    continue
                self.seen_ids.add(url)
                source = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title, source = (parts[0], parts[1]) if len(parts) == 2 else (title, "")
                matched, raw = [], 0
                for kw, pts in self.RISK_KW.items():
                    if kw in title:
                        matched.append(f"{kw}({pts})")
                        raw += pts
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                days_old = (datetime.now() - parse_date(pub_date)).days
                score = round(raw * calc_decay(max(0, days_old))) if raw > 0 else 0
                articles.append({
                    "title": title, "url": url, "date": pub_date, "source": source,
                    "keywords": matched, "risk_score": min(score, 100), "is_risk": score > 0,
                    "sentiment": "부정" if score > 0 else "중립"
                })
        except Exception as e:
            print(f"  ⚠️ 특허 뉴스 스캔 오류: {e}")
        time.sleep(0.3)
        return articles
    
    def scan(self, company: str, limit: int = 10) -> tuple:
        """특허 정보 스캔 (KIPRIS + 뉴스 병합)"""
        results = []
        
        # KIPRIS API 사용 가능하면 먼저 조회
        if self.use_kipris:
            kipris_results = self._search_kipris(company, limit)
            results.extend(kipris_results)
        
        # 뉴스로 보충
        news_results = self._search_news(company, max(5, limit - len(results)))
        results.extend(news_results)
        
        return results[:limit], 0


class ReviewScanner:
    RISK_KW = {"횡령": 45, "갑질": 30, "급여체불": 50, "구조조정": 35, "권고사직": 40, "대량해고": 45}
    def __init__(self): self.seen_urls = set()
    def reset_session(self): self.seen_urls = set()
    def scan(self, company, limit=10):
        articles, duplicates = [], 0
        try:
            r = requests.get("https://news.google.com/rss/search", params={"q": f"{company} 구조조정 OR 갑질", "hl": "ko", "gl": "KR", "ceid": "KR:ko"}, timeout=10)
            soup = BeautifulSoup(r.content, "xml")
            for item in soup.find_all("item")[:limit]:
                title = item.find("title").get_text() if item.find("title") else ""
                url = item.find("link").get_text() if item.find("link") else ""
                if url in self.seen_urls: duplicates += 1; continue
                self.seen_urls.add(url)
                source = ""
                if " - " in title: parts = title.rsplit(" - ", 1); title, source = (parts[0], parts[1]) if len(parts)==2 else (title, "")
                matched, raw = [], 0
                for kw, pts in self.RISK_KW.items():
                    if kw in title: matched.append(f"{kw}({pts})"); raw += pts
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                days_old = (datetime.now() - parse_date(pub_date)).days
                score = round(raw * calc_decay(max(0, days_old))) if raw > 0 else 0
                articles.append({"title": title, "url": url, "date": pub_date, "source": source, 
                    "keywords": matched, "risk_score": min(score, 100), "is_risk": score > 0,
                    "sentiment": "부정" if score > 0 else "중립"})
        except Exception as e: print(f"  ⚠️ 리뷰 스캔 오류: {e}")
        time.sleep(0.3)
        return articles, duplicates


# ==============================================================================
# 소송/판결 스캐너 (NEW - Day 1)
# ==============================================================================

class LegalScanner:
    """대법원 판례/소송 관련 뉴스 스캐너"""
    RISK_KW = {
        "소송": 30, "패소": 50, "손해배상": 40, "가처분": 35, "가압류": 45,
        "파산": 70, "회생": 50, "청산": 60, "경매": 45, "압류": 40,
        "형사고발": 55, "기소": 50, "구속": 80, "징역": 70, "벌금": 35,
        "과징금": 40, "제재": 35, "금지명령": 45, "판결": 25, "항소": 20
    }
    
    def __init__(self):
        self.seen_urls = set()
    
    def reset_session(self):
        self.seen_urls = set()
    
    def scan(self, company, limit=10):
        """소송/판결 관련 뉴스 스캔"""
        articles, duplicates = [], 0
        try:
            # 법적 리스크 관련 뉴스 검색
            query = f"{company} 소송 OR 패소 OR 가압류 OR 파산 OR 회생"
            r = requests.get(
                "https://news.google.com/rss/search",
                params={"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"},
                timeout=10
            )
            soup = BeautifulSoup(r.content, "xml")
            
            for item in soup.find_all("item")[:limit]:
                title = item.find("title").get_text() if item.find("title") else ""
                url = item.find("link").get_text() if item.find("link") else ""
                
                if url in self.seen_urls:
                    duplicates += 1
                    continue
                self.seen_urls.add(url)
                
                source = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title, source = (parts[0], parts[1]) if len(parts) == 2 else (title, "")
                
                matched, raw = [], 0
                for kw, pts in self.RISK_KW.items():
                    if kw in title:
                        matched.append(f"{kw}({pts})")
                        raw += pts
                
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                days_old = (datetime.now() - parse_date(pub_date)).days
                score = round(raw * calc_decay(max(0, days_old))) if raw > 0 else 0
                
                # 소송/법적 리스크는 가중치 1.5배
                score = min(round(score * 1.5), 100)
                
                articles.append({
                    "title": title,
                    "url": url,
                    "date": pub_date,
                    "source": source,
                    "keywords": matched,
                    "risk_score": score,
                    "is_risk": score > 0,
                    "sentiment": "부정" if score > 0 else "중립",
                    "case_type": self._classify_case_type(title),
                    "severity": "high" if score > 50 else "medium" if score > 25 else "low"
                })
                
        except Exception as e:
            print(f"  ⚠️ 소송 스캔 오류: {e}")
        
        time.sleep(0.3)
        return articles, duplicates
    
    def _classify_case_type(self, title):
        """소송 유형 분류"""
        if any(kw in title for kw in ["형사", "구속", "징역", "기소", "검찰"]):
            return "형사"
        elif any(kw in title for kw in ["파산", "회생", "청산", "경매"]):
            return "도산"
        elif any(kw in title for kw in ["행정", "과징금", "제재", "금감원"]):
            return "행정"
        else:
            return "민사"


# ==============================================================================
# 신용등급 스캐너 (NEW - Day 1)
# ==============================================================================

class CreditScanner:
    """신용등급 변동 관련 뉴스 스캐너"""
    RISK_KW = {
        "신용등급 하락": 60, "등급 하향": 55, "하향 조정": 50,
        "워치리스트": 45, "부정적 전망": 40, "부정적": 30,
        "투기등급": 70, "BB": 35, "B등급": 45, "C등급": 65, "D등급": 80,
        "디폴트": 80, "채무불이행": 75, "이자 미지급": 60,
        "유동성 위험": 50, "재무 악화": 45, "적자": 30, "영업손실": 35
    }
    
    POSITIVE_KW = {
        "신용등급 상향": -30, "등급 상향": -25, "긍정적 전망": -20,
        "재무 개선": -15, "투자등급": -20, "A등급": -10
    }
    
    RATING_AGENCIES = ["한국신용평가", "한신평", "NICE", "나이스신용평가", "한국기업평가", "한기평", "S&P", "무디스", "피치"]
    
    def __init__(self):
        self.seen_urls = set()
    
    def reset_session(self):
        self.seen_urls = set()
    
    def scan(self, company, limit=10):
        """신용등급 관련 뉴스 스캔"""
        articles, duplicates = [], 0
        try:
            query = f"{company} 신용등급 OR 등급 전망 OR 워치리스트 OR 재무"
            r = requests.get(
                "https://news.google.com/rss/search",
                params={"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"},
                timeout=10
            )
            soup = BeautifulSoup(r.content, "xml")
            
            for item in soup.find_all("item")[:limit]:
                title = item.find("title").get_text() if item.find("title") else ""
                url = item.find("link").get_text() if item.find("link") else ""
                
                if url in self.seen_urls:
                    duplicates += 1
                    continue
                self.seen_urls.add(url)
                
                source = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title, source = (parts[0], parts[1]) if len(parts) == 2 else (title, "")
                
                matched, raw = [], 0
                
                # 부정적 키워드
                for kw, pts in self.RISK_KW.items():
                    if kw in title:
                        matched.append(f"{kw}({pts})")
                        raw += pts
                
                # 긍정적 키워드 (점수 감소)
                for kw, pts in self.POSITIVE_KW.items():
                    if kw in title:
                        matched.append(f"{kw}({pts})")
                        raw += pts
                
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                days_old = (datetime.now() - parse_date(pub_date)).days
                score = round(max(0, raw) * calc_decay(max(0, days_old)))
                
                # 신용평가사 언급 시 신뢰도 가중
                agency_mentioned = any(agency in title for agency in self.RATING_AGENCIES)
                if agency_mentioned and score > 0:
                    score = min(round(score * 1.3), 100)
                
                articles.append({
                    "title": title,
                    "url": url,
                    "date": pub_date,
                    "source": source,
                    "keywords": matched,
                    "risk_score": min(score, 100),
                    "is_risk": score > 0,
                    "sentiment": "부정" if score > 0 else "중립",
                    "rating_change": self._detect_rating_change(title),
                    "agency": self._detect_agency(title)
                })
                
        except Exception as e:
            print(f"  ⚠️ 신용등급 스캔 오류: {e}")
        
        time.sleep(0.3)
        return articles, duplicates
    
    def _detect_rating_change(self, title):
        """등급 변동 방향 감지"""
        if any(kw in title for kw in ["상향", "상승", "개선", "긍정"]):
            return "upgrade"
        elif any(kw in title for kw in ["하향", "하락", "악화", "부정"]):
            return "downgrade"
        else:
            return "maintain"
    
    def _detect_agency(self, title):
        """신용평가사 감지"""
        for agency in self.RATING_AGENCIES:
            if agency in title:
                return agency
        return None


# ==============================================================================
# 금융감독원 제재 스캐너 (B2)
# ==============================================================================

class FssScanner:
    """금융감독원 제재/제재현황 스캐너 (FSS 직접 크롤링 + 뉴스 폴백)"""
    FSS_BASE_URL = "https://www.fss.or.kr"
    
    RISK_KW = {
        "과징금": 50, "영업정지": 70, "경고": 30, "주의": 20,
        "제재": 40, "금감원": 25, "금융위": 30, "금융감독원": 25,
        "인가취소": 80, "허가취소": 75, "임원해임": 60, "직무정지": 55,
        "불완전판매": 45, "자금세탁": 70, "내부통제": 35,
        "검사결과": 35, "시정명령": 45, "기관경고": 50
    }
    
    def __init__(self):
        self.seen_urls = set()
    
    def reset_session(self):
        self.seen_urls = set()
    
    def scan(self, company, limit=10):
        articles, duplicates = [], 0
        
        # 1차: 금감원 웹사이트 직접 크롤링 시도
        try:
            # 금감원 보도자료/제재현황 검색
            fss_search_url = f"{self.FSS_BASE_URL}/fss/kr/bbs/list.do?bbsId=1289308592138&searchWrd={company}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            r = requests.get(fss_search_url, headers=headers, timeout=10)
            
            if r.status_code == 200:
                soup = BeautifulSoup(r.content, "html.parser")
                items = soup.select("ul.bdList li")[:limit]
                
                for item in items:
                    title_elem = item.select_one("a")
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    if company not in title:
                        continue
                    
                    href = title_elem.get("href", "")
                    url = f"{self.FSS_BASE_URL}{href}" if href.startswith("/") else href
                    
                    if url in self.seen_urls:
                        duplicates += 1
                        continue
                    self.seen_urls.add(url)
                    
                    date_elem = item.select_one("span.date")
                    date_str = date_elem.get_text(strip=True) if date_elem else ""
                    
                    matched, raw = [], 0
                    for kw, pts in self.RISK_KW.items():
                        if kw in title:
                            matched.append(f"{kw}({pts})")
                            raw += pts
                    
                    articles.append({
                        "title": f"[금감원] {title}",
                        "url": url,
                        "date": date_str,
                        "source": "금융감독원",
                        "keywords": matched,
                        "risk_score": min(raw, 100),  # 금감원 직접 발표는 decay 미적용
                        "is_risk": raw > 0,
                        "sentiment": "부정" if raw > 0 else "중립",
                        "channel": "fss_direct"
                    })
                
                if articles:
                    print(f"     ✅ 금감원 직접 수집 성공")
                    time.sleep(0.3)
                    return articles, duplicates
        except Exception as e:
            print(f"     ⚠️ 금감원 직접 수집 실패, 뉴스 폴백: {e}")
        
        # 2차: 뉴스 폴백
        try:
            query = f"{company} 금감원 제재 OR 금융감독원 제재 OR 과징금"
            r = requests.get("https://news.google.com/rss/search",
                params={"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"}, timeout=10)
            soup = BeautifulSoup(r.content, "xml")
            
            for item in soup.find_all("item")[:limit]:
                title = item.find("title").get_text() if item.find("title") else ""
                url = item.find("link").get_text() if item.find("link") else ""
                if url in self.seen_urls: duplicates += 1; continue
                self.seen_urls.add(url)
                
                source = "금감원뉴스"
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title, source = (parts[0], parts[1]) if len(parts) == 2 else (title, "금감원뉴스")
                
                matched, raw = [], 0
                for kw, pts in self.RISK_KW.items():
                    if kw in title: matched.append(f"{kw}({pts})"); raw += pts
                
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                days_old = (datetime.now() - parse_date(pub_date)).days
                score = round(raw * calc_decay(max(0, days_old)) * 1.3) if raw > 0 else 0
                
                articles.append({
                    "title": title, "url": url, "date": pub_date, "source": source,
                    "keywords": matched, "risk_score": min(score, 100), "is_risk": score > 0,
                    "sentiment": "부정" if score > 0 else "중립", "channel": "fss_news"
                })
        except Exception as e: print(f"  ⚠️ 금감원 뉴스 폴백 오류: {e}")
        time.sleep(0.3)
        return articles, duplicates


# ==============================================================================
# ESG 평가 스캐너 (B4)
# ==============================================================================

class EsgScanner:
    """ESG (환경/사회/지배구조) 리스크 스캐너"""
    RISK_KW = {
        # 환경 (E)
        "환경오염": 50, "탄소배출": 30, "그린워싱": 45, "폐수": 40, "유해물질": 45,
        "환경부": 25, "환경규제": 30, "온실가스": 25, "기후리스크": 35,
        # 사회 (S)
        "산업재해": 50, "사망사고": 60, "노동법": 35, "아동노동": 70, "갑질": 40,
        "성희롱": 45, "차별": 35, "불매운동": 40, "인권침해": 50,
        # 지배구조 (G)
        "횡령": 60, "배임": 60, "분식회계": 65, "일감몰아주기": 45, "오너리스크": 40,
        "지배구조": 20, "사외이사": 15, "이사회": 15
    }
    
    POSITIVE_KW = {
        "ESG 우수": -20, "친환경": -15, "RE100": -15, "탄소중립": -15,
        "사회공헌": -10, "지배구조 개선": -15
    }
    
    def __init__(self):
        self.seen_urls = set()
    
    def reset_session(self):
        self.seen_urls = set()
    
    def scan(self, company, limit=10):
        articles, duplicates = [], 0
        try:
            query = f"{company} ESG OR 환경오염 OR 산업재해 OR 그린워싱 OR 지배구조"
            r = requests.get("https://news.google.com/rss/search",
                params={"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"}, timeout=10)
            soup = BeautifulSoup(r.content, "xml")
            
            for item in soup.find_all("item")[:limit]:
                title = item.find("title").get_text() if item.find("title") else ""
                url = item.find("link").get_text() if item.find("link") else ""
                if url in self.seen_urls: duplicates += 1; continue
                self.seen_urls.add(url)
                
                source = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title, source = (parts[0], parts[1]) if len(parts) == 2 else (title, "")
                
                matched, raw = [], 0
                for kw, pts in self.RISK_KW.items():
                    if kw in title: matched.append(f"{kw}({pts})"); raw += pts
                for kw, pts in self.POSITIVE_KW.items():
                    if kw in title: matched.append(f"{kw}({pts})"); raw += pts
                
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                days_old = (datetime.now() - parse_date(pub_date)).days
                score = round(max(0, raw) * calc_decay(max(0, days_old)))
                
                articles.append({
                    "title": title, "url": url, "date": pub_date, "source": source,
                    "keywords": matched, "risk_score": min(score, 100), "is_risk": score > 0,
                    "sentiment": "부정" if score > 0 else "중립",
                    "esg_category": self._classify_esg(title)
                })
        except Exception as e: print(f"  ⚠️ ESG 스캔 오류: {e}")
        time.sleep(0.3)
        return articles, duplicates
    
    def _classify_esg(self, title):
        if any(kw in title for kw in ["환경", "탄소", "폐수", "오염", "기후"]): return "E"
        elif any(kw in title for kw in ["사망", "재해", "노동", "갑질", "인권", "불매"]): return "S"
        elif any(kw in title for kw in ["횡령", "배임", "분식", "지배구조", "이사"]): return "G"
        return "ESG"


# ==============================================================================
# SNS/커뮤니티 스캐너 (B5)
# ==============================================================================

class SocialScanner:
    """SNS/커뮤니티 여론 스캐너 (블라인드, 직장인 커뮤니티 통합)"""
    # BlindScanner 키워드 통합됨
    RISK_KW = {
        # 블라인드/직장인 관련
        "블라인드": 25, "퇴사": 30, "야근": 20, "갑질": 45, "급여체불": 55,
        "워라밸": 15, "권고사직": 50, "구조조정": 40, "희망퇴직": 35, "정리해고": 55,
        "복지": 10, "연봉": 10, "인사평가": 20, "직원": 10, "내부": 20,
        # SNS/여론 관련
        "불매": 35, "불매운동": 45, "보이콧": 40, "논란": 25, "비판": 20,
        "루머": 15, "의혹": 25, "폭로": 40, "내부고발": 40, "제보": 35
    }
    
    def __init__(self):
        self.seen_urls = set()
    
    def reset_session(self):
        self.seen_urls = set()
    
    def scan(self, company, limit=10):
        articles, duplicates = [], 0
        try:
            # 통합 검색 쿼리 (블라인드 + SNS)
            query = f"{company} 블라인드 OR 직장인 OR 퇴사 OR 불매 OR 논란 OR 연봉"
            r = requests.get("https://news.google.com/rss/search",
                params={"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"}, timeout=10)
            soup = BeautifulSoup(r.content, "xml")
            
            for item in soup.find_all("item")[:limit]:
                title = item.find("title").get_text() if item.find("title") else ""
                url = item.find("link").get_text() if item.find("link") else ""
                if url in self.seen_urls: duplicates += 1; continue
                self.seen_urls.add(url)
                
                source = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title, source = (parts[0], parts[1]) if len(parts) == 2 else (title, "")
                
                matched, raw = [], 0
                for kw, pts in self.RISK_KW.items():
                    if kw in title: matched.append(f"{kw}({pts})"); raw += pts
                
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                days_old = (datetime.now() - parse_date(pub_date)).days
                score = round(raw * calc_decay(max(0, days_old)))
                
                articles.append({
                    "title": title, "url": url, "date": pub_date, "source": source,
                    "keywords": matched, "risk_score": min(score, 100), "is_risk": score > 0,
                    "sentiment": "부정" if score > 0 else "중립", "channel": "social"
                })
        except Exception as e: print(f"  ⚠️ SNS/블라인드 스캔 오류: {e}")
        time.sleep(0.3)
        return articles, duplicates


# ==============================================================================
# 부동산 등기 스캐너 (B6)
# ==============================================================================

class RealEstateScanner:
    """부동산 등기/담보 관련 스캐너"""
    RISK_KW = {
        "가압류": 60, "압류": 55, "경매": 50, "담보설정": 35, "근저당": 30,
        "부동산": 15, "매각": 25, "강제집행": 55, "처분금지": 45,
        "채권자": 30, "채무자": 25, "명도소송": 40, "퇴거": 30
    }
    
    def __init__(self):
        self.seen_urls = set()
    
    def reset_session(self):
        self.seen_urls = set()
    
    def scan(self, company, limit=10):
        articles, duplicates = [], 0
        try:
            query = f"{company} 부동산 가압류 OR 경매 OR 담보 OR 압류"
            r = requests.get("https://news.google.com/rss/search",
                params={"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"}, timeout=10)
            soup = BeautifulSoup(r.content, "xml")
            
            for item in soup.find_all("item")[:limit]:
                title = item.find("title").get_text() if item.find("title") else ""
                url = item.find("link").get_text() if item.find("link") else ""
                if url in self.seen_urls: duplicates += 1; continue
                self.seen_urls.add(url)
                
                source = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title, source = (parts[0], parts[1]) if len(parts) == 2 else (title, "")
                
                matched, raw = [], 0
                for kw, pts in self.RISK_KW.items():
                    if kw in title: matched.append(f"{kw}({pts})"); raw += pts
                
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                days_old = (datetime.now() - parse_date(pub_date)).days
                score = round(raw * calc_decay(max(0, days_old)))
                
                articles.append({
                    "title": title, "url": url, "date": pub_date, "source": source,
                    "keywords": matched, "risk_score": min(score, 100), "is_risk": score > 0,
                    "sentiment": "부정" if score > 0 else "중립"
                })
        except Exception as e: print(f"  ⚠️ 부동산 스캔 오류: {e}")
        time.sleep(0.3)
        return articles, duplicates


# ==============================================================================
# 상표/디자인 스캐너 (B7)
# ==============================================================================

class TrademarkScanner:
    """상표/디자인권 분쟁 스캐너"""
    RISK_KW = {
        "상표분쟁": 45, "상표권": 25, "상표침해": 50, "디자인침해": 45,
        "브랜드분쟁": 40, "위조": 35, "모방": 30, "표절": 35,
        "무효심판": 40, "권리범위": 30, "사용금지": 45
    }
    
    def __init__(self):
        self.seen_urls = set()
    
    def reset_session(self):
        self.seen_urls = set()
    
    def scan(self, company, limit=10):
        articles, duplicates = [], 0
        try:
            query = f"{company} 상표분쟁 OR 상표침해 OR 디자인침해 OR 브랜드분쟁"
            r = requests.get("https://news.google.com/rss/search",
                params={"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"}, timeout=10)
            soup = BeautifulSoup(r.content, "xml")
            
            for item in soup.find_all("item")[:limit]:
                title = item.find("title").get_text() if item.find("title") else ""
                url = item.find("link").get_text() if item.find("link") else ""
                if url in self.seen_urls: duplicates += 1; continue
                self.seen_urls.add(url)
                
                source = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title, source = (parts[0], parts[1]) if len(parts) == 2 else (title, "")
                
                matched, raw = [], 0
                for kw, pts in self.RISK_KW.items():
                    if kw in title: matched.append(f"{kw}({pts})"); raw += pts
                
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                days_old = (datetime.now() - parse_date(pub_date)).days
                score = round(raw * calc_decay(max(0, days_old)))
                
                articles.append({
                    "title": title, "url": url, "date": pub_date, "source": source,
                    "keywords": matched, "risk_score": min(score, 100), "is_risk": score > 0,
                    "sentiment": "부정" if score > 0 else "중립"
                })
        except Exception as e: print(f"  ⚠️ 상표 스캔 오류: {e}")
        time.sleep(0.3)
        return articles, duplicates


# ==============================================================================
# 경쟁사 동향 스캐너 (B8)
# ==============================================================================

class CompetitorScanner:
    """경쟁사 동향/시장점유율 스캐너"""
    RISK_KW = {
        "시장점유율": 20, "점유율": 15, "경쟁사": 15, "경쟁업체": 15,
        "추월": 30, "역전": 30, "1위": 10, "선두": 10,
        "이탈": 25, "고객이탈": 35, "시장잠식": 40, "경쟁심화": 25,
        "가격경쟁": 20, "출혈경쟁": 35, "덤핑": 30
    }
    
    POSITIVE_KW = {
        "시장점유율 상승": -20, "점유율 확대": -15, "시장선도": -15
    }
    
    def __init__(self):
        self.seen_urls = set()
    
    def reset_session(self):
        self.seen_urls = set()
    
    def scan(self, company, limit=10):
        articles, duplicates = [], 0
        try:
            query = f"{company} 시장점유율 OR 경쟁사 OR 경쟁심화 OR 점유율"
            r = requests.get("https://news.google.com/rss/search",
                params={"q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"}, timeout=10)
            soup = BeautifulSoup(r.content, "xml")
            
            for item in soup.find_all("item")[:limit]:
                title = item.find("title").get_text() if item.find("title") else ""
                url = item.find("link").get_text() if item.find("link") else ""
                if url in self.seen_urls: duplicates += 1; continue
                self.seen_urls.add(url)
                
                source = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title, source = (parts[0], parts[1]) if len(parts) == 2 else (title, "")
                
                matched, raw = [], 0
                for kw, pts in self.RISK_KW.items():
                    if kw in title: matched.append(f"{kw}({pts})"); raw += pts
                for kw, pts in self.POSITIVE_KW.items():
                    if kw in title: matched.append(f"{kw}({pts})"); raw += pts
                
                pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
                days_old = (datetime.now() - parse_date(pub_date)).days
                score = round(max(0, raw) * calc_decay(max(0, days_old)))
                
                articles.append({
                    "title": title, "url": url, "date": pub_date, "source": source,
                    "keywords": matched, "risk_score": min(score, 100), "is_risk": score > 0,
                    "sentiment": "부정" if score > 0 else "중립"
                })
        except Exception as e: print(f"  ⚠️ 경쟁사 스캔 오류: {e}")
        time.sleep(0.3)
        return articles, duplicates


# ==============================================================================
# 그래프 빌더 (Neo4j)
# ==============================================================================

class GraphBuilder:
    CORP_PATTERNS = ['㈜', '(주)', '주식회사', '보험', '은행', '증권', '재단', '공사', '홀딩스']
    
    def __init__(self):
        self.graph = Neo4jGraph(url=os.getenv("NEO4J_URI"), username=os.getenv("NEO4J_USERNAME"),
                                password=os.getenv("NEO4J_PASSWORD"), database=os.getenv("NEO4J_DATABASE", "neo4j"))
        self._setup()
    
    def _setup(self):
        for q in ["CREATE CONSTRAINT IF NOT EXISTS FOR (r:RiskLevel) REQUIRE r.level IS UNIQUE",
                  "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE",
                  "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE",
                  "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Disclosure) REQUIRE d.code IS UNIQUE",
                  "CREATE CONSTRAINT IF NOT EXISTS FOR (n:NewsArticle) REQUIRE n.url IS UNIQUE"]:
            try: self.graph.query(q)
            except: pass
        self._create_risk_levels()
    
    def _create_risk_levels(self):
        for level, label in [("GREEN", "🟢 정상"), ("YELLOW", "🟡 주의"), ("RED", "🔴 위험")]:
            self.graph.query("MERGE (r:RiskLevel {level: $l}) SET r.label = $lb", {"l": level, "lb": label})
    
    def reset(self):
        self.graph.query("MATCH (n) DETACH DELETE n")
        self._create_risk_levels()
        print("🗑️ 전체 데이터 초기화 완료")
    
    def is_corp(self, name): return any(p in name for p in self.CORP_PATTERNS)
    def clean(self, name): return name.replace('\n', ' ').strip() if name else ""
    def add_company(self, name, code=None): self.graph.query("MERGE (c:Company {name: $n}) SET c.corp_code = COALESCE($c, c.corp_code)", {"n": name, "c": code})
    def add_person(self, name): self.graph.query("MERGE (p:Person {name: $n})", {"n": name})
    
    def add_category(self, company, cat_type):
        cat_id = f"{company}_{cat_type}"
        labels = {"주주": "📊 주주", "임원": "👔 임원", "공시": "📄 공시", "뉴스": "📰 뉴스", "특허": "📜 특허", "채용리뷰": "🗣️ 채용리뷰"}
        self.graph.query("MATCH (c:Company {name: $company}) MERGE (cat:Category {id: $id}) SET cat.type = $type, cat.label = $label MERGE (c)-[:HAS_CATEGORY]->(cat)",
                        {"company": company, "id": cat_id, "type": cat_type, "label": labels.get(cat_type, cat_type)})
        return cat_id
    
    def add_disclosure_subcategory(self, parent_cat_id, subcat_type, count, risk_score):
        subcat_id = f"{parent_cat_id}_{subcat_type}"
        labels = {"리스크": "⚠️ 리스크공시", "지배구조": "👥 지배구조공시", "재무": "📄 재무공시"}
        self.graph.query("MATCH (cat:Category {id: $parent}) MERGE (sub:DisclosureCategory {id: $id}) SET sub.type = $type, sub.label = $label, sub.count = $count, sub.risk_score = $risk MERGE (cat)-[:HAS_SUBCATEGORY]->(sub)",
                        {"parent": parent_cat_id, "id": subcat_id, "type": subcat_type, "label": labels.get(subcat_type, subcat_type), "count": count, "risk": risk_score})
        return subcat_id
    
    def add_news_subcategory(self, parent_cat_id, subcat_type):
        subcat_id = f"{parent_cat_id}_{subcat_type}"
        labels = {"기업": "🏢 기업뉴스", "주주": "👤 주주뉴스", "임원": "👔 임원뉴스"}
        self.graph.query("MATCH (cat:Category {id: $parent}) MERGE (sub:NewsCategory {id: $id}) SET sub.type = $type, sub.label = $label MERGE (cat)-[:HAS_SUBCATEGORY]->(sub)",
                        {"parent": parent_cat_id, "id": subcat_id, "type": subcat_type, "label": labels.get(subcat_type, subcat_type)})
        return subcat_id
    
    def add_supply_relation(self, supplier, customer):
        """공급망 관계 추가 (A -> SUPPLIES_TO -> B)"""
        self.graph.query("""
            MERGE (s:Company {name: $s}) 
            MERGE (c:Company {name: $c}) 
            MERGE (s)-[:SUPPLIES_TO]->(c)
        """, {"s": supplier, "c": customer})

    def update_entity_risk(self, entity_type, name, score, factors):
        """엔티티 리스크 점수 및 요인 업데이트"""
        if entity_type == "company":
            self.graph.query("""
                MATCH (c:Company {name: $name})
                SET c.total_score = $score, c.top_factors = $factors, c.analyzed_at = datetime()
                WITH c
                MATCH (r:RiskLevel)
                WHERE (c.total_score <= 30 AND r.level='GREEN') OR 
                      (c.total_score > 30 AND c.total_score <= 60 AND r.level='YELLOW') OR 
                      (c.total_score > 60 AND r.level='RED')
                MERGE (r)-[:HAS_STATUS]->(c)
            """, {"name": name, "score": score, "factors": factors})


    def add_patent_subcategory(self, parent_cat_id):
        subcat_id = f"{parent_cat_id}_특허내역"
        self.graph.query("MATCH (cat:Category {id: $parent}) MERGE (sub:NewsCategory {id: $id}) SET sub.type = '특허', sub.label = '📜 특허내역' MERGE (cat)-[:HAS_SUBCATEGORY]->(sub)",
                        {"parent": parent_cat_id, "id": subcat_id})
        return subcat_id

    def add_review_subcategory(self, parent_cat_id):
        subcat_id = f"{parent_cat_id}_리뷰내역"
        self.graph.query("MATCH (cat:Category {id: $parent}) MERGE (sub:NewsCategory {id: $id}) SET sub.type = '채용리뷰', sub.label = '🗣️ 리뷰내역' MERGE (cat)-[:HAS_SUBCATEGORY]->(sub)",
                        {"parent": parent_cat_id, "id": subcat_id})
        return subcat_id
    
    def add_to_category(self, cat_id, name, entity_type, ratio=None, position=None):
        if entity_type == "person":
            self.graph.query("MERGE (p:Person {name: $name}) WITH p MATCH (cat:Category {id: $cat_id}) MERGE (cat)-[r:CONTAINS]->(p) SET r.ratio = $ratio, r.position = $pos",
                           {"name": name, "cat_id": cat_id, "ratio": ratio, "pos": position})
        else:
            self.graph.query("MERGE (c:Company {name: $name}) WITH c MATCH (cat:Category {id: $cat_id}) MERGE (cat)-[r:CONTAINS]->(c) SET r.ratio = $ratio",
                           {"name": name, "cat_id": cat_id, "ratio": ratio})
    
    def add_disclosure(self, subcat_id, disc):
        self.graph.query("MERGE (d:Disclosure {code: $code}) SET d.title = $title, d.date = $date, d.submitter = $submitter, d.risk_score = $risk_score, d.keywords = $keywords, d.is_risk = $is_risk, d.category = $category WITH d MATCH (sub:DisclosureCategory {id: $subcat_id}) MERGE (sub)-[:CONTAINS]->(d)",
                        {"subcat_id": subcat_id, **disc})
        if disc.get('is_risk') and disc.get('risk_score') > 0:
             self.graph.query("MATCH (d:Disclosure {code: $code}), (c:Company {name: $name}) MERGE (d)-[:ABOUT]->(c)", 
                            {"code": disc['code'], "name": disc['submitter']})
        for person in disc.get("persons", []):
            self.add_person(person)
            self.graph.query("MATCH (d:Disclosure {code: $code}), (p:Person {name: $person}) MERGE (d)-[:INVOLVES]->(p)", {"code": disc["code"], "person": person})
    
    def add_news_to_subcategory(self, subcat_id, article, source_entity, source_type):
        params = {
            "subcat_id": subcat_id, 
            "searched_for": source_entity, 
            "source_type": source_type,
            "url": article.get("url"),
            "title": article.get("title", ""),
            "date": article.get("date", ""),
            "source": article.get("source", "Unknown"),
            "keywords": article.get("keywords", []),
            "risk_score": article.get("risk_score", 0),
            "raw_score": article.get("raw_score", article.get("risk_score", 0)),
            "days_old": article.get("days_old", 0),
            "decay_rate": article.get("decay_rate", 1.0),
            "is_risk": article.get("is_risk", False),
            "sentiment": article.get("sentiment", "중립")
        }
        
        self.graph.query("MERGE (n:NewsArticle {url: $url}) SET n.title = $title, n.date = $date, n.source = $source, n.keywords = $keywords, n.risk_score = $risk_score, n.raw_score = $raw_score, n.days_old = $days_old, n.decay_rate = $decay_rate, n.is_risk = $is_risk, n.sentiment = $sentiment, n.searched_for = $searched_for, n.source_type = $source_type WITH n MATCH (sub:NewsCategory {id: $subcat_id}) MERGE (sub)-[:CONTAINS]->(n)", params)
        
        confidence = article.get("confidence", 0.5)
        matched_by = "keyword" if article.get("keywords") else "search_query"
        
        if source_type == "기업":
            self.graph.query("MATCH (n:NewsArticle {url: $url}), (c:Company {name: $name}) MERGE (n)-[r:ABOUT]->(c) SET r.keywords = $kw, r.is_risk = $is_risk, r.source_type = '기업', r.confidence = $conf, r.matched_by = $matched, r.created_at = datetime()",
                           {"url": article["url"], "name": source_entity, "kw": article.get("keywords", []), "is_risk": article.get("is_risk", False), "conf": confidence, "matched": matched_by})
        elif source_type in ["주주", "임원", "특허", "채용리뷰"]:
             self.graph.query("MATCH (n:NewsArticle {url: $url}) OPTIONAL MATCH (p:Person {name: $name}) OPTIONAL MATCH (c:Company {name: $name}) FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END | MERGE (n)-[r:ABOUT]->(p) SET r.keywords = $kw, r.is_risk = $is_risk) FOREACH (_ IN CASE WHEN c IS NOT NULL AND p IS NULL THEN [1] ELSE [] END | MERGE (n)-[r:ABOUT]->(c) SET r.keywords = $kw, r.is_risk = $is_risk)",
                            {"url": article["url"], "name": source_entity, "kw": article.get('keywords', []), "is_risk": article.get('is_risk', False)})

    def update_news_subcategory_stats(self, subcat_id, count, risk_score, duplicates=0):
        self.graph.query("MATCH (sub:NewsCategory {id: $id}) SET sub.count = $count, sub.risk_score = $risk, sub.duplicates = $dup", {"id": subcat_id, "count": count, "risk": risk_score, "dup": duplicates})
    def update_category_score(self, cat_id, score):
        self.graph.query("MATCH (cat:Category {id: $id}) SET cat.risk_score = $score", {"id": cat_id, "score": score})
    def update_entity_risk(self, entity_type, name, score, factors):
        """엔티티 리스크 점수 및 요인 업데이트 (Merged)"""
        if entity_type == "company":
            self.graph.query("""
                MATCH (c:Company {name: $name})
                SET c.total_score = $score, c.top_factors = $factors, c.analyzed_at = datetime()
                WITH c
                MATCH (r:RiskLevel)
                WHERE (c.total_score <= 30 AND r.level='GREEN') OR 
                      (c.total_score > 30 AND c.total_score <= 60 AND r.level='YELLOW') OR 
                      (c.total_score > 60 AND r.level='RED')
                MERGE (r)-[:HAS_STATUS]->(c)
            """, {"name": name, "score": score, "factors": factors})
        else:
            # Person 업데이트
            self.graph.query("MATCH (p:Person {name: $n}) SET p.risk_score = $s, p.keywords = $k", {"n": name, "s": score, "k": factors})
    
    def set_risk_status(self, company, score, coverage, propagated=0, top_factors=None, dedup_stats=None):
        level = "GREEN" if score <= 30 else "YELLOW" if score <= 60 else "RED"
        self.graph.query("MATCH (c:Company {name: $c})-[r:HAS_STATUS]-() DELETE r", {"c": company})
        self.graph.query("MATCH (c:Company {name: $c}), (r:RiskLevel {level: $l}) MERGE (r)-[:HAS_STATUS]->(c) SET c.total_score = $s, c.analyzed_at = datetime(), c.data_coverage = $cov, c.propagated_risk = $p, c.top_factors = $f, c.news_duplicates = $d",
                        {"c": company, "l": level, "s": score, "cov": coverage, "p": propagated, "f": top_factors or [], "d": dedup_stats or 0})
    
    def calc_propagated_risk(self, company):
        # v2.0 Upgrade: ratio(지분율) 함께 반환
        return self.graph.query("""
            MATCH (c:Company {name: $company})-[:HAS_CATEGORY]->(cat:Category)-[:CONTAINS]->(e) 
            WHERE cat.type IN ['주주', '임원'] 
            WITH DISTINCT e 
            MATCH (other:Company)-[:HAS_CATEGORY]->(oCat:Category)-[r:CONTAINS]->(e) 
            WHERE other.name <> $company AND other.total_score IS NOT NULL AND other.total_score > 30 
            RETURN DISTINCT other.name AS connected_company, other.total_score AS risk_score, e.name AS connector, labels(e)[0] AS connector_type, r.ratio AS ratio 
            ORDER BY other.total_score DESC
        """, {"company": company})
    
    # ===========================================================================
    # Propagation v3.0 - 다단계 전이 + 시간 감쇠 + 산업별 계수
    # ===========================================================================
    
    # 산업별 전이 계수
    INDUSTRY_COEFFICIENTS = {
        "금융": 0.4,      # 높은 상호의존성
        "금융업": 0.4,
        "은행": 0.4,
        "보험": 0.35,
        "증권": 0.35,
        "제조": 0.25,     # 중간 의존성
        "제조업": 0.25,
        "반도체": 0.3,    # 글로벌 공급망 영향
        "IT": 0.2,        # 낮은 의존성
        "서비스": 0.2,
        "유통": 0.25,
        "건설": 0.3,      # 프로젝트 파이낸싱 연관
        "부동산": 0.3,
    }
    DEFAULT_COEFFICIENT = 0.3
    
    def calc_propagated_risk_v3(self, company, depth=2, include_decay=True):
        """
        🚀 v3.0 리스크 전이: 다단계 + 시간 감쇠 + 산업별 계수
        
        Args:
            company: 대상 기업명
            depth: 전이 깊이 (1=1차, 2=2차, 3=3차)
            include_decay: 시간 감쇠 적용 여부
        
        Returns:
            {
                "first_degree": [...],   # 1차 연결
                "second_degree": [...],  # 2차 연결
                "total_propagated": int, # 총 전이 점수
                "coefficient": float,    # 적용된 계수
                "industry": str          # 산업 분류
            }
        """
        # 1. 1차 전이 (직접 연결)
        first_degree = self.graph.query("""
            MATCH (c:Company {name: $company})-[:HAS_CATEGORY]->(cat:Category)-[:CONTAINS]->(e) 
            WHERE cat.type IN ['주주', '임원'] 
            WITH DISTINCT e 
            MATCH (other:Company)-[:HAS_CATEGORY]->(oCat:Category)-[r:CONTAINS]->(e) 
            WHERE other.name <> $company AND other.total_score IS NOT NULL AND other.total_score > 30 
            RETURN DISTINCT other.name AS company, other.total_score AS risk_score, 
                   e.name AS connector, labels(e)[0] AS connector_type, 
                   r.ratio AS ratio, other.analyzed_at AS analyzed_at
            ORDER BY other.total_score DESC LIMIT 10
        """, {"company": company})
        
        # 2. 2차 전이 (depth >= 2)
        second_degree = []
        if depth >= 2 and first_degree:
            seen = {company} | {c['company'] for c in first_degree}
            for conn in first_degree[:5]:  # 상위 5개만 2차 탐색
                secondary = self.graph.query("""
                    MATCH (c:Company {name: $connected})-[:HAS_CATEGORY]->(cat:Category)-[:CONTAINS]->(e) 
                    WHERE cat.type IN ['주주', '임원'] 
                    WITH DISTINCT e 
                    MATCH (other:Company)-[:HAS_CATEGORY]->(oCat:Category)-[r:CONTAINS]->(e) 
                    WHERE other.name <> $connected AND other.name <> $original
                          AND other.total_score IS NOT NULL AND other.total_score > 40 
                    RETURN DISTINCT other.name AS company, other.total_score AS risk_score, 
                           e.name AS connector, 'via ' + $connected AS path
                    ORDER BY other.total_score DESC LIMIT 3
                """, {"connected": conn['company'], "original": company})
                for s in secondary:
                    if s['company'] not in seen:
                        seen.add(s['company'])
                        s['degree'] = 2
                        second_degree.append(s)
        
        # 3. 산업 분류 추출 및 계수 결정
        industry = self._detect_industry(company)
        coefficient = self.INDUSTRY_COEFFICIENTS.get(industry, self.DEFAULT_COEFFICIENT)
        
        # 4. 전이 점수 계산
        first_score = 0
        for c in first_degree:
            base = c['risk_score'] * coefficient
            # 시간 감쇠 (분석 시점 기준, 최대 50% 감쇠)
            if include_decay and c.get('analyzed_at'):
                first_score += base * 0.8  # 간소화: 20% 기본 감쇠
            else:
                first_score += base
        
        second_score = 0
        for c in second_degree:
            # 2차 전이는 계수 절반 적용
            second_score += c['risk_score'] * coefficient * 0.5
        
        total = min(round(first_score + second_score), 50)  # 최대 50점
        
        return {
            "first_degree": first_degree,
            "second_degree": second_degree,
            "total_propagated": total,
            "coefficient": coefficient,
            "industry": industry,
            "first_count": len(first_degree),
            "second_count": len(second_degree)
        }
    
    def calc_supply_chain_risk(self, company):
        """
        ⛓️ A3 Supply Chain Risk Analysis
        - 공급사 리스크: 생산 차질 (계수 0.5)
        - 고객사 리스크: 매출 감소 (계수 0.3)
        """
        # 1. 공급사 (Suppliers) -> Company
        suppliers = self.graph.query("""
            MATCH (s:Company)-[:SUPPLIES_TO]->(c:Company {name: $company})
            WHERE s.total_score IS NOT NULL AND s.total_score > 20
            RETURN s.name AS company, s.total_score AS risk_score, 'Supplier' AS type
            ORDER BY s.total_score DESC
        """, {"company": company})
        
        # 2. Company -> 고객사 (Customers)
        customers = self.graph.query("""
            MATCH (c:Company {name: $company})-[:SUPPLIES_TO]->(cu:Company)
            WHERE cu.total_score IS NOT NULL AND cu.total_score > 20
            RETURN cu.name AS company, cu.total_score AS risk_score, 'Customer' AS type
            ORDER BY cu.total_score DESC
        """, {"company": company})
        
        supply_risk = 0
        customer_risk = 0
        
        for s in suppliers:
            supply_risk += s['risk_score'] * 0.5  # 공급망 이슈는 치명적
            
        for c in customers:
            customer_risk += c['risk_score'] * 0.3  # 매출처 이슈
            
        total = min(round(supply_risk + customer_risk), 40) # 최대 40점
        
        return {
            "suppliers": suppliers,
            "customers": customers,
            "supply_risk": round(supply_risk),
            "customer_risk": round(customer_risk),
            "total_score": total
        }
    
    def _detect_industry(self, company):
        """기업명에서 산업 분류 추정"""
        if any(kw in company for kw in ['은행', '금융', '캐피탈', '카드', '저축']):
            return "금융"
        if any(kw in company for kw in ['보험', '생명', '화재']):
            return "보험"
        if any(kw in company for kw in ['증권', '투자', '자산']):
            return "증권"
        if any(kw in company for kw in ['반도체', '하이닉스', '삼성전자', 'SK', '마이크론']):
            return "반도체"
        if any(kw in company for kw in ['건설', '건축', 'E&C', '엔지니어링']):
            return "건설"
        if any(kw in company for kw in ['유통', '마트', '백화점', '쇼핑']):
            return "유통"
        return "기타"
    
    def get_stats(self):
        nodes = self.graph.query("MATCH (n) RETURN labels(n)[0] AS l, count(*) AS c")
        rels = self.graph.query("MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c")
        return {"nodes": nodes, "rels": rels}


# ==============================================================================
# 리스크 엔진
# ==============================================================================

class RiskEngine:
    # 🏆 v13.0 가중치: 14개 카테고리
    BASE_WEIGHTS = {
        # 기존 8개
        "공시": 0.15, "뉴스": 0.12, "주주": 0.10, "임원": 0.05, 
        "특허": 0.03, "채용리뷰": 0.05, "소송": 0.10, "신용등급": 0.08,
        # 신규 6개
        "금감원": 0.10, "ESG": 0.07, "SNS": 0.05, 
        "부동산": 0.04, "상표": 0.03, "경쟁사": 0.03
    }
    
    def __init__(self, dart, graph, news, patent_scanner, review_scanner, 
                 legal_scanner=None, credit_scanner=None, 
                 naver_scanner=None, kind_scanner=None,
                 fss_scanner=None, esg_scanner=None, social_scanner=None,
                 realestate_scanner=None, trademark_scanner=None, competitor_scanner=None,
                 daum_scanner=None, court_scanner=None, blind_scanner=None, rating_agency_scanner=None): 
        self.dart, self.graph, self.news = dart, graph, news
        self.patent_scanner = patent_scanner
        self.review_scanner = review_scanner
        self.legal_scanner = legal_scanner
        self.credit_scanner = credit_scanner
        # 멀티채널 스캐너 (C1-C5, C7, C10)
        self.naver_scanner = naver_scanner
        self.kind_scanner = kind_scanner
        self.daum_scanner = daum_scanner
        self.court_scanner = court_scanner
        self.blind_scanner = blind_scanner
        self.rating_agency_scanner = rating_agency_scanner
        # 확장 카테고리 스캐너 (B2, B4-B8)
        self.fss_scanner = fss_scanner
        self.esg_scanner = esg_scanner
        self.social_scanner = social_scanner
        self.realestate_scanner = realestate_scanner
        self.trademark_scanner = trademark_scanner
        self.competitor_scanner = competitor_scanner
    
    def scan_entity_news(self, name, news_subcat_id, source_type):
        articles, duplicates = self.news.scan(name, limit=10)
        total_score, all_kw = 0, []
        for a in articles:
            self.graph.add_news_to_subcategory(news_subcat_id, a, name, source_type)
            if a["is_risk"]: 
                total_score += a["risk_score"]; all_kw.extend(a["keywords"])
        return len(articles), min(total_score, 100), all_kw, duplicates

    def calc_adjusted_weights(self, coverage):
        available = {cat: w for cat, w in self.BASE_WEIGHTS.items() if coverage.get(cat, False)}
        if not available: return self.BASE_WEIGHTS
        total = sum(available.values())
        return {cat: (self.BASE_WEIGHTS[cat] / total if coverage.get(cat, False) else 0) for cat in self.BASE_WEIGHTS}

    def calc_propagated_risk(self, company, direct_score):
        connections = self.graph.calc_propagated_risk(company)
        if not connections: return 0, []
        propagated, risk_sources = 0, []
        
        seen_connectors = set()
        
        for conn in connections:
            # 중복 커넥터 방지
            if conn['connector'] in seen_connectors: continue
            seen_connectors.add(conn['connector'])
            
            # v2.0 Dynamic Decay Logic
            base_score = conn['risk_score']
            ratio = conn.get('ratio')
            conn_type = conn.get('connector_type')
            
            decay_factor = 0.1 # 기본값
            
            if ratio:
                # 지분율이 있는 경우: 지분율의 50% 반영 (예: 50% 지분 -> 0.25 전이)
                try:
                    r_val = float(str(ratio).replace('%', ''))
                    decay_factor = min(r_val / 200, 0.5) # 최대 50% 전이
                except:
                    decay_factor = 0.2
            else:
                # 지분율 없는 경우 유형별 차등
                if conn_type == 'Company': # 관계사/모회사
                    decay_factor = 0.3 # 30% 전이
                elif conn_type == 'Person': # 인적 공유
                    decay_factor = 0.15 # 15% 전이 (임원 리스크는 상대적으로 낮게)
            
            transmitted = round(base_score * decay_factor)
            propagated += transmitted
            
            risk_sources.append({
                "company": conn['connected_company'], 
                "score": base_score, 
                "transmitted": transmitted, 
                "via": conn['connector'], 
                "type": conn_type,
                "factor": f"{int(decay_factor*100)}%"
            })
            
        return min(propagated, 40), risk_sources # 최대 전이 리스크 40점으로 상향 (v2.0)

    def extract_keyword_scores(self, keywords):
        result = []
        for kw in keywords:
            m = re.match(r'(.+)\((\d+)\)', kw)
            if m: result.append((m.group(1), int(m.group(2))))
        return result

    def collect_top_factors(self, all_keywords, risk_sources, n=5):
        kw_scores = {}
        for kw_list in all_keywords.values():
            for kw, score in self.extract_keyword_scores(kw_list): kw_scores[kw] = kw_scores.get(kw, 0) + score
        for src in risk_sources: kw_scores[f"전이:{src['company'][:6]}"] = kw_scores.get(f"전이:{src['company'][:6]}", 0) + src['transmitted']
        return [f"{kw}({score})" for kw, score in sorted(kw_scores.items(), key=lambda x: x[1], reverse=True)[:n]]

    def diagnose(self, company):
        print(f"\n{'='*60}\n📊 {company} 리스크 분석 (v10.0)\n{'='*60}")
        self.news.reset_session()
        code = self.dart.get_code(company)
        if not code: print(f"⚠️ 기업 코드 없음: {company}"); return None
        info = self.dart.get_info(code)
        corp_name = info.get("corp_name", company)
        self.graph.add_company(corp_name, code)
        
        scores = {k: 0 for k in self.BASE_WEIGHTS}
        coverage = {k: False for k in self.BASE_WEIGHTS}
        all_keywords = {k: [] for k in self.BASE_WEIGHTS}
        total_duplicates = 0
        
        # [1/6] 공시
        print(f"\n[1/6] 📄 공시...")
        disc_cat_id = self.graph.add_category(corp_name, "공시")
        categorized = self.dart.get_disclosures(code, corp_name)
        total_disc_risk, disc_count = 0, 0
        for cat_type, discs in categorized.items():
            if not discs: continue
            disc_count += len(discs)
            cat_risk = sum(d["risk_score"] for d in discs)
            total_disc_risk += cat_risk
            subcat_id = self.graph.add_disclosure_subcategory(disc_cat_id, cat_type, len(discs), cat_risk)
            for d in discs[:15]: 
                 self.graph.add_disclosure(subcat_id, d); all_keywords["공시"].extend(d.get("keywords", []))
            print(f"   [{cat_type}] {len(discs)}건, 리스크 {sum(1 for d in discs if d['is_risk'])}건 ({cat_risk}점)")
        scores["공시"] = min(total_disc_risk, 100); coverage["공시"] = disc_count > 0
        self.graph.update_category_score(disc_cat_id, scores["공시"])
        
        # [2/8] 뉴스 (멀티채널: 구글뉴스 + 네이버뉴스 + KIND)
        print(f"\n[2/8] 📰 뉴스 (멀티채널)...")
        news_cat_id = self.graph.add_category(corp_name, "뉴스")
        corp_news_subcat = self.graph.add_news_subcategory(news_cat_id, "기업")
        sh_news_subcat = self.graph.add_news_subcategory(news_cat_id, "주주")
        ex_news_subcat = self.graph.add_news_subcategory(news_cat_id, "임원")
        
        # 구글뉴스 스캔
        count, corp_risk, corp_kw, dup = self.scan_entity_news(corp_name, corp_news_subcat, "기업")
        total_duplicates += dup; all_keywords["뉴스"].extend(corp_kw)
        self.graph.update_news_subcategory_stats(corp_news_subcat, count, corp_risk, dup)
        print(f"   [구글뉴스] {count}건, {corp_risk}점")
        
        # 네이버뉴스 스캔 (C1)
        naver_risk = 0
        if self.naver_scanner:
            self.naver_scanner.reset_session()
            naver_articles, naver_dup = self.naver_scanner.scan(corp_name, limit=10)
            total_duplicates += naver_dup
            for a in naver_articles:
                self.graph.add_news_to_subcategory(corp_news_subcat, a, corp_name, "네이버")
                if a["is_risk"]: 
                    naver_risk += a["risk_score"]
                    all_keywords["뉴스"].extend(a["keywords"])
            print(f"   [C1 네이버] {len(naver_articles)}건, {min(naver_risk, 100)}점")
        
        # 다음뉴스 스캔 (C2)
        daum_risk = 0
        if self.daum_scanner:
            self.daum_scanner.reset_session()
            daum_articles, daum_dup = self.daum_scanner.scan(corp_name, limit=10)
            total_duplicates += daum_dup
            for a in daum_articles:
                self.graph.add_news_to_subcategory(corp_news_subcat, a, corp_name, "다음")
                if a["is_risk"]: 
                    daum_risk += a["risk_score"]
                    all_keywords["뉴스"].extend(a["keywords"])
            print(f"   [C2 다음] {len(daum_articles)}건, {min(daum_risk, 100)}점")
        
        # KIND 공시 스캔 (C3)
        kind_risk = 0
        if self.kind_scanner:
            self.kind_scanner.reset_session()
            kind_articles, kind_dup = self.kind_scanner.scan(corp_name, limit=10)
            total_duplicates += kind_dup
            for a in kind_articles:
                self.graph.add_news_to_subcategory(corp_news_subcat, a, corp_name, "KIND")
                if a["is_risk"]: 
                    kind_risk += a["risk_score"]
                    all_keywords["뉴스"].extend(a["keywords"])
            print(f"   [C3 KIND] {len(kind_articles)}건, {min(kind_risk, 100)}점")
        
        # 대법원 판례 스캔 (C5)
        court_risk = 0
        if self.court_scanner:
            self.court_scanner.reset_session()
            court_articles, court_dup = self.court_scanner.scan(corp_name, limit=10)
            total_duplicates += court_dup
            for a in court_articles:
                self.graph.add_news_to_subcategory(corp_news_subcat, a, corp_name, "대법원")
                if a["is_risk"]: 
                    court_risk += a["risk_score"]
                    all_keywords["뉴스"].extend(a["keywords"])
            print(f"   [C5 대법원] {len(court_articles)}건, {min(court_risk, 100)}점")
        # 신용평가사 직접 발표 스캔 (C10)
        rating_risk = 0
        if self.rating_agency_scanner:
            self.rating_agency_scanner.reset_session()
            rating_articles, rating_dup = self.rating_agency_scanner.scan(corp_name, limit=10)
            total_duplicates += rating_dup
            for a in rating_articles:
                self.graph.add_news_to_subcategory(corp_news_subcat, a, corp_name, "신용평가사")
                if a["is_risk"]: 
                    rating_risk += a["risk_score"]
                    all_keywords["뉴스"].extend(a["keywords"])
            print(f"   [C10 신용평가사] {len(rating_articles)}건, {min(rating_risk, 100)}점")
        
        # 6채널 통합 뉴스 점수 (최대 100점) - C7 블라인드는 SocialScanner(B5)로 통합됨
        channel_risks = [
            corp_risk,  # 구글뉴스
            min(naver_risk, 30),   # C1
            min(daum_risk, 30),    # C2
            min(kind_risk, 30),    # C3
            min(court_risk, 30),   # C5
            min(rating_risk, 30)   # C10
        ]
        total_news_risk = min(sum(channel_risks), 100)
        scores["뉴스"] = total_news_risk
        coverage["뉴스"] = count > 0 or any([naver_risk, daum_risk, kind_risk, court_risk, rating_risk])
        
        # [3/6] 주주
        print(f"\n[3/6] 📊 주주...")
        sh_cat = self.graph.add_category(corp_name, "주주")
        seen, sh_risks, sh_news_count, sh_dup = set(), [], 0, 0
        for sh in self.dart.get_shareholders(code):
            name = self.graph.clean(sh.get("nm", ""))
            if not name or name in ["-", "계", "합계"] or name in seen: continue
            seen.add(name); ratio = sh.get("trmend_posesn_stock_qota_rt", ""); is_corp = self.graph.is_corp(name)
            self.graph.add_to_category(sh_cat, name, "company" if is_corp else "person", ratio)
            cnt, risk, kw, dup = self.scan_entity_news(name, sh_news_subcat, "주주")
            sh_dup += dup; all_keywords["주주"].extend(kw)
            self.graph.update_entity_risk("company" if is_corp else "person", name, risk, kw)
            print(f"   {'🏢' if is_corp else '👤'} {name[:10]} → {risk}점")
            sh_risks.append(risk); sh_news_count += cnt
        total_duplicates += sh_dup
        scores["주주"] = sum(sh_risks) / len(sh_risks) if sh_risks else 0; coverage["주주"] = len(seen) > 0
        self.graph.update_category_score(sh_cat, round(scores["주주"]))
        self.graph.update_news_subcategory_stats(sh_news_subcat, sh_news_count, round(scores["주주"]), sh_dup)
        
        # [4/6] 임원
        print(f"\n[4/6] 👔 임원...")
        ex_cat = self.graph.add_category(corp_name, "임원")
        seen, ex_risks, ex_news_count, ex_dup = set(), [], 0, 0
        for ex in self.dart.get_executives(code)[:10]:
            name = self.graph.clean(ex.get("repror", ""))
            if not name or name == "-" or name in seen: continue
            seen.add(name); position = ex.get("isu_exctv_ofcps", "")
            self.graph.add_to_category(ex_cat, name, "person", position=position)
            cnt, risk, kw, dup = self.scan_entity_news(name, ex_news_subcat, "임원")
            ex_dup += dup; all_keywords["임원"].extend(kw)
            self.graph.update_entity_risk("person", name, risk, kw)
            print(f"   👔 {name} ({position}) → {risk}점")
            ex_risks.append(risk); ex_news_count += cnt
        total_duplicates += ex_dup
        scores["임원"] = sum(ex_risks) / len(ex_risks) if ex_risks else 0; coverage["임원"] = len(seen) > 0
        self.graph.update_category_score(ex_cat, round(scores["임원"]))
        self.graph.update_news_subcategory_stats(ex_news_subcat, ex_news_count, round(scores["임원"]), ex_dup)
        self.graph.update_category_score(news_cat_id, scores["뉴스"])

        # [5/6] 특허
        print(f"\n[5/6] 📜 특허/IP...")
        pat_cat_id = self.graph.add_category(corp_name, "특허")
        pat_subcat_id = self.graph.add_patent_subcategory(pat_cat_id)
        self.patent_scanner.reset_session()
        pats, _ = self.patent_scanner.scan(corp_name)
        pat_risk = min(sum(r['risk_score'] for r in pats if r['is_risk']), 100)
        for p in pats:
             self.graph.add_news_to_subcategory(pat_subcat_id, p, corp_name, "특허")
             if p['is_risk']: all_keywords['특허'].extend(p['keywords'])
        print(f"   {len(pats)}건, {pat_risk}점")
        scores["특허"] = pat_risk; coverage["특허"] = len(pats) > 0
        self.graph.update_category_score(pat_cat_id, pat_risk)

        # [6/6] 채용리뷰
        print(f"\n[6/6] 👥 채용/리뷰...")
        rev_cat_id = self.graph.add_category(corp_name, "채용리뷰")
        rev_subcat_id = self.graph.add_review_subcategory(rev_cat_id)
        self.review_scanner.reset_session()
        revs, _ = self.review_scanner.scan(corp_name)
        rev_risk = min(sum(r['risk_score'] for r in revs if r['is_risk']), 100)
        for r in revs:
             self.graph.add_news_to_subcategory(rev_subcat_id, r, corp_name, "채용리뷰")
             if r['is_risk']: all_keywords['채용리뷰'].extend(r['keywords'])
        print(f"   {len(revs)}건, {rev_risk}점")
        scores["채용리뷰"] = rev_risk; coverage["채용리뷰"] = len(revs) > 0
        self.graph.update_category_score(rev_cat_id, rev_risk)
        
        # [7/8] 소송/판결 (NEW - Day 1)
        print(f"\n[7/8] ⚖️ 소송/판결...")
        if self.legal_scanner:
            legal_cat_id = self.graph.add_category(corp_name, "소송")
            legal_subcat_id = self.graph.add_patent_subcategory(legal_cat_id)  # Reuse subcategory structure
            self.legal_scanner.reset_session()
            legals, _ = self.legal_scanner.scan(corp_name)
            legal_risk = min(sum(l['risk_score'] for l in legals if l['is_risk']), 100)
            for l in legals:
                self.graph.add_news_to_subcategory(legal_subcat_id, l, corp_name, "소송")
                if l['is_risk']: all_keywords['소송'].extend(l['keywords'])
            print(f"   {len(legals)}건, {legal_risk}점")
            scores["소송"] = legal_risk; coverage["소송"] = len(legals) > 0
            self.graph.update_category_score(legal_cat_id, legal_risk)
        else:
            print(f"   (스캐너 미설정)")
            scores["소송"] = 0; coverage["소송"] = False
        
        # [8/8] 신용등급 (NEW - Day 1)
        print(f"\n[8/8] 📉 신용등급...")
        if self.credit_scanner:
            credit_cat_id = self.graph.add_category(corp_name, "신용등급")
            credit_subcat_id = self.graph.add_patent_subcategory(credit_cat_id)  # Reuse subcategory structure
            self.credit_scanner.reset_session()
            credits, _ = self.credit_scanner.scan(corp_name)
            credit_risk = min(sum(c['risk_score'] for c in credits if c['is_risk']), 100)
            for c in credits:
                self.graph.add_news_to_subcategory(credit_subcat_id, c, corp_name, "신용등급")
                if c['is_risk']: all_keywords['신용등급'].extend(c['keywords'])
            print(f"   {len(credits)}건, {credit_risk}점")
            scores["신용등급"] = credit_risk; coverage["신용등급"] = len(credits) > 0
            self.graph.update_category_score(credit_cat_id, credit_risk)
        else:
            print(f"   (스캐너 미설정)")
            scores["신용등급"] = 0; coverage["신용등급"] = False
        
        # [9/14] 금감원 제재 (B2)
        print(f"\n[9/14] 🏛️ 금감원 제재...")
        if self.fss_scanner:
            self.fss_scanner.reset_session()
            fss_articles, _ = self.fss_scanner.scan(corp_name)
            fss_risk = min(sum(a['risk_score'] for a in fss_articles if a['is_risk']), 100)
            print(f"   {len(fss_articles)}건, {fss_risk}점")
            scores["금감원"] = fss_risk; coverage["금감원"] = len(fss_articles) > 0
        else:
            scores["금감원"] = 0; coverage["금감원"] = False
        
        # [10/14] ESG (B4)
        print(f"\n[10/14] 🌿 ESG 리스크...")
        if self.esg_scanner:
            self.esg_scanner.reset_session()
            esg_articles, _ = self.esg_scanner.scan(corp_name)
            esg_risk = min(sum(a['risk_score'] for a in esg_articles if a['is_risk']), 100)
            print(f"   {len(esg_articles)}건, {esg_risk}점")
            scores["ESG"] = esg_risk; coverage["ESG"] = len(esg_articles) > 0
        else:
            scores["ESG"] = 0; coverage["ESG"] = False
        
        # [11/14] SNS/커뮤니티 (B5)
        print(f"\n[11/14] 💬 SNS/커뮤니티...")
        if self.social_scanner:
            self.social_scanner.reset_session()
            social_articles, _ = self.social_scanner.scan(corp_name)
            social_risk = min(sum(a['risk_score'] for a in social_articles if a['is_risk']), 100)
            print(f"   {len(social_articles)}건, {social_risk}점")
            scores["SNS"] = social_risk; coverage["SNS"] = len(social_articles) > 0
        else:
            scores["SNS"] = 0; coverage["SNS"] = False
        
        # [12/14] 부동산 등기 (B6)
        print(f"\n[12/14] 🏢 부동산 등기...")
        if self.realestate_scanner:
            self.realestate_scanner.reset_session()
            re_articles, _ = self.realestate_scanner.scan(corp_name)
            re_risk = min(sum(a['risk_score'] for a in re_articles if a['is_risk']), 100)
            print(f"   {len(re_articles)}건, {re_risk}점")
            scores["부동산"] = re_risk; coverage["부동산"] = len(re_articles) > 0
        else:
            scores["부동산"] = 0; coverage["부동산"] = False
        
        # [13/14] 상표/디자인 (B7)
        print(f"\n[13/14] 🏷️ 상표/디자인...")
        if self.trademark_scanner:
            self.trademark_scanner.reset_session()
            tm_articles, _ = self.trademark_scanner.scan(corp_name)
            tm_risk = min(sum(a['risk_score'] for a in tm_articles if a['is_risk']), 100)
            print(f"   {len(tm_articles)}건, {tm_risk}점")
            scores["상표"] = tm_risk; coverage["상표"] = len(tm_articles) > 0
        else:
            scores["상표"] = 0; coverage["상표"] = False
        
        # [14/14] 경쟁사 동향 (B8)
        print(f"\n[14/14] 🏭 경쟁사 동향...")
        if self.competitor_scanner:
            self.competitor_scanner.reset_session()
            comp_articles, _ = self.competitor_scanner.scan(corp_name)
            comp_risk = min(sum(a['risk_score'] for a in comp_articles if a['is_risk']), 100)
            print(f"   {len(comp_articles)}건, {comp_risk}점")
            scores["경쟁사"] = comp_risk; coverage["경쟁사"] = len(comp_articles) > 0
        else:
            scores["경쟁사"] = 0; coverage["경쟁사"] = False
        
        # Final Calculation
        adjusted_weights = self.calc_adjusted_weights(coverage)
        direct_score = sum(scores[cat] * adjusted_weights[cat] for cat in scores)
        propagated, risk_sources = self.calc_propagated_risk(corp_name, direct_score)
        total = round(direct_score + propagated)
        top_factors = self.collect_top_factors(all_keywords, risk_sources)
        signal = "🟢 정상" if total <= 30 else "🟡 주의" if total <= 60 else "🔴 위험"
        num_categories = len(self.BASE_WEIGHTS)  # Dynamic count
        coverage_pct = sum(1 for v in coverage.values() if v) / num_categories * 100
        
        self.graph.set_risk_status(corp_name, total, f"{int(coverage_pct)}%", propagated, top_factors, total_duplicates)
        
        return {"company": corp_name, "signal": signal, "score": total, "direct_score": round(direct_score), "propagated": propagated,
                "risk_sources": risk_sources, "top_factors": top_factors, "duplicates_removed": total_duplicates,
                "breakdown": scores, "coverage": coverage, "adjusted_weights": adjusted_weights, "graph": self.graph.get_stats()}


# ==============================================================================
# 고도화 기능 (AlertGenerator, TimelineGenerator, RiskLeaderboard)
# ==============================================================================

class AlertGenerator:
    """GlobalAlert 생성기 - 뉴스/공시 기반 실시간 알림"""
    SEVERITY_THRESHOLDS = {'high': 60, 'medium': 30, 'low': 0}
    
    def __init__(self, graph_builder):
        self.graph = graph_builder
    
    def generate_alerts(self, company: str, limit: int = 10) -> List[Dict]:
        alerts = []
        news_query = """
        MATCH (c:Company {name: $company})<-[:ABOUT]-(n:NewsArticle)
        WHERE n.is_risk = true
        RETURN n.title AS content, n.date AS time, n.risk_score AS score, n.source_type AS type, n.url AS url
        ORDER BY n.date DESC LIMIT $limit
        """
        news_results = self.graph.graph.query(news_query, {"company": company, "limit": limit})
        
        for item in news_results:
            severity = 'high' if item.get('score', 0) >= 60 else 'medium' if item.get('score', 0) >= 30 else 'low'
            alerts.append({
                "id": str(uuid.uuid4()), "dealId": company, "dealName": company,
                "type": 'news' if item.get('type') == '기업' else 'legal',
                "content": item.get('content', ''), "time": item.get('time', ''), "severity": severity
            })
        return alerts[:limit]
    
    def generate_global_signals(self, limit: int = 10) -> List[Dict]:
        """🏆 전체 포트폴리오의 실시간 리스크 신호 집계 (기업별 1건씩만)"""
        # 법적 위기 키워드
        LEGAL_KEYWORDS = ['횡령', '배임', '검찰', '수사', '기소', '구속', '압수수색', '고발', '소송', '벌금', '범죄', '형사']
        # 시장 위기 키워드  
        MARKET_KEYWORDS = ['부도', '파산', '채무불이행', '신용등급', '하락', '매각', '구조조정', '유동성', '자금난', '디폴트']
        
        # 기업별 가장 심각한 시그널만 조회 (서브쿼리 사용)
        query = """
        MATCH (c:Company)<-[:ABOUT]-(n:NewsArticle)
        WHERE n.is_risk = true AND n.risk_score IS NOT NULL
        WITH c, n ORDER BY n.risk_score DESC, n.date DESC
        WITH c, COLLECT(n)[0] AS top_news
        RETURN c.name AS company, c.total_score AS company_score,
               top_news.title AS content, top_news.date AS time, 
               top_news.risk_score AS score, top_news.source_type AS source_type
        ORDER BY top_news.risk_score DESC
        LIMIT $limit
        """
        results = self.graph.graph.query(query, {"limit": limit})
        
        signals = []
        for item in results:
            content = item.get('content', '')
            if not content:
                continue
            
            # 시그널 타입 자동 분류
            if any(kw in content for kw in LEGAL_KEYWORDS):
                signal_type = 'LEGAL_CRISIS'
                badge_color = 'red'
            elif any(kw in content for kw in MARKET_KEYWORDS):
                signal_type = 'MARKET_CRISIS'
                badge_color = 'yellow'
            else:
                signal_type = 'OPERATIONAL'
                badge_color = 'blue'
            
            # 긴급도 표시
            score = item.get('score', 0)
            is_urgent = score >= 60
            
            signals.append({
                "id": str(uuid.uuid4()),
                "company": item.get('company', ''),
                "company_score": item.get('company_score', 0),
                "content": content,
                "time": item.get('time', ''),
                "score": score,
                "signal_type": signal_type,
                "badge_color": badge_color,
                "is_urgent": is_urgent,
                "source_type": item.get('source_type', '')
            })
        
        return signals


class TimelineGenerator:
    """🏆 Timeline 이벤트 생성기 - 3단계 선행 감지 로직 (AI 연동)"""
    
    def __init__(self, graph_builder):
        self.graph = graph_builder
        # AI 서비스 로드
        try:
            from ai_service import analyze_timeline_with_ai, AI_AVAILABLE
            self.use_ai = AI_AVAILABLE
            self.ai_classify = analyze_timeline_with_ai
        except ImportError:
            self.use_ai = False
            self.ai_classify = None
    
    def classify_stage_fallback(self, title: str) -> tuple:
        """키워드 기반 분류 (Fallback)"""
        STAGE_KEYWORDS = {
            'stage3': ['대주단', '채권단', '상환', '만기', 'EOD', '기한이익', '워크아웃', '채무'],
            'stage2': ['금융위', '금감원', '검찰', '수사', '조사', '제재', '과징금', '기소']
        }
        
        for kw in STAGE_KEYWORDS['stage3']:
            if kw in title:
                return (3, '대주단 확인', '🔴', "담당자 조치 필요")
        
        for kw in STAGE_KEYWORDS['stage2']:
            if kw in title:
                return (2, '금융위 통지', '🟡', "규제 리스크 발생")
        
        return (1, '뉴스 보도', '🔵', "선행 감지 완료")
    
    def generate_timeline(self, company: str) -> List[Dict]:
        """🏆 AI 기반 3단계 타임라인 생성"""
        events = []
        
        # 뉴스 기사 조회
        news_query = """
        MATCH (c:Company {name: $company})<-[:ABOUT]-(n:NewsArticle)
        WHERE n.is_risk = true
        RETURN n.title AS title, n.date AS date, n.risk_score AS score, 
               n.source_type AS source_type, n.url AS url
        ORDER BY n.date DESC
        LIMIT 10
        """
        news = self.graph.graph.query(news_query, {"company": company})
        
        # 공시 데이터 조회
        disclosure_query = """
        MATCH (c:Company {name: $company})<-[:ABOUT]-(d:Disclosure)
        RETURN d.title AS title, d.date AS date, d.report_type AS report_type
        ORDER BY d.date DESC
        LIMIT 5
        """
        try:
            disclosures = self.graph.graph.query(disclosure_query, {"company": company})
        except:
            disclosures = []
        
        # 🏆 AI 분류 시도
        news_list = list(news)
        if self.use_ai and self.ai_classify and news_list:
            try:
                ai_results = self.ai_classify([{"title": n.get('title', '')} for n in news_list[:5]])
                
                for i, item in enumerate(news_list[:5]):
                    title = item.get('title', '')
                    
                    if i < len(ai_results):
                        ai = ai_results[i]
                        stage_num = ai.get('stage', 1)
                        stage_label = ai.get('stage_label', '뉴스 보도')
                        icon = ai.get('icon', '🔵')
                        description = ai.get('description', '리스크 감지')
                    else:
                        stage_num, stage_label, icon, description = self.classify_stage_fallback(title)
                    
                    events.append({
                        "id": str(uuid.uuid4()),
                        "stage": stage_num,
                        "stage_label": stage_label + " (AI)" if i < len(ai_results) else stage_label,
                        "icon": icon,
                        "label": title[:40] + '...' if len(title) > 40 else title,
                        "date": item.get('date', ''),
                        "description": description,
                        "score": item.get('score', 0),
                        "source": "news"
                    })
                
                # 나머지 뉴스 (AI 미적용)
                for item in news_list[5:]:
                    title = item.get('title', '')
                    stage_num, stage_label, icon, description = self.classify_stage_fallback(title)
                    events.append({
                        "id": str(uuid.uuid4()),
                        "stage": stage_num,
                        "stage_label": stage_label,
                        "icon": icon,
                        "label": title[:40] + '...' if len(title) > 40 else title,
                        "date": item.get('date', ''),
                        "description": description,
                        "score": item.get('score', 0),
                        "source": "news"
                    })
            except Exception as e:
                # AI 실패 시 Fallback
                for item in news_list:
                    title = item.get('title', '')
                    stage_num, stage_label, icon, description = self.classify_stage_fallback(title)
                    events.append({
                        "id": str(uuid.uuid4()),
                        "stage": stage_num,
                        "stage_label": stage_label,
                        "icon": icon,
                        "label": title[:40] + '...' if len(title) > 40 else title,
                        "date": item.get('date', ''),
                        "description": description,
                        "score": item.get('score', 0),
                        "source": "news"
                    })
        else:
            # AI 미사용 시 Fallback
            for item in news_list:
                title = item.get('title', '')
                stage_num, stage_label, icon, description = self.classify_stage_fallback(title)
                events.append({
                    "id": str(uuid.uuid4()),
                    "stage": stage_num,
                    "stage_label": stage_label,
                    "icon": icon,
                    "label": title[:40] + '...' if len(title) > 40 else title,
                    "date": item.get('date', ''),
                    "description": description,
                    "score": item.get('score', 0),
                    "source": "news"
                })
        
        # 공시 이벤트 (Fallback 사용)
        for item in disclosures:
            title = item.get('title', '')
            report_type = item.get('report_type', '')
            
            if any(kw in title for kw in ['정정', '조치', '제재', '벌금']):
                stage_num, stage_label, icon = 2, '금융위 통지', '🟡'
            else:
                stage_num, stage_label, icon = 1, '뉴스 보도', '🔵'
            
            events.append({
                "id": str(uuid.uuid4()),
                "stage": stage_num,
                "stage_label": stage_label,
                "icon": icon,
                "label": title[:40] + '...' if len(title) > 40 else title,
                "date": item.get('date', ''),
                "description": f"DART {report_type}" if report_type else "DART 공시",
                "score": 0,
                "source": "disclosure"
            })
        
        # 날짜순 정렬 (최신순)
        events.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        return events[:10]


        events.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        return events[:10]


class RiskLeaderboard:
    """리스크 리더보드 - TOP N 위험 기업"""
    def __init__(self, graph_builder):
        self.graph = graph_builder
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        query = """
        MATCH (r:RiskLevel)-[:HAS_STATUS]->(c:Company)
        WHERE c.total_score IS NOT NULL
        RETURN c.name AS company, c.total_score AS score, r.level AS level, r.label AS status,
               c.top_factors AS factors, c.data_coverage AS coverage, c.analyzed_at AS analyzed_at
        ORDER BY c.total_score DESC LIMIT $limit
        """
        results = self.graph.graph.query(query, {"limit": limit})
        
        leaderboard = []
        for rank, item in enumerate(results, 1):
            score = item.get('score', 0)
            leaderboard.append({
                "rank": rank, "company": item.get('company'), "score": score,
                "level": item.get('level'), "status": item.get('status'),
                "icon": "🔥" if score >= 60 else "⚠️" if score >= 30 else "✅",
                "factors": item.get('factors', []), "coverage": item.get('coverage'),
                "analyzed_at": str(item.get('analyzed_at', ''))
            })
        return leaderboard


class InternalDataStub:
    """내부 시스템 연동 스텁 - Mock 데이터 반환"""
    
    def get_ltv_metrics(self, deal_id: str) -> Dict:
        # Mock Logic based on Company Name (Context-Aware)
        if "태영" in deal_id:
            return {"current": "98.5%", "prev": "85.2%", "trend": "up", "_mock": True}
        elif "LG" in deal_id:
            return {"current": "72.1%", "prev": "68.5%", "trend": "up", "_mock": True}
        return {"current": "65.2%", "prev": "63.8%", "trend": "down", "_mock": True}

    def get_ebitda_metrics(self, deal_id: str) -> Dict:
        if "태영" in deal_id:
            return {"value": "₩-1,200억", "yoy_change": "-210%", "_mock": True}
        return {"value": "₩2,450억", "yoy_change": "-12.3%", "_mock": True}
    
    def get_covenant_status(self, deal_id: str) -> Dict:
        return {"status": "정상", "breaches": 0, "next_review": "2026-03-31", "_mock": True}

    def get_5_stage_timeline(self, company_name: str) -> List[Dict]:
        """5-Stage Timeline Mock Data"""
        import uuid
        
        if "태영" in company_name:
            # Crisis Case (Stage 4 Active)
            return [
                {"id": str(uuid.uuid4()), "active": True, "date": "2025.12.10", "type": "rumor", "label": "워크아웃설 유포", "description": "건설업계 찌라시 확산"},
                {"id": str(uuid.uuid4()), "active": True, "date": "2025.12.28", "type": "news", "label": "주채권은행 소집", "description": "산업은행 긴급 회의"},
                {"id": str(uuid.uuid4()), "active": True, "date": "2026.01.11", "type": "disclosure", "label": "실사 개시", "description": "자산 부채 실사 시작"},
                {"id": str(uuid.uuid4()), "active": True, "date": "2026.01.28", "type": "action", "label": "대주단 협의회", "description": "워크아웃 개시 여부 투표 (진행 중)"},
                {"id": str(uuid.uuid4()), "active": False, "date": "-", "type": "prediction", "label": "MOU 체결", "description": "경영 정상화 계획 이행"}
            ]
        else:
            # Normal Case (Stage 2 Active)
            return [
                {"id": str(uuid.uuid4()), "active": True, "date": "2026.01.20", "type": "news", "label": "HBM 공급 확대", "description": "NVIDIA 추가 수주 보도"},
                {"id": str(uuid.uuid4()), "active": True, "date": "2026.01.28", "type": "disclosure", "label": "실적 발표", "description": "연간 영업이익 흑자 전환 (예상)"},
                {"id": str(uuid.uuid4()), "active": False, "date": "-", "type": "prediction", "label": "등급 상향 검토", "description": "신용평가사 정기 평정"},
                {"id": str(uuid.uuid4()), "active": False, "date": "-", "type": "prediction", "label": "투자 심의", "description": "용인 클러스터 CAPEX"},
                {"id": str(uuid.uuid4()), "active": False, "date": "-", "type": "prediction", "label": "모니터링", "description": "지속 관찰"}
            ]

    def get_graph_data(self, deal_id: str) -> Dict:
        """Mock Graph Data based on Company"""
        if "태영" in deal_id:
            # Crisis Graph (Affinity Case Mock)
            return {
                "nodes": [
                    {"id": "n1", 
                     "name": "Affinity Equity", 
                     "type": "Sponsor", 
                     "status": "FAIL", 
                     "position": {"x": 50, "y": 10}, 
                     "details": [{"label": "Status", "value": "Distressed"}], 
                     "insights": [{"title": "Sponsor Integrity Failure", "content": "CEO Embezzlement confirmed. 100% Risk Contagion to subsidiaries.", "impactScore": 95, "relatedCovenant": "Bad Boy Act", "actionRequired": "Immediate EOD"}],
                     "graphMetrics": {"centrality": 0.95, "degree": 12, "riskContagionScore": 99},
                     "financials": {"revenue": "N/A (Holding)", "operatingIncome": "-$50M", "debtRatio": "450%", "creditRating": "D (Default)"},
                     "cypherAnalysis": {
                         "shortestPathToRisk": "Direct Source (0 hops)",
                         "commonShareholders": ["Affinity Fund IV", "CEO Personal Holdings"],
                         "riskFactors": ["Criminal Investigation", "Asset Freeze", "Covenant Breach"]
                     }},
                    {"id": "n2", 
                     "name": "SEEK Limited", 
                     "type": "Investor", 
                     "status": "WARNING", 
                     "position": {"x": 85, "y": 10}, 
                     "details": [{"label": "Ownership", "value": "10%"}],
                     "graphMetrics": {"centrality": 0.3, "degree": 4, "riskContagionScore": 45},
                     "financials": {"revenue": "$800M", "operatingIncome": "$120M", "debtRatio": "150%", "creditRating": "BBB+"},
                     "cypherAnalysis": {
                         "shortestPathToRisk": "Connected to Affinity via JV (1 hop)",
                         "commonShareholders": ["National Pension Service"],
                         "riskFactors": ["Reputational Damage"]
                     }},
                    {"id": "n3", 
                     "name": "Career Opps Ltd.", 
                     "type": "HoldCo", 
                     "status": "FAIL", 
                     "position": {"x": 50, "y": 40}, 
                     "details": [{"label": "Debt", "value": "720M USD"}],
                     "insights": [{"title": "Liquidity Crunch", "content": "Unable to service debt due to parent company freeze.", "impactScore": 88, "relatedCovenant": "Cross Default", "actionRequired": "Account Freeze"}],
                     "graphMetrics": {"centrality": 0.8, "degree": 8, "riskContagionScore": 95},
                     "financials": {"revenue": "N/A (SPC)", "operatingIncome": "-$5M", "debtRatio": "Infinite", "creditRating": "CC"},
                     "cypherAnalysis": {
                         "shortestPathToRisk": "Directly controlled by Affinity (1 hop)",
                         "riskFactors": ["Cross-Default Triggered", "Cash Trap Activated"]
                     }},
                    {"id": "n4", 
                     "name": "JobKorea (OpCo)", 
                     "type": "OpCo", 
                     "status": "WARNING", 
                     "position": {"x": 50, "y": 70}, 
                     "details": [{"label": "MAU", "value": "3.5M"}],
                     "graphMetrics": {"centrality": 0.6, "degree": 15, "riskContagionScore": 60},
                     "financials": {"revenue": "$150M", "operatingIncome": "$45M", "debtRatio": "120%", "creditRating": "BB+"},
                     "cypherAnalysis": {
                         "shortestPathToRisk": "Owned by Career Opps (2 hops from Source)",
                         "riskFactors": ["Change of Control Trigger", "IPO Delayed"]
                     }},
                    {"id": "n5", 
                     "name": "AlbaMon", 
                     "type": "OpCo", 
                     "status": "WARNING", 
                     "position": {"x": 20, "y": 70}, 
                     "details": [{"label": "Growth", "value": "-5% YoY"}],
                     "graphMetrics": {"centrality": 0.4, "degree": 3, "riskContagionScore": 55},
                     "financials": {"revenue": "$40M", "operatingIncome": "$10M", "debtRatio": "100%", "creditRating": "BB"},
                     "cypherAnalysis": {
                         "shortestPathToRisk": "Sister company to JobKorea (2 hops)",
                         "riskFactors": ["Advertising Revenue Drop"]
                     }},
                    {"id": "n6", 
                     "name": "JobKorea Partners", 
                     "type": "Partner", 
                     "status": "PASS", 
                     "position": {"x": 50, "y": 95}, 
                     "details": [{"label": "Status", "value": "Active"}],
                     "graphMetrics": {"centrality": 0.1, "degree": 1, "riskContagionScore": 10},
                     "financials": {"revenue": "Unknown", "operatingIncome": "N/A", "debtRatio": "N/A", "creditRating": "NR"},
                     "cypherAnalysis": {
                         "shortestPathToRisk": "Service Vendor (3 hops)",
                         "riskFactors": ["Contract Termination Risk"]
                     }}
                ],
                "edges": [
                    {"from": "n1", "to": "n3", "label": "100% Risk Contagion", "isRiskPath": True},
                    {"from": "n2", "to": "n3", "label": "Joint Venture"},
                    {"from": "n3", "to": "n4", "label": "Debt Service Link", "isRiskPath": True},
                    {"from": "n3", "to": "n5", "label": "Ownership", "isRiskPath": True},
                    {"from": "n4", "to": "n6", "label": "Service Control"}
                ],
                "status_card": {
                    "title": "어피니티 크레딧 위기",
                    "description": "스폰서의 형사 리스크가 하위 SPC로 전이되었습니다. 대주단은 즉시 EOD(기한이익상실) 여부를 판단해야 합니다.",
                    "level": "CRITICAL"
                }
            }
        else:
            # Normal Graph (SK Hynix Mock)
            return {
                "nodes": [
                    {"id": "s1", 
                     "name": "SK Square", 
                     "type": "Sponsor", 
                     "status": "PASS", 
                     "position": {"x": 50, "y": 10}, 
                     "details": [{"label": "Role", "value": "Strategic Investor"}],
                     "graphMetrics": {"centrality": 0.85, "degree": 20, "riskContagionScore": 5},
                     "financials": {"revenue": "$4.5B", "operatingIncome": "$1.2B", "debtRatio": "45%", "creditRating": "AA+"},
                     "cypherAnalysis": {
                         "shortestPathToRisk": "Safe Distance",
                         "commonShareholders": ["SK Holdings", "NPS"],
                         "riskFactors": ["None Detected"]
                     }},
                    {"id": "h1", 
                     "name": "SK Hynix", 
                     "type": "OpCo", 
                     "status": "PASS", 
                     "position": {"x": 50, "y": 45}, 
                     "details": [{"label": "Market Cap", "value": "$100B+"}],
                     "graphMetrics": {"centrality": 0.98, "degree": 50, "riskContagionScore": 2},
                     "financials": {"revenue": "$30B", "operatingIncome": "$8B", "debtRatio": "35%", "creditRating": "AAA"},
                     "cypherAnalysis": {
                         "shortestPathToRisk": "Safe",
                         "riskFactors": ["Geopolitical Supply Chain (Low)"]
                     }},
                    {"id": "v1", 
                     "name": "NVIDIA", 
                     "type": "Client", 
                     "status": "PASS", 
                     "position": {"x": 85, "y": 45}, 
                     "details": [{"label": "Share", "value": "15%"}],
                     "graphMetrics": {"centrality": 0.99, "degree": 100, "riskContagionScore": 0},
                     "financials": {"revenue": "$60B", "operatingIncome": "$30B", "debtRatio": "10%", "creditRating": "AAA (Global)"},
                     "cypherAnalysis": {
                         "shortestPathToRisk": "N/A",
                         "riskFactors": ["AI Chip Demand Surge (Opportunity)"]
                     }},
                    {"id": "v2", 
                     "name": "Apple", 
                     "type": "Client", 
                     "status": "PASS", 
                     "position": {"x": 15, "y": 45}, 
                     "details": [{"label": "Product", "value": "NAND"}],
                     "graphMetrics": {"centrality": 0.95, "degree": 80, "riskContagionScore": 0},
                     "financials": {"revenue": "$380B", "operatingIncome": "$110B", "debtRatio": "20%", "creditRating": "AAA"},
                     "cypherAnalysis": {
                         "shortestPathToRisk": "N/A",
                         "riskFactors": []
                     }},
                    {"id": "s2", 
                     "name": "Hana Micron", 
                     "type": "Partner", 
                     "status": "PASS", 
                     "position": {"x": 35, "y": 80}, 
                     "details": [{"label": "Focus", "value": "Back-end Testing"}],
                     "graphMetrics": {"centrality": 0.4, "degree": 5, "riskContagionScore": 1},
                     "financials": {"revenue": "$800M", "operatingIncome": "$50M", "debtRatio": "180%", "creditRating": "BBB"},
                     "cypherAnalysis": {
                         "shortestPathToRisk": "Safe",
                         "riskFactors": ["Vendor Dependency"]
                     }},
                     {"id": "s3", 
                     "name": "TSMC", 
                     "type": "Partner", 
                     "status": "PASS", 
                     "position": {"x": 65, "y": 80}, 
                     "details": [{"label": "Focus", "value": "Advanced Packaging"}],
                     "graphMetrics": {"centrality": 0.99, "degree": 200, "riskContagionScore": 0},
                     "financials": {"revenue": "$70B", "operatingIncome": "$28B", "debtRatio": "15%", "creditRating": "AAA"},
                     "cypherAnalysis": {
                         "shortestPathToRisk": "N/A",
                         "riskFactors": ["Geopolitical Risk"]
                     }}
                ],
                "edges": [
                    {"from": "s1", "to": "h1", "label": "Major Shareholder"},
                    {"from": "h1", "to": "v1", "label": "HBM3 Supply"},
                    {"from": "h1", "to": "v2", "label": "NAND Supply"},
                    {"from": "h1", "to": "s2", "label": "Outsourcing"},
                    {"from": "h1", "to": "s3", "label": "Stratgic Alliance"}
                ],
                "status_card": {
                    "title": "안정적 공급망 유지",
                    "description": "스폰서 및 주요 고객사(NVIDIA)와의 관계가 견고하며, 특별한 리스크 전이 징후가 발견되지 않았습니다.",
                    "level": "NORMAL"
                }
            }


def convert_to_monitoring_data(analyze_result: Dict, internal_stub: InternalDataStub = None) -> Dict:
    """analyze() 결과를 MonitoringData UI 타입으로 변환"""
    if internal_stub is None:
        internal_stub = InternalDataStub()
    if analyze_result is None:
        return {}
    
    company = analyze_result.get('company', '')
    ltv = internal_stub.get_ltv_metrics(company)
    covenant = internal_stub.get_covenant_status(company)
    ebitda = internal_stub.get_ebitda_metrics(company)
    graph_data = internal_stub.get_graph_data(company)
    
    score = analyze_result.get('score')
    if score is None: score = 0
    status = "PASS" if score <= 30 else "WARNING" if score <= 60 else "FAIL"
    
    return {
        "dealName": company, "tranche": f"리스크 점수: {score}점", "status": status,
        "metrics": {"ltv": ltv, "ebitda": ebitda.get('value', 'N/A'), "covenant": covenant.get('status', 'N/A')},
        "graph": graph_data,
        "timeline": internal_stub.get_5_stage_timeline(company), 
        "rmActions": {}, "opsActions": {}, "evidence": [],
        "_analyze_result": analyze_result
    }


# ==============================================================================
# 메인 시스템 클래스
# ==============================================================================

class RiskWarningSystem:
    """기업 리스크 조기경보 시스템 v14.1 - 14개 카테고리 + 6개 채널"""
    
    def __init__(self, reset_data: bool = False, use_kipris: bool = True):
        print("🚀 기업 리스크 조기경보 시스템 v14.1 초기화 (14 카테고리 + 6 채널)...")
        
        # 핵심 컴포넌트 (기존)
        self.dart = DartAPI()
        self.news = NewsScanner()
        self.patent_scanner = PatentScanner(use_kipris=use_kipris)
        self.review_scanner = ReviewScanner()
        
        # Day 1: 소송/신용등급 (B1, B3)
        self.legal_scanner = LegalScanner()
        self.credit_scanner = CreditScanner()
        
        # 멀티채널 스캐너 (C1-C5, C10) - C7 블라인드는 SocialScanner로 통합
        self.naver_scanner = NaverNewsScanner()     # C1: 네이버
        self.kind_scanner = KindScanner()           # C3: KIND
        self.daum_scanner = DaumNewsScanner()       # C2: 다음
        self.court_scanner = CourtScanner()         # C5: 대법원
        self.rating_agency_scanner = RatingAgencyScanner()  # C10: 신용평가사
        
        # 확장 카테고리 (B2, B4-B8)
        self.fss_scanner = FssScanner()          # B2: 금감원
        self.esg_scanner = EsgScanner()          # B4: ESG
        self.social_scanner = SocialScanner()    # B5: SNS/커뮤니티
        self.realestate_scanner = RealEstateScanner()  # B6: 부동산
        self.trademark_scanner = TrademarkScanner()    # B7: 상표
        self.competitor_scanner = CompetitorScanner()  # B8: 경쟁사
        
        self.graph = GraphBuilder()
        
        # 엔진 (모든 스캐너 전달)
        self.engine = RiskEngine(
            self.dart, self.graph, self.news, 
            self.patent_scanner, self.review_scanner,
            self.legal_scanner, self.credit_scanner,
            self.naver_scanner, self.kind_scanner,
            self.fss_scanner, self.esg_scanner, self.social_scanner,
            self.realestate_scanner, self.trademark_scanner, self.competitor_scanner,
            self.daum_scanner, self.court_scanner, None, self.rating_agency_scanner  # None = 구 blind_scanner (SocialScanner로 통합)
        )
        
        # 고도화 모듈
        self.alert_gen = AlertGenerator(self.graph)
        self.timeline_gen = TimelineGenerator(self.graph)
        self.leaderboard = RiskLeaderboard(self.graph)
        self.internal_stub = InternalDataStub()
        
        # AI 서비스 로드 (Day 4 & 통합테스트용)
        try:
            from . import ai_service
            self.ai_service = ai_service
        except ImportError:
            self.ai_service = None
            print("⚠️ ai_service 모듈 로드 실패")
            
        if reset_data:
            self.graph.reset()
        
        # 공급망 데이터 초기화 (Day 5)
        self._init_supply_chain()
        
        print("✅ 시스템 초기화 완료")
        
    def _init_supply_chain(self):
        """⛓️ 공급망 데이터 초기화 (Mock Data)"""
        print("  ⛓️ 공급망 데이터(Supply Chain) 주입 중...")
        # 1. SK하이닉스 공급사 (Supplier -> Corp)
        suppliers = [
            ("한미반도체", 60),  # 고위험
            ("에스앤에스텍", 40), # 중위험
            ("ASML", 20)      # 저위험
        ]
        for name, score in suppliers:
            self.graph.add_company(name)
            self.graph.update_entity_risk("company", name, score, ["공급망리스크"])
            self.graph.add_supply_relation(name, "SK하이닉스")
            
        # 2. SK하이닉스 고객사 (Corp -> Customer)
        customers = [
            ("Apple", 10),    # 저위험
            ("NVIDIA", 30),   # 중위험 (최근 변동성)
            ("Dell", 50)      # 중위험
        ]
        for name, score in customers:
            self.graph.add_company(name)
            self.graph.update_entity_risk("company", name, score, ["매출감소우려"])
            self.graph.add_supply_relation("SK하이닉스", name)
        
    def get_dashboard_data(self, company: str) -> Dict:
        """DB에 저장된 데이터 조회 (스캔 없이 모니터링 화면 구성용)"""
        print(f"🔍 '{company}' 데이터 조회 중...")
        
        # 1. 기본 정보 & 스코어 조회
        query = """
        MATCH (c:Company {name: $company})
        OPTIONAL MATCH (r:RiskLevel)-[:HAS_STATUS]->(c)
        RETURN c.total_score AS score, r.level AS level, r.label AS signal, 
               c.data_coverage AS coverage, c.propagated_risk AS propagated, c.top_factors AS factors
        """
        basic = self.graph.graph.query(query, {"company": company})
        if not basic:
            print(f"⚠️ '{company}'에 대한 분석 데이터가 없습니다. 먼저 run.py를 실행하세요.")
            return None
            
        basic_info = basic[0]
        
        # 2. 카테고리별 점수 (Breakdown)
        cat_query = """
        MATCH (c:Company {name: $company})-[:HAS_CATEGORY]->(cat:Category)
        RETURN cat.label AS label, cat.type AS type, cat.risk_score AS score
        """
        cats = self.graph.graph.query(cat_query, {"company": company})
        breakdown = {c['type']: c['score'] for c in cats}
        
        # 3. 고도화 데이터 (기존 모듈 활용)
        alerts = self.alert_gen.generate_alerts(company, limit=5)
        timeline = self.timeline_gen.generate_timeline(company)
        
        # 4. Mock Metrics & Graph Data
        monitoring_data = convert_to_monitoring_data({'company': company, 'score': basic_info['score']}, self.internal_stub)
        
        # 결과 통합
        return {
            "dealName": company,
            "metrics": monitoring_data['metrics'],
            "graph": monitoring_data.get('graph', {"nodes": [], "edges": []}),
            "timeline": timeline,
            "alerts": alerts,
            "_analyze_result": {
                "score": basic_info['score'],
                "propagated": basic_info.get('propagated', 0),
                "signal": basic_info['signal'],
                "factors": basic_info.get('factors', []),
                "breakdown": breakdown,
                "adjusted_weights": self.engine.BASE_WEIGHTS # 저장된 가중치가 없으면 기본값 사용
            }
        }
    
    def analyze(self, company: str) -> Dict:
        """단일 기업 분석"""
        result = self.engine.diagnose(company)
        if not result: return None
        
        print(f"\n{'='*60}\n🏢 {result['company']} 리스크 진단 결과\n{'='*60}")
        print(f"\n   신호: {result['signal']}")
        print(f"   총점: {result['score']}점 (직접 {result['direct_score']}점 + 전이 {result['propagated']}점)")
        cov = result['coverage']; cov_count = sum(1 for v in cov.values() if v)
        print(f"   📊 커버리지: {cov_count}/6 ({int(cov_count/6*100)}%)")
        if result['top_factors']:
            print(f"\n🔥 Top {len(result['top_factors'])} 리스크 요인:")
            for i, f in enumerate(result['top_factors'], 1): print(f"   {i}. {f}")
        
        return result
    
    def full_analysis(self, company: str) -> Dict:
        """전체 분석 + 고도화 기능"""
        result = self.analyze(company)
        if not result: return None
        
        alerts = self.alert_gen.generate_alerts(company, limit=5)
        timeline = self.timeline_gen.generate_timeline(company)
        monitoring = convert_to_monitoring_data(result, self.internal_stub)
        monitoring['timeline'] = timeline
        monitoring['alerts'] = alerts
        
        print(f"\n📊 고도화 결과: 알림 {len(alerts)}건, 타임라인 {len(timeline)}건")
        return monitoring
    
    def batch_analyze(self, companies: List[str]) -> List[Dict]:
        """여러 기업 일괄 분석"""
        results = []
        for company in companies:
            result = self.analyze(company)
            if result: results.append(result)
        self.recalc_propagation()
        return results
    
    def recalc_propagation(self):
        """리스크 전이 재계산"""
        print("\n🔄 리스크 전이 재계산...")
        companies = self.graph.graph.query("MATCH (r:RiskLevel)-[:HAS_STATUS]->(c:Company) WHERE c.total_score IS NOT NULL RETURN c.name AS name, c.total_score AS score, c.propagated_risk AS old_prop ORDER BY c.total_score DESC")
        updated = 0
        for c in companies:
            company, old_prop = c['name'], c.get('old_prop', 0) or 0
            connections = self.graph.calc_propagated_risk(company)
            new_prop = min(sum(round(conn['risk_score'] * 0.3) for conn in connections), 30) if connections else 0
            if new_prop != old_prop:
                direct_score = c['score'] - old_prop
                new_total = round(direct_score + new_prop)
                level = "GREEN" if new_total <= 30 else "YELLOW" if new_total <= 60 else "RED"
                self.graph.graph.query("MATCH (c:Company {name: $name})-[r:HAS_STATUS]-(:RiskLevel) DELETE r", {"name": company})
                self.graph.graph.query("MATCH (c:Company {name: $name}), (r:RiskLevel {level: $level}) MERGE (r)-[:HAS_STATUS]->(c) SET c.total_score = $total, c.propagated_risk = $prop",
                                 {"name": company, "level": level, "total": new_total, "prop": new_prop})
                updated += 1
        print(f"✅ {updated}개 기업 업데이트")
    
    def show_leaderboard(self, limit: int = 10):
        """리더보드 출력"""
        print(f"\n📊 리스크 리더보드 (TOP {limit})")
        print("=" * 60)
        for item in self.leaderboard.get_leaderboard(limit):
            print(f"{item['icon']} #{item['rank']} {item['company']}: {item['score']}점 ({item['status']})")
    
    def show_summary(self):
        """전체 현황 출력"""
        companies = self.graph.graph.query("MATCH (r:RiskLevel)-[:HAS_STATUS]->(c:Company) RETURN r.label AS status, c.name AS company, c.total_score AS score ORDER BY c.total_score DESC")
        print("\n📊 분석된 기업:")
        for c in companies:
            print(f"   {c['status']} {c['company']}: {c['score']}점")


# ==============================================================================
# 모듈 로드 시 출력
# ==============================================================================

if __name__ != "__main__":
    print("✅ risk_engine 모듈 로드 완료")
