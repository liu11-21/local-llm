"""Managed private IPv4 certificates using PyCA and Windows DPAPI."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from ipaddress import IPv4Address
from pathlib import Path
from secrets import token_urlsafe
import socket
import ssl
from tempfile import TemporaryDirectory

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from remote_client import parse_invite, protect
from remote_host import private_ip


def fingerprint(pem):
    return sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest().upper()


def inspect_invite(value):
    details = parse_invite(value)
    try:
        pin = fingerprint(details["certificate"])
    except ValueError:
        raise ValueError("邀請內的主機憑證無效。") from None
    return {"address":details["host"], "port":details["port"], "fingerprint":pin}


def private_addresses():
    addresses = set()
    try:
        rows = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET, socket.SOCK_STREAM)
    except OSError:
        return []
    for *_, address in rows:
        try:
            candidate = private_ip(address[0])
        except ValueError:
            continue
        if not IPv4Address(candidate).is_loopback:
            addresses.add(candidate)
    return sorted(addresses, key=IPv4Address)


def create_material(address):
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Local LLM Private Host")])
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=180)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5)).not_valid_after(expiry)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(IPv4Address(address))]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(key, hashes.SHA256()))
    password = token_urlsafe(32).encode("ascii")
    encrypted = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                  serialization.BestAvailableEncryption(password))
    return address, cert.public_bytes(serialization.Encoding.PEM), encrypted, protect(password), int(expiry.timestamp())


class ManagedTLS:
    def __init__(self, connect, host):
        self.connect, self.host = connect, host
        with connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS remote_tls(
                          id INTEGER PRIMARY KEY CHECK(id=1), address TEXT NOT NULL, cert BLOB NOT NULL,
                          encrypted_key BLOB NOT NULL, protected_password BLOB NOT NULL, expires INTEGER NOT NULL)""")
            if db.execute("PRAGMA user_version").fetchone()[0] < 7:
                db.execute("PRAGMA user_version=7")

    @staticmethod
    def read(db):
        return db.execute("SELECT address,cert,encrypted_key,protected_password,expires FROM remote_tls WHERE id=1").fetchone()

    def settings(self):
        with self.connect() as db:
            record = self.read(db)
            has_peers = db.execute("SELECT 1 FROM remote_host_grants LIMIT 1").fetchone() is not None
        return {"addresses": private_addresses(), "address": record[0] if record else None,
                "expires": record[4] if record else None, "has_peers": has_peers,
                "fingerprint": fingerprint(record[1].decode("ascii")) if record else None}

    def start(self, address, port, label, *, replace=False):
        address = private_ip(address)
        with self.connect() as db:
            saved = self.read(db)
            has_peers = db.execute("SELECT 1 FROM remote_host_grants LIMIT 1").fetchone() is not None
        expiry_threshold = int(datetime.now(timezone.utc).timestamp()) + 86400 * 14
        renew = bool(saved and (saved[0] != address or saved[4] <= expiry_threshold))
        if (renew or (not saved and has_peers)) and not replace:
            raise ValueError("需更新主機憑證。請確認撤銷舊配對後再啟用。")
        change = not saved or replace
        record = create_material(address) if change else saved

        def save(db):
            if change:
                db.execute("INSERT OR REPLACE INTO remote_tls VALUES(1,?,?,?,?,?)", record)
                db.execute("DELETE FROM remote_host_grants")

        with TemporaryDirectory(prefix="localllm-tls-") as folder:
            cert, key = Path(folder) / "cert.pem", Path(folder) / "encrypted-key.pem"
            cert.write_bytes(record[1])
            key.write_bytes(record[2])
            return self.host.start(address, port, label, str(cert), str(key),
                                   password=protect(record[3], decrypt=True), configure=save)
