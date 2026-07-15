"""
CS408 / Term Project SUquid Quiz Games - Server Application
Group 104 - Hüseyin Eren Yıldız (31047), Bahar Abit (28933)
"""
import socket
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
from datetime import datetime

class QuizServer:
    def __init__(self, root):
        self.root = root
        self.root.title("SUquid Quiz Games - Server")
        self.root.geometry("850x750")
        self.root.resizable(True, True)
        
        # Server state
        self.server_socket = None
        self.is_listening = False
        self.game_started = False
        self.game_ended = False
        
        # Client management
        self.clients = {}  # {username: {'socket': socket, 'address': addr}}
        self.clients_lock = threading.Lock()
        self.disconnected_during_game = set()  #tracking usernames that disconnected during game
        
        # Game state
        self.questions = []
        self.current_question_index = 0
        self.num_questions_to_ask = 0
        self.scoreboard = {}  # {username: score}
        self.current_answers = {}  # {username: answer}
        self.answer_order = []  # List of (username, answer) in order received
        self.waiting_for_answers = False
        self.questions_file_loaded = False
        self.current_question_data = None
        self.setup_gui()
        
    def setup_gui(self): #GUI components setup
        
        main_frame = ttk.Frame(self.root, padding="10") # main frame
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        config_frame = ttk.LabelFrame(main_frame, text="Server Configuration", padding="10")  #config frame
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        port_frame = ttk.Frame(config_frame) #prot config
        port_frame.pack(fill=tk.X, pady=2)
        ttk.Label(port_frame, text="Port Number:", width=18).pack(side=tk.LEFT)
        self.port_var = tk.StringVar()
        self.port_entry = ttk.Entry(port_frame, textvariable=self.port_var, width=20)
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        file_frame = ttk.Frame(config_frame) #queation file
        file_frame.pack(fill=tk.X, pady=2)
        ttk.Label(file_frame, text="Questions File:", width=18).pack(side=tk.LEFT)
        self.file_var = tk.StringVar()
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_var, width=35)
        self.file_entry.pack(side=tk.LEFT, padx=5)
        self.browse_btn = ttk.Button(file_frame, text="Browse", command=self.browse_file)
        self.browse_btn.pack(side=tk.LEFT, padx=5)
        self.load_btn = ttk.Button(file_frame, text="Load File", command=self.load_questions)
        self.load_btn.pack(side=tk.LEFT, padx=5)
        
        num_frame = ttk.Frame(config_frame) #number of question part
        num_frame.pack(fill=tk.X, pady=2)
        ttk.Label(num_frame, text="Number of Questions:", width=18).pack(side=tk.LEFT)
        self.num_questions_var = tk.StringVar(value="5")
        self.num_questions_entry = ttk.Entry(num_frame, textvariable=self.num_questions_var, width=20)
        self.num_questions_entry.pack(side=tk.LEFT, padx=5)
        
        self.file_status_var = tk.StringVar(value="Status: No questions file loaded")  #file status laberl
        self.file_status_label = ttk.Label(config_frame, textvariable=self.file_status_var, foreground="red")
        self.file_status_label.pack(anchor=tk.W, pady=2)
        
        button_frame = ttk.Frame(main_frame) #control buttons frame
        button_frame.pack(fill=tk.X, pady=5)
        self.listen_btn = ttk.Button(button_frame, text="Start Listening", command=self.toggle_listening)
        self.listen_btn.pack(side=tk.LEFT, padx=5)
        self.start_game_btn = ttk.Button(button_frame, text="Start Game", command=self.start_game, state=tk.DISABLED)
        self.start_game_btn.pack(side=tk.LEFT, padx=5)
        self.stop_server_btn = ttk.Button(button_frame, text="Stop Server", command=self.stop_server)
        self.stop_server_btn.pack(side=tk.LEFT, padx=5)
        
        clients_frame = ttk.LabelFrame(main_frame, text="Connected Clients", padding="5") #connected clients frame
        clients_frame.pack(fill=tk.X, pady=5)
        self.clients_listbox = tk.Listbox(clients_frame, height=4)
        self.clients_listbox.pack(fill=tk.X, pady=2)
        
        question_frame = ttk.LabelFrame(main_frame, text="Current Question", padding="5") #current question frame
        question_frame.pack(fill=tk.X, pady=5)
        self.current_question_var = tk.StringVar(value="No active question")
        ttk.Label(question_frame, textvariable=self.current_question_var, wraplength=800).pack(fill=tk.X, pady=2)
        
        score_frame = ttk.LabelFrame(main_frame, text="Scoreboard", padding="5") # scoreboard frame
        score_frame.pack(fill=tk.X, pady=5)
        self.score_text = tk.Text(score_frame, height=6, state=tk.DISABLED)
        self.score_text.pack(fill=tk.X, pady=2)
        
        log_frame = ttk.LabelFrame(main_frame, text="Server Activity Log (All Operations & Errors)", padding="5") #activity log frame
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        log_scrollbar = ttk.Scrollbar(log_frame) #scrollbar for log
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text = tk.Text(log_frame, height=12, yscrollcommand=log_scrollbar.set)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scrollbar.config(command=self.log_text.yview)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)     # to handle window close event
        self.log("Server application started")  #initial log message
        self.log("Please configure port, load questions file, and start listening")
        
    def log(self, message): 
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select Questions File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.file_var.set(filename)
            self.log(f"Selected file: {filename}")
            
    def load_questions(self):  #for reading questions from file
        filename = self.file_var.get().strip()
        if not filename:
            messagebox.showerror("Error", "Please select a questions file first!")
            self.log("ERROR: No questions file selected")
            self.file_status_var.set("Status: No file selected")
            self.file_status_label.config(foreground="red")
            return
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            self.log(f"Reading file: {filename}")
            self.questions = [] #parsed questions list
            i = 0
            while i + 4 <= len(lines) - 1:
                question = lines[i].strip()
                choice_a = lines[i + 1].strip()
                choice_b = lines[i + 2].strip()
                choice_c = lines[i + 3].strip()
                raw_answer = lines[i + 4].strip()

                if ":" in raw_answer:  #if answer line has "Answer: X" format, I know there is no such format in sample file, but just in case
                    left, right = raw_answer.split(":", 1)
                    if left.strip().lower() == "answer":
                        raw_answer = right.strip()
                correct_answer = raw_answer.strip().upper()
                if question and choice_a and choice_b and choice_c and correct_answer in ['A', 'B', 'C']:
                    self.questions.append({
                        'question': question,
                        'A': choice_a,
                        'B': choice_b,
                        'C': choice_c,
                        'correct': correct_answer
                    })
                i += 5
            
            if len(self.questions) == 0:
                raise ValueError("No valid questions found in the file. Check file format.")
                
            self.questions_file_loaded = True
            self.file_status_var.set(f"Status: Successfully loaded {len(self.questions)} questions")
            self.file_status_label.config(foreground="green")
            self.log(f"SUCCESS: Loaded {len(self.questions)} questions from file")
              
            for idx, q in enumerate(self.questions):  #log each question
                self.log(f"  Question {idx+1}: {q['question'][:50]}... (Answer: {q['correct']})")
            self.update_start_button_state()
            
        except FileNotFoundError:
            messagebox.showerror("Error", f"File not found: {filename}")
            self.log(f"ERROR: File not found - {filename}")
            self.file_status_var.set("Status: File not found")
            self.file_status_label.config(foreground="red")
            self.questions_file_loaded = False
        except Exception as e:
            messagebox.showerror("Error", f"Error loading questions: {str(e)}")
            self.log(f"ERROR: Failed to load questions - {str(e)}")
            self.file_status_var.set(f"Status: Error - {str(e)}")
            self.file_status_label.config(foreground="red")
            self.questions_file_loaded = False
            
    def toggle_listening(self):  
        if not self.is_listening:
            self.start_listening()
        else:
            self.stop_listening()
            
    def start_listening(self):
        try:
            port_str = self.port_var.get().strip()
            if not port_str:
                raise ValueError("Port number cannot be empty")
            port = int(port_str)
            if port < 1 or port > 65535:
                raise ValueError("Port must be between 1 and 65535")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid port number: {str(e)}")
            self.log(f"ERROR: Invalid port number - {str(e)}")
            return
            
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('', port))
            self.server_socket.listen(10)
            self.is_listening = True
            
            self.listen_btn.config(text="Stop Listening")
            self.port_entry.config(state=tk.DISABLED)
            self.log(f"SUCCESS: Server started listening on port {port}")
            self.log("Waiting for client connections...")
            
            self.accept_thread = threading.Thread(target=self.accept_connections, daemon=True)  #to accepting connections separate thread
            self.accept_thread.start()  
            self.update_start_button_state()
            
        except OSError as e:
            messagebox.showerror("Error", f"Could not bind to port {port}: {str(e)}")
            self.log(f"ERROR: Failed to bind to port {port} - {str(e)}")
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
        except Exception as e:
            messagebox.showerror("Error", f"Could not start server: {str(e)}")
            self.log(f"ERROR: Failed to start server - {str(e)}")
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
                
    def stop_listening(self): #to stop listening for new connections
        self.is_listening = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        self.listen_btn.config(text="Start Listening")
        self.port_entry.config(state=tk.NORMAL)
        self.log("Server stopped listening for new connections")
        self.update_start_button_state()

    def stop_server(self):
        if self.game_started and not self.game_ended:  #if game is active, end it first
            self.log("Stopping server during active game...")
            self.broadcast_message({
                'type': 'server_shutdown',
                'message': 'Server is shutting down'
            })
            self.end_game()
        
        with self.clients_lock:  #close all client connections
            for username, client_info in list(self.clients.items()):
                try:
                    client_info['socket'].close()
                except:
                    pass
            self.clients.clear()
        
        self.is_listening = False  # close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        
        self.listen_btn.config(text="Start Listening", state=tk.NORMAL)  #reset for GUI
        self.port_entry.config(state=tk.NORMAL)
        self.start_game_btn.config(state=tk.DISABLED)
        self.browse_btn.config(state=tk.NORMAL)
        self.load_btn.config(state=tk.NORMAL)
        self.num_questions_entry.config(state=tk.NORMAL)
        self.update_clients_list()
        self.log("Server stopped completely")

    def accept_connections(self): #to accepting connections
        while self.is_listening:
            try:
                client_socket, address = self.server_socket.accept()
                if self.game_started: #game is started or not
                    try:
                        msg = json.dumps({
                            'type': 'error', 
                            'message': 'Game is already in progress. Cannot accept new connections.'
                        })
                        client_socket.send(msg.encode('utf-8'))
                        client_socket.close()
                        self.root.after(0, lambda a=address: self.log(f"REJECTED: Connection from {a[0]}:{a[1]} - Game in progress"))
                    except:
                        pass
                    continue
                
                handler_thread = threading.Thread(  # to handle new connection in separate thread
                    target=self.handle_new_connection, 
                    args=(client_socket, address), 
                    daemon=True
                )
                handler_thread.start()
                
            except socket.error:
                break
            except Exception as e:
                if self.is_listening:
                    self.root.after(0, lambda e=e: self.log(f"ERROR: Failed to accept connection - {str(e)}"))
                    
    def handle_new_connection(self, client_socket, address):
        try:
            client_socket.settimeout(30)
            data = client_socket.recv(4096).decode('utf-8') #receiving username
            msg = json.loads(data)
            
            if msg.get('type') != 'connect':
                self.root.after(0, lambda a=address: self.log(f"REJECTED: Invalid connection request from {a[0]}:{a[1]}"))
                client_socket.close()
                return         
            username = msg.get('username', '').strip()
            
            if not username: #to validate usernama
                response = json.dumps({'type': 'error', 'message': 'Username cannot be empty'})
                client_socket.send(response.encode('utf-8'))
                client_socket.close()
                self.root.after(0, lambda a=address: self.log(f"REJECTED: Empty username from {a[0]}:{a[1]}"))
                return
            
            with self.clients_lock: #checking existing clients for duplicates
                if username in self.clients:
                    response = json.dumps({
                        'type': 'error', 
                        'message': f'Username "{username}" is already in use. Please choose a different name.'
                    })
                    client_socket.send(response.encode('utf-8'))
                    client_socket.close()
                    self.root.after(0, lambda u=username, a=address: 
                        self.log(f"REJECTED: Duplicate username '{u}' from {a[0]}:{a[1]}"))
                    return
                
                if username in self.disconnected_during_game: #to prevent reconnection, if disconnected during game
                    response = json.dumps({
                        'type': 'error', 
                        'message': f'Username "{username}" disconnected during an active game and cannot reconnect.'
                    })
                    client_socket.send(response.encode('utf-8'))
                    client_socket.close()
                    self.root.after(0, lambda u=username: 
                        self.log(f"REJECTED: '{u}' tried to reconnect after disconnecting during game"))
                    return
                
                self.clients[username] = { #storing client info
                    'socket': client_socket,
                    'address': address
                }
                self.scoreboard[username] = 0
            
            response = json.dumps({ #welcome message for client
                'type': 'connected', 
                'message': f'Welcome to SUquid Quiz Games, {username}!'
            })
            client_socket.send(response.encode('utf-8'))
            client_socket.settimeout(None)
            
            self.root.after(0, lambda u=username, a=address: self.on_client_connected(u, a)) #update gui
            self.client_listener(username, client_socket) #start listening for client messages
            
        except socket.timeout:
            self.root.after(0, lambda a=address: self.log(f"TIMEOUT: Connection from {a[0]}:{a[1]} timed out"))
            try:
                client_socket.close()
            except:
                pass
        except Exception as e:
            self.root.after(0, lambda e=e, a=address: self.log(f"ERROR: Connection from {a[0]}:{a[1]} failed - {str(e)}"))
            try:
                client_socket.close()
            except:
                pass
                
    def on_client_connected(self, username, address):    # after successful connection
        self.log(f"CONNECTED: Client '{username}' from {address[0]}:{address[1]}")
        self.update_clients_list()
        self.update_scoreboard_display()
        self.update_start_button_state()
        self.broadcast_client_list()  #to inform all clients about new connection
        
    def client_listener(self, username, client_socket):     # start listening for client messages
        while True:
            try:
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break                   
                msg = json.loads(data)
                self.root.after(0, lambda u=username, m=msg: self.handle_client_message(u, m))
                
            except socket.error:
                break
            except json.JSONDecodeError:
                self.root.after(0, lambda u=username: self.log(f"WARNING: Received invalid JSON from {u}"))
                continue
            except Exception as e:
                self.root.after(0, lambda e=e, u=username: self.log(f"ERROR: Receiving from {u} - {str(e)}"))
                break
        
        self.root.after(0, lambda u=username: self.on_client_disconnected(u))  #client disconnection handling
        
    def handle_client_message(self, username, msg): 
        msg_type = msg.get('type')
        
        if msg_type == 'answer':
            if self.waiting_for_answers and username not in self.current_answers:
                answer = msg.get('answer', '').upper()
                if answer in ['A', 'B', 'C']:
                    self.current_answers[username] = answer
                    self.answer_order.append((username, answer))
                    self.log(f"ANSWER: {username} answered '{answer}'")
                    with self.clients_lock:
                        active_players = list(self.clients.keys())
                    active_answered = sum(1 for u in active_players if u in self.current_answers)    
                    if active_players and active_answered >= len(active_players):
                        self.process_answers()
                else:
                    self.log(f"WARNING: Invalid answer '{answer}' from {username}")
            elif username in self.current_answers:
                self.log(f"WARNING: Duplicate answer attempt from {username} (ignored)")
                    
        elif msg_type == 'disconnect':
            self.log(f"DISCONNECT REQUEST: {username} requested to disconnect")
            self.on_client_disconnected(username)
            
    def on_client_disconnected(self, username):
        was_in_game = self.game_started and not self.game_ended
        removed = False
        with self.clients_lock:
            if username in self.clients:
                try:
                    self.clients[username]['socket'].close()
                except:
                    pass
                del self.clients[username]
                removed = True

                if username in self.current_answers:
                    del self.current_answers[username]
                self.answer_order = [(u, a) for (u, a) in self.answer_order if u != username]
                if was_in_game:
                    self.disconnected_during_game.add(username)
        if not removed:
            return
                
        self.log(f"DISCONNECTED: Client '{username}' left the server")
        if was_in_game:
            self.log(f"  -> '{username}' disconnected during active game")
        
        self.update_clients_list()
        self.update_start_button_state()
        self.broadcast_client_list() #to inform all clients about disconnection
        self.broadcast_message({
            'type': 'player_disconnected',
            'username': username,
            'message': f"Player '{username}' has disconnected"
        })
        
        if self.game_started and not self.game_ended: #condition to check game continuation
            with self.clients_lock:
                remaining_players = len(self.clients)
            self.log(f"  -> Remaining players: {remaining_players}")

            if remaining_players < 2:
                self.log("  -> Less than 2 players remaining")
                if remaining_players == 0:
                    self.end_game()
                    return
                if self.waiting_for_answers:
                    with self.clients_lock:
                        active_players = list(self.clients.keys()) 
                    active_answered = sum(1 for u in active_players if u in self.current_answers)
                    if active_players and active_answered >= len(active_players):
                        self.process_answers()
                    else:
                        self.log("  -> Waiting for the remaining player's answer before ending the game")
                        return
                else:
                    self.end_game()

                return            

    def update_clients_list(self): 
        self.clients_listbox.delete(0, tk.END)
        with self.clients_lock:
            for username in self.clients:
                self.clients_listbox.insert(tk.END, username) 
                
    def update_start_button_state(self): 
        with self.clients_lock:
            client_count = len(self.clients)

        num_q_str = self.num_questions_var.get().strip()
        valid_num = False
        error_msg = None    

        if num_q_str == "":
            error_msg = None
        else:
            try:
                num_q = int(num_q_str)
                if num_q > 0:
                    valid_num = True
                else:
                    error_msg = f"Number of questions must be positive (entered: {num_q})"
            except ValueError:
                error_msg = f"Invalid number of questions format (entered: '{num_q_str}')"
        
        if error_msg and getattr(self, '_last_num_error', None) != error_msg:
            self.log(f"ERROR: {error_msg}")
            self._last_num_error = error_msg
        elif valid_num:
            self._last_num_error = None

        can_start = (
            self.is_listening and
            client_count >= 2 and
            self.questions_file_loaded and
            valid_num and
            not self.game_started
        )
        
        if can_start:
            self.start_game_btn.config(state=tk.NORMAL)
        else:
            self.start_game_btn.config(state=tk.DISABLED)
            
    def start_game(self):
        try: #checking valid number of questions
            num_questions = int(self.num_questions_var.get())
            if num_questions < 1:
                raise ValueError("Must ask at least 1 question")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid number of questions: {str(e)}")
            self.log(f"ERROR: Invalid number of questions - {str(e)}")
            return
        
        with self.clients_lock: #checking connected enough clients tıo start game
            if len(self.clients) < 2:
                messagebox.showerror("Error", "Need at least 2 players to start the game!")
                self.log("ERROR: Cannot start game - need at least 2 players")
                return
            player_names = list(self.clients.keys())
        
        if not self.questions_file_loaded or len(self.questions) == 0:  # checking questions loaded
            messagebox.showerror("Error", "Please load a valid questions file first!")
            self.log("ERROR: Cannot start game - no questions loaded")
            return
        
        self.num_questions_to_ask = num_questions
        self.current_question_index = 0
        self.game_started = True
        self.game_ended = False
        self.disconnected_during_game.clear()
    
        self.start_game_btn.config(state=tk.DISABLED)
        self.browse_btn.config(state=tk.DISABLED)
        self.load_btn.config(state=tk.DISABLED)
        self.num_questions_entry.config(state=tk.DISABLED)
        self.listen_btn.config(state=tk.DISABLED)
        
        self.log("=" * 50)
        self.log(f"GAME STARTED with {self.num_questions_to_ask} questions")
        self.log(f"Players: {', '.join(player_names)}")
        
        self.broadcast_message({ #informing all clients about game start
            'type': 'game_start',
            'message': 'The game is starting!',
            'num_questions': self.num_questions_to_ask,
            'players': player_names
        })
        
        self.send_scoreboard_to_all() #sending scoreboard to all clients
        self.root.after(1500, self.send_next_question) #sending first question after a short delay
        
    def send_next_question(self):
        with self.clients_lock: #checking connected clients before sending next question
            if len(self.clients) < 2:
                self.log("Less than 2 players remaining. Ending game.")
                self.end_game()
                return
        if self.current_question_index >= self.num_questions_to_ask: #all questions asked checking
            self.log("All questions have been asked. Ending game.")
            self.end_game()
            return
            
        # get question --> cycle through if we need more than available
        question_idx = self.current_question_index % len(self.questions)
        question = self.questions[question_idx]
        self.current_question_data = question
        
        self.current_answers = {}
        self.answer_order = []
        self.waiting_for_answers = True
        question_num = self.current_question_index + 1
        self.current_question_var.set(   # showing question on gui
            f"Q{question_num}/{self.num_questions_to_ask}: {question['question']}\n"
            f"{question['A']}  |  {question['B']}  |  {question['C']}"
        )
        
        self.log("-" * 40) # for well appearance in output log
        self.log(f"QUESTION {question_num}/{self.num_questions_to_ask}: {question['question']}")
        self.log(f"  {question['A']}")
        self.log(f"  {question['B']}")
        self.log(f"  {question['C']}")
        self.log(f"  Correct Answer: {question['correct']}")
        self.log("Waiting for player answers")

        msg = {   #sending question to clients
            'type': 'question',
            'question_number': question_num,
            'total_questions': self.num_questions_to_ask,
            'question': question['question'],
            'choices': {
                'A': question['A'],
                'B': question['B'],
                'C': question['C']
            }
        }
        self.broadcast_message(msg)
        
    def process_answers(self): # evaluating answers and updating scores
        if not self.waiting_for_answers:
            return   
        self.waiting_for_answers = False      
        if self.current_question_data is None:
            return
    
        correct_answer = self.current_question_data['correct']
        question_num = self.current_question_index + 1
        self.log(f"Processing answers for Question {question_num}")
        with self.clients_lock:
            active_players = list(self.clients.keys())
        
        num_players = len(active_players)
        results = {} #calculating scores and preparing responses
        first_correct_found = False
        first_correct_player = None
        
        for username, answer in self.answer_order:
            if username not in active_players:
                continue
                
            is_correct = (answer == correct_answer)
            points = 0
            is_first = False
            if is_correct:
                points = 1   #guarantee point for correct answer
                if not first_correct_found:
                    points += (num_players - 1)    #if a player is first to answer correctly, it gets extra points
                    first_correct_found = True
                    is_first = True
                    first_correct_player = username
                self.scoreboard[username] = self.scoreboard.get(username, 0) + points

            results[username] = {
                'is_correct': is_correct,
                'is_first': is_first,
                'points': points,
                'correct_answer': correct_answer,
                'their_answer': answer
            }
        
        for username in active_players: #handling players who did not answer
            if username not in results:
                results[username] = {
                    'is_correct': False,
                    'is_first': False,
                    'points': 0,
                    'correct_answer': correct_answer,
                    'their_answer': 'No answer'
                }
        
        self.log(f"Answer Results for Question {question_num}:") 
        for username in active_players:
            r = results.get(username, {})
            status = "CORRECT" if r.get('is_correct') else "WRONG"
            first_tag = " (FIRST!)" if r.get('is_first') else ""
            self.log(f"  {username}: {r.get('their_answer', 'N/A')} - {status}{first_tag} (+{r.get('points', 0)} pts)")
        if first_correct_player:
            self.log(f"  First correct answer: {first_correct_player} (+{num_players} total points)")
        
        sorted_scoreboard = self.get_sorted_scoreboard() #sending updated scoreboard to clients  
        with self.clients_lock:
            for username, client_info in self.clients.items():
                if username in results:
                    result = results[username]
                    msg = {
                        'type': 'answer_result',
                        'question_number': question_num,
                        'your_answer': result['their_answer'],
                        'correct_answer': correct_answer,
                        'is_correct': result['is_correct'],
                        'is_first': result['is_first'],
                        'points_earned': result['points'],
                        'your_total_score': self.scoreboard.get(username, 0),
                        'scoreboard': sorted_scoreboard
                    }
                    try:
                        client_info['socket'].send(json.dumps(msg).encode('utf-8'))
                    except Exception as e:
                        self.log(f"ERROR: Failed to send result to {username} - {str(e)}")
        
        
        self.update_scoreboard_display() #updating scoreboard display in gui
        self.log("Current Standings:")
        for entry in sorted_scoreboard:
            self.log(f"  {entry['rank']}. {entry['username']}: {entry['score']} pts")
        
        self.current_question_index += 1 #incrementing queston index to go to next question
        
        with self.clients_lock:    #  checking connected clients to decide game continuation
            remaining_players = len(self.clients)
        
        if remaining_players < 2:
            self.log("Less than 2 players remaining after processing answers")
            self.root.after(2000, self.end_game)
        elif self.current_question_index >= self.num_questions_to_ask:
            self.log("All questions completed")
            self.root.after(2000, self.end_game)
        else:
            self.root.after(2500, self.send_next_question)
            
    def get_sorted_scoreboard(self): #to determining rankings and sorting scoreboard
        
        sorted_scores = sorted(self.scoreboard.items(), key=lambda x: x[1], reverse=True) # Sort by score descending
        # adding rankings to handle ties
        result = []        
        current_rank = 1
        prev_score = None
        players_at_prev_rank = 0
        
        for username, score in sorted_scores:
            if prev_score is not None and score < prev_score:
                current_rank += players_at_prev_rank
                players_at_prev_rank = 1
            elif prev_score is not None and score == prev_score:
                players_at_prev_rank += 1
            else:
                players_at_prev_rank = 1
            with self.clients_lock:         #checking if player is disconnected
                is_disconnected = username not in self.clients

            result.append({
                'rank': current_rank,
                'username': username,
                'score': score,
                'disconnected': is_disconnected 
            })
            prev_score = score
        return result
        
    def update_scoreboard_display(self): # updating scoreboard display in gui
        self.score_text.config(state=tk.NORMAL)
        self.score_text.delete(1.0, tk.END)
        sorted_sb = self.get_sorted_scoreboard()
        for entry in sorted_sb:
            rank_suffix = self.get_rank_suffix(entry['rank'])
            disconnected_mark = " (disconnected)" if entry.get('disconnected', False) else ""
            self.score_text.insert(tk.END, 
                f"{entry['rank']}{rank_suffix} place - {entry['username']}{disconnected_mark}: {entry['score']} points\n")        
        self.score_text.config(state=tk.DISABLED)
        
    def get_rank_suffix(self, rank):
        return 'th' if 11 <= rank % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(rank % 10, 'th')

    def send_scoreboard_to_all(self): # broadcasting scoreboard to all clients
        msg = {
            'type': 'scoreboard',
            'scoreboard': self.get_sorted_scoreboard()
        }
        self.broadcast_message(msg)
        
    def end_game(self):  
        if self.game_ended:
            return
            
        self.game_ended = True
        self.game_started = False
        self.waiting_for_answers = False
        sorted_sb = self.get_sorted_scoreboard() #getting final sorted scoreboard
        winners = []
        if sorted_sb:
            top_score = sorted_sb[0]['score']
            winners = [entry['username'] for entry in sorted_sb if entry['score'] == top_score]
        
        self.log("=" * 50)     #for well formatted output, we put these symbols
        self.log("GAME OVER!")
        self.log("=" * 50)
        
        if len(winners) == 1:
            self.log(f"WINNER: {winners[0]}")
        elif len(winners) > 1:
            self.log(f"TIE! Winners: {', '.join(winners)}")
        else:
            self.log("No winners determined")
        self.log("Final Rankings:")
        for entry in sorted_sb:
            rank_suffix = self.get_rank_suffix(entry['rank'])
            self.log(f"  {entry['rank']}{rank_suffix} - {entry['username']}: {entry['score']} points")
        
        self.current_question_var.set("Game Over! See final results above.")  #updating gui current question box
        msg = {  # broadcasting final results to all clients
            'type': 'game_over',
            'winners': winners,
            'final_scoreboard': sorted_sb,
            'message': f"Game Over! Winner(s): {', '.join(winners)}" if winners else "Game Over!"
        }
        self.broadcast_message(msg)
        
        self.update_scoreboard_display()  #updating scoreboard display in gui
        with self.clients_lock:  # closing all client connections
            for username, client_info in list(self.clients.items()):
                try:
                    client_info['socket'].close()
                except:
                    pass
            self.clients.clear()
        
        self.scoreboard = {}
        self.current_question_index = 0
        self.current_question_data = None
        self.disconnected_during_game.clear()
        
        self.browse_btn.config(state=tk.NORMAL)
        self.load_btn.config(state=tk.NORMAL)
        self.num_questions_entry.config(state=tk.NORMAL)
        self.listen_btn.config(state=tk.NORMAL)
        
        self.update_clients_list()
        self.update_start_button_state()
        
        self.log("=" * 50)     #for well formatted output, we put these symebols
        self.log("Server is ready for a new game")
        self.log("Clients have been disconnected. Waiting for new connections...")
        self.log("=" * 50)
        
    def broadcast_message(self, msg): #to all clients
        msg_json = json.dumps(msg)
        with self.clients_lock:
            for username, client_info in list(self.clients.items()):
                try:
                    client_info['socket'].send(msg_json.encode('utf-8'))
                except Exception as e:
                    self.log(f"ERROR: Failed to send to {username} - {str(e)}")
                    
    def broadcast_client_list(self): # updated client list to all clients
        with self.clients_lock:
            client_names = list(self.clients.keys())
        msg = {
            'type': 'client_list',
            'clients': client_names
        }
        self.broadcast_message(msg)
        
    def on_closing(self):  #server shutdown handling
        self.log("Server shutting down...")
        if self.game_started and not self.game_ended:
            self.broadcast_message({
                'type': 'server_shutdown',
                'message': 'Server is shutting down'
            })
        with self.clients_lock:
            for username, client_info in list(self.clients.items()):
                try:
                    client_info['socket'].close()
                except:
                    pass
        
        self.is_listening = False   # stop listening
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        self.root.destroy()

def main():
    root = tk.Tk()
    app = QuizServer(root)
    root.mainloop()

if __name__ == "__main__":
    main()