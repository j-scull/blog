#from flask import Flask
#app = Flask(__name__)


#from flask import request, make_response, redirect, abort


@app.route('/')
def index():
    return '<h1>Yo-Yo-Yo</h1>'

@app.route('/user/<name>')
def user(name):
    if name.lower() != 'joe':
        abort(404)
    return '<h1>Yo, {}!</h1>'.format(name)

@app.route('/agent')
def agent():
    user_agent = request.headers.get('User-Agent')
    return '<p>Your browser is {}</p>'.format(user_agent)

@app.route('/response')
def response():
    response = make_response('<h1>Cookie!</h1>')
    response.set_cookie('answer', '42')
    return response

@app.route('/redirect')
def redirect():
    return redirect('https://www.theguardian.com')