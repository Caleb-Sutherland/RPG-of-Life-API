from os import close
from flask import Flask, g
import sqlite3
import json



app = Flask(__name__)

DATABASE = 'database.db'

#returns a connection to the existing database
def get_db():
	return sqlite3.connect(DATABASE)

#creates the database (does not edit if the tables already exist)
def create_db():
	db = getattr(g, '_database', None)
	if db is None:
		db = g._database = sqlite3.connect(DATABASE)

		cursor = db.cursor()

		player = "CREATE TABLE IF NOT EXISTS player (username TEXT NOT NULL, email TEXT NOT NULL, password TEXT NOT NULL, xp INTEGER NOT NULL, coins INTEGER NOT NULL, health INTEGER NOT NULL, strength INTEGER NOT NULL, intelligence INTEGER NOT NULL, creativity INTEGER NOT NULL, charisma INTEGER NOT NULL, hat TEXT, armor TEXT, weapon TEXT, FOREIGN KEY(hat) REFERENCES itemsOwned(itemName), FOREIGN KEY(armor) REFERENCES itemsOwned(itemName), FOREIGN KEY(weapon) REFERENCES itemsOwned(itemName), PRIMARY KEY(username));"

		itemsOwned = "CREATE TABLE IF NOT EXISTS itemsOwned (username TEXT NOT NULL, itemName TEXT NOT NULL, type TEXT NOT NULL, url TEXT NOT NULL, FOREIGN KEY(username) REFERENCES player(username), PRIMARY KEY(username, itemName));"

		friend = "CREATE TABLE IF NOT EXISTS friend (username1 TEXT NOT NULL, username2 TEXT NOT NULL, FOREIGN KEY(username1) REFERENCES player(username), FOREIGN KEY(username2) REFERENCES player(username), PRIMARY KEY(username1, username2));"

		task = "CREATE TABLE IF NOT EXISTS task (id INTEGER NOT NULL, username TEXT NOT NULL, taskName TEXT NOT NULL, statType TEXT NOT NULL, statVal INTEGER NOT NULL, completionTime TEXT, FOREIGN KEY(username) REFERENCES player(username), PRIMARY KEY(id));"

		challenge = "CREATE TABLE IF NOT EXISTS challenge(sender TEXT NOT NULL, receiver TEXT NOT NULL, accepted INTEGER NOT NULL, startTime TEXT NOT NULL, senderXPStart INTEGER NOT NULL, receiverXPStart INTEGER NOT NULL, senderXPEnd INTEGER NOT NULL, receiverXPEnd INTEGER NOT NULL, FOREIGN KEY(sender) REFERENCES player(username), FOREIGN KEY(receiver) REFERENCES player(username), PRIMARY KEY(sender, receiver));"

		shop = "CREATE TABLE IF NOT EXISTS shop(name TEXT NOT NULL, url TEXT NOT NULL, price INTEGER NOT NULL, type TEXT NOT NULL, PRIMARY KEY(name));"

		cursor.execute(itemsOwned)
		cursor.execute(player)
		cursor.execute(friend)
		cursor.execute(task)
		cursor.execute(challenge)
		cursor.execute(shop)
		db.commit()

		#YYYY-MM-DD HH:MM:SS.SSS is the timestamp format in TEXT for sqlite
		cursor.close()
		print("\nsuccessfully created your database!\n")
	return db

#closes database connection when server goes down
@app.teardown_appcontext
def close_connection(exception):
	db = getattr(g, '_database', None)
	if db is not None:
		db.close()

#route to create the database
@app.route("/create", methods=["GET"])
def initDB():
	cursor = create_db()
	return "DB CREATED"

#test route to manipulate db
@app.route("/get", methods=["GET"])
def lame():
	cursor = get_db().cursor()
	cursor.execute("INSERT INTO shop VALUES('test', 'test', '1', 'test');")
	get_db().commit()
	result = cursor.execute("SELECT * FROM shop;").fetchall() #retreive all rows found (should justbe one)
	jsonVal = json.dumps(result) #convert tuples to json to return
	return jsonVal

if __name__ == "__main__":
	app.run(debug = True)