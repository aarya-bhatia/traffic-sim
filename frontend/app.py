import flask

app = flask.Flask(__name__)

@app.get("/")
def GET_index():
    return flask.render_template("index.html")


if __name__=="__main__":
    app.run(host="127.0.0.1", port=3000, debug=True)
