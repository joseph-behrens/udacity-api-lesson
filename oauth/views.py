from models import Base, User
from flask import (Flask, jsonify, request, url_for, abort, g,
make_response, render_template)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
import json, httplib2, requests
from flask_httpauth import HTTPBasicAuth
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError


auth = HTTPBasicAuth()

engine = create_engine('sqlite:///users.db')

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()
app = Flask(__name__)

CLIENT_ID = json.loads(open('client_secret.json', 'r').read())['web']['client_id']


@auth.verify_password
def verify_password(username_or_token, password):
    user_id = User.verify_auth_token(username_or_token)
    if user_id:
        user = session.query(User).filter_by(id=user_id).first()
    else:
        user = session.query(User).filter_by(username=username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True


@app.route('/clientOAuth')
def start():
    return render_template('clientOAuth.html')


@app.route('/oauth/<provider>', methods=['POST'])
def login(provider):
    # Parse the auth code
    auth_code = request.json.get('auth_code')
    print("Received the authorization code {0}".format(auth_code))
    if provider == 'google':
        # Exchange the auth code for a token
        try:
            # The oauth2client.client.flow_from_clientsecrets() method creates a Flow
            # object from a client_secrets.json file. This JSON formatted file stores
            # your client ID, client secret, and other OAuth 2.0 parameters.

            # from oauth2client.client import flow_from_clientsecrets
            # ...
            # flow = flow_from_clientsecrets('path_to_directory/client_secrets.json',
            #                             scope='https://www.googleapis.com/auth/calendar',
            #                             redirect_uri='http://example.com/auth_return')
            oauth_flow = flow_from_clientsecrets('client_secret.json', scope='')
            oauth_flow.redirect_uri = 'postmessage'
            # The step2_exchange() function of the Flow class exchanges an authorization
            # code for a Credentials object. Pass the code provided by the authorization
            # server redirection to this function:
            credentials = oauth_flow.step2_exchange(auth_code)
        except FlowExchangeError:
            response = make_response(json.dumps('Failed to upgrade the authorization code'), 401)
            response.headers['Content-Type'] = 'application/json'
            return response

        # Validate the token
        access_token = credentials.access_token
        url = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={0}'.format(access_token)
        h = httplib2.Http()
        result = json.loads(h.request(url, 'GET')[1])
        if result.get('error') is not None:
            response = make_response(json.dumps('error'), 500)
            response.headers['Content-Type'] = 'application/json'

        print("Access Token: {0}".format(credentials.access_token))

        # Find user in db, if none create
        h = httplib2.Http()
        userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
        params = {'access_token': credentials.access_token, 'alt':'json'}
        answer = requests.get(userinfo_url, params=params)
        data = answer.json()
        name = data['name']
        picture = data['picture']
        email = data['email']

        user = session.query(User).filter_by(email=email).first()
        if not user:
            user = User(
                username=name,
                picture=picture,
                email=email
            )
            session.add(user)
            session.commit()

        token = user.generate_auth_token(600)
        return jsonify({'token': token.decode('ascii')})
    else:
        return 'Provider {0} not recognized'.format(provider)


@app.route('/token')
@auth.login_required
def get_auth_token():
    token = g.user.generate_auth_token()
    return jsonify({'token': token.decode('ascii')})


@app.route('/users', methods = ['POST'])
def new_user():
    username = request.json.get('username')
    password = request.json.get('password')
    if username is None or password is None:
        print("missing params")
        abort(400) # missing arguments
    if session.query(User).filter_by(username = username).first() is not None:
        print("user exists")
        abort(400) # existing user
    user = User(username=username)
    user.hash_password(password)
    session.add(user)
    session.commit()
    return jsonify({ 'username': user.username }), 201, {'Location': url_for('get_user', id = user.id, _external = True)}

@app.route('/api/users/<int:id>')
def get_user(id):
    user = session.query(User).filter_by(id=id).one()
    if not user:
        abort(400)
    return jsonify({'username': user.username})


@app.route('/get-users')
def get_all_users():
    users = session.query(User).all()
    return jsonify(users=[user.serialize for user in users])


@app.route('/api/resource')
@auth.login_required
def get_resource():
    return jsonify({'data':'Hello, {0}'.format(g.user.username)})


if __name__ == '__main__':
    app.debug = True
app.run(host='0.0.0.0', port=5000)