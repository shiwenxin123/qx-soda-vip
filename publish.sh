#!/bin/bash
# 一条命令建库并推送。前置：gh auth login 过一次。
set -e
REPO="${1:-qx-soda-vip}"
cd "$(dirname "$0")"

if ! gh auth status >/dev/null 2>&1; then
  echo "还没登录 GitHub，先跑： gh auth login -h github.com -s repo -w"
  exit 1
fi

git init -q 2>/dev/null || true
git branch -M main
git add -A
git -c user.name="$(gh api user -q .login)" \
    -c user.email="$(gh api user -q .id)+$(gh api user -q .login)@users.noreply.github.com" \
    commit -qm "QX rewrite script for Soda Music VIP" 2>/dev/null || true

if ! git remote get-url origin >/dev/null 2>&1; then
  gh repo create "$REPO" --public --source=. --remote=origin --push
else
  git push -u origin main
fi

USER=$(gh api user -q .login)
echo
echo "仓库   : https://github.com/$USER/$REPO"
echo "jsDelivr: https://cdn.jsdelivr.net/gh/$USER/$REPO@main/soda_vip_unlock.js"
echo "raw     : https://raw.githubusercontent.com/$USER/$REPO/main/soda_vip_unlock.js"
echo
echo "把上面任一地址填进 QX 规则："
echo "  ^https?:\\/\\/[^\\/]*qishui\\.com\\/ url script-response-body <上面的地址>"
