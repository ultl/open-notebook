from __future__ import annotations

import os

import psycopg


def main() -> int:
  url = os.getenv('DATABASE_URL') or 'postgresql://postgres:pw@localhost:5432/postgres'
  with psycopg.connect(url) as conn, conn.cursor() as cur:
    cur.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    conn.commit()
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
