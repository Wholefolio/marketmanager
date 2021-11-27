data = from(bucket: "marketmanager")
    |> range(start: -10m)
    |> filter(fn: (r) => r._measurement == "currencies_fiat")
    |> filter(fn: (r) => r._value > 0)
    |> drop(columns: ["exchange_id"])
    |> sort(columns: ["_time"])

data
    |> aggregateWindow(fn: mean, every: 5m)
    |> filter(fn: (r) => exists r._value)
    |> to(bucket: "marketmanager_aggregated", org: "wholefolio")