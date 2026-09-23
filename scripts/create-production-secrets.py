#!/usr/bin/env python3
"""Create production Kubernetes Secrets encrypted with SOPS, without plaintext files."""

import base64
from getpass import getpass
import json
from pathlib import Path
import re
import secrets
import shutil
import subprocess
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "kubernetes" / "clusters" / "production"
SOPS_IMAGE = (
    "ghcr.io/getsops/sops@"
    "sha256:ae501277bf742f1662e0f881f43dd8fd6798b489a8058e921dbf6cda597140ea"
)


def yaml_string(value: str) -> str:
    # JSON string literals are valid YAML scalars and escape special characters.
    return json.dumps(value, ensure_ascii=False)


def age_recipient() -> str:
    config = (ROOT / ".sops.yaml").read_text(encoding="utf-8")
    match = re.search(r"\bage1[0-9a-z]+\b", config)
    if match is None:
        raise RuntimeError("No se encontró el destinatario age en .sops.yaml")
    return match.group()


def encrypt(plaintext: str, name: str, recipient: str) -> str:
    result = subprocess.run(
        [
            "docker", "run", "--rm", "-i", SOPS_IMAGE,
            "encrypt", "--filename-override", f"kubernetes/clusters/production/{name}",
            "--age", recipient,
            "--encrypted-regex", "^(data|stringData)$",
            "--input-type", "yaml", "--output-type", "yaml",
        ],
        input=plaintext,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"SOPS no pudo cifrar {name}: {result.stderr.strip()}")
    if "ENC[" not in result.stdout or "\nsops:" not in result.stdout:
        raise RuntimeError(f"SOPS no devolvió un manifiesto cifrado válido para {name}")
    return result.stdout


def main() -> None:
    if shutil.which("docker") is None:
        raise RuntimeError("Instala o inicia Docker Desktop antes de continuar")

    runtime_path = DESTINATION / "runtime.sops.yaml"
    registry_path = DESTINATION / "ghcr-pull.sops.yaml"
    if runtime_path.exists() or registry_path.exists():
        raise RuntimeError(
            "Ya existe un Secret cifrado. Para rotarlo, sigue el procedimiento de rotación; "
            "este comando no sobrescribe las credenciales actuales."
        )

    print("Los valores que escribas aquí no se mostrarán ni se guardarán en claro.")
    admin_password = getpass("Contraseña inicial de Cresko (mínimo 16 caracteres): ")
    if len(admin_password) < 16:
        raise RuntimeError("La contraseña inicial debe tener al menos 16 caracteres")
    if admin_password != getpass("Repite la contraseña inicial: "):
        raise RuntimeError("Las contraseñas no coinciden")

    ghcr_token = getpass("Token clásico de GitHub con solo read:packages: ").strip()
    if not ghcr_token:
        raise RuntimeError("El token de lectura de GHCR no puede estar vacío")

    db_password = secrets.token_urlsafe(36)
    jwt_secret = secrets.token_urlsafe(48)
    database_url = (
        "postgresql+psycopg2://chemistry:"
        f"{quote(db_password, safe='')}@postgres:5432/chemistry_academy"
    )
    runtime = (
        "apiVersion: v1\nkind: Secret\nmetadata:\n"
        "  name: beciencia-runtime\n  namespace: beciencia\n"
        "type: Opaque\nstringData:\n"
        f"  POSTGRES_PASSWORD: {yaml_string(db_password)}\n"
        f"  DATABASE_URL: {yaml_string(database_url)}\n"
        f"  SECRET_KEY: {yaml_string(jwt_secret)}\n"
        f"  ADMIN_PASSWORD: {yaml_string(admin_password)}\n"
    )

    username = "cypm92"
    auth = base64.b64encode(f"{username}:{ghcr_token}".encode("utf-8")).decode("ascii")
    registry_config = json.dumps(
        {"auths": {"ghcr.io": {"username": username, "password": ghcr_token, "auth": auth}}},
        separators=(",", ":"),
    )
    registry = (
        "apiVersion: v1\nkind: Secret\nmetadata:\n"
        "  name: ghcr-pull\n  namespace: beciencia\n"
        "type: kubernetes.io/dockerconfigjson\nstringData:\n"
        f"  .dockerconfigjson: {yaml_string(registry_config)}\n"
    )

    recipient = age_recipient()
    encrypted_runtime = encrypt(runtime, runtime_path.name, recipient)
    encrypted_registry = encrypt(registry, registry_path.name, recipient)
    for value in (admin_password, ghcr_token, db_password, jwt_secret):
        if value in encrypted_runtime or value in encrypted_registry:
            raise RuntimeError("Se ha detectado un valor sin cifrar; no se guardará ningún fichero")

    # Open exclusively: running this helper again must never overwrite working credentials.
    with runtime_path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(encrypted_runtime)
    with registry_path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(encrypted_registry)
    print("Creados runtime.sops.yaml y ghcr-pull.sops.yaml (solo contenido cifrado).")
    print("No compartas tu contraseña ni el token; guarda también el acceso a sus cuentas.")


if __name__ == "__main__":
    main()
