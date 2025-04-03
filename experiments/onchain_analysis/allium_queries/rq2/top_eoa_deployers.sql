WITH RECURSIVE
    contract_chain AS (
        -- Base case: select all direct contract creations, starting at depth 1
        SELECT
            from_address AS original_creator,
            to_address,
            1 AS depth
        FROM
            ethereum.raw.traces
        WHERE
            status = 1
            AND (
                trace_type = 'create'
                OR trace_type = 'create2'
            )
        UNION ALL
        -- Recursive case: trace back to the creators of the created contracts (subcontracts)
        SELECT
            t.from_address AS original_creator,
            c.to_address,
            c.depth + 1
        FROM
            ethereum.raw.traces t
            JOIN contract_chain c ON t.to_address = c.original_creator
        WHERE
            t.status = 1
            AND (
                t.trace_type = 'create'
                OR t.trace_type = 'create2'
            )
    )
    -- Final selection: Count contracts created and filter EOAs
SELECT
    original_creator,
    COUNT(DISTINCT to_address) AS total_created_contracts,
    MAX(depth) AS max_depth
FROM
    contract_chain
    -- Ensure original_creator is an EOA (not a contract)
WHERE
    NOT EXISTS (
        SELECT
            1
        FROM
            ethereum.raw.contracts c
        WHERE
            c.address = contract_chain.original_creator
    )
GROUP BY
    original_creator
ORDER BY
    total_created_contracts DESC
LIMIT
    100;