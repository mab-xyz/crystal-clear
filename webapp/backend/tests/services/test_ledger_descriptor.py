import pytest

from src.api.services import ledger_descriptor as ld


def test_der_length_boundaries():
    assert ld.der_length(0) == b"\x00"
    assert ld.der_length(127) == b"\x7f"
    assert ld.der_length(128) == b"\x81\x80"
    assert ld.der_length(256) == b"\x82\x01\x00"


def test_tag_0x80_is_two_bytes():
    # Spec: tag 0x80 is encoded `81 80`.
    assert ld.tlv(0x80, b"\x01") == bytes.fromhex("818001" + "01")


def _fields(**kw):
    base = dict(
        address=bytes(range(20)),
        tx_hash=bytes(range(32)),
        risk=ld.RISK_RISK,
        category=ld.CATEGORY_CONTRACT,
        tiny_url="https://x.io/r/AbCdEfGh",
        simulation_type=ld.SIMULATION_TX,
        chain_id=1,
    )
    base.update(kw)
    return ld.DescriptorFields(**base)


def test_encode_known_vector():
    body = ld.encode_fields(_fields(tiny_url="u"))
    expected = (
        "010109"
        "020101"
        "23080000000000000001"
        "2214" + bytes(range(20)).hex()
        + "2720" + bytes(range(32)).hex()
        + "81800101"  # tag 0x80 is DER long form: 81 80
        + "81810103"
        + "81830175"
        + "81840100"
    )
    assert body.hex() == expected


def test_sign_and_verify_roundtrip_and_tamper():
    key = ld.load_private_key("11" * 32)
    pub = ld.public_key_compressed_hex(key)
    desc = ld.sign_descriptor(_fields(), key)
    assert ld.verify_descriptor(desc, pub)
    parsed = ld.parse_descriptor(desc)
    assert parsed[ld.TX_HASH] == bytes(range(32))
    assert parsed[ld.W3C_NORMALIZED_RISK] == b"\x01"
    bad = bytearray(desc)
    bad[10] ^= 0xFF
    assert not ld.verify_descriptor(bytes(bad), pub)


def test_optional_fields_omitted():
    parsed = ld.parse_descriptor(
        ld.encode_fields(_fields(chain_id=None, domain_hash=None))
    )
    assert ld.CHAIN_ID not in parsed
    assert ld.DOMAIN_HASH not in parsed
    assert ld.W3C_PROVIDER_MESSAGE not in parsed


def test_limits_enforced():
    with pytest.raises(ValueError):
        ld.encode_fields(_fields(tiny_url="x" * 31))
    with pytest.raises(ValueError):
        ld.encode_fields(_fields(provider_message="x" * 26))
    ld.encode_fields(_fields(tiny_url="x" * 30, provider_message="y" * 25))
    with pytest.raises(ValueError):
        ld.encode_fields(_fields(tx_hash=b"\x00" * 31))
    with pytest.raises(ValueError):
        ld.encode_fields(_fields(risk=3))
