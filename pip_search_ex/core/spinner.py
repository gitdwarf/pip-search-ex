"""Shared spinner utility for showing progress."""
import sys
import time
import threading


class Spinner:
    """Animated spinner for command-line progress indication."""
    
    def __init__(self, message="Working"):
        self.message = message
        self.frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.running = False
        self.thread = None
    
    def _spin(self):
        i = 0
        while self.running:
            frame = self.frames[i % len(self.frames)]
            print(f"\r{frame} {self.message}...", end="", file=sys.stderr, flush=True)
            time.sleep(0.1)
            i += 1
    
    def start(self):
        """Start the spinner animation."""
        self.running = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the spinner and clear the line."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.5)
        print("\r" + " " * 80 + "\r", end="", file=sys.stderr, flush=True)
    
    def update(self, message):
        """Update the spinner message."""
        self.message = message
