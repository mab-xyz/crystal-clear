from typing import List

from pydantic import BaseModel, Field
from slither.core.cfg.node import Node
from slither.core.declarations.function import Function
from slither.core.variables.state_variable import StateVariable
from slither.slither import Slither


class PermissionedFunction(BaseModel):
    """Model representing a permissioned function in a contract."""

    function: str = Field(..., description="Function signature")
    state_variables: List[str] = Field(
        ..., description="State variables involved in permission checks"
    )
    conditions: List[str] = Field(
        ..., description="Conditions involving msg.sender or state variables"
    )

    def _to_dict(self):
        return self.model_dump()


class PermissionsInfo(BaseModel):
    """Model representing permission information of a contract."""

    permissions: List[PermissionedFunction] = Field(
        ..., description="Permissioned functions"
    )

    def to_dict(self):
        return {"permissions": [perm._to_dict() for perm in self.permissions]}


def get_msg_sender_checks(function: Function) -> List[Node]:
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


def check_owner_condition(
    checks: List[Node], state_variables_written: List[StateVariable]
) -> bool:
    for var in state_variables_written:
        if str(var.type) == "address":
            for check in checks:
                if var.name in [v.name for v in check.variables_read]:
                    return True
    return False


def detect_permissions(slither: Slither) -> PermissionsInfo:
    """
    Detect if the given address is an admin of any contract.

    Args:
        address (str): The address to check.
        etherscan_api_key (str): Etherscan API key for contract verification.
    Returns:
        bool: True if the address is an admin of any contract, False otherwise.
    """
    mainContract = get_main_contract_name(slither)

    contract = slither.get_contract_from_name(mainContract)[0]
    written_variables = []
    for super_contract in contract._inheritance:
        state_vars = super_contract.all_state_variables_written
        if state_vars:
            written_variables.extend(state_vars)
    written_variables.extend(contract.all_state_variables_written)
    written_variables = list(set(written_variables))
    if not written_variables:
        return PermissionsInfo(permissions=[])
    res = []
    for function in contract.functions:
        state_variables_written = [
            v.name for v in function.all_state_variables_written() if v.name
        ]
        msg_sender_condition = get_msg_sender_checks(function)
        if (
            len(state_variables_written) > 0
            and len(msg_sender_condition) > 0
            and check_owner_condition(msg_sender_condition, written_variables)
        ):
            res.append((function.name, state_variables_written, msg_sender_condition))
    cleaned_res = []
    for function, state_vars, conds in res:
        func = PermissionedFunction(
            function=function,
            state_variables=state_vars,
            conditions=[str(c.expression) for c in conds],
        )
        cleaned_res.append(func)
    return PermissionsInfo(permissions=cleaned_res)


def get_main_contract_name(slither: Slither) -> str:
    """
    Get the main contract name from a Slither object.

    Args:
        slither: Slither object

    Returns:
        Main contract name
    """
    return next(iter(slither._crytic_compile.compilation_units.keys()))
