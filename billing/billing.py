import math
import cx_Oracle
from flask import Flask, redirect, render_template, request, url_for, jsonify
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
    max=20,
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

            # Replace 'YOUR_SCHEMA_NAME' with actual schema if needed
            query = """
                SELECT COLUMN_NAME 
                FROM ALL_TAB_COLUMNS 
                WHERE TABLE_NAME = 'CUSTOMERS'
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            html = "<h2>DB Test - Column Names from 'CUSTOMERS'</h2><ul>"
            html += f"<p>Rows fetched: {len(rows)}</p>"

            if not rows:
                html += "<p><b>No columns found. Check table name or schema.</b></p>"

            for idx, row in enumerate(rows, start=1):
                html += f"<li><b>Index {idx}:</b> {row[0]}</li><br>"

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
               
               if not rows:  # Check if rows is empty
                   return jsonify([])  # Return an empty list if no items found

               items = [dict(zip(columns, row)) for row in rows]
               print(items)
               print(items[0])  # This line may cause an error if items is empty
               print(type(items[0]["retailprice"]))

           except Exception as e:
               print("Error executing query:", e)
               return jsonify({"error": "Query failed"}), 500
           finally:
               cursor.close()

       return jsonify(items)

@app.route("/api/customer_code", methods=["GET"])
def get_customer_code():
    customer_name = request.args.get("customer_name", "").strip()
    
    if not customer_name:
        return jsonify({"error": "Customer name is required."}), 400

    try:
        with pool.acquire() as connection:
            cursor = connection.cursor()
            
            # Update the query with the correct schema if necessary
            query = """
                SELECT CUST_CODE 
                FROM customers  
                WHERE LOWER(CUST_NAME) = LOWER(:customer_name)
            """
            
            cursor.execute(query, {"customer_name": customer_name})
            result = cursor.fetchone()

            if result is None:
                return jsonify({"error": "Customer not found."}), 404
            
            customer_code = result[0]
            return jsonify({"customer_code": customer_code})

    except cx_Oracle.DatabaseError as e:
        error, = e.args
        print("Database error:", error.message)
        return jsonify({"error": "Database error: " + error.message}), 500
    except Exception as e:
        print("Error executing query:", e)
        return jsonify({"error": str(e)}), 500
    
@app.route("/get_item_units", methods=["GET"])
def get_item_units():
    item_code = request.args.get("itemcode", "").strip()
    
    if not item_code:
        return jsonify({"error": "Item code is required."}), 400

    try:
        with pool.acquire() as connection:
            cursor = connection.cursor()
            query = """
                SELECT DISTINCT UNIT FROM ITEMMASTERDETAILS WHERE ITEMCODE = :itemcode
            """
            cursor.execute(query, {"itemcode": item_code})
            units = cursor.fetchall()

            if not units:
                return jsonify([])  # Return an empty list if no units found

            # Format the results into a list
            unit_list = [row[0] for row in units]
            return jsonify(unit_list)

    except cx_Oracle.DatabaseError as e:
        error, = e.args
        print("Database error:", error.message)
        return jsonify({"error": "Database error: " + error.message}), 500
    except Exception as e:
        print("Error executing query:", e)
        return jsonify({"error": str(e)}), 500



@app.route("/api/purchased_items", methods=["GET"])
def get_purchased_items():
    customer_code = request.args.get("customer_code", "").strip()
    
    if not customer_code:
        return jsonify({"error": "Customer code is required."}), 400

    try:
        with pool.acquire() as connection:
            cursor = connection.cursor()
            
            # Update the query with the correct schema if necessary
            query = """
                SELECT DISTINCT 
                    im.itemcode,
                    im.itemname,
                    im.baseuom AS unit,
                    im.retailprice AS retail,
                    im.currentstock AS stock,
                    im.QUANTITYLIMIT AS limit,
                    im.description,
                    c.name AS micro,
                    b.name AS brand,
                    o.name AS origin,
                    p.name AS propertyname,
                    MAX(hdr.billdate) AS lastdate,
                    MAX(hdr.billno) AS billno,
                    MAX(hdr.customercode) AS customercode
                FROM 
                    itemmaster im
                JOIN 
                    (SELECT code, name FROM category WHERE flag = 'C') c ON im.categorycode = c.code
                JOIN 
                    (SELECT code, name FROM category WHERE flag = 'B') b ON im.brandcode = b.code
                JOIN 
                    (SELECT code, name FROM tblitemorigin) o ON im.origin = o.code
                JOIN 
                    (SELECT code, name FROM tblitemproperty) p ON im.property = p.code
                JOIN 
                    billdtlhistory dtl ON dtl.itemcode = im.itemcode
                JOIN 
                    billhdrhistory hdr ON dtl.billno = hdr.billno
                WHERE 
                    hdr.customercode = :customer_code
                GROUP BY 
                    im.itemcode, im.itemname, im.baseuom, im.retailprice, im.currentstock, 
                    im.QUANTITYLIMIT, c.name, b.name, o.name, p.name, im.description, im.itemflag, 
                    im.ownproduct
                ORDER BY 
                    billno, itemname DESC
            """
            
            cursor.execute(query, {"customer_code": customer_code})
            items = cursor.fetchall()

            if not items:
                return jsonify([])  # Return an empty list if no items found

            # Format the results into a list of dictionaries
            purchased_items = [
                {
                    "itemCode": row[0],
                    "itemName": row[1],
                    "unit": row[2],
                    "retail": float(row[3]),
                    "stock": row[4],
                    "limit": row[5],
                    "description": row[6],
                    "micro": row[7],
                    "brand": row[8],
                    "origin": row[9],
                    "propertyName": row[10],
                    "lastDate": row[11],
                    "billNo": row[12],
                    "customerCode": row[13]
                }
                for row in items
            ]
            print(purchased_items)
            
            return jsonify(purchased_items)

    except cx_Oracle.DatabaseError as e:
        error, = e.args
        print("Database error:", error.message)
        return jsonify({"error": "Database error: " + error.message}), 500
    except Exception as e:
        print("Error executing query:", e)
        return jsonify({"error": str(e)}), 500





if __name__ == '__main__':
    app.run(debug=True)