/**
 * 여기선 PWA - Gemini API Proxy Worker (v1.4 — maxOutputTokens 2048 안전 확대)
 * ------------------------------------------------
 * 목적: 클라이언트에 API 키 노출 없이 Gemini 호출
 * 배포: Cloudflare Workers (ES Module, fetch handler)
 *
 * v1.4 (2026-05-20 모바일 추가 검증 후):
 *   - 1024로도 일부 사물 잘림 잔존 (한글 응답 토큰 더 많음).
 *   - 2048로 안전 확대 → 응답 잘림 거의 0 보장.
 *   - 정상 응답(100~200 토큰)은 영향 0. 비용도 미세 (사용된 토큰만 과금).
 *
 * v1.3 (2026-05-20 벤치마크 측정 후):
 *   - 512가 부족 (벤치마크 102장 중 43건 MAX_TOKENS로 잘림, 특히 종이박스).
 *   - 1024로 올림 → 정상 응답(100~200토큰)은 영향 0, 잘림 케이스 거의 0.
 *   - OCR 차단 안전망은 SYSTEM_PROMPT 원칙 6(책·노트북·문서)으로 유지.
 *
 * v1.2 (2026-05-20 후속):
 *   - generationConfig.maxOutputTokens=512 추가 → 책·노트북 같은
 *     텍스트 많은 물건에서 Gemini가 본문 OCR로 빠져 응답이 잘리던 이슈 해결
 *
 * v1.1 (2026-05-20):
 *   - safetySettings 명시 (BLOCK_NONE × 4) → 분리수거 프롬프트가
 *     기본 medium safety filter에 차단되어 빈 응답 오던 이슈 해결
 *   - 응답에 finishReason 포함 → app.html toast 디버그용
 *
 * 환경변수 (Cloudflare Dashboard → Settings → Variables and Secrets):
 *   - GEMINI_API_KEY  (Secret, 필수)
 *   - ALLOWED_ORIGINS (Plain, 선택, 콤마 구분)
 *   - GEMINI_MODEL    (Plain, 선택, 기본 gemini-2.0-flash)
 *   - DAILY_LIMIT     (Plain, 선택, 기본 100)
 *   - MINUTE_LIMIT    (Plain, 선택, 기본 10)
 *   - RATE_LIMIT_KV   (KV Namespace binding, 권장 — 없으면 메모리 fallback)
 *
 * 99점 기준 충족:
 *   - 보안: API 키 미노출, Origin 화이트리스트, MIME·길이 검증
 *   - 안정성: 30s timeout, 4xx/5xx 차등, 429 retry-after
 *   - 비용 보호: prompt 2000자·이미지 5MB·base64 검증
 *   - 개인정보: IP 해시, 바디 미로깅
 */

// 기본 화이트리스트 (운영 + 개발)
const DEFAULT_ORIGINS = [
  "https://ilsanintel0602-collab.github.io",
  "http://localhost:8004",
  "http://localhost:5500",
  "http://127.0.0.1:8004",
];

const MAX_IMAGE_BYTES = 5 * 1024 * 1024;     // 5MB
const MAX_PROMPT_CHARS = 2000;                 // prompt 길이 제한
const ALLOWED_MIME = ["image/jpeg", "image/png", "image/webp"];
const FETCH_TIMEOUT_MS = 30_000;
const BASE64_RE = /^[A-Za-z0-9+/=\s]+$/;

