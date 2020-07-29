from flask import Flask, render_template, request, redirect, make_response
import MySQLdb
import datetime

app = Flask(__name__)


def config_parser():
    file = open('config.json', 'r')
    data = file.read()
    file.close()
    config = eval(data)
    return config


def connection():
    conn = MySQLdb.connect(
        host=config_parser()["mysql"]["host"],
        user=config_parser()["mysql"]["user"],
        passwd=config_parser()["mysql"]["password"],
        db=config_parser()["mysql"]["db"]
    )
    c = conn.cursor()

    return c, conn


def write_query(query):
    c, conn = connection()
    conn.query(query)
    conn.commit()
    c.close()


def read_query(query):
    c, conn = connection()
    c.execute(query)
    data = c.fetchall()
    c.close()
    return data


@app.route("/")
def main():
    return render_template('login.html')


@app.route("/auth", methods=['POST'])
def auth():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        submit_type = request.form.get('submit')

        get_user = read_query("SELECT * FROM colabedit.users WHERE username='{}' and password='{}'".format(username, password))

        if len(get_user) == 0 and submit_type == "login":
            data = {
                "message": "Wrong username/password combination. Try signing up."
            }
            return render_template('Error.html', data=data)

        elif len(get_user) == 0 and submit_type == "signup":
            try:
                write_query("INSERT INTO colabedit.users VALUES('{}', '{}')".format(username, password))
                resp = make_response(redirect("/colabeditor"))
                resp.set_cookie('colabUser', username)
                return resp
            except Exception as error:
                data = {
                    "message": "Error while signing up [{}]".format(error)
                }
                return render_template('Error.html', data=data)

        elif len(get_user) > 0 and submit_type == "login":
            resp = make_response(redirect("/colabeditor"))
            resp.set_cookie('colabUser', username)
            return resp

        elif len(get_user) > 0 and submit_type == "signup":
            data = {
                "message": "User already signed up. Try logging in"
            }
            return render_template('Error.html', data=data)

    else:
        return 405


@app.route("/colabeditor")
def homepage():
    username = request.cookies.get('colabUser')
    docs = read_query("SELECT * FROM colabedit.document WHERE owner='{}'".format(username))
    shared_docs = read_query("SELECT document_id FROM colabedit.document_colabs WHERE username='{}'".format(username))

    data = {
        "posts": [],
        "shared": []
    }
    for doc in docs:
        tmp = data["posts"]

        history = read_query("SELECT * FROM colabedit.document_history WHERE document_id={}".format(doc[0]))
        history_data = []
        for hist in history:
            timestamp = "{}/{}/{} {}:{}:{}".format(hist[3].day, hist[3].month, hist[3].year, hist[3].hour,
                                                   hist[3].minute, hist[3].second)
            history_data.append([hist[2], timestamp])

        tmp.append(
            {
                "id": doc[0],
                "title": doc[1],
                "content": doc[2],
                "author": doc[3],
                "history": history_data
            }
        )
        data["posts"] = tmp

    for id in shared_docs:
        docs = read_query("SELECT * FROM colabedit.document WHERE id={}".format(id[0]))
        for doc in docs:
            tmp = data["shared"]

            history = read_query("SELECT * FROM colabedit.document_history WHERE document_id={}".format(doc[0]))
            history_data = []
            for hist in history:
                timestamp = "{}/{}/{} {}:{}:{}".format(hist[3].day, hist[3].month, hist[3].year, hist[3].hour,
                                                       hist[3].minute, hist[3].second)
                history_data.append([hist[2], timestamp])

            tmp.append(
                {
                    "id": doc[0],
                    "title": doc[1],
                    "content": doc[2],
                    "author": doc[3],
                    "history": history_data
                }
            )
            data["shared"] = tmp

    return render_template('main.html', data=data)


@app.route("/logout")
def logout():
    return render_template('main.html')


@app.route("/savedoc", methods=['POST'])
def save_post():
    if request.method == "POST":
        title = request.form.get("title")
        author = request.form.get("author")
        data = request.form.get("content")

        write_query("INSERT INTO colabedit.document(title, content, owner) VALUES('{}', '{}', '{}')".format(title, data, author))

        resp = make_response(redirect("/colabeditor"))
        return resp


@app.route("/updatedoc", methods=['POST'])
def update_post():
    if request.method == "POST":
        id = eval(request.form.get("id"))
        title = request.form.get("title")
        author = request.form.get("author")
        data = request.form.get("content")
        shared = request.form.get("share")
        editor = request.form.get("editor")

        write_query("UPDATE colabedit.document SET title='{}', content='{}' WHERE id='{}' and owner='{}'".format(title, data, id, author))
        write_query("INSERT INTO colabedit.document_history(document_id, username) VALUES('{}', '{}')".format(id, editor))

        check_shared = read_query("SELECT * FROM colabedit.document_colabs WHERE document_id={} and username='{}'".format(id, shared))
        if len(check_shared) == 0:
            write_query("INSERT INTO colabedit.document_colabs(document_id, username) VALUES({}, '{}')".format(id, shared))

        resp = make_response(redirect("/colabeditor"))
        return resp


if __name__ == "__main__":
    print("Initiating database ...")
    try:
        write_query(
            "CREATE TABLE colabedit.users(username VARCHAR(64) NOT NULL PRIMARY KEY, password VARCHAR(64) NOT NULL)"
        )
    except Exception as error:
        print(error)

    try:
        write_query(
            "CREATE TABLE colabedit.document(id int AUTO_INCREMENT PRIMARY KEY, title VARCHAR(64) NOT NULL, content VARCHAR(10000) NOT NULL, owner VARCHAR(64) NOT NULL)"
        )
    except Exception as error:
        print(error)

    try:
        write_query(
            "CREATE TABLE colabedit.document_colabs(id int AUTO_INCREMENT PRIMARY KEY, document_id int NOT NULL, username VARCHAR(64) NOT NULL)"
        )
    except Exception as error:
        print(error)

    try:
        write_query(
            "CREATE TABLE colabedit.document_history(id int AUTO_INCREMENT PRIMARY KEY, document_id int NOT NULL, username VARCHAR(64) NOT NULL, timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
    except Exception as error:
        print(error)

    app.run(host='0.0.0.0', debug=True)
