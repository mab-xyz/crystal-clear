import re
import subprocess

# def run_sevm_command(bytecode_file):
#     """
#     Run the `sevm sol bytecode.txt` command and capture the output (Solidity source code).
#     """
#     command = ["sevm", "sol", bytecode_file]
#     result = subprocess.run(command, capture_output=True, text=True)

#     if result.returncode == 0:
#         return result.stdout.splitlines()  # Return the output as lines
#     else:
#         print(f"Error running command on {bytecode_file}: {result.stderr}")
#         return None


def run_sevm_command(address, rpc_url):
    """
    Run the `sevm sol address` command and capture the output (Solidity source code).
    """
    command = ["sevm", "sol", address, "--rpc-url", rpc_url]
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode == 0:
        return result.stdout.splitlines()  # Return the output as lines
    else:
        print(f"Error running command on {command}: {result.stderr}")
        return None


def clean_line(line):
    """
    Clean the line of code by removing comments and extra spaces.
    """
    return re.sub(
        r"//.*", "", line
    ).strip()  # Remove comments (anything after "//") and extra spaces


def detect_keccak256_traces(all_lines):
    """
    Detect keccak256 usage and track the local variables or storage being assigned based on it.
    Returns a mapping of keccak256-derived variables to storage slots.
    """
    keccak256_traces = {}
    keccak_pattern = r"keccak256\((.*?)\)"  # Match keccak256(...)

    for _, line in enumerate(all_lines):
        cleaned_line = clean_line(line)
        match = re.search(keccak_pattern, cleaned_line)
        if match:
            keccak_value = match.group(1)  # Value passed to keccak256
            # Capture local variable assignment to the keccak256 result
            storage_assign_pattern = r"(\w+)\s*=\s*keccak256"
            storage_match = re.search(storage_assign_pattern, cleaned_line)
            if storage_match:
                local_variable = storage_match.group(1)
                keccak256_traces[
                    local_variable
                ] = keccak_value  # Store trace: local_variable -> keccak256 value
    return keccak256_traces


def detect_storage_assignments(keccak256_traces, all_lines):
    """
    Detect storage assignments using the keccak256 result.
    Tracks the storage locations assigned with the implementation address.
    """
    storage_assignments = {}
    for variable, keccak_value in keccak256_traces.items():
        for line in all_lines:
            cleaned_line = clean_line(line)
            # Detect storage[keccak256 value] = <address>
            storage_pattern = rf"storage\[{variable}\]\s*=\s*(.+);"
            match = re.search(storage_pattern, cleaned_line)
            if match:
                assigned_value = match.group(1)
                storage_assignments[
                    keccak_value
                ] = assigned_value  # Trace the assignment
    return storage_assignments


def extract_implementation_address(delegatecall_line):
    """
    Extract the second parameter (variable or address) inside the delegatecall, ignoring operations and hex values.
    """
    delegatecall_pattern = r"delegatecall\([^,]+,\s*(.*?),"
    match = re.search(delegatecall_pattern, delegatecall_line)

    if match:
        second_param = match.group(1).strip()

        # Remove operations and hex values to isolate variables
        variables = extract_variables_from_expression(second_param)

        if variables:
            return variables[
                0
            ]  # Return the first variable as the implementation address

    return None


def extract_variables_from_expression(expression):
    """
    Extract variables from an expression by removing hex values and numbers.
    """
    # Remove hex values and numbers
    expression = re.sub(r"0x[a-fA-F0-9]+", "", expression)
    expression = re.sub(r"\b\d+\b", "", expression)

    # Remove operators
    expression = re.sub(r"[&|>>|<<|\+|\-|\*|/|%|\^|\(|\)]", " ", expression)

    # Split into tokens
    tokens = expression.split()

    # Filter out empty tokens and keywords
    keywords = {
        "msg",
        "gasleft",
        "memory",
        "storage",
        "require",
        "return",
        "if",
        "else",
        "revert",
        "assert",
        "gas",
        "this",
        "keccak256",
        "true",
        "false",
    }
    variables = [token for token in tokens if token and token not in keywords]

    return variables


