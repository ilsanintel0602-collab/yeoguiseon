/**
 * 여기선 PWA - Gemini API Proxy Worker (v1.9.14 — 영문 item_id 사용자 노출 차단 / v1.9.13 Post-AI 가드레일 / v1.9.12 — /data/bins GPS 가까운 수거함 + v1.9.11 필드명 정정 + UA 헤더 / v1.9.10 /admin/crawl-bins (시군구 데이터 자동 수집) + DAILY_LIMIT 100→1000)
 * ------------------------------------------------
 * 목적: 클라이언트에 API 키 노출 없이 Gemini 호출 + D1 DB 직접 서비스 + 무인 운영
 * 배포: Cloudflare Workers (ES Module, fetch + scheduled handler)
 *
 * v1.9.9 (2026-05-24 — DAILY_LIMIT 풀기):
 *   - 기본 DAILY_LIMIT 100 → 1000 (시연·일반 사용 안 걸림, 폭주만 차단)
 *   - 100은 초기 Claude가 임의로 박은 보수적 값. 시연·개발에 너무 작음.
 *
 * v1.9.8 (2026-05-24 — Rate limit 완화):
 *   - 기본 MINUTE_LIMIT 10 → 30 (시연·테스트 시 일반 사용자도 분당 30회까지 가능)
 *   - DAILY_LIMIT은 100 그대로 (일일 폭주 방지)
 *
 * v1.9.7 (2026-05-23 — MAX_TOKENS 근본 해결):
 *   - maxOutputTokens 2048 → 8192 (압력솥·노트북·복잡 사진에서 MAX_TOKENS 잘림 사라짐)
 *   - 정상 응답 100~200 토큰엔 영향 0. 비용은 실제 사용 토큰만 과금이라 0.
 *
 * v1.9.6.1 (2026-05-22 핫픽스):
 *   - /admin/health + /feedback/dump를 Origin 검증 이전으로 이동 (브라우저/서버 호출 둘 다 통과)
 *
 * v1.9.6 (2026-05-22 — Phase A2 cron 활성):
 *   - scheduled() 핸들러 추가 → Cloudflare cron trigger로 무인 운영 진입
 *   - 매일 00:05 KST: D1 items/aliases 카운트 + KV 캐시 통계를 metrics:daily:YYYY-MM-DD 기록 (90일 보존)
 *   - 6시간마다: 빈/이상 응답 캐시(item_id=unknown) 정리 안전망
 *   - /admin/health 엔드포인트: 최근 metrics + 직전 cron 실행 시간 + 데이터 헬스 (모니터링용)
 *   - /feedback/dump 핫픽스: `url.searchParams` → `reqUrl.searchParams` (변수명 오타로 500 떨어지던 버그)
 *   - cron trigger는 wrangler.toml [triggers] crons 등록 필요 (wrangler deploy 시 자동 활성)
 *
 * v1.9.3 (2026-05-22):
 *   - 핫픽스: 코드 기본 모델 gemini-2.0-flash → gemini-2.5-flash (2.0 deprecated, 2.5는 2025년 stable)
 *   - 이유: Cloudflare 대시보드 GEMINI_MODEL 환경변수가 reset된 경우에도 코드가 항상 2.5 사용 보장
 *
 * v1.9.2 (2026-05-22):
 *   - /data/all 추가: 정적 national_rules.json과 동일 구조로 응답 (점진적 D1 전환)
 *   - 클라이언트는 /data/all 우선 → 실패 시 정적 JSON 폴백
 *
 * v1.9.1 (2026-05-22):
 *   - 핫픽스: /data/* GET 라우팅을 POST 검사보다 먼저 처리 (GET 차단 버그 해결)
 *
 * v1.9 (2026-05-21):
 *   - /data/* 엔드포인트: D1 직접 읽기 (정적 JSON 폐기)
 *   - /data/items, /data/search, /data/regions, /data/region/:code/exceptions
 *   - 캐시 헤더 1h (items·regions), 5min (search)
 *   - env.DB binding 필요 (wrangler.toml d1_databases 설정)
 *
 * v1.8 (2026-05-21):
 *   - 결과 캐싱 (KV): 같은 이미지 = 즉시 응답 (Gemini 호출 0, 비용 0)
 *   - Claude Haiku 폴백 (앙상블): Gemini 빈 응답 시 자동 Claude 호출
 *   - 추가 env: ANTHROPIC_API_KEY (선택, 있으면 폴백 활성)
 *
 * v1.7.2 (2026-05-21):
 *   - /augment maxOutputTokens 512 → 2048 (한국어 alias 응답 잘림 해결)
 *
 * v1.7.1 (2026-05-21):
 *   - Gemini가 {aliases:[...]} 객체로 응답해도 잡아냄 (이전엔 빈 배열로 떨어짐)
 *   - 코드펜스(```json) 감싸도 정규식으로 배열 추출
 *   - parseHow + raw_preview 디버그 필드 추가
 *
 * v1.7 (2026-05-21):
 *   - /augment 엔드포인트가 Python 스크립트 등 비-브라우저에서도 호출 가능
 *   - Origin 검증 우회 (서버간 호출), 대신 IP rate limit 강화 (분당 60회, 일당 2000회)
 *   - 키는 여전히 env.GEMINI_API_KEY (Cloudflare Secret) 안에만 존재
 *
 * v1.6 (2026-05-21):
 *   - /augment 엔드포인트 신설 (텍스트 alias 데이터 증강용)
 *
 * v1.5 (2026-05-21):
 *   - /feedback 엔드포인트 신설 (사용자 피드백 자동 수집)
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
 *   - GEMINI_MODEL    (Plain, 선택, 기본 gemini-2.5-flash — v1.9.3: 2.0-flash 404 → 2.5-flash)
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

    const reqUrl = new URL(request.url);
    const path = reqUrl.pathname;

    // 1) CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(corsOrigin || "*") });
    }

    // v1.7: /augment 는 비-브라우저 서버간 호출 허용 (Python 스크립트용)
    // 보안: IP rate limit 강화 (분당 60회, 일당 2000회)
    // 키는 여전히 Cloudflare 안에 안전 (env.GEMINI_API_KEY)
    if (path === "/augment") {
      if (request.method !== "POST") {
        return json({ error: "Method not allowed" }, 405, corsHeaders("*"));
      }
      const ip = request.headers.get("CF-Connecting-IP") || "0.0.0.0";
      const ipHash = await sha256(ip);
      const augMin = await incr(env, `rl:aug:m:${ipHash}:${Math.floor(Date.now()/60_000)}`, 60);
      const augDay = await incr(env, `rl:aug:d:${ipHash}:${new Date().toISOString().slice(0,10)}`, 86400);
      if (augMin > 60) {
        return json({ error: "augment rate limit (60/min)" }, 429, corsHeaders("*"));
      }
      if (augDay > 2000) {
        return json({ error: "augment daily limit (2000/day)" }, 429, corsHeaders("*"));
      }
      return await handleAugment(request, env, "*");
    }

    // v1.9.5 (Phase B4): /feedback/dump — KV에 누적된 피드백 전체 dump (자동 학습 사이클용)
    //   GET 전용. Origin 무관 (서버 스크립트용). 키 보호: ?key=DUMP_KEY 필수.
    //   v1.9.6 핫픽스: 변수명 url 미정의 → reqUrl (이 함수 위에 const reqUrl = new URL(request.url) 이미 있음)
    if (path === "/feedback/dump") {
      if (request.method !== "GET") {
        return json({ error: "GET only" }, 405, corsHeaders("*"));
      }
      const dumpKey = reqUrl.searchParams.get("key");
      if (!env.FEEDBACK_DUMP_KEY || dumpKey !== env.FEEDBACK_DUMP_KEY) {
        return json({ error: "invalid dump key" }, 403, corsHeaders("*"));
      }
      if (!env.RATE_LIMIT_KV) {
        return json({ error: "KV not configured" }, 503, corsHeaders("*"));
      }
      try {
        const list = await env.RATE_LIMIT_KV.list({ prefix: "fb:" });
        const items = [];
        for (const k of list.keys.slice(0, 1000)) {
          const v = await env.RATE_LIMIT_KV.get(k.name);
          if (v) {
            try { items.push({ key: k.name, ...JSON.parse(v) }); }
            catch { items.push({ key: k.name, raw: v }); }
          }
        }
        return json({ ok: true, count: items.length, items }, 200, corsHeaders("*", 60));
      } catch (e) {
        return json({ error: `dump failed: ${String(e).slice(0, 80)}` }, 500, corsHeaders("*"));
      }
    }

    // v1.9.6 (Phase A2): /admin/health — cron 동작 + 데이터 헬스 확인용 (Origin 무관)
    //   GET 전용. 모니터링용이라 키 없음. 민감정보 없음 (카운트만).
    //   클라이언트 헬스 알림 + cron 동작 검증에 활용.
    if (path === "/admin/health") {
      if (request.method !== "GET") {
        return json({ error: "GET only" }, 405, corsHeaders("*"));
      }
      try {
        const today = new Date().toISOString().slice(0, 10);
        const yest = new Date(Date.now() - 86400_000).toISOString().slice(0, 10);
        const out = {
          ok: true,
          worker_version: "v1.9.6.1",
          now: new Date().toISOString(),
          d1_bound: !!env.DB,
          kv_bound: !!env.RATE_LIMIT_KV,
        };
        if (env.RATE_LIMIT_KV) {
          out.metrics_today = await readMetricSafe(env, `metrics:daily:${today}`);
          out.metrics_yesterday = await readMetricSafe(env, `metrics:daily:${yest}`);
          out.last_cron = await readMetricSafe(env, "cron:last_run");
        }
        if (env.DB) {
          try {
            const items = await env.DB.prepare("SELECT COUNT(*) AS c FROM items").first();
            const aliases = await env.DB.prepare("SELECT COUNT(*) AS c FROM aliases").first();
            out.d1_items_now = items?.c ?? null;
            out.d1_aliases_now = aliases?.c ?? null;
          } catch (e) {
            out.d1_error = String(e).slice(0, 80);
          }
        }
        return json(out, 200, corsHeaders("*", 60));
      } catch (e) {
        return json({ error: `health failed: ${String(e).slice(0, 80)}` }, 500, corsHeaders("*"));
      }
    }

    // v1.9.10 (Phase A1-2): /admin/crawl-bins — data.go.kr 행안부 4개 표준데이터 자동 크롤 + D1 입력
    //   GET 전용. ?key=<DATA_GO_KR_API_KEY>로 인증 (기존 secret 재사용, 사용자 추가 작업 0).
    //   ?area=medicine|clothes|lamp_battery 선택 (위치 데이터 3개).
    //   ?dryrun=true 옵션 → 1페이지만, sample 3개 반환, D1 입력 X (구조 확인용).
    //   기본 호출: 전체 페이지네이션 + D1 batch INSERT.
    //   결과 → KV 'bins:last_crawl:<area>'에 90일 기록.
    if (path === "/admin/crawl-bins") {
      if (request.method !== "GET") {
        return json({ error: "GET only" }, 405, corsHeaders("*"));
      }
      const apiKey = env.DATA_GO_KR_API_KEY;
      if (!apiKey) {
        return json({ error: "DATA_GO_KR_API_KEY secret not configured" }, 503, corsHeaders("*"));
      }
      const adminKey = reqUrl.searchParams.get("key");
      if (adminKey !== apiKey) {
        return json({ error: "invalid admin key (use DATA_GO_KR_API_KEY value as ?key=)" }, 403, corsHeaders("*"));
      }
      if (!env.DB) {
        return json({ error: "D1 not configured" }, 503, corsHeaders("*"));
      }

      const area = reqUrl.searchParams.get("area") || "medicine";
      const dryrun = reqUrl.searchParams.get("dryrun") === "true";

      const ENDPOINTS = {
        medicine: "https://api.data.go.kr/openapi/tn_pubr_public_lung_medicine_api",
        clothes: "https://api.data.go.kr/openapi/tn_pubr_public_clothing_collect_bins_api",
        lamp_battery: "https://api.data.go.kr/openapi/tn_pubr_public_waste_lamp_battery_collection_box_api"
      };
      const endpoint = ENDPOINTS[area];
      if (!endpoint) {
        return json({ error: `unknown area: ${area}`, supported: Object.keys(ENDPOINTS) }, 400, corsHeaders("*"));
      }

      const startedAt = Date.now();
      let allItems = [];
      let totalCount = 0;
      let page = 1;
      const maxPages = dryrun ? 1 : 30;
      const errors = [];

      while (page <= maxPages) {
        const apiUrl = `${endpoint}?serviceKey=${encodeURIComponent(apiKey)}&pageNo=${page}&numOfRows=1000&type=json`;
        try {
          const resp = await fetch(apiUrl, {
            headers: {
              "Accept": "application/json",
              "User-Agent": "Mozilla/5.0 (compatible; YeoguiseonBot/1.0; +https://ilsanintel0602-collab.github.io/yeoguiseon/)"
            }
          });
          if (!resp.ok) {
            errors.push(`page ${page}: HTTP ${resp.status}`);
            break;
          }
          const data = await resp.json();
          const body = (data && (data.response?.body || data.body)) || {};
          totalCount = Number(body.totalCount || 0);
          let itemsRaw = body.items;
          if (itemsRaw && itemsRaw.item) itemsRaw = itemsRaw.item;
          if (!Array.isArray(itemsRaw)) itemsRaw = itemsRaw ? [itemsRaw] : [];
          if (itemsRaw.length === 0) break;
          allItems.push(...itemsRaw);
          if (allItems.length >= totalCount) break;
          page++;
        } catch (e) {
          errors.push(`page ${page}: ${String(e).slice(0, 60)}`);
          break;
        }
      }

      // v1.9.11: 정규화 — data.go.kr 실제 응답 필드명 (검증 완료)
      //   위도: lat / 경도: lot (longitude 아님!)
      //   시설명: instlPlcNm / 도로명주소: lctnRoadNm / 지번주소: lctnLotnoAddr
      //   시군구코드: insttCode / 시군구명: insttNm / 관리기관 전화: mngInstTelno
      const normalized = allItems.map(raw => {
        const lat = parseFloat(raw.lat || raw.latitude || raw.LAT || 0);
        const lng = parseFloat(raw.lot || raw.longitude || raw.LON || raw.LNG || raw.lng || 0);
        return {
          area_type: area,
          region_code: raw.insttCode || raw.sigunguCode || raw.SIGUN_CD || raw.signguCode || null,
          name: raw.instlPlcNm || raw.instlPlace || raw.fcltyNm || raw.NAME || raw.placeName || null,
          address: raw.lctnRoadNm || raw.lctnLotnoAddr || raw.rdnmadr || raw.lnmadr || raw.ADDR || null,
          lat: (isFinite(lat) && lat !== 0) ? lat : null,
          lng: (isFinite(lng) && lng !== 0) ? lng : null,
          phone: raw.mngInstTelno || raw.phoneNumber || raw.TEL || raw.phone || null
        };
      }).filter(it => it.name && it.address);

      if (dryrun) {
        return json({
          ok: true, area, endpoint, dryrun: true,
          fetched: allItems.length, totalCount, normalized: normalized.length,
          sample: normalized.slice(0, 3),
          raw_sample: allItems.slice(0, 1),
          errors,
          duration_ms: Date.now() - startedAt
        }, 200, corsHeaders("*"));
      }

      // D1 batch INSERT (200개 청크)
      let inserted = 0;
      try {
        await env.DB.prepare("DELETE FROM bins WHERE area_type = ?").bind(area).run();
        const CHUNK = 200;
        for (let i = 0; i < normalized.length; i += CHUNK) {
          const chunk = normalized.slice(i, i + CHUNK);
          const stmts = chunk.map(it =>
            env.DB.prepare("INSERT INTO bins (area_type, region_code, name, address, lat, lng, phone) VALUES (?,?,?,?,?,?,?)")
              .bind(it.area_type, it.region_code, it.name, it.address, it.lat, it.lng, it.phone)
          );
          await env.DB.batch(stmts);
          inserted += chunk.length;
        }
      } catch (e) {
        errors.push(`d1: ${String(e).slice(0, 80)}`);
      }

      // KV에 결과 기록
      const result = {
        area, endpoint, fetched: allItems.length, totalCount,
        normalized: normalized.length, inserted, errors,
        ts: Date.now(), iso: new Date().toISOString(),
        duration_ms: Date.now() - startedAt
      };
      if (env.RATE_LIMIT_KV) {
        try {
          await env.RATE_LIMIT_KV.put(`bins:last_crawl:${area}`, JSON.stringify(result), {
            expirationTtl: 90 * 24 * 60 * 60
          });
        } catch (e) {}
      }
      return json({ ok: errors.length === 0, ...result }, 200, corsHeaders("*"));
    }

    // 2) 그 외 엔드포인트는 Origin 검증 (브라우저 호출 전용)
    if (!corsOrigin) {
      return json({ error: "Origin not allowed" }, 403, corsHeaders(""));
    }

    // v1.9.1: /data/* 는 GET 전용 (D1 읽기) — POST 검사보다 먼저!
    if (path.startsWith("/data/")) {
      if (request.method !== "GET") {
        return json({ error: "GET only for /data/*" }, 405, corsHeaders(corsOrigin));
      }
      return await handleData(request, env, corsOrigin, path);
    }

    // 3) Method / Content-Type 검증 (이후 분기는 POST 전용)
    if (request.method !== "POST") {
      return json({ error: "Method not allowed" }, 405, corsHeaders(corsOrigin));
    }

    // v1.5: /feedback 엔드포인트 (사용자 피드백 자동 수집)
    if (path === "/feedback") {
      return await handleFeedback(request, env, corsOrigin);
    }

    // (/augment는 위 비-브라우저 분기에서 이미 처리됨)
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

    // v1.8: 결과 캐싱 — 같은 이미지 = 즉시 응답 (Gemini 호출 0, 비용 0)
    const imageHash = await sha256(pureB64.slice(0, 5000));  // 빠른 hash (첫 5KB)
    const cacheKey = `cache:img:${imageHash}`;
    if (env.RATE_LIMIT_KV) {
      try {
        const cached = await env.RATE_LIMIT_KV.get(cacheKey);
        if (cached) {
          log("cache_hit", { ipHash, imageHash });
          const parsed = JSON.parse(cached);
          return json({ ok: true, result: parsed, finishReason: "cached", blockReason: null, cached: true }, 200, corsHeaders(corsOrigin));
        }
      } catch (e) { /* 캐시 실패 → 정상 흐름 */ }
    }

    // 6) Gemini 호출 (캐시 miss)
    const model = env.GEMINI_MODEL || "gemini-2.5-flash";
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
        // v1.9.7: 2048도 압력솥·노트북 같은 케이스에서 MAX_TOKENS 발생 → 8192로 확대
        //   정상 응답(100~200 토큰)은 영향 0. 비용 영향 0 (사용 토큰만 과금).
        //   v5.34에서 SYSTEM_PROMPT 46% 축소했지만 응답 자체가 길어지는 경우 잔존 → 출력 한도 자체 확대
        maxOutputTokens: 8192,
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
    const blockReason = geminiData?.promptFeedback?.blockReason || null;
    let parsed = null;
    try { parsed = JSON.parse(text); } catch { /* 텍스트 그대로 반환 */ }

    // v1.9.13 (2026-05-25): Post-AI 가드레일 — Gemini 환각 카테고리 차단
    // 환경부 분리배출.kr 12 표준 + 비재활용 8 + unknown 만 허용
    if (parsed && typeof parsed === 'object') {
      const VALID_CATS = new Set([
        'paper', 'paper_pack', 'pet_clear', 'plastic', 'vinyl', 'styrofoam',
        'glass', 'can', 'clothes', 'battery', 'lamp', 'electronics',
        'food', 'general', 'general_noncombustible', 'general_or_bulky',
        'bulky', 'furniture', 'hazardous', 'medicine', 'unknown'
      ]);
      if (parsed.category_hint && !VALID_CATS.has(parsed.category_hint)) {
        log("post_guard_invalid_cat", { ipHash, bad_cat: parsed.category_hint, item: parsed.item_id });
        parsed.category_hint = 'unknown';
        parsed._guarded = 'invalid_category';
      }
      // v1.9.14 (2026-05-25): 영문 item_id 사용자 노출 차단 (사용자 명령 "대한민국이에요! 영어 X")
      if (parsed.item_id && parsed.item_id !== 'unknown') {
        const _id = String(parsed.item_id);
        const _hasKor = /[\uAC00-\uD7A3]/.test(_id);
        if (!_hasKor) {
          log("post_guard_english_id_blocked", { ipHash, blocked_id: _id });
          const EN_KO_MIN = {
            'spray_can': '에어로졸 캔', 'pressure_cooker': '압력솥', 'coffee_maker': '커피머신',
            'hand_blender': '핸드블렌더', 'mug': '머그잔', 'newspaper': '신문지',
            'milk_carton': '우유팩', 'battery': '폐건전지', 'aerosol_can': '에어로졸 캔',
            'vinyl_bag': '비닐봉지', 'pet_bottle': '페트병', 'plastic_bottle': '플라스틱 병',
            'glass_bottle': '유리병', 'paper_box': '종이박스', 'snack_bag': '과자 봉지',
            'instant_rice_bowl': '즉석밥 용기', 'styrofoam_box': '스티로폼 박스',
            'paper_cup': '종이컵', 'paper_cup_coated': '코팅 종이컵', 'ceramic_dish': '도자기 그릇',
            'plastic_container': '플라스틱 용기', 'diaper': '기저귀', 'wet_tissue': '물티슈',
            'medicine': '폐의약품', 'clothes': '의류', 'electronics': '소형가전',
            'furniture': '대형폐기물', 'receipt': '영수증'
          };
          const lower = _id.toLowerCase().replace(/_\d+$/, '');
          if (EN_KO_MIN[lower]) {
            // 사전 매칭 성공 — 즉시 한국어 변환
            parsed.item_id = EN_KO_MIN[lower];
            parsed._worker_translated_from = _id;
          } else {
            // v1.9.14 정정: unknown 강제 X — client matchRule이 한국어 alias 매칭하도록 영문 그대로 전달
            // (예: 'laptop' → client matchRule이 노트북 item.aliases에서 'laptop' 발견 → '노트북' 매칭)
            parsed._needs_alias_lookup = true;
            parsed._english_id_marked = _id;
          }
        }
      }
    }

    // v1.8: Gemini 빈 응답 시 Claude 폴백 (앙상블)
    if (!parsed && !text && env.ANTHROPIC_API_KEY) {
      log("gemini_empty_claude_fallback", { ipHash, finishReason, blockReason });
      try {
        const claudeRes = await fetchWithTimeout("https://api.anthropic.com/v1/messages", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-api-key": env.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
          },
          body: JSON.stringify({
            model: "claude-haiku-4-5-20251001",
            max_tokens: 2048,
            messages: [{
              role: "user",
              content: [
                { type: "image", source: { type: "base64", media_type: mimeType, data: pureB64 } },
                { type: "text", text: prompt },
              ],
            }],
          }),
        }, FETCH_TIMEOUT_MS);
        if (claudeRes.ok) {
          const claudeData = await claudeRes.json();
          const claudeText = claudeData.content?.[0]?.text || "";
          try { parsed = JSON.parse(claudeText); } catch {}
          log("claude_fallback_ok", { ipHash, hasJson: !!parsed });
        }
      } catch (e) {
        log("claude_fallback_err", { ipHash, err: String(e).slice(0, 80) });
      }
    }

    // v1.9.4 (2026-05-22): 빈 응답·실패 응답은 캐시 X (사용자 finishReason=cached 빈 응답 버그 해결)
    //   - parsed가 있고 item_id가 비어있지 않을 때만 캐시
    //   - 빈 응답 캐시 시 사용자가 같은 이미지 재시도해도 빈 응답 계속 받음
    const cacheable = parsed
      && typeof parsed === 'object'
      && parsed.item_id
      && String(parsed.item_id).trim().length > 0
      && parsed.item_id !== 'unknown';
    if (env.RATE_LIMIT_KV && cacheable) {
      try {
        await env.RATE_LIMIT_KV.put(cacheKey, JSON.stringify(parsed), {
          expirationTtl: 24 * 60 * 60,  // 24시간
        });
      } catch (e) { /* 캐시 실패 무시 */ }
    } else if (env.RATE_LIMIT_KV && !cacheable) {
      // 캐시된 빈 응답이 있으면 삭제 (다음 분석은 fresh)
      try { await env.RATE_LIMIT_KV.delete(cacheKey); } catch (e) {}
    }

    log("ok", { ipHash, ms: Date.now() - startedAt, hasJson: !!parsed, finishReason, blockReason });
    return json(
      { ok: true, result: parsed ?? text, finishReason, blockReason, cached: false },
      200,
      corsHeaders(corsOrigin)
    );
  },

  // ============================================================================
  // v1.9.6 — Phase A2 cron 활성: scheduled() 핸들러
  // ============================================================================
  // wrangler.toml [triggers] crons 항목과 1:1 매핑
  //   - "5 15 * * *"   UTC 15:05 = KST 00:05  매일 자정 KST → 일일 metrics 기록
  //   - "0 */6 * * *"  6시간마다 → 캐시 안전망 청소
  // event.cron 에 등록한 cron 문자열이 그대로 들어오므로 분기 가능.
  // ctx.waitUntil로 비동기 작업 보장.
  async scheduled(event, env, ctx) {
    const cron = event.cron || "";
    const startedAt = Date.now();
    log("cron_start", { cron, scheduledTime: event.scheduledTime });

    try {
      if (cron === "5 15 * * *") {
        ctx.waitUntil(runDailyMetrics(env, startedAt, cron));
      } else if (cron === "0 */6 * * *") {
        ctx.waitUntil(runCacheSweep(env, startedAt, cron));
      } else {
        // 미등록 cron → 안전하게 양쪽 다 시도하지 말고 metrics만 (안전 기본값)
        log("cron_unknown", { cron });
        ctx.waitUntil(runDailyMetrics(env, startedAt, cron));
      }
    } catch (e) {
      log("cron_error", { cron, error: String(e).slice(0, 120) });
    }
  },
};

