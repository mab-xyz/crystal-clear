SELECT
  DATE_TRUNC('year', block_timestamp) AS year,
  COUNT(DISTINCT CASE WHEN to_address IS NOT NULL THEN to_address END) AS nodes_count,
  COUNT(*) AS edges_count,
  COUNT(call_type) AS distinct_call_types,
  COUNT(CASE WHEN call_type = 'call' THEN 1 END) AS call_count_call,
  COUNT(CASE WHEN call_type = 'delegatecall' THEN 1 END) AS call_count_delegatecall,
  COUNT(CASE WHEN call_type = 'staticcall' THEN 1 END) AS call_count_staticcall,
  COUNT(CASE WHEN call_type = 'callcode' THEN 1 END) AS call_count_callcode
FROM ethereum.raw.traces
WHERE
  trace_type = 'call'
  AND status = 1
  AND to_address IS NOT NULL
  AND from_address IS NOT NULL
  AND block_number <= 21525889
GROUP BY
  DATE_TRUNC('year', block_timestamp)
ORDER BY
  year;

-- RUN_ID = "3NlwsJ9AuPuV5ws35dKo_20250127T134412_feign"