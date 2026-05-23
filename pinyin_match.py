import tkinter as tk
import random
import math
import json
import os

# ── Sound ──────────────────────────────────────────────
try:
    import winsound
    def _beep(freq, dur):
        try: winsound.Beep(freq, dur)
        except: pass
except ImportError:
    def _beep(freq, dur): pass

# ── Constants ──────────────────────────────────────────
CANVAS_W = 800
CANVAS_H = 600
TOP_BAR_H = 60
MSG_AREA_H = 50
CARD_PAD = 20
MIN_CARD = 120
MAX_CARD = 160

BG        = "#FFF8E7"
CARD_BACK = "#5B9BD5"
CARD_BACK_BORDER = "#BDD7EE"
CARD_FRONT = "#FFFFFF"
CARD_FRONT_BORDER = "#CCCCCC"
MATCHED_BG = "#A8E6CF"
MATCHED_BORDER = "#7BC8A4"
TEXT_DARK = "#333333"
TEXT_HINT = "#FF6B35"
STAR_GOLD = "#FFD700"
LOCKED_CLR = "#CCCCCC"

LEVEL_PASTEL = [
    "#FFB3BA", "#BAFFC9", "#BAE1FF", "#FFFFBA",
    "#FFD4BA", "#E8BAFF", "#BAFFEC", "#FFC8DD", "#C9D9FF"
]

# ── Fonts ──────────────────────────────────────────────
def _safe_font(family, size, bold=False, italic=False):
    """Return a font tuple, with tkinter silently falling back to system default."""
    weight = "bold" if bold else "normal"
    slant = "italic" if italic else "roman"
    return (family, size, weight, slant)

FONT_CARD   = lambda s: ("Comic Sans MS", s, "bold")
FONT_ZH     = lambda s, b=False: ("KaiTi", s, "bold" if b else "normal")
FONT_TITLE  = lambda: ("Comic Sans MS", 32, "bold")
FONT_SUB    = lambda: ("Comic Sans MS", 14)
FONT_HINT   = lambda: ("KaiTi", 14)
FONT_BTN    = lambda: ("KaiTi", 16)

# ── Level Config ───────────────────────────────────────
LEVELS = [
    {"id":1, "name":"韵母入门", "letters":["a","o","e"],     "hint":None},
    {"id":2, "name":"韵母进阶", "letters":["i","u","ü"],     "hint":None},
    {"id":3, "name":"声母bpmf","letters":["b","p","m","f"],  "hint":None},
    {"id":4, "name":"声母dtnl","letters":["d","t","n","l"],  "hint":None},
    {"id":5, "name":"声母gkh",  "letters":["g","k","h"],     "hint":None},
    {"id":6, "name":"声母jqx",  "letters":["j","q","x"],     "hint":None},
    {"id":7, "name":"平翘舌音", "letters":["z","c","s","zh"],"hint":None},
    {"id":8, "name":"声母yw",   "letters":["y","w"],         "hint":None},
    {"id":9, "name":"火眼金睛", "letters":["b","d","p","q"], "hint": {
        "b": "b: 圆肚子在 右下方",
        "d": "d: 圆肚子在 左下方",
        "p": "p: 圆肚子在 右上方",
        "q": "q: 圆肚子在 左上方",
    }},
]

# ── Save path ──────────────────────────────────────────
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "pinyin_match_save.json")


