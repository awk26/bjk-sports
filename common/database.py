import os
import json
import pymysql
from dbutils.pooled_db import PooledDB
from dotenv import load_dotenv
from common.logs import log

load_dotenv()
class Database:
    __raw_connection = None

    def __init__(self):
        self.host = os.getenv("HOST_JIA")
        self.username = os.getenv("USER_JIA")
        self.password = os.getenv("PASSWORD_JIA")
        self.port = int(os.getenv("PORT_JIA", 3306))  # ensure port is int
        self.db_name = os.getenv("DB_NAME_JIA")
        
        Database.__raw_connection = PooledDB(
            creator=pymysql,
            host=self.host,
            user=self.username,
            password=self.password,
            database=self.db_name,
            port=self.port,
            autocommit=True,
            maxconnections=5
        )

    def execute(self, query, args=None):
        """Run a plain SQL statement (SELECT/INSERT/UPDATE/DELETE)."""
        connection = None
        try:
            connection = Database.__raw_connection.connection()
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                if isinstance(args, dict):
                    args = tuple(args.values())  # convert dict to tuple
                cursor.execute(query, args)
                result = cursor.fetchall()
            return result
        except Exception as e:
            log(f"Exception occurred in execute(): {e}")
            return []
        finally:
            if connection:
                connection.close()

    def call_proc(self, proc_name, args=()):
        """
        Call a stored procedure.

        Returns a dict: {"rows": [...], "out_params": {...} | None}

        - "rows"       -> result set from procedures that SELECT (e.g. sp_*_list, sp_*_get_by_id)
        - "out_params" -> dict of OUT parameters keyed as p0, p1, p2... matching
                          the positional index of the arg in `args`. Only
                          populated when `args` is non-empty. For our create
                          procedures the OUT param is always the LAST arg, so
                          access it as out_params[f"p{len(args) - 1}"].

        Pass None as a placeholder for OUT parameters, e.g.:
            db.call_proc("sp_user_create", (username, pwd_hash, role, name, email, created_by, None))
        """
        connection = None
        try:
            connection = Database.__raw_connection.connection()
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.callproc(proc_name, args)
                rows = cursor.fetchall()

                out_params = None
                if args:
                    placeholders = ", ".join(
                        f"@_{proc_name}_{i} AS p{i}" for i in range(len(args))
                    )
                    cursor.execute(f"SELECT {placeholders}")
                    out_params = cursor.fetchone()

            return {"rows": rows, "out_params": out_params}
        except Exception as e:
            log(f"Exception occurred in call_proc({proc_name}): {e}")
            return {"rows": [], "out_params": None}
        finally:
            if connection:
                connection.close()


# if __name__ == '__main__':
#     db=Database()
#     result=db.execute("SELECT * FROM bjk_athletes.coaches")
#     print(result)