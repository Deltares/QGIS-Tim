class CircularAreaSinkSchema:
    schemata = {
        "rate": Required(),
        "layer": Required(Membership("aquifer layers")),
    }


class TransientCircularAreaSinkSchema:
    consistency_schemata = (
        AllOrNone("time_start", "time_end", "rate_transient"),
        NotBoth("time_start", "timeseries_id"),
    )
    schemata = {
        "time_start": Optional(Time()),
        "time_end": Optional(Time()),
        "timeseries_id": Optional(Membership("timeseries_ids")),
    }
