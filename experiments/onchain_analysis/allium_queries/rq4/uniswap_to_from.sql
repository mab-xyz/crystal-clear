WITH
    from_count AS (
        SELECT
            to_address,
            COUNT(DISTINCT from_address) AS distinct_from_address_count
        FROM
            ethereum.raw.traces
        WHERE
            LOWER(to_address) IN (
                '0x1f98431c8ad98523631ae4a59f267346ea31f984',
                '0x5ba1e12693dc8f9c48aad8770482f4739beed696',
                '0xb753548f6e010e7e680ba186f9ca1bdab2e90cf2',
                '0xbfd8137f7d1516d3ea5ca83523914859ec47f573',
                '0xb27308f9f90d607463bb33ea1bebb41c27ce5ab6',
                '0xe592427a0aece92de3edee1f18e0157c05861564',
                '0x42b24a95702b9986e82d421cc3568932790a48ec',
                '0x91ae842a5ffd8d12023116943e72a606179294f3',
                '0xee6a57ec80ea46401049e92587e52f5ec1c24785',
                '0xc36442b4a4522e871399cd717abdd847ab11fe88',
                '0xa5644e29708357803b5a882d272c41cc0df92b34',
                '0x61ffe014ba17989e743c5f6cb21bf9697530b21e',
                '0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45',
                '0x000000000022d473030f116ddee9f6b43ac78ba3',
                '0x66a9893cc07d91d95644aedd05d03f95e1dba8af',
                '0xe34139463ba50bd61336e0c446bd8c0867c6fe65',
                '0x000000000004444c5dc75cb358380d2e3de08a90',
                '0xd1428ba554f4c8450b763a0b2040a4935c63f06c',
                '0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e',
                '0x52f0e24d1c21c8a0cb1e5a5dd6198556bd9e1203',
                '0x7ffe42c4a5deea5b0fec41c94c136cf115597227',
                '0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f',
                '0x7a250d5630b4cf539739df2c5dacb4c659f2488d',
                '0x00000011f84b9aa48e5f8aa8b9897600006289be',
                '0x6000da47483062a0d734ba3dc7576ce6a0b645c4',
                '0x54539967a06fc0e3c3ed0ee320eb67362d13c5ff'
            )
            AND trace_type = 'call'
            AND status = 1
        GROUP BY
            to_address
    ),
    to_count AS (
        SELECT
            from_address,
            COUNT(DISTINCT to_address) AS distinct_to_address_count
        FROM
            ethereum.raw.traces
        WHERE
            LOWER(from_address) IN (
                '0x1f98431c8ad98523631ae4a59f267346ea31f984',
                '0x5ba1e12693dc8f9c48aad8770482f4739beed696',
                '0xb753548f6e010e7e680ba186f9ca1bdab2e90cf2',
                '0xbfd8137f7d1516d3ea5ca83523914859ec47f573',
                '0xb27308f9f90d607463bb33ea1bebb41c27ce5ab6',
                '0xe592427a0aece92de3edee1f18e0157c05861564',
                '0x42b24a95702b9986e82d421cc3568932790a48ec',
                '0x91ae842a5ffd8d12023116943e72a606179294f3',
                '0xee6a57ec80ea46401049e92587e52f5ec1c24785',
                '0xc36442b4a4522e871399cd717abdd847ab11fe88',
                '0xa5644e29708357803b5a882d272c41cc0df92b34',
                '0x61ffe014ba17989e743c5f6cb21bf9697530b21e',
                '0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45',
                '0x000000000022d473030f116ddee9f6b43ac78ba3',
                '0x66a9893cc07d91d95644aedd05d03f95e1dba8af',
                '0xe34139463ba50bd61336e0c446bd8c0867c6fe65',
                '0x000000000004444c5dc75cb358380d2e3de08a90',
                '0xd1428ba554f4c8450b763a0b2040a4935c63f06c',
                '0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e',
                '0x52f0e24d1c21c8a0cb1e5a5dd6198556bd9e1203',
                '0x7ffe42c4a5deea5b0fec41c94c136cf115597227',
                '0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f',
                '0x7a250d5630b4cf539739df2c5dacb4c659f2488d',
                '0x00000011f84b9aa48e5f8aa8b9897600006289be',
                '0x6000da47483062a0d734ba3dc7576ce6a0b645c4',
                '0x54539967a06fc0e3c3ed0ee320eb67362d13c5ff'
            )
            AND trace_type = 'call'
            AND status = 1
        GROUP BY
            from_address
    )
SELECT
    from_count.to_address AS address,
    from_count.distinct_from_address_count AS from_address_count,
    to_count.distinct_to_address_count AS to_address_count
FROM
    from_count
    JOIN to_count ON from_count.to_address = to_count.from_address
ORDER BY
    to_address_count desc;