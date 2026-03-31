const API_BASE = "http://127.0.0.1:8000";

let sessionId = null;
let challengeId = null;
let captchaVerified = false;
let failedAttempts = 0;
let cooldownTimer = null;
let isLockedOut = false;

// DOM Elements
const captchaModal = document.getElementById("captchaModal");
const modalCloseBtn = document.getElementById("modalCloseBtn");

const word1El = document.getElementById("captchaWord1");
const word2El = document.getElementById("captchaWord2");

const captchaInput = document.getElementById("captchaInput");
const captchaStatus = document.getElementById("captchaStatus");

const verifyBtn = document.getElementById("verifyCaptchaBtn");
const refreshBtn = document.getElementById("refreshCaptcha");

const loginForm = document.getElementById("loginForm");
const emailEl = document.getElementById("email");
const passwordEl = document.getElementById("password");
const togglePwdBtn = document.getElementById("togglePwd");
const loginStatus = document.getElementById("loginStatus");

// ── Session ─────────────────────────────────────────────────────────────
async function initSession() {
  if (sessionId) return;
  try {
    const res = await fetch(`${API_BASE}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        api_key: "demo_secret_key",
        domain: "http://localhost",
        signals_json: "{}"
      })
    });
    if (!res.ok) throw new Error("Failed to create session");
    const data = await res.json();
    sessionId = data.session_id;
  } catch (err) {
    console.error("Session init error:", err);
  }
}

// ── Generate Challenge ──────────────────────────────────────────────────
async function generateCaptcha(keepStatus = false) {
  if (!keepStatus) {
    captchaStatus.textContent = "جاري التحميل...";
    captchaStatus.style.color = "rgba(0,0,0,0.65)";
  }

  captchaInput.value = "";
  captchaInput.disabled = false;
  if (!isLockedOut) {
    verifyBtn.disabled = false;
  }
  captchaVerified = false;

  try {
    await initSession();
    if (!sessionId) throw new Error("No session created");

    const chalRes = await fetch(`${API_BASE}/challenges`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId })
    });
    if (!chalRes.ok) throw new Error("Failed to fetch challenge");
    const chalData = await chalRes.json();

    challengeId = chalData.challenge_id;

    const getFullUrl = (path) => path.startsWith("http") ? path : `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`;
    word1El.src = getFullUrl(chalData.ref_image_url);
    word2El.src = getFullUrl(chalData.low_conf_image_url);
    word1El.alt = "كلمة ١";
    word2El.alt = "كلمة ٢";

    if (!keepStatus) {
      captchaStatus.textContent = "";
    }
  } catch (err) {
    console.error("Generate Captcha error:", err);
    captchaStatus.textContent = "⚠️ فشل تحميل التحدي. حاول تحديث الصفحة.";
    captchaStatus.style.color = "#b03a2e";
  }
}

// ── Cooldown Timer ──────────────────────────────────────────────────────
function startCooldown() {
  const extraMinutes = failedAttempts - 2; // 3rd fail = 1 min, 4th = 2 min, etc.
  const cooldownSeconds = extraMinutes * 60;
  let remaining = cooldownSeconds;

  isLockedOut = true;
  verifyBtn.disabled = true;
  captchaInput.disabled = true;

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
      captchaInput.disabled = false;
      captchaStatus.textContent = "يمكنك المحاولة الآن.";
      captchaStatus.style.color = "rgba(0,0,0,0.65)";
      generateCaptcha();
    } else {
      updateTimer();
    }
  }, 1000);
}

// ── Modal Controls ──────────────────────────────────────────────────────
function openCaptchaModal() {
  captchaModal.classList.remove("hidden");
  if (!isLockedOut) {
    generateCaptcha();
  }
}

function closeCaptchaModal() {
  captchaModal.classList.add("hidden");
}

modalCloseBtn.addEventListener("click", closeCaptchaModal);

captchaModal.addEventListener("click", (e) => {
  if (e.target === captchaModal) closeCaptchaModal();
});

// ── Helpers ─────────────────────────────────────────────────────────────
function normalizeInput(str) {
  return str.trim().replace(/\s+/g, " ");
}

// ── Refresh ─────────────────────────────────────────────────────────────
refreshBtn.addEventListener("click", () => {
  if (!isLockedOut) generateCaptcha();
});

// ── Verify ──────────────────────────────────────────────────────────────
verifyBtn.addEventListener("click", async () => {
  if (!challengeId || isLockedOut) return;

  const userInput = normalizeInput(captchaInput.value);
  const inputParts = userInput.split(" ");

  const refAnswer = inputParts[0] || "";
  const lowConfAnswer = inputParts[1] || "";

  // Check: empty input
  if (!refAnswer) {
    captchaStatus.textContent = "⚠️ يرجى كتابة النص العربي.";
    captchaStatus.style.color = "#b03a2e";
    return;
  }

  // Check: only one word entered
  if (!lowConfAnswer) {
    captchaStatus.textContent = "⚠️ يرجى كتابة الكلمتين معًا مفصولتين بمسافة.";
    captchaStatus.style.color = "#b03a2e";
    return;
  }

  captchaStatus.textContent = "جاري التحقق...";
  captchaStatus.style.color = "rgba(0,0,0,0.65)";
  verifyBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/challenges/${challengeId}/solve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ref_answer: refAnswer,
        low_conf_answer: lowConfAnswer,
        response_time_ms: 1500,
        signals_json: "{}"
      })
    });

    if (!res.ok) throw new Error("Invalid request");

    const data = await res.json();

    if (data.passed) {
      captchaStatus.textContent = "✅ تم التحقق بنجاح!";
      captchaStatus.style.color = "#1e7e34";
      captchaVerified = true;
      captchaInput.disabled = true;
      verifyBtn.disabled = true;
      failedAttempts = 0; // Reset on success

      setTimeout(() => {
        closeCaptchaModal();
        loginStatus.textContent = "✅ تم التحقق! جاري تسجيل الدخول...";
        loginStatus.style.color = "#1e7e34";
        setTimeout(() => {
          alert("تم تسجيل الدخول بنجاح! 🎉");
          loginStatus.textContent = "";
        }, 700);
      }, 800);

    } else {
      failedAttempts++;

      if (failedAttempts >= 3) {
        // Start cooldown timer
        captchaStatus.textContent = "❌ إجابة خاطئة.";
        captchaStatus.style.color = "#b03a2e";
        startCooldown();
      } else {
        // Show error and auto-refresh challenge (keep error message visible)
        captchaStatus.textContent = "❌ إجابة خاطئة. حاول مرة أخرى.";
        captchaStatus.style.color = "#b03a2e";
        verifyBtn.disabled = false;
        generateCaptcha(true); // true = keep status message visible
      }
    }
  } catch (err) {
    console.error("Verify Error:", err);
    failedAttempts++;

    if (failedAttempts >= 3) {
      captchaStatus.textContent = "❌ إجابة خاطئة.";
      captchaStatus.style.color = "#b03a2e";
      startCooldown();
    } else {
      captchaStatus.textContent = "❌ إجابة خاطئة. حاول مرة أخرى.";
      captchaStatus.style.color = "#b03a2e";
      verifyBtn.disabled = false;
      generateCaptcha(true);
    }
  }
});

// ── Toggle Password ─────────────────────────────────────────────────────
togglePwdBtn.addEventListener("click", () => {
  passwordEl.type = passwordEl.type === "password" ? "text" : "password";
});

// ── Form Submit ─────────────────────────────────────────────────────────
loginForm.addEventListener("submit", (e) => {
  e.preventDefault();

  if (!emailEl.value || !passwordEl.value) {
    loginStatus.textContent = "⚠️ يرجى تعبئة البريد الإلكتروني وكلمة المرور أولاً.";
    loginStatus.style.color = "#b03a2e";
    return;
  }

  if (!captchaVerified) {
    loginStatus.textContent = "⚠️ يجب التحقق أولاً للمتابعة.";
    loginStatus.style.color = "#b03a2e";
    openCaptchaModal();
    return;
  }

  alert("تم تسجيل الدخول بنجاح! 🎉");
});
