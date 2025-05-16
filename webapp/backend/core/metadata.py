import requests
from typing import Optional, List, Dict

def get_labels(addresses: List[str], ALLIUM_API_KEY: str) -> Optional[Dict[str, str]]:
    """
    Get labels for multiple Ethereum addresses from Etherscan.

    Args:
        addresses: List of Ethereum addresses to lookup

    Returns:
        dict: Dictionary mapping addresses to their labels
    """
    try:
        params = ""
        for address in addresses:
            # lowercase the address to ensure consistency
            params += f"'{address.lower()}',"
        params = params[:-1]  # Remove the last comma
        parameters = {"param_477":f"{params}"}
        print(parameters)

        response = requests.post(
            "https://api.allium.so/api/v1/explorer/queries/g23nJaD4vABOS6utYocZ/run",
            json=parameters,
            headers={"X-API-Key": ALLIUM_API_KEY},
        )

        print(response.json())
        json = response.json()
        if 'data' in json and len(json['data']) > 0:
            labels = {item['address']: item['name'] for item in json['data']}
            return labels
        else:
            return None
    except Exception as e:
        print(f"Error getting labels for addresses {addresses}: {e}")
        return None