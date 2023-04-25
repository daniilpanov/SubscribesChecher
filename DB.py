from mysql.connector import connect
from mysql.connector.errors import OperationalError


class DB:
    cnx = None
    cursor = None

    def __init__(self, db_name, db_user, db_pass, db_host, db_charset=None, db_port=3306):
        self.db_name = db_name
        self.db_user = db_user
        self.db_pass = db_pass
        self.db_host = db_host
        self.db_charset = db_charset
        self.db_port = db_port

        self.cnx = connect(user=db_user, password=db_pass, host=db_host, database=db_name, port=db_port)
        self.cursor = self.cnx.cursor(dictionary=True, buffered=True)

        self.query('SET NAMES %s', (db_charset,))

    def query(self, sql, params=None, commit=True, reconnectonerror=True):
        if reconnectonerror:
            try:
                self.cursor.execute(sql, params)
                if commit:
                    self.cnx.commit()
            except OperationalError:
                self.cnx = connect(user=self.db_user, password=self.db_pass, host=self.db_host, database=self.db_name,
                                   port=self.db_port)
                self.cursor = self.cnx.cursor(dictionary=True, buffered=True)
                self.query(sql, params, commit, False)
        else:
            self.cursor.execute(sql, params)
            if commit:
                self.cnx.commit()

    def select_query(self, sql, params=None, multi=True):
        self.query(sql, params, False)
        return self.cursor.fetchall() if multi else self.cursor.fetchone()

    def __del__(self):
        self.cursor.close()
        self.cnx.close()
