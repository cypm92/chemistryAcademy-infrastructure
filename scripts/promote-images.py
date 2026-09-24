"""Promote only images built successfully from each application's main branch.

Run in an infrastructure checkout of develop. No credential is printed or saved.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "kubernetes/clusters/production/image-promotion-state.json"
APPS = {
    "backend": {
        "repository": "chemistryAcademy-backend",
        "manifest": ROOT / "kubernetes/apps/production/backend.yaml",
    },
    "frontend": {
        "repository": "chemistryAcademy-frontend",
        "manifest": ROOT / "kubernetes/apps/production/frontend.yaml",
    },
}
OWNER = "cypm92"
PUBLISH_JOB = "Publicar imagen de producción en GHCR"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def github_get(path: str, token: str) -> dict:
    request = Request(
        f"https://api.github.com/{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "beciencia-image-promotion",
        },
    )
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def published_main_sha(repository: str, token: str) -> str:
    base = f"repos/{OWNER}/{repository}"
    sha = github_get(f"{base}/branches/main", token)["commit"]["sha"]
    if not SHA_PATTERN.fullmatch(sha):
        raise ValueError(f"SHA principal inválido para {repository}")

    runs = github_get(
        f"{base}/actions/workflows/ci.yml/runs?branch=main&event=push&per_page=30",
        token,
    )["workflow_runs"]
    matching = next((run for run in runs if run["head_sha"] == sha), None)
    if matching is None or matching["status"] != "completed":
        raise RuntimeError(f"CI de main pendiente o ausente para {repository} ({sha})")
    if matching["conclusion"] != "success":
        raise RuntimeError(f"CI de main no pasó para {repository} ({sha})")

    jobs = github_get(
        f"{base}/actions/runs/{matching['id']}/jobs?per_page=100", token
    )["jobs"]
    published = [job for job in jobs if job["name"] == PUBLISH_JOB]
    if len(published) != 1 or published[0]["conclusion"] != "success":
        raise RuntimeError(f"La imagen de {repository} no se publicó correctamente")
    return sha


def replace_image(contents: str, app: str, sha: str) -> str:
    if not SHA_PATTERN.fullmatch(sha):
        raise ValueError("SHA de imagen inválido")
    pattern = re.compile(
        rf"(?m)^([ \t]*image: ghcr\.io/{OWNER}/beciencia-{app}:sha-)[0-9a-f]{{40}}$"
    )
    replaced, count = pattern.subn(lambda match: match.group(1) + sha, contents)
    if count != 1:
        raise ValueError(f"Se esperaban exactamente una imagen de {app}; hay {count}")
    return replaced


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Actualizar manifiestos y estado")
    args = parser.parse_args()
    token = os.environ.get("GH_TOKEN")
    if not token:
        parser.error("Falta GH_TOKEN con lectura de los repositorios de aplicación")

    state = json.loads(STATE.read_text(encoding="utf-8"))
    if set(state) != set(APPS):
        raise ValueError("El estado de promoción no coincide con las aplicaciones")
    changes: dict[str, str] = {}
    for app, config in APPS.items():
        sha = published_main_sha(config["repository"], token)
        if state[app] == sha:
            print(f"{app}: sin nuevo commit publicado en main")
            continue
        manifest = config["manifest"]
        updated = replace_image(manifest.read_text(encoding="utf-8"), app, sha)
        changes[app] = updated
        print(f"{app}: nueva imagen publicada sha-{sha}")

    if not changes:
        return 0
    if not args.apply:
        print("Simulación: usa --apply para actualizar manifiestos y estado")
        return 0

    for app, updated in changes.items():
        APPS[app]["manifest"].write_text(updated, encoding="utf-8", newline="\n")
        state[app] = re.search(r"beciencia-" + app + r":sha-([0-9a-f]{40})", updated).group(1)
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (HTTPError, URLError, KeyError, ValueError, RuntimeError) as error:
        print(f"Promoción detenida: {error}", file=sys.stderr)
        sys.exit(1)
