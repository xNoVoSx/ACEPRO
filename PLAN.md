# PLAN

Goal: ACEPRO on the Kobra X (branch `kobra-x`), feeding one shared toolhead
inlet through the RDM. Everything below is optional, to be picked up later.

## Open items

1. **Early load failure at the RDM** (optional). A load feeds up to
   `toolchange_load_length` and only checks the toolhead intake sensor
   (`intake_gated.py` `_feed_to_intake`); with `toolhead_load_retries: 2`
   that is three full-length attempts. A jam at the RDM merge (seen when
   one slot's tip blocked another) is only reported after all three, with
   the filament buckled against the blockage. Proposal: fail the attempt
   when the RDM switch has not triggered within `parkposition_to_rdm_length`
   plus a margin, with an error naming "stuck before/in the RDM". Use the
   switch, not the encoder (item 2).
2. **RDM encoder stalls** (optional, hardware first). While moving the
   encoder gives about 0.9 mm per edge, but the wheel stalls intermittently.
   Hand test: push 100 mm by hand and watch `encoder_pulse`. Only after that
   decide whether the encoder can serve as a movement check.
3. **Live `ace_KX.cfg` comment** (optional). On the printer,
   `parkposition_to_toolhead_length: 900` still carries a "VERIFY" comment;
   the value is verified (RDM clears at about 14.5 s of the 18 s retract).
   Align the comment with the template.
4. **Display timing of the inlet number** (optional, OPEN). After the
   put-back incident the toolhead display showed "4" only after the ACE had
   pulled the filament out, while the log shows the selector move before the
   retract. Unexplained; reproduce before changing anything.
5. **ACE USB drops** (optional, watch). 17 drops before the cable swap, none
   in about 8 tool changes since. Re-check the count after longer use; the
   ACE's internal hub sits at 1-1.3, the ACE device at 1-1.3.3.
6. **Rollback assist in the default strategy** (optional, needs an ACE2 on a
   `sensor_push` printer to test). `execute_coordinated_retraction`
   (`manager.py`, test retracts that identify an unknown tool) lets the ACE
   retract run to completion before its `G1 E-`, so on an ACE2 that
   extruder retract pulls against the idle clamp. Wrap it in
   `rollback_assist()` as `intake_gated.py` does, or start the ACE pull
   without waiting so both run together. The 2 mm pre-cut retract of
   `PREPARE_RETRACT` is the same case at a size that hardly matters.
