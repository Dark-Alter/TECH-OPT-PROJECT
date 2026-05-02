import sys
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QSpinBox, QDoubleSpinBox, QFormLayout, 
                             QFrame, QLineEdit, QComboBox, QScrollArea, QMessageBox)
from PyQt6.QtCore import QTimer, Qt

# Distinct colors for players
PLAYER_COLORS = ['#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4', 
                 '#46f0f0', '#f032e6', '#bcf60c', '#fabebe', '#008080']

class NetworkVisualizer(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        super().__init__(self.fig)
        self.G = nx.DiGraph()
        
    def draw_network(self, nodes, links, link_loads, strategies, paths, anim_progress):
        self.ax.clear()
        self.G.clear()
        self.G.add_nodes_from(nodes)
        self.G.add_edges_from([(l['u'], l['v']) for l in links])
        
        # Use a fixed seed so the topology doesn't jump around every frame
        pos = nx.spring_layout(self.G, seed=42) 
        
        edge_labels = {}
        for l in links:
            u, v = l['u'], l['v']
            load = link_loads.get(u+v, 0)
            edge_labels[(u, v)] = f"k={load}\nc={l['a']}k+{l['b']}"

        nx.draw(self.G, pos, ax=self.ax, with_labels=True, node_color='skyblue', 
                node_size=800, arrowsize=20, font_weight='bold')
        nx.draw_networkx_edge_labels(self.G, pos, edge_labels=edge_labels, ax=self.ax, font_size=7)

        # Draw the moving player markers
        for p_idx, strat_idx in enumerate(strategies):
            if strat_idx >= len(paths): continue
            path_links = paths[strat_idx]
            n_links = len(path_links)
            
            # Determine link and local progress[cite: 1]
            link_index = int(anim_progress * n_links)
            if link_index >= n_links: link_index = n_links - 1
            local_progress = (anim_progress * n_links) - link_index
            
            # Get node names for the current link
            link_str = path_links[link_index]
            # Handle potential multi-char node names by finding the split point[cite: 1]
            # This logic assumes nodes in links are formatted as 'UV'
            u_node = None
            for n in nodes:
                if link_str.startswith(n):
                    u_node = n
                    v_node = link_str[len(n):]
                    break
            
            if u_node and v_node in pos:
                p1, p2 = pos[u_node], pos[v_node]
                px = p1[0] + local_progress * (p2[0] - p1[0])
                py = p1[1] + local_progress * (p2[1] - p1[1])
                
                # Visual offset so players don't overlap on the same link[cite: 1]
                offset = 0.08 * (p_idx - len(strategies)/2)
                self.ax.plot(px, py + offset, 'o', color=PLAYER_COLORS[p_idx % 10], 
                             markersize=12, markeredgecolor='black', zorder=5)
        self.draw()

class GameWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("USTHB - Game Theory Load Balancing")
        # Default Topology: Braess Paradox[cite: 1]
        self.nodes = ['S', 'A', 'B', 'D']
        self.links = [
            {'u': 'S', 'v': 'A', 'a': 1.0, 'b': 0.0},
            {'u': 'S', 'v': 'B', 'a': 0.0, 'b': 10.0},
            {'u': 'A', 'v': 'D', 'a': 0.0, 'b': 10.0},
            {'u': 'B', 'v': 'D', 'a': 1.0, 'b': 0.0},
            {'u': 'A', 'v': 'B', 'a': 0.0, 'b': 0.0}
        ]
        self.anim_progress = 0.0
        self.is_equilibrium = False
        self.paths = []
        
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.advance_animation)
        self.timer.start(33)
        self.setup_game()

    def init_ui(self):
        main_layout = QHBoxLayout()
        sidebar = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # 1. Topology Editor Section
        content_layout.addWidget(QLabel("<b>1. Topology Editor</b>"))
        self.node_input = QLineEdit(); self.node_input.setPlaceholderText("Node name")
        content_layout.addWidget(self.node_input)
        content_layout.addWidget(QPushButton("Add Node", clicked=self.add_node))
        
        self.combo_s = QComboBox(); self.combo_d = QComboBox()
        content_layout.addWidget(QLabel("Start Node:")); content_layout.addWidget(self.combo_s)
        content_layout.addWidget(QLabel("End Node:")); content_layout.addWidget(self.combo_d)

        self.link_u = QComboBox(); self.link_v = QComboBox()
        self.link_a = QDoubleSpinBox(); self.link_b = QDoubleSpinBox()
        self.link_a.setRange(0, 100); self.link_b.setRange(0, 100)
        
        link_form = QFormLayout()
        link_form.addRow("From:", self.link_u); link_form.addRow("To:", self.link_v)
        link_form.addRow("Coeff a:", self.link_a); link_form.addRow("Const b:", self.link_b)
        content_layout.addLayout(link_form)
        content_layout.addWidget(QPushButton("Add/Update Link", clicked=self.add_link))

        btn_apply = QPushButton("APPLY TOPOLOGY")
        btn_apply.clicked.connect(self.setup_game)
        btn_apply.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 5px;")
        content_layout.addWidget(btn_apply)

        # 2. Control Section[cite: 1]
        content_layout.addWidget(QLabel("<hr><b>2. Game Controls</b>"))
        self.player_spin = QSpinBox(); self.player_spin.setRange(1, 10); self.player_spin.setValue(3)
        content_layout.addWidget(QLabel("Number of Players:")); content_layout.addWidget(self.player_spin)
        
        self.btn_reset = QPushButton("RESET SIMULATION")
        self.btn_reset.clicked.connect(self.reset_simulation)
        self.btn_reset.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        content_layout.addWidget(self.btn_reset)

        self.btn_step = QPushButton("Next Iteration (BRD)")
        self.btn_step.clicked.connect(self.run_step)
        content_layout.addWidget(self.btn_step)

        # 3. Legend & Stats[cite: 1]
        self.legend_layout = QVBoxLayout()
        content_layout.addWidget(QLabel("<b>Player Keys:</b>"))
        content_layout.addLayout(self.legend_layout)
        
        self.stats_label = QLabel("")
        content_layout.addWidget(self.stats_label)
        
        scroll.setWidget(content)
        sidebar.addWidget(scroll)
        main_layout.addLayout(sidebar, 1)
        
        self.canvas = NetworkVisualizer(self)
        main_layout.addWidget(self.canvas, 3)
        self.setLayout(main_layout)
        self.update_combos()

    def add_node(self):
        name = self.node_input.text().strip().upper()
        if name and name not in self.nodes:
            self.nodes.append(name)
            self.update_combos()
            self.node_input.clear()

    def add_link(self):
        u, v = self.link_u.currentText(), self.link_v.currentText()
        if u and v and u != v:
            # Remove duplicate link if it exists[cite: 1]
            self.links = [l for l in self.links if not (l['u'] == u and l['v'] == v)]
            self.links.append({'u': u, 'v': v, 'a': self.link_a.value(), 'b': self.link_b.value()})

    def update_combos(self):
        for c in [self.combo_s, self.combo_d, self.link_u, self.link_v]:
            c.clear()
            c.addItems(self.nodes)
        if 'S' in self.nodes: self.combo_s.setCurrentText('S')
        if 'D' in self.nodes: self.combo_d.setCurrentText('D')

    def setup_game(self):
        """Initializes the graph and calculates paths[cite: 1]"""
        start = self.combo_s.currentText()
        end = self.combo_d.currentText()
        
        temp_G = nx.DiGraph()
        temp_G.add_edges_from([(l['u'], l['v']) for l in self.links])
        
        try:
            if not nx.has_path(temp_G, start, end):
                raise ValueError("No path exists between Start and End.")
            
            raw_paths = list(nx.all_simple_paths(temp_G, start, end))
            self.paths = [[p[i] + p[i+1] for i in range(len(p)-1)] for p in raw_paths]
            self.current_costs = {l['u']+l['v']: (l['a'], l['b']) for l in self.links}
            self.reset_simulation()
        except Exception as e:
            QMessageBox.warning(self, "Topology Error", str(e))

    def reset_simulation(self):
        """Resets players without changing the topology[cite: 1]"""
        self.is_equilibrium = False
        from game_engine import CongestionGame
        if hasattr(self, 'current_costs') and self.paths:
            self.game = CongestionGame(self.player_spin.value(), self.paths, self.current_costs)
            self.update_legend()
        self.update_view()

    def update_legend(self):
        while self.legend_layout.count():
            child = self.legend_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        for i in range(self.player_spin.value()):
            color = PLAYER_COLORS[i % 10]
            lbl = QLabel(f"<font color='{color}'>■</font> Player {i+1}")
            self.legend_layout.addWidget(lbl)

    def advance_animation(self):
        self.anim_progress = (self.anim_progress + 0.01) % 1.0
        self.update_view()

    def run_step(self):
        if hasattr(self, 'game'):
            changed = self.game.best_response_step()
            if not changed:
                self.is_equilibrium = True
            self.update_view()

    def update_view(self):
        if not hasattr(self, 'game'): return
        loads = self.game.get_link_loads(self.game.strategies)
        self.canvas.draw_network(self.nodes, self.links, loads, 
                                 self.game.strategies, self.paths, self.anim_progress)
        
        sc_nash = self.game.get_social_cost()
        opt_cost, _ = self.game.find_social_optimum()
        poa = sc_nash / opt_cost if opt_cost > 0 else 1.0
        
        status = (f"<b>Price of Anarchy:</b> {poa:.3f}<br>"
                  f"<b>Nash Social Cost:</b> {sc_nash:.1f}")
        if self.is_equilibrium:
            status += "<br><font color='green'><b>(Equilibrium Reached!)</b></font>"
        self.stats_label.setText(status)