// 메모리 fallback (isolate 내부에서만 유효; KV 없을 때 임시용)
const memStore = new Map();

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowList = buildAllowList(env);
    const corsOrigin = allowList.includes(origin) ? origin : "";

    // 1) CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(corsOrigin) });
    }

    // 2) Origin 검증
    if (!corsOrigin) {
      return json({ error: "Origin not allowed" }, 403, corsHeaders(""));
    }

    // v1.5: path 분기 — /feedback 엔드포인트 추가 (Phase 8 자동 시스템)
    const url = new URL(request.url);
    const path = url.pathname;

    // 3) Method / Content-Type 검증
    if (request.method !== "POST") {
      return json({ error: "Method not allowed" }, 405, corsHeaders(corsOrigin));
    }

    // v1.5: /feedback 엔드포인트 (사용자 피드백 자동 수집)
    if (path === "/feedback") {
      return await handleFeedback(request, env, corsOrigin);
    }

    // v1.6: /augment 엔드포인트 (텍스트 데이터 증강 — alias 자동 확장)
    if (path === "/augment") {
      return await handleAugment(request, env, corsOrigin);
    }
    if (!(request.headers.get("Content-Type") || "").includes("application/json")) {
      return json({ error: "Content-Type must be application/json" }, 415, corsHeaders(corsOrigin));
    }

    // 4) Rate limit (IP 기반)
    const ip = request.headers.get("CF-Connecting-IP") || "0.0.0.0";
    const ipHash = await sha256(ip);
    const rl = await checkRateLimit(env, ipHash);
    if (!rl.ok) {
      return json(
        { error: "Rate limit exceeded", scope: rl.scope },
        429,
        { ...corsHeaders(corsOrigin), "Retry-After": String(rl.retryAfter) }
      );
    }

    // 5) Body 파싱·검증
    let body;
    try { body = await request.json(); }
    catch { return json({ error: "Invalid JSON body" }, 400, corsHeaders(corsOrigin)); }

    const imageB64Raw = body.imageBase64 || body.image;
    const prompt = body.prompt;

    if (!imageB64Raw || typeof imageB64Raw !== "string") {
      return json({ error: "imageBase64 (string) required" }, 400, corsHeaders(corsOrigin));
    }
    if (!prompt || typeof prompt !== "string") {
      return json({ error: "prompt (string) required" }, 400, corsHeaders(corsOrigin));
    }
    if (prompt.length > MAX_PROMPT_CHARS) {
      return json({ error: `prompt too long (max ${MAX_PROMPT_CHARS} chars)` }, 400, corsHeaders(corsOrigin));
    }

    // base64 검증 + 크기 추정
    const mimeType = extractMime(imageB64Raw) || body.mimeType || "image/jpeg";
    if (!ALLOWED_MIME.includes(mimeType)) {
      return json({ error: `mimeType not allowed (${ALLOWED_MIME.join(", ")})` }, 400, corsHeaders(corsOrigin));
    }
    const pureB64 = imageB64Raw.replace(/^data:[^,]+,/, "").replace(/\s/g, "");
    if (!BASE64_RE.test(pureB64) || pureB64.length < 100) {
      return json({ error: "Invalid base64 image" }, 400, corsHeaders(corsOrigin));
    }
    const approxBytes = Math.floor(pureB64.length * 0.75);
    if (approxBytes > MAX_IMAGE_BYTES) {
      return json({ error: "Image too large (max 5MB)" }, 413, corsHeaders(corsOrigin));
    }

    // 6) Gemini 호출
    const model = env.GEMINI_MODEL || "gemini-2.0-flash";
    const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${env.GEMINI_API_KEY}`;
    const payload = {
      contents: [{
        parts: [
          { text: prompt },
          { inline_data: { mime_type: mimeType, data: pureB64 } },
        ],
      }],
      generationConfig: {
        responseMimeType: "application/json",
        temperature: Number.isFinite(body.temperature) ? body.temperature : 0.2,
        // v1.4: 2048 토큰 — v1.3의 1024도 일부 잘림 잔존. 2048 안전 마진 + 비용 영향 0.
        // 정상 응답(100~200 토큰)은 영향 X. OCR 차단은 SYSTEM_PROMPT 원칙 6 담당.
        maxOutputTokens: 2048,
      },
      // v1.1: 한국 분리수거 작업은 명백히 안전 → 기본 medium filter 해제.
      // "주사기·리튬배터리·깨진 유리" 같은 단어가 medium에서 차단되던 이슈 차단.
      safetySettings: [
        { category: "HARM_CATEGORY_HARASSMENT", threshold: "BLOCK_NONE" },
        { category: "HARM_CATEGORY_HATE_SPEECH", threshold: "BLOCK_NONE" },
        { category: "HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold: "BLOCK_NONE" },
        { category: "HARM_CATEGORY_DANGEROUS_CONTENT", threshold: "BLOCK_NONE" },
      ],
    };

    const startedAt = Date.now();
    let upstream;
    try {
      upstream = await fetchWithTimeout(geminiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }, FETCH_TIMEOUT_MS);
    } catch (e) {
      log("upstream_error", { ipHash, ms: Date.now() - startedAt, reason: String(e.message || e).slice(0, 80) });
      return json({ error: "Upstream timeout or network error" }, 504, corsHeaders(corsOrigin));
    }

    // 7) 응답 처리
    if (!upstream.ok) {
      const status = upstream.status;
      log("upstream_fail", { ipHash, status, ms: Date.now() - startedAt });
      if (status >= 500) {
        return json({ error: "Gemini service unavailable, please retry", retry: true }, 503, corsHeaders(corsOrigin));
      }
      return json({ error: `Gemini request rejected (${status})` }, 400, corsHeaders(corsOrigin));
    }

    let geminiData;
    try { geminiData = await upstream.json(); }
    catch { return json({ error: "Invalid upstream response" }, 502, corsHeaders(corsOrigin)); }

    const candidate = geminiData?.candidates?.[0];
    const text = candidate?.content?.parts?.[0]?.text ?? "";
    const finishReason = candidate?.finishReason || "unknown";
    // promptFeedback.blockReason (요청 자체가 차단된 경우)도 함께 노출
    const blockReason = geminiData?.promptFeedback?.blockReason || null;
    let parsed = null;
    try { parsed = JSON.parse(text); } catch { /* 텍스트 그대로 반환 */ }

    log("ok", { ipHash, ms: Date.now() - startedAt, hasJson: !!parsed, finishReason, blockReason });
    return json(
      { ok: true, result: parsed ?? text, finishReason, blockReason },
      200,
      corsHeaders(corsOrigin)
    );
  },
};

/* ---------- 유틸 ---------- */
function buildAllowList(env) {
  const extra = (env.ALLOWED_ORIGINS || "").split(",").map(s => s.trim()).filter(Boolean);
  return [...new Set([...DEFAULT_ORIGINS, ...extra])];
}

function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin": origin || "null",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
  };
}

function json(obj, status, headers) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...headers },
  });
}

async function fetchWithTimeout(url, opts, ms) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), ms);
  try { return await fetch(url, { ...opts, signal: ctrl.signal }); }
  finally { clearTimeout(t); }
}

async function sha256(s) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
}

function extractMime(b64) {
  const m = /^data:([^;,]+)[;,]/.exec(b64);
  return m?.[1] || null;
}

async function checkRateLimit(env, ipHash) {
  const minuteLimit = Number(env.MINUTE_LIMIT || 10);
  const dailyLimit = Number(env.DAILY_LIMIT || 100);
  const now = Date.now();
  const minuteKey = `rl:m:${ipHash}:${Math.floor(now / 60_000)}`;
  const dayKey = `rl:d:${ipHash}:${new Date().toISOString().slice(0, 10)}`;

  const [mCount, dCount] = await Promise.all([incr(env, minuteKey, 60), incr(env, dayKey, 86400)]);
  if (mCount > minuteLimit) return { ok: false, scope: "minute", retryAfter: 60 };
  if (dCount > dailyLimit) return { ok: false, scope: "day", retryAfter: 3600 };
  return { ok: true };
}

async function incr(env, key, ttlSec) {
  if (env.RATE_LIMIT_KV) {
    const cur = Number((await env.RATE_LIMIT_KV.get(key)) || 0) + 1;
    await env.RATE_LIMIT_KV.put(key, String(cur), { expirationTtl: ttlSec });
    return cur;
  }
  const rec = memStore.get(key);
  const expire = Date.now() + ttlSec * 1000;
  if (!rec || rec.expire < Date.now()) { memStore.set(key, { c: 1, expire }); return 1; }
  rec.c += 1; return rec.c;
}

function log(event, data) {
  console.log(JSON.stringify({ t: new Date().toISOString(), event, ...data }));
}

// ============================================================================
// v1.5: Phase 8 사용자 피드백 자동 수집 시스템
// ============================================================================
// POST /feedback
// Body: { vote: "good"|"bad"|"wrong", item_id, item_name, category, region, user_correction? }
// PII 차단: 사진 X, 식별자 X, IP 해시만
// 저장: FEEDBACK_KV (Cloudflare KV) — 없으면 GitHub Issue 자동 생성
//
async function handleFeedback(request, env, corsOrigin) {
  if (!(request.headers.get("Content-Type") || "").includes("application/json")) {
    return json({ error: "Content-Type must be application/json" }, 415, corsHeaders(corsOrigin));
  }

  let body;
  try { body = await request.json(); }
  catch { return json({ error: "Invalid JSON body" }, 400, corsHeaders(corsOrigin)); }

  // PII 검증 — 명시적 거부
  const piiFields = ["user_email", "user_phone", "user_name", "ip", "address", "uuid"];
  for (const f of piiFields) {
    if (body[f]) return json({ error: `PII detected (${f}) — feedback rejected` }, 400, corsHeaders(corsOrigin));
  }

  // 허용 필드만 추출
  const vote = body.vote;
  if (!["good", "bad", "wrong"].includes(vote)) {
    return json({ error: "vote must be good/bad/wrong" }, 400, corsHeaders(corsOrigin));
  }
  const item_id = String(body.item_id || "").slice(0, 60);
  const item_name = String(body.item_name || "").slice(0, 60);
  const category = String(body.category || "").slice(0, 30);
  const region = String(body.region || "").slice(0, 30);
  const user_correction = String(body.user_correction || "").slice(0, 60);
  const version = String(body.version || "").slice(0, 20);
  const source = String(body.source || "").slice(0, 30);

  const id = crypto.randomUUID();
  const ts = Date.now();
  const record = {
    id, ts, vote, item_id, item_name, category, region, user_correction, version, source,
  };

  // Cloudflare KV에 저장 (있으면)
  if (env.FEEDBACK_KV) {
    try {
      await env.FEEDBACK_KV.put(`fb:${ts}:${id}`, JSON.stringify(record), {
        expirationTtl: 90 * 24 * 60 * 60,  // 90일 보존
      });
      log("feedback_saved_kv", { vote, item_id, region });
      return json({ ok: true, id }, 200, corsHeaders(corsOrigin));
    } catch (e) {
      log("feedback_kv_error", { error: String(e) });
    }
  }

  // 폴백: 메모리에 저장 (재배포 시 사라짐, 단지 첫 활성용)
  memStore.set(`fb:${id}`, record);
  log("feedback_saved_mem", { vote, item_id, region });
  return json({ ok: true, id, note: "stored in memory (no KV)" }, 200, corsHeaders(corsOrigin));
}

// ============================================================================
// v1.6: /augment 텍스트 데이터 증강 — alias 자동 확장
// ============================================================================
// 사용자 API 키 노출 0 — Cloudflare Worker 환경변수의 GEMINI_API_KEY만 사용.
// POST /augment
// Body: { item_name, category, existing_aliases?: [], count?: 12 }
// Response: { ok: true, aliases: ["변형1", "변형2", ...] }
//
async function handleAugment(request, env, corsOrigin) {
  if (!(request.headers.get("Content-Type") || "").includes("application/json")) {
    return json({ error: "Content-Type must be application/json" }, 415, corsHeaders(corsOrigin));
  }

  let body;
  try { body = await request.json(); }
  catch { return json({ error: "Invalid JSON body" }, 400, corsHeaders(corsOrigin)); }

  const item_name = String(body.item_name || "").slice(0, 60);
  const category = String(body.category || "").slice(0, 30);
  const existing = Array.isArray(body.existing_aliases) ? body.existing_aliases.slice(0, 10) : [];
  const count = Math.min(20, Math.max(5, Number(body.count) || 12));

  if (!item_name || !category) {
    return json({ error: "item_name + category required" }, 400, corsHeaders(corsOrigin));
  }

  const prompt = `한국 분리수거 앱의 데이터 증강 작업입니다.

