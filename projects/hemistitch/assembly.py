"""Hemistitch assembly orchestrator — placeholder for v0.6 Fusion-Python export.

Once the Fusion-Python export feature ships, this module will import each part
generator from ./parts/, feed it the parameter block from params.json, and
assemble the result in the active Fusion design.

Expected final shape:

    from lib.profiles.cushion import cushion_profile
    from lib.operations.extrude import extrude
    from .parts import case_middle, bezel, caseback, lug, motor_bracket

    def build(design, params):
        case_middle.build(design, params['case_middle'])
        bezel.build(design, params['bezel'])
        caseback.build(design, params['caseback'])
        for i in range(4):
            lug.build(design, params[f'lug_{i}'])
        motor_bracket.build(design, params['motor_bracket'])

Deferred until v0.6 per SIMULATOR_SPEC.md §7 roadmap.
"""