def is_hex_or_operation(param):
    """
    Check if the parameter contains hex, shift operators, or arithmetic operations.
    If it's a hex or part of a shift operation, we consider it an operation or constant.
    """
    # Check if param is a hex value, operator, or a number
    return bool(re.fullmatch(r"0x[0-9a-fA-F]+|\d+|[+\-*/&|^%~]|<<|>>", param))


def is_hardcoded_address(param):
    """
    Check if the parameter is a hardcoded 20-byte hexadecimal address.
    """
    # A 20-byte address is 40 hexadecimal characters long, starting with '0x'
    return bool(re.fullmatch(r"0x[a-fA-F0-9]{40}", param.strip()))


# Newly added functions to match the original logic


def find_function_boundaries(lines):
    """
    Identify function boundaries using 'function', '{', and '}'.
    """
    functions = {}
    current_function = None
    open_braces = 0

    for idx, line in enumerate(lines):
        cleaned_line = clean_line(line)
        # Identify function declarations
        function_match = re.match(r"(function\s.*?|fallback\(\))\s*{", cleaned_line)
        if function_match:
            current_function = idx
            functions[current_function] = {
                "start": idx,
                "end": None,
                "delegatecall": False,
                "name": function_match.group(1),
            }
            open_braces = cleaned_line.count("{") - cleaned_line.count("}")
        else:
            open_braces += cleaned_line.count("{") - cleaned_line.count("}")
        if open_braces == 0 and current_function is not None:
            functions[current_function]["end"] = idx
            current_function = None

    # Ensure all functions have an end; if not found, assume it's the last line
    for func in functions:
        if functions[func]["end"] is None:
            functions[func]["end"] = (
                len(lines) - 1
            )  # Set end to last line if no closing brace found
    return functions


def mark_delegatecall_functions(delegatecall_lines, functions, all_lines):
    """
    Mark functions that contain delegatecalls.
    """
    for function_start, function_boundaries in functions.items():
        for idx in range(function_boundaries["start"], function_boundaries["end"] + 1):
            cleaned_line = clean_line(all_lines[idx])
            if "delegatecall" in cleaned_line:
                functions[function_start]["delegatecall"] = True
                break


def identify_fallback_function(functions, all_lines):
    """
    Identify the fallback function among the functions.
    The fallback function is the one explicitly named 'fallback()'.
    """
    fallback_function_index = None
    for function_start, func_info in functions.items():
        function_name = func_info.get("name", "")
        if function_name.strip() == "fallback()":
            fallback_function_index = function_start
            break
    return fallback_function_index


def trace_variable(
    variable_name, all_lines, current_line_index, visited_variables=None
):
    """
    Recursively trace the assignments of a variable to find its origin(s).
    """
    if visited_variables is None:
        visited_variables = set()
    if variable_name in visited_variables:
        return []
    visited_variables.add(variable_name)

    # Collect origins
    origins = []

    # Search for assignments to the variable before the current line
    assignment_found = False
    for idx in range(
        current_line_index - 1, -1, -1
    ):  # Search from current line upwards
        cleaned_line = clean_line(all_lines[idx])

        # Check for assignment to the variable
        # Pattern to match variable assignments: variable = RHS;
        assignment_pattern = re.compile(rf"\b{re.escape(variable_name)}\s*=\s*(.+);")
        match = assignment_pattern.search(cleaned_line)
        if match:
            assignment_found = True
            rhs = match.group(1)

            # Check if RHS is a hardcoded address
            if is_hardcoded_address(rhs.strip()):
                origins.append(rhs.strip())
            else:
                # Extract variables from RHS
                rhs_variables = extract_variables_from_expression(rhs)
                for var in rhs_variables:
                    origins.extend(
                        trace_variable(var, all_lines, idx, visited_variables)
                    )
            break

    if not assignment_found:
        origins.append(variable_name)  # Assume it's a state variable

    return origins


