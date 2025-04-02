WITH TraceSummary AS (
    SELECT
        to_address,
        call_type,
        COUNT(*) AS call_count
    FROM
        ethereum.raw.traces
    WHERE
        to_address IS NOT NULL 
        AND block_number <= 21525890 
        AND block_number >= 18908895
        AND trace_type = 'call'
        AND status = 1
    GROUP BY
        to_address,
        call_type
),
TopCallees AS (
    SELECT
        to_address,
        call_type,
        call_count,
        ROW_NUMBER() OVER (PARTITION BY call_type ORDER BY call_count DESC) AS row_num
    FROM
        TraceSummary
)
SELECT
    to_address,
    call_type,
    call_count
FROM
    TopCallees
WHERE
    row_num <= 10
ORDER BY
    call_type,
    call_count DESC;

-- RUN_ID = "sA0Q4wmTe47s8XsN8iYa_20250208T135005_unfit"