class PinyinMatchGame:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("拼音卡片接龙 - Pinyin Card Matching")
        self.window.resizable(False, False)

        self.canvas = tk.Canvas(
            self.window, width=CANVAS_W, height=CANVAS_H, bg=BG
        )
        self.canvas.pack()

        self.status_var = tk.StringVar(value="")
        self.status_label = tk.Label(
            self.window, textvariable=self.status_var,
            font=FONT_SUB(), fg=TEXT_DARK, bg=BG, pady=6
        )
        self.status_label.pack(fill=tk.X)

        self.canvas.bind("<Button-1>", self.on_click)

        self._load_progress()
        self.state = "MENU"
        self.cards = []
        self.flipped = []
        self.matched_count = 0
        self.total_pairs = 0
        self.animating = False
        self.msg_id = None
        self.hint_id = None
        self.star_particles = []
        self._book_flash_id = None

        self.draw_menu()
        self.window.mainloop()

    # ── Progress ───────────────────────────────────────
    def _load_progress(self):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                self.highest_unlocked = json.load(f).get("highest_unlocked", 1)
        except (FileNotFoundError, json.JSONDecodeError):
            self.highest_unlocked = 1

    def _save_progress(self):
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump({"highest_unlocked": self.highest_unlocked}, f)
        except Exception:
            pass

    # ── Sound helpers ───────────────────────────────────
    def _play_flip(self):
        _beep(800, 50)

    def _play_match(self):
        for note, delay in [(523,0), (659,100), (784,200)]:
            self.window.after(delay, lambda f=note: _beep(f, 100))

    def _play_mismatch(self):
        for note, delay in [(600,0), (400,100)]:
            self.window.after(delay, lambda f=note: _beep(f, 100))

    def _play_level_complete(self):
        for note, delay in [(523,0),(659,120),(784,240),(1047,360)]:
            self.window.after(delay, lambda f=note: _beep(f, 120))

    def _play_win(self):
        for i, note in enumerate([523, 587, 659, 784, 880, 1047, 1175]):
            self.window.after(i * 150, lambda f=note: _beep(f, 200))

    # ── Menu ────────────────────────────────────────────
    def draw_menu(self):
        self.canvas.delete("all")
        self.state = "MENU"
        self.animating = False
        self.status_var.set("选择关卡开始游戏！")
        self._base_draw_menu()
        self._draw_book()

    def _base_draw_menu(self):

        self.canvas.create_text(
            CANVAS_W // 2, 36, text="拼音卡片接龙",
            font=FONT_TITLE(), fill=TEXT_DARK
        )
        self.canvas.create_text(
            CANVAS_W // 2, 68, text="Pinyin Card Matching",
            font=FONT_SUB(), fill="#888888"
        )

        # 3x3 level buttons
        btn_size = 90
        gap = 24
        grid_w = 3 * btn_size + 2 * gap
        grid_h = 3 * btn_size + 2 * gap
        start_x = (CANVAS_W - grid_w) // 2 + btn_size // 2
        start_y = 130 + btn_size // 2

        self._menu_buttons = {}  # (col,row) -> {id, rect_id, ...}
        for i, lv in enumerate(LEVELS):
            row = i // 3
            col = i % 3
            cx = start_x + col * (btn_size + gap)
            cy = start_y + row * (btn_size + gap)
            unlocked = lv["id"] <= self.highest_unlocked

            bg_color = LEVEL_PASTEL[i] if unlocked else LOCKED_CLR
            rect = self.canvas.create_rectangle(
                cx - btn_size//2, cy - btn_size//2,
                cx + btn_size//2, cy + btn_size//2,
                fill=bg_color, outline="#999999", width=2
            )
            name = self.canvas.create_text(
                cx, cy - 12, text=lv["name"],
                font=FONT_ZH(14, True), fill=TEXT_DARK
            )
            preview = ", ".join(lv["letters"][:4])
            preview_id = self.canvas.create_text(
                cx, cy + 14, text=preview,
                font=FONT_CARD(13), fill=TEXT_DARK if unlocked else "#AAAAAA"
            )
            self._menu_buttons[(col, row)] = {
                "id": lv["id"],
                "rect": rect,
                "cx": cx, "cy": cy, "size": btn_size,
                "unlocked": unlocked,
            }
            if not unlocked:
                self.canvas.create_rectangle(
                    cx - 8, cy - 8, cx + 8, cy + 8,
                    fill="#999999", outline=""
                )
                self.canvas.create_arc(
                    cx - 8, cy - 14, cx + 8, cy,
                    start=0, extent=180, fill="#999999", outline=""
                )

        self.canvas.create_text(
            CANVAS_W // 2, start_y + 3*(btn_size+gap)//2 + 20,
            text=f"已解锁: 第{self.highest_unlocked}关 / 共9关",
            font=FONT_ZH(14), fill="#888888"
        )

    # ── Level Start ─────────────────────────────────────
    def start_level(self, level_id):
        self.state = "PLAYING"
        self.animating = False
        self.current_level_id = level_id
        level = LEVELS[level_id - 1]
        self.flipped = []
        self.matched_count = 0
        self.total_pairs = len(level["letters"])
        self.msg_id = None
        self.hint_id = None
        self.star_particles = []

        self.canvas.delete("all")
        self._draw_book()
        self.status_var.set(f"第{level_id}关 · {level['name']}  |  找出相同拼音的一对")

        # build card list: 2 cards per letter
        cards_data = []
        for i, letter in enumerate(level["letters"]):
            cards_data.append({"letter": letter, "pair_id": i})
            cards_data.append({"letter": letter, "pair_id": i})
        random.shuffle(cards_data)

        cols, rows = self._grid_for_count(len(cards_data))
        positions, card_size = self._calc_layout(cols, rows)
        self.cards = []
        for idx, ((x, y), cd) in enumerate(zip(positions, cards_data)):
            card = {
                "id": idx,
                "letter": cd["letter"],
                "pair_id": cd["pair_id"],
                "x": x, "y": y, "size": card_size,
                "state": "down",
                "items": {},
                "ill_items": [],
            }
            self._draw_card_back(card)
            self.cards.append(card)

    def _grid_for_count(self, n):
        if n <= 4:  return (2, 2)
        if n <= 6:  return (3, 2)
        return (4, 2)

    def _calc_layout(self, cols, rows):
        avail_w = CANVAS_W - CARD_PAD * (cols + 1)
        avail_h = CANVAS_H - TOP_BAR_H - MSG_AREA_H - CARD_PAD * (rows + 1)
        card_size = min(avail_w // cols, avail_h // rows, MAX_CARD)
        card_size = max(card_size, MIN_CARD)

        grid_w = cols * card_size + (cols - 1) * CARD_PAD
        grid_h = rows * card_size + (rows - 1) * CARD_PAD
        ox = (CANVAS_W - grid_w) // 2
        oy = TOP_BAR_H + (CANVAS_H - TOP_BAR_H - MSG_AREA_H - grid_h) // 2

        positions = []
        for r in range(rows):
            for c in range(cols):
                x = ox + c * (card_size + CARD_PAD)
                y = oy + r * (card_size + CARD_PAD)
                positions.append((x, y))
        return positions, card_size

    # ── Card Drawing ────────────────────────────────────
    def _draw_card_back(self, card, show=True):
        x, y, s = card["x"], card["y"], card["size"]
        st = "normal" if show else "hidden"
        rect = self.canvas.create_rectangle(
            x, y, x + s, y + s,
            fill=CARD_BACK, outline=CARD_BACK_BORDER, width=2,
            state=st
        )
        # star on back
        cx, cy = x + s/2, y + s/2
        pts = self._star_points(cx, cy, s * 0.18, s * 0.08)
        star = self.canvas.create_polygon(
            pts, fill="#FFFFFF", outline="", state=st
        )
        card["items"]["rect"] = rect
        card["items"]["star"] = star
        card["items"]["front_rect"] = None
        card["items"]["front_text"] = None
        card["items"]["front_items"] = []

    def _star_points(self, cx, cy, r_outer, r_inner):
        pts = []
        for i in range(10):
            ang = math.pi/2 + i * math.pi/5
            r = r_outer if i % 2 == 0 else r_inner
            pts.extend([cx + r * math.cos(ang), cy - r * math.sin(ang)])
        return pts

    def _show_card_front(self, card):
        x, y, s = card["x"], card["y"], card["size"]
        rect = self.canvas.create_rectangle(
            x, y, x + s, y + s,
            fill=CARD_FRONT, outline=CARD_FRONT_BORDER, width=2
        )
        # letter
        text = self.canvas.create_text(
            x + s/2, y + s/2,
            text=card["letter"], font=FONT_CARD(int(s * 0.35)), fill=TEXT_DARK
        )
        # illustration
        ill_items = self._draw_illustration(card["letter"], x + s * 0.75, y + s * 0.2, s * 0.14)
        card["items"]["front_rect"] = rect
        card["items"]["front_text"] = text
        card["items"]["front_items"] = ill_items

    def _hide_card_front(self, card):
        items = card["items"]
        for k in ("front_rect", "front_text"):
            if items.get(k):
                self.canvas.delete(items[k])
                items[k] = None
        for item in items.get("front_items", []):
            self.canvas.delete(item)
        items["front_items"] = []

    def _set_card_matched(self, card):
        self.canvas.itemconfigure(card["items"]["rect"], fill=MATCHED_BG, outline=MATCHED_BORDER)

    # ── Illustrations ───────────────────────────────────
    def _draw_illustration(self, letter, cx, cy, r):
        items = []
        c = self.canvas
        lt = letter

        def oval(x1,y1,x2,y2,**kw):
            return c.create_oval(x1,y1,x2,y2,**kw)
        def rect(x1,y1,x2,y2,**kw):
            return c.create_rectangle(x1,y1,x2,y2,**kw)
        def line(x1,y1,x2,y2,**kw):
            return c.create_line(x1,y1,x2,y2,**kw)
        def arc(x1,y1,x2,y2,**kw):
            return c.create_arc(x1,y1,x2,y2,**kw)

        # Each letter gets a simple mnemonic illustration
        if lt == "a":
            items.append(oval(cx-r,cy-r,cx+r,cy+r,fill="#FF6B6B",outline=""))
            items.append(line(cx-r/2,cy-r,cx,cy-r*1.8,fill="#4CAF50",width=2))
        elif lt == "o":
            items.append(oval(cx-r,cy-r,cx+r,cy+r,fill="",outline="#FF9800",width=3))
        elif lt == "e":
            items.append(line(cx-r,cy,cx+r,cy,fill="#999",width=2))
            items.append(arc(cx-r*0.6,cy-r,cx+r*0.6,cy+r,start=200,extent=180,style="arc",outline="#999",width=2))
        elif lt == "i":
            items.append(line(cx,cy-r,cx,cy+r,fill="#333",width=2))
            items.append(oval(cx-r*0.4,cy-r*1.2,cx+r*0.4,cy-r*0.4,fill="#FF9800",outline=""))
        elif lt == "u":
            items.append(arc(cx-r,cy,cx+r,cy+r*1.2,start=0,extent=180,style="arc",outline="#5B9BD5",width=3))
        elif lt == "ü":  # ü
            items.append(arc(cx-r,cy,cx+r,cy+r*1.2,start=0,extent=180,style="arc",outline="#5B9BD5",width=3))
            items.append(oval(cx-r*0.6,cy-r*1.2,cx-r*0.1,cy-r*0.7,fill="#333",outline=""))
            items.append(oval(cx+r*0.1,cy-r*1.2,cx+r*0.6,cy-r*0.7,fill="#333",outline=""))
        elif lt == "b":
            items.append(line(cx,cy-r,cx,cy+r,fill="#1565C0",width=3))
            items.append(arc(cx,cy,cx+r*2,cy+r,start=240,extent=300,style="arc",outline="#1565C0",width=2))
        elif lt == "p":
            items.append(line(cx,cy-r,cx,cy+r,fill="#1565C0",width=3))
            items.append(arc(cx,cy-r*2,cx+r*2,cy,start=60,extent=300,style="arc",outline="#1565C0",width=2))
        elif lt == "m":
            items.append(line(cx-r*0.8,cy-r,cx-r*0.8,cy+r,fill="#E91E63",width=2))
            items.append(arc(cx-r*0.8,cy,cx,cy+r,start=0,extent=180,style="arc",outline="#E91E63",width=2))
            items.append(arc(cx,cy,cx+r*0.8,cy+r,start=0,extent=180,style="arc",outline="#E91E63",width=2))
            items.append(line(cx+r*0.8,cy-r,cx+r*0.8,cy+r,fill="#E91E63",width=2))
        elif lt == "f":
            items.append(line(cx,cy-r,cx,cy+r,fill="#4CAF50",width=3))
            items.append(line(cx-r/2,cy-r,cx+r,cy-r,fill="#4CAF50",width=2))
        elif lt == "d":
            items.append(line(cx,cy-r,cx,cy+r,fill="#1565C0",width=3))
            items.append(arc(cx-r*2,cy,cx,cy+r,start=300,extent=300,style="arc",outline="#1565C0",width=2))
        elif lt == "t":
            items.append(line(cx,cy-r,cx,cy+r,fill="#4CAF50",width=3))
            items.append(line(cx-r,cy-r*0.5,cx+r,cy-r*0.5,fill="#4CAF50",width=2))
        elif lt == "n":
            items.append(line(cx-r*0.6,cy-r,cx-r*0.6,cy+r,fill="#FF5722",width=2))
            items.append(arc(cx-r*0.6,cy,cx+r*0.6,cy+r,start=0,extent=180,style="arc",outline="#FF5722",width=2))
            items.append(line(cx+r*0.6,cy,cx+r*0.6,cy+r,fill="#FF5722",width=2))
        elif lt == "l":
            items.append(line(cx,cy-r,cx,cy+r,fill="#E91E63",width=3))
        elif lt == "g":
            items.append(line(cx+r*0.3,cy-r,cx,cy+r*0.5,fill="#4CAF50",width=3))
            items.append(arc(cx-r,cy-r*0.5,cx,cy+r,start=270,extent=180,style="arc",outline="#4CAF50",width=2))
        elif lt == "k":
            items.append(line(cx,cy-r,cx,cy+r,fill="#9C27B0",width=3))
            items.append(line(cx,cy,cx+r*0.6,cy-r*0.6,fill="#9C27B0",width=2))
            items.append(line(cx,cy,cx+r*0.6,cy+r*0.6,fill="#9C27B0",width=2))
        elif lt == "h":
            items.append(line(cx-r*0.6,cy-r,cx-r*0.6,cy+r,fill="#795548",width=3))
            items.append(arc(cx-r*0.6,cy,cx+r*0.6,cy+r,start=0,extent=180,style="arc",outline="#795548",width=2))
            items.append(line(cx+r*0.6,cy,cx+r*0.6,cy+r,fill="#795548",width=2))
        elif lt == "j":
            items.append(line(cx,cy+r*0.2,cx,cy+r,fill="#FF9800",width=3))
            items.append(arc(cx-r,cy+r*0.5,cx,cy+r*1.5,start=180,extent=180,style="arc",outline="#FF9800",width=2))
            items.append(oval(cx-r*0.4,cy-r*0.9,cx+r*0.4,cy-r*0.1,fill="#FF9800",outline=""))
        elif lt == "q":
            items.append(oval(cx-r*0.5,cy-r*0.5,cx+r*0.5,cy+r*0.5,fill="#FF5722",outline=""))
            items.append(line(cx+cx*0.01,cy+r*0.3,cx+r,cy+r,fill="#FF5722",width=2))
        elif lt == "x":
            items.append(line(cx-r*0.7,cy-r*0.7,cx+r*0.7,cy+r*0.7,fill="#607D8B",width=2))
            items.append(line(cx+r*0.7,cy-r*0.7,cx-r*0.7,cy+r*0.7,fill="#607D8B",width=2))
        elif lt == "z":
            items.append(line(cx-r,cy-r*0.6,cx+r,cy-r*0.6,fill="#00BCD4",width=2))
            items.append(line(cx+r,cy-r*0.6,cx-r,cy+r*0.6,fill="#00BCD4",width=2))
            items.append(line(cx-r,cy+r*0.6,cx+r,cy+r*0.6,fill="#00BCD4",width=2))
        elif lt == "c":
            items.append(arc(cx-r,cy-r,cx+r,cy+r,start=45,extent=270,style="arc",outline="#00BCD4",width=3))
        elif lt == "s":
            items.append(arc(cx-r,cy-r,cx,cy,start=90,extent=180,style="arc",outline="#00BCD4",width=2))
            items.append(arc(cx,cy,cx+r,cy+r,start=270,extent=180,style="arc",outline="#00BCD4",width=2))
        elif lt == "r":
            items.append(line(cx,cy-r*0.5,cx,cy+r,fill="#E91E63",width=2))
            items.append(oval(cx-r*0.4,cy-r*1.2,cx+r*0.4,cy-r*0.4,fill="#F48FB1",outline=""))
        elif lt == "y":
            items.append(line(cx-r*0.5,cy-r,cx,cy,fill="#00BCD4",width=2))
            items.append(line(cx+r*0.5,cy-r,cx,cy+r,fill="#00BCD4",width=2))
        elif lt == "w":
            items.append(line(cx-r*0.8,cy-r,cx-r*0.3,cy+r,fill="#FF9800",width=2))
            items.append(line(cx-r*0.3,cy+r,cx,cy,fill="#FF9800",width=2))
            items.append(line(cx,cy,cx+r*0.3,cy+r,fill="#FF9800",width=2))
            items.append(line(cx+r*0.3,cy+r,cx+r*0.8,cy-r,fill="#FF9800",width=2))
        elif lt == "zh":
            # composite: small z + h
            items.append(line(cx-r*0.7,cy-r*0.8,cx-r*0.1,cy-r*0.8,fill="#00BCD4",width=1.5))
            items.append(line(cx-r*0.1,cy-r*0.8,cx-r*0.7,cy,fill="#00BCD4",width=1.5))
            items.append(line(cx-r*0.7,cy,cx-r*0.1,cy,fill="#00BCD4",width=1.5))
            items.append(line(cx+r*0.1,cy-r,cx+r*0.1,cy+r*0.3,fill="#795548",width=2))
            items.append(arc(cx+r*0.1,cy,cx+r*0.8,cy+r*0.5,start=0,extent=180,style="arc",outline="#795548",width=1.5))

        return items

    # ── Flip Animation ──────────────────────────────────
    def _animate_flip_to_front(self, card, on_complete=None):
        self.animating = True
        card["state"] = "animating"
        self._flip_step(card, reveal_front=True, step=0, on_complete=on_complete)

    def _animate_flip_to_back(self, card, on_complete=None):
        self.animating = True
        card["state"] = "animating"
        self._flip_step(card, reveal_front=False, step=0, on_complete=on_complete)

    def _flip_step(self, card, reveal_front, step, on_complete):
        FLIP_FRAMES = 16
        HALF = 8
        x, y, s = card["x"], card["y"], card["size"]
        cx = x + s / 2

        if step < HALF:
            scale = 1.0 - (step / (HALF - 1)) * 0.95
            new_left = cx - (s * scale / 2)
            new_right = cx + (s * scale / 2)
            self.canvas.coords(card["items"]["rect"], new_left, y, new_right, y + s)
            if step == HALF - 1:
                self.canvas.itemconfigure(card["items"]["star"], state="hidden")
        elif step == HALF:
            # switch faces
            scale = 0.05
            new_left = cx - (s * scale / 2)
            new_right = cx + (s * scale / 2)
            self.canvas.coords(card["items"]["rect"], new_left, y, new_right, y + s)
            if reveal_front:
                self.canvas.itemconfigure(card["items"]["rect"], fill=CARD_FRONT, outline=CARD_FRONT_BORDER)
                self._show_card_front(card)
            else:
                self._hide_card_front(card)
                self.canvas.itemconfigure(card["items"]["rect"], fill=CARD_BACK, outline=CARD_BACK_BORDER)
                self.canvas.itemconfigure(card["items"]["star"], state="normal")
        else:
            scale = 0.05 + ((step - HALF) / (HALF - 1)) * 0.95
            new_left = cx - (s * scale / 2)
            new_right = cx + (s * scale / 2)
            self.canvas.coords(card["items"]["rect"], new_left, y, new_right, y + s)

        if step < FLIP_FRAMES - 1:
            self.window.after(22, lambda: self._flip_step(card, reveal_front, step + 1, on_complete))
        else:
            # ensure full size
            self.canvas.coords(card["items"]["rect"], x, y, x + s, y + s)
            card["state"] = "up" if reveal_front else "down"
            if on_complete:
                on_complete()

    # ── Click Handling ──────────────────────────────────
    def on_click(self, event):
        if self.state == "MENU":
            self._handle_menu_click(event.x, event.y)
        elif self.state == "PLAYING":
            self._handle_play_click(event.x, event.y)
        elif self.state in ("LEVEL_COMPLETE", "WIN"):
            self._handle_complete_click(event.x, event.y)

    def _handle_menu_click(self, mx, my):
        for key, btn in getattr(self, "_menu_buttons", {}).items():
            cx, cy, s = btn["cx"], btn["cy"], btn["size"]
            if abs(mx - cx) < s/2 and abs(my - cy) < s/2 and btn["unlocked"]:
                self.start_level(btn["id"])
                return

    def _handle_play_click(self, mx, my):
        if self.animating:
            return
        for card in self.cards:
            if card["state"] != "down":
                continue
            x, y, s = card["x"], card["y"], card["size"]
            if x <= mx <= x + s and y <= my <= y + s:
                self._play_flip()
                self._animate_flip_to_front(card, on_complete=lambda c=card: self._after_flip(c))
                break

    def _after_flip(self, card):
        self.flipped.append(card)
        if len(self.flipped) == 1:
            self.animating = False
        elif len(self.flipped) == 2:
            c1, c2 = self.flipped
            if c1["pair_id"] == c2["pair_id"]:
                self.window.after(250, lambda: self._handle_match(c1, c2))
            else:
                self.window.after(250, lambda: self._handle_mismatch(c1, c2))

    # ── Match Handling ──────────────────────────────────
    def _handle_match(self, c1, c2):
        self._play_match()
        c1["state"] = "matched"
        c2["state"] = "matched"
        self._set_card_matched(c1)
        self._set_card_matched(c2)
        self._show_msg("配对成功！真棒！")
        self._spawn_stars(c1)
        self._spawn_stars(c2)
        self._fly_cards_to_book(c1, c2)
        self.matched_count += 1
        self.flipped = []

        if self.matched_count == self.total_pairs:
            self.window.after(800, self._show_level_complete)
        else:
            self.window.after(600, lambda: setattr(self, "animating", False))

    def _handle_mismatch(self, c1, c2):
        self._play_mismatch()
        self._show_msg("不一样哦，再记一记～")

        if self.current_level_id == 9:
            self._show_level9_hint(c1, c2)

        def flip_back():
            self._animate_flip_to_back(c1, on_complete=None)
            self._animate_flip_to_back(c2, on_complete=self._mismatch_done)

        self.window.after(1000, flip_back)

    def _mismatch_done(self):
        self.flipped = []
        self._clear_msg()
        self.animating = False

    # ── Messages ────────────────────────────────────────
    def _show_msg(self, text):
        self._clear_msg()
        self.msg_id = self.canvas.create_text(
            CANVAS_W // 2, CANVAS_H - 25,
            text=text, font=FONT_HINT(), fill=TEXT_HINT
        )

    def _clear_msg(self):
        if self.msg_id:
            self.canvas.delete(self.msg_id)
            self.msg_id = None

    def _show_level9_hint(self, c1, c2):
        level = LEVELS[8]
        hint_dict = level["hint"]
        h1 = hint_dict.get(c1["letter"], "")
        h2 = hint_dict.get(c2["letter"], "")
        hint_text = f"{h1}    |    {h2}"
        hint2 = "小口诀: b像6向右, d反写向左, p像9向上, q反写向下"
        self.hint_id = self.canvas.create_text(
            CANVAS_W // 2, CANVAS_H - 48,
            text=hint_text, font=FONT_HINT(), fill=TEXT_HINT
        )
        self.hint2_id = self.canvas.create_text(
            CANVAS_W // 2, CANVAS_H - 26,
            text=hint2, font=FONT_ZH(11), fill="#888888"
        )
        self.window.after(2500, self._clear_hints)

    def _clear_hints(self):
        if self.hint_id:
            self.canvas.delete(self.hint_id)
            self.hint_id = None
        if getattr(self, "hint2_id", None):
            self.canvas.delete(self.hint2_id)
            self.hint2_id = None

    # ── Star Particles ──────────────────────────────────
    def _spawn_stars(self, card):
        cx = card["x"] + card["size"] / 2
        cy = card["y"] + card["size"] / 2
        particles = []
        for _ in range(8):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 6)
            dx = math.cos(angle) * speed
            dy = math.sin(angle) * speed - 3
            size = random.uniform(4, 10)
            pts = self._star_points(cx, cy, size, size * 0.4)
            item = self.canvas.create_polygon(pts, fill=STAR_GOLD, outline="")
            particles.append({"item": item, "x": cx, "y": cy, "dx": dx, "dy": dy,
                              "life": 1.0, "size": size})
        self.star_particles.extend(particles)
        if len(self.star_particles) == len(particles):
            self._animate_stars()

    def _animate_stars(self):
        if not self.star_particles:
            return
        alive = []
        for p in self.star_particles:
            p["x"] += p["dx"]
            p["y"] += p["dy"]
            p["dy"] += 0.3  # gravity
            p["life"] -= 0.035
            if p["life"] > 0:
                sz = p["size"] * p["life"]
                cx, cy = p["x"], p["y"]
                pts = self._star_points(cx, cy, sz, sz * 0.4)
                self.canvas.coords(p["item"], pts)
                alive.append(p)
            else:
                self.canvas.delete(p["item"])
        self.star_particles = alive
        if alive:
            self.window.after(30, self._animate_stars)

    # ── Card Fly to Book ────────────────────────────────
    def _fly_cards_to_book(self, c1, c2):
        target_x = CANVAS_W - 50
        target_y = 30
        for card in (c1, c2):
            self._fly_one_card(card, target_x, target_y, 0)

    def _fly_one_card(self, card, tx, ty, step):
        FRAMES = 12
        sx, sy = card["x"] + card["size"]/2, card["y"] + card["size"]/2
        t = step / FRAMES
        # ease-in-out
        t_eased = t * t * (3 - 2 * t)
        cx = sx + (tx - sx) * t_eased
        cy = sy + (ty - sy) * t_eased
        scale = 1.0 - t * 0.7
        s = card["size"] * scale
        rect = card["items"]["rect"]
        self.canvas.coords(rect, cx - s/2, cy - s/2, cx + s/2, cy + s/2)
        # scale text if present
        txt = card["items"].get("front_text")
        if txt:
            self.canvas.coords(txt, cx, cy)
            self.canvas.itemconfigure(txt, font=FONT_CARD(int(card["size"] * 0.35 * scale)))
        if step < FRAMES:
            self.window.after(25, lambda: self._fly_one_card(card, tx, ty, step + 1))
        else:
            self._hide_card_front(card)
            self.canvas.delete(rect)
            # flash book
            self._flash_book()

    def _flash_book(self):
        if self._book_flash_id:
            self.canvas.delete(self._book_flash_id)
        r = 22
        tx, ty = CANVAS_W - 50, 30
        self._book_flash_id = self.canvas.create_oval(
            tx - r, ty - r, tx + r, ty + r,
            fill="#FFD700", outline="", stipple="gray50"
        )
        self.window.after(200, lambda: self._clear_book_flash())

    def _clear_book_flash(self):
        if self._book_flash_id:
            self.canvas.delete(self._book_flash_id)
            self._book_flash_id = None

    def _draw_book(self):
        tx, ty = CANVAS_W - 50, 30
        r = 18
        # book shape
        self.canvas.create_rectangle(tx - r, ty - r, tx + 2, ty + r, fill="#3F51B5", outline="")
        self.canvas.create_rectangle(tx + 2, ty - r, tx + r, ty + r, fill="#5C6BC0", outline="")
        self.canvas.create_line(tx + 2, ty - r, tx + 2, ty + r, fill="#1A237E", width=1)
        self.canvas.create_text(tx, ty + r + 14, text="收藏本", font=FONT_ZH(10), fill="#888888")

    # ── Level Complete ──────────────────────────────────
    def _show_level_complete(self):
        self.canvas.delete("all")
        self.animating = False
        self._draw_book()
        self.flipped = []
        self.star_particles = []

        if self.current_level_id == 9:
            self.state = "WIN"
            self._play_win()
            self.canvas.create_text(
                CANVAS_W // 2, 100, text="恭喜全部通关！",
                font=FONT_ZH(40, True), fill="#FF6B35"
            )
            self.canvas.create_text(
                CANVAS_W // 2, 170, text="你已经认识了所有拼音字母！",
                font=FONT_ZH(20), fill=TEXT_DARK
            )
            # only "return to menu" button
            self._complete_button(CANVAS_W // 2, 350, "返回菜单", "MENU")
            self.status_var.set("全部通关！太厉害了！")
        else:
            self.state = "LEVEL_COMPLETE"
            self._play_level_complete()
            self.canvas.create_text(
                CANVAS_W // 2, 80, text="太棒了！",
                font=FONT_ZH(40, True), fill="#4CAF50"
            )
            level_name = LEVELS[self.current_level_id - 1]["name"]
            self.canvas.create_text(
                CANVAS_W // 2, 140, text=f"第{self.current_level_id}关 · {level_name} 完成！",
                font=FONT_ZH(20), fill=TEXT_DARK
            )
            # unlock next
            next_lv = self.current_level_id + 1
            if next_lv <= self.highest_unlocked:
                self.canvas.create_text(
                    CANVAS_W // 2, 220,
                    text=f"第{next_lv}关已解锁！",
                    font=FONT_ZH(20), fill=TEXT_DARK
                )
            elif next_lv <= 9:
                self.canvas.create_text(
                    CANVAS_W // 2, 220,
                    text=f"新解锁：第{next_lv}关！",
                    font=FONT_ZH(20), fill="#FF6B35"
                )
            else:
                self.canvas.create_text(
                    CANVAS_W // 2, 220,
                    text="全部完成！",
                    font=FONT_ZH(20), fill=TEXT_DARK
                )

            # buttons
            self._complete_button(250, 350, "下一关 →", "NEXT")
            self._complete_button(550, 350, "返回菜单", "MENU")
            self.status_var.set(f"第{self.current_level_id}关完成！")

        # update progress
        if self.current_level_id < 9 and self.current_level_id + 1 > self.highest_unlocked:
            self.highest_unlocked = self.current_level_id + 1
            self._save_progress()
        if self.current_level_id == 9:
            if self.highest_unlocked < 9:
                self.highest_unlocked = 9
            self._save_progress()

    def _complete_button(self, cx, cy, text, action):
        bw, bh = 160, 50
        rect = self.canvas.create_rectangle(
            cx - bw//2, cy - bh//2, cx + bw//2, cy + bh//2,
            fill="#5B9BD5", outline="#3F7EB6", width=2
        )
        txt = self.canvas.create_text(
            cx, cy, text=text, font=FONT_BTN(), fill="#FFFFFF"
        )
        self._complete_buttons = getattr(self, "_complete_buttons", {})
        self._complete_buttons[action] = {"cx": cx, "cy": cy, "bw": bw, "bh": bh,
                                           "rect": rect, "txt": txt}

    def _handle_complete_click(self, mx, my):
        for action, btn in getattr(self, "_complete_buttons", {}).items():
            cx, cy, bw, bh = btn["cx"], btn["cy"], btn["bw"], btn["bh"]
            if abs(mx - cx) < bw//2 and abs(my - cy) < bh//2:
                if action == "MENU":
                    self.draw_menu()
                elif action == "NEXT":
                    self.start_level(self.current_level_id + 1)
                return



if __name__ == "__main__":
    PinyinMatchGame()
