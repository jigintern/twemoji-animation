---
name: twemoji-animation
description: |
  Twemoji の SVG からアニメーション WebP を作る。path を fill 色と bbox の実測で
  グルーピングし、transform で動かして resvg でラスタライズし、img2webp で束ねる。
  「絵文字を動かしたい」「アニメーションアイコンを作る」「動く emoji」
  「アニメーション素材が欲しい」と言及された時に使用する。
  素材のライセンス (再配布の可否) の判断も含む。
---

# Twemoji からアニメーション WebP を作る

Twemoji の SVG を部品ごとに分解し、フレームごとに `transform` で変形させ、ラスタライズして 1 本のアニメーション WebP に束ねる。
絵文字ごとに固有なのは動きの設計だけで、それ以外の工程は共通になる。

`examples/` に実装がある。
新しく作るときは構図の近いものを写して、動かす部分を書き換える。

## 守備範囲

入力は Twemoji の SVG。
`viewBox="0 0 36 36"` を前提にしてよい。

出力はロスレスのアニメーション WebP。
既定は 192x192 / 背景透明 / 無限ループ。

対象外は次の 3 つ。

- Twemoji 以外の SVG。要素数の assert と 36x36 前提の座標が Twemoji 固有で、他の素材では成り立たない
- GIF と APNG。実績がなく、透明背景とサイズの検証をやり直すことになる
- 動きの共通ライブラリ化。括り出せるのは bbox 実測・viewBox 決定・frames 出力だけで、動きの設計は毎回書き下ろしになる

## 依存コマンド

`python3` / `resvg` / `magick` / `img2webp` / `webpmux`。

macOS はこれで入る。

```sh
brew install resvg imagemagick webp
```

検証したのは macOS 26.6.2 (arm64) の Python 3.14.6 / resvg 0.47.0 / ImageMagick 7.1.2-13 / libwebp 1.6.0。

Linux は次が目安で、動作は未検証。

- Debian / Ubuntu: `apt install imagemagick webp`。resvg は apt にないので `cargo install resvg`
- Fedora: `dnf install ImageMagick libwebp-tools`。resvg は同じく `cargo install resvg`

Windows は未検証。

`build.sh` は起動時にすべての存在を確認して、欠けていれば名前を出して止まる。
この形を維持する。
依存が欠けたまま `python3 gen.py` に入ると、resvg の呼び出しで初めて落ちて原因が読みにくくなる。

## 手順

### 1. SVG を取る

コードポイントを調べて `jdecked/twemoji` から取る。

```sh
curl -O https://raw.githubusercontent.com/jdecked/twemoji/main/assets/svg/1f44f.svg
```

`1f44f` が 👏 にあたる。
複数のコードポイントを持つ絵文字は `-` で連結される。

### 2. path 構造を実測する

座標も要素の対応も目視や推測で決めない。
ここが工程の中で最も間違えやすい。

まず要素の種類と数を数える。
Twemoji は `path` 以外に `circle` と `ellipse` も使う。

```sh
grep -o '<path' 1f44f.svg | wc -l
grep -o '<circle' 1f44f.svg | wc -l
grep -o '<ellipse' 1f44f.svg | wc -l
```

次に `fill` 色で当たりを付ける。
色が部品の役割と対応していることが多い。

```sh
grep -o 'fill="[^"]*"' 1f44f.svg | sort | uniq -c
```

👏 は `#EF9645` / `#FA743E` / `#FFDB5E` の 3 色で、それぞれ奥の手・衝撃線・手前の手に分かれる。
色が一意ならこの形でグルーピングできる。

```python
P = {}
for m in re.finditer(r'<path\b[^>]*>', src):
    f = re.search(r'fill="([^"]*)"', m.group(0)).group(1)
    P[{'#EF9645': 'back', '#FA743E': 'lines', '#FFDB5E': 'front'}[f]] = m.group(0)
```

同じ色が複数ある場合は出現順で切る。
🦋 は片羽 5 要素ずつと胴体で、`els[0:5]` / `els[5:10]` / `els[10]` に分かれる。
どちらの方式でも要素数を assert して、素材が差し替わったら止まるようにする。

```python
els = re.findall(r'<path\b[^>]*?/?>', src)
assert len(els) == 11, len(els)
```

最後に各要素の bbox を測る。
1 要素だけを含む SVG を書いてラスタライズし、`magick -format %@` で不透明領域を取る。

```python
def bbox(el):                               # svg units, measured not assumed
    open('.bb.svg', 'w').write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 36 36">{el}</svg>')
    subprocess.run(['resvg', '-w', '720', '-h', '720', '.bb.svg', '.bb.png'], check=True)
    out = subprocess.run(['magick', '.bb.png', '-format', '%@', 'info:'],
                         capture_output=True, text=True, check=True).stdout
    w, h, ox, oy = [int(v) * 36 / 720 for v in
                    re.match(r'(\d+)x(\d+)\+(\d+)\+(\d+)', out).groups()]
    return ox, oy, ox + w, oy + h
```

