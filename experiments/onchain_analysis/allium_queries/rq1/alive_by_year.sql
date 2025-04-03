WITH
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
            AND EXTRACT(YEAR, block_timestamp) < 2023 -- change for any year before 2024
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
            -- block_number <= 18908894 /* last block of 2023 */
            EXTRACT(YEAR, block_timestamp) < 2023 -- change for any year before 2024
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
    )
SELECT
    COUNT(*)
FROM
    alive_before