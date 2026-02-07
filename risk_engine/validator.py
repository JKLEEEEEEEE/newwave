"""
데이터 검증 모듈 (Risk Graph v3)
- 책임: 수집 데이터의 유효성 검증, 정규화, 중복 검사
- 위치: risk_engine/validator.py

Design Doc: docs/02-design/features/risk-graph-v3.design.md Section 3.6
"""

from __future__ import annotations
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any, Literal
from urllib.parse import urlparse

# =============================================================================
# 상수 정의
# =============================================================================

DataType = Literal["News", "Disclosure", "Company", "Person", "Financials"]

# 데이터 타입별 필수 필드
REQUIRED_FIELDS: dict[str, list[str]] = {
    "News": ["title", "source", "url", "published_at"],
    "Disclosure": ["rcept_no", "title", "corp_code", "filing_date"],
    "Company": ["id", "name", "source"],
    "Person": ["id", "name", "source"],
    "Financials": ["company_id", "fiscal_year", "source"],
}

# 숫자 범위 검증
RANGE_VALIDATION: dict[str, tuple[float, float]] = {
    "risk_score": (0, 100),
    "raw_score": (0, 100),
    "decayed_score": (0, 100),
    "sentiment": (-1, 1),
    "confidence": (0, 1),
    "decay_rate": (0, 1),
    "ownership_percent": (0, 100),
}

# 문자열 길이 제한
LENGTH_LIMITS: dict[str, int] = {
    "title": 500,
    "name": 200,
    "url": 2000,
    "content": 50000,
    "summary": 1000,
}

# URL 스키마 허용 목록
ALLOWED_URL_SCHEMES = {"http", "https"}

# 날짜 필드 목록
DATE_FIELDS = {"published_at", "filing_date", "fetched_at", "created_at", "updated_at", "report_date"}


# =============================================================================
# 데이터 클래스
# =============================================================================

@dataclass
class ValidationError:
    """검증 오류"""
    field: str
    message: str
    severity: Literal["error", "warning"] = "error"


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    normalized_data: dict | None = None

    def add_error(self, field: str, message: str) -> None:
        self.errors.append(ValidationError(field, message, "error"))
        self.is_valid = False

    def add_warning(self, field: str, message: str) -> None:
        self.warnings.append(ValidationError(field, message, "warning"))

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "errors": [{"field": e.field, "message": e.message} for e in self.errors],
            "warnings": [{"field": w.field, "message": w.message} for w in self.warnings],
        }


# =============================================================================
# DataValidator 클래스
# =============================================================================

