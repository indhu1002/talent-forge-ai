import secrets, time
from pathlib import Path
import pymysql
root = Path(__file__).resolve().parent
for attempt in range(30):
    try:
        connection = pymysql.connect(host="127.0.0.1",port=3307,user="root",password="")
        break
    except pymysql.Error:
        time.sleep(1)
else:
    raise RuntimeError("Project MySQL did not become ready")
app_password = secrets.token_urlsafe(32)
root_password = secrets.token_urlsafe(32)
with connection.cursor() as cursor:
    cursor.execute("CREATE DATABASE talentforge CHARACTER SET utf8mb4")
    cursor.execute("CREATE USER 'talentforge'@'localhost' IDENTIFIED BY %s", (app_password,))
    cursor.execute("GRANT ALL ON talentforge.* TO 'talentforge'@'localhost'")
    cursor.execute("GRANT ALL ON test_talentforge.* TO 'talentforge'@'localhost'")
    cursor.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s", (root_password,))
connection.close()
(root / ".env").write_text("DEBUG=1\nDB_ENGINE=mysql\nMYSQL_DATABASE=talentforge\nMYSQL_USER=talentforge\nMYSQL_PASSWORD="+app_password+"\nMYSQL_HOST=127.0.0.1\nMYSQL_PORT=3307\nENABLE_AI_FEEDBACK=0\n",encoding="utf-8")
(root / ".mysql-root-password").write_text(root_password,encoding="utf-8")
print("Isolated MySQL configured on 127.0.0.1:3307; generated passwords saved privately in backend configuration.")