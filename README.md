# AI-oka_passwd — Oak Random Password Generator / 橡木随机密码生成助手

Skip the hassle of inventing a new password on any sign-up page: an AI reads the site's password
requirements, the app generates a compliant password, and saves it locally.

在“要求输入新密码”的网站上免去想密码的烦恼：AI 识别该站密码格式 → 本地生成合规强密码 → 保存到本地。

> AI only reads the password **rules** (public page information) — it never sees or receives your
> password. Passwords are generated locally and are not submitted to any website.
> AI 只读取页面的**密码规则**（公开信息），**从不接触你的密码**；密码在本地生成，不提交给任何网站。

## Features / 功能

- Detect password rules on any page via an embedded browser (QtWebEngine) + AI
- Generate a compliant strong password locally
- Save to local plaintext txt — auto-save or manual (“custom save”) with a configurable folder
- Choose the AI source: built-in (glm-5.3-flash / deepseek-v4.1-flash) · auto-detect local services
  (Ollama / LM Studio / llama.cpp) · custom API
- UI languages: 中文 / English / Русский
- Falls back to local heuristics when no AI service is available
- Won't generate unless detection succeeded (prompts to detect first)

## How it works / 工作流

1. Detect: open the URL in the embedded browser, extract the password field context
2. Analyze: send the rules context to an AI service (default built-in) → rules JSON
3. Generate + save: generate locally and write `<domain>_<timestamp>.txt` (password / rules / URL / time)

## Requirements / 依赖

- Python 3.10 to run from source (see `requirements.txt`)
- An AI service is recommended (built-in local proxy, or Ollama / LM Studio / llama.cpp / custom API).
  Without one, the app falls back to local heuristics.

## Run / Build

```
pip install -r requirements.txt
run_qt.bat        # run from source
build_qt.bat      # build Windows exe (output in dist/)
```

(Re)generate the logo/icon (dev): `python tools/make_logo.py` (needs Pillow)

## Layout / 目录

- `core/`  pure-Python core (rules / generate / store / llm / probe / settings / providers / i18n)
- `app/qt_app.py`  PySide6 UI (embedded browser, 5 pages)
- `assets/`  background + logo
- `tests/`  unit tests

## Tests

```
python -m unittest discover -s tests -t .
```

## License

MIT
