import threading
import time


class StatusUpdater:
    """Thread-safe helper to push status/progress updates onto the Tk main thread."""

    def __init__(self, step_label, details_label, progress_bar, status_display=None):
        self.step_label = step_label
        self.details_label = details_label
        self.progress_bar = progress_bar
        self.display = status_display
        self.lock = threading.Lock()
        self._animation_job = None
        self._last_progress_value = 0.0
        self._last_progress_time = None
        self._ema_rate = None
        self._eta_seconds = None

    def attach_display(self, status_display):
        """Attach the redesigned StatusDisplay for richer updates."""
        self.display = status_display

    def update_status(self, step_text, details_text, progress_value):
        """Update copy and animate progress to new value."""
        with self.lock:
            self.step_label.after(0, self.step_label.config, {"text": step_text})
            self.details_label.after(0, self.details_label.config, {"text": details_text})
            target = max(0, min(100, float(progress_value)))
            if self.display is not None:
                try:
                    eta_seconds = self._estimate_eta(target)
                    self.display.apply_status_update(step_text, details_text, target, eta_seconds=eta_seconds)
                except Exception:
                    pass
            self._schedule_progress_animation(target)

    def _estimate_eta(self, target):
        """Estimate remaining time in seconds once progress crosses 10%."""
        now = time.monotonic()
        if target <= 0 or target >= 100:
            self._last_progress_value = target
            self._last_progress_time = now
            self._ema_rate = None
            self._eta_seconds = None
            return None

        if self._last_progress_time is None:
            self._last_progress_time = now
            self._last_progress_value = target
            return None

        delta_value = target - self._last_progress_value
        delta_time = now - self._last_progress_time if self._last_progress_time else 0
        self._last_progress_time = now
        if delta_value <= 0 or delta_time <= 0:
            return self._eta_seconds

        rate = delta_value / delta_time  # percent per second
        if self._ema_rate is None:
            self._ema_rate = rate
        else:
            alpha = 0.3
            self._ema_rate = alpha * rate + (1 - alpha) * self._ema_rate

        self._last_progress_value = target
        if not self._ema_rate or self._ema_rate <= 0:
            return self._eta_seconds

        remaining = max(0.0, 100.0 - target)
        eta = remaining / self._ema_rate
        if target < 10:
            # Hide ETA until we have enough signal.
            self._eta_seconds = None
            return None
        self._eta_seconds = eta
        return self._eta_seconds

    def _schedule_progress_animation(self, target):
        if self._animation_job is not None:
            self.progress_bar.after_cancel(self._animation_job)
        current = float(self.progress_bar["value"])
        if abs(target - current) < 0.5:
            self.progress_bar.after(0, self.progress_bar.config, {"value": target})
            self._animation_job = None
            return

        step = 1 if target > current else -1

        def animate():
            nonlocal current
            current += step
            self.progress_bar.config(value=max(0, min(100, current)))
            if (step > 0 and current >= target) or (step < 0 and current <= target):
                self.progress_bar.config(value=target)
                self._animation_job = None
                return
            self._animation_job = self.progress_bar.after(10, animate)

        self._animation_job = self.progress_bar.after(10, animate)
