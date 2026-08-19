import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.database import init_db

init_db()

from login import LoginWindow

app = LoginWindow()
app.mainloop()
# مبضون اوي 