
const path = require('path');
require('dotenv').config({
    path: path.resolve(__dirname, '..', '.env.local') // C:\dev\newwave\.env.local
});
const express = require('express');
const multer = require('multer');
const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const OpenAI = require('openai');
const pdf = require('pdf-parse');
const cors = require('cors');

const app = express();
const port = 3001;
function sanitizeJsonText(s) {
    if (!s) return s;

    // 1) 코드펜스 제거 ```json ... ```
    s = s.trim()
        .replace(/^```(?:json)?\s*/i, '')
        .replace(/\s*```$/, '')
        .trim();

    // 2) JSON 앞뒤 쓰레기 제거 (첫 { ~ 마지막 })
    const first = s.indexOf('{');
    const last = s.lastIndexOf('}');
    if (first !== -1 && last !== -1 && last > first) {
        s = s.slice(first, last + 1);
    }

    // 3) JSON에서 허용되지 않는 제어문자 제거 (PDF 파싱 시 자주 섞임)
    s = s.replace(/[\u0000-\u001F\u007F]/g, '');

    return s;
}
// Middleware
app.use(cors());
app.use(express.json());

// Database
const dbPath = path.resolve(__dirname, 'database.sqlite');
const db = new sqlite3.Database(dbPath);

// File Upload
const uploadDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir);
}
const upload = multer({ dest: uploadDir });

// OpenAI Setup
const openaiApiKey = process.env.OPENAI_API_KEY;
if (!openaiApiKey) {
    throw new Error("Missing OPENAI_API_KEY. Check .env.local in project root");
}
const openai = new OpenAI({ apiKey: openaiApiKey });

