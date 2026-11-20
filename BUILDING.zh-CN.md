# DailyTask APK 构建与安装

本构建基于作者 AndroidCoderPeng / Pengxh 的 DailyTask，保留原界面、功能、作者信息和根目录 LICENSE。上游提交见 `UPSTREAM.json`。上游没有 GitHub Release 或标签，所用源码为 2026-11-20 查询到的默认分支最新快照，不能称为作者认证的稳定发布版。

## 直接安装

从本地交付目录或下面的 Actions Artifacts 获取 `DT_日期_2.5.0.0.apk`，传到手机，在文件管理器中打开并允许该来源安装应用。无需 Android Studio、JDK 或电脑上的 Android SDK。

包名为 `com.pengxh.daily.app`，最低 Android 8.0 / API 26，目标 API 36。一个 APK 包含 armeabi-v7a、arm64-v8a、x86、x86_64，无需分别安装分包。具体校验结果以同目录 `verification.json`、`signature.txt`、`package.txt` 为准。声明支持的系统版本不等同于所有厂商手机均已实测。

首次运行按实际需要授权通知、悬浮窗、通知使用权和系统截屏；应用设置中的结果来源和消息渠道仍需本人配置。请先阅读 `PRIVACY-REVIEW.zh-CN.md`。请勿把应用设置为设备管理员，也不需要 Root。

如果提示签名不一致，不能覆盖安装其他签名的同包名版本。先备份必要数据，再由本人决定是否卸载旧版；卸载通常会删除应用数据。不要用禁用系统签名验证的方法安装。若提示“解析失败”，检查下载完整性及 Android 版本。

## 在自己的 GitHub 上重新编译

本次使用的个人 Fork：<https://github.com/2521594623/DailyTask>。

1. 打开个人仓库，选择 **Actions → Build signed APK → Run workflow**。
2. 选择 `master`；`signing` 选择 `upstream-public` 可直接运行，不需配置 Secrets。
3. 等待该次任务变为绿色，打开任务详情页，在下方 **Artifacts** 下载 `DailyTask-APK-运行序号-重试序号`。
4. 解压 Artifact 的 ZIP，安装其中 `.apk`。ZIP 本身不能安装。
5. 同一目录提供 SHA-256、证书指纹、包信息、权限清单和源码提交信息。构建日志位于另一个 `DailyTask-build-logs-*` Artifact。

需要登录有访问权限的 GitHub 账号才能从网页下载 Artifacts，默认保留 APK 产物 30 天、日志 14 天。工作流不会自动发布 GitHub Release。若未看到 Run workflow，确认工作流文件已经在默认分支，并先在 Actions 页面启用 Fork 的 Actions。

更新源码时，在个人 Fork 页面用 **Sync fork** 合并上游提交。更新冲突需要保留本仓库的工作流与构建修改，再手动运行。工作流编译的是所选分支当前提交，不会在编译中悄悄拉取未记录的新代码。上游变更工具链或依赖后，也可能需要相应调整。

## 签名与后续升级

默认沿用上游 `app/DailyTask.jks` 的 release 签名。该密钥及口令已由作者公开，能够生成 Android 可验证的签名，但**任何持有者都能生成相同签名的 APK，不能据此识别作者或排除恶意更新**。只安装可信来源产物并核对 SHA-256。

若要长期使用，建议自己生成并备份专用密钥。工作流已支持个人密钥，无需改业务代码。在仓库 **Settings → Secrets and variables → Actions** 添加：

| Secret | 内容 |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | 自有 JKS / PKCS12 文件的完整 Base64，不是文件路径 |
| `ANDROID_STORE_PASSWORD` | 密钥库口令 |
| `ANDROID_KEY_ALIAS` | 签名别名 |
| `ANDROID_KEY_PASSWORD` | 私钥口令 |

再手动运行并将 `signing` 选择 `personal`。缺少任一 Secret 会明确失败，不会退回公开密钥。个人密钥只恢复到临时目录，不会进入 Artifact。请勿把个人密钥、口令或邮箱授权码提交到仓库。

同一个包名的覆盖升级需要使用同一密钥，且版本号满足系统升级规则。更换签名通常需要卸载旧版后安装；务必自行备份数据。不要丢失个人密钥，否则未来无法签发可覆盖升级的 APK。

## 无 Android Studio 的本地构建

| 工具 | 本项目配置 |
| --- | --- |
| JDK | 17，运行 Gradle 和 Java toolchain |
| Gradle | Wrapper 8.13，官方发行地址及 SHA-256 |
| Android Gradle Plugin | 8.11.1 |
| Kotlin 插件 | 2.3.20 |
| Android SDK | platforms;android-36 |
| Android Build Tools | 36.0.0 |
| NDK | 21.4.7075529 |
| CMake | 3.22.1；C++14 |
| Python | 3.10+，仅用于产物校验，无额外 Python 依赖 |

安装 JDK 17 和 Android 官方 command line tools，设置 `JAVA_HOME`、`ANDROID_HOME`，并把相应 `bin` 加入 PATH。随后在源码根目录执行：

```text
sdkmanager --licenses
sdkmanager --install "platforms;android-36" "build-tools;36.0.0" "platform-tools" "ndk;21.4.7075529" "cmake;3.22.1"
```

Windows：

```powershell
.\gradlew.bat --no-daemon --stacktrace --console=plain :app:assembleRelease
python scripts/verify_apk.py --out dist
```

Linux / macOS：

```bash
chmod +x gradlew
./gradlew --no-daemon --stacktrace --console=plain :app:assembleRelease
python3 scripts/verify_apk.py --out dist
```

原始 APK 在 `app/build/outputs/apk/release/`，校验后的 APK 和报告在 `dist/`。本机路径放在 `local.properties` 或环境变量中，不提交到 GitHub。Windows 目录太深时，可对本工作区使用临时 `subst` 盘符缩短 SDK 和源码路径。

依赖通过 Google Maven、Maven Central、阿里云和 JitPack 获取，未发现必须提供的私有 Maven 账号、Firebase 配置或后台服务私钥。邮件和企业微信配置属于用户可选的运行时配置，不是编译凭据。首次构建需要网络。

## 校验与测试边界

`scripts/verify_apk.py` 会运行 Android SDK `apksigner verify --verbose --print-certs`、`zipalign`、`aapt`，检查 ZIP CRC、代码/资源完整性、非调试 release 标志和四种 ABI，并输出 SHA-256。最初构建发现旧 NDK 的原生库只有 4 KB 页对齐，因此给原有 CMake 增加 `-Wl,-z,max-page-size=16384`，保留 NDK 版本及原生逻辑。最终工作流同时要求 ELF LOAD 段和 APK 中未压缩原生库通过 16 KB 对齐校验；仍未做 16 KB 设备的运行测试。

签名、结构校验不等于完成手机安装或业务测试。没有连接的测试设备时，报告会明确记录 `device_install_tested=false` 和 `functional_tested=false`。通知监听、系统截屏、厂商后台限制和实际出勤流程需要本人在自己的设备与授权范围内验证。

项目仅限 LICENSE 允许的非商业学习、研究和实验等用途。使用还需符合单位的实际出勤规定。构建修改不增加定位伪造、考勤检测规避或新的远程控制能力。
