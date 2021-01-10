#Heroku git remote is herokuRPG

# Required Imports
import os
from flask import Flask, request, jsonify
from firebase_admin import credentials, firestore, initialize_app
from flask_bcrypt import Bcrypt
from flask_cors import CORS

# Initialize Flask App
app = Flask(__name__)
CORS(app)
# Initialize Firestore DB
cred = credentials.Certificate('key.json')
default_app = initialize_app(cred)
db = firestore.client()

#initialize password hashing object
bcrypt = Bcrypt(app)

player_cursor = db.collection('player')
challenge_cursor = db.collection('challenge')
shop = db.collection('shop')


NEW_PLAYER_DATA = {
	"armor": None,
	"charisma": 1,
	"coins": 0,
	"creativity": 1,
	"hat": None,
	"health": 1,
	"intelligence": 1,
	"strength": 1,
	"weapon": None,
	"xp": 5
}

########################################
## Player Endpoints
########################################

#route to add new users to the database
@app.route('/addPlayer', methods=['POST'])
def create():
	#format
	#username, email, password, xp, coins, health, strength, intelligence, creativity, charisma, hat, armor, weapon
	#friends, tasks, and itemsOwned are collections within a player that have their own endpoints

	try:
		data = request.json

		player_data = NEW_PLAYER_DATA

		player = player_cursor.document(data['username']).get().to_dict()
		if player is None:
			player_data["password"] = bcrypt.generate_password_hash(data['password'])
			player_data["username"] = data['username']
			player_data["email"] = data['email']

			player_cursor.document(data['username']).set(player_data)
		else:
			return jsonify({"message": "This username is already taken"}), 200

		return jsonify({"message": "success"}), 200
	except Exception as e:
		return f"An Error Occured: {e}"


#returns a specific player
#NOTE: must replace spaces in name with %20 because a url param cannot have spaces 
@app.route('/getPlayer/<username>', methods=['GET'])
def find(username):
	try:   
		if username:
			player = player_cursor.document(username).get()
			player = player.to_dict()
			player.pop("password") #password must be removed to jsonify the dictionary
			
			return jsonify(player), 200
		else:
			return "No username was passed!", 200

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


#authentication
@app.route('/login', methods=['POST'])
def auth():
	#request should include a username and password
	try:
		req = request.json
		result = player_cursor.document(req['username']).get()	#get user
		if result.to_dict() is not None:	#if user is found then check password using hash function
			player = result.to_dict()
			if bcrypt.check_password_hash(player['password'], req['password']):
				return jsonify({"message": "success"}), 200
		
		return jsonify({"message": "declined"}), 200
		
	except Exception as e:
		return f"An Error Occured: {e}"


########################################
## Task Endpoints
########################################

#this endpoint is to add tasks for a specific user
#NOTE: task id's are actually strings, not integers
@app.route('/addTask', methods=['POST'])
def createTask():
	#format
	#id, name, statType, statVal, completionTime for task (probably empty when adding (but make sure to add it))
	#username to be entered for
	
	try:
		format = request.json
		username = format.pop('username')
		player_cursor.document(username).collection('tasks').document(format['id']).set(format)
		return jsonify({"success": True}), 200
	except Exception as e:
		return f"An Error Occured: {e}"


@app.route('/completeTask', methods=['POST', 'PUT'])
def complete():
    #must pass a username so client knows who to update
	#must pass task id so task can be completed
	try:
		format = request.json
		username = format.pop('username')
		id = format.pop('id')

		#check to see if task has been completed (date is initially "" before being completed)
		task = player_cursor.document(username).collection('tasks').document(id).get().to_dict()
		if task['completionTime'] != "\"\"":
			return jsonify({"message": "This task has already been completed!"}), 200

		#update task completion time
		format['completionTime'] = firestore.SERVER_TIMESTAMP
		player_cursor.document(username).collection('tasks').document(id).update(format)

		#update player stat and xp
		
		player = player_cursor.document(username).get().to_dict()
		player_cursor.document(username).update({task['statType']: player[task['statType']]+task['statVal'], "xp": player['xp'] + task['statVal']})

		return jsonify({"success": True}), 200

	except Exception as e:
		return f"An Error Occured: {e}"


