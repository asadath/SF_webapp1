from flask import Flask, request, render_template_string, redirect, url_for
import uuid

from db import init_db, insert_account, get_accounts, get_account, update_account, delete_account
from publisher2 import send_account, send_account_update, send_account_delete

SYSTEM_NAME = "NPC_SF2"

app = Flask(__name__)

init_db()


HTML_PAGE = """
<h2>Create Account (NPC_SF2)</h2>

<form method="post" action="/create">
First Name:<br>
<input name="first"><br>

Last Name:<br>
<input name="last"><br>

Email:<br>
<input name="email"><br>

Phone:<br>
<input name="phone"><br><br>

<button type="submit">Create</button>
</form>

<hr>

<h2>Accounts</h2>

<table border="1">
<tr>
<th>ID</th>
<th>First</th>
<th>Last</th>
<th>Email</th>
<th>Phone</th>
<th>Source</th>
<th>Created by</th>
<th>Edit</th>
<th>Delete</th>
</tr>

{% for acc in accounts %}
<tr>
<td>{{acc[0]}}</td>
<td>{{acc[1]}}</td>
<td>{{acc[2]}}</td>
<td>{{acc[3]}}</td>
<td>{{acc[4]}}</td>
<td>{{acc[5]}}</td>
<td>{{acc[6] or '—'}}</td>
<td><a href="/edit/{{acc[0]}}">Edit</a></td>
<td><a href="/delete/{{acc[0]}}" onclick="return confirm('Delete this account?');">Delete</a></td>
</tr>
{% endfor %}

</table>
"""


@app.route("/")
def home():
    accounts = get_accounts()
    return render_template_string(HTML_PAGE, accounts=accounts)


@app.route("/create", methods=["POST"])
def create():

    first = request.form["first"]
    last = request.form["last"]
    email = request.form["email"]
    phone = request.form["phone"]

    # Generate unique ID (shared across systems)
    account_id = str(uuid.uuid4())

    # Save locally (created via form → database)
    insert_account(
        account_id,
        first,
        last,
        email,
        phone,
        SYSTEM_NAME,
        created_by="database",
    )

    # Send to other system via gRPC
    send_account(
        account_id,
        first,
        last,
        email,
        phone
    )

    return redirect(url_for("home"))


EDIT_PAGE = """
<h2>Edit Account (NPC_SF2)</h2>

<form method="post" action="/update/{{acc[0]}}">
First Name:<br>
<input name="first" value="{{acc[1] or ''}}"><br>

Last Name:<br>
<input name="last" value="{{acc[2] or ''}}"><br>

Email:<br>
<input name="email" value="{{acc[3] or ''}}"><br>

Phone:<br>
<input name="phone" value="{{acc[4] or ''}}"><br><br>

<button type="submit">Save</button>
</form>

<br><a href="/">Back to list</a>
"""


@app.route("/edit/<account_id>")
def edit_form(account_id):
    acc = get_account(account_id)
    if not acc:
        return "Account not found <br><a href='/'>Back</a>", 404
    return render_template_string(EDIT_PAGE, acc=acc)


@app.route("/update/<account_id>", methods=["POST"])
def update(account_id):
    first = request.form.get("first", "")
    last = request.form.get("last", "")
    email = request.form.get("email", "")
    phone = request.form.get("phone", "")

    update_account(account_id, first, last, email, phone, source_system=SYSTEM_NAME, created_by="database")
    send_account_update(account_id, first, last, email, phone)

    return redirect(url_for("home"))


@app.route("/delete/<account_id>", methods=["GET", "POST"])
def delete(account_id):
    acc = get_account(account_id)
    if not acc:
        return "Account not found <br><a href='/'>Back</a>", 404
    # Publish DELETE so the other system (NSPS_SF1) removes it too
    send_account_delete(account_id)
    delete_account(account_id)
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(port=8002, debug=True)