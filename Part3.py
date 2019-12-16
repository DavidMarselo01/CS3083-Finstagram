from flask import Flask, render_template, request, session, redirect, url_for, send_file
import os
import uuid
import hashlib
import pymysql.cursors
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = "super secret key"
IMAGES_DIR = os.path.join(os.getcwd(), "images")

connection = pymysql.connect(host="localhost",
                             user="root",
                             password="Marselo01",
                             db="Finstagram",
                             charset="utf8mb4",
                             port=3306,
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

#FIRST PAGE OF THE APP, LOGIN OR REGISTER
@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")

#LOGGING IN

#This function is here to make sure that when a person is using our app, the user is always logged in
#So, we are checking if the session is ative and not just in the cookies
def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return dec

#1. We click on the Register link in the index.html which will follow the route of /register, which will render register.html

@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")

#2. In register.html we fill out the form and the action is taken by the registerAuth()function
    #In the function we check if the user already exists and if not put the new user in the database

@app.route("/registerAuth", methods=["POST"])
def registerAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()
        firstName = requestData["firstName"]
        lastName = requestData["lastName"]
        
        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO Person (username, password, firstName, lastName) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (username, hashedPassword, firstName, lastName))
        except pymysql.err.IntegrityError:
            error = "%s is already taken." % (username)
            return render_template('register.html', error=error)    

        return redirect(url_for("login"))

    error = "An error has occurred. Please try again."
    return render_template("register.html", error=error)

#3. Index.html - click on login
    
@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")

#4. In the login.html there is a form, the action is the loginAuth() fucntion
    #Check if the user is in the database and log in or not
    
@app.route("/loginAuth", methods=["POST"])
def loginAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()

        with connection.cursor() as cursor:
            queryLogin = "SELECT * FROM person WHERE username = %s AND password = %s"
            cursor.execute(queryLogin, (username, hashedPassword))
            
        data = cursor.fetchone()
        cursor.close()
        error = None
        if data:
            session["username"] = username
            #with connection.cursor() as cursor:
                #queryName = "SELECT firstName, lastName FROM person  WHERE username = %s AND password = $s"
                #cursor.execute(queryName, (username, hashedPassword))
            #dataName = cursor.fetchone()
            #session["nameOfPerson"] = str(dataName)
            #cursor.close()
            return redirect(url_for("home"))

        error = "Incorrect username or password."
        return render_template("login.html", error=error)

#5. Log out

@app.route("/logout", methods=["GET"])
def logout():
    session.pop("username")
    return redirect("/")

#HOME PAGE WHERE THE USER DOES ALL OF THE ACTIONS

@app.route('/home')
@login_required
def home():
    return render_template('home.html', username = session['username'])
    
    
#EVERYTHING TO DO WITH IMAGES (UPLOAD AND SEE YOU IMAGES OR IMAGES OF YOUR FRIENDS)

#1. Render the upload.html, in which we have a form with an action to go the 
    #/uploadImage path with method post
    
def getUsersGroupsToShare():
    queryForGroups = "SELECT groupName, owner_username FROM BelongTo WHERE owner_username = %s OR member_username = %s"
    with connection.cursor() as cursor:
        cursor.execute(queryForGroups, (session['username'], session['username']))
    dataForPrintingGroups = cursor.fetchall()
    cursor.close()
    return dataForPrintingGroups
@app.route("/upload", methods=["GET"])
@login_required
def upload():
    dataForPrintingGroups = getUsersGroupsToShare()
    return render_template("upload.html", dataForPrintingGroups = dataForPrintingGroups)

#We upload the image (its filepath, poster etc.) to the database
@app.route("/uploadImage", methods=["POST"])
@login_required
def upload_image():
    if request.files and request.form:
        #Code to insert the photo into Photo table in the database, witht the correct file path etc
        requestData = request.form
        caption = requestData['caption']
        image_file = request.files.get("imageToUpload", "")
        image_name = image_file.filename
        filepath = os.path.join(IMAGES_DIR, image_name)
        image_file.save(filepath)
        queryPhoto = "INSERT INTO Photo (postingdate, filepath, photoPoster, allFollowers, caption) VALUES (%s, %s, %s, %s, %s)"
        try:
            allFollowers = requestData['allFollowersCheckBox']
            with connection.cursor() as cursor:
                cursor.execute(queryPhoto, (time.strftime('%Y-%m-%d %H:%M:%S'), image_name, session['username'], 1, caption))
                photoId = cursor.lastrowid
        except:
            with connection.cursor() as cursor:
                cursor.execute(queryPhoto, (time.strftime('%Y-%m-%d %H:%M:%S'), image_name, session['username'], 0, caption))
                photoId = cursor.lastrowid
        cursor.close()
        
        #Code to insert the data in SharedWith table in our database
        queryShared = "INSERT INTO SharedWith (groupOwner, groupName, photoID) VALUES (%s, %s, %s)"
        for group in requestData:
            if group == 'allFollowersCheckBox' or group == 'caption':
                continue
            else:
                listGroupNamaOwner = group.split('+')
                groupName = listGroupNamaOwner[0]
                owner = listGroupNamaOwner[1]
                with connection.cursor() as cursor:
                    cursor.execute(queryShared, (owner, groupName, photoId))
                cursor.close()
        
        message = "Image has been successfully uploaded. Upload another image!"
        dataForPrintingGroups = getUsersGroupsToShare()
        return render_template("upload.html", message=message, dataForPrintingGroups = dataForPrintingGroups,requestData=requestData, photoId = photoId, caption = caption)
    else:
        message = "Failed to upload image."
        return render_template("upload.html", message=message)
    
