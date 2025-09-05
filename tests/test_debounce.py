import os
import sys

import pytest

# Ensure the project root is on the path so that 'debounce' can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from debounce import DebounceManager


# Testing the DebounceManager's core logic without waiting in real time

def test_should_process_respects_debounce(monkeypatch):
    manager = DebounceManager(debounce_seconds=2, max_wait_seconds=10)

    # First call at time 0 should be allowed
    monkeypatch.setattr('debounce.time.time', lambda: 0)
    assert manager.should_process(1) is True

    # Second call at time 1 (< debounce_seconds) should be blocked
    monkeypatch.setattr('debounce.time.time', lambda: 1)
    assert manager.should_process(1) is False

    # Call after 3 seconds (> debounce_seconds) should be allowed again
    monkeypatch.setattr('debounce.time.time', lambda: 3)
    assert manager.should_process(1) is True


def test_cleanup_old_entries(monkeypatch):
    manager = DebounceManager()
    # Setup fake timestamps
    start_time = 1000
    manager.last_requests = {
        1: start_time - 4000,  # old
        2: start_time - 100,   # recent
        3: start_time,         # current
    }

    # Freeze time at start_time
    monkeypatch.setattr('debounce.time.time', lambda: start_time)

    manager.cleanup_old_entries(max_age_seconds=3600)

    assert 1 not in manager.last_requests
    assert set(manager.last_requests.keys()) == {2, 3}
