# Required Imports
import os
from flask import Flask, request, jsonify
from firebase_admin import credentials, firestore, initialize_app

# Initialize Flask App
app = Flask(__name__)
# Initialize Firestore DB
cred = credentials.Certificate('key.json')
default_app = initialize_app(cred)
db = firestore.client()

player_cursor = db.collection('player')
challenge_cursor = db.collection('challenge')
shop = db.collection('shop')


#route to add new users to the database
@app.route('/addPlayer', methods=['POST'])
def create():
	#format
	#username, email, password, xp, coins, health, strength, intelligence, creativity, charisma, friends (object of its own), tasks (object of its own), hat, armor, weapon, itemsOwned (object of its own)
	
    try:
        player_cursor.document(request.json['username']).set(request.json)
        return jsonify({"success": True}), 200
    except Exception as e:
        return f"An Error Occured: {e}"


#returns a specific player
#Note: must replace spaces in name with %20 because a url param cannot have spaces 
@app.route('/getPlayer/<username>', methods=['GET'])
def find(username):
	try:   
		if username:
			player = player_cursor.document(username).get()
			return jsonify(player.to_dict()), 200
		else:
			return "No username was passed!"

	except Exception as e:
		return f"An Error Occured: {e}"

@app.route('/updatePlayer', methods=['POST', 'PUT'])
def update():
    #must pass a username so client knows who to update
    try:
        username = request.json['username']
        player_cursor.document(username).update(request.json)
        return jsonify({"success": True}), 200

    except Exception as e:
        return f"An Error Occured: {e}"




port = int(os.environ.get('PORT', 8080))
if __name__ == '__main__':
    app.run(threaded=True, host='0.0.0.0', port=port)


