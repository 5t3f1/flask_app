from flask import (
    Flask,
    flash,
    render_template, 
    redirect,
    request,
    logging,
    session, 
    url_for
)
from data import Movies
from flaskext.mysql import MySQL
from wtforms import (
    Form, 
    StringField, 
    FloatField,
    TextAreaField, 
    PasswordField,
    validators
)
from passlib.hash import sha256_crypt
from functools import wraps


app = Flask(__name__)
app.secret_key = 'bestKeptsecret'

app.config['MYSQL_DATABASE_HOST'] = 'localhost'
app.config['MYSQL_DATABASE_PORT'] = 3308
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'flaskapp'
app.config['MYSQL_DATABASE_CURSORCLASS'] = 'DictCursor'

mysql = MySQL()
mysql.init_app(app)

Movies = Movies()

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/movies')
def movies():
    return render_template('movies.html', movies=Movies)

@app.route('/movies/<string:id>/')
def movie(id):
    movie = Movies[int(id)-1]
    cur = mysql.get_db().cursor()

    result = cur.execute("SELECT * FROM reviews WHERE movie = %s", movie['name'])

    reviews = cur.fetchall()

    if result > 0:
        return render_template('movie.html',movie=movie, reviews=reviews)
    else:
        msg = 'No Reviews Added Yet'
        return render_template('movie.html', movie=movie, msg=msg)

class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=30)])
    username = StringField('Username', [validators.Length(min=1, max=20)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Password')]
        )
    confirm = PasswordField('Confirm Passwod')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        cur = mysql.get_db().cursor()

        cur.execute("INSERT INTO users(name, username, password) VALUES(%s, %s, %s)", (name, username, password))

        mysql.connect()

        cur.close()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']
        cur = mysql.get_db().cursor()

        result = cur.execute('SELECT * FROM users WHERE username = %s', [username])

        if result > 0:
            data = cur.fetchone()
            
            password = data[3]
            if sha256_crypt.verify(password_candidate, password):
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in.')
                return redirect(url_for('dashboard'))
            else:
                error = 'Wrong password'
                return render_template('login.html', error=error)

            cur.close()

        else:
            error = 'User not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, please login.', 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

class ReviewForm(Form):
    content = TextAreaField('Content', [validators.Length(min=1)])

class RateForm(Form):
    rate = FloatField('Rate', [validators.required()])

@app.route('/add_review/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def add_review(id):
    form = ReviewForm(request.form)
    movie = Movies[int(id)-1]['name']
    
    if request.method == 'POST' and form.validate():
        content = form.content.data
        
        cur = mysql.get_db().cursor()

        cur.execute("INSERT INTO reviews(movie, content, user) VALUES(%s, %s, %s)", (movie, content, session['username']))

        mysql.connect()

        cur.close()
    
        flash('Review added', 'success')

        return redirect((url_for('dashboard')))

    return render_template('add_review.html', form=form)

@app.route('/add_rate/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def add_rate(id):
    form = RateForm(request.form)
    movie = Movies[int(id)-1]['name']
    
    if request.method == 'POST' and form.validate():
        user_rate = (form.rate.data)
        
        cur = mysql.get_db().cursor()
        cur.execute("INSERT INTO rate(movie, rating) VALUES(%s, %s)", (movie, user_rate))

        cur.execute("SELECT AVG(rating) AS user FROM rate WHERE movie = %s", movie)
        result = cur.fetchall()

        mysql.connect()

        cur.close()

        Movies[int(id)-1]['user_rate'] = round(result[0][0], 2)
        flash('Rate added', 'success')

        return redirect(url_for('dashboard'))

    return render_template('add_rate.html', form=form)


@app.route ('/dashboard')
@is_logged_in
def dashboard():
    cur = mysql.get_db().cursor()

    result = cur.execute("SELECT * FROM reviews WHERE user = %s", [session['username']])

    reviews = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', reviews=reviews)
    else:
        msg = 'No Reviews Added Yet'
        return render_template('dashboard.html', msg=msg)

    cur.close()

if __name__ == '__main__':
    app.run(debug=True)

