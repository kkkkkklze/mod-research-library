#!/bin/bash
# 克隆代表性 mod 仓库(浅克隆, 优先 1.21.1/neoforge 分支)
# 落地目录：仓库根/源码库/_参考仓库（可用 REF_REPO_DIR 覆盖）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REF="${REF_REPO_DIR:-$SCRIPT_DIR/../源码库/_参考仓库}"
mkdir -p "$REF" && cd "$REF" || exit 1

clone_repo() {
  local url="$1"
  local name=$(basename "$url")
  if [ -d "$name" ]; then echo "SKIP $name (exists)"; return; fi
  # 找合适的分支
  local heads=$(git ls-remote --heads "$url" 2>/dev/null | sed 's#.*refs/heads/##')
  local branch=""
  for pat in "1.21.1" "1.21" "neoforge/1.21.1" "dev/1.21.1" "main" "master" "dev" "1.21.x"; do
    if echo "$heads" | grep -qx "$pat"; then branch="$pat"; break; fi
  done
  if [ -z "$branch" ]; then
    # 尝试含 1.21 的分支
    branch=$(echo "$heads" | grep -E '^1\.21' | head -1)
  fi
  if [ -z "$branch" ]; then
    echo "CLONE $name (default branch)"
    git clone --depth 1 --quiet "$url" "$name" 2>&1 | tail -2
  else
    echo "CLONE $name (branch=$branch)"
    git clone --depth 1 --quiet -b "$branch" "$url" "$name" 2>&1 | tail -2
  fi
  if [ -d "$name" ]; then
    echo "  size: $(du -sm "$name" 2>/dev/null | cut -f1) MB  branch: $(git -C "$name" branch --show-current 2>/dev/null)"
  fi
}

clone_repo https://github.com/vectorwing/FarmersDelight
clone_repo https://github.com/TartaricAcid/TouhouLittleMaid
clone_repo https://github.com/Snownee/Jade
clone_repo https://github.com/noobanidus/Lootr
clone_repo https://github.com/mrh0/createaddition
clone_repo https://github.com/Minecraft-LightLand/L2Library
clone_repo https://github.com/KaleidoscopeMods/KaleidoscopeCookery
clone_repo https://github.com/malte0811/FerriteCore
clone_repo https://github.com/squeek502/AppleSkin
clone_repo https://github.com/0999312/umapyo
echo "ALL CLONES DONE"
ls -la
