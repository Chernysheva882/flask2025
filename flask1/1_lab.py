from flask import Flask, request, render_template_string
import random

app = Flask(__name__)

phone_numbers = sorted({f"8913{random.randint(1000000, 9999999)}" for _ in range(1000)})

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Phone Numbers</title>
</head>
<body>
    <h1>Phone Numbers</h1>

    <form action="/number/" method="get">
        <label for="number">Enter phone number:</label>
        <input type="text" id="number" name="number" required>
        <input type="submit" value="Search">
    </form>

    <div>
    {% for number in numbers %}
        <a href="/number/?number={{ number }}">{{ number }}</a>&nbsp;&nbsp;
    {% endfor %}
    </div>

</body>
</html>
"""

NUMBER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Phone Number Details</title>
</head>
<body>
    <h1>Phone Number Details</h1>

    {% if exists %}
        <p>Selected phone number: {{ number }}</p>
    {% else %}
        <p style="color:black;">This number is not exist!</p>
    {% endif %}

    <a href="/">Main page</a>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(INDEX_HTML, numbers=phone_numbers)

@app.route("/number/")
def number_info():
    num = request.args.get("number", "")
    exists = num in phone_numbers
    return render_template_string(NUMBER_HTML, number=num, exists=exists)

if __name__ == "__main__":
    app.run(debug=True)