720 は 36 の 20 倍で、1 px が 0.05 svg 単位にあたる。
支点や中心はこの実測値から導く。

### 3. 動きを設計する

構図が手口を決める。
共通化できる部分がないので、ここは毎回考える。

- 🦋 は真上から見た左右対称。回転させると羽が下へ垂れて畳む動きになるので、胴体軸に向けた `scaleX` を使う
- 👏 は両手がほぼ完全に重なる。平行移動では横にずれるだけで拍手に見えないので、手首を支点にした回転で扇状に開く
- 🎂 は静止部と炎に分かれる。動かすのは炎だけで、皿とケーキ本体は固定する
- 🎉 は本体と既に弾けた紙吹雪。各要素の中心から放射状に飛ばす

判断の材料は `examples/*/README.md` にある。
「決めた理由」と「採らなかった方法」の両方を読む。
特に採らなかった方法は、同じ構図で同じ失敗を繰り返さないために書いてある。

### 4. gen.py を書く

構図の近い `examples/*/gen.py` を写して、`body(u, vb)` を書き換える。
骨格は後述する。

### 5. build.sh を通す

`examples/*/build.sh` を写す。
`ID` を変えるだけで動く。

```sh
cd examples/clap && ./build.sh
```

出力先は `OUT` で変えられる。

```sh
OUT=../../dist/clap.webp ./build.sh
```

### 6. 検証する

次の 4 つを見る。

アニメーションになっていること。
静止画を置いてしまっても気付けるようにする。

```sh
webpmux -info clap.webp | sed -n '1,4p'
```

`Features present: animation transparency` と `Loop Count : 0` と `Number of frames` が出る。

生成が決定的であること。
2 回実行して sha256 が一致することを見る。

```sh
shasum -a 256 clap.webp && ./build.sh >/dev/null && shasum -a 256 clap.webp
```

静止アイコンと並べたときの見た目の大きさ。
全フレームの和と最小のフレームの両方を測る。

```sh
magick frames/f*.png -background none -flatten -format '%@\n' info:
for f in frames/f*.png; do magick "$f" -format '%@\n' info:; done | sort -t x -k1,1n | head -1
```

👏 は和が 185x142、最小のフレームが 124x124。
`SIZE=192` に対して 65% しかないので、36x36 全域を使う静止アイコンと並べると 1 フレームは小さく見える。
並べて置く用途なら `SIZE` を上げるか、静止アイコン側の余白を合わせる。

実際にブラウザで動くこと。
`<img src>` で読み込んで、ループの継ぎ目と背景の透明を目で見る。

## gen.py の骨格

2 パス構成にする。

1 パス目で全フレームの bbox の和を測り、切れない最小の viewBox を決める。
2 パス目でその viewBox を全フレームに固定して SVG を吐き、resvg でラスタライズする。

viewBox をフレームごとに決めると絵が揺れる。

```python
# pass 1: find the union bbox across all frames, in svg units
probe, W, BIG = '.probe.svg', 400, '-40 -40 116 116'
lo_x = lo_y = 1e9; hi_x = hi_y = -1e9
for i in range(N):
    open(probe, 'w').write(body(i / N, BIG))
    subprocess.run(['resvg', '-w', str(W), '-h', str(W), probe, '.probe.png'], check=True)
    out = subprocess.run(['magick', '.probe.png', '-format', '%@', 'info:'],
                         capture_output=True, text=True, check=True).stdout
    bw, bh, ox, oy = map(int, re.match(r'(\d+)x(\d+)\+(\d+)\+(\d+)', out).groups())
    k = 116 / W
    lo_x = min(lo_x, -40 + ox * k);         lo_y = min(lo_y, -40 + oy * k)
    hi_x = max(hi_x, -40 + (ox + bw) * k);  hi_y = max(hi_y, -40 + (oy + bh) * k)

side = max(hi_x - lo_x, hi_y - lo_y) * (1 + MARGIN * 2)
cx, cy = (lo_x + hi_x) / 2, (lo_y + hi_y) / 2
vb = f'{cx - side/2:.3f} {cy - side/2:.3f} {side:.3f} {side:.3f}'

# pass 2: emit frames
for i in range(N):
    p = os.path.join(OUT, 'f%03d.svg' % i)
    open(p, 'w').write(body(i / N, vb))
    subprocess.run(['resvg', '-w', str(SIZE), '-h', str(SIZE), p, p[:-4] + '.png'], check=True)
```

`BIG` は 1 パス目の測定用の広い枠で、動きが枠外に出ない大きさにする。
出ると和が正しく測れない。

`body(u, vb)` は位相 `u` (0 以上 1 未満) と viewBox から 1 フレームの SVG 文字列を返す。
ここだけが絵文字ごとに変わる。

パラメータは環境変数で受ける。
既定値をコードに書き、コマンドラインから振れるようにする。

```python
N    = int(os.environ.get('N', 20))
DUR  = int(os.environ.get('DUR', 20))   # ms per frame; N * DUR is the cycle
ROT  = float(os.environ.get('ROT', 26)) # degrees at full open, per hand
```

