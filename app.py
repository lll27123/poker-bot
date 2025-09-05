
import streamlit as st
import numpy as np
from deuces import Card, Evaluator

# -----------------------------
# Utilitaires cartes / parsing
# -----------------------------
RANKS = list("23456789TJQKA")
SUITS = list("shdc")  # s=h♠, h=♥, d=♦, c=♣
ALL_CARDS = [r + s for r in RANKS for s in SUITS]  # "As", "Kh", etc.

def parse_cards(text):
    """
    "As Kh" -> ["As","Kh"]
    Tolère espaces multiples / casse.
    """
    text = (text or "").strip()
    if not text:
        return []
    parts = text.replace(",", " ").split()
    # normalise (ex: aS -> As)
    norm = []
    for p in parts:
        p = p.strip()
        if len(p) != 2:
            continue
        r, s = p[0].upper(), p[1].lower()
        if r in RANKS and s in SUITS:
            norm.append(r + s)
    return norm

def to_treys(card_str):
    # "As" -> treys Card
    return Card.new(card_str)

def to_treys_list(cards):
    return [to_treys(c) for c in cards]

def unseen_cards(used):
    used_set = set(used)
    return [c for c in ALL_CARDS if c not in used_set]

# -----------------------------
# Monte-Carlo ultra-rapide
# -----------------------------
evaluator = Evaluator()

def equity_vs_field(hero, board, n_opp=1, n_sim=20000, rng=None):
    """
    Estime la probabilité de victoire du Hero contre n_opp adversaires
    par tirage Monte-Carlo des cartes manquantes.
    - hero: ["As","Kh"]
    - board: [], [..3 flop..], [..4 turn..], [..5 river..]
    """
    if rng is None:
        rng = np.random.default_rng()

    used = hero + board
    remain = unseen_cards(used)
    remain_arr = np.array(remain, dtype=object)

    wins = 0
    ties = 0

    # combien de cartes du board manquent ?
    need_board = 5 - len(board)
    # combien de cartes adverses ?
    need_opp = 2 * n_opp
    draw_count = need_board + need_opp

    hero_t = to_treys_list(hero)
    board_t_fixed = to_treys_list(board)

    for _ in range(n_sim):
        # Tirage sans remise sur le reste du paquet
        sample = rng.choice(remain_arr, size=draw_count, replace=False)

        # Split échantillon : d'abord on complète le board, puis les mains adverses
        add_board = list(sample[:need_board])
        opp_cards = list(sample[need_board:])

        board_full_t = board_t_fixed + to_treys_list(add_board)

        hero_rank = evaluator.evaluate(board_full_t, hero_t)

        best_opp = 1_000_000_000
        same_count = 0
        # évalue chaque adversaire
        for i in range(n_opp):
            opp = opp_cards[2*i:2*i+2]
            opp_t = to_treys_list(opp)
            rank = evaluator.evaluate(board_full_t, opp_t)
            if rank < best_opp:
                best_opp = rank
                same_count = 1
            elif rank == best_opp:
                same_count += 1

        # Dans treys : plus le rank est PETIT, meilleure est la main
        if hero_rank < best_opp:
            wins += 1
        elif hero_rank == best_opp:
            # partage si même meilleur rang que les meilleurs opposants
            ties += 1 / same_count

    return (wins + ties) / n_sim  # équité (avec split)

# -----------------------------
# Décision stratégique
# -----------------------------
def advise_action(p_equity, call_amount, pot_size, aggressivity=1.0):
    """Retourne Fold / Call / Raise (+ montant conseillé) via pot odds."""
    if call_amount <= 0:
        # cas de check possible : miser si edge net
        if p_equity > 0.55:
            bet = max(1, int(pot_size * 0.5 * aggressivity))
            return f"Bet {bet} 💰 (équité {p_equity:.2%})"
        return f"Check ✅ (équité {p_equity:.2%})"

    pot_odds = call_amount / (pot_size + call_amount)
    margin = 0.03 + 0.05 * aggressivity  # marge de sécurité

    if p_equity < pot_odds:
        return f"Fold ❌ (équité {p_equity:.2%} < pot odds {pot_odds:.2%})"
    elif p_equity < pot_odds + margin:
        return f"Call ✅ (équité {p_equity:.2%} vs pot odds {pot_odds:.2%})"
    else:
        # sizing de relance : ~ 0.7–1.2 pot selon agressivité
        target = pot_size * (0.7 + 0.5 * aggressivity)
        raise_amt = max(int(target), call_amount * 2)
        return f"Raise 💥 {raise_amt} (équité {p_equity:.2%} >> pot odds {pot_odds:.2%})"

# -----------------------------
# UI Streamlit
# -----------------------------
st.set_page_config(page_title="Poker Bot Advisor (fast)", page_icon="🂡")
st.title("🂡 Poker Bot Advisor — rapide & précis")

st.markdown(
    "Saisis **ta main** et le **board** avec initiales de couleurs : "
    "`s`=pique, `h`=cœur, `d`=carreau, `c`=trèfle.  \n"
    "Exemples : `As Kh` • Board flop : `2d 7c Jd`"
)

col1, col2 = st.columns(2)
hero_str = col1.text_input("Ta main (deux cartes)", "As Kh")
board_str = col2.text_input("Board (0 à 5 cartes)", "2d 7c Jd")

c1, c2, c3 = st.columns(3)
pot = c1.number_input("Pot actuel", min_value=0, value=100)
to_call = c2.number_input("Mise à payer (0 si check possible)", min_value=0, value=20)
n_opp = c3.number_input("Nb d'adversaires", min_value=1, max_value=8, value=2)

c4, c5 = st.columns(2)
n_sim = c4.slider("Nb de simulations", 5_000, 200_000, 50_000, step=5_000)
aggr = c5.slider("Agressivité bot", 0.0, 2.0, 1.0, 0.1)

if st.button("Calculer"):
    hero = parse_cards(hero_str)
    board = parse_cards(board_str)

    # validations rapides
    used = hero + board
    if len(hero) != 2:
        st.error("👉 Ta main doit contenir **exactement 2 cartes** (ex: `As Kh`).")
    elif len(board) not in (0, 3, 4, 5):
        st.error("👉 Le **board** doit avoir 0, 3, 4 ou 5 cartes.")
    elif len(set(used)) != len(used):
        st.error("👉 Carte dupliquée détectée. Vérifie ta saisie.")
    else:
        with st.spinner(f"Simulation Monte-Carlo ({n_sim:,} tirages)…"):
            eq = equity_vs_field(hero, board, n_opp=n_opp, n_sim=n_sim)
        st.write(f"**Équité estimée** : {eq:.2%}")

        advice = advise_action(eq, to_call, pot, aggressivity=aggr)
        st.success(advice)

        st.caption(
            "Calcul via évaluateur **exact** de mains (`treys`) + Monte-Carlo pour les cartes inconnues. "
            "Plus de tirages = plus précis."
        )
