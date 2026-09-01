"""Versao: v1; criado em 2026-08-31, por Codex (ChatGPT).

Projeto: tarifas-energia-brasil. Leitores nativos executados somente em subprocesso.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal


def _json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Tipo nao serializavel: {type(value).__name__}")


def _main():
    # Um crash nao deve produzir core dumps grandes no servidor do HA.
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except ImportError:  # Windows
        pass
    if sys.argv[1] == "duckdb_cli":
        os.execv(sys.argv[2], [sys.argv[2], "-json", "-batch", "-init", os.devnull, ":memory:"])
    request = json.load(sys.stdin)
    path, filters = request["path"], request["filters"] or {}
    if sys.argv[1] == "duckdb":
        import duckdb

        with duckdb.connect(":memory:") as connection:
            connection.execute("SET threads=1")
            connection.execute("SET memory_limit='256MB'")
            clauses = []
            for key in filters:
                if not key.replace("_", "").isalnum():
                    raise ValueError("Campo Parquet invalido")
                clauses.append('"' + key + '" = ?')
            query = "SELECT * FROM read_parquet(?)"
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            cursor = connection.execute(query, [path, *filters.values()])
            columns = [column[0] for column in cursor.description]
            records = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
    else:
        import pyarrow as pa
        import pyarrow.parquet as pq

        pa.set_cpu_count(1)
        pa.set_io_thread_count(1)
        records = pq.read_table(
            path,
            filters=[(key, "=", value) for key, value in filters.items()] or None,
            use_threads=False,
        ).to_pylist()
    json.dump(records, sys.stdout, default=_json_default, ensure_ascii=True)


if __name__ == "__main__":
    _main()