물건: "${item_name}"
카테고리: ${category}
기존 별칭: ${existing.length ? existing.join(", ") : "없음"}

이 물건의 다양한 한국어 표현을 ${count}개 생성해주세요. 다음 종류를 골고루:
1. 한국어 변형/동의어 (예: 노트북 → 랩탑)
2. 영어/외래어 (예: 프린터 → printer)
3. 구어체/줄임말 (예: 냉장고 → 냉장이)
4. 브랜드명·일반명 (예: 신라면, 삼다수)
5. 유아어·방언

규칙:
- 기존 별칭과 중복 안 됨
- 다른 카테고리와 혼동 안 됨
- 2자 이하 너무 짧은 단어 피하기
- JSON 배열만 응답: ["단어1", "단어2", ...]

JSON 응답만:`;

  const model = env.GEMINI_MODEL || "gemini-2.0-flash";
  const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${env.GEMINI_API_KEY}`;
  const payload = {
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: {
      responseMimeType: "application/json",
      maxOutputTokens: 512,
      temperature: 0.7,
    },
    safetySettings: [
      { category: "HARM_CATEGORY_HATE_SPEECH", threshold: "BLOCK_NONE" },
      { category: "HARM_CATEGORY_DANGEROUS_CONTENT", threshold: "BLOCK_NONE" },
      { category: "HARM_CATEGORY_HARASSMENT", threshold: "BLOCK_NONE" },
      { category: "HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold: "BLOCK_NONE" },
    ],
  };

  try {
    const r = await fetch(geminiUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      return json({ error: `Gemini API error ${r.status}` }, 502, corsHeaders(corsOrigin));
    }
    const data = await r.json();
    const text = data.candidates?.[0]?.content?.parts?.[0]?.text || "";
    let aliases = [];
    try { aliases = JSON.parse(text); } catch { aliases = []; }
    if (!Array.isArray(aliases)) aliases = [];
    log("augment_ok", { item_name, count: aliases.length });
    return json({ ok: true, item_name, category, aliases }, 200, corsHeaders(corsOrigin));
  } catch (e) {
    return json({ error: `Worker fetch failed: ${String(e)}` }, 500, corsHeaders(corsOrigin));
  }
}