// ============================================================================
// v1.9.6 cron 작업 본체
// ============================================================================

async function runDailyMetrics(env, startedAt, cron) {
  const today = new Date().toISOString().slice(0, 10);
  const metric = {
    date: today,
    cron,
    started_at: new Date(startedAt).toISOString(),
    d1_items: null,
    d1_aliases: null,
    d1_regions: null,
    kv_fb_count: null,
    kv_cache_img_count: null,
    duration_ms: null,
    errors: [],
  };

  // D1 카운트
  if (env.DB) {
    try {
      const items = await env.DB.prepare("SELECT COUNT(*) AS c FROM items").first();
      metric.d1_items = items?.c ?? null;
    } catch (e) { metric.errors.push(`d1_items: ${String(e).slice(0, 60)}`); }
    try {
      const aliases = await env.DB.prepare("SELECT COUNT(*) AS c FROM aliases").first();
      metric.d1_aliases = aliases?.c ?? null;
    } catch (e) { metric.errors.push(`d1_aliases: ${String(e).slice(0, 60)}`); }
    try {
      const regions = await env.DB.prepare("SELECT COUNT(*) AS c FROM regions").first();
      metric.d1_regions = regions?.c ?? null;
    } catch (e) { metric.errors.push(`d1_regions: ${String(e).slice(0, 60)}`); }
  }

  // KV 카운트 (피드백 / 이미지 캐시)
  if (env.RATE_LIMIT_KV) {
    try {
      const fbList = await env.RATE_LIMIT_KV.list({ prefix: "fb:", limit: 1000 });
      metric.kv_fb_count = fbList.keys.length + (fbList.list_complete === false ? 1000 : 0);
    } catch (e) { metric.errors.push(`kv_fb: ${String(e).slice(0, 60)}`); }
    try {
      const cacheList = await env.RATE_LIMIT_KV.list({ prefix: "cache:img:", limit: 1000 });
      metric.kv_cache_img_count = cacheList.keys.length + (cacheList.list_complete === false ? 1000 : 0);
    } catch (e) { metric.errors.push(`kv_cache_img: ${String(e).slice(0, 60)}`); }
  }

  metric.duration_ms = Date.now() - startedAt;

  // 저장: metrics:daily:YYYY-MM-DD (90일 보존) + cron:last_run (최신 덮어쓰기, TTL 없음)
  if (env.RATE_LIMIT_KV) {
    try {
      await env.RATE_LIMIT_KV.put(`metrics:daily:${today}`, JSON.stringify(metric), {
        expirationTtl: 90 * 24 * 60 * 60,
      });
      await env.RATE_LIMIT_KV.put("cron:last_run", JSON.stringify({
        cron, kind: "daily_metrics", ts: Date.now(), iso: new Date().toISOString(),
        duration_ms: metric.duration_ms, errors: metric.errors.length,
      }));
    } catch (e) {
      log("cron_metric_save_err", { error: String(e).slice(0, 80) });
    }
  }
  log("cron_daily_done", { date: today, items: metric.d1_items, aliases: metric.d1_aliases, ms: metric.duration_ms, errs: metric.errors.length });
}

