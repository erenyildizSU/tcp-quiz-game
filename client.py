import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import json
from datetime import datetime


class QuizClient:
    def __init__(self, root):
        self.root = root
        self.root.title("SUquid Quiz Games - Client")
        self.root.geometry("850x750")
        self.root.resizable(True, True)

        #socket used to talk to the server
        self.client_socket = None
        self.is_connected = False
        self.username = ""
        self.current_question = None # holds the current question sent by the server
        # stores the selected answer 
        self.selected_answer = tk.StringVar(value="")
        self.game_in_progress = False
        self.answer_submitted = False
        
        self.setup_gui()
        
    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding="10") 
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        top_frame = ttk.Frame(main_frame) # Top section of the layout
        top_frame.pack(fill=tk.X, expand=False)

        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL) #slits the UI into left and right parts
        paned.pack(fill=tk.X, expand=False)

        left_frame = ttk.Frame(paned)
        right_frame = ttk.Frame(paned)

        paned.add(left_frame, weight=3)   #main UI
        paned.add(right_frame, weight=1)  # for log panel
        
        conn_frame = ttk.LabelFrame(left_frame, text="Connection Settings", padding="10") # Connection frame
        conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        ip_frame = ttk.Frame(conn_frame) # Server IP input
        ip_frame.pack(fill=tk.X, pady=2)
        ttk.Label(ip_frame, text="Server IP:", width=12).pack(side=tk.LEFT)
        self.ip_var = tk.StringVar()
        self.ip_entry = ttk.Entry(ip_frame, textvariable=self.ip_var, width=25)
        self.ip_entry.pack(side=tk.LEFT, padx=5)
        
        port_frame = ttk.Frame(conn_frame) # Server port input
        port_frame.pack(fill=tk.X, pady=2)
        ttk.Label(port_frame, text="Port:", width=12).pack(side=tk.LEFT)
        self.port_var = tk.StringVar()
        self.port_entry = ttk.Entry(port_frame, textvariable=self.port_var, width=25)
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        user_frame = ttk.Frame(conn_frame) # Username input
        user_frame.pack(fill=tk.X, pady=2)
        ttk.Label(user_frame, text="Username:", width=12).pack(side=tk.LEFT)
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(user_frame, textvariable=self.username_var, width=25)
        self.username_entry.pack(side=tk.LEFT, padx=5)
        
        btn_frame = ttk.Frame(conn_frame) 
        btn_frame.pack(fill=tk.X, pady=5)
        self.connect_btn = ttk.Button(btn_frame, text="Connect", command=self.connect_to_server)
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        self.disconnect_btn = ttk.Button(btn_frame, text="Disconnect", command=self.disconnect_from_server, state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=5)
        self.status_var = tk.StringVar(value="Status: Not connected")
        self.status_label = ttk.Label(conn_frame, textvariable=self.status_var, foreground="red")
        self.status_label.pack(anchor=tk.W)
        
        # players frame 
        players_frame = ttk.LabelFrame(left_frame, text="Connected Players", padding="5")
        players_frame.pack(fill=tk.X, pady=5)
        self.players_listbox = tk.Listbox(players_frame, height=5)
        self.players_listbox.pack(fill=tk.X, pady=2)
        
        # question frame
        question_frame = ttk.LabelFrame(main_frame, text="Current Question", padding="10")
        question_frame.pack(fill=tk.BOTH, expand=True, pady=5) 
        self.question_label = ttk.Label(question_frame, text="Waiting for the game to start...", 
                                         wraplength=650, font=('Helvetica', 11))
        self.question_label.pack(fill=tk.X, pady=5)

        # Frame holds the answer options a,b,c
        self.answer_frame = ttk.Frame(question_frame)
        self.answer_frame.pack(fill=tk.X, pady=5)
        
        self.radio_a = ttk.Radiobutton(self.answer_frame, text="A: ", variable=self.selected_answer, 
                                        value="A", state=tk.DISABLED)
        self.radio_a.pack(anchor=tk.W, pady=2)
        self.radio_b = ttk.Radiobutton(self.answer_frame, text="B: ", variable=self.selected_answer, 
                                        value="B", state=tk.DISABLED)
        self.radio_b.pack(anchor=tk.W, pady=2)
        self.radio_c = ttk.Radiobutton(self.answer_frame, text="C: ", variable=self.selected_answer, 
                                        value="C", state=tk.DISABLED)
        self.radio_c.pack(anchor=tk.W, pady=2)
        
        self.submit_btn = ttk.Button(question_frame, text="Submit Answer", 
                                      command=self.submit_answer, state=tk.DISABLED)
        self.submit_btn.pack(pady=10)
        
        self.result_var = tk.StringVar(value="")
        self.result_label = ttk.Label(question_frame, textvariable=self.result_var, 
                                       font=('Helvetica', 10, 'bold'), wraplength=650)
        self.result_label.pack(fill=tk.X, pady=5)
        
        # scoreboard frame
        score_frame = ttk.LabelFrame(left_frame, text="Scoreboard", padding="5")
        score_frame.pack(fill=tk.X, pady=5)

        self.score_text = tk.Text(score_frame, height=5, state=tk.DISABLED)
        self.score_text.pack(fill=tk.X, pady=2)
        
        #log frame
        log_frame = ttk.LabelFrame(right_frame, text="Activity Log", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        log_scrollbar = ttk.Scrollbar(log_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text = tk.Text(log_frame, height=6, yscrollcommand=log_scrollbar.set)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scrollbar.config(command=self.log_text.yview)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log("Client application started")
        
    def log(self, message):# Writing  message to  activity log with a timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
    def connect_to_server(self):# Handling connection to the server
        server_ip = self.ip_var.get().strip()
        if not server_ip:
            messagebox.showerror("Error", "Please enter server IP!")
            return
        try:
            port = int(self.port_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid port!")
            return
        username = self.username_var.get().strip()
        if not username:
            messagebox.showerror("Error", "Please enter username!")
            return
        
        self.log(f"Connecting to {server_ip}:{port}...")
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Creating socketand connect
            self.client_socket.settimeout(10)
            self.client_socket.connect((server_ip, port))
            
            msg = json.dumps({'type': 'connect', 'username': username})# Telling  server we want to connect
            self.client_socket.send(msg.encode('utf-8'))
            
            response = self.client_socket.recv(4096).decode('utf-8') # Reading response from the server
            response_msg = json.loads(response)
            
            if response_msg.get('type') == 'error':
                messagebox.showerror("Error", response_msg.get('message'))
                self.log(f"ERROR: {response_msg.get('message')}")
                self.client_socket.close()
                self.client_socket = None
                return
                
            if response_msg.get('type') == 'connected':# Updating UI successfyl connection
                self.is_connected = True
                self.username = username
                self.client_socket.settimeout(None)
                
                self.status_var.set(f"Status: Connected as {username}")
                self.status_label.config(foreground="green")
                self.connect_btn.config(state=tk.DISABLED)
                self.disconnect_btn.config(state=tk.NORMAL)
                self.ip_entry.config(state=tk.DISABLED)
                self.port_entry.config(state=tk.DISABLED)
                self.username_entry.config(state=tk.DISABLED)
                
                self.log(f"SUCCESS: {response_msg.get('message')}")
                # start listening server in background
                self.listener_thread = threading.Thread(target=self.listen_to_server, daemon=True)
                self.listener_thread.start()
                
        except socket.timeout:
            messagebox.showerror("Error", "Connection timed out")
            self.log("ERROR: Connection timed out")
        except ConnectionRefusedError:
            messagebox.showerror("Error", "Connection refused by server")
            self.log("ERROR: Connection refused by server")
        except ConnectionResetError:
            messagebox.showerror("Error", "Connection was reset by server")
            self.log("ERROR: Connection was reset by server")
        except OSError as e:
            # Windows socket errors 
            messagebox.showerror("Error", "Connection failed - server may have closed the connection")
            self.log(f"ERROR: Connection failed - {e.errno}")
        except Exception as e:
            messagebox.showerror("Error", f"Connection error: {type(e).__name__}")
            self.log(f"ERROR: {type(e).__name__} - {str(e)}")
                
    def disconnect_from_server(self): # sending disconnect  message and closing conection
        if self.client_socket:
            try:
                msg = json.dumps({'type': 'disconnect'})
                self.client_socket.send(msg.encode('utf-8'))
            except:
                pass
            self.cleanup_connection()
            
    def cleanup_connection(self): #reset connection state and UI
        self.is_connected = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        
        self.status_var.set("Status: Not connected")
        self.status_label.config(foreground="red")
        self.connect_btn.config(state=tk.NORMAL)
        self.disconnect_btn.config(state=tk.DISABLED)
        self.ip_entry.config(state=tk.NORMAL)
        self.port_entry.config(state=tk.NORMAL)
        self.username_entry.config(state=tk.NORMAL)
        
        self.reset_question_ui()
        self.players_listbox.delete(0, tk.END)
        self.game_in_progress = False
        self.log("Disconnected from server")

    def listen_to_server(self):# Listening for messages from server
        while self.is_connected:
            try:
                data = self.client_socket.recv(4096).decode('utf-8')
                if not data:
                    break
                messages = self.parse_json_messages(data)
                for msg in messages:
                    self.root.after(0, lambda m=msg: self.handle_server_message(m))
            except socket.error:
                break
            except Exception as e:
                self.root.after(0, lambda: self.log(f"ERROR: {str(e)}"))
                break
        self.root.after(0, self.on_connection_lost)
        
    def parse_json_messages(self, data): # Parse incoming JSON messages
        messages = []
        decoder = json.JSONDecoder()
        pos = 0
        while pos < len(data):
            try:
                msg, index = decoder.raw_decode(data, pos)
                messages.append(msg)
                pos += index
                while pos < len(data) and data[pos] in ' \n\r\t':
                    pos += 1
            except json.JSONDecodeError:
                break
        return messages
        
    def handle_server_message(self, msg): # Decide what to do based on server messages
        msg_type = msg.get('type')
        
        if msg_type == 'client_list':
            clients = msg.get('clients', [])
            self.log(f"Client list updated: {', '.join(clients)}")
            self.update_players_list(clients)
        elif msg_type == 'scoreboard':
            sb = msg.get('scoreboard', [])
            self.log("Scoreboard updated")
            self.update_scoreboard(sb)
        elif msg_type == 'game_start':
            self.log("GAME STARTING!")
            self.log(f"Total questions: {msg.get('num_questions')}")
            self.log(f"Players: {', '.join(msg.get('players', []))}")
            self.log("=" * 40)
            self.game_in_progress = True
        elif msg_type == 'question':
            self.display_question(msg)
        elif msg_type == 'answer_result':
            self.display_answer_result(msg)
        elif msg_type == 'game_over':
            self.display_game_over(msg)
        elif msg_type == 'player_disconnected':
            self.log(f"Player disconnected: {msg.get('username')}")
        elif msg_type == 'server_shutdown':
            self.log("Server is shutting down!")
            messagebox.showinfo("Server Shutdown", "Server is shutting down.")
            self.cleanup_connection()
        elif msg_type == 'error':
            self.log(f"ERROR: {msg.get('message')}")
            
    def update_players_list(self, clients):# Update the players list
        self.players_listbox.delete(0, tk.END)
        for client in clients:
            display = client + (" (You)" if client == self.username else "")
            self.players_listbox.insert(tk.END, display)
            
    def update_scoreboard(self, scoreboard): # Show updated scores
        self.score_text.config(state=tk.NORMAL)
        self.score_text.delete(1.0, tk.END)
        for entry in scoreboard:
            suffix = self.get_rank_suffix(entry['rank'])
            marker = " <-- YOU" if entry['username'] == self.username else ""
            disconnected_mark = " (disconnected)" if entry.get('disconnected', False) else ""
            self.score_text.insert(tk.END, 
                f"{entry['rank']}{suffix} - {entry['username']}{disconnected_mark}: {entry['score']} pts{marker}\n")
        self.score_text.config(state=tk.DISABLED)
        
    def get_rank_suffix(self, rank): # Getting rank suffix
        if 11 <= rank % 100 <= 13:
            return 'th'
        elif rank % 10 == 1:
            return 'st'
        elif rank % 10 == 2:
            return 'nd'
        elif rank % 10 == 3:
            return 'rd'
        return 'th'
            
    def display_question(self, msg):# showing the question and reset answers
        self.game_in_progress = True
        self.answer_submitted = False
        self.current_question = msg
        
        q_num = msg.get('question_number', 0)
        total = msg.get('total_questions', 0)
        question = msg.get('question', '')
        choices = msg.get('choices', {})
        
        self.question_label.config(text=f"Question {q_num}/{total}: {question}")
        self.radio_a.config(text=choices.get('A', ''), state=tk.NORMAL)
        self.radio_b.config(text=choices.get('B', ''), state=tk.NORMAL)
        self.radio_c.config(text=choices.get('C', ''), state=tk.NORMAL)
        self.selected_answer.set("")
        self.submit_btn.config(state=tk.NORMAL)
        self.result_var.set("")
        
        self.log(f"Question {q_num}: {question}")
        
    def submit_answer(self):
        answer = self.selected_answer.get()
        if not answer:
            messagebox.showwarning("Warning", "Please select an answer!")
            return
        if not self.is_connected:
            messagebox.showerror("Error", "Not connected!")
            return
        if self.answer_submitted:
            return
        try:
            msg = json.dumps({'type': 'answer', 'answer': answer})
            self.client_socket.send(msg.encode('utf-8'))
            self.answer_submitted = True
            
            self.radio_a.config(state=tk.DISABLED)
            self.radio_b.config(state=tk.DISABLED)
            self.radio_c.config(state=tk.DISABLED)
            self.submit_btn.config(state=tk.DISABLED)
            
            self.result_var.set("Answer submitted! Waiting for others...")
            self.result_label.config(foreground="blue")
            self.log(f"Submitted answer: {answer}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.log(f"ERROR sending answer: {str(e)}")
            
    def display_answer_result(self, msg): # Showing result of  submitted answer
        your_answer = msg.get('your_answer', 'N/A')
        correct = msg.get('correct_answer', '?')
        is_correct = msg.get('is_correct', False)
        is_first = msg.get('is_first', False)
        points = msg.get('points_earned', 0)
        total = msg.get('your_total_score', 0)
        
        if is_correct:
            if is_first:
                text = f"CORRECT and FIRST! +{points} points (Total: {total})"
            else:
                text = f"Correct! +{points} point (Total: {total})"
            self.result_label.config(foreground="green")
        else:
            text = f"Wrong! Your answer: {your_answer}, Correct: {correct} (Total: {total})"
            self.result_label.config(foreground="red")
            
        self.result_var.set(text)
        self.log(text)
        self.update_scoreboard(msg.get('scoreboard', []))
        
    def display_game_over(self, msg):# show game over screen
        self.game_in_progress = False
        winners = msg.get('winners', [])
        scoreboard = msg.get('final_scoreboard', [])
        
        self.reset_question_ui()
        
        if self.username in winners:
            if len(winners) == 1:
                text = "YOU WON!"
            else:
                others = [w for w in winners if w != self.username]
                text = f"TIE! You won with: {', '.join(others)}"
            self.result_label.config(foreground="green")
        else:
            text = f"Game Over! Winner(s): {', '.join(winners)}"
            self.result_label.config(foreground="blue")
            
        self.result_var.set(text)
        self.question_label.config(text="Game Over!")
        self.update_scoreboard(scoreboard)
        
        self.log("=" * 40)
        self.log("GAME OVER!")
        if winners:
            self.log(f"Winner(s): {', '.join(winners)}")
        self.log("Final Rankings:")
        for e in scoreboard:
            self.log(f"  {e['rank']}. {e['username']}: {e['score']} pts")
        self.log("=" * 40)
        
    def reset_question_ui(self):# reseting question area for next round
        self.question_label.config(text="Waiting for next game...")
        self.radio_a.config(text="", state=tk.DISABLED)
        self.radio_b.config(text="", state=tk.DISABLED)
        self.radio_c.config(text="", state=tk.DISABLED)
        self.selected_answer.set("")
        self.submit_btn.config(state=tk.DISABLED)
        self.current_question = None
        self.answer_submitted = False
        
    def on_connection_lost(self):# handling  lost connection to server
        if self.is_connected:
            self.log("Connection to server lost!")
            messagebox.showwarning("Connection Lost", "Lost connection to server.")
            self.cleanup_connection()
            
    def on_closing(self):# Clean  and close  application
        if self.is_connected:
            try:
                msg = json.dumps({'type': 'disconnect'})
                self.client_socket.send(msg.encode('utf-8'))
            except:
                pass
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        self.is_connected = False
        self.root.destroy()

def main():# starting the client application
    root = tk.Tk()
    app = QuizClient(root)
    root.mainloop()

if __name__ == "__main__":
    main()