#From the home page, when I click on View My Images, the path of this link is to go to this route
#Here, I get the filepath, username and the name of the user that was all stored in the database and the session
#In here we render the page images.html
@app.route("/MyImages", methods=["GET"])
@login_required
def MyImages():
    query = "SELECT * FROM photo WHERE photoPoster = %s"
    with connection.cursor() as cursor:
        cursor.execute(query, (session['username']))
    data = cursor.fetchall()
    cursor.close()
    
    with connection.cursor() as cursor:
        queryName = "SELECT firstName, lastName FROM person WHERE username = %s"
        cursor.execute(queryName, (session['username']))
    name = cursor.fetchone()
    return render_template("images.html", images=data, name = name['firstName'] + " " + name['lastName'])

#This allows us to send the file
@app.route("/images/<image_name>", methods=["GET"])
def image(image_name):
    image_location = os.path.join(IMAGES_DIR, image_name)
    if os.path.isfile(image_location):
        return send_file(image_location, mimetype="image/jpg")


@app.route("/sharedPhotos", methods=["GET"])
@login_required
def SharedImages():
    allImagesQuery = "SELECT username, photoID, filepath, postingdate, firstName, lastName" \
                " FROM Finstagram.Follow JOIN Finstagram.Photo ON username_follower = photoPoster" \
                " JOIN Finstagram.Person ON photoPoster = username" \
                " WHERE username_followed = %s AND followstatus = 1 AND allFollowers = 1" \
                " UNION SELECT username, photoID, filepath, postingdate, firstName, lastName" \
                " FROM Finstagram.BelongTo JOIN Finstagram.SharedWith" \
                " ON BelongTo.groupName = SharedWith.groupName  NATURAL JOIN Finstagram.Photo" \
                " JOIN Finstagram.Person ON photoPoster = username" \
                " WHERE member_username = %s ORDER BY postingdate DESC"
                
    with connection.cursor() as cursor:
        cursor.execute(allImagesQuery, (session['username'],session['username'] ))
    data = cursor.fetchall()    
    cursor.close()

    return render_template("sharedPhotos.html", data = data)

@app.route("/tagsAndLikes", methods=["POST"])
@login_required
def tagsAndLikes():
    if request.form:
        data = request.form
        photoID = data['photoID']
        #Who have been tagged given that they have accepted it
        queryTag = "SELECT username, firstName, lastName FROM Tagged  NATURAL JOIN PERSON WHERE photoID = %s and tagstatus = 1"
        with connection.cursor() as cursor:
            cursor.execute(queryTag, (photoID))
        dataTag = cursor.fetchall()    
        cursor.close()
        #Who Liked the photo
        queryLike = "SELECT username, rating FROM Likes WHERE photoID = %s"
        with connection.cursor() as cursor:
            cursor.execute(queryLike, (photoID))
        dataLike = cursor.fetchall()    
        cursor.close()
        return render_template('tagsAndLikes.html', dataTag = dataTag, dataLike = dataLike)

#EVERYTHING TO DO WITH FOLLOWING OTHER PEOPLE

def allPeopleWhoTheUserFollows():
    #Select all the people who the user follows and show their followstatus
    query = "SELECT username_followed, followstatus FROM Follow where username_follower = %s"
    with connection.cursor() as cursor:
        cursor.execute(query, (session['username']))
    cursor.close()
    dataForFollowing = cursor.fetchall()
    return dataForFollowing

def peopleWhoFollowTheUserAndTheUserDoesntFollowBack():
    #Select all the people who follow the user and the user doesn't follow them back
    query = "SELECT username_followed, username_follower FROM Follow where username_followed = %s and followstatus = 0"
    with connection.cursor() as cursor:
        cursor.execute(query, (session['username']))
    cursor.close()
    dataForFollowed = cursor.fetchall()
    return dataForFollowed