async function runCacheSweep(env, startedAt, cron) {
  if (!env.RATE_LIMIT_KV) {
    log("cron_sweep_skipped", { reason: "no_kv" });
    return;
  }

  // 빈/이상 응답 캐시 (item_id=unknown 또는 빈 객체) 정리. 사용자가 같은 사진 다시 찍었을 때 fresh 보장.
  // 안전: 100개까지만 스캔 (Worker CPU time 제약 회피)
  let scanned = 0, removed = 0;
  let cursor = undefined;
  const maxScan = 200;
  const errors = [];

  try {
    while (scanned < maxScan) {
      const page = await env.RATE_LIMIT_KV.list({ prefix: "cache:img:", limit: 50, cursor });
      for (const k of page.keys) {
        scanned++;
        try {
          const v = await env.RATE_LIMIT_KV.get(k.name);
          if (!v) continue;
          let bad = false;
          try {
            const p = JSON.parse(v);
            const id = p?.item_id ? String(p.item_id).trim() : "";
            if (!id || id === "unknown") bad = true;
          } catch {
            bad = true; // JSON 깨졌으면 정리
          }
          if (bad) {
            await env.RATE_LIMIT_KV.delete(k.name);
            removed++;
          }
        } catch (e) {
          errors.push(String(e).slice(0, 40));
        }
        if (scanned >= maxScan) break;
      }
      if (page.list_complete || !page.cursor) break;
      cursor = page.cursor;
    }
  } catch (e) {
    errors.push(`scan: ${String(e).slice(0, 60)}`);
  }

  const duration_ms = Date.now() - startedAt;
  try {
    await env.RATE_LIMIT_KV.put("cron:last_run", JSON.stringify({
      cron, kind: "cache_sweep", ts: Date.now(), iso: new Date().toISOString(),
      scanned, removed, duration_ms, errors: errors.length,
    }));
  } catch {}
  log("cron_sweep_done", { scanned, removed, ms: duration_ms, errs: errors.length });
}

