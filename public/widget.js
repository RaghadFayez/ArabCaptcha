const BACKEND_BASE_URL = window.location.origin;

let sessionId = null;
let challengeId = null;
let verifiedToken = null;
let challengeStartedAt = null;

// ── Passive Tracking (from page load, before Start) ─────────────────────
const _pageLoadTime = performance.now();
let _hoverBeforeStart = false;
let _hadAnyMouseMove = false;

// ── Behavioral Tracking ──────────────────────────────────────────────
let behavioralData = {
  mouse_moves: 0,
  scrolls: 0,
  click_count: 0,
  paste_used: false,
  webdriver: navigator.webdriver || false,
  first_interaction_ms: null,
  focus_blur_count: 0,
  failed_attempts: 0,
  time_to_start_ms: null,
  hover_before_start: false,
  keyboard_only: false,
};

function recordFirstInteraction() {
  if (behavioralData.first_interaction_ms === null && challengeStartedAt) {
    behavioralData.first_interaction_ms = Math.round(performance.now() - challengeStartedAt);
  }
}

window.addEventListener("mousemove", () => {
  behavioralData.mouse_moves++;
  _hadAnyMouseMove = true;
  if (!sessionId) {
    _hoverBeforeStart = true;
  }
});
window.addEventListener("scroll", () => behavioralData.scrolls++);
window.addEventListener("blur", () => behavioralData.focus_blur_count++);
window.addEventListener("keydown", (e) => {
  recordFirstInteraction();
  if (!_hadAnyMouseMove) {
    behavioralData.keyboard_only = true;
  }
});
window.addEventListener("click", () => {
  behavioralData.click_count++;
  recordFirstInteraction();
});

let isLockedOut = false;
let failedAttempts = 0;
let cooldownTimer = null;

const capPage1 = document.getElementById("capPage1");
const capPage2 = document.getElementById("capPage2");
const startBtn = document.getElementById("capStartBtn");

const refImage = document.getElementById("refImage");
const lowConfImage = document.getElementById("lowConfImage");

const refAnswerInput = document.getElementById("refAnswer");
const lowConfAnswerInput = document.getElementById("lowConfAnswer");

refAnswerInput.addEventListener("paste", () => behavioralData.paste_used = true);
lowConfAnswerInput.addEventListener("paste", () => behavioralData.paste_used = true);
const captchaStatus = document.getElementById("captchaStatus");

const verifyBtn = document.getElementById("verifyCaptchaBtn");
const refreshBtn = document.getElementById("refreshCaptcha");

// -- استقبال أوامر المحاكاة من الديمو الخارجي --
window.addEventListener('message', async (e) => {
  if (e.data && e.data.type === 'SIMULATE_BEHAVIOR') {
    await simulateBehavior(e.data.level);
  }
});

async function simulateBehavior(level) {
  if (level === 'easy') {
    behavioralData.mouse_moves = 15;
    behavioralData.scrolls = 2;
    behavioralData.paste_used = false;
    behavioralData.webdriver = false;
    behavioralData.first_interaction_ms = 1200;
    behavioralData.failed_attempts = 0;
    behavioralData.keyboard_only = false;
    behavioralData.time_to_start_ms = 3500;
    behavioralData.hover_before_start = true;
    captchaStatus.textContent = "محاكاة: سلوك طبيعي...";
    captchaStatus.style.color = "#1e7e34";
  } else if (level === 'medium') {
    behavioralData.mouse_moves = 5;
    behavioralData.scrolls = 0;
    behavioralData.paste_used = true; // +25 points
    behavioralData.webdriver = false;
    behavioralData.first_interaction_ms = 100; // +15 points
    behavioralData.failed_attempts = 0;
    behavioralData.keyboard_only = false;
    behavioralData.time_to_start_ms = 1500;
    behavioralData.hover_before_start = false;
    captchaStatus.textContent = "محاكاة: سلوك مريب...";
    captchaStatus.style.color = "#d39e00";
  } else if (level === 'hard') {
    behavioralData.mouse_moves = 0;
    behavioralData.scrolls = 0;
    behavioralData.paste_used = true;
    behavioralData.webdriver = true; // +90 points (Hard Cap)
    behavioralData.first_interaction_ms = 40;
    behavioralData.failed_attempts = 5;
    behavioralData.keyboard_only = true;
    behavioralData.time_to_start_ms = 200;
    behavioralData.hover_before_start = false;
    captchaStatus.textContent = "محاكاة: نشاط آلي...";
    captchaStatus.style.color = "#b03a2e";
  }
  
  // إجبار النظام على بدء جلسة جديدة بالبيانات المحددة
  sessionId = null;
  verifyBtn.disabled = false;
  refAnswerInput.disabled = false;
  lowConfAnswerInput.disabled = false;
  isLockedOut = false;
  
  if (cooldownTimer) {
    clearInterval(cooldownTimer);
    cooldownTimer = null;
  }
  
  await loadChallenge();
}

