from src.api.crud.deployment import create_deployment, get_deployment
from src.api.models.deployment import DeploymentCreate


def test_create_and_get_deployment(session):
    # Create a deployment
    deployment_data = DeploymentCreate(
        address="0xABC123",
        deployer="0xfactorycontract",
        deployer_eoa="0xdeployereoa",
        tx_hash="0xtxhash",
        block_number=123456,
    )
    created = create_deployment(session, deployment_data)

    # Check returned object
    assert created.address == "0xABC123"
    assert created.deployer == "0xfactorycontract"
    assert created.deployer_eoa == "0xdeployereoa"
    assert created.tx_hash == "0xtxhash"
    assert created.block_number == 123456

    # Get deployment by address
    fetched = get_deployment(session, "0xABC123")
    assert fetched is not None
    assert fetched.address == "0xABC123"
    assert fetched.deployer == "0xfactorycontract"
    assert fetched.deployer_eoa == "0xdeployereoa"
    assert fetched.tx_hash == "0xtxhash"
    assert fetched.block_number == 123456
    # Getting non-existent deployment returns None
    non_existent = get_deployment(session, "0xDEADBEF")
    assert non_existent is None
