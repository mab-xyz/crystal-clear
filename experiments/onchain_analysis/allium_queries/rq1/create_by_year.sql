SELECT
  EXTRACT(
    YEAR
    FROM
      block_timestamp
  ) AS YEAR,
  COUNT(*) AS trace_count
FROM
  ethereum.raw.traces
WHERE
  status = 1
  AND trace_type IN ('create', 'create2')
GROUP BY
  YEAR
ORDER BY
  YEAR;