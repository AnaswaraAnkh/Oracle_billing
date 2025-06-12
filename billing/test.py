from flask import Flask
import os
import cx_Oracle
import pymysql  # Import pymysql for MySQL connection

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'abc')

print("[1] Starting script...")

oracle_conn = None
oracle_cursor = None
mysql_conn = None
mysql_cursor = None

try:
    # Oracle connection
    oracle_dsn = cx_Oracle.makedsn("sayiq-rawabi.dyndns.org", 1521, service_name="rgc")
    print("[2] Creating Oracle connection...")
    oracle_conn = cx_Oracle.connect(
        user=os.getenv('DB_USER', 'rfsr'),
        password=os.getenv('DB_PASSWORD', 'rfsr'),
        dsn=oracle_dsn,
        encoding="UTF-8"
    )
    oracle_cursor = oracle_conn.cursor()
    print("[✔] Connected to Oracle")

    # MySQL connection using pymysql
    print("[3] Connecting to MySQL with pymysql...")
    mysql_conn = pymysql.connect(
        host="localhost",
        user="root",
        password="root",
        database="sharfu",
        port=3306,
        charset='utf8',
        cursorclass=pymysql.cursors.DictCursor
    )
    mysql_cursor = mysql_conn.cursor()
    print("[✔] Connected to MySQL")

    # Get Oracle DB name
    print("[4] Fetching Oracle DB name...")
    oracle_cursor.execute("SELECT sys_context('USERENV', 'DB_NAME') FROM dual")
    db_name = oracle_cursor.fetchone()[0]
    print(f"\n📛 Oracle Database Name: {db_name}\n")

    # Get all accessible tables
    print("[5] Fetching table list...")
    oracle_cursor.execute("SELECT owner, table_name FROM all_tables ORDER BY owner, table_name")
    tables = oracle_cursor.fetchall()

    print("📋 All Accessible Tables:")
    for owner, table in tables:
        print(f"  - {owner}.{table}")

    # Export tables data from Oracle to MySQL
    oracle_cursor.execute("SELECT table_name FROM all_tables")
    tables = [row[0] for row in oracle_cursor.fetchall()]

    for table in tables:
        print(f"\nExporting table: {table}")
        try:
            oracle_cursor.execute(f'SELECT * FROM "{table}"')
            columns = [desc[0] for desc in oracle_cursor.description]
            rows = oracle_cursor.fetchall()

            # Create table with all columns as TEXT in MySQL (basic example)
            col_defs = ", ".join([f"`{col}` TEXT" for col in columns])
            create_query = f"CREATE TABLE IF NOT EXISTS `{table}` ({col_defs})"
            mysql_cursor.execute(create_query)

            placeholders = ", ".join(["%s"] * len(columns))
            insert_query = f"INSERT INTO `{table}` ({', '.join([f'`{col}`' for col in columns])}) VALUES ({placeholders})"

            if rows:
                # pymysql expects list of tuples, ensure correct format if using DictCursor
                data = [tuple(row[col] for col in columns) for row in rows]
                mysql_cursor.executemany(insert_query, data)
                mysql_conn.commit()

            print(f"✅ Exported {len(rows)} rows from `{table}`")

        except Exception as e:
            print(f"❌ Failed to export `{table}`: {e}")

except Exception as e:
    print(f"❌ Error: {e}")

finally:
    if oracle_cursor: oracle_cursor.close()
    if oracle_conn: oracle_conn.close()
    if mysql_cursor: mysql_cursor.close()
    if mysql_conn: mysql_conn.close()
    print("\n🔒 Connections closed.")

if __name__ == '__main__':
    app.run(debug=True)





    <script>
$(document).ready(function () {
    // Filter logic
    $('#customerSearch').on('keyup', function () {
      var value = $(this).val().toLowerCase();
      $('#customerTable tbody tr').filter(function () {
        $(this).toggle(
          $(this).text().toLowerCase().indexOf(value) > -1
        );
      });
    });

    // Optional: clear search when modal closes
    $('#customerModal').on('hidden.bs.modal', function () {
      $('#customerSearch').val('');
      $('#customerTable tbody tr').show();
    });
  });

</script>

@app.route("/update_salesman", methods=["POST"])
def update_salesman():
    cust_code = request.form.get("cust_code")
    new_salesman = request.form.get("salesman")

    try:
        with pool.acquire() as connection:
            with connection.cursor() as cmd:
                cmd.execute("""
    UPDATE customers
    SET SALESMAN = :new_salesman
    WHERE CUST_CODE = :cust_code
""", {
    "new_salesman": new_salesman,
    "cust_code": cust_code
})

                connection.commit()
        return redirect(url_for("index", cust_code=cust_code))
    except cx_Oracle.DatabaseError as e:
        return f"Database error: {e}", 500
