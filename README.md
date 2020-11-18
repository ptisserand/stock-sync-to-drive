
# vracoop xls export to drive spreadsheet

This repository contains source code to 'import' an xls file exported by [vracoop](http://vracoop.fr/) (based on [ODOO](https://www.odoo.com/)) to a google spreadsheet


A standalone script and a web version are available.

## Common configuration
/!\ TBD /!\ 

## CLI application

Just run stock_update_drive.py with your XLS file as an argument

```bash
./stock_update_drive.py ./stock.xls 
```
## Web application (flask)


### Add a new user in database for web application

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