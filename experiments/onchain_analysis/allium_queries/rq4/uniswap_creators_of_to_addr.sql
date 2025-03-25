WITH
    call_counts AS (
        SELECT
            LOWER(from_address) AS from_address,
            LOWER(to_address) AS to_address,
            COUNT(*) AS call_count
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
                '0x54539967a06fc0e3c3ed0ee320eb67362d13c5ff',
                '0x1f9840a85d5af5bf1d1762f925bdaddc4201f984',
                '0x1a9c8182c09f50c8318d769245bea52c32be35bc',
                '0x5e4be8bc9637f0eaa1a755019e06a68ce081d58f',
                '0xc4e172459f1e7939d522503b81afaac1014ce6f6',
                '0x408ed6354d4973f66138c91495f2f2fcbd8724c3',
                '0x090d4613473dee047c3f2706764f49e0821d256e',
                '0x3032ab3fa8c01d786d29dade018d7f2017918e12',
                '0x6c3e4cb2e96b01f4b866965a91ed4437839a121a',
                '0x7fba4b8dc5e7616e59622806932dbea72537a56b',
                '0xa1484c3aa22a66c62b77e0ae78e15258bd0cb711',
                '0xca35e32e7926b96a9988f61d510e038108d8068e',
                '0x4750c43867ef5f89869132eccf19b9b6c4286e1a',
                '0xe3953d9d317b834592ab58ab2c7a6ad22b54075d',
                '0x4b4e140d1f131fdad6fb59c13af796fd194e4135',
                '0x3d30b1ab88d487b0f3061f40de76845bec3f1e94',
                '0x18e433c7bf8a2e1d0197ce5d8f9afada1a771360',
                '0xdaf819c2437a82f9e01f6586207ebf961a7f0970'
            )
            AND trace_type = 'call'
            AND status = 1
            AND LOWER(to_address) != '0x0000000000000000000000000000000000000001'
            AND LOWER(to_address) != LOWER(from_address)
        GROUP BY
            from_address,
            to_address
    ),
    ranked_calls AS (
        SELECT
            from_address,
            to_address,
            call_count,
            ROW_NUMBER() OVER (
                PARTITION BY
                    from_address
                ORDER BY
                    call_count DESC,
                    to_address ASC
            ) AS rn
        FROM
            call_counts
    ),
    top_n_calls AS (
        SELECT
            from_address,
            to_address,
            call_count
        FROM
            ranked_calls
        WHERE
            rn <= 5
        ORDER BY
            from_address,
            call_count DESC,
            to_address ASC
    )
    --   ,to_addr AS (
    --   SELECT to_address
    --   FROM top_n_calls
    --   GROUP BY to_address
    -- )
    -- , creators AS (
    --   SELECT
    --     lower(from_address) as from_address,
    --     lower(to_address) as to_address
    --   FROM
    --     ethereum.raw.traces
    --   WHERE
    --     status = 1
    --     AND trace_type IN ('create', 'create2')
    --     AND LOWER(from_address) IN (
    --       '0x1f98431c8ad98523631ae4a59f267346ea31f984',
    --       '0x5ba1e12693dc8f9c48aad8770482f4739beed696',
    --       '0xb753548f6e010e7e680ba186f9ca1bdab2e90cf2',
    --       '0xbfd8137f7d1516d3ea5ca83523914859ec47f573',
    --       '0xb27308f9f90d607463bb33ea1bebb41c27ce5ab6',
    --       '0xe592427a0aece92de3edee1f18e0157c05861564',
    --       '0x42b24a95702b9986e82d421cc3568932790a48ec',
    --       '0x91ae842a5ffd8d12023116943e72a606179294f3',
    --       '0xee6a57ec80ea46401049e92587e52f5ec1c24785',
    --       '0xc36442b4a4522e871399cd717abdd847ab11fe88',
    --       '0xa5644e29708357803b5a882d272c41cc0df92b34',
    --       '0x61ffe014ba17989e743c5f6cb21bf9697530b21e',
    --       '0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45',
    --       '0x000000000022d473030f116ddee9f6b43ac78ba3',
    --       '0x66a9893cc07d91d95644aedd05d03f95e1dba8af',
    --       '0xe34139463ba50bd61336e0c446bd8c0867c6fe65',
    --       '0x000000000004444c5dc75cb358380d2e3de08a90',
    --       '0xd1428ba554f4c8450b763a0b2040a4935c63f06c',
    --       '0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e',
    --       '0x52f0e24d1c21c8a0cb1e5a5dd6198556bd9e1203',
    --       '0x7ffe42c4a5deea5b0fec41c94c136cf115597227',
    --       '0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f',
    --       '0x7a250d5630b4cf539739df2c5dacb4c659f2488d',
    --       '0x00000011f84b9aa48e5f8aa8b9897600006289be',
    --       '0x6000da47483062a0d734ba3dc7576ce6a0b645c4',
    --       '0x54539967a06fc0e3c3ed0ee320eb67362d13c5ff',
    --       '0x4e59b44847b379578588920ca78fbf26c0b4956c', -- creators
    --       '0xe60ae42e7497f488ea682270e0918d3677bb637d',
    --       '0x48e516b34a1274f49457b9c6182097796d0498cb',
    --       '0x6c9fc64a53c1b71fb3f9af64d1ae3a4931a5f4e9',
    --       '0x9c33eacc2f50e39940d3afaf2c7b8246b681a374',
    --       '0x1b5caa1d3a1582a438e4cd93ee7a7e0e4d5624fb'
    --     )
    -- )
    -- , same_creators as (
    -- select *
    -- from top_n_calls t join creators c on c.to_address = t.to_address 
    -- )
SELECT
    *
FROM
    top_n_calls