import streamlit as st
import numpy as np
import eval7

# -----------------------------
# Cartes & parsing
# -----------------------------
RANKS = list("23456789TJQKA")
SUITS = list("shdc")  # s=♠, h=♥, d=♦, c=♣
ALL = [r + s for r in RANKS for s in SUITS]  # "As", "Kh", ...

def parse_cards(s: str):
    s = (s or "").strip()
    if not s:
        return []
    out = []
    for p in s.replace(",", " ").split():
        if len(p) != 2:
            continue
        r, t = p[0].upper(), p[1].lower()
        if r in RANKS and t in SUITS:
            out.append(r + t)
    return out

def to_eval7(cards):
    return [eval7.Card(c) for c in cards]

def unseen(used):
    u = set(used)
    return [c for c in ALL if c not in u]

# -----------------------------
# Monte-Carlo (eval7 : plus le score est GRAND, meilleure est la main)
# -----------------------------
def equity_vs_field(hero, board, n_opp=2, n_sim=50000, rng=None):
    if rng is None:
        rng = np.random.default_rng()

    need_board = 5 - len(board)
    need_opp = 2 * n_opp
    draw = need_board + need_opp

    used = hero + board
    deck_text = unseen(used)
    deck = np.array(deck_text, dtype=object)

    hero_e = to_eval7(hero)
    board_fixed_e = to_eval7(board)

    wins = 0
    ties = 0

    for _ in range(n_sim):
        sample = rng.choice(deck, size=draw, replace=False)
        add_board = list(sample[:need_board])
        opp_text = list(sample[need_board:])

        board_full_e = board_fixed_e + to_eval7(add_board)

        hero_score = eval7.evaluate(hero_e + board_full_e)

        best_opp = -1
        best_count = 0
        for i in range(n_opp):
            opp_e = to_eval7(opp_text[2*i:2*i+2])
            score = eval7.evaluate(opp_e + board_full_e)
            if score > best_opp:
                best_opp = score
                best_count = 1
            elif score == best_opp:
                best_count += 1

        if hero_score > best_opp:
            wins += 1
        elif hero_score == best_opp:
            ties += 1 / best_count

    return (wins + ties) / n_sim

# -----------------------------
# Politique de décision
# -----------------------------
def advise_action(p_eq, to_call, pot, aggressivity=1.0):
    if to_call <= 0:
        # Pas de relance à payer : value bet si bon edge
        if p_eq > 0.55:
            bet = max(1, int(pot * (0.5 + 0.3 * aggressivity)))
            return f"Bet {bet} 💰  (équité {p_eq:.2%})"
        return f"Check ✅  (équité {p_eq:.2%})"

    pot_odds = to_call / (pot + to_call)
    margin = 0.03 + 0.05 * aggressivity

    if p_eq < pot_odds:
        return f"Fold ❌  (équité {p_eq:.2%} < pot odds {pot_odds:.2%})"
    elif p_eq < pot_odds + margin:
        return f"Call ✅  (équité {p_eq:.2%} vs {pot_odds:.2%})"
    else:
        target = pot * (0.7 + 0.5 * aggressivity)
        raise_amt = max(int(target), to_call * 2)
        return f"Raise 💥 {raise_amt}  (équité {p_eq:.2%} >> {pot_odds:.2%})"

# -----------------------------
# UI Streamlit
# -----------------------------
st.set_page_config(page_title="Poker Bot Advisor (eval7)", page_icon="🂡")
st.title("🂡 Poker Bot Advisor — rapide & précis (eval7)")

st.markdown(
    "Format cartes : `As Kh` ; board : `2d 7c Jd` • Couleurs: `s`=pique, `h`=cœur, `d`=carreau, `c`=trèfle."
)

c1, c2 = st.columns(2)
hero_str = c1.text_input("Ta main (2 cartes)", "As Kh")
board_str = c2.text_input("Board (0/3/4/5 cartes)", "2d 7c Jd")

c3, c4, c5 = st.columns(3)
pot = c3.number_input("Pot", min_value=0, value=100)
to_call = c4.number_input("Mise à payer (0 si check)", min_value=0, value=20)
n_opp = c5.number_input("Adversaires", min_value=1, max_value=8, value=2)

c6, c7 = st.columns(2)
n_sim = c6.slider("Nb de simulations", 5000, 200000, 50000, step=5000)
aggr = c7.slider("Agressivité", 0.0, 2.0, 1.0, 0.1)

if st.button("Calculer"):
    hero = parse_cards(hero_str)
    board = parse_cards(board_str)
    used = hero + board

    if len(hero) != 2:
        st.error("Ta main doit contenir exactement 2 cartes.")
    elif len(board) not in (0, 3, 4, 5):
        st.error("Le board doit avoir 0, 3, 4 ou 5 cartes.")
    elif len(set(used)) != len(used):
        st.error("Carte dupliquée détectée.")
    else:
        with st.spinner(f"Monte-Carlo en cours ({n_sim:,} tirages)…"):
            eq = equity_vs_field(hero, board, n_opp=n_opp, n_sim=n_sim)
        st.write(f"**Équité estimée** : {eq:.2%}")
        st.success(advise_action(eq, to_call, pot, aggressivity=aggr))
        st.caption("Évaluations exactes par `eval7` + tirages Monte-Carlo des cartes inconnues.")
