
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
    throw new Error("Missing GEMINI_API_KEY. Check C:\\dev\\newwave\\.env.local");
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
    const originalName = req.file.originalname;

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
아래에 제공된 투자설명서(IM, Investment Memorandum) 텍스트를 분석하여,
주어진 평가 항목(scoring items)에 따라 정량·정성 평가를 수행하세요.

⚠️ 매우 중요:
- 모든 서술, 요약, 코멘트, 설명은 **반드시 한국어로만 작성**하세요.
- JSON의 **속성명(key)은 절대로 변경하지 마세요.**
- 마크다운, 설명 문장, 여분의 텍스트 없이 **JSON만 출력**하세요.

---

[평가 항목 / Scoring Items]
${scoringPrompt}

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

        let jsonResponse;
        try {
            jsonResponse = JSON.parse(text);
        } catch (e) {
            console.error("Failed to parse Gemini JSON", text);
            return res.status(500).json({ error: "LLM Response invalid JSON", raw: text });
        }

        // 4. Save to DB
        db.serialize(() => {
            const stmtRun = db.prepare("INSERT INTO scoring_runs (file_name, status, llm_model, total_score, project_summary_json) VALUES (?, ?, ?, ?, ?)");
            stmtRun.run(originalName, 'completed', 'gemini-pro', jsonResponse.run_summary.total_score, JSON.stringify(jsonResponse.project_golden_summary), function (err) {
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

            res.json({
                run: {
                    ...run,
                    project_summary: JSON.parse(run.project_summary_json || '{}')
                },
                results
            });
        });
    });
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
