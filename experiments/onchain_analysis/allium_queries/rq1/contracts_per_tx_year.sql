WITH
    contracts AS (
        SELECT
            to_address AS address
        FROM
            ethereum.raw.traces
        WHERE
            status = 1
            AND trace_type IN ('create', 'create2')
        GROUP BY
            to_address
    ),
    traces AS (
        SELECT
            transaction_hash,
            from_address,
            to_address
        FROM
            ethereum.raw.traces
        WHERE
            status = 1
            AND trace_type = 'call'
            AND EXTRACT(YEAR, block_timestamp) = 2024 -- change to the select year
    ),
    contract_calls AS (
        SELECT
            t.transaction_hash,
            t.from_address,
            t.to_address
        FROM
            traces t
            JOIN contracts a_from ON t.from_address = a_from.address
            JOIN contracts a_to ON t.to_address = a_to.address
    ),
    union_traces AS (
        SELECT
            transaction_hash,
            from_address AS address
        FROM
            contract_calls
        WHERE
            from_address IS NOT NULL
        UNION ALL
        SELECT
            transaction_hash,
            to_address AS address
        FROM
            contract_calls
        WHERE
            to_address IS NOT NULL
    ),
    distinct_counts AS (
        SELECT
            transaction_hash,
            COUNT(DISTINCT address) AS distinct_addresses_called
        FROM
            union_traces
        GROUP BY
            transaction_hash
    )
SELECT
    distinct_addresses_called,
    COUNT(*)
FROM
    distinct_counts
GROUP BY
    distinct_addresses_called