def insertIntoFollow(followed, follower, followstatus):
    query = "INSERT INTO Follow (username_followed, username_follower, followstatus) VALUES (%s, %s, %s)"
    with connection.cursor() as cursor:
        cursor.execute(query, (followed, follower, followstatus))
    cursor.close()
    
def updateFollowStatus(followed, follower, followstatus):
    query = "UPDATE Follow SET followstatus = %s WHERE username_follower = %s and username_followed = %s;"
    with connection.cursor() as cursor:
        cursor.execute(query, (followstatus, followed, follower))
    cursor.close()
            
        
@app.route("/followBloggers", methods=["GET"])
@login_required
def followBloggers():
    return render_template('followBloggers.html')

@app.route('/follow', methods=["POST"])
def follow():
    if request.form:
        whoYouWantToFollow = request.form
        usernameFollowed = whoYouWantToFollow["username"]
        usernameFollower = session['username']
        
        #Check if you already follow this person
        query = "SELECT username_followed, followstatus FROM Follow where username_follower = %s and username_followed = %s"
        with connection.cursor() as cursor:
            cursor.execute(query, (session['username'], usernameFollowed))
        dataForFollowing = cursor.fetchone()
        cursor.close()
        if dataForFollowing:
            messageSuccess = "You already follow this person"
        else:
            #Check if the person who the user selected already follows this person
            query = "SELECT username_follower FROM Follow where username_follower = %s and username_followed = %s"
            with connection.cursor() as cursor:
                cursor.execute(query, (usernameFollowed, session['username']))
            dataToChangeFollowStatus = cursor.fetchone()
            
            #If the person follows the user, then insert a row into the database with followstatus = 1 and change the followstatus of the person(not the user)
            if dataToChangeFollowStatus:
            
                query = "INSERT INTO Follow (username_followed, username_follower, followstatus) VALUES (%s, %s, %s)"
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(query, (usernameFollowed, usernameFollower, 1))
                except:
                    messageFailure = "There is no such user in Finstagram, please enter a correct username"
                    return render_template('followBloggers.html', messageFailure = messageFailure)
                messageSuccess = "Your request is sent to " + usernameFollowed
                cursor.close()
                
                query = "UPDATE Follow SET followstatus = 1 WHERE username_follower = %s and username_followed = %s;"
                with connection.cursor() as cursor:
                    cursor.execute(query, (usernameFollowed, session['username']))
                cursor.close()
                
            #If the person doesn't follow the user, then just insert a row with followstatus = 0
            else:
                query = "INSERT INTO Follow (username_followed, username_follower, followstatus) VALUES (%s, %s, %s)"
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(query, (usernameFollowed, usernameFollower, 0))
                except:
                    messageFailure = "There is no such user in Finstagram, please enter a correct username"
                    return render_template('followBloggers.html', messageFailure = messageFailure)
                messageSuccess = "Your request is sent to " + usernameFollowed
                cursor.close()
            
            
        return render_template('followBloggers.html', messageSuccess = messageSuccess)
    
@app.route('/followBack', methods=["POST"])
def followBack():
    if request.form:
        #Update follow status when user clicks follow back
        data = request.form        
        updateFollowStatus(data['username_follower'], session['username'], 1)
        
        
        usernameFollowed = data['username_follower']
        usernameFollower = session['username']
        try:
            insertIntoFollow(usernameFollowed, usernameFollower, 1)
        except:
            dataForFollowing = allPeopleWhoTheUserFollows()
            dataForFollowed = peopleWhoFollowTheUserAndTheUserDoesntFollowBack()
            return render_template('followersFolowees.html', dataForFollowing = dataForFollowing, dataForFollowed = dataForFollowed)
        
        dataForFollowing = allPeopleWhoTheUserFollows()
        
        dataForFollowed = peopleWhoFollowTheUserAndTheUserDoesntFollowBack()

        return render_template('followersFolowees.html', dataForFollowing = dataForFollowing, dataForFollowed = dataForFollowed)
    
@app.route('/deleteFollowRequest', methods=["POST"])
def deleteFollowRequest():
    if request.form:
        data = request.form
        username_followed = session['username']
        username_follower = data['username_follower']
        
        queryToDelete = "DELETE FROM Follow WHERE username_followed = %s and username_follower = %s"
        with connection.cursor() as cursor:
            cursor.execute(queryToDelete, (username_followed, username_follower))
        cursor.close()
        
        return redirect(url_for('followersFolowees'))
        
        
         
@app.route("/followersFolowees", methods=["GET"])
@login_required
def followersFolowees():
    dataForFollowing = allPeopleWhoTheUserFollows()
    dataForFollowed = peopleWhoFollowTheUserAndTheUserDoesntFollowBack()
    
    return render_template('followersFolowees.html', dataForFollowing = dataForFollowing, dataForFollowed = dataForFollowed)