@app.route('/deleteTask', methods=['DELETE'])
def deleteTask():
    #must pass a username so client knows who to delete
	#must pass task id so task can be deleted
	try:
		format = request.json
		username = format.pop('username')
		id = format.pop('id')
		player_cursor.document(username).collection('tasks').document(id).delete()
		return jsonify({"success": True}), 200

	except Exception as e:
		return f"An Error Occured: {e}"

#route to get a list of users tasks
@app.route('/getTasks/<username>', methods=['GET'])
def getTasks(username):
	try:
		tasks = player_cursor.document(username).collection('tasks').stream()
		result = {}
		for task in tasks:
			result[task.to_dict()['id']] = task.to_dict()

		return result, 200
	except Exception as e:
		return f"An Error Occured: {e}"


########################################
## Friend Endpoints
########################################

#endpoint to add friends
@app.route('/addFriend', methods=['POST'])
def addFriend():
	#format
	#username and friend
	
	try:
		format = request.json
		username = format.pop('username')
		player_cursor.document(username).collection('friends').document(format['friend']).set(format)
		return jsonify({"success": True}), 200
	except Exception as e:
		return f"An Error Occured: {e}"
	
#route to get friends
@app.route('/getFriends/<username>', methods=['GET'])
def getFriends(username):
	try:
		#4 states for challenges: accept/decline, pending, view, challenge
		#accept/decline if you are receiver and friend is sender + accepted = false
		#pending if you are sender and friend is receiver + accepted = false
		#view if you are receiver OR sender + accepted = true
		#challenge if friend is niether a sender or receiver

		friends = player_cursor.document(username).collection('friends').stream()
		challenges = challenge_cursor.stream()
		result = {}
		for friend in friends:
			friendName = friend.to_dict()['friend']
			state = "challenge"
			for challenge in challenges:
				receiver = challenge.to_dict()['receiver']
				sender = challenge.to_dict()['sender']
				accepted = challenge.to_dict()['accepted']
				
				if(friendName == sender and username == receiver and accepted == False):
					state = "accept"
				elif(friendName == receiver and username == sender and accepted == False):
					state = "pending"
				elif(username == receiver or username == sender and accepted == True):
					state = "view"
			returnObject = {
				"friend": friendName,
				"state": state
			}
			result[friendName] = returnObject

		return result, 200
	except Exception as e:
		return f"An Error Occured: {e}"


########################################
## Challenge Endpoints
########################################

#route to add challenges
@app.route('/addChallenge', methods=['POST'])
def addChallenge():
	#format
	#sender, receiver
	
	try:
		format = request.json

		format['accepted'] = False
		format['completed'] = False
		sender = player_cursor.document(format['sender']).get().to_dict()
		format['senderStartXp'] = sender['xp']
		receiver = player_cursor.document(format['receiver']).get().to_dict()
		format['receiverStartXp'] = receiver['xp']
		format['senderEndXp'] = -1
		format['receiverEndXp'] = -1
		format['start'] = ""

		key = format['sender'] + "-" + format['receiver']
		challenge_cursor.document(key).set(format)
		return jsonify({"success": True}), 200
	except Exception as e:
		return f"An Error Occured: {e}"

#endpoint updates a challenge to be accepted
@app.route('/acceptChallenge', methods=['POST', 'PUT'])
def acceptChallenge():
	#format
	#sender, receiver
	
	try:
		format = request.json
		key = format['sender'] + "-" + format['receiver']
		challenge_cursor.document(key).update({"accepted": True, 'start': firestore.SERVER_TIMESTAMP})
		return jsonify({"success": True}), 200
	except Exception as e:
		return f"An Error Occured: {e}"

