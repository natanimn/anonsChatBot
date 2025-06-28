# <p align='center'> AnonsChatBot </p>

<p align='center'><i>A telegram bot that let you chat anonymously with third person</i></p>

## Installation On Ubuntu VPS
### I order to run the bot on linux server, follow the following steps respectfully

* **Setup PostgreSQL**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib -y
```
__Change the password to 'admin'__
```commandline
sudo -i -u postgres
psql
```
```sql
ALTER USER postgres WITH PASSWORD 'admin';
```
__Create a database "anonChat"__
```sql
CREATE DATABASE "anonChat";
```
__Exit the database__
```commandline
\q
exit
```

* **Install Redis**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl enable redis-server
```
__Check status__
```commandline
sudo systemctl status redis-server
```
You should see something like:
```bash
Active: active(running)
```

* **Create and open a screen**
```commandline
screen -S anonchatbot
```

* **Clone the repo**
```commandline
git clone https://natanimn:<Your TOKEN HERE>@github.com/natanimn/anonsChatBot.git
```
* **Open the folder**
```commandline
cd anonsChatBot
```

* **Install required libs with pip**
```commandline
pip install -r requirements.txt
```

**Now everything is ready, but before that you need to do add required fields in order to the bot function. To do so:**

```commandline
nano config.py
```
You should see something like this:
```python
class Config:
    API_ID = 0000000
    API_HASH = ""
    TOKEN = ""
    TEST_TOKEN = ""
    DATABASE_URI = "postgresql+asyncpg://postgres:admin@localhost/anonChat"
    REPORT_CHANNEL_ID: int = -1000000000 # Channel ID of where reports are go
    DAILY_CHAT_LIMIT = 20
    ADMIN_ID: int = 00000 # Admin/Owner ID
    PREMIUM_CHANNEL_ID: int = -10000000 # Channel ID of where notification of premium subscription goes
```
Now, pass a value for these required field: `API_ID`,  `API_HASH`, `TOKEN`, `REPORT_CHANNEL_ID`, `ADMIN_ID`, `PREMIUM_CHANNEL_ID`
**CTRL + X** then **Y** then enter


**Now RUN THE BOT**
```commandline
python3 main.py
```

**You should see something like**:
```commandline
BOT STARTED
```
DONE

**Deattach your screen with**
```bash
Ctrl + A + D
```