/**
 * Risk Engine V4 - TypeScript Types
 */

// Category codes
export type CategoryCode = 'LEGAL' | 'CREDIT' | 'GOVERNANCE' | 'OPERATIONAL' | 'AUDIT' | 'ESG' | 'SUPPLY' | 'OTHER';
export type RiskLevel = 'PASS' | 'WARNING' | 'FAIL';
export type Trend = 'UP' | 'DOWN' | 'STABLE';
export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

// Category config
export const CATEGORY_CONFIG: Record<CategoryCode, { name: string; icon: string; color: string }> = {
  LEGAL: { name: '법률위험', icon: '⚖️', color: '#8B5CF6' },
  CREDIT: { name: '신용위험', icon: '💳', color: '#EF4444' },
  GOVERNANCE: { name: '지배구조', icon: '👥', color: '#F59E0B' },
  OPERATIONAL: { name: '운영위험', icon: '⚙️', color: '#3B82F6' },
  AUDIT: { name: '감사위험', icon: '📋', color: '#10B981' },
  ESG: { name: 'ESG위험', icon: '🌱', color: '#22C55E' },
  SUPPLY: { name: '공급망위험', icon: '🔗', color: '#6366F1' },
  OTHER: { name: '기타위험', icon: '📊', color: '#6B7280' },
};

// Score breakdown
export interface ScoreBreakdown {
  direct: number;
  propagated: number;
}

// Category summary
export interface CategorySummary {
  code: CategoryCode;
  name: string;
  icon: string;
  score: number;
  weight: number;
  weightedScore: number;
  eventCount: number;
  personCount: number;
  trend: Trend;
}

// Event summary
export interface EventSummary {
  id: string;
  title: string;
  category: CategoryCode;
  score: number;
  severity: Severity;
  newsCount: number;
  disclosureCount: number;
  firstDetectedAt: string;
}

// Person summary
export interface PersonSummary {
  id: string;
  name: string;
  position: string;
  type: 'EXECUTIVE' | 'SHAREHOLDER';
  riskScore: number;
  relatedNewsCount: number;
  relatedEventCount: number;
}

// Evidence summary
export interface EvidenceSummary {
  totalNews: number;
  totalDisclosures: number;
  topFactors: string[];
}

// News item
export interface NewsItem {
  id: string;
  title: string;
  source: string;
  publishedAt: string;
  rawScore: number;
  sentiment: 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE';
  url: string;
}

// Disclosure item
export interface DisclosureItem {
  id: string;
  title: string;
  filingDate: string;
  rawScore: number;
  category: string;
  url: string;
}

// Deal detail
export interface DealDetail {
  id: string;
  name: string;
  sector: string;
  score: number;
  riskLevel: RiskLevel;
  breakdown: ScoreBreakdown;
  trend: Trend;
  categories: CategorySummary[];
  topEvents: EventSummary[];
  topPersons: PersonSummary[];
  evidence: EvidenceSummary;
  lastUpdated: string;
}

// Category detail
export interface CategoryDetail {
  code: CategoryCode;
  name: string;
  icon: string;
  score: number;
  weight: number;
  events: EventSummary[];
  persons: PersonSummary[];
  news: NewsItem[];
  disclosures: DisclosureItem[];
}

// Event detail
export interface EventDetail {
  id: string;
  title: string;
  description: string;
  category: CategoryCode;
  score: number;
  severity: Severity;
  matchedKeywords: string[];
  involvedPersons: PersonSummary[];
  news: NewsItem[];
  disclosures: DisclosureItem[];
  firstDetectedAt: string;
  isActive: boolean;
}

// Person detail
export interface PersonDetail {
  id: string;
  name: string;
  position: string;
  type: 'EXECUTIVE' | 'SHAREHOLDER';
  tier: number;
  riskScore: number;
  riskLevel: RiskLevel;
  riskFactors: string[];
  companies: string[];
  involvedEvents: EventSummary[];
  relatedNews: NewsItem[];
}

// API response wrappers
export interface DealDetailResponse {
  schemaVersion: string;
  generatedAt: string;
  deal: DealDetail;
}

export interface CategoryDetailResponse {
  schemaVersion: string;
  generatedAt: string;
  category: CategoryDetail;
}

export interface EventDetailResponse {
  schemaVersion: string;
  generatedAt: string;
  event: EventDetail;
}

export interface PersonDetailResponse {
  schemaVersion: string;
  generatedAt: string;
  person: PersonDetail;
}
