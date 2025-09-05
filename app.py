import streamlit as st
import random

# --- Fonctions utilitaires ---

valeurs = "23456789TJQKA"
couleurs = "shdc"  # s = spades, h = hearts, d = diamonds, c = clubs

def creer_deck():
    return [v + c for v in valeurs for c in couleurs]

def eval_simple(main, board):
    """Évaluation très simplifiée : +points pour paire, As, Roi"""
    total = 0
    cartes = main + board
    valeurs_cartes = [c[0] for c in cartes]
    if len(set(valeurs_cartes)) < len(valeurs_cartes):  # paire
        total += 2
    if "A" in valeurs_cartes:  # as
        total += 1.5
    if "K" in valeurs_cartes:
        total += 1
    return total + random.random()

def proba_victoire(main, board, nb_adversaires=2, n_sim=10000):
    deck = [c for c in creer_deck() if c not in main + board]
    wins = 0
    for _ in range(n_sim):
        random.shuffle(deck)
        board_complet = board + deck[:5-len(board)]
        adversaires = [deck[5-len(board)+i*2:5-len(board)+(i+1)*2] for i in range(nb_adversaires)]
        score_bot = eval_simple(main, board_complet)
        scores_adv = [eval_simple(a, board_complet) for a in adversaires]
        if score_bot >= max(scores_adv):
            wins += 1
    return wins / n_sim

def decision_strategique(main, board, mise_a_payer, pot, nb_adversaires=2, agressivite=1.0):
    p_win = proba_victoire(main, board, nb_adversaires)
    pot_odds = mise_a_payer / (pot + mise_a_payer)

    if p_win < pot_odds:
        return f"Fold ❌ (proba {p_win:.2f} < pot odds {pot_odds:.2f})"
    elif p_win < pot_odds + 0.05:
        return f"Call ✅ (proba {p_win:.2f})"
    else:
        montant_relance = int(pot * 0.75 * agressivite)
        return f"Raise 💰 {montant_relance} (proba {p_win:.2f})"


# --- Interface Streamlit ---

st.title("♠️ Poker Bot Advisor ♣️")

st.markdown("Entrez vos cartes, le board, la mise et le pot. Le bot calcule et conseille Fold / Call / Raise.")

main_input = st.text_input("Votre main (ex: As Kh)", "As Kh")
board_input = st.text_input("Board (ex: 2d 7c Jd, laisser vide si pré-flop)", "")

mise = st.number_input("Mise à payer", min_value=0, value=20)
pot = st.number_input("Pot actuel", min_value=1, value=100)
adversaires = st.number_input("Nombre d'adversaires", min_value=1, max_value=8, value=2)

if st.button("Calculer"):
    main = main_input.split()
    board = board_input.split() if board_input else []
    decision = decision_strategique(main, board, mise, pot, nb_adversaires=adversaires)
    st.success(decision)