// --- Screening Criteria Table + Seed ---
db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS screening_criteria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module TEXT NOT NULL,
        category TEXT NOT NULL,
        item TEXT NOT NULL,
        score_1 TEXT DEFAULT '',
        score_2 TEXT DEFAULT '',
        score_3 TEXT DEFAULT '',
        score_4 TEXT DEFAULT '',
        score_5 TEXT DEFAULT '',
        source TEXT DEFAULT '',
        sort_order INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`);

    // Seed if empty
    db.get("SELECT COUNT(*) as cnt FROM screening_criteria", (err, row) => {
        if (err || (row && row.cnt > 0)) return;
        const seed = [
            ['1. 상환능력','현금흐름(Cash)','EBITDA 규모 (절대금액)','음수 (-)','10억 미만','10~50억','50~100억','100억 이상','추가',1],
            ['1. 상환능력','현금흐름(Cash)','영업활동현금흐름 (OCF)','음수 (Cash Burn)','매출의 0~3%','3~5%','5~10%','10% 이상','추가',2],
            ['1. 상환능력','현금흐름(Cash)','잉여현금흐름 (FCF)','대규모 적자','소폭 적자','BEP 수준','흑자 전환','안정적 흑자','추가',3],
            ['1. 상환능력','커버리지','DSCR (총부채상환비율)','1.0 미만 (불가)','1.0 ~ 1.2배','1.2 ~ 1.5배','1.5 ~ 2.0배','2.0배 초과','추가',4],
            ['1. 상환능력','커버리지','Net Debt / EBITDA (상환기간)','8배 초과','6 ~ 8배','4 ~ 6배','2 ~ 4배','2배 미만','보완',5],
            ['1. 상환능력','커버리지','이자보상배율 (ICR)','1.0 미만 (잠식)','1.0 ~ 1.5배','1.5 ~ 3.0배','3.0 ~ 5.0배','5.0배 초과','추가',6],
            ['1. 상환능력','재무안정성','유동비율 (단기지급능력)','50% 미만','50 ~ 90%','90 ~ 120%','120 ~ 200%','200% 초과','추가',7],
            ['2. 재무 기초','성장성','매출액 증가율 (CAGR)','역성장 (<0%)','0 ~ 3%','3 ~ 5%','5 ~ 10%','10% 초과','추가',8],
            ['2. 재무 기초','수익성','영업이익률 (OPM)','적자','0 ~ 3%','3 ~ 6%','6 ~ 10%','10% 초과','추가',9],
            ['2. 재무 기초','안정성','부채비율','400% 초과','300 ~ 400%','200 ~ 300%','100 ~ 200%','100% 미만','추가',10],
            ['2. 재무 기초','안정성','차입금 의존도','60% 초과','45 ~ 60%','30 ~ 45%','15 ~ 30%','15% 미만','추가',11],
            ['2. 재무 기초','수익성','ROE (자기자본이익률)','적자','0 ~ 5%','5 ~ 10%','10 ~ 15%','15% 초과','추가',12],
            ['3. HR/비재무','인력 이탈','최근 1년 퇴사율','30% 이상','20 ~ 30%','15 ~ 20%','10 ~ 15%','10% 미만','추가',13],
            ['3. HR/비재무','조직 활력','고용 증가율 (YoY)','감소 (구조조정)','보합 (0%)','0 ~ 5%','5 ~ 10%','10% 이상','추가',14],
            ['3. HR/비재무','처우 수준','평균 연봉 (업계 순위)','하위 25%','하위 50%','상위 30 ~ 50%','상위 10 ~ 30%','상위 10%','추가',15],
            ['3. HR/비재무','신용도','기업 신용등급 (NICE)','B- 이하','B ~ B+','BB ~ BB+','BBB ~ A','A+ 이상','추가',16],
            ['3. HR/비재무','평판','채용 공고 빈도','상시 채용 (기피)','매우 빈번','보통','가끔','결원 시만','추가',17],
            ['4. Sponsor','신뢰도','블라인드 펀드 유무','0 (미보유)','-','-','-','1 (보유)','기존룰',18],
            ['4. Sponsor','전문성','운용 전문인력 수','5명 이하','10명 이하','15명 이하','20명 이하','20명 초과','기존룰',19],
            ['4. Sponsor','업력','운용사 존속 기간','5년 이하','10년 이하','15년 이하','20년 이하','20년 초과','기존룰',20],
            ['4. Sponsor','규모','AUM (운용자산)','1조 미만','1조 이상','3조 이상','5조 이상','10조 이상','기존룰',21],
            ['4. Sponsor','안정성','만기시 리파이낸싱 비율','85% 초과','85% 이하','80% 이하','75% 이하','70% 이하','기존룰',22],
            ['4. Sponsor','경험','Track Record (유사 딜)','없음','1~2건','3~5건','5~10건','10건 이상','추가',23],
            ['5. Deal 구조','형태','단일 스폰서 여부','0 (Club Deal)','-','-','-','1 (Single)','기존룰',24],
            ['5. Deal 구조','담보','LTV (담보인정비율)','60% 초과','50 ~ 60%','40 ~ 50%','30 ~ 40%','30% 미만','기존룰',25],
            ['5. Deal 구조','레버리지','LTC (Loan To Cost)','9배 초과','9배 이하','8배 이하','7배 이하','6배 이하','기존룰',26],
            ['5. Deal 구조','규모','Deal Size (금액)','2,000억 이하','5,000억 이하','1조원 이하','3조원 이하','3조원 초과','기존룰',27],
            ['5. Deal 구조','우선권','상환 우선순위','후순위','-','중순위','-','선순위','기존룰',28],
            ['5. Deal 구조','통제권','담보/경영권 확보','미확보','일부 담보','100% 담보','경영권 양수도','완전 확보','기존룰',29],
            ['6. Target 구조','지배력','실질지배력 확보율','50% 이하','-','-','50% 초과','1','기존룰',30],
            ['6. Target 구조','지배력','단일 최대주주 유지기간','10년 이하','5년 이하','3년 이하','1년 이하','최초 조달','기존룰',31],
            ['6. Target 구조','시장지위','Market Share (순위)','하위 25%','하위 25% 이상','상위 25% 이상','상위 10% 이상','1위 (선도)','기존룰',32],
            ['6. Target 구조','수익성(상대)','동종업계 대비 수익성','하위 50%','중위 50%','상위 40%','상위 30%','상위 20%','기존룰',33],
        ];
        const stmt = db.prepare("INSERT INTO screening_criteria (module,category,item,score_1,score_2,score_3,score_4,score_5,source,sort_order) VALUES (?,?,?,?,?,?,?,?,?,?)");
        seed.forEach(row => stmt.run(row));
        stmt.finalize();
        console.log("Screening criteria seeded: 33 rows");
    });
});

// --- API ---

// 1. Upload & Analyze
app.post('/api/im/upload', upload.single('file'), async (req, res) => {
    if (!req.file) {
        return res.status(400).json({ error: 'No file uploaded' });
    }

    const filePath = req.file.path;
    // multer는 originalname을 latin1로 읽으므로 한글 파일명이 깨짐 → UTF-8로 변환
    const originalName = Buffer.from(req.file.originalname, 'latin1').toString('utf-8');

    try {
        // 1. Extract Text
        const dataBuffer = fs.readFileSync(filePath);
        const pdfData = await pdf(dataBuffer);
        const extractedText = pdfData.text;

        // 2. Fetch Scoring Items for Context
        const items = await new Promise((resolve, reject) => {
            db.all("SELECT * FROM scoring_items WHERE is_active = 1", (err, rows) => {
                if (err) reject(err);
                else resolve(rows);
            });
        });

        const scoringPrompt = items.map(item =>
            `- ID: ${item.item_key} | Name: ${item.item_name} | Criteria: ${item.description || item.item_name} (Min: ${item.score_min}, Max: ${item.score_max})`
        ).join('\n');

        // 3. Call OpenAI GPT-5.2
        const modelName = process.env.OPENAI_MODEL || "gpt-5.2";
        const systemPrompt = `당신은 숙련된 투자심사역(Investment Analyst)입니다.
