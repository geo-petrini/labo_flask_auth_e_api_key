import numpy as np
import sympy as sp


def calcola_serie_utente():
    # 1. Chiedi la formula all'utente
    formula_str = input(
        "Inserisci la funzione in termini di x (es. cos(x), x**2, 1/x): "
    )

    # 2. Definisci il range
    inizio = int(input("Inserisci l'inizio del range (es. 1): "))
    fine = int(input("Inserisci la fine del range (es. 100): "))

    # 3. Trasforma la stringa in un'espressione matematica di SymPy
    x = sp.Symbol("x")
    try:
        espressione = sp.sympify(formula_str)
    except Exception as e:
        print("Errore nella sintassi della formula:", e)
        return

    # 4. Converte l'espressione in una funzione NumPy molto veloce
    # Questo permette di passare un intero array di colpo
    funzione_vettorizzata = sp.lambdify(x, espressione, "numpy")

    # 5. Genera i punti e calcola la somma
    valori_x = np.arange(inizio, fine + 1)
    valori_y = funzione_vettorizzata(valori_x)
    somma_totale = np.sum(valori_y)

    print(f"\nRisultato della sommatoria: {somma_totale}")


if __name__ == "__main__":
    calcola_serie_utente()
