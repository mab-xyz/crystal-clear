import pytest
from unittest.mock import patch, MagicMock
from src.api.clients.allium_client import AlliumClient


class TestAlliumClient:
    @pytest.fixture
    def client(self):
        return AlliumClient(api_key="test_api_key")

    @patch("src.api.clients.base_client.requests.request")
    def test_get_labels_success(self, mock_request, client):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"address": "0x123", "name": "Contract A"},
                {"address": "0xabc", "name": "Contract B"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Call the method
        addresses = ["0x123", "0xABC"]
        result = client.get_labels(addresses)

        # Assert the correct API call was made
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert "g23nJaD4vABOS6utYocZ/run" in call_args[0][1]
        assert call_args[1]["json"] == {"param_477": "'0x123','0xabc'"}

        # Assert the result is correct
        assert result == {"0x123": "Contract A", "0xabc": "Contract B"}

    @patch("src.api.clients.base_client.requests.request")
    def test_get_labels_empty_addresses(self, mock_request, client):
        # Test with empty addresses list
        result = client.get_labels([])
        assert result is None
        mock_request.assert_not_called()

    @patch("src.api.clients.base_client.requests.request")
    def test_get_labels_no_data(self, mock_request, client):
        # Setup mock response with no data
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Some error"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Call the method
        result = client.get_labels(["0x123"])

        # Assert result is None when no data
        assert result is None

    @patch("src.api.clients.base_client.requests.request")
    def test_get_deployment_success(self, mock_request, client):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "address": "0x123",
                    "deployer": "0xdeployer",
                    "block_number": 12345
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Call the method
        result = client.get_deployment("0x123")

        # Assert the correct API call was made
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert "zz57rFHkFDf69LFLWsX4/run" in call_args[0][1]
        assert call_args[1]["json"] == {"param_191": "0x123"}

        # Assert the result is correct
        expected = {
            "address": "0x123",
            "deployer": "0xdeployer",
            "block_number": 12345
        }
        assert result == expected

    @patch("src.api.clients.base_client.requests.request")
    def test_get_deployment_empty_address(self, mock_request, client):
        # Test with empty address
        result = client.get_deployment("")
        assert result is None
        mock_request.assert_not_called()

    @patch("src.api.clients.base_client.requests.request")
    def test_get_deployment_no_data(self, mock_request, client):
        # Setup mock response with empty data list
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Call the method
        result = client.get_deployment("0x123")

        # Assert result is None when no data
        assert result is None

    @patch("src.api.clients.base_client.requests.request")
    def test_get_contract_dependencies_success(self, mock_request, client):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "from_address": "0x123",
                    "to_address": "0x456",
                    "call_type": "call",
                    "call_count": 10,
                    "n_matching_transactions": 5
                },
                {
                    "from_address": "0x123",
                    "to_address": "0x789",
                    "call_type": "delegate",
                    "call_count": 3,
                    "n_matching_transactions": 2
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Call the method
        result = client.get_contract_dependencies("0x123", "1000000", "2000000")

        # Assert the correct API call was made
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert "Iovn51yTlL1FamnKu2BH/run" in call_args[0][1]
        assert call_args[1]["json"] == {
            "param_87": "1000000",
            "param_43": "2000000",
            "param_97": "0x123"
        }

        # Assert the result is correct
        expected = {
            "address": "0x123",
            "from_block": 1000000,
            "to_block": 2000000,
            "n_nodes": 3,
            "n_matching_transactions": 7,
            "nodes": ["0x123", "0x456", "0x789"],
            "edges": [
                {"source": "0x123", "target": "0x456", "types": {"CALL": 10}},
                {"source": "0x123", "target": "0x789", "types": {"DELEGATE": 3}}
            ]
        }
        
        # Since the order of nodes in the list isn't guaranteed, we need to check separately
        assert result["address"] == expected["address"]
        assert result["from_block"] == expected["from_block"]
        assert result["to_block"] == expected["to_block"]
        assert result["n_nodes"] == expected["n_nodes"]
        assert result["n_matching_transactions"] == expected["n_matching_transactions"]
        assert set(result["nodes"]) == set(expected["nodes"])
        
        # Check edges
        assert len(result["edges"]) == len(expected["edges"])
        for edge in result["edges"]:
            matching_edge = next((e for e in expected["edges"] if e["source"] == edge["source"] and e["target"] == edge["target"]), None)
            assert matching_edge is not None
            assert edge["types"] == matching_edge["types"]

    @patch("src.api.clients.base_client.requests.request")
    def test_get_contract_dependencies_missing_params(self, mock_request, client):
        # Test with missing parameters
        result = client.get_contract_dependencies("", "1000000", "2000000")
        assert result is None
        mock_request.assert_not_called()

        result = client.get_contract_dependencies("0x123", "", "2000000")
        assert result is None
        mock_request.assert_not_called()

        result = client.get_contract_dependencies("0x123", "1000000", "")
        assert result is None
        mock_request.assert_not_called()

    @patch("src.api.clients.base_client.requests.request")
    def test_get_contract_dependencies_no_data(self, mock_request, client):
        # Setup mock response with no data
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Some error"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Call the method
        result = client.get_contract_dependencies("0x123", "1000000", "2000000")

        # Assert result is None when no data
        assert result is None

    @patch("src.api.clients.base_client.requests.request")
    def test_get_contract_dependencies_latest_success(self, mock_request, client):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "from_address": "0x123",
                    "to_address": "0x456",
                    "call_type": "call",
                    "call_count": 10,
                    "n_matching_transactions": 5,
                    "from_block": 1000000,
                    "to_block": 1000020
                },
                {
                    "from_address": "0x123",
                    "to_address": "0x789",
                    "call_type": "delegate",
                    "call_count": 3,
                    "n_matching_transactions": 2,
                    "from_block": 1000000,
                    "to_block": 1000020
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Call the method
        result = client.get_contract_dependencies_latest("0x123", 20)

        # Assert the correct API call was made
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert "N8wWhdIF1OWEALVQVQlA/run" in call_args[0][1]
        assert call_args[1]["json"] == {
            "param_69": "20",
            "param_97": "0x123"
        }

        # Assert the result is correct
        expected = {
            "address": "0x123",
            "from_block": 1000000,
            "to_block": 1000020,
            "n_nodes": 3,
            "n_matching_transactions": 7,
            "nodes": ["0x123", "0x456", "0x789"],
            "edges": [
                {"source": "0x123", "target": "0x456", "types": {"CALL": 10}},
                {"source": "0x123", "target": "0x789", "types": {"DELEGATE": 3}}
            ]
        }
        
        # Since the order of nodes in the list isn't guaranteed, we need to check separately
        assert result["address"] == expected["address"]
        assert result["from_block"] == expected["from_block"]
        assert result["to_block"] == expected["to_block"]
        assert result["n_nodes"] == expected["n_nodes"]
        assert result["n_matching_transactions"] == expected["n_matching_transactions"]
        assert set(result["nodes"]) == set(expected["nodes"])
        
        # Check edges
        assert len(result["edges"]) == len(expected["edges"])
        for edge in result["edges"]:
            matching_edge = next((e for e in expected["edges"] if e["source"] == edge["source"] and e["target"] == edge["target"]), None)
            assert matching_edge is not None
            assert edge["types"] == matching_edge["types"]

    @patch("src.api.clients.base_client.requests.request")
    def test_get_contract_dependencies_latest_default_block_range(self, mock_request, client):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "from_address": "0xabc",
                    "to_address": "0xdef",
                    "call_type": "call",
                    "call_count": 5,
                    "n_matching_transactions": 2,
                    "from_block": 2000000,
                    "to_block": 2000010
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Call the method with default block_range
        result = client.get_contract_dependencies_latest("0xabc")

        # Assert the correct API call was made with default block_range=10
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]["json"] == {
            "param_69": "10",
            "param_97": "0xabc"
        }

        # Verify result
        assert result["address"] == "0xabc"
        assert result["from_block"] == 2000000
        assert result["to_block"] == 2000010
        assert result["n_matching_transactions"] == 2

    @patch("src.api.clients.base_client.requests.request")
    def test_get_contract_dependencies_latest_no_data(self, mock_request, client):
        # Setup mock response with no data
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Some error"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Call the method
        result = client.get_contract_dependencies_latest("0x123", 10)

        # Assert result is None when no data
        assert result is None