```sh
ROT=32 N=28 ./build.sh
```

最後に設定値を JSON で吐く。
どの値で作ったかが実行ログに残る。

```python
print(json.dumps({'n': N, 'dur': DUR, 'cycle_ms': N * DUR, 'size': SIZE,
                  'rot': ROT, 'viewBox': vb}, ensure_ascii=False))
```

1 フレームの表示時間は `frames/duration` に書き出し、`build.sh` がそれを読んで `img2webp -d` に渡す。

```python
open(os.path.join(OUT, 'duration'), 'w').write(str(DUR))
```

`N` と表示時間の対応が 1 箇所に収まる。
`build.sh` 側に `-d` の値を書くと、`N` を振ったときに周期がずれる。

## 落とし穴

すべて `examples/` の実装と各 README から採ったもので、推測は含まない。

### パイプライン

- 透明背景には `webpmux -set bgcolor 0,0,0,0` が要る。`img2webp` が書く ANIM チャンクの背景色は既定で不透明白で、dispose method が `background` のフレームはその色で塗る規定になっているため、透明のはずの領域に白が出る余地がある
- `ffmpeg` の webp は decode only で書けない。`img2webp` を使う
- `-lossy -q 85` はむしろ増える。🦋 で 103972 bytes に対し `-lossless` は 77396 bytes
- `-near_lossless` は `-lossless` と併用しても出力が変わらない
- サイズはフレーム数が支配する。🦋 は 20 フレーム 77396 bytes に対し 14 フレームで 54064 bytes
- 全フレームをフルキャンバスで置いて dispose を不要にすると、`img2webp` の差分矩形の最適化が失われて増える
- headless Chrome で 1 フレームずつ撮る手は、サンドボックス内では動かないことがある。ProcessSingleton の unix socket の `bind()` が拒否されて abort する

### 設計

- 支点を定数で書かない。🎂 の炎 3 本は下端が中央 9.95、両端 6.70 で違い、1 つの値では中央が浮くか埋まる
- viewBox は全フレームで固定する。ただし飛び散る動きでは bbox の和で決める方式が本体を縮める。🎉 は `FIT=0` の固定枠にしている。`SPRD` を上げるほど絵が縮む競合を避けるため
- 構図が手口を決める。真上視点の 🦋 は回転ではなく `scaleX`、重なった構図の 👏 は平行移動ではなく回転
- 片手を鏡像で作ると接触フレームの重なりが崩れる。2 つの手は重なる前提で形が設計されていて、反転すると手のひらの膨らみが逆側に来る
- 静止アイコンと並べると 1 フレームが小さく見える。👏 の最小フレームは 124x124 で `SIZE=192` の 65%
- 消えていく要素は opacity の閾値で打ち切る。薄すぎて見えない要素がフレームに残ると bbox の和を無駄に広げ、差分矩形も広がる
- ループの継ぎ目は位相 0 と 1 の両方を見る。位置が元に戻る動きなら、そのとき opacity も 0 にすると継ぎ目が見えない

### 受け手のリポジトリ

- `deno fmt` は SVG を整形して 1 行のタグを複数行に割る。`gen.py` の要素数の正規表現が当たらなくなる。生成一式を置くディレクトリを fmt と lint の対象外にする

## ライセンスの判断

再配布の可否が先、表記の要否が次。

無料のアニメーションアイコン配布サイトは「表記不要」「商用利用可」をうたうものでも、素材ファイルそのものの再配布をライセンスで禁じていることが多い。
素材を配信して読み込ませる用途はまさに再配布にあたるので、表記の要否を見る前にここで落ちる。

Twemoji は CC-BY 4.0 で、帰属表記だけが条件になる。
継承義務がない。

- 著作権表示: Copyright 2019 Twitter, Inc and other contributors
- ライセンス: <https://creativecommons.org/licenses/by/4.0/>

生成物を表示する画面を公開する場合は、フッタか HTML コメントに 1 行入れる。

```html
<!-- Icons: Twemoji by Twitter, Inc and other contributors, licensed under CC-BY 4.0 -->
```

CC0 に限定する案は取らない。
再配布可能かつ CC0 のアニメーション素材が実質見つからない。

## examples の対応表

| id | 絵文字 | 構図 | 採った手口 |
| --- | --- | --- | --- |
| `clap` | 👏 | 両手がほぼ完全に重なる | 手首 (18, 40) を支点に 2 つの手を逆向きに回転。接触時に線を光らせる |
| `butterfly` | 🦋 | 真上から見た左右対称 | 胴体軸 x=18.1 に向けた scaleX で羽を畳む |
| `cake` | 🎂 | 静止部と炎 3 本 | 各炎の下端を実測して支点にし、skew と 2 倍波で揺らす |
| `party-popper` | 🎉 | 本体と飛び散る紙吹雪 | 各要素の中心から放射状に飛ばし、smoothstep で fade out |
