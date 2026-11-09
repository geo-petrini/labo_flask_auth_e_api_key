from flask import Blueprint, jsonify, request, render_template

frontend_bp = Blueprint('frontend', __name__)


@frontend_bp.route("/")
def home():
    return render_template('default.html')