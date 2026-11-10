# GitHub 访问修复：Steam++（Watt Toolkit）hosts 劫持

> 记录人：于悦　｜　日期：2026-11-06　｜　环境：Windows 11 + Git 2.55 + PowerShell

本文补充 [GitHub访问诊断报告](GitHub访问诊断报告.md) 未覆盖的一类根因：**本机 hosts 被加速工具改写成 `127.0.0.1`**。

---

## 症状

- 浏览器打开 `github.com` 长时间无响应或直接失败
- `git clone` / `git ls-remote` 报 TLS 握手错误：

```
schannel: next InitializeSecurityContext failed: CRYPT_E_NO_REVOCATION_CHECK (0x80092012)
```

- 或在改用 OpenSSL 后端后报：

```
SSL certificate OpenSSL verify result: unable to get local issuer certificate (20)
```

以上报错容易误判为"证书问题"或"网络被墙"，实际先看 hosts。

---

## 定位过程

| 步骤 | 命令 / 操作 | 观察结果 | 结论 |
| --- | --- | --- | --- |
| 1 | 查看 hosts 中的 github 相关行 | 全部指向 `127.0.0.1` | 域名被劫持到本机 |
| 2 | `nslookup github.com` | 返回 `20.205.243.166` | nslookup 只查 DNS 服务器，不读 hosts，容易误判 |
| 3 | 绕开 hosts 直连各候选 IP（`curl --resolve`） | `140.82.114.3` → 200，其余多个 IP → 000 | 链路本身可用，问题在本地解析 |
| 4 | 查看进程列表 | 存在 `Steam++.Accelerator` 等进程 | 劫持来源为加速工具 |

**关键判断**：`127.0.0.1` 表示加速工具在自己改 hosts，把流量导向本机代理端口；一旦该代理服务没在运行（或规则失效），GitHub 就变成"指向自己、无人应答"，所有请求必然失败。

---

## 修复步骤

### 1. 关闭加速工具

托盘图标 → 退出 Steam++ / Watt Toolkit；或在其「网络加速」页关闭 GitHub 相关开关。
**两个方案只能二选一**：加速工具每次启动都会重写 hosts，开着它跑下面的脚本会被覆盖。

### 2. 清理并重写 hosts（需管理员权限）

以管理员身份运行修复脚本（本机放置于 `D:\SDD-env\fix-github.bat`），脚本逻辑：

1. 备份原文件为 `hosts.bak`
2. `findstr /V /I /C:"github"` 删除所有含 github 的行（连同劫持记录一并清除，避免重复叠加）
3. 写入实测可用的 IP
4. `ipconfig /flushdns` 刷新缓存

写入的 IP（2026-11-06 实测）：

```
140.82.114.3       github.com
140.82.114.5       api.github.com
140.82.112.10      codeload.github.com
185.199.108.133    raw.githubusercontent.com
185.199.110.133    objects.githubusercontent.com
```

> IP 会轮换。失效时用 `curl --resolve 域名:443:候选IP https://域名` 逐个测试，把返回 `200/301` 的地址替换进 hosts。

### 3. 调整 git TLS 行为

国内网络访问不到证书吊销列表服务器，schannel 后端会因此直接拒绝连接：

```bash
git config --global http.schannelCheckRevoke false
```

**不要**为此改用 `http.sslBackend=openssl`——Git for Windows 自带的 OpenSSL 缺少 CA 证书包时，会报"unable to get local issuer certificate"，问题反而变多。

### 4. 重开终端

hosts 与 DNS 缓存对已打开的终端不生效，必须关闭所有终端窗口后重新打开。

---

## 验证

```bash
git ls-remote https://github.com/onetwothree-go/smart-daily
```

返回 `HEAD` 与 `refs/heads/*` 即修复完成；浏览器打开 github.com 应正常显示页面。

---

## 经验教训

1. **先看 hosts，再怀疑网络**。`C:\Windows\System32\drivers\etc\hosts` 里出现 `127.0.0.1 域名` 的形式，基本可以断定是本机加速/代理工具所为。
2. **`nslookup` 有误导性**，它不读 hosts 文件；判断实际解析结果要用 `ping`、`curl` 或浏览器。
3. **报错信息会指向错误方向**。`CRYPT_E_NO_REVOCATION_CHECK` 看起来像证书链问题，根因却是解析被劫持到本机。
4. **同一台机器不要叠加多种"加速"方案**（hosts 固定 IP、系统代理、加速工具三者混用会互相打架），选定一种，其余全部关闭。
