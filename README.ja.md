# Apple-Music-for-Rooted-Devices

[English](README.md) | **日本語** | [Français](README.fr.md) | [简体中文](README.zh-CN.md)

Android 版 Apple Music の **root 検出を無効化**するための調査記録とビルドツールです。
**APK 本体は一切公開していません。** このリポジトリにあるのはスクリプト、パッチ手法、
ドキュメントのみで、公式アプリはご自身でダウンロードし、ローカルでパッチを適用します。

本プロジェクトは [arabaizzet のリポジトリ](https://github.com/arabaizzet/Apple-Music-for-Rooted-Devices)
（Apple Music 4.8.1 の改造版を配布）のフォークとして始まりました。元リポジトリは更新が
止まっているため、本フォークは「やり方（how-to）」に舵を切りました。同じ手法を文書化・
自動化し、Apple Music **5.2.1 / 6.5.3 / 7.0.0** でも変更なしで有効であることを確認済みです。

## 背景

Apple Music for Android は v4.7（2024 年 3 月）以降、端末が root 化されていると判断すると
起動を拒否します。問題になるのは次の 2 パターンです。

- 実際に root 化されており、`su` がチェック対象パスに存在する端末
- 誤検知する正規端末 — 一部の **Xiaomi TV** など。公式アプリが起動直後に終了します。

## root 検出の仕組み

リバースエンジニアリングの詳細（smali ダンプ、バージョンごとのクラス名）は
[`docs/root-detection-analysis.md`](docs/root-detection-analysis.md) にあります。要約すると、
アプリの `Application` クラスが次のようなチェックを実行します。

```java
boolean isDeviceRooted() {
    return helperCheck()                     // ("test-keys", /system/app/Superuser.apk, /system/xbin/su)
        || new File("/system/bin/su").exists();
}
```

ヘルパー側のチェーンは正規端末では通過します。ブロックされる端末で決定的なのは
`new File("/system/bin/su").exists()` の判定です。

### パッチ内容

dex の定数プールにある 14 バイトの文字列 `/system/bin/su` を、**同じ長さ**の
存在しないパスへ置き換えます。

```
/system/bin/su   →   /system/b1n/su        ("bin" → "b1n")
```

同じ長さで、dex をバイナリレベルで書き換えるだけ（smali 再コンパイルなし）なので、
生成される APK は zipalign と再署名を除けば、この 14 バイト以外は公式版と完全に同一です
（split APK も再署名が必要なため、結局は全体の再署名が避けられません）。

元の 4.8.1 改造版は同じ発想を `/system/bin/applemusicwizzeyeren` という文字列で
実現していました（長い文字列のため smali の再コンパイルが必要でした）。

**変更しないもの:** DRM の改変、サブスクリプションの回避、その他一切なし。
アプリを利用するには、有効な Apple Music サブスクリプションを持つ本物の Apple ID が
必要です。

## 自分でパッチ済み APK を作る

### 前提条件

- JDK 17+（必要なのは `java` のみ。Java ソースのコンパイルは不要）
- [APKEditor 1.4.x](https://github.com/REAndroid/APKEditor/releases) — 公式 `.apkm`
  バンドルの base APK と設定 split を 1 つの universal APK にマージ
- [uber-apk-signer 1.3.x](https://github.com/patrickfav/uber-apk-signer/releases) —
  zipalign と v1/v2/v3 署名（デバッグ鍵を自動生成）
- （任意・検証用）Python 3 と `uv`、または `pip install androguard`

ビルドスクリプトは JAR が無ければ自動でダウンロードします。
環境が整っているか不明な場合は、まず `./tools/doctor.sh` を実行してください。

### 1. 公式バンドルを取得

```bash
python3 tools/fetch_official.py --version 5.2.1
```

APKMirror から公式 `.apkm` を自動取得し（Cookie と Referer を考慮したダウンロード
チェーン）、保存前に下の表の SHA-256 で検証します。チェーンの詳細と手動での取得方法は
[`docs/downloading-official.md`](docs/downloading-official.md) を参照してください。

| バージョン | versionCode | 必要な Android | APKMirror リリースページ | `.apkm` の SHA-256 |
|---|---|---|---|---|
| 5.2.1 | 1545 | 10.0 (API 29) | [release](https://www.apkmirror.com/apk/apple/apple-music/apple-music-5-2-1-release/) | `1d74cea9d0d6a7c77bf4d004197be52e9e14110414255caa3825142fc19b7962` |
| 6.5.3 | 1599 | 11.0 (API 30) | [release](https://www.apkmirror.com/apk/apple/apple-music/apple-music-6-5-3-release/) | `a0494d1aac72f9d7901683b9da7df0afe46fae56ac5ad4070c7e265567eabd89` |
| 7.0.0 | 1614 | 11.0 (API 30) | [release](https://www.apkmirror.com/apk/apple/apple-music/apple-music-7-0-0-release/) | `08219d7f9ab143e4ca5858964c630e8b197881eff0e8dff0742cdc7510bf4b1c` |

*（ダウンロードページでは **universal / BUNDLE** 版を選んでください。取得後に
SHA-256 を検証してください。）*

### 2. ビルドを実行

```bash
./tools/build_patched_apk.sh AppleMusic-5.2.1.apkm
# → AppleMusic-5.2.1-patched.apk
```

スクリプトの処理: バンドルをマージ → dex 内の `/system/bin/su` をバイナリパッチ →
パッチ件数を表示 → zipalign と署名。パッチ件数が 1 件でない場合は明確に失敗します。
入力がすでに単一 APK の場合はマージを自動でスキップします。

### 3. 検証（任意だが推奨）

```bash
uv run --with androguard python tools/verify_patched_apk.py AppleMusic-5.2.1-patched.apk
```

パッケージ名・バージョン、旧文字列が消えていること、置換後の文字列が存在すること、
v1+v2+v3 署名が付いていることを確認します。

### 4. インストール

既に別の署名でアプリがインストールされている場合は、先にアンインストールしてください
（再ログイン時にパスワードを求められることがあります）。

```bash
adb uninstall com.apple.android.music
adb install AppleMusic-5.2.1-patched.apk
```

APK を端末にコピーし、ファイルマネージャーからインストールする方法でも構いません
（先にファイルマネージャーの「提供元不明のアプリ」を許可してください）。

## リポジトリ構成

```
tools/fetch_official.py          APKMirror から公式 .apkm を取得 + SHA-256 検証
tools/doctor.sh                  ビルド前の環境チェック（java/python/curl/空き容量）
tools/build_patched_apk.sh       マージ → バイナリパッチ → 署名のパイプライン
tools/patch_dex.py               文字列パッチ本体（上のスクリプトが使用）
tools/test_patch_dex.py          パッチロジックのセルフテスト（Apple のコード不要）
tools/verify_patched_apk.py      ビルド後の検証（androguard）
tools/locate_root_check.py       su パス検査を探す dex スキャナ
tools/check_new_version.py       APKMirror の最新版と上の表を比較
docs/root-detection-analysis.md  リバースエンジニアリングの詳細、バージョン別対応表
docs/building-android-tv.md      TV へのサイドロード手順とトラブルシューティング
docs/downloading-official.md     APKMirror のダウンロードチェーンと対策
DISCLAIMER.md                    詳細な免責事項
```

CI は push ごとにパッチロジックのセルフテストを実行します
（`.github/workflows/ci.yml`）。毎日実行されるワークフロー
（`.github/workflows/version-watch.yml`）が APKMirror の新バージョンを確認し、
見つかった場合は対応チェックリスト付きの Issue を自動作成します。

スクリプトとドキュメントは MIT ライセンス（`LICENSE`）です。Apple Music の
バイナリは本リポジトリに含まれず、配布もされません。

## 法的注意

**[`DISCLAIMER.md`](DISCLAIMER.md) を全文お読みください。** 要約: 本リポジトリには
スクリプトとドキュメントのみが含まれ、Apple のバイナリは含まれません。本プロジェクトは
Apple とは無関係の未監査の研究であり、14 バイトの診断用文字列を書き換えるものです。
DRM、サブスクリプション判定、コンテンツ保護機構には一切触れません。パッチ済み APK の
ビルドとインストールはご自身の判断と責任で行ってください（現地法、Apple の規約、
端末の保証に従う必要があります）。いかなる保証もありません。