#endpoint updates a challenge to be completed
@app.route('/completeChallenge', methods=['POST', 'PUT'])
def completeChallenge():
	#format
	#sender, receiver	
	try:
		#add stuff to winner
		format = request.json
		key = format['sender'] + "-" + format['receiver']

		#get the current challenge data and player data
		curr_challenge = challenge_cursor.document(key).get().to_dict()
		sender = player_cursor.document(format['sender']).get().to_dict()
		receiver = player_cursor.document(format['receiver']).get().to_dict()

		#adjust coins based on who won
		senderGains = sender['xp'] - curr_challenge['senderStartXp']
		receiverGains = receiver['xp'] - curr_challenge['receiverStartXp']
		if senderGains > receiverGains:
			player_cursor.document(sender['username']).update({"coins": sender['coins']+100})
		elif senderGains < receiverGains:
			player_cursor.document(receiver['username']).update({"coins": receiver['coins']+100})


		challenge_cursor.document(key).update({"completed": True, "senderEndXp": sender['xp'], "receiverEndXp": receiver['xp']})
		return jsonify({"success": True}), 200
	except Exception as e:
		return f"An Error Occured: {e}"

#endpoint returns a specific challenge
@app.route('/getChallenge/<sender>/<receiver>', methods=['GET'])
def getChallenge(sender, receiver):
	#format
	#sender, receiver
	
	try:
		key = sender + "-" + receiver
		#get challenge and players
		challenge = challenge_cursor.document(key).get().to_dict()
		send = player_cursor.document(sender).get().to_dict()
		rec = player_cursor.document(receiver).get().to_dict()

		#calculate the current gains in xp since challenge began
		challenge['senderGains'] = send['xp'] - challenge['senderStartXp']
		challenge['receiverGains'] = rec['xp'] - challenge['receiverStartXp']

		return challenge, 200
	except Exception as e:
		return f"An Error Occured: {e}"


########################################
## Items Endpoints
########################################


#route to add items to the shop
@app.route('/addItem', methods=['POST'])
def addItem():
	#format
	#name, url, price, type (hat, weapon, or armor)
	
	try:
		format = request.json
		shop.document(format['name']).set(format)
		return jsonify({"success": True}), 200
	except Exception as e:
		return f"An Error Occured: {e}"

#route to get all shop items
@app.route('/getShop', methods=['GET'])
def getShop():
	try:
		items = shop.stream()
		result = {}
		for item in items:
			result[item.to_dict()['name']] = item.to_dict()

		return result, 200
	except Exception as e:
		return f"An Error Occured: {e}"

#route to purchase an item for a player
@app.route('/purchaseItem', methods=['POST'])
def purchaseItem():
	#format
	#username, name (name of item)
	
	try:
		format = request.json
		item = shop.document(format['name']).get().to_dict()
		player = player_cursor.document(format['username']).get().to_dict()

		#execute transaction
		if player['coins'] >= item['price']:
			player_cursor.document(format['username']).update({"coins": player['coins']-item['price']})
		else:
			return jsonify({"message": "Insufficient Funds"}), 200

		#add item to itemsOwned list name, type, url
		item.pop('price')
		player_cursor.document(format['username']).collection('itemsOwned').document(format['name']).set(item)
		return jsonify({"success": True}), 200
	except Exception as e:
		return f"An Error Occured: {e}"


#route to equip an item for a player
@app.route('/equipItem', methods=['PUT', 'POST'])
def equipItem():
	#format
	#username, name (name of item)
	try:
		format = request.json
		item = player_cursor.document(format['username']).collection('itemsOwned').document(format['name']).get().to_dict()

		if item is not None:
			player_cursor.document(format['username']).update({item['type']: item})
		else:
			return jsonify({"message": "player does not have this item (or player doesn't exist)"}), 200

	
		return jsonify({"success": True}), 200
	except Exception as e:
		return f"An Error Occured: {e}"



port = int(os.environ.get('PORT', 8080))
if __name__ == '__main__':
    app.run(threaded=True, host='0.0.0.0', port=port)


