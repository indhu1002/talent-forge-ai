from pathlib import Path
import pymysql
root = Path(__file__).resolve().parent
password_file = root / ".mysql-root-password"
if password_file.exists():
    try:
        connection = pymysql.connect(host="127.0.0.1",port=3307,user="root",password=password_file.read_text().strip())
        with connection.cursor() as cursor:
            cursor.execute("SHUTDOWN")
        connection.close()
        print("Project MySQL stopped gracefully.")
    except pymysql.Error as exc:
        print("Project MySQL shutdown unavailable:", type(exc).__name__)