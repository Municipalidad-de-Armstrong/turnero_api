from app.core.security import (
    decrypt_pii,
    encrypt_pii,
    hash_dni_hmac,
    hash_password,
    mask_dni,
    mask_phone,
    verify_password,
    create_access_token,
    decode_access_token,
)


def test_password_hashing():
    pwd = "MySecretPassword123!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_pii_encryption_decryption():
    raw_dni = "38123456"
    raw_phone = "3471556677"

    enc_dni = encrypt_pii(raw_dni)
    enc_phone = encrypt_pii(raw_phone)

    assert enc_dni != raw_dni
    assert enc_phone != raw_phone

    assert decrypt_pii(enc_dni) == raw_dni
    assert decrypt_pii(enc_phone) == raw_phone


def test_dni_hmac_hashing():
    dni_1 = "38.123.456"
    dni_2 = "38123456"
    dni_different = "38123457"

    hmac_1 = hash_dni_hmac(dni_1)
    hmac_2 = hash_dni_hmac(dni_2)
    hmac_diff = hash_dni_hmac(dni_different)

    # HMAC must be deterministic regardless of dots
    assert hmac_1 == hmac_2
    assert hmac_1 != hmac_diff
    assert len(hmac_1) == 64  # SHA256 hex digest length


def test_pii_masking():
    assert mask_dni("38123456") == "XX.XXX.456"
    assert mask_phone("3471556677") == "XXXX-XX6677"
    assert mask_dni("12") == "***"
    assert mask_phone("123") == "****"


def test_jwt_creation_and_decoding():
    payload = {"sub": "123", "role": "ciudadano"}
    token = create_access_token(payload)
    decoded = decode_access_token(token)

    assert decoded["sub"] == "123"
    assert decoded["role"] == "ciudadano"
    assert "exp" in decoded
