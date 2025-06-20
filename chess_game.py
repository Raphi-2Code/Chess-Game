from ursina.prefabs.splash_screen import *
from ursina.prefabs.dropdown_menu import DropdownMenu, DropdownMenuButton
import chess

app = Ursina(borderless=False)
UrsinaSplashScreen()
window.title = 'Ursina Chess'
camera.orthographic = True
camera.fov = 1
Text.default_font = "seguisym.ttf"

UNICODE_PIECE = {
    'p': '♙', 'n': '♘', 'b': '♗', 'r': '♖', 'q': '♕', 'k': '♔',
    'P': '♟', 'N': '♞', 'B': '♝', 'R': '♜', 'Q': '♛', 'K': '♚'
}

LIGHT, DARK = color.hex('F99850'), color.hex('774212')

board = chess.Board()
squares = {}
clicked = []
promo_gui = []
highlighted = []
tile_len = 0.125
move_display = None
undo_button = None
history_menu = None


def centered_text(msg: str, col, duration: float = 1.5):
    btn = Button(
        parent=camera.ui,
        text=msg,
        color=col,
        text_color=color.black,
        origin=(0, 0),
        scale=(.6, .15),
        z=-.15,
        radius=0
    )
    invoke(destroy, btn, delay=duration)
    return btn


def enable_board_input(state: bool):
    for btn in squares.values():
        btn.collider = 'box' if state else None


def rebuild_history_menu():
    global history_menu
    if history_menu:
        destroy(history_menu)

    tmp = chess.Board()
    labels = []
    for mv in board.move_stack:
        turn="⏹"
        if tmp.turn==True:
            turn="⏹"
        if tmp.turn==False:
            turn="□"
        labels.append(turn + str("   ") + tmp.san(mv))
        tmp.push(mv)

    if not labels:
        labels = ['(empty)']

    buttons = [DropdownMenuButton(lbl) for lbl in labels]
    #position = (window.left + 0.02, window.top - 0.05)
    history_menu = DropdownMenu(
        'History',
        buttons=buttons,
        parent=camera.ui,
        scale=(.25, .025),
        origin=(-.5, .5),
        z=-.2
    )


def update_board():
    for name, btn in squares.items():
        piece = board.piece_at(chess.parse_square(name))
        btn.text = UNICODE_PIECE[piece.symbol()] if piece else ''

    move_display.text = str(f"{board.peek().uci() if board.move_stack else ''}\n\n\n")

    rebuild_history_menu()


def undo_move():
    if not board.move_stack:
        return
    board.pop()
    update_board()
    clear_highlights()
    clicked.clear()
    rebuild_history_menu()


def ask_promotion(base_move: str):
    enable_board_input(False)
    pieces = [('q', '♕'), ('r', '♖'), ('b', '♗'), ('n', '♘')]

    spacing = tile_len * 1.2
    start_x = -1.5 * spacing
    y_pos = 0

    def choose(letter: str):
        for b in promo_gui:
            destroy(b)
        promo_gui.clear()
        enable_board_input(True)

        board.push_uci(base_move + letter)
        update_board()
        if board.is_check() and not board.is_checkmate():
            centered_text('Check!', color.red)
        if board.is_checkmate():
            centered_text('Checkmate!', color.gold)
        if board.is_stalemate():
            centered_text('Stalemate!', color.gold)

    for i, (letter, glyph) in enumerate(pieces):
        b = Button(
            parent=camera.ui,
            text=glyph,
            color=color.azure,
            text_color=color.black,
            scale=(tile_len, tile_len),
            position=(start_x + i * spacing, y_pos),
            origin=(0, 0),
            z=-0.1,
            on_click=Func(choose, letter),
            radius=0
        )
        promo_gui.append(b)


def clear_highlights():
    global highlighted
    for sq in highlighted:
        x = chess.square_file(chess.parse_square(sq))
        y = chess.square_rank(chess.parse_square(sq))
        squares[sq].color = LIGHT if (x + y) % 2 else DARK
    highlighted.clear()


def show_legal_targets(from_sq: str):
    clear_highlights()
    origin_idx = chess.parse_square(from_sq)
    squares[from_sq].color = color.hex("#86A666")
    highlighted.append(from_sq)

    for move in board.legal_moves:
        if move.from_square == origin_idx:
            name = chess.square_name(move.to_square)
            squares[name].color = color.hex("#4D7E42")
            highlighted.append(name)


def handle_click(square_name: str):
    if promo_gui:
        return

    if not clicked:
        if board.piece_at(chess.parse_square(square_name)) is None:
            return
        clicked.append(square_name)
        show_legal_targets(square_name)
        return

    clicked.append(square_name)
    move = ''.join(clicked)
    clear_highlights()

    try:
        board.push_uci(move)
        update_board()
        if board.is_check() and not board.is_checkmate():
            centered_text('Check!', color.red)
        if board.is_checkmate():
            centered_text('Checkmate!', color.gold)
        if board.is_stalemate():
            centered_text('Stalemate!', color.gold)
    except chess.IllegalMoveError:
        if needs_promotion(move):
            ask_promotion(move)
        else:
            centered_text('Illegal Move!', color.red)
    except chess.InvalidMoveError:
        centered_text('Invalid Move!', color.red)
    finally:
        clicked.clear()


def needs_promotion(base_move: str) -> bool:
    if len(base_move) != 4:
        return False
    start_sq = chess.parse_square(base_move[:2])
    piece = board.piece_at(start_sq)
    if piece is None or piece.piece_type != chess.PAWN:
        return False
    for l in 'qrbn':
        if chess.Move.from_uci(base_move + l) in board.legal_moves:
            return True
    return False



for x in range(8):
    for y in range(8):
        name = chess.square_name(chess.square(x, y))
        btn = Button(
            parent=camera.ui,
            text='',
            color=LIGHT if (x + y) % 2 else DARK,
            radius=0,
            collider='box',
            on_click=Func(handle_click, name),
        )
        btn.text_size = 4.5
        squares[name] = btn


def layout_board():
    global tile_len, move_display, undo_button
    aspect = window.aspect_ratio
    tile_len = 1 / 8
    if aspect < 1:
        tile_len *= aspect

    size = tile_len * 8
    x0 = -size / 2
    y0 = -size / 2

    for x in range(8):
        for y in range(8):
            name = chess.square_name(chess.square(x, y))
            btn = squares[name]
            btn.scale = (tile_len, tile_len)
            btn.position = (x0 + (x + .5) * tile_len, y0 + (y + .5) * tile_len)
            btn.origin = (0, 0)
            btn.z = 0

    if move_display is None:
        move_display = Draggable(parent=camera.ui, text='')

    if undo_button is None:
        undo_button = Button(
            parent=move_display,
            text=" ",
            texture="takeback",
            color=color.white,
            on_click=undo_move,
            radius=0,
        )
    else:
        undo_button.parent = move_display

    a8_pos = squares['a8'].position
    move_display.scale = (tile_len * .9, tile_len * .9)
    move_display.position = (a8_pos[0], a8_pos[1])
    move_display.origin = (0, 0)
    move_display.z = -0.1

    undo_button.scale = move_display.scale*5
    undo_button.position = (move_display.scale_x * 1.1, -1.5*tile_len)
    undo_button.origin = (0, 0)
    undo_button.z = -0.1

layout_board()
update_board()
rebuild_history_menu()

_prev = window.size


def update():
    global _prev
    if window.size != _prev:
        layout_board()
        _prev = window.size


def input(key):
    if key == 'u':
        undo_move()

app.run()