#CREATING GROUPS
def queryToCreateFriendGroup(groupOwner, groupName, description):
    #Check if there is a friend group with the same name already for the same user
    query = 'SELECT groupOwner, groupName FROM Friendgroup WHERE groupOwner = %s and groupName = %s'
    with connection.cursor() as cursor:
        cursor.execute(query, (groupOwner, groupName))
    dataCheck = cursor.fetchone()
    cursor.close()
    if dataCheck:
        #If there is a duplicate, return to the creategroup page
        return 'Duplicate'
    else:   
        #Insert everything in Frinedgroup table in our database
        queryFriend = "INSERT INTO Friendgroup (groupOwner, groupName, description) VALUES (%s, %s, %s)"
        with connection.cursor() as cursor:
            cursor.execute(queryFriend, (groupOwner, groupName, description))
        cursor.close()
        #Addding owner of the group to the group as a memeber as wells
        queryOwner = "INSERT INTO BelongTo (member_username, owner_username, groupName) VALUES (%s, %s, %s)"
        with connection.cursor() as cursor:
            cursor.execute(queryOwner, (groupOwner, groupOwner, groupName))
        cursor.close()
        
@app.route("/createGroup", methods=["GET"])
@login_required
def createGroup():
    return render_template('createGroups.html')

@app.route("/createGroupsAction", methods=["POST"])
@login_required
def createGroupsAction():
    if request.form:
        allData = request.form
        groupName = allData['groupName']
        groupDescription = allData['groupDescription']
        
        duplicate = queryToCreateFriendGroup(session['username'], groupName, groupDescription)
        if (duplicate == 'Duplicate'):
            messageDuplicate = 'You already have a friend group that is called ' + groupName + ', so change the name'
            return render_template('createGroups.html', messageDuplicate = messageDuplicate)
        
    messageSuccess = "You have created " + groupName
    return render_template('createGroups.html', messageSuccess = messageSuccess)

@app.route("/addPeopleToGroup", methods=["GET"])
@login_required
def addPeopleToGroup():
    return render_template("addPeopleToGroup.html")

@app.route("/addPersonIntoGroup", methods=["GET", "POST"])
@login_required
def addPersonIntoGroup():
    if request.form:
        data = request.form
        groupName = data['groupName']
        groupMemberToBe = data['username']
        queryCheckGroupExists = "SELECT groupName FROM Friendgroup where groupName = %s"
        with connection.cursor() as cursor:
            cursor.execute(queryCheckGroupExists, (groupName))
        resultCheckGroupExists = cursor.fetchone()
        cursor.close()
        if resultCheckGroupExists:
            #Check that groupMember ToBe exists
            queryCheckMemberToBeExists = "SELECT username FROM Person where username = %s"
            with connection.cursor() as cursor:
                cursor.execute(queryCheckMemberToBeExists, (groupMemberToBe))
            resultCheckMemberExists = cursor.fetchone()
            cursor.close()
            
            if resultCheckMemberExists:
                #Check if this user is in the group
                queryCheckInGroup = "SELECT member_username, owner_username FROM BelongTo WHERE member_username = %s and groupName = %s"
                with connection.cursor() as cursor:
                    cursor.execute(queryCheckInGroup, (session['username'], groupName))
                result = cursor.fetchone()
                cursor.close()
                
                if result:
                    queryCheckNotAddingDuplicate = "SELECT member_username FROM BelongTo WHERE member_username = %s"
                    with connection.cursor() as cursor:
                        cursor.execute(queryCheckNotAddingDuplicate, (groupMemberToBe))
                    resulDuplicate = cursor.fetchone()
                    cursor.close()
                    if resulDuplicate:
                        message = groupMemberToBe + " is already in " + groupName
                        return render_template("addPeopleToGroup.html", message = message)
                    else:
                        ownerOfGroup = result['owner_username']
                        message = groupMemberToBe + " was successfully added to " + groupName
                        query = "INSERT INTO BelongTo (member_username, owner_username, groupName) VALUES (%s, %s, %s)"
                        with connection.cursor() as cursor:
                            cursor.execute(query, (groupMemberToBe, ownerOfGroup, groupName))
                        cursor.close()
                        return render_template("addPeopleToGroup.html", message = message)
                else:
                    message = "You do not belong to " + groupName + " please enter a group name in which you belong"
                    return render_template("addPeopleToGroup.html", message = message)
            else:
                message = groupMemberToBe + " user does not exist, please enter a valid username"
                return render_template("addPeopleToGroup.html", message = message)
        else:
            message = groupName + " group does not exists, please enter a valid group name"
            return render_template("addPeopleToGroup.html", message = message)


if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run('127.0.0.1', 5000, debug = True)