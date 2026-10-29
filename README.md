# TDT4225_Assignment3_G110

Deadline: 30 October 2026 at 14:00.

GitHub repo: https://github.com/AleksanderKvelland/TDT4225_Assignment3_G110

Contributors: Aleksander Kvelland, André Klarpås, Brage Andreas Hoven

Group: 110

## Setup guide

We run MongoDB **7.0.1** locally in Docker instead of on the IDI virtual machine.

**Prerequisites:** Docker (with Compose) and Python 3.

### 1. Dataset

Put the Kaggle CSV files in `dataset/` in this repo. The folder is git-ignored because the files are too large.

```
TDT4225_Assignment3_G110/
└── dataset/
    ├── credits.csv
    ├── keywords.csv
    ├── links.csv
    ├── links_small.csv
    ├── movies_metadata.csv
    ├── ratings.csv
    └── ratings_small.csv
```

### 2. Start MongoDB

```bash
docker compose up -d
```

On first start, [mongo-init.js](mongo-init.js) creates the database and the readWrite user.

| | Value |
|---|---|
| Host | `localhost:27017` |
| Database | `movies_db` |
| User (readWrite on `movies_db`) | `g110` / `g110pass` |
| Admin (root) | `adminuser` / `admin123` |

`DbConnector.py` already uses these values.

### 3. Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python example.py
```

If everything works, `example.py` prints `You are connected to the database: movies_db`, then creates, prints and drops a `Person` collection.

## Useful commands

| Task | Command |
|---|---|
| Start / stop the database | `docker compose up -d` / `docker compose stop` |
| Wipe all data and start fresh | `docker compose down -v` |
| MongoDB shell | `docker compose exec mongo mongosh -u g110 -p g110pass movies_db` |
