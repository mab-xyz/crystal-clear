from scsc.supply_chain import SupplyChain

if __name__ == "__main__":
    url = "http://localhost:8545"
    contract_address = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
    sc = SupplyChain(url, contract_address)
    sc.collect_calls("0x14c3b86", "0x14c3b90")
    deps = sc.get_all_dependencies()
    print(deps)
    sc.export_json(f"{contract_address}.json")