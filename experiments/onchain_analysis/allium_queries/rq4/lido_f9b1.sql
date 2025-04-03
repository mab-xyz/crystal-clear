SELECT
    from_address,
    to_address,
    COUNT(*) AS call_count
FROM ethereum.raw.traces
WHERE
    from_address = '0x889edc2edab5f40e902b864ad4d7ade8e412f9b1'
    AND trace_type = 'call'
    AND status = 1
    AND block_number > 17244958
GROUP BY
    from_address,
    to_address
ORDER BY
    call_count DESC;