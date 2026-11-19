#!/usr/bin/env bash
# The release workflow supplies a fresh clone of the Wiki default branch.
set -euo pipefail
wiki_dir=${1:?Expected a clean Wiki clone}
pages_dir="$(cd "$(dirname "$0")/../../docs/github-wiki" && pwd)"
if [[ -n "$(git -C "$wiki_dir" status --porcelain)" ]]; then
  echo "Wiki checkout has pending changes" >&2
  exit 1
fi
stage_pages() {
  local wiki_dir=$1
  cp "$pages_dir/Home.md" "$pages_dir/_Sidebar.md" "$wiki_dir/"
  git -C "$wiki_dir" add -- Home.md _Sidebar.md
  if git -C "$wiki_dir" diff --cached --quiet; then
    echo "Wiki pages already match the site release"
    return 0
  fi
  git -C "$wiki_dir" -c user.name='github-actions[bot]' \
    -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
    commit -m 'Publish reviewed ADLC5 Wiki landing pages'
}

stage_pages "$wiki_dir"
if git -C "$wiki_dir" push origin HEAD; then
  exit 0
fi

# A Wiki editor may have advanced the default branch since checkout. Apply the
# two release-owned files to its new tip and preserve all other pages.
retry_dir=$(mktemp -d)
trap 'rm -rf "$retry_dir"' EXIT
git clone --depth 1 "$(git -C "$wiki_dir" remote get-url origin)" "$retry_dir"
stage_pages "$retry_dir"
git -C "$retry_dir" push origin HEAD