class DataValidator:
    """데이터 검증기"""

    def __init__(self, neo4j_client=None):
        """
        Args:
            neo4j_client: Neo4j 클라이언트 (중복 검사용, 선택)
        """
        self.neo4j_client = neo4j_client

    def validate(self, data: dict, data_type: DataType) -> ValidationResult:
        """
        데이터 종합 검증

        Args:
            data: 검증할 데이터
            data_type: 데이터 타입

        Returns:
            ValidationResult: 검증 결과
        """
        result = ValidationResult(is_valid=True)

        # 1. 필수 필드 검증
        required_errors = self.validate_required_fields(data, data_type)
        for err in required_errors:
            result.add_error(err["field"], err["message"])

        # 2. 범위 검증
        range_errors = self.validate_ranges(data)
        for err in range_errors:
            result.add_error(err["field"], err["message"])

        # 3. 형식 검증
        format_errors = self.validate_formats(data, data_type)
        for err in format_errors:
            if err.get("severity") == "warning":
                result.add_warning(err["field"], err["message"])
            else:
                result.add_error(err["field"], err["message"])

        # 4. 정규화 (검증 통과 시)
        if result.is_valid:
            result.normalized_data = self.normalize(data, data_type)

        return result

    def validate_required_fields(self, data: dict, data_type: DataType) -> list[dict]:
        """
        필수 필드 검증

        Args:
            data: 검증할 데이터
            data_type: 데이터 타입

        Returns:
            오류 목록 [{"field": str, "message": str}, ...]
        """
        errors = []
        required = REQUIRED_FIELDS.get(data_type, [])

        for field in required:
            if field not in data:
                errors.append({
                    "field": field,
                    "message": f"필수 필드 '{field}'가 없습니다",
                })
            elif data[field] is None or data[field] == "":
                errors.append({
                    "field": field,
                    "message": f"필수 필드 '{field}'가 비어있습니다",
                })

        return errors

    def validate_ranges(self, data: dict) -> list[dict]:
        """
        숫자 범위 검증

        Args:
            data: 검증할 데이터

        Returns:
            오류 목록
        """
        errors = []

        for field, (min_val, max_val) in RANGE_VALIDATION.items():
            if field in data and data[field] is not None:
                value = data[field]
                if not isinstance(value, (int, float)):
                    errors.append({
                        "field": field,
                        "message": f"'{field}'는 숫자여야 합니다 (현재: {type(value).__name__})",
                    })
                elif value < min_val or value > max_val:
                    errors.append({
                        "field": field,
                        "message": f"'{field}' 값이 범위를 벗어났습니다 ({min_val}~{max_val}, 현재: {value})",
                    })

        return errors

    def validate_formats(self, data: dict, data_type: DataType) -> list[dict]:
        """
        형식 검증 (URL, 날짜, 길이 등)

        Args:
            data: 검증할 데이터
            data_type: 데이터 타입

        Returns:
            오류/경고 목록
        """
        issues = []

        # URL 검증
        if "url" in data and data["url"]:
            url_error = self._validate_url(data["url"])
            if url_error:
                issues.append({"field": "url", "message": url_error})

        # 날짜 검증
        for field in DATE_FIELDS:
            if field in data and data[field]:
                date_error = self._validate_date(data[field], field)
                if date_error:
                    issues.append({"field": field, "message": date_error})

        # 길이 검증
        for field, max_len in LENGTH_LIMITS.items():
            if field in data and data[field] and isinstance(data[field], str):
                if len(data[field]) > max_len:
                    issues.append({
                        "field": field,
                        "message": f"'{field}' 길이가 최대치를 초과했습니다 (max: {max_len}, 현재: {len(data[field])})",
                        "severity": "warning",
                    })

        # corp_code 형식 검증 (8자리 숫자)
        if "corp_code" in data and data["corp_code"]:
            if not re.match(r"^\d{8}$", str(data["corp_code"])):
                issues.append({
                    "field": "corp_code",
                    "message": "corp_code는 8자리 숫자여야 합니다",
                })

        return issues

    def _validate_url(self, url: str) -> str | None:
        """URL 형식 검증"""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ALLOWED_URL_SCHEMES:
                return f"허용되지 않는 URL 스키마: {parsed.scheme}"
            if not parsed.netloc:
                return "URL에 호스트가 없습니다"
            return None
        except Exception as e:
            return f"URL 파싱 실패: {str(e)}"

    def _validate_date(self, value: Any, field_name: str) -> str | None:
        """날짜 형식 검증"""
        if isinstance(value, (datetime, date)):
            return None

        if isinstance(value, str):
            # ISO 형식 체크
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                return None
            except ValueError:
                pass

            # YYYYMMDD 형식 체크
            if re.match(r"^\d{8}$", value):
                return None

            # YYYY-MM-DD 형식 체크
            if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                return None

            return f"'{field_name}' 날짜 형식이 올바르지 않습니다"

        return f"'{field_name}'는 날짜 타입이어야 합니다"

    def check_duplicate(self, data: dict, data_type: DataType) -> bool:
        """
        중복 검사 (Neo4j 조회)

        Args:
            data: 검사할 데이터
            data_type: 데이터 타입

        Returns:
            중복 여부 (True = 중복)
        """
        if self.neo4j_client is None:
            return False

        # 데이터 타입별 중복 키
        duplicate_keys = {
            "News": ("url",),
            "Disclosure": ("rcept_no",),
            "Company": ("id",),
            "Person": ("id",),
        }

        keys = duplicate_keys.get(data_type)
        if not keys:
            return False

        # 해시 기반 중복 검사 (URL 등)
        if "url" in keys and "url" in data:
            url_hash = self._hash_url(data["url"])
            # Neo4j 조회 (구현 필요)
            # query = f"MATCH (n:{data_type}) WHERE n.url_hash = $hash RETURN n LIMIT 1"
            # result = self.neo4j_client.run(query, {"hash": url_hash})
            # return result.single() is not None

        return False

    def _hash_url(self, url: str) -> str:
        """URL 해시 생성"""
        normalized = url.lower().strip().rstrip("/")
        return hashlib.md5(normalized.encode()).hexdigest()

    def normalize(self, data: dict, data_type: DataType | None = None) -> dict:
        """
        데이터 정규화

        Args:
            data: 정규화할 데이터
            data_type: 데이터 타입

        Returns:
            정규화된 데이터
        """
        normalized = data.copy()

        # 문자열 트림
        for key, value in normalized.items():
            if isinstance(value, str):
                normalized[key] = value.strip()

        # 날짜 정규화
        for field in DATE_FIELDS:
            if field in normalized and normalized[field]:
                normalized[field] = self._normalize_date(normalized[field])

        # URL 정규화
        if "url" in normalized and normalized["url"]:
            normalized["url"] = self._normalize_url(normalized["url"])
            normalized["url_hash"] = self._hash_url(normalized["url"])

        # corp_code 정규화 (8자리 패딩)
        if "corp_code" in normalized and normalized["corp_code"]:
            normalized["corp_code"] = str(normalized["corp_code"]).zfill(8)

        return normalized

    def _normalize_date(self, value: Any) -> str:
        """날짜를 ISO 형식으로 정규화"""
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str):
            # YYYYMMDD → YYYY-MM-DD
            if re.match(r"^\d{8}$", value):
                return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
            return value
        return str(value)

    def _normalize_url(self, url: str) -> str:
        """URL 정규화"""
        url = url.strip()
        # 프로토콜 없으면 https 추가
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url


