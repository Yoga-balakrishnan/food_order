from flask import Flask, request, render_template, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a random secret key

# Database setup
def init_db():
    conn = sqlite3.connect('data/food_order.db')  # Update the path to the database
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            image TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            food_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (food_id) REFERENCES foods (id)
        )
    ''')
    # Insert sample foods with images from the static folder
    cursor.execute('INSERT OR IGNORE INTO foods (name, price, image) VALUES (?, ?, ?)', ('Pizza', 10.99, '/static/images/pizza.jpg'))
    cursor.execute('INSERT OR IGNORE INTO foods (name, price, image) VALUES (?, ?, ?)', ('Pasta', 7.99, '/static/images/pasta.jpg'))
    cursor.execute('INSERT OR IGNORE INTO foods (name, price, image) VALUES (?, ?, ?)', ('Dosa', 8.99, '/static/images/dosa.jpg'))
    cursor.execute('INSERT OR IGNORE INTO foods (name, price, image) VALUES (?, ?, ?)', ('Idly', 5.49, '/static/images/idly.jpg'))
    cursor.execute('INSERT OR IGNORE INTO foods (name, price, image) VALUES (?, ?, ?)', ('Poori', 6.99, '/static/images/poori.jpg'))
    cursor.execute('INSERT OR IGNORE INTO foods (name, price, image) VALUES (?, ?, ?)', ('Vada', 3.99, '/static/images/vada.jpeg'))
    cursor.execute('INSERT OR IGNORE INTO foods (name, price, image) VALUES (?, ?, ?)', ('Meal', 12.99, '/static/images/meals.jpeg'))
    cursor.execute('INSERT OR IGNORE INTO foods (name, price, image) VALUES (?, ?, ?)', ('Fried Rice', 9.99, '/static/images/friedrice.jpeg'))
    cursor.execute('INSERT OR IGNORE INTO foods (name, price, image) VALUES (?, ?, ?)', ('Mutton Biryani', 14.99, '/static/images/muttonbiriyani.jpeg'))
    cursor.execute('INSERT OR IGNORE INTO foods (name, price, image) VALUES (?, ?, ?)', ('Veg Biryani', 11.99, '/static/images/vegbiriyani.jpg'))
    cursor.execute('INSERT OR IGNORE INTO foods (name, price, image) VALUES (?, ?, ?)', ('Chicken Biryani', 13.99, '/static/images/chickenbiriyni.jpg'))
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('data/food_order.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user[2], password):
            session['username'] = username
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        conn = sqlite3.connect('data/food_order.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error='Username already exists')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    conn = sqlite3.connect('data/food_order.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM foods')
    foods = cursor.fetchall()
    cursor.execute('SELECT * FROM users WHERE username = ?', (session['username'],))
    user = cursor.fetchone()
    cursor.execute(''' 
        SELECT orders.id, foods.name, foods.image, foods.price 
        FROM orders 
        JOIN foods ON orders.food_id = foods.id 
        WHERE orders.user_id = ? 
    ''', (user[0],))
    orders = cursor.fetchall()
    
    # Calculate total amount
    total_amount = sum(order[3] for order in orders)  # Assuming order[3] contains the price

    conn.close()
    return render_template('home.html', foods=foods, orders=orders, total_amount=total_amount)

@app.route('/order/<int:food_id>', methods=['GET'])
def order(food_id):
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    conn = sqlite3.connect('data/food_order.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (session['username'],))
    user = cursor.fetchone()
    
    # Insert the selected food item into the orders table
    cursor.execute('INSERT INTO orders (user_id, food_id) VALUES (?, ?)', (user[0], food_id))
    conn.commit()
    conn.close()
    
    # Redirect to the payment page after ordering
    return redirect(url_for('payment'))

@app.route('/delete_order', methods=['POST'])
def delete_order():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    conn = sqlite3.connect('data/food_order.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?', (session['username'],))
    user_id = cursor.fetchone()[0]
    
    # Delete all orders for the user
    cursor.execute('DELETE FROM orders WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove username from session
    return redirect(url_for('login'))  # Redirect to login after logout

@app.route('/payment', methods=['GET'])
def payment():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    conn = sqlite3.connect('data/food_order.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (session['username'],))
    user = cursor.fetchone()
    
    # Check if the user has any orders
    cursor.execute(''' 
        SELECT COUNT(*) 
        FROM orders 
        WHERE user_id = ? 
    ''', (user[0],))
    order_count = cursor.fetchone()[0]

    if order_count == 0:
        return redirect(url_for('home'))  # Redirect to home if no orders

    # Calculate total amount
    cursor.execute(''' 
        SELECT SUM(foods.price) 
        FROM orders 
        JOIN foods ON orders.food_id = foods.id 
        WHERE orders.user_id = ? 
    ''', (user[0],))
    total_amount = cursor.fetchone()[0] or 0  # Get total amount or 0 if no orders
    
    # Get success message if it exists
    success_message = request.args.get('success')
    
    conn.close()
    return render_template('payment.html', total_amount=total_amount, success_message=success_message)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    payment_method = request.form['payment_method']
    total_amount = float(request.form['total_amount'])
    
    # Prepare a success message
    success_message = "Thank you for your payment. Your order will be deliverd soon!!!."

    # Get the user ID
    conn = sqlite3.connect('data/food_order.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?', (session['username'],))
    user_id = cursor.fetchone()[0]

    # Delete all orders for the user
    cursor.execute('DELETE FROM orders WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

    if payment_method == 'online':
        # Redirect to the payment confirmation page with a success message
        return render_template('payment_confirmation.html', success_message=success_message)
    
    elif payment_method == 'cash':
        # Display thank you message directly for cash on delivery
        return render_template('thank_you.html', success_message=success_message)

    # Default redirect if needed
    return redirect(url_for('home'))

@app.route('/payment_confirmation')
def payment_confirmation():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    total_amount = request.args.get('total_amount', type=float)
    return render_template('payment_confirmation.html', total_amount=total_amount)

if __name__ == '__main__':
    init_db()  # Initialize the database
    app.run(host='0.0.0.0', port=5000, debug=True)