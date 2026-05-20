import tkinter as tk
import random

CELL = 20
COLS = 30
ROWS = 20
WIDTH = COLS * CELL
HEIGHT = ROWS * CELL
INITIAL_SPEED = 120

DIRECTIONS = {
    "Up":    (0, -1),
    "Down":  (0,  1),
    "Left":  (-1, 0),
    "Right": (1,  0),
}

OPPOSITE = {
    "Up": "Down", "Down": "Up",
    "Left": "Right", "Right": "Left",
}


class SnakeGame:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Snake Game")
        self.window.resizable(False, False)

        self.canvas = tk.Canvas(
            self.window, width=WIDTH, height=HEIGHT, bg="#1a1a2e"
        )
        self.canvas.pack()

        self.score_var = tk.StringVar(value="Score: 0")
        score_label = tk.Label(
            self.window, textvariable=self.score_var,
            font=("Consolas", 14), fg="#e0e0e0", bg="#16213e", pady=6
        )
        score_label.pack(fill=tk.X)

        self.window.bind("<KeyPress>", self.on_key)

        self.new_game()
        self.window.mainloop()

    def new_game(self):
        self.canvas.delete("all")
        self.snake = [(COLS // 2, ROWS // 2)]
        self.direction = "Right"
        self.next_direction = "Right"
        self.score = 0
        self.speed = INITIAL_SPEED
        self.running = True
        self.score_var.set("Score: 0")
        self.spawn_food()
        self.draw_all()
        self.window.after(self.speed, self.tick)

    def spawn_food(self):
        while True:
            x = random.randint(0, COLS - 1)
            y = random.randint(0, ROWS - 1)
            if (x, y) not in self.snake:
                self.food = (x, y)
                break

    def draw_all(self):
        self.canvas.delete("all")
        # food
        fx, fy = self.food
        self.canvas.create_rectangle(
            fx * CELL, fy * CELL,
            fx * CELL + CELL, fy * CELL + CELL,
            fill="#e94560", outline=""
        )
        # snake
        for i, (sx, sy) in enumerate(self.snake):
            color = "#0f3460" if i == 0 else "#16c79a"
            self.canvas.create_rectangle(
                sx * CELL, sy * CELL,
                sx * CELL + CELL, sy * CELL + CELL,
                fill=color, outline=""
            )

    def on_key(self, event):
        key = event.keysym
        if key in DIRECTIONS and key != OPPOSITE.get(self.direction):
            self.next_direction = key
        elif key == "r" and not self.running:
            self.new_game()

    def tick(self):
        if not self.running:
            return

        self.direction = self.next_direction
        dx, dy = DIRECTIONS[self.direction]
        head_x, head_y = self.snake[0]
        new_head = (head_x + dx, head_y + dy)

        # wall collision
        if not (0 <= new_head[0] < COLS and 0 <= new_head[1] < ROWS):
            self.game_over()
            return

        # self collision
        if new_head in self.snake:
            self.game_over()
            return

        self.snake.insert(0, new_head)

        if new_head == self.food:
            self.score += 10
            self.score_var.set(f"Score: {self.score}")
            self.spawn_food()
            self.speed = max(50, self.speed - 2)
        else:
            self.snake.pop()

        self.draw_all()
        self.window.after(self.speed, self.tick)

    def game_over(self):
        self.running = False
        self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 - 12,
            text="GAME OVER", fill="#e94560",
            font=("Consolas", 28, "bold")
        )
        self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 + 22,
            text="Press R to restart", fill="#e0e0e0",
            font=("Consolas", 14)
        )


if __name__ == "__main__":
    SnakeGame()
