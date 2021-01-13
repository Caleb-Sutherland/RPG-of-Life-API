#Heroku git remote is herokuRPG

# Required Imports
import os
import datetime
import uuid
import js2py
import random
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
lore = db.collection('lore')


NEW_PLAYER_DATA = {
	"charisma": 1,
	"coins": 0,
	"creativity": 1,
	"health": 1,
	"intelligence": 1,
	"strength": 1,
	"chest": None,
	"weapon": None,
	"boots": None,
	"pants": None,
	"hat": None,
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
			
			eval_res, jsFile = js2py.run_file('backstories.js')
			num = random.randrange(1,3)
			story = jsFile.nameGen(num)
			lore.document(data['username']).set({"username": data['username'], "lore": story})
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
	#name, statType, statVal, for task (probably empty when adding (but make sure to add it))
	#username to be entered for
	
	try:
		format = request.json
		username = format.pop('username')
		format['completionTime'] = ""
		format['completedToday'] = False
		format['id'] = str(uuid.uuid4())
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
		if task['completionTime'] != "":
			now = datetime.datetime.today()
			now = now.replace(hour=0, minute=0, second=0, microsecond=0)
			now = now.replace(tzinfo=datetime.timezone.utc)
			completionTime = task['completionTime']
			if(completionTime > now):
				return jsonify({"message": "You can only complete this task once a day!"})
			else:
				print("This is valid to complete")
			
		#update task completion time
		format['completionTime'] = firestore.SERVER_TIMESTAMP
		format['completedToday'] = True
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
		now = datetime.datetime.today()
		now = now.replace(hour=0, minute=0, second=0, microsecond=0)
		now = now.replace(tzinfo=datetime.timezone.utc)
		
		for task in tasks:
			completionTime = task.to_dict()['completionTime']
			print(completionTime)
			if completionTime != "" and completionTime < now and task.to_dict()['completedToday']:
				player_cursor.document(username).collection('tasks').document(task.to_dict()['id']).update({"completedToday": False})
				temp = player_cursor.document(username).collection('tasks').document(task.to_dict()['id']).get().to_dict()
				result[temp['id']] = temp
			else:
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

		#checking to make sure the friend you are trying to add exists and that you dont already have them as a friend
		friend = player_cursor.document(format['friend']).get().to_dict()
		if friend is None:
			return jsonify({"message": "User does not exist."}), 200

		friends = player_cursor.document(username).collection('friends').stream()
		for person in friends:
			if person.to_dict()['friend'] == format['friend']:
				return jsonify({"message": "You already have that friend!"}), 200

		#add eachother as friends for both users (will add "accept friend" button later, for now it just auto adds as friend)
		player_cursor.document(username).collection('friends').document(format['friend']).set(format)
		player_cursor.document(format['friend']).collection('friends').document(username).set({"friend": username})
		return jsonify({"message": True}), 200
	except Exception as e:
		return f"An Error Occured: {e}"

@app.route('/getChallenges/<username>', methods=['GET'])
def getChallenges(username):
	try:
		challenges = challenge_cursor.stream()
		userChallenges = {}
		for challenge in challenges:
			if challenge.to_dict()['receiver'] == username:	
				userChallenges[challenge.to_dict()['sender']] = challenge.to_dict()
			elif challenge.to_dict()['sender'] == username:
				userChallenges[challenge.to_dict()['receiver']] = challenge.to_dict()
		
		return userChallenges, 200
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
		userChallenges = []
		for challenge in challenges:
			if challenge.to_dict()['receiver'] == username or challenge.to_dict()['sender'] == username:	
				userChallenges.append(challenge)

		result = {}
		count = 0
		for friend in friends:
			friendName = friend.to_dict()['friend']
			state = "challenge"

			for challenge in userChallenges:
				receiver = challenge.to_dict()['receiver']
				sender = challenge.to_dict()['sender']
				accepted = challenge.to_dict()['accepted']
				completed = challenge.to_dict()['completed']
	
				if(friendName == sender and username == receiver and accepted == False and completed == False):
					state = "accept"
					break
					
				elif(friendName == receiver and username == sender and accepted == False and completed == False):
					state = "pending"
					break
					
				elif((username == receiver or username == sender) and (friendName == sender or friendName == receiver) and accepted == True and completed == False):
					state = "view"
					break
					
			returnObject = {
				"friend": friendName,
				"state": state
			}
			result[count] = returnObject
			count = count + 1

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
		tempKey = format['receiver'] + "-" + format['sender']
		challenge = challenge_cursor.document(tempKey).get().to_dict()
		if challenge is not None:
			challenge_cursor.document(tempKey).delete()

		format['accepted'] = False
		format['completed'] = False
		sender = player_cursor.document(format['sender']).get().to_dict()
		format['senderStartXp'] = sender['xp']
		receiver = player_cursor.document(format['receiver']).get().to_dict()
		format['receiverStartXp'] = receiver['xp']
		format['senderEndXp'] = -1
		format['receiverEndXp'] = -1
		format['start'] = firestore.SERVER_TIMESTAMP

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
		if challenge is None:
			key = receiver + "-" + sender
			challenge = challenge_cursor.document(key).get().to_dict()

		send = player_cursor.document(challenge['sender']).get().to_dict()
		rec = player_cursor.document(challenge['receiver']).get().to_dict()

		#calculate the current gains in xp since challenge began
		challenge['senderGains'] = send['xp'] - challenge['senderStartXp']
		challenge['receiverGains'] = rec['xp'] - challenge['receiverStartXp']

		return challenge, 200
	except Exception as e:
		return f"An Error Occured: {e}"

#endpoint returns a specific challenge
@app.route('/checkChallenges/<username>', methods=['GET'])
def checkChallenges(username):
	#format
	#username
	
	try:
		challenges = challenge_cursor.stream()
		for challenge in challenges:
			if challenge.to_dict()['receiver'] == username or challenge.to_dict()['sender'] == username:	
				#check times
				time = challenge.to_dict()['start']
				week = (time + datetime.timedelta(days=7)) #find the date a week from start time
				#if the current time is passed a week, update the challenge to be completed
				if(datetime.datetime.now(datetime.timezone.utc) >= week and challenge.to_dict()['completed'] == False):
					key = challenge.to_dict()['sender'] + "-" + challenge.to_dict()['receiver']
					challenge_cursor.document(key).update({"completed": True})

					#if it was an ongoing challenge (not one that was never accepted)
					if(challenge.to_dict()['accepted'] == True):
						sender = player_cursor.document(challenge.to_dict()['sender']).get().to_dict()
						receiver = player_cursor.document(challenge.to_dict()['receiver']).get().to_dict()

						#adjust coins based on who won
						senderGains = sender['xp'] - challenge.to_dict()['senderStartXp']
						receiverGains = receiver['xp'] - challenge.to_dict()['receiverStartXp']
						if senderGains > receiverGains:
							player_cursor.document(sender['username']).update({"coins": sender['coins']+100})
						elif senderGains < receiverGains:
							player_cursor.document(receiver['username']).update({"coins": receiver['coins']+100})

						challenge_cursor.document(key).update({"senderEndXp": sender['xp'], "receiverEndXp": receiver['xp']})

		return jsonify({"message": "success"}), 200
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

		#check to see if player already owns item
		items = player_cursor.document(format['username']).collection('itemsOwned').stream()
		for obj in items:
			if obj.to_dict()['name'] == format['name']:
				return jsonify({"message": "You already own that item!"}), 200


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

#route to get a list of users tasks
@app.route('/getItemsOwned/<username>', methods=['GET'])
def getItems(username):
	try:
		items = player_cursor.document(username).collection('itemsOwned').stream()
		result = {}
		for item in items:
			result[item.to_dict()['name']] = item.to_dict()

		return result, 200
	except Exception as e:
		return f"An Error Occured: {e}"

#route to get a list of users tasks
@app.route('/getItemsEquipped/<username>', methods=['GET'])
def getItemsEquipped(username):
	try:
		if username:
			player = player_cursor.document(username).get()
			player = player.to_dict()
			
			if player is not None:
				items_equipped = {		
					"chest": player.get("chest", None),
					"weapon": player.get("weapon", None),
					"boots": player.get("boots", None),
					"pants": player.get("pants", None),
					"hat": player.get("hat", None)
				}

				return jsonify(items_equipped), 200

			return "User does not exist", 200
		else:
			return "No username was passed!", 200

	except Exception as e:
		return f"An Error Occured: {e}"


port = int(os.environ.get('PORT', 8080))
if __name__ == '__main__':
    app.run(threaded=True, host='0.0.0.0', port=port)


