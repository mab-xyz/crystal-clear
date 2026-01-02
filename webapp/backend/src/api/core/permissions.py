from slither.slither import Slither
from slither.core.declarations.function import Function
from typing import List
import requests

from src.api.core.config import settings

def get_msg_sender_checks(function: Function) -> List[str]:
        all_functions = (
            [
                ir.function
                for ir in function.all_internal_calls()
                if isinstance(ir.function, Function)
            ]
            + [function]
            + [m for m in function.modifiers if isinstance(m, Function)]
        )

        all_nodes_ = [f.nodes for f in all_functions]
        all_nodes = [item for sublist in all_nodes_ for item in sublist]

        all_conditional_nodes = [
            n for n in all_nodes if n.contains_if() or n.contains_require_or_assert()
        ]
        all_conditional_nodes_on_msg_sender = [
            n
            for n in all_conditional_nodes
            if "msg.sender" in [v.name for v in n.solidity_variables_read]
        ]
        return all_conditional_nodes_on_msg_sender

def check_onwer_condition(checks, state_variables_written):
    for var in state_variables_written:
        if str(var.type) == "address":
            for check in checks:
                if var.name in [v.name for v in check.variables_read]:
                    return True
    return False

def detect_permissions(path, mainContract, etherscan_api_key=None):
    """
    Detect if the given address is an admin of any contract.
    
    Args:
        address (str): The address to check.
        etherscan_api_key (str): Etherscan API key for contract verification.
    Returns:
        bool: True if the address is an admin of any contract, False otherwise.
    """
    if etherscan_api_key:
        slither = Slither(path, etherscan_api_key=etherscan_api_key, disallow_partial=True)
    else:
        slither = Slither(path, disallow_partial=True)    

    contract = slither.get_contract_from_name(mainContract)[0]
    written_variables = []
    for super_contract in contract._inheritance:
        state_vars = super_contract.all_state_variables_written
        if state_vars:
            written_variables.extend(state_vars)
    written_variables.extend(contract.all_state_variables_written)
    written_variables = list(set(written_variables))
    if not written_variables:
        print("No state variables written in the contract.")
        return []
    res = []
    for function in contract.functions:

        state_variables_written = [
            v.name for v in function.all_state_variables_written() if v.name
        ]
        msg_sender_condition = get_msg_sender_checks(function)
        if len(state_variables_written) > 0 and len(msg_sender_condition) > 0 and check_onwer_condition(msg_sender_condition, written_variables):
            res.append((function.name, state_variables_written, msg_sender_condition))
    cleaned_res = []
    for function, state_vars, conds in res:
        func = {}
        func["function"] = function
        func["state_variables"] = state_vars
        func["conditions"] = [ str(c.expression) for c in conds]
        cleaned_res.append(func)
    return cleaned_res

def get_contract_sourcecode(address, api_key, chain_id=1):
    url = "https://api.etherscan.io/v2/api"
    params = {
        "chainid": chain_id,
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
        "apikey": api_key
    }

    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API request failed with status code {response.status_code}")

def get_permissions(address: str):
    """
    Get permissioned functions of a contract.

    Args:
        address: Ethereum contract address

    Returns:
        Permissioned functions
    
    Raises:
        ValueError: If no source code is found for the address
        RuntimeError: If there's any other error fetching permissions info
    """
    try:
        res = get_contract_sourcecode(address, settings.etherscan_api_key)
        if not res or 'result' not in res or len(res['result']) == 0:
            raise ValueError(f"No source code found for address {address}")
        contract_name = res['result'][0]['ContractName']

        permission_info = detect_permissions(address, contract_name, etherscan_api_key=settings.etherscan_api_key)
        return permission_info
    except ValueError as ve:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to get permissions info: {str(e)}") from e