def check_assignments_outside_fallback(
    variable_name, functions, fallback_function_index, all_lines
):
    """
    Check for assignments to the state variable in functions other than the fallback function.
    Returns a list of assignments.
    """
    assignments_outside_fallback = []
    assignment_pattern = re.compile(rf"\b{re.escape(variable_name)}\s*=\s*(.+);")

    for func_start, func_info in functions.items():
        if func_start != fallback_function_index:
            # Search for assignments within this function
            start_idx = func_info["start"]
            end_idx = func_info["end"]
            for idx in range(start_idx, end_idx + 1):
                cleaned_line = clean_line(all_lines[idx])
                match = assignment_pattern.search(cleaned_line)
                if match:
                    rhs = match.group(1)
                    assignments_outside_fallback.append(
                        {"line_number": idx, "assignment": f"{variable_name} = {rhs};"}
                    )
    return assignments_outside_fallback


def detect_delegatecall_and_address(address, rpc_url):
    print("Running SEVM command to decompile bytecode...")
    # Run the SEVM command to generate Solidity code from the bytecode
    decompiled_output = run_sevm_command(address, rpc_url)

    # If SEVM fails to decompile the bytecode, return a default classification
    if decompiled_output is None:
        return "Unknown", "Failed to decompile bytecode", None
    print("SEVM command executed successfully.")
    all_lines = decompiled_output
    delegatecall_lines = [
        (idx, line)
        for idx, line in enumerate(all_lines)
        if "delegatecall" in clean_line(line)
    ]

    if not delegatecall_lines:
        return "Not a proxy", "No delegatecall found", all_lines

    keccak256_traces = detect_keccak256_traces(all_lines)
    storage_assignments = detect_storage_assignments(keccak256_traces, all_lines)

    functions = find_function_boundaries(all_lines)
    fallback_function_index = identify_fallback_function(functions, all_lines)
    mark_delegatecall_functions(
        [line for idx, line in delegatecall_lines], functions, all_lines
    )

    for delegatecall_line_index, line in delegatecall_lines:
        implementation_variable = extract_implementation_address(line)

        if implementation_variable:
            origins = trace_variable(
                implementation_variable, all_lines, delegatecall_line_index
            )
            if any(is_hardcoded_address(origin) for origin in origins):
                return (
                    "Forward proxy",
                    "Forward proxy with hardcoded address",
                    all_lines,
                )

            if any(origin in storage_assignments for origin in origins):
                return (
                    "Upgradeable proxy",
                    f"Variable {implementation_variable} retrieved from storage",
                    all_lines,
                )

            assignments = check_assignments_outside_fallback(
                implementation_variable, functions, fallback_function_index, all_lines
            )
            if assignments:
                return (
                    "Upgradeable proxy",
                    f"Variable {implementation_variable} assigned outside the fallback function",
                    all_lines,
                )
            else:
                return (
                    "Forward proxy",
                    f"No assignments to {implementation_variable} outside the fallback function",
                    all_lines,
                )
    return "Forward proxy", "No valid implementation assignment found", all_lines


def save_bytecode_to_file(bytecode, file_path="bytecode.txt"):
    """
    Saves the bytecode to a text file for further processing.
    """
    with open(file_path, "w") as f:
        f.write(bytecode)


def main():
    bytecode = input("Enter the bytecode file: ")

    # Save the bytecode to a file
    # save_bytecode_to_file(bytecode)
    # Detect the proxy type and implementation address
    proxy_type, message, all_lines = detect_delegatecall_and_address(bytecode)
    print(f"Proxy Type: {proxy_type}")
    print(f"Message: {message}")


if __name__ == "__main__":
    main()
