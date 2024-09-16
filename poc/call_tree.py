
from evm_trace import CallType, ParityTraceList, get_calltree_from_parity_trace, get_unique_addresses_from_parity_trace

def get_block_calltree(web3, block_number, contract_address):
    raw_trace_list = web3.manager.request_blocking("trace_block", [block_number])
    txs_hashes = set()
    for trace in raw_trace_list:
        if trace['type'] == 'call' and trace['action']['from'].lower() == contract_address.lower():
            txs_hashes.add(trace['transactionHash'])
    if (len(txs_hashes) == 0):
        return None
    list_hashes = list(txs_hashes)

    calltrees = {}
    for tx_hash in list_hashes:
        traces = []
        for tr in raw_trace_list:
            if tr['transactionHash'] == tx_hash:
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


def get_blocks_called_addresses(web3, start_block, end_block, contract_address):
    addresses = set()
    for block in range(start_block, end_block):
        called = get_block_called_addresses(web3, block, contract_address)
        if called == None:
            continue
        addresses.update(called)
    number_of_addr = len(addresses)
    print("Number of called contracts:", number_of_addr)
    if number_of_addr > 0:
        print("Addresses:")
        for a in addresses:
            print(a)
        print()


def get_block_called_addresses(web3, block_number, contract_address):
    raw_trace_list = web3.manager.request_blocking("trace_block", [block_number])
    txs_hashes = set()
    for trace in raw_trace_list:
        if trace['type'] == 'call' and trace['action']['from'].lower() == contract_address.lower():
            txs_hashes.add(trace['transactionHash'])
    if (len(txs_hashes) == 0):
        return None
    list_hashes = list(txs_hashes)

    addresses = set()
    for tx_hash in list_hashes:
        traces = []
        for tr in raw_trace_list:
            if tr['transactionHash'] == tx_hash:
                traces.append(tr)
        trace_list = ParityTraceList.model_validate(traces)
        addresses = get_unique_addresses_from_parity_trace(trace_list)
    addresses.discard(contract_address)
    only_contracts = set()
    for a in addresses:
        code = web3.eth.get_code(web3.to_checksum_address(a))
        if code.hex() != "":
            only_contracts.add(a)

    return only_contracts
