#!/usr/bin/env bash
set -euo pipefail

mode=$1
source=$2
source_ref=$3
mirror=$4
mirror_ref=$5
case "$mode" in check|push) ;; *) exit 2 ;; esac
git check-ref-format "$source_ref"
git check-ref-format "$mirror_ref"
case "$mirror_ref" in refs/heads/*|refs/tags/*) ;; *) exit 2 ;; esac

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
git init --quiet --bare "$work"
cd "$work"
git fetch --quiet --no-tags "$source" "$source_ref"
source_oid=$(git rev-parse FETCH_HEAD)

result=$(git ls-remote --refs "$mirror" "$mirror_ref")
mirror_oid=$(awk -v ref="$mirror_ref" '$2 == ref {print $1}' <<< "$result")
if [[ "$source_oid" == "$mirror_oid" ]]; then
    echo "$mirror_ref already matches $source_oid"
    exit 0
fi

if [[ -n "$mirror_oid" ]]; then
    if [[ "$mirror_ref" == refs/tags/* ]] ||
        ! git cat-file -e "$mirror_oid^{commit}" 2>/dev/null ||
        ! git merge-base --is-ancestor "$mirror_oid" "$source_oid"; then
        echo "::error::Gitee $mirror_ref diverged. Reconcile this ref before syncing it."
        exit 1
    fi
fi

if [[ "$mode" == push ]]; then
    git push --porcelain "$mirror" "$source_oid:$mirror_ref"
    published=$(git ls-remote --refs "$mirror" "$mirror_ref" | awk -v ref="$mirror_ref" '$2 == ref {print $1}')
    [[ "$published" == "$source_oid" ]]
fi
echo "$mirror_ref can advance to $source_oid"
