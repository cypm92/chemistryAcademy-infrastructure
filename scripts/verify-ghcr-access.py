#!/usr/bin/env python3
"""Verify private GHCR image pulls using a decrypted pull Secret from stdin.

Never print the Secret, registry credentials, or bearer tokens.
"""

import base64
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yaml


ROOT = Path(__file__).resolve().parents[1]
IMAGE_FILES = (
    ROOT / "kubernetes/apps/production/frontend.yaml",
    ROOT / "kubernetes/apps/production/backend.yaml",
)
ACCEPT = ", ".join(
    (
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    )
)


def image_references() -> list[str]:
    images = []
    for path in IMAGE_FILES:
        content = path.read_text(encoding="utf-8")
        match = re.search(r"^\s*image:\s*(ghcr\.io/cypm92/[^\s]+)$", content, re.M)
        if match is None or ":sha-" not in match.group(1):
            raise ValueError(f"Imagen inmutable ausente en {path.name}")
        images.append(match.group(1))
    return images


def registry_token(repository: str, authorization: str | None) -> str | None:
    query = urlencode({"scope": f"repository:{repository}:pull", "service": "ghcr.io"})
    headers = {"Accept": "application/json"}
    if authorization:
        headers["Authorization"] = authorization
    request = Request(f"https://ghcr.io/token?{query}", headers=headers)
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except HTTPError:
        return None
    return payload.get("token") or payload.get("access_token")


def manifest_status(repository: str, tag: str, bearer: str | None) -> int:
    if bearer is None:
        return 401
    headers = {"Accept": ACCEPT, "Authorization": f"Bearer {bearer}"}
    request = Request(
        f"https://ghcr.io/v2/{repository}/manifests/{tag}",
        headers=headers,
        method="HEAD",
    )
    try:
        with urlopen(request, timeout=15) as response:
            return response.status
    except HTTPError as error:
        return error.code


def github_token_valid(username: str, password: str) -> bool:
    request = Request(
        "https://api.github.com/user",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {password}",
            "User-Agent": "beciencia-ghcr-verification",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            account = json.load(response)
            scopes = response.headers.get("X-OAuth-Scopes", "")
            return (
                account.get("login") == username
                and "read:packages" in {scope.strip() for scope in scopes.split(",")}
            )
    except HTTPError:
        return False


def main() -> int:
    # The caller pipes SOPS output directly here: no plaintext file is created.
    secret = yaml.safe_load(sys.stdin)
    if not isinstance(secret, dict):
        raise ValueError("No se recibió un Secret descifrado")
    if secret.get("metadata", {}).get("name") != "ghcr-pull":
        raise ValueError("El Secret de entrada no es ghcr-pull")
    config = json.loads(secret["stringData"][".dockerconfigjson"])
    credentials = config["auths"]["ghcr.io"]
    username = credentials["username"]
    password = credentials["password"]
    if username != "cypm92" or not password:
        raise ValueError("La identidad de GHCR no coincide con la esperada")
    if not github_token_valid(username, password):
        print("ERROR: GitHub no acepta el token o le falta read:packages.")
        return 1
    print("OK: token de cypm92 válido y con read:packages")
    basic = base64.b64encode(f"{username}:{password}".encode()).decode()
    authorization = f"Basic {basic}"

    failed = False
    for image in image_references():
        repository_and_tag = image.removeprefix("ghcr.io/")
        repository, tag = repository_and_tag.rsplit(":", 1)
        authenticated = manifest_status(
            repository, tag, registry_token(repository, authorization)
        )
        anonymous = manifest_status(repository, tag, registry_token(repository, None))
        if authenticated == 200 and anonymous != 200:
            print(f"OK: {repository} — imagen accesible con token y no anónimamente")
        else:
            failed = True
            print(
                f"ERROR: {repository} — acceso autenticado HTTP {authenticated}; "
                f"anónimo HTTP {anonymous}"
            )
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyError, ValueError, yaml.YAMLError, URLError):
        print("ERROR: no se pudo validar el Secret o consultar GHCR (sin mostrar credenciales).")
        sys.exit(1)
