# Windows 本地环境搭建与常见报错

> 记录人：于悦　｜　日期：2026-11-06
> 面向：在 Windows 上首次拉起本项目、准备第一次 `uv run` 的组员
> 已在 Windows 11 + Python 3.13 + uv 0.13.6 实测通过

---

## 一、必装三件套

| 工具 | 版本要求 | 检查命令 | 说明 |
| --- | --- | --- | --- |
| Python | ≥ 3.13（见 `.python-version`） | `python --version` | 版本低于 3.13 时 `uv sync` 会直接拒绝 |
| uv | ≥ 0.13.6（`pyproject.toml` 的构建后端要求） | `uv --version` | 本项目用 uv 管理依赖，不用 pip / venv |
| Git | 任意较新版本 | `git --version` | 需能访问 GitHub（见《GitHub访问修复》一文） |

---

## 二、拉代码并装依赖

```bash
git clone https://github.com/onetwothree-go/smart-daily.git
cd smart-daily
uv sync
```

`uv sync` 会按 `uv.lock` 精确还原依赖，并在 `.venv` 里建好虚拟环境。看到 `Installed N packages` 即成功。

**不要**手动 `pip install`，也不要提交 `.venv` 目录（已在 `.gitignore` 中）。

---

## 三、配置 `.env`（凭证唯一的存放位置）

```bash
cp .env.example .env
```

然后编辑 `.env`。三组凭证相互独立，**先配哪组都能跑**，未配的采集源会在降级链里自动跳过。

| 组 | 变量 | 从哪来 | 权限要求 |
| --- | --- | --- | --- |
| GitHub 采集 | `GITHUB_TOKEN`、`GITHUB_REPO_OWNER`、`GITHUB_REPO_NAME` | GitHub → Settings → Developer settings → Fine-grained tokens | **仅只读**（Contents: Read-only）即可，不要给写权限 |
| 飞书采集 / 推送 | `FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_CHAT_ID`、`FEISHU_WEBHOOK_URL`、`FEISHU_WEBHOOK_SECRET` | 飞书开放平台自建应用 + 群自定义机器人 | 应用需开消息读取相关权限并发版 |
| 邮件推送 | `SMTP_HOST`、`SMTP_PORT`、`SMTP_USER`、`SMTP_PASSWORD` | 邮箱网页版 → 设置 → POP3/SMTP 服务，生成**授权码** | 用授权码，不是登录密码 |

**三条硬规矩**：

1. `.env` 绝不提交（已在 `.gitignore`，提交前用 `git status` 再确认一次）
2. 凭证不写进任何 `.py` 文件、不写进文档、不发群
3. 填完先用 `git check-ignore -v .env` 验证它确实被忽略

---

## 四、先跑无凭证模式

没配任何凭证也能验证链路是否通：

```bash
uv run smart-daily --mock --day 2026-11-02
```

`--mock` 用内置假数据走完整流程（采集 → 生成 → 存储），输出正常说明环境没问题。再加 `--no-notify` 可跳过推送。

---

## 五、常见报错对照表

| 现象 | 真实原因 | 处理 |
| --- | --- | --- |
| `uv : 无法将"uv"项识别为 cmdlet` | 装完 uv 没重开终端，PATH 未刷新 | 关闭**所有**终端窗口，重新打开；仍不行则检查用户 PATH 是否含 uv 所在目录 |
| `PowerShell` 里粘贴命令没反应 | 粘贴后未按回车 | 按一次回车；若提示"无法加载文件，因为在此系统上禁止运行脚本"，是执行策略问题，与本项目无关（uv 不依赖 .ps1） |
| `uv sync` 报 Python 版本不符 | 本机 Python < 3.13，或 uv 找不到 3.13 | 装 Python 3.13；或 `uv python install 3.13` 让 uv 自己管理 |
| `git clone` 报 `CRYPT_E_NO_REVOCATION_CHECK` | 国内访问不到证书吊销列表，与证书本身无关 | `git config --global http.schannelCheckRevoke false` |
| 改 OpenSSL 后报 `unable to get local issuer certificate` | Git 自带 CA 包缺失，换后端反而更糟 | 改回 `git config --global http.sslBackend schannel` |
| `github.com` 打不开、`git` 一连就超时 | hosts 被加速工具改成 `127.0.0.1` | 见《GitHub访问修复-Steam++hosts劫持》 |
| 终端中文显示为乱码 | 控制台代码页不是 UTF-8 | `chcp 65001`（临时）；或改用 Windows Terminal |
| 日报日期差一天 | 用 UTC 取日期，东八区 0–8 点的提交被归到前一天 | 项目已统一用 `local_date()`，自写脚本时不要用 `datetime.utcnow().date()` |
| 读不到 `.env` 里的值 | 值后面带了行内注释、或路径含空格未加引号 | 注释单独占一行；含空格的值用双引号包起来 |
| 飞书推送返回 `19021` | Webhook 开启了签名校验但密钥没配 | 补 `FEISHU_WEBHOOK_SECRET`，或关闭机器人签名校验 |

---

## 六、提交前自查

1. `git status` 里**不应出现** `.env`、`.venv/`、`__pycache__/`
2. 提交信息按 `BRANCHING.md` 约定：`<类型>: <一句话描述>`
3. 从 `dev` 拉分支开发，PR 合回 `dev`，不直接推 `main`
4. 有 AI 参与产出的内容，当天记入 `docs/ai-usage-log.md`（资格项，不得事后补写）
