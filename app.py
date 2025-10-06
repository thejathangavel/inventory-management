# app.py
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret'  # for flash messages
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------------
# Models
# -------------------------
class Product(db.Model):
    product_id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(120), nullable=False)

class Location(db.Model):
    location_id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(120), nullable=False)

class ProductMovement(db.Model):
    movement_id = db.Column(db.String(36), primary_key=True)
    timestamp = db.Column(db.DateTime, server_default=func.now())
    from_location = db.Column(db.String(36), db.ForeignKey('location.location_id'), nullable=True)
    to_location = db.Column(db.String(36), db.ForeignKey('location.location_id'), nullable=True)
    product_id = db.Column(db.String(36), db.ForeignKey('product.product_id'), nullable=False)
    qty = db.Column(db.Integer, nullable=False)

# -------------------------
# Create tables
# -------------------------
with app.app_context():
    db.create_all()

# -------------------------
# Home
# -------------------------
@app.route('/')
def index():
    return redirect(url_for('list_products'))

# -------------------------
# Product CRUD
# -------------------------
@app.route('/products')
def list_products():
    products = Product.query.order_by(Product.name).all()
    return render_template('products/list.html', products=products)

@app.route('/products/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        pid = request.form.get('product_id') or str(uuid.uuid4())
        name = request.form.get('name').strip()
        if not name:
            flash('Product name required')
            return redirect(url_for('add_product'))
        if Product.query.get(pid):
            flash('Product ID already exists')
            return redirect(url_for('add_product'))
        p = Product(product_id=pid, name=name)
        db.session.add(p)
        db.session.commit()
        return redirect(url_for('list_products'))
    return render_template('products/form.html', product=None)

@app.route('/products/edit/<product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    p = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        p.name = request.form.get('name').strip()
        db.session.commit()
        return redirect(url_for('list_products'))
    return render_template('products/form.html', product=p)

# -------------------------
# Location CRUD
# -------------------------
@app.route('/locations')
def list_locations():
    locations = Location.query.order_by(Location.name).all()
    return render_template('locations/list.html', locations=locations)

@app.route('/locations/add', methods=['GET', 'POST'])
def add_location():
    if request.method == 'POST':
        lid = request.form.get('location_id') or str(uuid.uuid4())
        name = request.form.get('name').strip()
        if not name:
            flash('Location name required')
            return redirect(url_for('add_location'))
        if Location.query.get(lid):
            flash('Location ID already exists')
            return redirect(url_for('add_location'))
        l = Location(location_id=lid, name=name)
        db.session.add(l)
        db.session.commit()
        return redirect(url_for('list_locations'))
    return render_template('locations/form.html', location=None)

@app.route('/locations/edit/<location_id>', methods=['GET', 'POST'])
def edit_location(location_id):
    l = Location.query.get_or_404(location_id)
    if request.method == 'POST':
        l.name = request.form.get('name').strip()
        db.session.commit()
        return redirect(url_for('list_locations'))
    return render_template('locations/form.html', location=l)

# -------------------------
# Product Movements
# -------------------------
@app.route('/movements')
def list_movements():
    movements = ProductMovement.query.order_by(ProductMovement.timestamp.desc()).all()
    products = {p.product_id: p.name for p in Product.query.all()}
    locations = {l.location_id: l.name for l in Location.query.all()}
    return render_template('movements/list.html', movements=movements, products=products, locations=locations)

@app.route('/movements/add', methods=['GET', 'POST'])
def add_movement():
    products = Product.query.order_by(Product.name).all()
    locations = Location.query.order_by(Location.name).all()
    if request.method == 'POST':
        mid = str(uuid.uuid4())
        product_id = request.form.get('product_id')
        qty = int(request.form.get('qty') or 0)
        from_loc = request.form.get('from_location') or None
        to_loc = request.form.get('to_location') or None
        if not product_id or qty <= 0:
            flash('Choose product and positive qty')
            return redirect(url_for('add_movement'))
        m = ProductMovement(
            movement_id=mid,
            product_id=product_id,
            qty=qty,
            from_location=from_loc,
            to_location=to_loc
        )
        db.session.add(m)
        db.session.commit()
        return redirect(url_for('list_movements'))
    return render_template('movements/form.html', products=products, locations=locations)

# -------------------------
# Report: Balance per product per location
# -------------------------
@app.route('/report')
def report():
    products = Product.query.order_by(Product.name).all()
    locations = Location.query.order_by(Location.name).all()
    rows = []
    for p in products:
        for l in locations:
            inbound = db.session.query(func.coalesce(func.sum(ProductMovement.qty), 0))\
                .filter(ProductMovement.product_id==p.product_id, ProductMovement.to_location==l.location_id).scalar()
            outbound = db.session.query(func.coalesce(func.sum(ProductMovement.qty), 0))\
                .filter(ProductMovement.product_id==p.product_id, ProductMovement.from_location==l.location_id).scalar()
            qty = (inbound or 0) - (outbound or 0)
            rows.append({'product': p.name, 'warehouse': l.name, 'qty': qty})
    return render_template('report.html', rows=rows)

# -------------------------
# Run the app
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)
