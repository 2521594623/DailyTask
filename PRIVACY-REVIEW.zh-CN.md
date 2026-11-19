# 权限、网络与隐私静态检查

检查基线：`a52e094125ea5aff21e56f0d6fb8c91871f0efbb`，检查日期 2026-11-19。本报告基于 Manifest、Kotlin / Java、C++ 与构建依赖的静态阅读；没有进行动态抓包、第三方依赖漏洞数据库全量扫描或真机渗透测试。未发现不等于保证不存在。

## 需要注意的发现

| 风险 | 源码位置与证据 | 影响与建议 |
| --- | --- | --- |
| 高：公开签名私钥 | `app/DailyTask.jks` 与 `app/build.gradle` 公开了签名库和口令 | 默认 APK 签名有效，但第三方也能签发同签名包。长期使用建议切换个人密钥并备份，勿把公开签名当成作者身份凭据 |
| 高：远程指令缺少发送者身份认证 | `service/NotificationMonitorService.kt` 从 QQ / TIM / 微信 / 支付宝通知中查找固定 `DT#` 前缀；核心控制分支没有可信发送者白名单或加密挑战 | 能向这些应用发送相应通知的人可能触发原有指令；修改自定义打卡口令不能保护所有固定指令。请使用隔离测试账号，敏感设备不要授权通知使用权；本次没有扩展该功能 |
| 高：配置导出包含凭据 | `utils/TaskDataManager.kt` 的 `exportTasks()` 导出 `wxKey` 和 `emailConfig`（含 SMTP 授权码） | 导出内容、剪贴板、分享文件可能泄露凭据。不要贴到群、Issue、云端日志或公开仓库；误发后应撤销并重新生成授权码/机器人 Key |
| 高：部分配置明文落盘 | `utils/AppConfig.kt`、`ConfigStore.kt`：Webhook Key 在应用私有 SharedPreferences；邮件 JSON 在应用专用外部 Documents 目录，未见加密 | 系统沙箱不等于加密，Root、调试、备份或被导出的文件可能暴露凭据。用专用邮箱授权码和专用测试机器人，不使用主账号登录密码 |
| 中至高：请求和通知日志可能包含隐私 | `retrofit/RetrofitFactory.kt` 的 `debug` 默认 true，BODY 日志可包含 URL 参数 Key、正文、图片 Base64；通知服务记录收到的通知内容 | 不要公开 logcat / 导出日志，截屏前关闭敏感页面。本次为保留行为没有修改日志逻辑 |
| 中：允许备份、允许明文流量 | `AndroidManifest.xml` 的 `allowBackup=true`、`usesCleartextTraffic=true` | 具体备份行为受 Android 版本与厂商影响；明文开关允许 HTTP，但扫描到的业务 URL 为 HTTPS，不能据开关断言已经明文上传。生产化应另行评估加密和网络策略 |
| 中：通知内容本地存储 | `NotificationMonitorService.kt` 保存目标应用及辅助聊天应用的通知到 SQLite，清理 90 天以前记录 | 可能保存聊天、考勤和联系人相关内容。谨慎授权通知使用权和分享导出记录 |
| 已做构建兼容性修复：旧 NDK 与 16 KB 页面 | `app/build.gradle` 固定 NDK 21.4.7075529；首次 APK 的 LOAD 段只有 4 KB 对齐 | 在 CMake 为原有库增加 16 KB 链接对齐参数，校验脚本同时验证 ELF 及 APK 对齐；这不是完成新系统真机功能测试 |

以上风险主要来自上游既有实现。本次构建工作保留业务与界面，记录风险而未擅自删除功能。建议在隔离设备、隔离账号和不含敏感数据的学习场景测试。

## Manifest 权限

| 权限或能力 | 用途与范围 |
| --- | --- |
| INTERNET、ACCESS_NETWORK_STATE、ACCESS_WIFI_STATE | 网络与网络状态；不是“完全离线、从不联网”的应用 |
| SYSTEM_ALERT_WINDOW | 悬浮窗，可遮挡其他应用，需用户授权 |
| SYSTEM_OVERLAY_WINDOW | 上游声明的名称；不是普通应用可直接获得的标准 Android 悬浮窗授权，实际仍以 SYSTEM_ALERT_WINDOW 为准 |
| FOREGROUND_SERVICE、DATA_SYNC、MEDIA_PROJECTION、POST_NOTIFICATIONS | 前台运行通知与截屏服务；新系统可能限制 dataSync 前台服务持续时间，未做真机长时间稳定性验证 |
| QUERY_ALL_PACKAGES，maxSdkVersion=30 | 旧版本查询已安装应用；新版本通过 `<queries>` 列举指定应用 |
| BIND_NOTIFICATION_LISTENER_SERVICE（服务保护权限） | 系统绑定通知监听服务，需本人到系统设置授予通知使用权；不是普通运行时弹窗权限 |
| MediaProjection | 系统录屏/截屏确认，可捕获屏幕可见信息，内容可能经配置渠道发送 |

原始 Manifest 未声明定位、模拟定位、联系人、短信、麦克风、相机、无障碍服务或设备管理员权限。原生 C++ 文件只返回免费软件提醒水印字符串；静态检查未发现定位注入、Root 提权、动态加载外来代码或 shell 命令执行逻辑。本次没有增加上述功能。最终合并后的实际权限以 Artifact 中 `permissions.txt` 为准，因为第三方库可能引入额外权限。

## 可见网络去向

| 主机 | 触发与数据 |
| --- | --- |
| `qyapi.weixin.qq.com` | 配置企业微信机器人后发送文本及截图；Key 是 URL 查询参数，经 HTTPS 传输；数据也进入用户配置的群和第三方平台 |
| `smtp.qq.com:465` | 使用用户填写的邮箱与授权码，通过 SSL SMTP 发送结果、日志或截图；源码启用了服务端身份校验 |
| `cdn.jsdelivr.net`、`fastly.jsdelivr.net` | 获取 `chinese-days` 节假日 JSON |
| `registry.npmmirror.com` | 节假日 JSON 镜像后备；第三方服务会看到普通网络访问元数据 |

没有发现自建业务后台或显式分析 SDK 上传入口，但不应照搬 README “完全本地、不上传任何数据”的笼统表述：消息渠道会按配置外发通知/截图，节假日数据也需要访问第三方网络。

Gradle 构建另需访问 Gradle 官方分发、Google Maven、Maven Central、阿里云 Maven、JitPack 等服务器；这是编译时获取工具与依赖的网络请求，不等于手机运行时上传数据。

## 未修改内容及后续边界

原界面、通知监听、定时调度、已有消息渠道、截屏、水印、作者和许可证保持原样。既有功能是否符合具体单位规定须由使用者确认。该包不提供虚拟定位，也没有加入规避考勤检测的实现。没有进行商业发布。