function notifyParentHeight() {
  const height = document.documentElement.scrollHeight;
  window.parent.postMessage({ type: "ARABCAPTCHA_RESIZE", height: height }, "*");
}

function getHostDomain() {
  const params = new URLSearchParams(window.location.search);
  return params.get("domain") || "http://localhost";
}

function getApiKey() {
  const params = new URLSearchParams(window.location.search);
  return params.get("apiKey") || "demo_secret_key";
}

async function createSession() {
  const response = await fetch(`${BACKEND_BASE_URL}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      api_key: getApiKey(),
      domain: getHostDomain(),
      signals_json: JSON.stringify(behavioralData)
    })
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Session failed: ${response.status} ${errorText}`);
  }

  const data = await response.json();
  sessionId = data.session_id;

  window.parent.postMessage({ type: 'ARABCAPTCHA_DEBUG_SCORE', score: data.bot_score || 0 }, '*');

  return data;
}

async function loadChallenge(keepStatus = false) {
  if (!keepStatus) {
    captchaStatus.textContent = "جاري التحميل...";
    captchaStatus.style.color = "rgba(0,0,0,0.65)";
  }

  refAnswerInput.value = "";
  lowConfAnswerInput.value = "";
  verifiedToken = null;

  if (!isLockedOut) {
    verifyBtn.disabled = false;
    refAnswerInput.disabled = false;
    lowConfAnswerInput.disabled = false;
  }

  if (!sessionId) {
    await createSession();
  }

  const response = await fetch(`${BACKEND_BASE_URL}/challenges`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId })
  });

  if (!response.ok) {
    throw new Error(`Challenge failed`);
  }

  const data = await response.json();
  challengeId = data.challenge_id;

  const getFullUrl = (path) => path.startsWith("http") ? path : `${BACKEND_BASE_URL}${path.startsWith('/') ? '' : '/'}${path}`;
  refImage.src = getFullUrl(data.ref_image_url);
  lowConfImage.src = getFullUrl(data.low_conf_image_url);

  // Difficulty is now handled server-side via image obfuscation (image_obfuscation.py)
  // Reset any leftover CSS from previous approach
  refImage.style.filter = "";
  lowConfImage.style.filter = "";
  refImage.style.transform = "";
  lowConfImage.style.transform = "";

  if (data.difficulty === "hard") {
    window.parent.postMessage({ type: 'ARABCAPTCHA_DEBUG_DIFF', diffText: "عالي الخطورة (صعب)", color: "#b03a2e" }, '*');
  } else if (data.difficulty === "medium") {
    window.parent.postMessage({ type: 'ARABCAPTCHA_DEBUG_DIFF', diffText: "متوسط", color: "#d39e00" }, '*');
  } else {
    window.parent.postMessage({ type: 'ARABCAPTCHA_DEBUG_DIFF', diffText: "طبيعي (سهل)", color: "#1e7e34" }, '*');
  }


  challengeStartedAt = performance.now();

  if (!keepStatus) {
    captchaStatus.textContent = "";
  }
  notifyParentHeight();
}

// ── Cooldown Timer ──────────────────────────────────────────────────────
function startCooldown() {
  const extraMinutes = failedAttempts - 2;
  const cooldownSeconds = extraMinutes * 60;
  let remaining = cooldownSeconds;

  isLockedOut = true;
  verifyBtn.disabled = true;
  refAnswerInput.disabled = true;
  lowConfAnswerInput.disabled = true;

  function updateTimer() {
    const mins = Math.floor(remaining / 60);
    const secs = remaining % 60;
    const timeStr = mins > 0
      ? `${mins} دقيقة${secs > 0 ? ` و ${secs} ثانية` : ""}`
      : `${secs} ثانية`;
    captchaStatus.textContent = `⏳ حاولت كثيرًا. حاول مرة أخرى بعد ${timeStr}`;
    captchaStatus.style.color = "#b03a2e";
  }

  updateTimer();

  cooldownTimer = setInterval(() => {
    remaining--;
    if (remaining <= 0) {
      clearInterval(cooldownTimer);
      cooldownTimer = null;
      isLockedOut = false;
      verifyBtn.disabled = false;
      refAnswerInput.disabled = false;
      lowConfAnswerInput.disabled = false;
      captchaStatus.textContent = "يمكنك المحاولة الآن.";
      captchaStatus.style.color = "rgba(0,0,0,0.65)";
      loadChallenge();
    } else {
      updateTimer();
    }
  }, 1000);
}

