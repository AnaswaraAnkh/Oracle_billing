import cx_Oracle
from flask import Flask, redirect, render_template, request, url_for
import math
import os

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'abc')  # Use environment variable for secret key

# Oracle connection pool
dsn = cx_Oracle.makedsn("sayiq-rawabi.dyndns.org", 1521, service_name="rgc")
pool = cx_Oracle.SessionPool(
    user=os.getenv('DB_USER', 'rfim'),
    password=os.getenv('DB_PASSWORD', 'rfim'),
    dsn=dsn,
    min=1, 
    max=10,
    increment=1,
    encoding="UTF-8"
)

# Configuration for pagination
PER_PAGE = 50
@app.route('/cus_search')
def cus_search():
    try:
        with pool.acquire() as connection:
            cmd = connection.cursor()
            # Get page number and search term
            page = int(request.args.get('page', 1))
            if page < 1:
                page = 1
            search_query = request.args.get('search', '').strip()
            offset = (page - 1) * PER_PAGE
            max_row = offset + PER_PAGE

            # Prepare SQL conditions for search
            bind_vars = {'max_row': max_row, 'offset': offset}
            if search_query:
                where_clause = """
                    WHERE LOWER(CUST_CODE) LIKE :search
                       OR LOWER(CUST_NAME) LIKE :search
                       OR LOWER(ADDRESS) LIKE :search
                       OR LOWER(MOBILE) LIKE :search
                       OR LOWER(CATEGORYNAME) LIKE :search
                       OR LOWER(ROUTENAME) LIKE :search
                       OR LOWER(SALESMANNAME) LIKE :search
                """
                bind_vars['search'] = f'%{search_query}%'
                count_bind_vars = {'search': f'%{search_query}%'}
            else:
                where_clause = ""
                count_bind_vars = {}

            # Get total count efficiently
            count_query = f"SELECT COUNT(CUST_CODE) FROM customers {where_clause}"
            print(f"Count query: {count_query}, bind_vars: {count_bind_vars}")
            cmd.execute(count_query, count_bind_vars)
            total_customers = cmd.fetchone()[0]
            total_pages = math.ceil(total_customers / PER_PAGE)

            # Fetch paginated customers
            query = """
                SELECT * FROM (
                    SELECT a.*, ROWNUM rn FROM (
                        SELECT LOCATIONCODE, CUST_CODE, CUST_NAME, ADDRESS, CREDIT_LIMIT,
                               CREDIT_AMOUNT, CATEGORY, CATEGORYNAME, ROUTE, ROUTENAME,
                               SALESMAN, SALESMANNAME, TYPE, MOBILE
                        FROM customers
                        %s
                        ORDER BY CUST_CODE
                    ) a WHERE ROWNUM <= :max_row
                ) WHERE rn > :offset
            """ % where_clause
            print(f"Executing query: {query}, bind_vars: {bind_vars}")
            cmd.execute(query, bind_vars)
            result = cmd.fetchall()

            # Get column names
            description = cmd.description
            column_names = [col[0] for col in description]

            return render_template(
                "customerview.html",
                value=result,
                column_names=column_names,
                current_page=page,
                total_pages=total_pages,
                per_page=PER_PAGE,
                search_query=search_query
            )
    except cx_Oracle.DatabaseError as e:
        print(f"Database error in /cus_search: {e}")
        return f"Database error: {e}", 500
    except Exception as e:
        print(f"General error in /cus_search: {e}")
        return f"Error: {e}", 500
    
@app.route('/')
def index():
    try:
        with pool.acquire() as connection:
            cmd = connection.cursor()

            cust_code = request.args.get('cust_code')
            page = int(request.args.get('page', 1))
            if page < 1:
                page = 1
            offset = (page - 1) * PER_PAGE

            # Get total number of customers
            cmd.execute("SELECT COUNT(CUST_CODE) FROM customers")
            total_customers = cmd.fetchone()[0]
            total_pages = math.ceil(total_customers / PER_PAGE)

            # Fetch paginated customers
            print(f"Executing query with offset={offset}, per_page={PER_PAGE}")
            cmd.execute("""
                SELECT * FROM (
                    SELECT a.*, ROWNUM rn FROM (
                        SELECT LOCATIONCODE, CUST_CODE, CUST_NAME, ADDRESS, CREDIT_LIMIT,
                               CREDIT_AMOUNT, CATEGORY, CATEGORYNAME, ROUTE, ROUTENAME,
                               SALESMAN, SALESMANNAME, TYPE, MOBILE
                        FROM customers
                        ORDER BY CUST_CODE
                    ) a WHERE ROWNUM <= :max_row
                ) WHERE rn > :offset
            """, {'max_row': offset + PER_PAGE, 'offset': offset})
            all_customers = cmd.fetchall()

            # Get selected customer details if cust_code is provided
            selected_customer = None
            if cust_code:
                cmd.execute("SELECT * FROM customers WHERE CUST_CODE = :code", {'code': cust_code})
                selected_customer = cmd.fetchone()

            # Get all distinct salesman names
            cmd.execute("SELECT * from salesman")
            salesmen = [row[2] for row in cmd.fetchall()]

            return render_template(
                "index.html",
                value=all_customers,
                selected_customer=selected_customer,
                current_page=page,
                total_pages=total_pages,
                per_page=PER_PAGE,
                salesmen=salesmen
            )

    except cx_Oracle.DatabaseError as e:
        print(f"Database error in /: {e}")
        return f"Database error: {e}", 500
    except Exception as e:
        print(f"General error in /: {e}")
        return f"Error: {e}", 500


