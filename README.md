# Radio Roam — なんかちいさくてたのしいやつ

ESP32-S3を使ったポケット育成ゲーム。Lo-Viで使っていたハードウェアを流用し、独立したコードベースで開発しています。

## 開発版

最新版は [v0.13-rumigaru](releases/v0.13-rumigaru/README.md) です。
Wi-Fi環境によるイベント生成、育成、コマンドバトル、スキャン捕獲、合成、Androidブラウザ連携、画面スリープを含みます。

魚型ルミガルの頭・胴体・胸ビレ・発光アンテナを別々の画像から実装しています。バルクルは参考画像の段階です。
この開発版はPCで54件のテストを確認済みですが、実機への反映は未完了です。BLEの二台間検証も未完了です。

## 構成

- `releases/v0.13-rumigaru/firmware/`: 実機用コード・パーツ・スマホUI
- `releases/v0.13-rumigaru/tests/`: ゲームロジックとパーツ整合性のテスト
- `releases/v0.13-rumigaru/art/`: 個別パーツ編集素材
- `releases/v0.13-rumigaru/docs/`: 仕様・過去の検証記録
- `art/original-monsters-20260926/`: オリジナルキャラ原画と生成指示
- `tools/compile_rumigaru.py`: 個別PNGを端末用パーツに変換

## 検証

```sh
python -m unittest discover -s releases/v0.13-rumigaru/tests
```

原画の再変換にはPillowを利用します。

```sh
python -m pip install -r requirements-dev.txt
python tools/compile_rumigaru.py
```

## 対象機材

Waveshare ESP32-S3-Touch-LCD-1.28 / MicroPython / GC9A01 240×240。
LCD: SCK=10, MOSI=11, DC=8, CS=9, RST=14, BL=2。タッチI2C: SDA=6, SCL=7。

端末バックアップ、個人のセーブ、認証情報、作業用環境は含めていません。
