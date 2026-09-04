# twemoji-animation

Twemoji の SVG からアニメーション WebP を作る手順をまとめた Claude Code の skill です。
出力は背景が透明でループするロスレスの WebP になります。

`examples/` に実装があります。
構図の近いものを写して、動きの部分を書き換える形で新しい絵文字に対応します。

## 入れ方

```sh
git clone https://github.com/jigintern/twemoji-animation ~/.claude/skills/twemoji-animation
```

Claude Code に「絵文字を動かしたい」と伝えると読み込まれます。

動かして確かめる場合は、依存コマンドを入れてから `examples/` のどれかで `build.sh` を叩いてください。
必要なコマンドは [SKILL.md](./SKILL.md) の「依存コマンド」にあります。

```sh
cd ~/.claude/skills/twemoji-animation/examples/clap && ./build.sh
```

`clap.webp` ができます。
生成物はリポジトリに含めていません。

## 手順

[SKILL.md](./SKILL.md) にあります。
各 `examples/*/README.md` には、その絵文字で採った手口と採らなかった手口が書かれています。

## ライセンス

コードと文書は MIT です。
条件は [LICENSE](./LICENSE) にあります。

同梱している Twemoji の SVG と、そこから生成される WebP は CC-BY 4.0 です。
帰属表記は [NOTICE](./NOTICE) にあります。
生成物を表示する画面を公開する場合は、そこにある 1 行を入れてください。
