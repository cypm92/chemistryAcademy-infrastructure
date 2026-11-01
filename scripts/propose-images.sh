#!/usr/bin/env bash
set -euo pipefail
branch='automation/promote-production-images'
base="$(git rev-parse HEAD)"
gh auth setup-git
git fetch origin main
python3 scripts/promotion_branch.py base "$base" "$(git rev-parse FETCH_HEAD)"
previous="$(git ls-remote --heads origin "refs/heads/$branch" | cut -f1)"
if [ -n "$previous" ]; then
  git fetch origin "refs/heads/$branch"
  test "$(git rev-parse FETCH_HEAD)" = "$previous"
  python3 scripts/promotion_branch.py previous "$base" "$previous"
fi
prs="$(gh pr list --base main --state open --limit 1000 --json number,headRefName,headRepositoryOwner --jq '.[] | [.number, .headRefName, .headRepositoryOwner.login] | @tsv')"
own_pr=''
while IFS=$'\t' read -r number head owner; do
  [ -n "$number" ] || continue
  if [ "$head" = "$branch" ] && [ "$owner" = "${GITHUB_REPOSITORY%/*}" ]; then
    [ -z "$own_pr" ] || { echo 'Más de una PR de automatización' >&2; exit 1; }
    own_pr="$number"
    continue
  fi
  files="$(gh api --paginate "repos/$GITHUB_REPOSITORY/pulls/$number/files" --jq '.[].filename')"
  if printf '%s\n' "$files" | grep -Fxq -e kubernetes/apps/production/backend.yaml -e kubernetes/apps/production/frontend.yaml -e kubernetes/apps/production/notification-worker.yaml -e kubernetes/clusters/production/image-promotion-state.json; then
    echo "PR #$number también modifica imágenes/estado: revisar antes de continuar." >&2
    exit 1
  fi
done <<< "$prs"
if [ -n "$own_pr" ] && [ -z "$previous" ]; then
  echo 'PR sin rama verificada; intervención necesaria' >&2; exit 1
fi
ensure_unreviewed() {
  [ -n "$own_pr" ] || return 0
  local data sha draft reviews comments labels
  data="$(gh pr view "$own_pr" --json headRefOid,isDraft,reviews,comments,labels --jq '[.headRefOid, (.isDraft|tostring), (.reviews|length|tostring), (.comments|length|tostring), (.labels|length|tostring)] | @tsv')"
  IFS=$'\t' read -r sha draft reviews comments labels <<< "$data"
  if [ "$sha" != "$previous" ] || [ "$draft" != 'false' ] || [ "$reviews" != '0' ] || [ "$comments" != '0' ] || [ "$labels" != '0' ]; then
    echo 'La PR automática contiene revisión o contexto humano, o cambió su rama; requiere intervención.' >&2
    return 1
  fi
}
python3 scripts/promote-images.py --apply
paths=(kubernetes/apps/production/backend.yaml kubernetes/apps/production/frontend.yaml kubernetes/apps/production/notification-worker.yaml kubernetes/clusters/production/image-promotion-state.json)
if git diff --quiet -- "${paths[@]}"; then
  if [ -n "$own_pr" ]; then
    ensure_unreviewed
    gh pr close "$own_pr" --comment 'La propuesta ya no contiene imágenes nuevas sobre main; se cierra sin fusionar.'
  fi
  echo 'No hay imágenes nuevas que proponer.'
  exit 0
fi
git fetch origin main
python3 scripts/promotion_branch.py base "$base" "$(git rev-parse FETCH_HEAD)"
git config user.name 'beciencia-promotion[bot]'
git config user.email 'beciencia-promotion[bot]@users.noreply.github.com'
git add -- "${paths[@]}"
git commit -m 'Promote published main images'
if ! python3 scripts/promotion_branch.py same "$previous" HEAD; then
  ensure_unreviewed
  git push --force-with-lease="refs/heads/$branch:$previous" origin "HEAD:refs/heads/$branch"
else
  echo 'Propuesta idéntica: se conserva la rama y sus revisiones.'
fi
if [ -z "$own_pr" ]; then
  gh pr create --base main --head "$branch" \
    --title 'Promover imágenes publicadas desde main' \
    --body 'Verifica CI y publicación GHCR; requiere revisión y merge manual a main. Backend y worker comparten imagen.'
else
  echo "PR #$own_pr actualizada; pendiente de revisión."
fi