투자설명서(IM) 텍스트를 분석하여 정량·정성 평가를 수행합니다.

⚠️ 매우 중요:
- 모든 서술, 요약, 코멘트, 설명은 반드시 한국어로만 작성하세요.
- JSON의 속성명(key)은 절대로 변경하지 마세요.
- evidence_text는 반드시 문자열(string) 1개여야 하며, 근거가 여러 개면 " / " 로 한 문장에 합치며 배열로 만들면 안됩니다.`;

        const userPrompt = `[평가 항목 / Scoring Items]
${scoringPrompt}

---

[추가로 반드시 추출해야 하는 Deal Terms — 누락 금지]
아래 5개 항목을 IM 본문에서 "정확히" 찾아서 출력하세요.
- PROJECT_NAME: 첫장 제목에 명시된 Project명 문장 그대로
- BORROWER: 차주(또는 SPC) 법인명
- SPONSOR: Sponsor/투자자/PE 운용사 명칭
- DEALSIZE: 본건 인수금융/리파이낸싱 총 조달금액(통화/단위 포함)
- TARGET_EQUITY: 대상회사(또는 담보 지분)의 자기자본가치/지분가치/Equity Value
  - 문서에 여러 값(예: Min/Avg/Max, DCF/Trading/Transaction 등)이 있으면
    1) "대표값(가능하면 Average 또는 문서가 '평균'이라 명시한 값)"을 extracted_value에 넣고,
    2) evidence_text에 근거 문장(표/문장)을 그대로 인용하며,
    3) notes에 "어떤 기준(DCF/Trading/Transaction 등)에서 어떤 값들을 봤는지" 요약하세요.
  - IM에 TARGET_EQUITY가 명확히 없으면 extracted_value는 "N/A"로, notes에 "IM 내 명시값 없음"을 쓰고,
    evidence_text는 "N/A"로 두세요. (절대 임의 추정 금지)

