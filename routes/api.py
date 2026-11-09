from flask import Blueprint, jsonify, request, url_for

from models.conn import db
from models.model import Series
from worker import enqueue_series, validate_series_input


api_bp = Blueprint('api', __name__, url_prefix='/api')

# In questa fase l'API non ha autenticazione: le serie create vengono
# assegnate a un utente fisso. In futuro l'API key identificherà l'utente.
API_USER_ID = 1


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


@api_bp.route('/series', methods=['GET'])
def list_series():
    """Restituisce tutte le serie, dalla più recente."""
    series_list = (
        Series.query
        .order_by(Series.created_at.desc(), Series.id.desc())
        .all()
    )
    return jsonify({'series': [series.to_dict() for series in series_list]})


@api_bp.route('/series/<int:series_id>', methods=['GET'])
def get_series(series_id):
    """Restituisce una singola serie."""
    series = db.session.get(Series, series_id)
    if series is None:
        return jsonify({'error': 'Serie non trovata.'}), 404

    return jsonify(series.to_dict())


@api_bp.route('/series', methods=['POST'])
def create_series():
    """Crea una nuova serie e la accoda per il calcolo."""
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
        user_id=API_USER_ID,
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
