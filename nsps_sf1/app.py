from flask import Flask, request, render_template_string
import uuid

from db import init_db, insert_account, get_accounts
from grpc_client import send_account

SYSTEM_NAME = "NSPS_SF1"

app = Flask(__name__)

init_db()


HTML_PAGE = """
<h2>Create Account (NSPS_SF1)</h2>

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
</tr>

{% for acc in accounts %}
<tr>
<td>{{acc[0]}}</td>
<td>{{acc[1]}}</td>
<td>{{acc[2]}}</td>
<td>{{acc[3]}}</td>
<td>{{acc[4]}}</td>
<td>{{acc[5]}}</td>
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

    # Save locally
    insert_account(
        account_id,
        first,
        last,
        email,
        phone,
        SYSTEM_NAME
    )

    # Send to other system via gRPC
    send_account(
        account_id,
        first,
        last,
        email,
        phone
    )

    return "Account Created <br><a href='/'>Back</a>"


if __name__ == "__main__":
    app.run(port=8020, debug=True)