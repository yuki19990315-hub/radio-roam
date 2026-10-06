# 犬・猫の新パーツ

今回の対象は獣タイプ。犬系2番号、猫系2番号（各系統内は模様・足先の差分）で、頭・胴・前脚・後脚・尾・目・小さな角・羽を独立ファイルとして作成しました。成長段階間は同じ基本体形で、模様の差分です。鳥・竜・魚・人型・植物の新規デザインは今回の対象に含みません。

`art/reference/dog.png` と `cat.png` は組み立て前の全身デザイン参考。内蔵imagegenで生成しました。実機はこの大きな画像を読み込みません。

`tools/build_beast_v2.py` の編集可能なドット記号データから、`art/parts/獣/` の個別PNG・JSON・pixels.txt、および `firmware/assets/beast_v2/` の96個の部位ファイルを生成しています。参考画像の自動切り抜きや縮小ではなく、ゲームの小さな格子に合わせた描き起こしです。元の大きな参考画像と実機の絵は同一ではありません。

獣専用のパレットで口先・胸・足先を淡い色に分離。待機・踏み込みに加え、睡眠は頭と胴を下げて脚を畳む配置にしています。スマホ側の画像キャッシュ識別子も更新します。能力、所持キャラ、名前、合成・進化の遺伝子は維持します。

## 生成プロンプト

犬（内蔵ツール）:

Create ONE original canine virtual-pet monster pixel sprite as a design reference for a 64x64 game. Single complete character, facing RIGHT, isolated transparent background, no text, no grid, no shadows outside creature. Pixel art enlarged with crisp square blocks and no antialiasing, roughly 40x35 native pixels. Very appealing compact wolf puppy: large triangular ears, short cream muzzle, expressive visible amber eye correctly on face, large head, sturdy short FOUR legs and distinct rounded paws, compact horizontal torso with a cream chest bib, fluffy upward curled tail, a single angular cheek fur tuft. Blue-teal main fur, navy outline, one shadow tone, pale cream muzzle/chest, amber eye. Exactly 6 solid colors plus transparency. Beautiful readable chunky silhouette, cute but brave, Japanese handheld monster-raising game feel. No armor no horns no wings no complex fur speckles, no humanoid arms, no dinosaur body, no long thin limbs. This is a finished whole-body reference; individual modular parts will be authored separately in the game.

猫（内蔵ツール）:

One single original kitten monster sprite, facing RIGHT on truly transparent background, crisp enlarged retro handheld pixel art approximately 40x35 logical pixels, six solid colors, no smooth gradients, no text or panel. Compact appealing FOUR-legged kitten with large triangular ears, big expressive amber visible eye, short round muzzle, wide cream cheeks and chest, sturdy little paws, rounded horizontal body and an elegant upright curved tail, exactly 2 broad navy forehead stripes. Main fur warm muted coral, dark navy outlines, single darker coral shade, pale cream cheeks paws chest, amber eye. Cute proud mischievous expression with a strong silhouette, Japanese monster-raising handheld game feel. Stand naturally on four paws; no dinosaur, no upright humanoid pose, no spikes wings armor or intricate texture. Finished whole-body design reference, for subsequently authoring separate compatible game parts.
