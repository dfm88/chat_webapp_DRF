# chat_webapp_DRF

## Django App:
* Authentication (for user management)
* Chat (for messages and chatrooms management)

# INTRO
Preliminary assumptions:

the environment was treated as a "test" environment whereby the data is volatile.
When starting the application with the `docker-compose up` command, 15 dummy users are created. 
The volumes of the containers will be reset when they are restarted.

The service is completely REST, so it is not a live chat. 
There is a dedicated endpoint to get all the latest unread messages, which could be used for a long polling system.

The user list is cached by Redis. The cached data is reset following modification operations on any user.
No cache is, at th moment, implemente for messaes and chatrooms.

The sending of messages is relegated to a celery worker which returns the job id, which can be queried by another dedicated endpoint.
Even the business logic that sets the messages as "seen" is done asynchronously but it's transparent to the user.

No authentication is requested, request user will be always provided by the query string param `?user_id=${user_id}`

## Links to diagrams
[USE CASE diagram](https://github.com/dfm88/chat_webapp_DRF/blob/master/chat_USE_CASE_diagram.pdf)

[ER diagram](https://github.com/dfm88/chat_webapp_DRF/blob/master/chat_ER_diagram.pdf)

[DB ER diagram](https://github.com/dfm88/chat_webapp_DRF/blob/master/chat_DB_ER_diagram.png)

### USER LIST
GET `http://localhost:8000/users/`

`curl --location --request GET 'http://localhost:8000/users/'`

### USER CREATE
POST `http://localhost:8000/users/`
```json
{
    "profile": {
        "status": "Online",
        "status_msg": 5
    },
    "username": "My_firt_chat_user",
    "password":"Password!",
    "first_name": "",
    "last_name": "",
    "email": ""
}
```

```
curl --location --request POST 'http://localhost:8000/users/' \
--header 'Content-Type: application/json' \
--data-raw '{
    "profile": {
        "status": "Online",
        "status_msg": 5
    },
    "username": "My_firt_chat_user",
    "password":"Password!",
    "first_name": "",
    "last_name": "",
    "email": ""
}'
```

### CHATROOM LIST
GET `http://localhost:8000/chat/chatroom/?user_id=10`

`curl --location --request GET 'http://localhost:8000/chat/chatroom/'`

If authentication is not provided, the list will show up only the chartooms_name 

### CHATROOM CREATE
POST `http://localhost:8000/chat/chatroom/`
```json
    {
        "room_member": [
            {
                "username": "user_7"
            },
            {
                "username": "user_8"
            },
            {
                "username": "user_9"
            }
        ],
        "room_name": "family"
    }
```

Example creating a chatroom named 'family' with 3 users
```
curl --location --request POST 'http://localhost:8000/chat/chatroom/' \
--header 'Content-Type: application/json' \
--data-raw '    {
        "room_member": [
            {
                "username": "user_7"
            },
            {
                "username": "user_8"
            },
            {
                "username": "user_9"
            }
        ],
        "room_name": "family"
    }'
```

room_member are optional

### JOIN GROUP CHATROOM
PUT `http://localhost:8000/chat/chatroom/:chatroom_id/?user_id=12`

`curl --location --request PUT 'http://localhost:8000/chat/chatroom/1/?user_id=9'`

### LEAVE CHATROOM
DELETE `http://localhost:8000/chat/chatroom/:chatroom_id/?user_id=7`

`curl --location --request DELETE 'http://localhost:8000/chat/chatroom/1/?user_id=7'`

### GET DIRECT CHATROOM
GET `http://localhost:8000/chat/chatroom/:id/?user_id=7`
-- optional user id

`curl --location --request GET 'http://localhost:8000/chat/chatroom/1/?user_id=7'`

_____________________________

### SEND DIRECT MESSAGE
POST `http://localhost:8000/chat/user/1/`
```json
{
    "from": 2,
    "text": "hey man"
}
```

```
curl --location --request POST 'http://localhost:8000/chat/user/1/' \
--header 'Content-Type: application/json' \
--data-raw '{
    "from": 2,
    "text": "hey man"
}
'
```

### SEND GROUP MESSAGE
POST `http://localhost:8000/chat/group/1/`
```json
{
    "from": 9,
    "text": "hi fam"
}
```
```
curl --location --request POST 'http://localhost:8000/chat/group/1/' \
--header 'Content-Type: application/json' \
--data-raw '{
    "from": 7,
    "text": "hi fam"
}
'
```

### MESSAGES LIST BY CHATROOM ID
GET `http://localhost:8000/chat/messages/:chatroom_id/?user_id=8`

If authentication is not provided, the list will show up only the chartooms_name 

`curl --location --request GET 'http://localhost:8000/chat/messages/1/?user_id=8'`

### ONLY MINE UNREAD MESSAGES
GET `http://localhost:8000/chat/messages/unseen/?user_id=8`

`curl --location --request GET 'http://localhost:8000/chat/messages/unseen/?user_id=8'`

_______________________________

### GET SENT MESSAGE TASK STATUS
`http://localhost:8000/chat/task_state/:task_id`

`curl --location --request GET 'http://localhost:8000/chat/task_state/a487117c-d31b-45b0-ae3c-28126b0f3ec2'`


