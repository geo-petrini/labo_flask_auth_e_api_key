from functools import wraps

from flask import Blueprint, g, jsonify, request, url_for

from models.conn import db
from models.model import ApiKey, Series
from worker import enqueue_series, validate_series_input


api_bp = Blueprint('api', __name__, url_prefix='/api')


def _parse_int(value):
    """Converte value in int rifiutando booleani e decimali non interi."""
    if isinstance(value, bool):
        raise ValueError
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise ValueError


def api_key_required(view):
    """Richiede l'header Authorization: Bearer <chiave API>."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get('Authorization', '')
        parts = header.split(None, 1)
        if len(parts) != 2 or parts[0].lower() != 'bearer' or not parts[1].strip():
            return jsonify({'error': 'Chiave API mancante.'}), 401

        api_key = ApiKey.query.filter_by(key=parts[1].strip()).first()
        if api_key is None or api_key.user is None:
            return jsonify({'error': 'Chiave API non valida.'}), 401

        g.api_key = api_key
        g.api_user = api_key.user
        return view(*args, **kwargs)

    return wrapped


@api_bp.route('/series', methods=['GET'])
@api_key_required
def list_series():
    """Restituisce le serie dell'utente associato alla chiave API."""
    series_list = (
        Series.query
        .filter_by(user_id=g.api_user.id)
        .order_by(Series.created_at.desc(), Series.id.desc())
        .all()
    )
    return jsonify({'series': [series.to_dict() for series in series_list]})


@api_bp.route('/series/<int:series_id>', methods=['GET'])
@api_key_required
def get_series(series_id):
    """Restituisce una serie dell'utente associato alla chiave API."""
    series = Series.query.filter_by(
        id=series_id, user_id=g.api_user.id
    ).first()
    if series is None:
        return jsonify({'error': 'Serie non trovata.'}), 404

    return jsonify(series.to_dict())


@api_bp.route('/series', methods=['POST'])
@api_key_required
def create_series():
    """Crea una nuova serie per l'utente associato alla chiave API."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({'error': 'Body JSON non valido.'}), 400

    expression = payload.get('expression')
    if not isinstance(expression, str):
        return jsonify({'error': 'expression deve essere una stringa.'}), 400
    expression = expression.strip()

    try:
        start = _parse_int(payload.get('start'))
        end = _parse_int(payload.get('end'))
    except (TypeError, ValueError):
        return jsonify({'error': 'start e end devono essere numeri interi.'}), 400

    try:
        expression, start, end = validate_series_input(expression, start, end)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    series = Series(
        user_id=g.api_user.id,
        expression=expression,
        start=start,
        end=end,
        status=Series.STATUS_PENDING,
    )
    db.session.add(series)
    db.session.commit()

    enqueue_series(series.id)

    response = jsonify(series.to_dict())
    response.status_code = 201
    response.headers['Location'] = url_for(
        'api.get_series', series_id=series.id
    )
    return response
