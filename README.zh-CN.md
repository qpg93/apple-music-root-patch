# Apple Music Root Patch

[English](README.md) | [日本語](README.ja.md) | [Français](README.fr.md) | **简体中文**

Android 版 Apple Music「**root 检测**」的工程研究记录与构建工具。
**本仓库不托管任何 APK 文件。** 这里只有脚本、补丁技术和文档；官方应用需要
你自己下载，并在本地应用补丁。

本项目最初受 [arabaizzet 的仓库](https://github.com/arabaizzet/Apple-Music-for-Rooted-Devices)
（分发修改版 Apple Music 4.8.1）启发。由于原仓库已停止更新，现已成为一个独立项目，
围绕同样的技术做成一份*操作指南*：文档化、工具化，并确认在 Apple Music
**5.2.1、6.5.3、7.0.0** 上无需修改即可适用。

## 背景

自 v4.7（2024 年 3 月）起，Apple Music for Android 一旦认为设备已 root 就拒绝运行。
受影响的场景包括：

- 真正 root 的设备，`su` 位于被检查的路径中；
- 误判的正规设备——例如部分**小米电视**，官方应用启动即退出。

## root 检测的原理

逆向细节（smali 反汇编、各版本的类名对应）见
[`docs/root-detection-analysis.md`](docs/root-detection-analysis.md)。简而言之，
应用的 `Application` 类执行等价于以下的检查：

```java
boolean isDeviceRooted() {
    return helperCheck()                     // ("test-keys", /system/app/Superuser.apk, /system/xbin/su)
        || new File("/system/bin/su").exists();
}
```

辅助检查链在正规系统上本来就会通过；真正导致被拦截的，是
`new File("/system/bin/su").exists()` 这一判断。

### 补丁内容

把 dex 常量池中 14 字节的字符串 `/system/bin/su` 替换成**等长**的不存在路径：

```
/system/bin/su   →   /system/b1n/su        ("bin" → "b1n")
```

由于替换等长、且 dex 只做二进制补丁（不重新编译 smali），生成的 APK 除这 14 字节
之外与官方版逐字节一致——再加上 zipalign 与重新签名（split 也必须重新签名，
所以整体重签本来不可避免）。

最初的 4.8.1 修改版用的是同样的思路，替换为
`/system/bin/applemusicwizzeyeren`（字符串更长，因此必须重新编译 smali）。

**没有改动的东西：** 不碰 DRM、不绕过订阅、不动其他任何内容。
使用该应用仍然需要真实的 Apple ID 和有效的 Apple Music 订阅。

## 自行构建补丁版 APK

### 前置条件

- JDK 17+（只需要 `java`，无需编译 Java 源码）
- [APKEditor 1.4.x](https://github.com/REAndroid/APKEditor/releases) —— 把官方
  `.apkm` 包中的 base APK 与配置 split 合并成单一 universal APK
- [uber-apk-signer 1.3.x](https://github.com/patrickfav/uber-apk-signer/releases) ——
  zipalign + v1/v2/v3 签名（自动生成调试密钥）
- （可选，用于校验）Python 3 与 `uv`，或 `pip install androguard`

构建脚本会在缺少时自动下载两个 JAR。若不确定环境是否就绪，先运行
`./tools/doctor.sh`。

### 1. 获取官方安装包

```bash
python3 tools/fetch_official.py --version 5.2.1
```

自动从 APKMirror 下载官方 `.apkm`（处理 Cookie 与 Referer 的下载链路），
并在保存前用下表的 SHA-256 校验。完整链路说明与手动获取方式见
[`docs/downloading-official.md`](docs/downloading-official.md)。

| 版本 | versionCode | 需要 Android | APKMirror 发布页 | `.apkm` 的 SHA-256 |
|---|---|---|---|---|
| 5.2.1 | 1545 | 10.0 (API 29) | [release](https://www.apkmirror.com/apk/apple/apple-music/apple-music-5-2-1-release/) | `1d74cea9d0d6a7c77bf4d004197be52e9e14110414255caa3825142fc19b7962` |
| 6.5.3 | 1599 | 11.0 (API 30) | [release](https://www.apkmirror.com/apk/apple/apple-music/apple-music-6-5-3-release/) | `a0494d1aac72f9d7901683b9da7df0afe46fae56ac5ad4070c7e265567eabd89` |
| 7.0.0 | 1614 | 11.0 (API 30) | [release](https://www.apkmirror.com/apk/apple/apple-music/apple-music-7-0-0-release/) | `08219d7f9ab143e4ca5858964c630e8b197881eff0e8dff0742cdc7510bf4b1c` |

*（在下载页请选择 **universal / BUNDLE** 变体。下载后请校验 SHA-256。）*

### 2. 执行构建

```bash
./tools/build_patched_apk.sh AppleMusic-5.2.1.apkm
# → AppleMusic-5.2.1-patched.apk
```

脚本流程：合并安装包 → 对 dex 中的 `/system/bin/su` 做二进制补丁 → 输出补丁数量 →
zipalign 并签名。若补丁数量不等于 1，脚本会明确报错退出。若输入本身已是单一 APK，
会自动跳过合并步骤。

### 3. 校验（可选但推荐）

```bash
uv run --with androguard python tools/verify_patched_apk.py AppleMusic-5.2.1-patched.apk
```

检查包名/版本、旧字符串是否已消失、替换后的字符串是否存在，以及是否带有
v1+v2+v3 签名。

### 4. 安装

如果设备上已安装签名不同的同包名应用，请先卸载（重新登录时可能需要密码）：

```bash
adb uninstall com.apple.android.music
adb install AppleMusic-5.2.1-patched.apk
```

也可以把 APK 拷到设备上，用文件管理器安装（请先允许文件管理器的
「安装未知应用」权限）。

## 仓库结构

```
tools/fetch_official.py          从 APKMirror 下载官方 .apkm 并校验 SHA-256
tools/doctor.sh                  构建前环境检查（java/python/curl/磁盘空间）
tools/build_patched_apk.sh       合并 → 二进制补丁 → 签名流水线
tools/patch_dex.py               字符串补丁本体（供上面的脚本调用）
tools/test_patch_dex.py          补丁逻辑自测（不需要任何 Apple 代码）
tools/verify_patched_apk.py      构建后校验（androguard）
tools/locate_root_check.py       dex 扫描器，定位 su 路径检查点
tools/check_new_version.py       将 APKMirror 最新版本与上表比对
docs/root-detection-analysis.md  完整逆向结论、各版本类/方法对应表
docs/building-android-tv.md      电视侧载指南与故障排查（小米示例）
docs/downloading-official.md     APKMirror 下载链路与反爬说明
DISCLAIMER.md                    完整免责声明
```

CI 在每次 push 时运行补丁逻辑自测（`.github/workflows/ci.yml`）。
每日定时工作流（`.github/workflows/version-watch.yml`）会检查 APKMirror 上的
新版本，一旦出现就自动创建带后续检查清单的 issue。

脚本与文档采用 MIT 许可（`LICENSE`）；Apple Music 的二进制文件既未包含、
也不会由本仓库分发。

## 法律声明

**请完整阅读 [`DISCLAIMER.md`](DISCLAIMER.md)。** 摘要：本仓库只包含脚本与文档，
不含任何 Apple 二进制文件。本项目是与 Apple 无关的、未经审计的研究，仅修改一处
14 字节的诊断用字符串；不涉及 DRM、订阅校验或任何内容保护机制。构建并安装补丁版
APK 是你的决定与责任，需自行遵守当地法律、Apple 条款与设备保修政策。不提供任何
形式的担保。
