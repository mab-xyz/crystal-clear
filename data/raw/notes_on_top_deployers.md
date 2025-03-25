1: 0x0de8bf93da2f7eecb3d9169422413a9bef4ef628
    CoinTool: XEN Batch Minter
    Owned by deployer EOA
    All created contracts are EIP-1167 minimal proxy standard, i.e. all calls to them are forwared to the creator contract

2: 0x0a252663dbcc0b073063d6420a40319e438cfa59
    XEN Crypto: XENT Token
    EIP-1167 minimal proxy forwards to this contract

3: 0x0000000000004946c0e9f43f4dee607b0ef1fa1c
    1inch: CHI Token
    gas token, each created contract is minimal and "stores gas unit" which then can be freed by destroying it

4: 0x881d4032abe4188e2237efcd27ab435e81fc6bb1
    Coinbase: Commerce
    EIP-1167 minimal proxy forwards to this contract: 0xf84C1073FB737E998d74F179e33a3946BD8462f0

5: 0xa3c1e324ca1ce40db73ed6026c4a177f099b5770
    Bittrex: Controller
    Creates user wallets
    controlled by owner/other admins
    * filed for bankrupcy and charged with "unregistered securities exchange"
6: 0xa5409ec958c83c3f309868babaca7c86dcb077c1
    OpenSea: Registry
    each child is an upgradedable proxy callable by the owner of the proxy or addrs approved by the registry

7: 0xffa397285ce46fb78c588a9e993286aac68c37cd
    Bitstamp: Forwarder Factory

8: 0x8a91c9a16cd62693649d80afa85a09dbbdcb8508
    MMM BSC
    bytecode

9: 0xa24787320ede4cc19d800bf87b41ab9539c4da9d
    Kraken: Deployer 2
    bytecode
    EIP-1167 to 0xd332254f274cc65aa11178b74734e2992b8f349e

10: 0x46d781c076596e1836f62461f150f387ad140c0e
    Contract Deployer
    bytecode
    proxy to 0x1ad92ece0ecf64cb5a4a443b2a214843a358e1a1