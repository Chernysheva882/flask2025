from flask import Flask, request, render_template
import random

app = Flask(__name__)

phone_numbers = sorted({f"8913{random.randint(1000000, 9999999)}" for _ in range(1000)})


@app.route("/")
def index():
    return render_template("index.html", numbers=phone_numbers)


@app.route("/phone/")
def number_info():
    num = request.args.get("number", "")
    return render_template("number.html", number=num)


if __name__ == "__main__":
    app.run(debug=True)