@app.route("/test_db")
def test_db():
    try:
        with pool.acquire() as connection:
            cursor = connection.cursor()

            # Oracle table names are typically stored in uppercase
            query = "SELECT column_name FROM all_tab_columns WHERE table_name = 'ITEMMASTERDETAILS'"
            cursor.execute(query)

            rows = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]
            results = [dict(zip(col_names, row)) for row in rows]

            # Create HTML output with index
            html = "<h2>DB Test - Basic Item Info</h2><ul>"
            for idx, row in enumerate(results, start=1):
                html += f"<li><b>Index {idx}:</b><br>" + "<br>".join(f"<b>{k}</b>: {v}" for k, v in row.items()) + "</li><br>"
            html += "</ul>"

            return html

    except Exception as e:
        return f"<h2>DB Test Failed</h2><p>{str(e)}</p>", 500



from flask import jsonify



# @app.route("/customers")
# def customers():
#     try:
#         with pool.acquire() as connection:
#             with connection.cursor() as cmd:
#                 cmd.execute("""
#                     SELECT CUST_CODE, CUST_NAME,ADDRESS, CREDIT_LIMIT, CREDIT_AMOUNT,SALESMANNAME, TYPE, MOBILE
#                     FROM customers
#                     WHERE CUSTOMERSTATUS = 'Y' and rownum<50
#                     ORDER BY CUST_CODE
#                 """)
                
#                 rows = cmd.fetchall()
#                 print(rows)
             
#                 columns = [col[0] for col in cmd.description]
#                 customers = [dict(zip(columns, row)) for row in rows]
#         return jsonify(customers)
#     except Exception as e:
#         print("Error in customers:", e)
#         return jsonify({"error": str(e)}), 500


@app.route("/customers")
def customers():
    search = request.args.get('search', '').strip()  # Get the search term from query params
    try:
        with pool.acquire() as connection:
            with connection.cursor() as cmd:
                # Base query
                query = """
                    SELECT CUST_CODE, CUST_NAME, ADDRESS, CREDIT_LIMIT, CREDIT_AMOUNT, SALESMANNAME, TYPE, MOBILE
                    FROM customers
                    WHERE CUSTOMERSTATUS = 'Y'
                """

                # Add search filter if provided
                if search:
                    query += " AND (LOWER(CUST_NAME) LIKE :search OR LOWER(CUST_CODE) LIKE :search)"
                
                # Limit results to 50
                query += " AND ROWNUM < 50 ORDER BY CUST_NAME"

                # Bind variables
                bind_vars = {'search': f'%{search.lower()}%'} if search else {}
                cmd.execute(query, bind_vars)

                rows = cmd.fetchall()
                columns = [col[0] for col in cmd.description]
                customers = [dict(zip(columns, row)) for row in rows]
                
        return jsonify(customers)
    except Exception as e:
        print("Error in customers:", e)
        return jsonify({"error": str(e)}), 500


    
@app.route("/itempage")
def itempage():
    try:
        with pool.acquire() as connection:
            cmd = connection.cursor()
            cmd.execute("SELECT DISTINCT CATEGORYNAME FROM ITEMMASTERDETAILS")
            result = cmd.fetchall()
            return render_template("itempage.html", value=result)
    except Exception as e:
        print("Error in /itempage:", e)
        return f"Error: {e}", 500








from flask import jsonify, request

@app.route("/search_items")
def search_items():
    itemcode = request.args.get("itemcode", "").strip().lower()
    customer = request.args.get("customer", "").strip().lower()
    itemname = request.args.get("itemname", "").strip().lower()
    category = request.args.get("category", "").strip().lower()

    with pool.acquire() as connection:
        cursor = connection.cursor()

        query = """
            SELECT 
                i.ITEMCODE,
                i.ITEMNAME,
                i.RETAILPRICE,
                i.UNIT,
                i.CATEGORYNAME,
                i.BARCODE,
                i.LOCATIONCODE,
                l.LOCATIONNAME
            FROM 
                ITEMMASTERDETAILS i
            JOIN 
                LOCATIONMASTER l
            ON 
                i.LOCATIONCODE = l.LOCATIONCODE WHERE 1=1 and TABLES='MASTER' and BaselocationFlag='Y'
        """

        params = {}

        if itemcode:
            query += " AND LOWER(ITEMCODE) LIKE :itemcode"
            params["itemcode"] = f"%{itemcode}%"

        if itemname:
            query += " AND LOWER(ITEMNAME) LIKE :itemname"
            params["itemname"] = f"%{itemname}%"

        if customer:
            query += " AND LOWER(SUPPLIERNAME) LIKE :customer"
            params["customer"] = f"%{customer}%"

        if category:
            query += " AND LOWER(CATEGORYNAME) LIKE :category"
            params["category"] = f"%{category}%"


        # ✅ Oracle-compatible limit clause
        query += " AND ROWNUM <= 50"

        try:
            cursor.execute(query, params)
            columns = [col[0].lower() for col in cursor.description]
            rows = cursor.fetchall()
            
            items = [dict(zip(columns, row)) for row in rows]
            print(items)
            print(items[0])
            print(type(items[0]["retailprice"]))

        except Exception as e:
            print("Error executing query:", e)
            return jsonify({"error": "Query failed"}), 500
        finally:
            cursor.close()

    return jsonify(items)



if __name__ == '__main__':
    app.run(debug=True)