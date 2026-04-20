#!/usr/bin/env python3
"""
VISION-GUARD Analytics Dashboard
View your productivity and health statistics
"""

import json
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class AnalyticsDashboard:
    """Analytics viewer for Vision Guard sessions"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("📊 VISION-GUARD Analytics")
        self.root.geometry("1000x700")
        self.root.configure(bg='#1e1e1e')
        
        self.load_data()
        self.setup_ui()
    
    def load_data(self):
        """Load session history"""
        data_file = Path('session_history.json')
        if data_file.exists():
            with open(data_file, 'r') as f:
                data = json.load(f)
                self.sessions = data.get('sessions', [])
        else:
            self.sessions = []
    
    def setup_ui(self):
        """Setup the dashboard UI"""
        
        # Header
        header = tk.Frame(self.root, bg='#2d2d30', height=80)
        header.pack(fill='x')
        
        title = tk.Label(
            header,
            text="📊 VISION-GUARD Analytics",
            font=('Arial', 24, 'bold'),
            bg='#2d2d30',
            fg='#61dafb'
        )
        title.pack(pady=20)
        
        # Main content
        main_frame = tk.Frame(self.root, bg='#1e1e1e')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        if not self.sessions:
            # No data message
            no_data = tk.Label(
                main_frame,
                text="No session data yet!\n\nRun vision_guard.py to start tracking.",
                font=('Arial', 14),
                bg='#1e1e1e',
                fg='#cccccc',
                justify='center'
            )
            no_data.pack(expand=True)
            return
        
        # Summary cards
        self.create_summary_cards(main_frame)
        
        # Charts
        self.create_charts(main_frame)
    
    def create_summary_cards(self, parent):
        """Create summary statistics cards"""
        cards_frame = tk.Frame(parent, bg='#1e1e1e')
        cards_frame.pack(fill='x', pady=(0, 20))
        
        # Calculate totals
        total_focus = sum(s['focus_time'] for s in self.sessions)
        total_breaks = sum(s['break_time'] for s in self.sessions)
        total_warnings = sum(s['posture_warnings'] for s in self.sessions)
        avg_productivity = sum(s['productivity_score'] for s in self.sessions) / len(self.sessions)
        
        cards = [
            ("Total Focus Time", str(timedelta(seconds=total_focus)), "#16825d"),
            ("Total Sessions", str(len(self.sessions)), "#0e639c"),
            ("Posture Warnings", str(total_warnings), "#d13438"),
            ("Avg Productivity", f"{avg_productivity:.0f}%", "#f0ad4e")
        ]
        
        for title, value, color in cards:
            card = tk.Frame(cards_frame, bg=color, width=200)
            card.pack(side='left', padx=10, fill='both', expand=True)
            
            tk.Label(
                card,
                text=title,
                font=('Arial', 10),
                bg=color,
                fg='white'
            ).pack(pady=(10, 5))
            
            tk.Label(
                card,
                text=value,
                font=('Arial', 20, 'bold'),
                bg=color,
                fg='white'
            ).pack(pady=(0, 10))
    
    def create_charts(self, parent):
        """Create visualization charts"""
        chart_frame = tk.Frame(parent, bg='#1e1e1e')
        chart_frame.pack(fill='both', expand=True)
        
        # Create figure with subplots
        fig = Figure(figsize=(10, 6), facecolor='#1e1e1e')
        
        # Focus time over time
        ax1 = fig.add_subplot(221, facecolor='#2d2d30')
        dates = [datetime.fromisoformat(s['date']).strftime('%m/%d') for s in self.sessions[-10:]]
        focus_times = [s['focus_time'] / 60 for s in self.sessions[-10:]]  # Convert to minutes
        ax1.plot(dates, focus_times, marker='o', color='#61dafb', linewidth=2)
        ax1.set_title('Focus Time (Last 10 Sessions)', color='white', fontsize=12)
        ax1.set_xlabel('Date', color='white')
        ax1.set_ylabel('Minutes', color='white')
        ax1.tick_params(colors='white')
        ax1.grid(True, alpha=0.2)
        
        # Productivity scores
        ax2 = fig.add_subplot(222, facecolor='#2d2d30')
        productivity = [s['productivity_score'] for s in self.sessions[-10:]]
        ax2.bar(dates, productivity, color='#16825d', alpha=0.7)
        ax2.set_title('Productivity Score', color='white', fontsize=12)
        ax2.set_xlabel('Date', color='white')
        ax2.set_ylabel('Score', color='white')
        ax2.tick_params(colors='white')
        ax2.set_ylim([0, 100])
        
        # Warnings breakdown
        ax3 = fig.add_subplot(223, facecolor='#2d2d30')
        warning_types = ['Posture', 'Distance', 'Eye Strain']
        warning_counts = [
            sum(s['posture_warnings'] for s in self.sessions),
            sum(s['distance_warnings'] for s in self.sessions),
            sum(s['eye_strain_warnings'] for s in self.sessions)
        ]
        colors = ['#d13438', '#f0ad4e', '#0e639c']
        ax3.pie(warning_counts, labels=warning_types, colors=colors, autopct='%1.1f%%',
               textprops={'color': 'white'})
        ax3.set_title('Warning Distribution', color='white', fontsize=12)
        
        # Focus vs Break time
        ax4 = fig.add_subplot(224, facecolor='#2d2d30')
        total_focus = sum(s['focus_time'] for s in self.sessions) / 3600  # Hours
        total_break = sum(s['break_time'] for s in self.sessions) / 3600
        ax4.bar(['Focus', 'Break'], [total_focus, total_break], 
               color=['#16825d', '#61dafb'], alpha=0.7)
        ax4.set_title('Total Time Distribution (Hours)', color='white', fontsize=12)
        ax4.set_ylabel('Hours', color='white')
        ax4.tick_params(colors='white')
        
        fig.tight_layout()
        
        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)


def main():
    """Main entry point"""
    root = tk.Tk()
    app = AnalyticsDashboard(root)
    root.mainloop()


if __name__ == '__main__':
    main()
