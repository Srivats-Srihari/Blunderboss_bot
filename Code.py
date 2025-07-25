# Let's write an extremely detailed and robust script for your bot.
# Part 1: Core setup - Lichess Bot that plays the worst legal move, but never blunders a forced checkmate

import berserk
import chess
import chess.engine
import chess.pgn
import time
import threading
import sys
import os
import random

# === CONFIGURATION ===
API_TOKEN = "lip_VnRyBkJHRFP4xkaldmlw"  # Replace with your Lichess bot API token
ENGINE_PATH = "C:\Users\sriva\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe"  # Adjust if stockfish is not in PATH

# === CONNECT TO LICHESS ===
session = berserk.TokenSession(API_TOKEN)
client = berserk.Client(session=session)

# === CUSTOM FUNCTION: Check if move leads to forced mate ===
def is_forced_mate(board, move, depth=8):
    test_board = board.copy()
    test_board.push(move)
    with chess.engine.SimpleEngine.popen_uci(ENGINE_PATH) as engine:
        result = engine.analyse(test_board, chess.engine.Limit(depth=depth))
        if "score" in result and result["score"].is_mate():
            mate_score = result["score"].relative.mate()
            return mate_score is not None and mate_score < 0  # Negative mate means forced mate by opponent
    return False

# === CUSTOM FUNCTION: Find worst move that is NOT a forced mate ===
def find_worst_move(board):
    legal_moves = list(board.legal_moves)
    scored_moves = []
    with chess.engine.SimpleEngine.popen_uci(ENGINE_PATH) as engine:
        for move in legal_moves:
            if is_forced_mate(board, move):
                continue  # skip suicidal moves
            info = engine.analyse(board, chess.engine.Limit(depth=4), root_moves=[move])
            score = info["score"].white().score(mate_score=100000)
            scored_moves.append((move, score if score is not None else -99999))
    if not scored_moves:
        return random.choice(list(board.legal_moves))  # fallback
    worst_move = min(scored_moves, key=lambda x: x[1])[0]
    return worst_move

# === PLAY MOVE ===
def play_worst_move(game_id, my_color):
    board = chess.Board()
    for event in client.board.stream_game_state(game_id):
        if event['type'] == 'gameFull':
            moves = event['state']['moves'].split()
            for m in moves:
                board.push_uci(m)
        elif event['type'] == 'gameState':
            moves = event['moves'].split()
            board = chess.Board()
            for m in moves:
                board.push_uci(m)
            if board.turn == (my_color == 'white'):
                move = find_worst_move(board)
                client.board.make_move(game_id, move.uci())
                print(f"Made move: {move.uci()}")

# === ACCEPT CHALLENGES ===
def accept_challenges():
    for event in client.bots.stream_incoming_events():
        if event['type'] == 'challenge':
            challenge = event['challenge']
            if challenge['variant']['key'] == 'standard' and challenge['speed'] in ['bullet', 'blitz', 'rapid']:
                client.bots.accept_challenge(challenge['id'])
                print(f"Accepted challenge from {challenge['challenger']['name']}")
        elif event['type'] == 'gameStart':
            game_id = event['game']['id']
            color = event['game']['color']
            threading.Thread(target=play_worst_move, args=(game_id, color)).start()

# === MAIN ===
def main():
    print("Starting Worst Legal Move Bot (No Suicide Allowed™)")
    try:
        accept_challenges()
    except KeyboardInterrupt:
        print("Shutting down.")
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    main()
