"""Flask interface for seating plan with basic authentication."""
from __future__ import annotations

import binascii
import functools
import hmac
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, List

from flask import (
    Flask,
    Response,
    render_template_string,
    request,
    send_file,
)

from seat_chart_generator import create_seat_chart, load_layout, simple_shuffle
from students import STUDENTS, COMMITTEES

app = Flask(__name__)

USERNAME = "meteosimaji"
PASSWORD_HASH = (
    "pbkdf2_sha256$260000$db3dee93a32dd6352f25952bd319c783$"
    "9d365fff266b8bc7457fbdebeb660405a4a1bda504a6d84d1f3c38f924a87049"
)

def _verify_password(username: str | None, password: str | None) -> bool:
    """Validate provided credentials against stored hash without plaintext storage."""

    if username != USERNAME or password is None:
        return False

    try:
        scheme, iter_str, salt_hex, hash_hex = PASSWORD_HASH.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iter_str)
        salt = binascii.unhexlify(salt_hex)
        expected = binascii.unhexlify(hash_hex)
    except (ValueError, binascii.Error):
        return False

    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(derived, expected)


def _requires_auth(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth or not _verify_password(auth.username, auth.password):
            return Response(
                "認証が必要です", 401, {"WWW-Authenticate": 'Basic realm="Login Required"'}
            )
        return view(*args, **kwargs)

    return wrapper


class SeatingState:
    def __init__(self) -> None:
        try:
            self.layout = load_layout()
        except Exception:
            from seat_chart_generator.layout import generate_layout

            self.layout = generate_layout(10, 5)
        self.assignments = self._shuffle()

    def _shuffle(self) -> List[object]:
        return simple_shuffle(STUDENTS, self.layout)

    def shuffle(self) -> None:
        self.assignments = self._shuffle()

    def assignment_map(self) -> Dict[int, object]:
        return {student.seat_number: student for student in self.assignments}


state = SeatingState()


def _render_page(message: str | None = None) -> str:
    assigned = state.assignment_map()
    return render_template_string(
        """
        <!doctype html>
        <html lang="ja">
        <head>
            <meta charset="utf-8">
            <title>座席表ビューア</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .layout { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ccc; padding: 6px; text-align: left; font-size: 14px; }
                th { background: #f5f5f5; }
                .actions { margin: 10px 0; }
                .message { color: #006400; font-weight: bold; }
                .seat-number { font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>座席表ビューア</h1>
            {% if message %}<p class="message">{{ message }}</p>{% endif %}
            <div class="actions">
                <form method="post" action="/shuffle">
                    <button type="submit">席替えを実行</button>
                </form>
                <form method="post" action="/download">
                    <button type="submit">PDFをダウンロード</button>
                </form>
            </div>
            <div class="layout">
                {% for row in layout %}
                    <table>
                        <thead><tr><th>席番号</th><th>生徒情報</th></tr></thead>
                        <tbody>
                        {% for seat in row %}
                            {% if seat %}
                                {% set student = assignments.get(seat) %}
                                <tr>
                                    <td class="seat-number">{{ seat }}</td>
                                    <td>
                                        {% if student %}
                                            <div>出席番号: {{ student.serial }}</div>
                                            <div>ID: {{ student.student_id }}</div>
                                            <div>氏名: {{ student.name_kanji }}</div>
                                            <div>かな: {{ student.name_kana }}</div>
                                        {% else %}
                                            <em>未割り当て</em>
                                        {% endif %}
                                    </td>
                                </tr>
                            {% endif %}
                        {% endfor %}
                        </tbody>
                    </table>
                {% endfor %}
            </div>
        </body>
        </html>
        """,
        layout=state.layout,
        assignments=assigned,
        message=message,
    )


@app.route("/")
@_requires_auth
def index() -> str:
    return _render_page()


@app.route("/shuffle", methods=["POST"])
@_requires_auth
def shuffle_view() -> str:
    state.shuffle()
    return _render_page("席替えを実行しました。")


@app.route("/download", methods=["POST"])
@_requires_auth
def download_pdf():
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "seat_chart.pdf"
        create_seat_chart(
            state.assignments,
            seat_rows=state.layout,
            committees=COMMITTEES,
            title="座席表",
            output_path=str(pdf_path),
        )
        return send_file(pdf_path, as_attachment=True, download_name="seat_chart.pdf")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
