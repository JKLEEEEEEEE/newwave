import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.RISK_API_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ dealId: string; categoryCode: string }> }
) {
  try {
    const { dealId, categoryCode } = await params;
    const res = await fetch(
      `${API_BASE}/api/v4/deals/${encodeURIComponent(dealId)}/categories/${categoryCode}`,
      { cache: 'no-store' }
    );

    if (!res.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch category detail' },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching category detail:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
