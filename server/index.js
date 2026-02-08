
const path = require('path');
require('dotenv').config({
    path: path.resolve(__dirname, '..', '.env.local') // C:\dev\newwave\.env.local
});
const express = require('express');
const multer = require('multer');
const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const { GoogleGenerativeAI } = require('@google/generative-ai');
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

// Gemini Setup
const apiKey = process.env.GEMINI_API_KEY;
if (!apiKey) {
    throw new Error("Missing GEMINI_API_KEY. Check .env.local in project root");
}
const genAI = new GoogleGenerativeAI(apiKey);
// NOTE: Make sure GEMINI_API_KEY is in .env or passed via environment

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

        // 3. Call Gemini
        const modelName = process.env.GEMINI_MODEL || "gemini-2.5-flash";
        const model = genAI.getGenerativeModel({ model: modelName });
        const prompt = `
당신은 숙련된 투자심사역(Investment Analyst)입니다.
아래에 제공된 투자설명서(IM, Investment Memorandum) 텍스트를 분석하여, 주어진 평가 항목(scoring items)에 따라 정량·정성 평가를 수행하세요.

⚠️ 매우 중요:
- 모든 서술, 요약, 코멘트, 설명은 **반드시 한국어로만 작성**하세요.
- JSON의 **속성명(key)은 절대로 변경하지 마세요.**
- 마크다운, 설명 문장, 여분의 텍스트 없이 **JSON만 출력**하세요.

---

[평가 항목 / Scoring Items]
${scoringPrompt}

---

[추가로 반드시 추출해야 하는 Deal Terms — 누락 금지]
아래 5개 항목을 IM 본문에서 “정확히” 찾아서 출력하세요.
- PROJECT_NAME: 첫장 제목에 명시된 Project명 문장 그대로
- BORROWER: 차주(또는 SPC) 법인명
- SPONSOR: Sponsor/투자자/PE 운용사 명칭
- DEALSIZE: 본건 인수금융/리파이낸싱 총 조달금액(통화/단위 포함)
- TARGET_EQUITY: 대상회사(또는 담보 지분)의 자기자본가치/지분가치/Equity Value
  - 문서에 여러 값(예: Min/Avg/Max, DCF/Trading/Transaction 등)이 있으면
    1) “대표값(가능하면 Average 또는 문서가 ‘평균’이라 명시한 값)”을 extracted_value에 넣고,
    2) evidence_text에 근거 문장(표/문장)을 그대로 인용하며,
    3) notes에 “어떤 기준(DCF/Trading/Transaction 등)에서 어떤 값들을 봤는지” 요약하세요.
  - IM에 TARGET_EQUITY가 명확히 없으면 extracted_value는 "N/A"로, notes에 "IM 내 명시값 없음"을 쓰고,
    evidence_text는 "N/A"로 두세요. (절대 임의 추정 금지)

---

[분석 작업 지시]
1. IM 본문에서 각 평가 항목(item_key)에 해당하는 **구체적인 수치, 문장, 근거**를 추출하세요.
2. 추출한 근거를 바탕으로 각 항목에 대해 **1~5점 수준의 score_raw**를 부여하세요.
3. 점수 산정 사유 및 판단 근거는 **논리적으로 한국어로 설명**하세요.
4. 전체 투자 건에 대해 아래 3가지 관점에서 핵심 요약을 작성하세요.
   - Industry (산업 개요 및 매력도)
   - Deal Structure (거래 구조 및 자금 조달 방식)
   - Risk (주요 리스크 및 완화 요인)
5. evidence_text는 반드시 문자열(string) 1개여야 하며, 근거가 여러 개면
   " / " 로 한 문장에 합치며 배열로 만들면 안됨

---

[분석 대상 IM 텍스트]
${extractedText.substring(0, 30000)}
(※ 길이 제한으로 일부가 잘릴 수 있음)

---

[출력 형식 규칙 — 반드시 준수]
- 아래 JSON 구조를 **그대로 유지**
- 모든 값(value)은 **한국어**
- 따옴표로 감싸진 **유효한 JSON**만 출력

{
  "run_summary": {
    "file_name": "${originalName}",
    "overall_comment": "본 투자건에 대한 종합적인 한국어 평가 요약",
    "total_score": 0
  },

  "deal_terms": {
    "PROJECT_INFO": {
      "extracted_value": "프로젝트 설명",
      "evidence_text": "IM 원문에서 프로젝트 설명 너가 한줄로 간단히 요약",
      "notes": "투자 설명서(IM)의 Deal개요를 간략하게 한 줄 요약 (한국어)"
    },
    "PROJECT_NAME": {
      "extracted_value": "프로젝트명",
      "evidence_text": "첫장 제목에 명시된 Project명 문장 그대로 ",
      "notes": "투자 설명서(IM)의 전체 내용을 간략하게 한 줄 요약 (한국어)"
    },
    "BORROWER": {
      "extracted_value": "차주(또는 SPC) 법인명",
      "evidence_text": "IM 원문에서 차주/차주 혹은 SPC를 명시한 문장 그대로, 괄호()안의 내용은 제외",
      "notes": "어떤 문맥에서 차주로 정의되었는지 간단 설명 (한국어)"
    },
    "SPONSOR": {
      "extracted_value": "Sponsor/투자자 명칭",
      "evidence_text": "IM 원문에서 Sponsor/투자자를 명시한 문장 그대로",
      "notes": "Sponsor의 역할(예: 인수 주체/PE 등) 간단 설명 (한국어)"
    },
    "DEALSIZE": {
      "extracted_value": "총 조달금액(단위 포함, 예: 6,850억원)",
      "evidence_text": "IM 원문에서 총 금액을 명시한 문장 그대로",
      "notes": "Tr.A/Tr.B 등 구성 요약 (한국어)"
    },
    "TARGET_EQUITY": {
      "extracted_value": "대상회사/담보 지분의 Equity Value 대표값 (없으면 N/A)",
      "evidence_text": "IM 원문에서 Equity Value/지분가치/자기자본가치를 명시한 문장 또는 표 설명 그대로 (없으면 N/A)",
      "notes": "평가 방법(DCF/Trading/Transaction 등)과 대표값 선택 근거 요약. 없으면 'IM 내 명시값 없음' (한국어)"
    }
  },

  "items": [
    {
      "item_key": "DB에 존재하는 item_key와 정확히 일치",
      "extracted_value": "IM에서 추출한 수치 또는 핵심 내용",
      "evidence_text": "IM 원문에서 발췌한 한국어/영어 문장 그대로 인용 가능",
      "score_raw": 5,
      "score_weighted": 0,
      "notes": "점수 산정 사유 및 투자 관점에서의 해석 (한국어)"
    }
  ],

  "project_golden_summary": {
    "industry_overview_highlights": [
      "산업의 성장성, 시장 규모, 구조적 트렌드 요약"
    ],
    "deal_structure_financing_plan": [
      "지분 구조, 투자 방식, 자금 사용 계획 요약"
    ],
    "risk_factors_mitigation": [
      "핵심 리스크와 이에 대한 대응 또는 완화 가능성"
    ]
  }
}
`;


        const result = await model.generateContent({
            contents: [{ role: "user", parts: [{ text: prompt }] }],
            generationConfig: { responseMimeType: "application/json" }
        });

        const response = await result.response;
        let text = response.text();

        text = sanitizeJsonText(text);

        try {
            jsonResponse = JSON.parse(text);
            console.log("Analyzed JSON:", JSON.stringify(jsonResponse, null, 2)); // Log for user visibility
        } catch (e) {
            console.error("Failed to parse Gemini JSON", text);
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

            stmtRun.run(originalName, 'completed', 'gemini-pro', jsonResponse.run_summary.total_score, JSON.stringify(combinedData), function (err) {
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

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
