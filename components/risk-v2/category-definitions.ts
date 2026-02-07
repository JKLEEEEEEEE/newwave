/**
 * Risk V2 - 카테고리 정의 (10개)
 * init_graph_v5.py 기반 고정 설정값
 * mock-data에서 분리된 독립 모듈
 */

import type { CategoryDefinitionV2 } from './types-v2';

export const CATEGORY_DEFINITIONS_V2: CategoryDefinitionV2[] = [
  { code: 'SHARE',  name: '주주',     icon: '📊', weight: 0.15 },
  { code: 'EXEC',   name: '임원',     icon: '👔', weight: 0.15 },
  { code: 'CREDIT', name: '신용',     icon: '💳', weight: 0.15 },
  { code: 'LEGAL',  name: '법률',     icon: '⚖️', weight: 0.12 },
  { code: 'GOV',    name: '지배구조', icon: '🏛️', weight: 0.10 },
  { code: 'OPS',    name: '운영',     icon: '⚙️', weight: 0.10 },
  { code: 'AUDIT',  name: '감사',     icon: '📋', weight: 0.08 },
  { code: 'ESG',    name: 'ESG',      icon: '🌱', weight: 0.08 },
  { code: 'SUPPLY', name: '공급망',   icon: '🔗', weight: 0.05 },
  { code: 'OTHER',  name: '기타',     icon: '📎', weight: 0.02 },
];
