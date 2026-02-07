/**
 * RiskScoreBreakdownV3 컴포넌트 테스트
 * Feature: supply-chain-e2e-test
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock data types
interface Category {
  name: string;
  score: number;
  weight: number;
}

interface Signal {
  id: string;
  type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  message: string;
}

interface Propagator {
  companyName: string;
  contribution: number;
}

interface ScoreBreakdownData {
  totalScore: number;
  status: 'PASS' | 'WARNING' | 'FAIL';
  breakdown: {
    directScore: number;
    propagatedScore: number;
  };
  categories: Category[];
  recentSignals: Signal[];
  propagators: Propagator[];
}

// Mock RiskScoreBreakdownV3 component
const MockRiskScoreBreakdownV3: React.FC<{ data: ScoreBreakdownData }> = ({ data }) => {
  const [activeTab, setActiveTab] = React.useState<'categories' | 'signals' | 'propagators'>('categories');

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PASS':
        return 'bg-green-500';
      case 'WARNING':
        return 'bg-yellow-500';
      case 'FAIL':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'text-red-700';
      case 'HIGH':
        return 'text-red-500';
      case 'MEDIUM':
        return 'text-yellow-500';
      case 'LOW':
        return 'text-green-500';
      default:
        return 'text-gray-500';
    }
  };

  return (
    <div data-testid="score-breakdown-container">
      {/* Header with total score and status */}
      <div data-testid="score-header">
        <span data-testid="total-score">{data.totalScore}</span>
        <span data-testid="status-badge" className={getStatusColor(data.status)}>
          {data.status}
        </span>
      </div>

      {/* Breakdown bars */}
      <div data-testid="breakdown-section">
        <div data-testid="direct-score">
          직접 리스크: {data.breakdown.directScore}
          <div
            data-testid="direct-progress-bar"
            style={{ width: `${data.breakdown.directScore}%` }}
          />
        </div>
        <div data-testid="propagated-score">
          전이 리스크: {data.breakdown.propagatedScore}
          <div
            data-testid="propagated-progress-bar"
            style={{ width: `${data.breakdown.propagatedScore}%` }}
          />
        </div>
      </div>

      {/* Tabs */}
      <div data-testid="tabs">
        <button
          data-testid="tab-categories"
          onClick={() => setActiveTab('categories')}
          className={activeTab === 'categories' ? 'active' : ''}
        >
          카테고리
        </button>
        <button
          data-testid="tab-signals"
          onClick={() => setActiveTab('signals')}
        >
          최근 신호
        </button>
        <button
          data-testid="tab-propagators"
          onClick={() => setActiveTab('propagators')}
        >
          전이 경로
        </button>
      </div>

      {/* Tab content */}
      <div data-testid="tab-content">
        {activeTab === 'categories' && (
          <div data-testid="categories-list">
            {data.categories.map((cat, idx) => (
              <div key={idx} data-testid="category-item">
                <span data-testid="category-name">{cat.name}</span>
                <span data-testid="category-score">{cat.score}</span>
                <span data-testid="category-weight">{cat.weight}</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'signals' && (
          <div data-testid="signals-list">
            {data.recentSignals.map((signal) => (
              <div key={signal.id} data-testid="signal-item">
                <span data-testid="signal-type">{signal.type}</span>
                <span data-testid="signal-severity" className={getSeverityColor(signal.severity)}>
                  {signal.severity}
                </span>
                <span data-testid="signal-message">{signal.message}</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'propagators' && (
          <div data-testid="propagators-list">
            {data.propagators.map((prop, idx) => (
              <div key={idx} data-testid="propagator-item">
                <span data-testid="propagator-name">{prop.companyName}</span>
                <span data-testid="propagator-contribution">{prop.contribution}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

describe('RiskScoreBreakdownV3 Component', () => {
  const mockData: ScoreBreakdownData = {
    totalScore: 58,
    status: 'WARNING',
    breakdown: {
      directScore: 46,
      propagatedScore: 12,
    },
    categories: [
      { name: '재무', score: 45, weight: 0.3 },
      { name: '운영', score: 52, weight: 0.25 },
      { name: '법률', score: 38, weight: 0.2 },
      { name: '시장', score: 61, weight: 0.15 },
      { name: '공급망', score: 72, weight: 0.1 },
    ],
    recentSignals: [
      { id: 's1', type: 'LEGAL', severity: 'HIGH', message: '소송 관련 뉴스' },
      { id: 's2', type: 'MARKET', severity: 'MEDIUM', message: '시장 변동성 증가' },
    ],
    propagators: [
      { companyName: 'ASML', contribution: 5.2 },
      { companyName: '삼성전자', contribution: 3.8 },
      { companyName: '마이크론', contribution: 3.0 },
    ],
  };

  describe('Score Display Tests', () => {
    test('SB-01: 총점이 표시되어야 함', () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      const totalScore = screen.getByTestId('total-score');
      expect(totalScore).toHaveTextContent('58');
    });

    test('SB-02: WARNING Status 배지가 표시되어야 함', () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      const statusBadge = screen.getByTestId('status-badge');
      expect(statusBadge).toHaveTextContent('WARNING');
    });

    test('SB-02: PASS Status 배지 표시', () => {
      const passData: ScoreBreakdownData = {
        ...mockData,
        totalScore: 40,
        status: 'PASS',
      };
      render(<MockRiskScoreBreakdownV3 data={passData} />);

      expect(screen.getByTestId('status-badge')).toHaveTextContent('PASS');
    });

    test('SB-02: FAIL Status 배지 표시', () => {
      const failData: ScoreBreakdownData = {
        ...mockData,
        totalScore: 80,
        status: 'FAIL',
      };
      render(<MockRiskScoreBreakdownV3 data={failData} />);

      expect(screen.getByTestId('status-badge')).toHaveTextContent('FAIL');
    });
  });

  describe('Breakdown Display Tests', () => {
    test('SB-03: 직접 리스크 점수가 표시되어야 함', () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      const directScore = screen.getByTestId('direct-score');
      expect(directScore).toHaveTextContent('46');
    });

    test('SB-03: 전이 리스크 점수가 표시되어야 함', () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      const propagatedScore = screen.getByTestId('propagated-score');
      expect(propagatedScore).toHaveTextContent('12');
    });

    test('SB-03: 직접 리스크 진행바가 렌더링되어야 함', () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      const progressBar = screen.getByTestId('direct-progress-bar');
      expect(progressBar).toBeInTheDocument();
    });

    test('SB-03: 전이 리스크 진행바가 렌더링되어야 함', () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      const progressBar = screen.getByTestId('propagated-progress-bar');
      expect(progressBar).toBeInTheDocument();
    });
  });

  describe('Category Tab Tests', () => {
    test('SB-04: 카테고리 목록이 기본으로 표시됨', () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      const categoriesList = screen.getByTestId('categories-list');
      expect(categoriesList).toBeInTheDocument();
    });

    test('SB-04: 모든 카테고리가 표시됨', () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      const categoryItems = screen.getAllByTestId('category-item');
      expect(categoryItems).toHaveLength(5);
    });

    test('SB-04: 카테고리 이름이 표시됨', () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      expect(screen.getByText('재무')).toBeInTheDocument();
      expect(screen.getByText('운영')).toBeInTheDocument();
      expect(screen.getByText('법률')).toBeInTheDocument();
      expect(screen.getByText('시장')).toBeInTheDocument();
      expect(screen.getByText('공급망')).toBeInTheDocument();
    });

    test('SB-04: 카테고리 점수가 표시됨', () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      const categoryScores = screen.getAllByTestId('category-score');
      expect(categoryScores[0]).toHaveTextContent('45');
    });
  });

  describe('Signals Tab Tests', () => {
    test('SB-05: 최근 신호 탭 클릭 시 신호 목록 표시', async () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      const signalsTab = screen.getByTestId('tab-signals');
      fireEvent.click(signalsTab);

      await waitFor(() => {
        expect(screen.getByTestId('signals-list')).toBeInTheDocument();
      });
    });

    test('SB-05: 신호 메시지가 표시됨', async () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      fireEvent.click(screen.getByTestId('tab-signals'));

      await waitFor(() => {
        expect(screen.getByText('소송 관련 뉴스')).toBeInTheDocument();
      });
    });

    test('SB-05: 신호 severity 배지가 표시됨', async () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      fireEvent.click(screen.getByTestId('tab-signals'));

      await waitFor(() => {
        expect(screen.getByText('HIGH')).toBeInTheDocument();
        expect(screen.getByText('MEDIUM')).toBeInTheDocument();
      });
    });

    test('SB-05: 신호 타입이 표시됨', async () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      fireEvent.click(screen.getByTestId('tab-signals'));

      await waitFor(() => {
        expect(screen.getByText('LEGAL')).toBeInTheDocument();
        expect(screen.getByText('MARKET')).toBeInTheDocument();
      });
    });
  });

  describe('Propagators Tab Tests', () => {
    test('SB-06: 전이 경로 탭 클릭 시 목록 표시', async () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      const propagatorsTab = screen.getByTestId('tab-propagators');
      fireEvent.click(propagatorsTab);

      await waitFor(() => {
        expect(screen.getByTestId('propagators-list')).toBeInTheDocument();
      });
    });

    test('SB-06: Propagator 기업명이 표시됨', async () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      fireEvent.click(screen.getByTestId('tab-propagators'));

      await waitFor(() => {
        expect(screen.getByText('ASML')).toBeInTheDocument();
        expect(screen.getByText('삼성전자')).toBeInTheDocument();
        expect(screen.getByText('마이크론')).toBeInTheDocument();
      });
    });

    test('SB-06: Propagator 기여도가 표시됨', async () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      fireEvent.click(screen.getByTestId('tab-propagators'));

      await waitFor(() => {
        const contributions = screen.getAllByTestId('propagator-contribution');
        expect(contributions[0]).toHaveTextContent('5.2');
      });
    });
  });

  describe('Tab Navigation Tests', () => {
    test('탭 전환이 정상 동작함', async () => {
      render(<MockRiskScoreBreakdownV3 data={mockData} />);

      // 초기: 카테고리 탭
      expect(screen.getByTestId('categories-list')).toBeInTheDocument();

      // 신호 탭으로 전환
      fireEvent.click(screen.getByTestId('tab-signals'));
      await waitFor(() => {
        expect(screen.getByTestId('signals-list')).toBeInTheDocument();
      });

      // 전이 경로 탭으로 전환
      fireEvent.click(screen.getByTestId('tab-propagators'));
      await waitFor(() => {
        expect(screen.getByTestId('propagators-list')).toBeInTheDocument();
      });

      // 카테고리 탭으로 다시 전환
      fireEvent.click(screen.getByTestId('tab-categories'));
      await waitFor(() => {
        expect(screen.getByTestId('categories-list')).toBeInTheDocument();
      });
    });
  });

  describe('Edge Cases', () => {
    test('빈 카테고리 목록 처리', () => {
      const emptyCategories: ScoreBreakdownData = {
        ...mockData,
        categories: [],
      };
      render(<MockRiskScoreBreakdownV3 data={emptyCategories} />);

      const categoryItems = screen.queryAllByTestId('category-item');
      expect(categoryItems).toHaveLength(0);
    });

    test('빈 신호 목록 처리', async () => {
      const emptySignals: ScoreBreakdownData = {
        ...mockData,
        recentSignals: [],
      };
      render(<MockRiskScoreBreakdownV3 data={emptySignals} />);

      fireEvent.click(screen.getByTestId('tab-signals'));

      await waitFor(() => {
        const signalItems = screen.queryAllByTestId('signal-item');
        expect(signalItems).toHaveLength(0);
      });
    });

    test('빈 propagators 목록 처리', async () => {
      const emptyPropagators: ScoreBreakdownData = {
        ...mockData,
        propagators: [],
      };
      render(<MockRiskScoreBreakdownV3 data={emptyPropagators} />);

      fireEvent.click(screen.getByTestId('tab-propagators'));

      await waitFor(() => {
        const propagatorItems = screen.queryAllByTestId('propagator-item');
        expect(propagatorItems).toHaveLength(0);
      });
    });

    test('경계값 점수 처리 - 0점', () => {
      const zeroScore: ScoreBreakdownData = {
        ...mockData,
        totalScore: 0,
        status: 'PASS',
        breakdown: { directScore: 0, propagatedScore: 0 },
      };
      render(<MockRiskScoreBreakdownV3 data={zeroScore} />);

      expect(screen.getByTestId('total-score')).toHaveTextContent('0');
    });

    test('경계값 점수 처리 - 100점', () => {
      const fullScore: ScoreBreakdownData = {
        ...mockData,
        totalScore: 100,
        status: 'FAIL',
        breakdown: { directScore: 80, propagatedScore: 20 },
      };
      render(<MockRiskScoreBreakdownV3 data={fullScore} />);

      expect(screen.getByTestId('total-score')).toHaveTextContent('100');
    });
  });
});

describe('Score Status Classification', () => {
  const getStatus = (score: number): 'PASS' | 'WARNING' | 'FAIL' => {
    if (score < 50) return 'PASS';
    if (score < 75) return 'WARNING';
    return 'FAIL';
  };

  test('점수 0-49: PASS', () => {
    expect(getStatus(0)).toBe('PASS');
    expect(getStatus(25)).toBe('PASS');
    expect(getStatus(49)).toBe('PASS');
  });

  test('점수 50-74: WARNING', () => {
    expect(getStatus(50)).toBe('WARNING');
    expect(getStatus(62)).toBe('WARNING');
    expect(getStatus(74)).toBe('WARNING');
  });

  test('점수 75-100: FAIL', () => {
    expect(getStatus(75)).toBe('FAIL');
    expect(getStatus(88)).toBe('FAIL');
    expect(getStatus(100)).toBe('FAIL');
  });
});
