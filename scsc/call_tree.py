from evm_trace import (
    CallType,
    ParityTraceList,
    get_calltree_from_parity_trace,
    get_unique_addresses_from_parity_trace,
)


def get_block_calltree(web3, block_number, contract_address):
    raw_trace_list = web3.manager.request_blocking("trace_block", [block_number])
    txs_hashes = set()
    for trace in raw_trace_list:
        if (
            trace["type"] == "call"
            and trace["action"]["from"].lower() == contract_address.lower()
        ):
            txs_hashes.add(trace["transactionHash"])
    if len(txs_hashes) == 0:
        return None
    list_hashes = list(txs_hashes)

    calltrees = {}
    for tx_hash in list_hashes:
        traces = []
        for tr in raw_trace_list:
            if tr["transactionHash"] == tx_hash:
                traces.append(tr)
        trace_list = ParityTraceList.model_validate(traces)
        calltree = get_calltree_from_parity_trace(trace_list)
        calltrees.setdefault(tx_hash, []).append(calltree)
    return calltrees


def get_blocks_calltree(web3, start_block, end_block, contract_address):
    for block in range(start_block, end_block):
        calltrees = get_block_calltree(web3, block, contract_address)
        if calltrees == None:
            continue
        for tx_hash in calltrees:
            print("Block Number:", block)
            print("Tx Hash:", tx_hash)
            print(calltrees[tx_hash])
            print()


def get_blocks_called_addresses(
    web3, start_block, end_block, contract_address, show_calls=False
):
    addresses = {}
    for block in range(start_block, end_block):
        called = get_block_called_addresses(web3, block, contract_address)
        if called is None:
            continue
        for addr, count in called.items():
            addresses[addr] = addresses.get(addr, 0) + count

    result = {
        "main_contract": contract_address,
        "called_contracts": [
            {"address": addr, "count": count} for addr, count in addresses.items()
        ],
        "total_calls": sum(addresses.values()),
        "unique_contracts": len(addresses),
    }

    if show_calls:
        print("Number of called contracts:", result["unique_contracts"])
        print("Total number of calls:", result["total_calls"])
        print("Addresses:")
        for contract in result["called_contracts"]:
            print(f"{contract['address']}: {contract['count']}")
        print()

    return result


def get_block_called_addresses(web3, block_number, contract_address):
    raw_trace_list = web3.manager.request_blocking("trace_block", [block_number])
    txs_hashes = set()
    for trace in raw_trace_list:
        if (
            trace["type"] == "call"
            and trace["action"]["from"].lower() == contract_address.lower()
        ):
            txs_hashes.add(trace["transactionHash"])
    if len(txs_hashes) == 0:
        return None
    list_hashes = list(txs_hashes)

    addresses = {}
    for tx_hash in list_hashes:
        traces = [tr for tr in raw_trace_list if tr["transactionHash"] == tx_hash]

        # 计算每个地址在这个交易中被调用的次数
        for trace in traces:
            if "action" in trace and "to" in trace["action"]:
                to_address = trace["action"]["to"].lower()
                addresses[to_address] = addresses.get(to_address, 0) + 1
            if (
                trace["type"] == "create"
                and "result" in trace
                and "address" in trace["result"]
            ):
                created_address = trace["result"]["address"].lower()
                addresses[created_address] = addresses.get(created_address, 0) + 1

    # 移除合约自身的地址
    if contract_address.lower() in addresses:
        del addresses[contract_address.lower()]

    only_contracts = {}
    for a, count in addresses.items():
        code = web3.eth.get_code(web3.to_checksum_address(a))
        if code.hex() != "":
            only_contracts[a] = count

    return only_contracts