startBtn.addEventListener("click", async () => {
  behavioralData.time_to_start_ms = Math.round(performance.now() - _pageLoadTime);
  behavioralData.hover_before_start = _hoverBeforeStart;

  capPage1.classList.add("hidden");
  capPage2.classList.remove("hidden");
  notifyParentHeight();
  if (!isLockedOut) {
    try {
      await loadChallenge();
    } catch (error) {
      console.error(error);
      captchaStatus.textContent = "⚠️ فشل تحميل التحدي.";
      captchaStatus.style.color = "#b03a2e";
    }
  }
});

refreshBtn.addEventListener("click", async () => {
  if (isLockedOut) return;
  try {
    await loadChallenge();
  } catch (error) {
    console.error(error);
    captchaStatus.textContent = "⚠️ فشل التحديث.";
    captchaStatus.style.color = "#b03a2e";
  }
});

verifyBtn.addEventListener("click", async () => {
  if (isLockedOut || !challengeId) return;

  const refAnswer = refAnswerInput.value.trim();
  const lowConfAnswer = lowConfAnswerInput.value.trim();

  if (!refAnswer) {
    captchaStatus.textContent = "⚠️ يرجى كتابة الكلمة المرجعية.";
    captchaStatus.style.color = "#b03a2e";
    return;
  }
  if (!lowConfAnswer) {
    captchaStatus.textContent = "⚠️ يرجى كتابة الكلمة غير الواضحة.";
    captchaStatus.style.color = "#b03a2e";
    return;
  }

  captchaStatus.textContent = "جاري التحقق...";
  captchaStatus.style.color = "rgba(0,0,0,0.65)";
  verifyBtn.disabled = true;

  const responseTimeMs = challengeStartedAt
    ? Math.round(performance.now() - challengeStartedAt)
    : null;

  try {
    behavioralData.failed_attempts = failedAttempts;
    behavioralData.submit_time_ms = responseTimeMs;

    const response = await fetch(`${BACKEND_BASE_URL}/challenges/${challengeId}/solve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ref_answer: refAnswer,
        low_conf_answer: lowConfAnswer,
        response_time_ms: responseTimeMs,
        signals_json: JSON.stringify(behavioralData)
      })
    });

    if (!response.ok) throw new Error("Solve failed");

    const data = await response.json();

    if (data.passed) {
      verifiedToken = data.token || "verified";
      captchaStatus.textContent = "✅ تم التحقق بنجاح!";
      captchaStatus.style.color = "#1e7e34";
      failedAttempts = 0;
      refAnswerInput.disabled = true;
      lowConfAnswerInput.disabled = true;

      window.parent.postMessage(
        { type: "ARABCAPTCHA_SUCCESS", token: verifiedToken },
        "*"
      );
    } else {
      failedAttempts++;
      if (failedAttempts >= 3) {
        captchaStatus.textContent = "❌ إجابة خاطئة.";
        captchaStatus.style.color = "#b03a2e";
        startCooldown();
      } else {
        captchaStatus.textContent = "❌ إجابة خاطئة. حاول مرة أخرى.";
        captchaStatus.style.color = "#b03a2e";
        verifyBtn.disabled = false;
        loadChallenge(true); // reload images, keep error message
      }
    }
  } catch (error) {
    console.error(error);
    failedAttempts++;
    if (failedAttempts >= 3) {
      captchaStatus.textContent = "❌ إجابة خاطئة.";
      captchaStatus.style.color = "#b03a2e";
      startCooldown();
    } else {
      captchaStatus.textContent = "❌ إجابة خاطئة. حاول مرة أخرى.";
      captchaStatus.style.color = "#b03a2e";
      verifyBtn.disabled = false;
      loadChallenge(true);
    }
  }
});

const observer = new MutationObserver(() => notifyParentHeight());
observer.observe(document.body, { childList: true, subtree: true, attributes: true });

window.addEventListener("load", notifyParentHeight);