---

[분석 작업 지시]
1. IM 본문에서 각 평가 항목(item_key)에 해당하는 구체적인 수치, 문장, 근거를 추출하세요.
2. 추출한 근거를 바탕으로 각 항목에 대해 1~5점 수준의 score_raw를 부여하세요.
3. 점수 산정 사유 및 판단 근거는 논리적으로 한국어로 설명하세요.
4. 전체 투자 건에 대해 아래 3가지 관점에서 핵심 요약을 작성하세요.
   - Industry (산업 개요 및 매력도)
   - Deal Structure (거래 구조 및 자금 조달 방식)
   - Risk (주요 리스크 및 완화 요인)

---

[분석 대상 IM 텍스트]
${extractedText.substring(0, 30000)}
(※ 길이 제한으로 일부가 잘릴 수 있음)

---

[출력 JSON 구조 — 반드시 준수]
{
  "run_summary": {
    "file_name": "${originalName}",
    "overall_comment": "본 투자건에 대한 종합적인 한국어 평가 요약",
    "total_score": 0
  },
  "deal_terms": {
    "PROJECT_INFO": { "extracted_value": "", "evidence_text": "", "notes": "" },
    "PROJECT_NAME": { "extracted_value": "", "evidence_text": "", "notes": "" },
    "BORROWER": { "extracted_value": "", "evidence_text": "", "notes": "" },
    "SPONSOR": { "extracted_value": "", "evidence_text": "", "notes": "" },
    "DEALSIZE": { "extracted_value": "", "evidence_text": "", "notes": "" },
    "TARGET_EQUITY": { "extracted_value": "", "evidence_text": "", "notes": "" }
  },
  "items": [
    { "item_key": "", "extracted_value": "", "evidence_text": "", "score_raw": 0, "score_weighted": 0, "notes": "" }
  ],
  "project_golden_summary": {
    "industry_overview_highlights": [],
    "deal_structure_financing_plan": [],
    "risk_factors_mitigation": []
  }
}`;

        const completion = await openai.chat.completions.create({
            model: modelName,
            messages: [
                { role: "system", content: systemPrompt },
                { role: "user", content: userPrompt }
            ],
            response_format: { type: "json_object" },
            temperature: 0.3,
        });

        let text = completion.choices[0].message.content;

        text = sanitizeJsonText(text);

        try {
            jsonResponse = JSON.parse(text);
            console.log("Analyzed JSON:", JSON.stringify(jsonResponse, null, 2)); // Log for user visibility
        } catch (e) {
            console.error("Failed to parse LLM JSON", text);
            return res.status(500).json({ error: "LLM Response invalid JSON", raw: text });
        }

        // 4. Save to DB
        db.serialize(() => {
            const stmtRun = db.prepare("INSERT INTO scoring_runs (file_name, status, llm_model, total_score, project_summary_json) VALUES (?, ?, ?, ?, ?)");

            // Store both project_summary and deal_terms in the JSON column to avoid schema change
            const combinedData = {
                project_golden_summary: jsonResponse.project_golden_summary,
                deal_terms: jsonResponse.deal_terms
            };

            stmtRun.run(originalName, 'completed', modelName, jsonResponse.run_summary.total_score, JSON.stringify(combinedData), function (err) {
                if (err) {
                    console.error("DB Insert Run Error", err);
                    return; // TODO: handle error
                }
                const runId = this.lastID;

                const stmtResult = db.prepare("INSERT INTO scoring_results (run_id, item_id, extracted_value, evidence_text, score_raw, notes) VALUES (?, ?, ?, ?, ?, ?)");

                // Map item_key to ID
                const itemMap = {};
                items.forEach(i => itemMap[i.item_key] = i.id);

                jsonResponse.items.forEach(resItem => {
                    const itemId = itemMap[resItem.item_key];
                    if (itemId) {
                        stmtResult.run(runId, itemId, resItem.extracted_value, resItem.evidence_text, resItem.score_raw, resItem.notes);
                    }
                });
                stmtResult.finalize();

                res.json({ runId, ...jsonResponse });
            });
            stmtRun.finalize();
        });

    } catch (error) {
        console.error("!!! Analysis processing failed !!!");
        console.error(error);
        res.status(500).json({ error: error.message, details: error.toString() });
    }
});

app.get('/api/im/run/:id', (req, res) => {
    const runId = req.params.id;
    db.get("SELECT * FROM scoring_runs WHERE id = ?", [runId], (err, run) => {
        if (err || !run) return res.status(404).json({ error: 'Run not found' });

        db.all(`
            SELECT r.*, i.item_key, i.item_name, i.module_id, m.module_name 
            FROM scoring_results r
            JOIN scoring_items i ON r.item_id = i.id
            JOIN scoring_modules m ON i.module_id = m.id
            WHERE r.run_id = ?
        `, [runId], (err, results) => {
            if (err) return res.status(500).json({ error: err.message });

            const savedJson = JSON.parse(run.project_summary_json || '{}');

            // Handle backward compatibility (if savedJson is just the summary array/object vs the new combined object)
            const projectSummary = savedJson.project_golden_summary || savedJson;
            const dealTerms = savedJson.deal_terms || null;

            res.json({
                run: {
                    ...run,
                    project_summary: projectSummary
                },
                results,
                deal_terms: dealTerms
            });
        });
    });
});

// --- Screening Criteria CRUD ---

app.get('/api/screening-criteria', (req, res) => {
    db.all("SELECT * FROM screening_criteria ORDER BY sort_order ASC, id ASC", (err, rows) => {
        if (err) return res.status(500).json({ error: err.message });
        res.json(rows);
    });
});

app.post('/api/screening-criteria', (req, res) => {
    const { module, category, item, score_1, score_2, score_3, score_4, score_5, source } = req.body;
    if (!module || !category || !item) {
        return res.status(400).json({ error: 'module, category, item are required' });
    }
    db.run(
        `INSERT INTO screening_criteria (module, category, item, score_1, score_2, score_3, score_4, score_5, source, sort_order)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, (SELECT COALESCE(MAX(sort_order),0)+1 FROM screening_criteria))`,
        [module, category, item, score_1 || '', score_2 || '', score_3 || '', score_4 || '', score_5 || '', source || ''],
        function (err) {
            if (err) return res.status(500).json({ error: err.message });
            db.get("SELECT * FROM screening_criteria WHERE id = ?", [this.lastID], (err, row) => {
                if (err) return res.status(500).json({ error: err.message });
                res.json(row);
            });
        }
    );
});

app.put('/api/screening-criteria/:id', (req, res) => {
    const { module, category, item, score_1, score_2, score_3, score_4, score_5, source } = req.body;
    db.run(
        `UPDATE screening_criteria SET module=?, category=?, item=?, score_1=?, score_2=?, score_3=?, score_4=?, score_5=?, source=?, updated_at=CURRENT_TIMESTAMP WHERE id=?`,
        [module, category, item, score_1 || '', score_2 || '', score_3 || '', score_4 || '', score_5 || '', source || '', req.params.id],
        function (err) {
            if (err) return res.status(500).json({ error: err.message });
            if (this.changes === 0) return res.status(404).json({ error: 'Not found' });
            db.get("SELECT * FROM screening_criteria WHERE id = ?", [req.params.id], (err, row) => {
                if (err) return res.status(500).json({ error: err.message });
                res.json(row);
            });
        }
    );
});

app.delete('/api/screening-criteria/:id', (req, res) => {
    db.run("DELETE FROM screening_criteria WHERE id = ?", [req.params.id], function (err) {
        if (err) return res.status(500).json({ error: err.message });
        if (this.changes === 0) return res.status(404).json({ error: 'Not found' });
        res.json({ success: true, id: parseInt(req.params.id) });
    });
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
