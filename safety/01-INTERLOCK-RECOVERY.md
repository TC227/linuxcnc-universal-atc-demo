# Safety 01 — Interlocks, Faults and Recovery

สถานะ: DRAFT — machine-specific safety review required.

## Fundamental boundary

LinuxCNC, HAL, QtVCP and ATC Manager are not safety-rated by default. E-stop, guard interlock, STO, hazardous-energy isolation and required safety functions must use suitable safety components and machine-specific risk assessment.

## Typical process permissives

Depending on machine: E-stop chain healthy, guard closed/locked, air pressure adequate, spindle speed zero, spindle orientation complete, axes at exchange position, magazine at exchange station, drive ready, drawbar and arm states valid.

These process permissives are not a substitute for certified safety functions.

## Sensor plausibility

Detect contradictory states, for example POT_UP and POT_DOWN simultaneously, ARM_HOME and ARM_180 simultaneously where impossible, DRAWBAR_CLAMPED and DRAWBAR_UNCLAMPED together, gripper open and closed together, or encoder position inconsistent with pocket sensor.

The plausibility matrix is profile-specific.

## Output behavior

For every output define safe behavior at power-up, LinuxCNC shutdown, watchdog timeout, field-power loss and communication loss. Do not assume all outputs OFF is mechanically safe; a suspended tool or loaded arm may require a designed holding/braking strategy.

## Recovery after interruption

1. Mark unverified mechanism states UNKNOWN.
2. Read physical sensors and drive feedback.
3. Never infer position from last commanded position alone.
4. Block automatic M6 until state is reconciled.
5. Present guided recovery.
6. Permit controlled manual movement only under appropriate maintenance conditions.
7. Verify spindle, drawbar, arm, gripper and magazine states.
8. Reconcile tool/pocket occupancy before resuming automatic operation.

## Manual mode

Use explicit maintenance mode, hold-to-run where appropriate, one motion at a time, speed/pressure limits, clear warnings and interlock checks. Never bypass required safety-rated functions.

## Validation tests

Sensor stuck ON/OFF, wire break, field power loss, output short, drive fault, watchdog loss, spindle fails to stop, M19 timeout, magazine overshoot, tool not captured, drawbar mismatch and power loss at each critical state.