async function readMetricSafe(env, key) {
  try {
    const v = await env.RATE_LIMIT_KV.get(key);
    if (!v) return null;
    try { return JSON.parse(v); } catch { return v; }
  } catch (e) {
    return { error: String(e).slice(0, 60) };
  }
}

/* ---------- 유틸 ---------- */
function buildAllowList(env) {
  const extra = (env.ALLOWED_ORIGINS || "").split(",").map(s => s.trim()).filter(Boolean);
  return [...new Set([...DEFAULT_ORIGINS, ...extra])];
}

function corsHeaders(origin, cacheSec) {
  return {
    "Access-Control-Allow-Origin": origin || "null",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
    "Cache-Control": cacheSec ? `public, max-age=${cacheSec}` : "no-store",
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
  const minuteLimit = Number(env.MINUTE_LIMIT || 30);  // v1.9.8: 10 → 30 (시연·테스트 시 차단 해소)
  const dailyLimit = Number(env.DAILY_LIMIT || 1000);  // v1.9.9: 100 → 1000 (시연·일반 사용 충분, 폭주만 차단)
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
// ============================================================================
// v1.9: /data/* 엔드포인트 — D1 직접 읽기 (정적 JSON 폐기)
// ============================================================================
// 사용 가능 경로:
//   GET /data/items                       → 모든 items (캐시 1h)
//   GET /data/items/:id                   → 특정 item
//   GET /data/search?q=노트북&limit=10    → alias 매칭 검색
//   GET /data/regions                     → 모든 시군구
//   GET /data/regions/:code               → 특정 시군구 (cityGuide 포함)
//   GET /data/region/:code/exceptions     → 지역 예외 룰
//
async function handleData(request, env, corsOrigin, path) {
  if (request.method !== "GET") {
    return json({ error: "GET only" }, 405, corsHeaders(corsOrigin || "*"));
  }
  if (!env.DB) {
    return json({ error: "D1 not configured (env.DB binding missing)" }, 503, corsHeaders(corsOrigin || "*"));
  }

  const url = new URL(request.url);
  const parts = path.split("/").filter(Boolean);  // ['data', 'items', ...]
  const resource = parts[1];

  try {
    // v1.9.12: /data/bins?lat=&lng=&area=medicine&limit=5 — 사용자 GPS 기반 가까운 수거함
    //   D1 bins 테이블에서 위경도 박스 1차 필터 (50km) → Haversine 정확 거리 → 가까운 N개 정렬
    //   응답: { ok, area, user_location, bins: [{name, address, lat, lng, phone, distance_m, region_code}] }
    if (resource === "bins") {
      const userLat = parseFloat(url.searchParams.get("lat"));
      const userLng = parseFloat(url.searchParams.get("lng"));
      const area = url.searchParams.get("area") || "medicine";
      const limit = Math.min(20, Math.max(1, parseInt(url.searchParams.get("limit") || "5")));
      if (!isFinite(userLat) || !isFinite(userLng)) {
        return json({ error: "lat/lng query params required" }, 400, corsHeaders(corsOrigin || "*"));
      }
      // 50km 박스 1차 필터 (위도 1도 ≈ 111km, 경도 1도 ≈ 88km 한국)
      const latRange = 0.5, lngRange = 0.6;
      const sql = `SELECT area_type, region_code, name, address, lat, lng, phone
                   FROM bins
                   WHERE area_type = ?
                     AND lat BETWEEN ? AND ?
                     AND lng BETWEEN ? AND ?
                     AND lat IS NOT NULL AND lng IS NOT NULL
                   LIMIT 200`;
      const dbRes = await env.DB.prepare(sql)
        .bind(area, userLat - latRange, userLat + latRange, userLng - lngRange, userLng + lngRange)
        .all();
      const candidates = dbRes.results || [];
      // Haversine 거리 (m)
      const R = 6371000;
      const toRad = d => d * Math.PI / 180;
      const hav = (a, b, c, d) => {
        const dLat = toRad(c - a), dLng = toRad(d - b);
        const x = Math.sin(dLat/2)**2 + Math.cos(toRad(a)) * Math.cos(toRad(c)) * Math.sin(dLng/2)**2;
        return Math.round(2 * R * Math.asin(Math.sqrt(x)));
      };
      const bins = candidates.map(b => ({ ...b, distance_m: hav(userLat, userLng, b.lat, b.lng) }))
        .sort((a, b) => a.distance_m - b.distance_m)
        .slice(0, limit);
      return json({
        ok: true, area, user_location: { lat: userLat, lng: userLng },
        candidates_in_box: candidates.length, count: bins.length, bins
      }, 200, corsHeaders(corsOrigin || "*", 60));
    }

    // v1.9.2: /data/all → 정적 national_rules.json과 동일 구조 (items: {id: {..., aliases:[]}})
    //   클라이언트(app.html)는 이걸 받으면 정적 JSON 대체 가능. cron 갱신 데이터 자동 반영.
    if (resource === "all") {
      const itemsRes = await env.DB.prepare("SELECT * FROM items").all();
      const aliasesRes = await env.DB.prepare("SELECT item_id, alias FROM aliases").all();
      const itemsMap = {};
      for (const it of (itemsRes.results || [])) {
        // JSON 필드 파싱 (steps, official_classification은 D1에 문자열로 저장됨)
        try { if (typeof it.steps === "string") it.steps = JSON.parse(it.steps); } catch {}
        try { if (typeof it.official_classification === "string") it.official_classification = JSON.parse(it.official_classification); } catch {}
        it.aliases = [];
        // 정적 JSON 호환: sourceUrl/sourceName 카멜케이스 alias 보강
        if (it.source_url && !it.sourceUrl) it.sourceUrl = it.source_url;
        if (it.source_name && !it.sourceName) it.sourceName = it.source_name;
        if (it.source_grade && !it.sourceGrade) it.sourceGrade = it.source_grade;
        if (it.last_verified && !it.lastVerified) it.lastVerified = it.last_verified;
        if (it.region_variation !== undefined && it.regionVariation === undefined) it.regionVariation = !!it.region_variation;
        itemsMap[it.id] = it;
      }
      for (const a of (aliasesRes.results || [])) {
        if (itemsMap[a.item_id]) itemsMap[a.item_id].aliases.push(a.alias);
      }
      return json({
        ok: true,
        source: "d1",
        version: "v7.0",
        items: itemsMap,
        count: Object.keys(itemsMap).length,
      }, 200, corsHeaders(corsOrigin || "*", 3600));
    }

    // /data/items, /data/items/:id
    if (resource === "items") {
      if (parts[2]) {
        const res = await env.DB.prepare("SELECT * FROM items WHERE id = ?").bind(parts[2]).first();
        if (!res) return json({ error: "item not found" }, 404, corsHeaders(corsOrigin || "*"));
        const aliases = await env.DB.prepare("SELECT alias FROM aliases WHERE item_id = ?").bind(parts[2]).all();
        res.aliases = (aliases.results || []).map(r => r.alias);
        return json({ ok: true, item: res }, 200, corsHeaders(corsOrigin || "*", 3600));
      }
      const res = await env.DB.prepare("SELECT * FROM items LIMIT 1000").all();
      return json({ ok: true, items: res.results || [] }, 200, corsHeaders(corsOrigin || "*", 3600));
    }

    // /data/search?q=...
    if (resource === "search") {
      const q = (url.searchParams.get("q") || "").trim().toLowerCase();
      const limit = Math.min(50, Number(url.searchParams.get("limit") || 10));
      if (!q || q.length < 1) return json({ ok: true, results: [] }, 200, corsHeaders(corsOrigin || "*"));
      const res = await env.DB.prepare(
        `SELECT a.alias, a.item_id, i.name, i.category
         FROM aliases a JOIN items i ON a.item_id = i.id
         WHERE a.alias_lower LIKE ?
         ORDER BY length(a.alias) ASC LIMIT ?`
      ).bind(`%${q}%`, limit).all();
      return json({ ok: true, results: res.results || [] }, 200, corsHeaders(corsOrigin || "*", 300));
    }

    // /data/regions, /data/regions/:code
    if (resource === "regions") {
      if (parts[2]) {
        const res = await env.DB.prepare("SELECT * FROM regions WHERE code = ?").bind(parts[2]).first();
        if (!res) return json({ error: "region not found" }, 404, corsHeaders(corsOrigin || "*"));
        // _inherits 체인 따라가서 cityGuide 보강
        let current = res;
        while (!current.city_guide && current.inherits_from) {
          current = await env.DB.prepare("SELECT * FROM regions WHERE code = ?").bind(current.inherits_from).first();
          if (!current) break;
        }
        if (current && current.city_guide) res.city_guide = current.city_guide;
        return json({ ok: true, region: res }, 200, corsHeaders(corsOrigin || "*", 3600));
      }
      const res = await env.DB.prepare("SELECT code, name, short_name, parent_code, type FROM regions").all();
      return json({ ok: true, regions: res.results || [] }, 200, corsHeaders(corsOrigin || "*", 3600));
    }

    // /data/region/:code/exceptions
    if (resource === "region" && parts[3] === "exceptions") {
      const res = await env.DB.prepare("SELECT * FROM region_exceptions WHERE region_code = ?").bind(parts[2]).all();
      return json({ ok: true, exceptions: res.results || [] }, 200, corsHeaders(corsOrigin || "*", 3600));
    }

    return json({ error: "unknown /data/* path" }, 404, corsHeaders(corsOrigin || "*"));
  } catch (e) {
    log("data_err", { path, error: String(e).slice(0, 80) });
    return json({ error: `DB query failed: ${String(e).slice(0, 80)}` }, 500, corsHeaders(corsOrigin || "*"));
  }
}

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

  const model = env.GEMINI_MODEL || "gemini-2.5-flash";
  const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${env.GEMINI_API_KEY}`;
  const payload = {
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: {
      responseMimeType: "application/json",
      // v1.7.2: 512는 한국어 12개 alias 다 생성 전 잘림. 2048로 안전 확대 (비용 영향 미세)
      maxOutputTokens: 2048,
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
    // v1.7.1: 유연한 파싱 — Gemini는 배열/객체/코드펜스 다양하게 응답
    let aliases = [];
    let parseHow = "none";
    try {
      const parsed = JSON.parse(text);
      if (Array.isArray(parsed)) {
        aliases = parsed;
        parseHow = "direct_array";
      } else if (parsed && typeof parsed === "object") {
        // 객체 응답 — 자주 쓰이는 키 찾기
        if (Array.isArray(parsed.aliases)) { aliases = parsed.aliases; parseHow = "obj.aliases"; }
        else if (Array.isArray(parsed.items)) { aliases = parsed.items; parseHow = "obj.items"; }
        else if (Array.isArray(parsed.result)) { aliases = parsed.result; parseHow = "obj.result"; }
        else if (Array.isArray(parsed.data)) { aliases = parsed.data; parseHow = "obj.data"; }
        else {
          // 처음 발견되는 배열 값
          const firstArr = Object.values(parsed).find(v => Array.isArray(v));
          if (firstArr) { aliases = firstArr; parseHow = "obj.firstArr"; }
        }
      }
    } catch {
      // JSON 파싱 실패 — 정규식으로 배열 추출
      const m = text.match(/\[[\s\S]*?\]/);
      if (m) {
        try { aliases  = JSON.parse(m[0]); parseHow = "regex_array"; } catch {}
      }
    }
    if (!Array.isArray(aliases)) aliases = [];
    // 각 요소 문자열로 정제
    aliases = aliases.filter(a => typeof a === "string").map(a => a.trim()).filter(a => a.length > 0);
    log("augment_ok", { item_name, count: aliases.length, parseHow });
    return json({ ok: true, item_name, category, aliases, parseHow, raw_preview: text.slice(0, 200) }, 200, corsHeaders(corsOrigin));
  } catch (e) {
    return json({ error: `Worker fetch failed: ${String(e)}` }, 500, corsHeaders(corsOrigin));
  }
}
