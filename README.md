# パチスロ台選びアシスタント

さいたま市のパチスロホールの台データを収集・分析し、期待値の高い台をランキング表示するWebアプリです。

## 機能

- site777.jp からホール情報・台データを自動取得
- BB/RB確率・差枚数をもとにスコアリング
- ランキング表示・台別の履歴グラフ

## セットアップ

### 必要環境

- Python 3.11+
- [Playwright](https://playwright.dev/python/)

### インストール

```bash
pip install -r requirements.txt
playwright install chromium
```

### 環境変数

`.env.example` をコピーして `.env` を作成し、site777.jp の認証情報を入力してください。

```bash
cp .env.example .env
```

```env
SITE7_EMAIL=your_email@example.com
SITE7_PASSWORD=your_password
```

### 起動

```bash
uvicorn app:app --reload
```

ブラウザで http://localhost:8000 を開いてください。

## API

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/stores` | 登録済みホール一覧 |
| POST | `/api/stores/sync` | さいたま市のホールを同期 |
| POST | `/api/data/fetch` | 台データを取得（バックグラウンド） |
| GET | `/api/data/status` | 取得状況の確認 |
| GET | `/api/ranking` | スコアランキング |
| GET | `/api/machine/history` | 台別履歴 |
