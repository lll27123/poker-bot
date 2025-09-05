import streamlit as st
import random

# --------- Cartes & helpers ----------
VALS = "23456789TJQKA"
SUITS = "shdc"  # s=♠, h=♥, d=♦, c=♣

def deck52():
    return [v + s for v in VALS for s in SUITS]

def parse_cards(txt):
    """'As Kh' -> ['As','Kh']"""
    if not txt: return []
    out = []
    for p in txt.replace(",", " ").split():
        p = p.strip()
        if len(p) == 2 and p[0].upper() in VALS and p[1].lower() in SUITS:
            out.append(p[0].upper() + p[1].lower())
    return out

def eval_simple(hand, board):
    """Éval ultra simple mais rapide (pour le fun/entraîneur).
       +2 si paire, +1.5 si As, +1 si Roi, +0..1 bruit pour départager."""
    total = 0.0
    cards = hand + board
    vals = [c[0] for c in cards]
    if len(set(vals)) < len(vals):   # au moins une paire
        total += 2.0
    if "A" in vals:
        total += 1.5
    if "K" in vals:
        total += 1.0
    return total + random.random()

def win_prob(hero, board, opp=2, n_sim=10000):
    pack = [c for c in deck52() if c not in hero + board]
    wins = 0
    need_board = 5 - len(board)
    for _ in range(n_sim):
        random.shuffle(pack)
        # complète le board puis distribue aux adversaires
        b_full = board + pack[:need_board]
        start = need_board
        opp_hands = [pack[start+i*2:start+(i+1)*2] for i in range(opp)]
        hero_s = eval_simple(hero, b_full)
        opp_s = [eval_simple(h, b_full) for h in opp_hands]
        if hero_s >= max(opp_s):
            wins += 1
    return wins / n_sim

def advise(hero, board, to_call, pot, opp=2, n_sim=10000, aggr=1.0):
    p = win_prob(hero, board, opp, n_sim)
    if to_call <= 0:
        # check possible : bet si bon edge
        if p > 0.55:
            bet = max(1, int(pot * 0.5 * aggr))
            return p, f"Bet {bet} 💰 (équité ~{p:.2%})"
        return p, f"Check ✅ (équité ~{p:.2%})"
    pot_odds = to_call / (pot + to_call)
    if p < pot_odds:
        return p, f"Fold ❌ (équité {p:.2%} < pot odds {pot_odds:.2%})"
    elif p < pot_odds + 0.05:
        return p, f"Call ✅ (équité ~{p:.2%})"
    else:
        raise_amt = max(int(pot * 0.75 * aggr), to_call * 2)
        return p, f"Raise 💥 {raise_amt} (équité ~{p:.2%})"

# --------- UI Streamlit ----------
st.set_page_config(page_title="Poker Bot – Simple", page_icon="🂡")
st.title("🂡 Poker Bot (version simple, rapide)")

st.markdown("Cartes au format **As Kh** ; board **2d 7c Jd**. Couleurs: s=♠, h=♥, d=♦, c=♣.")

c1, c2 = st.columns(2)
hero_str  = c1.text_input("Ta main (2 cartes)", "As Kh")
board_str = c2.text_input("Board (0, 3, 4, 5 cartes)", "2d 7c Jd")

c3, c4, c5 = st.columns(3)
pot     = c3.number_input("Pot", min_value=0, value=100)
to_call = c4.number_input("Mise à payer (0 si check)", min_value=0, value=20)
opp     = c5.number_input("Nombre d'adversaires", min_value=1, max_value=8, value=2)

c6, c7 = st.columns(2)
n_sim = c6.slider("Nb de simulations", 1000, 50000, 10000, step=1000)
aggr  = c7.slider("Agressivité", 0.5, 2.0, 1.0, 0.1)

if st.button("Calculer"):
    hero  = parse_cards(hero_str)
    board = parse_cards(board_str)
    used = hero + board

    if len(hero) != 2:
        st.error("Ta main doit contenir exactement 2 cartes.")
    elif len(board) not in (0,3,4,5):
        st.error("Le board doit avoir 0, 3, 4 ou 5 cartes.")
    elif len(set(used)) != len(used):
        st.error("Carte dupliquée détectée.")
    else:
        with st.spinner(f"Monte-Carlo en cours ({n_sim:,} tirages)…"):
            p, tip = advise(hero, board, to_call, pot, opp, n_sim, aggr)
        st.write(f"**Équité estimée** : {p:.2%}")
        st.success(tip)
        st.caption("Version simple (heuristique) — pour s'entraîner/amuser entre amis (sans argent réel).")
