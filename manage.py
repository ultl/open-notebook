#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio

import scripts.ensure_pgvector as tool
from open_notebook.database.seed import seed_defaults
from open_notebook.database.sql import SessionLocal, init_db


async def seed() -> None:
  await init_db()
  async with SessionLocal() as session:
    await seed_defaults(session)


def main() -> int:
  parser = argparse.ArgumentParser(description='Open Notebook management CLI')
  sub = parser.add_subparsers(dest='cmd', required=True)

  sub.add_parser('ensure-pgvector', help='Ensure pgvector extension exists in the database')
  sub.add_parser('seed', help='Create default rows and example profiles/models')

  args = parser.parse_args()

  if args.cmd == 'ensure-pgvector':
    return tool.main()
  if args.cmd == 'seed':
    asyncio.run(seed())
    return 0
  return 1


if __name__ == '__main__':
  raise SystemExit(main())
