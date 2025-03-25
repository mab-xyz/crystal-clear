WITH
    created_after AS (
        SELECT
            to_address AS address,
            block_number AS bnumber,
            transaction_hash AS tx_hash,
            block_timestamp AS btime
        FROM
            ethereum.raw.traces
        WHERE
            status = 1
            AND (
                trace_type = 'create'
                OR trace_type = 'create2'
            )
            AND block_number >= 19426587 /* cancun fork */
            AND block_number <= 21525890 /* last block of 2024*/
        GROUP BY
            to_address,
            block_number,
            transaction_hash,
            block_timestamp
    ),
    suicided_after AS (
        SELECT
            from_address AS address,
            block_number AS bnumber,
            transaction_hash AS tx_hash
        FROM
            ethereum.raw.traces
        WHERE
            status = 1
            AND trace_type = 'suicide'
            AND block_number >= 19426587 /* cancun fork */
            AND block_number <= 21525890
        GROUP BY
            from_address,
            block_number,
            transaction_hash
    ),
    alive_after AS (
        SELECT
            created_after.address,
            created_after.bnumber,
            created_after.btime
        FROM
            created_after
            LEFT JOIN suicided_after ON (
                created_after.address = suicided_after.address
                AND created_after.tx_hash = suicided_after.tx_hash
            )
        WHERE
            suicided_after.address IS NULL
    ),
    created_before AS (
        SELECT
            to_address AS address,
            MAX(block_number) AS bnumber,
            MAX(block_timestamp) AS btime
        FROM
            ethereum.raw.traces
        WHERE
            (
                trace_type = 'create'
                OR trace_type = 'create2'
            )
            AND status = 1
            AND block_number < 19426587
        GROUP BY
            to_address
    ),
    suicided_before AS (
        SELECT
            from_address AS address,
            MAX(block_number) AS bnumber
        FROM
            ethereum.raw.traces
        WHERE
            block_number < 19426587 /* cancun fork */
            AND trace_type = 'suicide'
            AND status = 1
        GROUP BY
            from_address
    ),
    alive_before AS (
        SELECT DISTINCT
            created_before.address,
            created_before.bnumber,
            btime
        FROM
            created_before
            LEFT JOIN suicided_before ON created_before.address = suicided_before.address
        WHERE
            suicided_before.address IS NULL
            OR created_before.bnumber > suicided_before.bnumber
    ),
    alive AS (
        SELECT
            *
        FROM
            alive_before
        UNION ALL
        SELECT
            *
        FROM
            alive_after
    )
SELECT
    COUNT(*)
FROM
    alive
    -- order by bnumber