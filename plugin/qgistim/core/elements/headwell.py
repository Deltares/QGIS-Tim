class HeadWellSchema:
    schemata = {
        "head": [AllValueSchema()],
        "radius": [AllValueSchema(), PositiveSchema()],
        "resistance": [AllValueSchema(), PositiveSchema()],
        "layer": [AllValueSchema(), MemberschipSchema("layers")],
    }


class TransientHeadWellSchema:
    schemata = {
        "timeseries_id": [MembershipSchema("timeseries_ids")],
    }
    consistency_schemata = (
        AllOrNoneSchema(("time_start", "time_end", "head_transient")),
        XorSchema("time_start", "timeseries_id"),
    )
