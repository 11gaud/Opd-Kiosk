// ─── Live Clock ────────────────────────────────────────────────────────────
const clockEl = document.getElementById('clock');
function updateClock() {
    if (clockEl) {
        clockEl.textContent = new Date().toLocaleTimeString('en-PH', {
            hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
    }
}
setInterval(updateClock, 1000);
updateClock();

// ─── Idle Reset Timer ──────────────────────────────────────────────────────
const IDLE_WARN_SECONDS = 90;   // show warning after 90s idle
const IDLE_RESET_SECONDS = 30;  // then countdown 30s before reset
const SKIP_IDLE_ON_PATHS = ['/', '/step/9/'];  // skip idle on start & ticket

const idleOverlay = document.getElementById('idle-overlay');
const idleCountdown = document.getElementById('idle-countdown');

let idleWarnTimer = null;
let idleCountdownTimer = null;
let countdownValue = IDLE_RESET_SECONDS;

function shouldSkipIdle() {
    return SKIP_IDLE_ON_PATHS.includes(window.location.pathname);
}

function startIdleWarnTimer() {
    if (shouldSkipIdle()) return;
    clearTimeout(idleWarnTimer);
    idleWarnTimer = setTimeout(() => {
        showIdleWarning();
    }, IDLE_WARN_SECONDS * 1000);
}

function showIdleWarning() {
    if (!idleOverlay) return;
    idleOverlay.classList.remove('hidden');
    idleOverlay.classList.add('flex');
    countdownValue = IDLE_RESET_SECONDS;
    if (idleCountdown) idleCountdown.textContent = countdownValue;

    idleCountdownTimer = setInterval(() => {
        countdownValue--;
        if (idleCountdown) idleCountdown.textContent = countdownValue;
        if (countdownValue <= 0) {
            clearInterval(idleCountdownTimer);
            // Submit reset form
            const resetForm = document.querySelector('form[action*="/api/reset/"]');
            if (resetForm) resetForm.submit();
            else window.location.href = '/';
        }
    }, 1000);
}

function resetIdleTimer() {
    clearTimeout(idleWarnTimer);
    clearInterval(idleCountdownTimer);
    if (idleOverlay) {
        idleOverlay.classList.add('hidden');
        idleOverlay.classList.remove('flex');
    }
    startIdleWarnTimer();
}

// Expose globally for inline onclick
window.resetIdleTimer = resetIdleTimer;

// Listen for any user activity
['touchstart', 'touchmove', 'click', 'keydown', 'mousemove'].forEach(evt => {
    document.addEventListener(evt, resetIdleTimer, { passive: true });
});

startIdleWarnTimer();
