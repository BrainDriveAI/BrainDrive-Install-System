import threading


class StatusUpdater:
    """Thread-safe helper to push status/progress updates onto the Tk main thread."""

    def __init__(self, step_label, details_label, progress_bar):
        self.step_label = step_label
        self.details_label = details_label
        self.progress_bar = progress_bar
        self.lock = threading.Lock()
        self._animation_job = None

    def update_status(self, step_text, details_text, progress_value):
        """Update copy and animate progress to new value."""
        with self.lock:
            self.step_label.after(0, self.step_label.config, {"text": step_text})
            self.details_label.after(0, self.details_label.config, {"text": details_text})
            target = max(0, min(100, float(progress_value)))
            self._schedule_progress_animation(target)

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
