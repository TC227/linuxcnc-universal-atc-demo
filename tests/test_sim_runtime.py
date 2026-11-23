from atc_configurator.sim_runtime import SimRuntime


def finish(runtime):
    for _ in range(160):
        runtime.tick()
        if not runtime.busy:
            return
    raise AssertionError("Sequence did not finish")


def test_two_changes_return_old_tool_before_rotating_for_new_tool():
    runtime = SimRuntime()
    for target in (4, 9):
        assert runtime.start(target)
        finish(runtime)
        assert runtime.status == "COMPLETE"
        assert runtime.spindle == runtime.pocket == target
        assert runtime.inputs["DRAWBAR_CLAMPED"]
        assert runtime.inputs["MAGAZINE_RETRACTED"]
        assert runtime.inputs["ATC_DOOR_CLOSED"]
    assert runtime.completed.index("EXTEND_RETURN") < runtime.completed.index("UNCLAMP")
    assert runtime.completed.index("LIFT_RETURN") < runtime.completed.index("NEW_POCKET")


def test_failed_feedback_times_out_without_loading_tool():
    runtime = SimRuntime(failed_sensor="DRAWBAR_UNCLAMPED")
    runtime.start(5)
    finish(runtime)
    assert runtime.status == "FAULT"
    assert "DRAWBAR_UNCLAMPED" in runtime.waiting
    assert runtime.spindle == 0
    assert not any(runtime.outputs.values())


def test_explicitly_disabled_sensor_is_bypassed():
    runtime = SimRuntime(failed_sensor="DRAWBAR_UNCLAMPED",
                         disabled={"DRAWBAR_UNCLAMPED"})
    runtime.start(3)
    finish(runtime)
    assert runtime.status == "COMPLETE"
    assert runtime.spindle == 3


def test_stop_requires_reset_and_clears_motor_commands():
    runtime = SimRuntime()
    runtime.start(6)
    runtime.tick()
    runtime.stop()
    assert not runtime.busy
    assert not runtime.start(2)
    assert not any(runtime.outputs.values())


def test_m19_confirms_only_after_reaching_target():
    runtime = SimRuntime(spindle_angle=37,orient_target=180)
    runtime.steps = ["ORIENT"]
    runtime.status = "RUNNING"
    runtime.tick(.1)
    assert 37 < runtime.spindle_angle < 180
    assert not runtime.inputs["SPINDLE_ORIENT_IN_POSITION"]
    assert runtime.outputs["SPINDLE_ORIENT_CMD"]
    for _ in range(45):
        runtime.tick(.1)
    assert runtime.status == "COMPLETE"
    assert runtime.spindle_angle == 180
    assert runtime.inputs["SPINDLE_ORIENT_IN_POSITION"]


def test_failed_m19_feedback_blocks_sequence():
    runtime = SimRuntime(failed_sensor="SPINDLE_ORIENT_IN_POSITION")
    runtime.start(4)
    finish(runtime)
    assert runtime.status == "FAULT"
    assert runtime.spindle_angle == 180
    assert runtime.waiting == "SPINDLE_ORIENT_IN_POSITION"
    assert not runtime.inputs["SPINDLE_ORIENT_IN_POSITION"]
    assert not runtime.inputs["ATC_DOOR_OPEN"]
