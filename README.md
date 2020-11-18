
## Add a new user in database

```bash
flask shell
```

```python
from werkzeug.security import generate_password_hash
from web.models import User, db
# create a new user with the form data. Hash the password so the plaintext version isn't saved.	
new_user = User(email=email, name=name,	
                password=generate_password_hash(password, method='sha256'))	

# add the new user to the database	
db.session.add(new_user)	
db.session.commit()
```