# =============================================================================
# 헬퍼 함수
# =============================================================================

def validate_news(data: dict, neo4j_client=None) -> ValidationResult:
    """뉴스 데이터 검증 (편의 함수)"""
    validator = DataValidator(neo4j_client)
    return validator.validate(data, "News")


def validate_disclosure(data: dict, neo4j_client=None) -> ValidationResult:
    """공시 데이터 검증 (편의 함수)"""
    validator = DataValidator(neo4j_client)
    return validator.validate(data, "Disclosure")


def validate_company(data: dict, neo4j_client=None) -> ValidationResult:
    """기업 데이터 검증 (편의 함수)"""
    validator = DataValidator(neo4j_client)
    return validator.validate(data, "Company")


def validate_batch(data_list: list[dict], data_type: DataType,
                   neo4j_client=None) -> tuple[list[dict], list[ValidationResult]]:
    """
    배치 데이터 검증

    Args:
        data_list: 데이터 목록
        data_type: 데이터 타입
        neo4j_client: Neo4j 클라이언트

    Returns:
        (유효한 데이터 목록, 검증 결과 목록)
    """
    validator = DataValidator(neo4j_client)
    valid_data = []
    results = []

    for data in data_list:
        result = validator.validate(data, data_type)
        results.append(result)
        if result.is_valid and result.normalized_data:
            valid_data.append(result.normalized_data)

    return valid_data, results


def get_validation_summary(results: list[ValidationResult]) -> dict:
    """검증 결과 요약"""
    total = len(results)
    valid = sum(1 for r in results if r.is_valid)
    errors = sum(len(r.errors) for r in results)
    warnings = sum(len(r.warnings) for r in results)

    return {
        "total": total,
        "valid": valid,
        "invalid": total - valid,
        "valid_rate": round(valid / total * 100, 1) if total > 0 else 0,
        "total_errors": errors,
        "total_warnings": warnings,
    }
