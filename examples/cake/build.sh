#!/bin/sh
# バースデーケーキアイコンのアニメーション WebP を生成する
# 素材は Twemoji の SVG (CC-BY 4.0)。帰属表記はリポジトリ直下の NOTICE にある
#
# 必要なコマンド: python3 / resvg / magick / img2webp / webpmux
#   brew install resvg imagemagick webp
#
# 使い方: cd examples/cake && ./build.sh
# 出力先は OUT で変えられる (既定はこのディレクトリの cake.webp)
# フレーム数や振幅は環境変数で振れる (gen.py 冒頭を参照)
set -e
cd "$(dirname "$0")"

readonly ID="cake"

# アニメーションの一辺 (px)
SIZE=${SIZE:-192}
export SIZE

readonly OUT="${OUT:-./$ID.webp}"
readonly OUT_DIR="$(dirname "$OUT")"

for cmd in python3 resvg magick img2webp webpmux; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "error: $cmd が見つからない" >&2
    exit 1
  fi
done

python3 gen.py
mkdir -p "$OUT_DIR"
img2webp -loop 0 -d "$(cat frames/duration)" -lossless -m 6 frames/f0*.png -o .bg.webp
# ANIM チャンクの背景色を透明にする。dispose=background のフレームで白が出るのを防ぐ
webpmux -set bgcolor 0,0,0,0 .bg.webp -o "$OUT"
rm -f .bg.webp

printf '%-16s %6s bytes\n' "$ID" "$(wc -c <"$OUT" | tr -d ' ')"
webpmux -info "$OUT" | sed -n '1,4p'
