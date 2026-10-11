"""The RDM-monitored unload pulls the overshoot within the same retract.

The unload retracts at most `length` and, once the RDM clears, on for
`rdm_overshoot_length` past the 4-in-1's merge point. One ACE command
covers both: a stop and a second retract make the ACE disengage and engage
its gears again. The overshoot is timed from the clear at the retract
speed, as the ACE reports no position.

When the RDM clears only after that retract has ended - on the Kobra X the
toolhead-to-RDM path is about as long as the maximum - there is no running
move left to extend, and the tip stayed at the switch, in the merge,
blocking the next slot; the overshoot is then a move of its own.

The ACE's retract (_retract, the serial boundary) is replaced by a fake that
runs on a stepped clock: it polls the callback every POLL_S like _retract,
moves at the commanded speed and records where it was stopped.
"""
from unittest.mock import Mock

import pytest

from ace.instance import AceInstance

SLOT = 1
SPEED = 50.0
POLL_S = 0.2


class Clock:
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now


class FakeAce:
    """The RDM sees filament until `clears_at` seconds into the first
    retract (never when None)."""

    def __init__(self, clock, clears_at):
        self.clock = clock
        self.clears_at = clears_at
        self.start = clock.now
        self.moves = []          # (slot, commanded length, length pulled)
        self.manager = Mock()
        self.manager.has_rdm_sensor.return_value = True
        self.manager.get_instant_switch_state.side_effect = self.rdm_present

    def rdm_present(self, sensor):
        return (self.clears_at is None
                or self.clock.now - self.start < self.clears_at)

    def retract(self, slot, length, speed, early_stop_callback=None, **kwargs):
        began = self.clock.now
        duration = length / speed
        while self.clock.now - began < duration:
            self.clock.now = min(self.clock.now + POLL_S, began + duration)
            if early_stop_callback is not None and early_stop_callback():
                break
        else:
            # _retract keeps polling while it waits for the ACE's ready.
            if early_stop_callback is not None:
                early_stop_callback()
        self.moves.append((slot, length, (self.clock.now - began) * speed))
        return {"code": 0, "msg": "success"}


@pytest.fixture
def clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr("ace.instance.time.time", clock.time)
    return clock


def _instance(fake):
    inst = object.__new__(AceInstance)
    inst.instance_num = 0
    inst.retract_speed = SPEED
    inst.gcode = Mock()
    inst.reactor = Mock()
    inst.reactor.monotonic.return_value = 0.0
    inst._get_current_feed_assist_index = Mock(return_value=-1)
    inst._disable_feed_assist = Mock()
    inst._restore_assist_after_unload = Mock()
    inst._retract = fake.retract
    return inst


def _unload(fake, length, overshoot):
    return _instance(fake).rmd_triggered_unload_slot(
        fake.manager, SLOT, length=length, overshoot_length=overshoot)


def test_one_retract_pulls_on_past_the_clear_by_the_overshoot(clock):
    fake = FakeAce(clock, clears_at=14.5)
    assert _unload(fake, length=900, overshoot=200)
    assert len(fake.moves) == 1
    slot, commanded, pulled = fake.moves[0]
    assert (slot, commanded) == (SLOT, 1100)
    past_clear = pulled - 14.5 * SPEED
    assert 200 <= past_clear <= 200 + POLL_S * SPEED


def test_the_overshoot_is_its_own_retract_when_the_move_ends_too_soon(
        clock):
    # The 850 mm move ends at 17 s: 2 s after the clear, half the overshoot.
    fake = FakeAce(clock, clears_at=15.0)
    assert _unload(fake, length=650, overshoot=200)
    assert [m[:2] for m in fake.moves] == [(SLOT, 850), (SLOT, 200)]


def test_no_overshoot_when_the_rdm_never_clears(clock):
    fake = FakeAce(clock, clears_at=None)
    assert not _unload(fake, length=650, overshoot=200)
    assert [m[:2] for m in fake.moves] == [(SLOT, 850)]


def test_a_zero_overshoot_stops_at_the_clear(clock):
    fake = FakeAce(clock, clears_at=5.0)
    assert _unload(fake, length=650, overshoot=0)
    assert len(fake.moves) == 1
    slot, commanded, pulled = fake.moves[0]
    assert (slot, commanded) == (SLOT, 650)
    assert 5.0 * SPEED <= pulled <= (5.0 + POLL_S) * SPEED
