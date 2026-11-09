import logging
import queue
import threading
from datetime import datetime

import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (
    auto_number,
    factorial_notation,
    lambda_notation,
    parse_expr,
)

from models.conn import db
from models.model import Series


logger = logging.getLogger(__name__)

MAX_TERMS = 100_000
MAX_EXPRESSION_LENGTH = 500

X = sp.Symbol('x')

# Whitelist dei nomi utilizzabili nelle formule. Usare una whitelist evita
# che sympify/parse_expr esegua codice Python arbitrario contenuto nell'input.
_ALLOWED_NAMES = {
    'x': X,
    'pi': sp.pi,
    'E': sp.E,
    'I': sp.I,
    'Integer': sp.Integer,
    'Float': sp.Float,
    'sin': sp.sin,
    'cos': sp.cos,
    'tan': sp.tan,
    'asin': sp.asin,
    'acos': sp.acos,
    'atan': sp.atan,
    'sinh': sp.sinh,
    'cosh': sp.cosh,
    'tanh': sp.tanh,
    'exp': sp.exp,
    'log': sp.log,
    'sqrt': sp.sqrt,
    'Abs': sp.Abs,
    'factorial': sp.factorial,
    'floor': sp.floor,
    'ceiling': sp.ceiling,
    'sign': sp.sign,
    'Min': sp.Min,
    'Max': sp.Max,
    'Mod': sp.Mod,
    'Rational': sp.Rational,
    '__builtins__': {},
}

_TRANSFORMATIONS = (lambda_notation, auto_number, factorial_notation)


def parse_expression(expression):
    """Trasforma la stringa dell'utente in un'espressione SymPy validata."""
    expression = (expression or '').strip()
    if not expression:
        raise ValueError('Inserisci una formula.')

    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ValueError(
            f'La formula non può superare {MAX_EXPRESSION_LENGTH} caratteri.'
        )

    try:
        expr = parse_expr(
            expression,
            local_dict={'x': X},
            global_dict=dict(_ALLOWED_NAMES),
            transformations=_TRANSFORMATIONS,
        )
    except NameError as exc:
        raise ValueError(
            'La formula può contenere solo la variabile x e le funzioni supportate.'
        ) from exc
    except Exception as exc:
        raise ValueError(f'Formula non valida: {exc}') from exc

    if not expr.free_symbols.issubset({X}):
        raise ValueError('La formula può contenere solo la variabile x.')

    return expr


def validate_series_input(expression, start, end):
    """Valida formula e intervallo. Solleva ValueError con un messaggio utente."""
    expression = (expression or '').strip()

    if start > end:
        raise ValueError(
            "L'inizio dell'intervallo non può essere maggiore della fine."
        )

    if end - start + 1 > MAX_TERMS:
        raise ValueError(f'Il numero massimo di termini è {MAX_TERMS}.')

    parse_expression(expression)
    return expression, start, end


def calculate_series(expression, start, end):
    """Calcola la sommatoria di expression per x da start a end inclusi."""
    expression, start, end = validate_series_input(expression, start, end)
    expr = parse_expression(expression)

    try:
        function = sp.lambdify(X, expr, 'numpy')
        x_values = np.arange(start, end + 1)
        y_values = function(x_values)
        total = np.sum(y_values)
    except Exception as exc:
        raise ValueError(f'Impossibile calcolare la serie: {exc}') from exc

    if np.iscomplexobj(total):
        raise ValueError('La serie produce un risultato complesso non supportato.')

    total = float(total)
    if not np.isfinite(total):
        raise ValueError('La serie produce un risultato non finito.')

    return total


# ---------------------------------------------------------------------------
# Worker in-process: un thread persistente consuma una coda di ID di serie.
# In futuro questa coda potrà essere sostituita da RabbitMQ senza cambiare
# l'interfaccia usata dalle route (enqueue_series).
# ---------------------------------------------------------------------------

_task_queue = queue.Queue()
_worker_thread = None
_worker_lock = threading.Lock()


def enqueue_series(series_id):
    """Accoda il calcolo di una serie per il worker."""
    _task_queue.put(series_id)


def _process_series(app, series_id):
    """Calcola una serie e aggiorna il suo stato sul database."""
    with app.app_context():
        series = db.session.get(Series, series_id)
        if series is None:
            logger.warning('Serie %s non trovata', series_id)
            return

        series.status = Series.STATUS_RUNNING
        series.started_at = datetime.utcnow()
        series.error = None
        db.session.commit()

        try:
            result = calculate_series(series.expression, series.start, series.end)
        except Exception as exc:
            logger.exception('Errore nel calcolo della serie %s', series_id)
            series.status = Series.STATUS_ERROR
            series.result = None
            series.error = str(exc)
        else:
            series.status = Series.STATUS_DONE
            series.result = result
            series.error = None

        series.finished_at = datetime.utcnow()
        db.session.commit()


def _worker_loop(app):
    logger.info('Worker delle serie avviato')
    while True:
        series_id = _task_queue.get()
        try:
            if series_id is None:
                break
            _process_series(app, series_id)
        except Exception:
            logger.exception('Errore imprevisto nel worker delle serie')
        finally:
            _task_queue.task_done()
    logger.info('Worker delle serie terminato')


def start_worker(app):
    """Avvia il thread worker se non è già attivo."""
    global _worker_thread

    with _worker_lock:
        if _worker_thread is not None and _worker_thread.is_alive():
            return _worker_thread

        _worker_thread = threading.Thread(
            target=_worker_loop,
            args=(app,),
            name='series-worker',
            daemon=True,
        )
        _worker_thread.start()
        return _worker_thread


def stop_worker(timeout=5):
    """Ferma il thread worker in modo ordinato (usato dai test)."""
    global _worker_thread

    with _worker_lock:
        thread = _worker_thread
        if thread is None or not thread.is_alive():
            _worker_thread = None
            return

        _task_queue.put(None)
        thread.join(timeout=timeout)
        _worker_thread = None


def calcola_serie_utente():
    """Entry point CLI interattivo, mantenuto per uso da terminale."""
    formula_str = input(
        "Inserisci la funzione in termini di x (es. cos(x), x**2, 1/x): "
    )
    inizio = int(input("Inserisci l'inizio del range (es. 1): "))
    fine = int(input("Inserisci la fine del range (es. 100): "))

    try:
        risultato = calculate_series(formula_str, inizio, fine)
    except ValueError as exc:
        print('Errore:', exc)
        return

    print(f"\nRisultato della sommatoria: {risultato}")


if __name__ == "__main__":
    calcola_serie_utente()
