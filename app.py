
import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
DB_PATH = os.environ.get("DATABASE_PATH", "mhz_erp.db")
csrf = CSRFProtect(app)

def get_db():
    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'Administrador',
        active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL,
        brand TEXT NOT NULL,
        name TEXT NOT NULL,
        weight TEXT,
        supplier TEXT,
        cost REAL NOT NULL DEFAULT 0,
        packaging TEXT NOT NULL DEFAULT '',
        other_costs REAL NOT NULL DEFAULT 0,
        sale_price REAL NOT NULL DEFAULT 0,
        min_stock INTEGER NOT NULL DEFAULT 1,
        current_stock INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'Ativo'
    );
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        customer TEXT NOT NULL,
        channel TEXT NOT NULL,
        total REAL NOT NULL DEFAULT 0,
        profit REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'Novo'
    );
    """)
    cur.execute("SELECT COUNT(*) AS n FROM users")
    if cur.fetchone()["n"] == 0:
        cur.execute("INSERT INTO users(name,email,password_hash,role) VALUES (?,?,?,?)",
                    ("Fernando Munhoz","admin@mhz.local",generate_password_hash("MHZ@2026"),"Administrador"))
    cur.execute("SELECT COUNT(*) AS n FROM products")
    if cur.fetchone()["n"] == 0:
        products = [
            ("CAF001","Café","Melitta","Regiões Brasileiras Mogiana","250 g","Carrefour",19.90,0,0,0,1,0,"Ativo"),
            ("CAF002","Café","Melitta","Regiões Brasileiras Cerrado","250 g","Carrefour",19.90,0,0,0,1,0,"Ativo"),
            ("CAF003","Café","Melitta","Regiões Brasileiras Sul de Minas","250 g","Carrefour",19.90,0,0,0,1,0,"Ativo"),
            ("CAF004","Café","3 Corações","Gourmet Dark Roast","250 g","Carrefour",23.50,0,0,0,1,0,"Ativo"),
            ("CAF005","Café","Baggio","Aromas Caramelo","250 g","Baggio",36.42,0,0,0,1,0,"Ativo"),
            ("CAF006","Café","Baggio","Chocolate com Avelã","250 g","Baggio",36.42,0,0,0,1,0,"Ativo"),
            ("CAF007","Café","Baggio","Chocolate Trufado","250 g","A definir",36.42,0,0,0,1,0,"Ativo"),
            ("CAF008","Café","Orfeu","Arara moído","250 g","Orfeu",43.90,0,9.94,0,1,0,"Ativo"),
            ("MEL001","Mel","Baldoni","Mel Silvestre","300 g","Baldoni",25.90,0,0,0,1,0,"Ativo"),
            ("GEL001","Geleia","Linea","Frutas Vermelhas","230 g","Carrefour",25.89,0,0,0,1,0,"Ativo"),
            ("TEM001","Tempero","Cozinha","Lemon Pepper","100 g","Carrefour",17.09,0,0,0,1,0,"Ativo"),
            ("TEM002","Tempero","Cozinha","Páprica Defumada","45 g","Carrefour",16.99,0,0,0,1,0,"Ativo")
        ]
        cur.executemany("""
            INSERT INTO products
            (code,category,brand,name,weight,supplier,cost,packaging,other_costs,sale_price,min_stock,current_stock,status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, products)
    conn.commit()
    conn.close()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

@app.before_request
def ensure_db():
    init_db()

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND active=1",(email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]
            return redirect(url_for("dashboard"))
        flash("E-mail ou senha inválidos.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/")
@login_required
def dashboard():
    conn = get_db()
    summary = conn.execute("""
        SELECT COUNT(*) products, COALESCE(SUM(current_stock),0) units,
        COALESCE(SUM(current_stock*cost),0) stock_cost,
        COALESCE(SUM(current_stock*sale_price),0) stock_value,
        COALESCE(SUM(CASE WHEN current_stock<=min_stock THEN 1 ELSE 0 END),0) low_stock
        FROM products WHERE status='Ativo'
    """).fetchone()
    sales = conn.execute("SELECT COALESCE(SUM(total),0) revenue, COALESCE(SUM(profit),0) profit, COUNT(*) orders FROM sales").fetchone()
    top = conn.execute("""
        SELECT code,brand,name,sale_price,cost,
        CASE WHEN sale_price>0 THEN ((sale_price-(cost+other_costs))/sale_price)*100 ELSE 0 END margin
        FROM products WHERE status='Ativo' ORDER BY margin DESC LIMIT 5
    """).fetchall()
    conn.close()
    ticket = sales["revenue"]/sales["orders"] if sales["orders"] else 0
    return render_template("dashboard.html", summary=summary, sales=sales, ticket=ticket, top=top)

@app.route("/products")
@login_required
def products():
    q = request.args.get("q","").strip()
    conn = get_db()
    if q:
        rows = conn.execute("""
            SELECT * FROM products WHERE code LIKE ? OR brand LIKE ? OR name LIKE ? OR category LIKE ?
            ORDER BY id DESC
        """, tuple([f"%{q}%"]*4)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("products.html", products=rows, q=q)

@app.route("/products/new", methods=["GET","POST"])
@login_required
def product_new():
    if request.method == "POST":
        d = request.form
        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO products(code,category,brand,name,weight,supplier,cost,packaging,other_costs,sale_price,min_stock,current_stock,status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,(d["code"].strip().upper(),d["category"],d["brand"],d["name"],d.get("weight",""),d.get("supplier",""),
                 float(d.get("cost") or 0),d.get("packaging",""),float(d.get("other_costs") or 0),
                 float(d.get("sale_price") or 0),int(d.get("min_stock") or 1),int(d.get("current_stock") or 0),d.get("status","Ativo")))
            conn.commit()
            flash("Produto cadastrado com sucesso.","success")
            return redirect(url_for("products"))
        except sqlite3.IntegrityError:
            flash("O código informado já existe.","error")
        finally:
            conn.close()
    return render_template("product_form.html", product=None)

@app.route("/products/<int:product_id>/edit", methods=["GET","POST"])
@login_required
def product_edit(product_id):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id=?",(product_id,)).fetchone()
    if not product:
        conn.close()
        return "Produto não encontrado",404
    if request.method == "POST":
        d=request.form
        try:
            conn.execute("""
                UPDATE products SET code=?,category=?,brand=?,name=?,weight=?,supplier=?,cost=?,packaging=?,other_costs=?,
                sale_price=?,min_stock=?,current_stock=?,status=? WHERE id=?
            """,(d["code"].strip().upper(),d["category"],d["brand"],d["name"],d.get("weight",""),d.get("supplier",""),
                 float(d.get("cost") or 0),d.get("packaging",""),float(d.get("other_costs") or 0),
                 float(d.get("sale_price") or 0),int(d.get("min_stock") or 1),int(d.get("current_stock") or 0),
                 d.get("status","Ativo"),product_id))
            conn.commit()
            flash("Produto atualizado.","success")
            return redirect(url_for("products"))
        except sqlite3.IntegrityError:
            flash("O código informado já existe.","error")
        finally:
            conn.close()
    conn.close()
    return render_template("product_form.html", product=product)

@app.route("/api/products")
@login_required
def api_products():
    conn=get_db()
    rows=conn.execute("SELECT * FROM products ORDER BY brand,name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.context_processor
def inject_user():
    return {"current_user_name":session.get("user_name"),"current_user_role":session.get("user_role")}

if __name__=="__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT",5000)),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )
